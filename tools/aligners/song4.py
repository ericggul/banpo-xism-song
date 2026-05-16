#!/usr/bin/env python3
"""
Custom aligner for 반포자이즘-4 (1:55, 92 BPM, E minor, K-Pop synth-driven minor variant).

Original whisper transcription of the bare mp3 hallucinated 24+ seconds of
"마 마 마…" instead of the actual sung Verse 1 — the synth-pop production
on this track confuses whisper-large-v3-turbo. Solution: run Demucs vocal
separation first (htdemucs vocals stem) and transcribe the clean vocal
stem. With the stem isolated, whisper recovers the entire lyric track.

Segment layout (from Demucs+whisper, all 24 lines actually transcribed):

   0   3.32– 4.72   "나나나…"  backing-vocal artifact — SKIP
   1   4.72– 5.56   "나나나…"                          — SKIP
   2   7.40– 8.80   "나나나…"                          — SKIP
   3   8.80–14.14   Verse 1 lines 1+2  ← split
   4  14.14–21.62   Verse 1 lines 3+4  ← split
   5  21.62–28.62   Chorus 1 lines 5+6 ← split
   6  28.62–32.18   line 7
   7  32.18–36.40   line 8
   8  38.90–42.22   line 9
   9  42.22–44.92   line 10
  10  44.92–49.72   line 11
  11  49.72–53.22   line 12
  12  54.62–58.26   line 13
  13  58.26–61.32   line 14
  14  61.32–64.74   line 15
  15  64.74–68.56   line 16
  16  68.56–72.04   line 17 (Bridge)
  17  72.04–75.06   line 18
  18  75.06–78.86   line 19
  19  78.86–85.86   line 20 (whisper merged "내 미래를 이곳에" + "맡기고 싶어")
  20  90.66–94.72   "내가 느끼고 싶어"  hallucinated echo — SKIP
  21  97.50–101.16  "내가 느끼고 싶어"  hallucinated echo — SKIP
  22 101.16–104.56  line 21 (Chorus 3)
  23 104.56–107.64  line 22
  24 107.64–111.04  line 23
  25 111.04–115.20  line 24
  26 115.20–115.54  "감사합니다" hallucination — SKIP
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


def build_timings(whisper_data: dict, lyric_lines: list[tuple[str, str]]):
    segs = whisper_data["segments"]
    t: list[tuple[float, float] | None] = [None] * 24

    # ── Verse 1 lines 1+2 from seg3 ──
    v1a = split_segment_by_words(segs[3]["words"], [ln for _, ln in lyric_lines[0:2]])
    t[0] = v1a[0]; t[1] = v1a[1]
    # ── Verse 1 lines 3+4 from seg4 ──
    v1b = split_segment_by_words(segs[4]["words"], [ln for _, ln in lyric_lines[2:4]])
    t[2] = v1b[0]; t[3] = v1b[1]
    # ── Chorus 1 lines 5+6 from seg5 ──
    c1a = split_segment_by_words(segs[5]["words"], [ln for _, ln in lyric_lines[4:6]])
    t[4] = c1a[0]; t[5] = c1a[1]
    # ── Chorus 1 lines 7+8 ──
    t[6] = seg_bounds(segs[6])
    t[7] = seg_bounds(segs[7])

    # ── Verse 2 (lines 9–12) ──
    t[8]  = seg_bounds(segs[8])
    t[9]  = seg_bounds(segs[9])
    t[10] = seg_bounds(segs[10])
    t[11] = seg_bounds(segs[11])

    # ── Chorus 2 (lines 13–16) ──
    t[12] = seg_bounds(segs[12])
    t[13] = seg_bounds(segs[13])
    t[14] = seg_bounds(segs[14])
    t[15] = seg_bounds(segs[15])

    # ── Bridge (lines 17–20) ──
    t[16] = seg_bounds(segs[16])
    t[17] = seg_bounds(segs[17])
    t[18] = seg_bounds(segs[18])
    t[19] = seg_bounds(segs[19])

    # segs 20, 21 = hallucinated "내가 느끼고 싶어" echoes — skipped

    # ── Chorus 3 (lines 21–24) ──
    t[20] = seg_bounds(segs[22])
    t[21] = seg_bounds(segs[23])
    t[22] = seg_bounds(segs[24])
    t[23] = seg_bounds(segs[25])

    return t


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: song4.py WHISPER.json LYRICS.txt OUT.json")
    whisper_p = Path(sys.argv[1])
    lyrics_p  = Path(sys.argv[2])
    out_p     = Path(sys.argv[3])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyric_lines(lyrics_p)
    timings = build_timings(d, lyric_lines)

    last = max((e for x in timings if x for _, e in [x]), default=0.0)
    final = interpolate_unassigned(timings, total_duration=last + 1.0)

    matched = sum(1 for x in timings if x is not None)
    print(f"custom · song 4 · {matched}/24 lines matched "
          f"(via demucs vocal stem; 3 backing-vocal + 2 hallucinated-echo segments skipped)")
    out_p.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
