#!/usr/bin/env python3
"""
v3 forced-alignment — global dynamic-programming assignment.

Why v3:
  v2 walks whisper segments greedily and consumes lyric lines as it goes.
  This breaks when whisper produces short *hallucinated duplicate* segments
  alongside the real long ones (very common on slow/ballad songs that
  re-state the same lyric line — whisper sometimes emits a 1.4-second false
  echo of a line that actually shows up 5 seconds later for real).

v3 makes ALL segment-to-line assignment decisions globally, optimising:

    max  Σ ratio(seg s → lines l..l+k-1) * k_weight(k)
       - SKIP_PENALTY * (segments skipped)
       - UNASSIGNED_PENALTY * (lyric lines left unassigned)

subject to:
    · segments and lines are consumed in order (monotonic);
    · a segment may match 1..MAX_K consecutive lines;
    · multi-line consumption requires duration / k ≥ MIN_DUR_PER_LINE
      (so a 1.4-second hallucinated echo can't claim 2 lines);
    · the *best ratio* over a competing later segment is preferred even
      when both could plausibly match the same line (this naturally drops
      short hallucinations in favour of the real long segment).

I/O is identical to v1/v2.

Usage:
    align_lyrics_v3.py WHISPER.json LYRICS.txt OUT.json [-v]
"""
from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

HANGUL_RE = re.compile(r"[가-힣]")
PUNCT_RE = re.compile(r"[\s.,!?·…\-–—\"'`()\[\]]")

MIN_RATIO = 0.20           # ratio below this won't be considered a match at all
MAX_K = 8                  # at most this many lyric lines per segment (raised for dense tracks where whisper crams a whole verse + chorus into one segment, e.g. song 3 seg1 covers 7 lines)
MIN_DUR_PER_LINE = 0.85    # any matched segment must give ≥ this many seconds per consumed line
SKIP_PENALTY = 0.15        # cost of skipping one whisper segment
UNASSIGNED_PENALTY = 0.30  # cost of leaving one lyric line unassigned.
                            # Kept low so DP prefers skipping a line that
                            # whisper genuinely missed over force-absorbing
                            # it into an unrelated neighbouring segment.

# Dedup uses both text similarity AND temporal proximity. A repeating
# chorus 30s later is NOT a hallucination — only flag near-by echoes.
DEDUP_MAX_MIDPOINT_DIST_S = 18.0

# Local NW for splitting a multi-line segment (no repetition inside → safe)
GAP = -2
MISMATCH = -1
MATCH = 3


