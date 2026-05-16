#!/usr/bin/env python3
"""
Forced-alignment: whisper transcript with word timestamps + known lyrics
                 → accurate per-line timings.json.

Strategy:
  1. Flatten every recognised whisper word to (syllable, start, end) per Hangul
     syllable, distributing the word's duration uniformly across its syllables.
  2. Flatten the known lyrics to (line_idx, syllable).
  3. Use difflib.SequenceMatcher on the syllable sequences to find longest
     common subsequence matches. This handles whisper mishearings (차이/자이,
     꿈꾼/꿈꾸, 삼각지/상급지 …) gracefully — only matched syllables
     contribute to timestamps, mismatches are skipped.
  4. For each lyric line, take min(start) / max(end) of its matched syllables.
  5. Interpolate any line that ended up empty from its neighbours.
  6. Enforce monotonic, non-overlapping output.

Usage:
    align_lyrics.py WHISPER.json LYRICS.txt OUT.json
"""
from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

HANGUL_RE = re.compile(r"[가-힣]")
PUNCT_RE = re.compile(r"[\s.,!?·…\-–—\"'`()\[\]]")


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


def flatten_whisper(d: dict) -> list[tuple[str, float, float]]:
    """Per-syllable (char, start, end). Hangul only — drop ASCII noise & punctuation."""
    out: list[tuple[str, float, float]] = []
    for seg in d.get("segments", []):
        words = seg.get("words", [])
        if not words:
            # fall back to evenly-spaced syllables across the segment
            text = PUNCT_RE.sub("", seg.get("text", ""))
            text = "".join(ch for ch in text if HANGUL_RE.match(ch))
            if not text:
                continue
            s, e = float(seg["start"]), float(seg["end"])
            per = (e - s) / len(text)
            for i, ch in enumerate(text):
                out.append((ch, s + i * per, s + (i + 1) * per))
            continue
        for w in words:
            text = PUNCT_RE.sub("", w.get("word", ""))
            text = "".join(ch for ch in text if HANGUL_RE.match(ch))
            if not text:
                continue
            ws, we = float(w["start"]), float(w["end"])
            per = max((we - ws) / len(text), 0.0)
            for i, ch in enumerate(text):
                out.append((ch, ws + i * per, ws + (i + 1) * per))
    return out


def flatten_lyrics(lines: list[tuple[str, str]]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for li, (_, text) in enumerate(lines):
        clean = PUNCT_RE.sub("", text)
        for ch in clean:
            if HANGUL_RE.match(ch):
                out.append((li, ch))
    return out


def align(lyric_chars: list[tuple[int, str]],
          whisper_chars: list[tuple[str, float, float]]) -> list[int | None]:
    L = [c for _, c in lyric_chars]
    W = [c for c, _, _ in whisper_chars]
    sm = SequenceMatcher(a=L, b=W, autojunk=False)
    mapping: list[int | None] = [None] * len(L)
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            mapping[block.a + k] = block.b + k
    return mapping


def build_per_line(
    n_lines: int,
    lyric_chars: list[tuple[int, str]],
    whisper_chars: list[tuple[str, float, float]],
    mapping: list[int | None],
) -> list[list[float] | None]:
    per_line: list[list[float] | None] = [None] * n_lines
    for i, (line_idx, _) in enumerate(lyric_chars):
        wi = mapping[i]
        if wi is None:
            continue
        _, ws, we = whisper_chars[wi]
        if per_line[line_idx] is None:
            per_line[line_idx] = [ws, we]
        else:
            per_line[line_idx][0] = min(per_line[line_idx][0], ws)
            per_line[line_idx][1] = max(per_line[line_idx][1], we)
    return per_line


def fill_gaps_and_monotonic(
    per_line: list[list[float] | None],
    total_duration: float,
) -> list[dict]:
    n = len(per_line)
    # 1. fill None entries by interpolation between nearest non-None neighbours
    out = [list(x) if x else None for x in per_line]
    # forward fill known anchors
    anchors_idx = [i for i, x in enumerate(out) if x is not None]
    if not anchors_idx:
        # nothing matched — fall back to even distribution over [5%, 95%]
        s = total_duration * 0.05
        e = total_duration * 0.95
        per = (e - s) / n
        return [
            {"start": round(s + i * per, 3), "end": round(s + (i + 1) * per, 3)}
            for i in range(n)
        ]

    # extrapolate the head
    if anchors_idx[0] > 0:
        first = out[anchors_idx[0]]
        # assume each missing line ~= duration of the first known line
        approx = max(0.5, first[1] - first[0])
        for k in range(anchors_idx[0] - 1, -1, -1):
            out[k] = [max(0.0, first[0] - (anchors_idx[0] - k) * approx),
                      max(0.0, first[0] - (anchors_idx[0] - k - 1) * approx)]
    # extrapolate the tail
    if anchors_idx[-1] < n - 1:
        last = out[anchors_idx[-1]]
        approx = max(0.5, last[1] - last[0])
        for k in range(anchors_idx[-1] + 1, n):
            offset = k - anchors_idx[-1]
            out[k] = [last[1] + (offset - 1) * approx,
                      last[1] + offset * approx]
    # interpolate gaps between two known anchors
    for a, b in zip(anchors_idx, anchors_idx[1:]):
        if b - a == 1:
            continue
        s = out[a][1]
        e = out[b][0]
        per = (e - s) / (b - a)
        for k in range(a + 1, b):
            out[k] = [s + (k - a - 1) * per, s + (k - a) * per]

    # 2. enforce monotonic and no overlap (but allow gaps — that's good for us)
    for i in range(1, n):
        if out[i][0] < out[i - 1][1]:
            out[i][0] = out[i - 1][1]
        if out[i][1] <= out[i][0]:
            out[i][1] = out[i][0] + 0.3

    # 3. clamp to song duration
    for i in range(n):
        out[i][0] = min(out[i][0], total_duration - 0.1)
        out[i][1] = min(out[i][1], total_duration)
        if out[i][1] <= out[i][0]:
            out[i][1] = out[i][0] + 0.2

    return [{"start": round(x[0], 3), "end": round(x[1], 3)} for x in out]


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    whisper_p = Path(sys.argv[1])
    lyrics_p = Path(sys.argv[2])
    out_p = Path(sys.argv[3])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyrics(lyrics_p)

    lyric_chars = flatten_lyrics(lyric_lines)
    whisper_chars = flatten_whisper(d)
    if not whisper_chars:
        sys.exit("no hangul recognised in whisper output")

    # song duration: last whisper char end, but drop hallucinated tail by
    # clipping anything after a 6+ second gap from the next-to-last line
    mapping = align(lyric_chars, whisper_chars)
    per_line_raw = build_per_line(len(lyric_lines), lyric_chars, whisper_chars, mapping)
    # if a line matched but its end exceeds the next line's start due to
    # noise, that gets cleaned in fill_gaps_and_monotonic. derive duration
    # robustly from matched anchors instead of the noisy tail.
    last_anchor_end = max(
        (x[1] for x in per_line_raw if x is not None), default=0.0
    )
    total_duration = last_anchor_end + 1.0

    timings = fill_gaps_and_monotonic(per_line_raw, total_duration)

    matched = sum(1 for x in per_line_raw if x is not None)
    print(f"matched {matched}/{len(lyric_lines)} lyric lines from whisper output")
    out_p.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
