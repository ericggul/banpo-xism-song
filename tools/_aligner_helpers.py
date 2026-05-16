"""
Shared helpers used by per-song aligners in tools/aligners/.

Two things they need:
  · split_segment_by_words  — split one whisper segment (with word-level
    timestamps) into N consecutive lyric lines, using Needleman–Wunsch
    syllable alignment to find natural word boundaries.
  · parse_lyric_lines        — read lyrics/lyrics.txt → [(section, text), …]
    skipping section markers like [Verse], [Chorus].

These are *exactly* the helpers v3 already uses, lifted out so the per-song
aligners can call them without duplicating ~80 lines apiece.
"""
from __future__ import annotations

import re
from pathlib import Path

HANGUL_RE = re.compile(r"[가-힣]")
PUNCT_RE = re.compile(r"[\s.,!?·…\-–—\"'`()\[\]]")

# Needleman–Wunsch tuning — same values as align_lyrics_v3
GAP, MISMATCH, MATCH = -2, -1, 3


def clean_hangul(s: str) -> str:
    return "".join(c for c in PUNCT_RE.sub("", s) if HANGUL_RE.match(c))


def parse_lyric_lines(path: Path) -> list[tuple[str, str]]:
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


def _nw(a: list[str], b: list[str]):
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


def seg_bounds(seg: dict) -> tuple[float, float]:
    """Word-precise (start, end) for a whisper segment.

    Whisper's segment-level start/end can drift a bit from the actual
    sung audio (especially the end), whereas the first/last *word*
    timestamps are derived from cross-attention alignment and are
    tighter. v3 uses these bounds; per-song aligners do too for
    byte-identical timings.
    """
    words = [w for w in seg.get("words", []) if w.get("word", "").strip()]
    if not words:
        return float(seg["start"]), float(seg["end"])
    return float(words[0]["start"]), float(words[-1]["end"])


def split_segment_by_words(
    words: list[dict],
    line_texts: list[str],
) -> list[tuple[float, float] | None]:
    """Split a whisper segment's words across N consecutive lyric lines.

    Returns a list of (start, end) tuples — one per lyric line — using each
    line's first-mapped-word.start and last-mapped-word.end as the bounds.
    Lines that couldn't be anchored to any word return None.
    """
    seg_chars: list[tuple[str, int]] = []  # (syllable, word_index)
    for wi, w in enumerate(words):
        for c in clean_hangul(w.get("word", "")):
            seg_chars.append((c, wi))

    lyr_chars: list[tuple[str, int]] = []  # (syllable, line_index)
    for li, t in enumerate(line_texts):
        for c in clean_hangul(t):
            lyr_chars.append((c, li))

    if not seg_chars or not lyr_chars:
        return [None] * len(line_texts)

    pairs = _nw([c for c, _ in lyr_chars], [c for c, _ in seg_chars])
    first_w: list[int | None] = [None] * len(line_texts)
    last_w:  list[int | None] = [None] * len(line_texts)
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
    for li in range(len(line_texts)):
        fw, lw = first_w[li], last_w[li]
        if fw is None or lw is None:
            out.append(None)
        else:
            out.append((float(words[fw]["start"]), float(words[lw]["end"])))
    return out


def interpolate_unassigned(
    timings: list[tuple[float, float] | None],
    total_duration: float | None = None,
) -> list[dict]:
    """Fill any None entries by linear interpolation between known anchors,
    then enforce monotonic, non-overlapping ordering. Same logic as v3's
    fill_and_enforce — identical output."""
    n = len(timings)
    out = [list(x) if x else None for x in timings]
    known = [i for i, x in enumerate(out) if x is not None]

    if not known:
        d = total_duration or 60.0
        s, e = d * 0.05, d * 0.95
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

    # monotonic + non-overlap
    for i in range(1, n):
        if out[i][0] < out[i - 1][1]:
            out[i][0] = out[i - 1][1]
        if out[i][1] <= out[i][0]:
            out[i][1] = out[i][0] + 0.3
    if total_duration is not None:
        for i in range(n):
            out[i][0] = min(out[i][0], total_duration - 0.1)
            out[i][1] = min(out[i][1], total_duration)
            if out[i][1] <= out[i][0]:
                out[i][1] = out[i][0] + 0.2

    return [{"start": round(x[0], 3), "end": round(x[1], 3)} for x in out]
