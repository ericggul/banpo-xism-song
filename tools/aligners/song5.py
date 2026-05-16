#!/usr/bin/env python3
"""
Custom aligner for 반포자이즘-5 (1:19, 99 BPM, E minor, 90s East Coast Hip-Hop).

Fast dense hip-hop track. All 24 lines are sung but Demucs+whisper on the
vocal stem only transcribed the second half cleanly. The first 30s
(V1 + C1) required chunked re-transcription with line-targeted prompts
to recover.

Recovery (chunk-transcribed segments saved in timings/recovery/):
  · V1 lines 1+2 captured: vocal text "나를 부르는 자의 품에 넘기고 싶어"
    at 10.74–14.16s — that's the *tail* of line 1 + line 2.
  · V1 lines 3+4 captured: "강남의 별들 아래 꿈꾸네 높은 순위 속에 날
    세우고 싶어" at 14.78–18.98s with word-level timestamps.
  · C1 lines 5–8 captured: full chorus packed into 18.60–29.22s with
    word-level timings.
  · Lines 9–24 come directly from the original Demucs+whisper segments.

Original whisper segment layout (vocal-stem):
   0   28.58– 29.98   "후우" non-lyric exclamation — SKIP
   1   30.00– 31.62   line 9
   2   31.62– 34.08   line 10
   3   34.08– 36.66   line 11
   4   36.66– 39.46   line 12
   5   39.46– 41.94   line 13
   6   41.94– 44.00   line 14
   7   44.00– 46.62   line 15
   8   46.62– 48.88   line 16
   9   48.88– 53.96   line 17
  10   53.96– 56.88   line 18
  11   58.82– 63.04   line 19
  12   63.04– 68.10   line 20
  13   68.10– 71.84   line 21 (+ start of line 22)
  14   71.84– 75.98   end of line 22 + line 23
  15   75.98– 78.30   line 24

Recovery sources used:
  · timings/recovery/반포자이즘-5.c1.json  (lines 5–8, word-level)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from _aligner_helpers import (
    parse_lyric_lines,
    split_segment_by_words,
    interpolate_unassigned,
    seg_bounds,
)

# Manually-determined V1 boundaries from chunk-transcribed vocal stem.
# Line 1 start (~7.5s) is anchored to where sustained vocal energy begins
# in the demucs vocal stem; line 1 end at 10.74s is where whisper first
# resolved actual phonemes for the V1 chunk transcribe.
V1_TIMINGS = [
    (7.50, 10.74),   # 1: 반포의 빛이 나를 부르네
    (10.74, 14.16),  # 2: 자이의 품에 안기고 싶어
    (14.78, 16.76),  # 3: 강남의 별들 아래 꿈꾸네  (word-level from chunk)
    (16.76, 18.60),  # 4: 높은 순위 속에 날 세우고 싶어 (word-level from chunk)
]


def build_timings(whisper_data: dict, lyric_lines: list[tuple[str, str]]):
    segs = whisper_data["segments"]
    t: list[tuple[float, float] | None] = [None] * 24

    # ── V1 (lines 1–4): from chunk-recovered timings ──
    for i, tt in enumerate(V1_TIMINGS):
        t[i] = tt

    # ── C1 (lines 5–8): recovered chunk, word-level split ──
    rec = json.loads((ROOT / "timings/recovery/반포자이즘-5.c1.json").read_text(encoding="utf-8"))
    c1_words = [w for seg in rec["segments"] for w in seg.get("words", [])]
    c1 = split_segment_by_words(c1_words, [ln for _, ln in lyric_lines[4:8]])
    for i in range(4):
        t[4 + i] = c1[i]

    # ── V2 (lines 9–12) ──
    t[8]  = seg_bounds(segs[1])
    t[9]  = seg_bounds(segs[2])
    t[10] = seg_bounds(segs[3])
    t[11] = seg_bounds(segs[4])

    # ── C2 (lines 13–16) ──
    t[12] = seg_bounds(segs[5])
    t[13] = seg_bounds(segs[6])
    t[14] = seg_bounds(segs[7])
    t[15] = seg_bounds(segs[8])

    # ── Bridge (lines 17–20) ──
    t[16] = seg_bounds(segs[9])
    t[17] = seg_bounds(segs[10])
    t[18] = seg_bounds(segs[11])
    t[19] = seg_bounds(segs[12])

    # ── C3 (lines 21–24): segs 13+14 cross line boundaries; merge their
    #    words and word-split into 3 lines (21, 22, 23). seg15 = line 24.
    c3_words = segs[13]["words"] + segs[14]["words"]
    c3 = split_segment_by_words(c3_words, [ln for _, ln in lyric_lines[20:23]])
    t[20] = c3[0]; t[21] = c3[1]; t[22] = c3[2]
    t[23] = seg_bounds(segs[15])

    return t


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: song5.py WHISPER.json LYRICS.txt OUT.json")
    whisper_p = Path(sys.argv[1])
    lyrics_p  = Path(sys.argv[2])
    out_p     = Path(sys.argv[3])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyric_lines(lyrics_p)
    timings = build_timings(d, lyric_lines)

    last = max((e for x in timings if x for _, e in [x]), default=0.0)
    final = interpolate_unassigned(timings, total_duration=last + 1.0)

    matched = sum(1 for x in timings if x is not None)
    print(f"custom · song 5 · {matched}/24 lines matched "
          f"(V1 from chunk-recovered word-level; C1 from chunk; C3 from word-split)")
    out_p.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
