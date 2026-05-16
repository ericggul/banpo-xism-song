#!/usr/bin/env python3
"""
Custom aligner for 반포자이즘-1 (2:33, 136 BPM, D# major, K-Pop synth-pop — reference cover).

Whisper was nearly perfect on this track. The only quirks:

  · seg0 (14.18–29.28s) crams all 4 Verse 1 lines into one segment because
    whisper didn't split between lines. → Word-level NW split into 4 lines.
  · seg5 (64.38–65.62s) = "한 번 더 해봅시다", a vocal ad-lib not in the
    canonical lyrics. → Skip.
  · Every other whisper segment maps 1:1 with one lyric line.

Whisper segment layout:
   0  14.18– 29.28   Verse 1 lines 1–4 (split needed)
   1  32.50– 36.56   line 5
   2  36.56– 40.00   line 6
   3  40.00– 43.98   line 7
   4  43.98– 48.84   line 8
   5  64.38– 65.62   ad-lib "한 번 더 해봅시다" — SKIP
   6  65.62– 68.50   line 9
   7  68.50– 72.06   line 10
   8  72.06– 75.54   line 11
   9  75.54– 79.66   line 12
  10  82.82– 86.44   line 13
  11  86.44– 90.00   line 14
  12  90.00– 94.12   line 15
  13  94.12– 99.00   line 16
  14 100.44–104.18   line 17
  15 104.18–107.82   line 18
  16 107.82–111.30   line 19
  17 111.30–115.16   line 20
  18 115.16–118.70   line 21
  19 118.70–122.50   line 22
  20 122.50–126.38   line 23
  21 126.38–131.20   line 24
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

    # ── Verse 1 (lines 1–4): split seg0 by words ──
    v1 = split_segment_by_words(segs[0]["words"], [ln for _, ln in lyric_lines[0:4]])
    for i in range(4):
        t[i] = v1[i]

    # ── Chorus 1 (lines 5–8) ──
    t[4] = seg_bounds(segs[1])
    t[5] = seg_bounds(segs[2])
    t[6] = seg_bounds(segs[3])
    t[7] = seg_bounds(segs[4])

    # seg5 "한 번 더 해봅시다" — ad-lib, skip

    # ── Verse 2 (lines 9–12) ──
    t[8]  = seg_bounds(segs[6])
    t[9]  = seg_bounds(segs[7])
    t[10] = seg_bounds(segs[8])
    t[11] = seg_bounds(segs[9])

    # ── Chorus 2 (lines 13–16) ──
    t[12] = seg_bounds(segs[10])
    t[13] = seg_bounds(segs[11])
    t[14] = seg_bounds(segs[12])
    t[15] = seg_bounds(segs[13])

    # ── Bridge (lines 17–20) ──
    t[16] = seg_bounds(segs[14])
    t[17] = seg_bounds(segs[15])
    t[18] = seg_bounds(segs[16])
    t[19] = seg_bounds(segs[17])

    # ── Chorus 3 (lines 21–24) ──
    t[20] = seg_bounds(segs[18])
    t[21] = seg_bounds(segs[19])
    t[22] = seg_bounds(segs[20])
    t[23] = seg_bounds(segs[21])

    return t


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: song1.py WHISPER.json LYRICS.txt OUT.json")
    whisper_p = Path(sys.argv[1])
    lyrics_p  = Path(sys.argv[2])
    out_p     = Path(sys.argv[3])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyric_lines(lyrics_p)
    timings = build_timings(d, lyric_lines)

    last = max((e for x in timings if x for _, e in [x]), default=0.0)
    final = interpolate_unassigned(timings, total_duration=last + 1.0)

    matched = sum(1 for x in timings if x is not None)
    print(f"custom · song 1 · {matched}/24 lines matched (seg5 ad-lib skipped)")
    out_p.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
