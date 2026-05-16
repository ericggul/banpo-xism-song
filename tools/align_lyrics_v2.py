#!/usr/bin/env python3
"""
v2 forced-alignment — monotonic segment walk.

Why monotonic-walk instead of global Needleman–Wunsch:
  v1 used difflib LCS over the flat syllable sequence; that drops mismatched
  syllables and clips line boundaries early.
  A naïve global NW over the flat sequence is *worse* on repetitive lyrics:
  the chorus repeats three times, NW collapses them to a single match span
  and squishes the other two repetitions into the wrong place.

This version walks whisper *segments* in order and consumes lyric lines
sequentially — so chorus repetitions stay separate because we move forward
through both streams together. Inside each segment, when one segment covers
multiple lyric lines (e.g. Verse 1 of song 1 is one segment of 4 lines),
NW alignment runs *locally* on that small region — no repetition there, so
NW behaves correctly.

  1. For each segment, try consuming N ∈ {1..5} lyric lines starting at the
     pointer; pick the N that maximises difflib similarity ratio between the
     segment hangul and the concatenated lyric hangul.
  2. If best ratio < 0.35, treat the segment as ad-lib / hallucination and
     skip it without consuming any lines.
  3. For N == 1, the lyric line inherits the segment's start/end directly
     (snapped to the segment's first/last word boundary).
  4. For N > 1, locally NW-align lyric chars to the segment's words; each
     lyric line gets (first_matched_word.start, last_matched_word.end).
  5. Lines that never get a match (e.g. a chorus repetition whisper hummed
     past silently) are interpolated from neighbours, then bounds are made
     monotonic + clamped.

I/O is identical to v1.

Usage:
    align_lyrics_v2.py WHISPER.json LYRICS.txt OUT.json
"""
from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

HANGUL_RE = re.compile(r"[가-힣]")
PUNCT_RE = re.compile(r"[\s.,!?·…\-–—\"'`()\[\]]")

MIN_SEG_MATCH = 0.35      # below this, the segment is treated as noise
MAX_LINES_PER_SEG = 5     # cap on lookahead inside one segment


# NW for *local* alignment inside one segment (no repetition, safe).
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
        row = S[i]
        prev = S[i - 1]
        ai = a[i - 1]
        for j in range(1, m + 1):
            s = MATCH if ai == b[j - 1] else MISMATCH
            row[j] = max(prev[j - 1] + s, prev[j] + GAP, row[j - 1] + GAP)

    pairs: list[tuple[int | None, int | None]] = []
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


def split_segment_by_words(words: list[dict], lines: list[tuple[str, str]]):
    """Split a multi-line segment into per-line (start, end). Words have
    'start','end','word'. Returns list of (start, end) or None for lines
    that got no anchor."""
    # Build chars for segment (each char tagged with whisper word index)
    seg_chars: list[tuple[str, int]] = []
    for wi, w in enumerate(words):
        for c in clean_hangul(w.get("word", "")):
            seg_chars.append((c, wi))

    # Build chars for lyric lines (each char tagged with line index 0..N-1)
    lyr_chars: list[tuple[str, int]] = []
    for li, (_, t) in enumerate(lines):
        for c in clean_hangul(t):
            lyr_chars.append((c, li))

    if not seg_chars or not lyr_chars:
        return [None] * len(lines)

    pairs = nw([c for c, _ in lyr_chars], [c for c, _ in seg_chars])
    first_w: list[int | None] = [None] * len(lines)
    last_w: list[int | None] = [None] * len(lines)
    for li, wi in pairs:
        if li is None or wi is None:
            continue
        line_idx = lyr_chars[li][1]
        word_idx = seg_chars[wi][1]
        if first_w[line_idx] is None or word_idx < first_w[line_idx]:
            first_w[line_idx] = word_idx
        if last_w[line_idx] is None or word_idx > last_w[line_idx]:
            last_w[line_idx] = word_idx

    out: list[tuple[float, float] | None] = []
    for li in range(len(lines)):
        fw, lw = first_w[li], last_w[li]
        if fw is None or lw is None:
            out.append(None)
        else:
            out.append((float(words[fw]["start"]), float(words[lw]["end"])))
    return out


def align_segments(
    whisper_data: dict,
    lyric_lines: list[tuple[str, str]],
) -> tuple[list[list[float] | None], list[str]]:
    segments = whisper_data.get("segments", [])
    n_lines = len(lyric_lines)
    line_times: list[list[float] | None] = [None] * n_lines
    log: list[str] = []
    line_ptr = 0

    for seg_i, seg in enumerate(segments):
        if line_ptr >= n_lines:
            break

        seg_text = clean_hangul(seg.get("text", ""))
        words = [w for w in seg.get("words", [])
                 if clean_hangul(w.get("word", ""))]
        if len(seg_text) < 2 or not words:
            log.append(f"seg{seg_i}: noise (too short)")
            continue

        seg_start = float(words[0]["start"])
        seg_end = float(words[-1]["end"])

        remaining = n_lines - line_ptr
        best_n, best_ratio = 0, 0.0
        for n in range(1, min(MAX_LINES_PER_SEG, remaining) + 1):
            target = "".join(clean_hangul(t) for _, t in lyric_lines[line_ptr:line_ptr + n])
            if not target:
                continue
            r = SequenceMatcher(None, seg_text, target, autojunk=False).ratio()
            # prefer multi-line consumption when ratio is comparable
            if r > best_ratio + 0.02:
                best_ratio, best_n = r, n

        if best_ratio < MIN_SEG_MATCH:
            log.append(
                f"seg{seg_i} ({seg_start:.1f}s) skip — best ratio {best_ratio:.2f}: {seg_text[:30]!r}"
            )
            continue

        if best_n == 1:
            line_times[line_ptr] = [seg_start, seg_end]
            log.append(
                f"seg{seg_i} ({seg_start:.2f}–{seg_end:.2f}) → line {line_ptr+1} (r={best_ratio:.2f})"
            )
            line_ptr += 1
        else:
            sub = split_segment_by_words(
                words, lyric_lines[line_ptr:line_ptr + best_n]
            )
            # Fill any None with segment-wide bounds
            for k, t in enumerate(sub):
                if t is None:
                    line_times[line_ptr + k] = None
                else:
                    line_times[line_ptr + k] = [t[0], t[1]]
            log.append(
                f"seg{seg_i} ({seg_start:.2f}–{seg_end:.2f}) → lines {line_ptr+1}..{line_ptr+best_n} (r={best_ratio:.2f}, split)"
            )
            line_ptr += best_n

    return line_times, log


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
    per_line, log = align_segments(d, lyric_lines)
    matched = sum(1 for x in per_line if x is not None)
    last_anchor = max((x[1] for x in per_line if x is not None), default=0.0)
    total_duration = last_anchor + 1.0
    timings = fill_and_enforce(per_line, total_duration)

    if verbose:
        for line in log:
            print(line)
    print(f"v2 · matched {matched}/{len(lyric_lines)} lines")
    out_p.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