def parse_lyrics(path: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    section = ""
    sec_re = re.compile(r"^\s*\[(.+)\]\s*$")
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s:
            continue
        m = sec_re.match(s)
        if m:
            section = m.group(1).strip()
            continue
        out.append((section, s))
    return out


def clean_hangul(s: str) -> str:
    return "".join(c for c in PUNCT_RE.sub("", s) if HANGUL_RE.match(c))


def nw(a: list[str], b: list[str]):
    n, m = len(a), len(b)
    S = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        S[i][0] = i * GAP
    for j in range(1, m + 1):
        S[0][j] = j * GAP
    for i in range(1, n + 1):
        row = S[i]; prev = S[i - 1]; ai = a[i - 1]
        for j in range(1, m + 1):
            s = MATCH if ai == b[j - 1] else MISMATCH
            row[j] = max(prev[j - 1] + s, prev[j] + GAP, row[j - 1] + GAP)
    pairs = []
    i, j = n, m
    while i > 0 and j > 0:
        s = MATCH if a[i - 1] == b[j - 1] else MISMATCH
        if S[i][j] == S[i - 1][j - 1] + s:
            pairs.append((i - 1, j - 1)); i -= 1; j -= 1
        elif S[i][j] == S[i - 1][j] + GAP:
            pairs.append((i - 1, None)); i -= 1
        else:
            pairs.append((None, j - 1)); j -= 1
    while i > 0:
        pairs.append((i - 1, None)); i -= 1
    while j > 0:
        pairs.append((None, j - 1)); j -= 1
    pairs.reverse()
    return pairs


def split_segment_by_words(words: list[dict], lines: list[str]):
    """Split a multi-line segment into per-line (start,end). lines = cleaned strings."""
    seg_chars = []
    for wi, w in enumerate(words):
        for c in clean_hangul(w.get("word", "")):
            seg_chars.append((c, wi))
    lyr_chars = []
    for li, t in enumerate(lines):
        for c in t:
            lyr_chars.append((c, li))
    if not seg_chars or not lyr_chars:
        return [None] * len(lines)

    pairs = nw([c for c, _ in lyr_chars], [c for c, _ in seg_chars])
    first_w = [None] * len(lines); last_w = [None] * len(lines)
    for li, wi in pairs:
        if li is None or wi is None:
            continue
        line_idx = lyr_chars[li][1]
        word_idx = seg_chars[wi][1]
        if first_w[line_idx] is None or word_idx < first_w[line_idx]:
            first_w[line_idx] = word_idx
        if last_w[line_idx] is None or word_idx > last_w[line_idx]:
            last_w[line_idx] = word_idx
    out = []
    for li in range(len(lines)):
        fw, lw = first_w[li], last_w[li]
        if fw is None or lw is None:
            out.append(None)
        else:
            out.append((float(words[fw]["start"]), float(words[lw]["end"])))
    return out


def prep_segments(whisper_data: dict):
    """Drop empty/noise segments and pre-compute clean text + word lists.
    Also pre-filter obvious whisper *hallucinated duplicates*: if two
    segments have ≥0.7 SequenceMatcher similarity and one is < 60% the
    duration of the other, drop the shorter."""
    raw = whisper_data.get("segments", [])
    prepped = []
    for s in raw:
        words = [w for w in s.get("words", [])
                 if clean_hangul(w.get("word", ""))]
        text = clean_hangul(s.get("text", ""))
        if not words or len(text) < 2:
            continue
        prepped.append({
            "start": float(words[0]["start"]),
            "end": float(words[-1]["end"]),
            "text": text,
            "words": words,
        })

    # de-duplicate hallucinations. Two segments count as duplicates only if:
    #   1. text similarity ≥ 0.7
    #   2. midpoint time distance ≤ DEDUP_MAX_MIDPOINT_DIST_S
    #      (a chorus that repeats 30s later is NOT a hallucination)
    #   3. one segment is ≤ 60% the duration of the other
    drop = set()
    for i, a in enumerate(prepped):
        if i in drop:
            continue
        mid_a = (a["start"] + a["end"]) / 2
        for j in range(i + 1, min(len(prepped), i + 8)):
            if j in drop:
                continue
            b = prepped[j]
            mid_b = (b["start"] + b["end"]) / 2
            if abs(mid_b - mid_a) > DEDUP_MAX_MIDPOINT_DIST_S:
                continue
            sim = SequenceMatcher(None, a["text"], b["text"], autojunk=False).ratio()
            if sim < 0.7:
                continue
            da = a["end"] - a["start"]; db = b["end"] - b["start"]
            if da < 0.6 * db:
                drop.add(i); break
            if db < 0.6 * da:
                drop.add(j)
    kept = [s for i, s in enumerate(prepped) if i not in drop]
    return kept, [(prepped[i]["start"], prepped[i]["text"]) for i in sorted(drop)]


def dp_align(segs, lyric_lines):
    """Returns (assignments, log_lines).
       assignments[i] = (start, end) or None for each lyric line."""
    n_segs = len(segs); n_lines = len(lyric_lines)
    NEG = -1e15

    line_clean = [clean_hangul(t) for _, t in lyric_lines]

    # ratio of segment text vs concatenation of lines [l..l+k-1]
    ratio_cache: dict[tuple[int, int, int], float] = {}
    def get_ratio(s, l, k):
        key = (s, l, k)
        if key in ratio_cache:
            return ratio_cache[key]
        target = "".join(line_clean[l + i] for i in range(k))
        if not target:
            ratio_cache[key] = 0.0
            return 0.0
        r = SequenceMatcher(None, segs[s]["text"], target, autojunk=False).ratio()
        ratio_cache[key] = r
        return r

    # ratio of segment text vs ONE specific line — used to penalise multi-line
    # consumption that includes lines whisper clearly didn't actually
    # transcribe in this segment.
    indiv_cache: dict[tuple[int, int], float] = {}
    def indiv_ratio(s, l):
        key = (s, l)
        if key in indiv_cache:
            return indiv_cache[key]
        if not line_clean[l]:
            indiv_cache[key] = 0.0
            return 0.0
        r = SequenceMatcher(
            None, segs[s]["text"], line_clean[l], autojunk=False
        ).ratio()
        indiv_cache[key] = r
        return r

    # threshold below which a consumed line is treated as "not really in this
    # segment" — each such line costs ABSENT_LINE_PEN inside the match score.
    LINE_PRESENT_THR = 0.22
    ABSENT_LINE_PEN = 0.35

    # dp[s][l] = best score from state (s, l) onward
    # act[s][l] = ("skip",) | ("match", k) | None
    dp = [[NEG] * (n_lines + 1) for _ in range(n_segs + 1)]
    act = [[None] * (n_lines + 1) for _ in range(n_segs + 1)]

    # base: end of segments — pay penalty for any unassigned lyric lines
    for l in range(n_lines + 1):
        dp[n_segs][l] = -UNASSIGNED_PENALTY * (n_lines - l)

    # Process states in order so dependencies are ready:
    #   match(s, l, k) → dp[s+1][l+k]  (next-row, ready)
    #   skip_seg(s, l) → dp[s+1][l]    (next-row, ready)
    #   skip_line(s, l) → dp[s][l+1]   (same row, larger l) — so iterate l
    #                                   from high to low.
    for s in range(n_segs - 1, -1, -1):
        for l in range(n_lines, -1, -1):
            best = dp[s + 1][l] - SKIP_PENALTY
            best_act = ("skip_seg",)

            # Option: skip lyric line l entirely (whisper missed it).
            # Pays UNASSIGNED_PENALTY but lets the segment land on a later
            # line that actually matches it. Without this, a missed line
            # forces the next segment to absorb it with garbage timing,
            # which cascades and squeezes subsequent lines.
            if l < n_lines:
                v = dp[s][l + 1] - UNASSIGNED_PENALTY
                if v > best:
                    best = v; best_act = ("skip_line",)

            if l < n_lines:
                seg = segs[s]
                dur = seg["end"] - seg["start"]
                max_k_dur = max(1, int(dur // MIN_DUR_PER_LINE))
                for k in range(1, min(MAX_K, max_k_dur, n_lines - l) + 1):
                    r = get_ratio(s, l, k)
                    if r < MIN_RATIO:
                        continue
                    # Per-line presence check: every consumed lyric line must
                    # have at least LINE_PRESENT_THR individual ratio with the
                    # segment, otherwise we treat that line as not actually
                    # contained in this segment and penalise.
                    absent_count = sum(
                        1 for i in range(k)
                        if indiv_ratio(s, l + i) < LINE_PRESENT_THR
                    )
                    score = r + 0.03 * (k - 1) - ABSENT_LINE_PEN * absent_count
                    v = dp[s + 1][l + k] + score
                    if v > best:
                        best = v; best_act = ("match", k)
            dp[s][l] = best
            act[s][l] = best_act

    # backtrack
    assignments: list[tuple[float, float] | None] = [None] * n_lines
    log = []
    s = 0; l = 0
    while s < n_segs and l < n_lines:
        a = act[s][l]
        if a is None:
            break
        if a[0] == "skip_seg":
            seg = segs[s]
            log.append(f"  skip seg @ {seg['start']:6.2f}–{seg['end']:6.2f}  {seg['text'][:40]!r}")
            s += 1
        elif a[0] == "skip_line":
            log.append(f"  skip line {l+1} (no whisper match): {lyric_lines[l][1][:30]}")
            l += 1
        else:  # ("match", k)
            _, k = a
            seg = segs[s]
            if k == 1:
                assignments[l] = (seg["start"], seg["end"])
                log.append(f"  seg @ {seg['start']:6.2f}–{seg['end']:6.2f} → line {l+1} ({lyric_lines[l][1][:30]})")
            else:
                sub = split_segment_by_words(seg["words"], line_clean[l:l + k])
                for i, t in enumerate(sub):
                    if t is not None:
                        assignments[l + i] = t
                log.append(f"  seg @ {seg['start']:6.2f}–{seg['end']:6.2f} → lines {l+1}..{l+k} (split)")
            l += k
            s += 1
    # drain any remaining unassigned lines into the log
    while l < n_lines:
        log.append(f"  skip line {l+1} (tail, no whisper match): {lyric_lines[l][1][:30]}")
        l += 1
    return assignments, log


def fill_and_enforce(per_line, total_duration):
    n = len(per_line)
    out = [list(x) if x else None for x in per_line]
    known = [i for i, x in enumerate(out) if x is not None]
    if not known:
        s, e = total_duration * 0.05, total_duration * 0.95
        per = (e - s) / n
        return [{"start": round(s + i * per, 3), "end": round(s + (i + 1) * per, 3)} for i in range(n)]

    if known[0] > 0:
        first = out[known[0]]
        approx = max(0.5, first[1] - first[0])
        for k in range(known[0] - 1, -1, -1):
            off = known[0] - k
            out[k] = [max(0.0, first[0] - off * approx),
                      max(0.0, first[0] - (off - 1) * approx)]
    if known[-1] < n - 1:
        last = out[known[-1]]
        approx = max(0.5, last[1] - last[0])
        for k in range(known[-1] + 1, n):
            off = k - known[-1]
            out[k] = [last[1] + (off - 1) * approx, last[1] + off * approx]
    for a, b in zip(known, known[1:]):
        if b - a == 1:
            continue
        s, e = out[a][1], out[b][0]
        per = (e - s) / (b - a)
        for k in range(a + 1, b):
            out[k] = [s + (k - a - 1) * per, s + (k - a) * per]

    for i in range(1, n):
        if out[i][0] < out[i - 1][1]:
            out[i][0] = out[i - 1][1]
        if out[i][1] <= out[i][0]:
            out[i][1] = out[i][0] + 0.3
    for i in range(n):
        out[i][0] = min(out[i][0], total_duration - 0.1)
        out[i][1] = min(out[i][1], total_duration)
        if out[i][1] <= out[i][0]:
            out[i][1] = out[i][0] + 0.2

    return [{"start": round(x[0], 3), "end": round(x[1], 3)} for x in out]


def main():
    args = sys.argv[1:]
    verbose = False
    if "-v" in args:
        verbose = True; args.remove("-v")
    if len(args) != 3:
        sys.exit(__doc__)
    whisper_p = Path(args[0]); lyrics_p = Path(args[1]); out_p = Path(args[2])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyrics(lyrics_p)
    segs, dropped = prep_segments(d)

    if verbose:
        for t, txt in dropped:
            print(f"  drop dup @ {t:.2f}s  {txt[:40]!r}")
    assignments, log = dp_align(segs, lyric_lines)
    if verbose:
        for line in log:
            print(line)

    matched = sum(1 for a in assignments if a is not None)
    last_anchor = max((a[1] for a in assignments if a is not None), default=0.0)
    total_duration = last_anchor + 1.0
    timings = fill_and_enforce(assignments, total_duration)

    print(f"v3 · matched {matched}/{len(lyric_lines)} lines · dropped {len(dropped)} dup-segments")
    out_p.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
