#!/usr/bin/env python3
"""
Custom aligner for 반포자이즘-6 (2:29, 89 BPM, C minor, Electropop / Dark Indie Pop).

Slow track with a long synth-pad intro. Whisper-on-vocal-stem hallucinated
the first 20s as "음 음 음…", missing V1 lines 1 and 2. Targeted chunk
re-transcription recovered them.

Recovery (chunk 13–22s):
  · "나를 부르네"  13.00–14.82s — TAIL of line 1
  · "자의의 품에 안기고 싶어"  16.32–20.28s — line 2

Original whisper segment layout (vocal-stem):
   0   0.00– 20.38   "음 음 음…" 50× hallucination — SKIP
   1  20.38– 25.70   line 3
   2  25.70– 31.80   line 4
   3  31.80– 36.68   line 5
   4  36.68– 41.72   line 6
   5  41.72– 45.08   line 7
   6  45.08– 48.96   line 8
   7  53.22– 57.82   line 9
   8  57.82– 63.14   line 10
   9  63.14– 69.06   line 11
  10  69.06– 74.78   line 12
  11  74.78– 79.08   line 13
  12  79.08– 84.32   line 14
  13  84.32– 87.76   line 15
  14  87.76– 91.80   line 16
  15  92.60– 98.34   line 17
  16  98.34–103.24   line 18
  17 103.24–108.40   line 19
  18 108.40–114.40   line 20
  19 125.16–130.10   line 21
  20 130.10–134.40   line 22
  21 134.70–138.44   line 23
  22 138.44–142.52   line 24

Recovery source: timings/recovery/반포자이즘-6.v1.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from _aligner_helpers import (
    parse_lyric_lines,
    interpolate_unassigned,
    seg_bounds,
)


def build_timings(whisper_data: dict, lyric_lines: list[tuple[str, str]]):
    segs = whisper_data["segments"]
    t: list[tuple[float, float] | None] = [None] * 24

    # ── V1 line 1: recovered chunk "나를 부르네" ends at 14.82s, so line 1
    #   spans from sustained vocal start (~9.5s by peak detection on stem)
    #   to 14.82s.
    # ── V1 line 2: recovered chunk says 16.32–20.28s.
    t[0] = (9.50, 14.82)
    t[1] = (16.32, 20.38)

    # ── V1 lines 3–4 ──
    t[2] = seg_bounds(segs[1])
    t[3] = seg_bounds(segs[2])

    # ── C1 (lines 5–8) ──
    t[4] = seg_bounds(segs[3])
    t[5] = seg_bounds(segs[4])
    t[6] = seg_bounds(segs[5])
    t[7] = seg_bounds(segs[6])

    # ── V2 (lines 9–12) ──
    t[8]  = seg_bounds(segs[7])
    t[9]  = seg_bounds(segs[8])
    t[10] = seg_bounds(segs[9])
    t[11] = seg_bounds(segs[10])

    # ── C2 (lines 13–16) ──
    t[12] = seg_bounds(segs[11])
    t[13] = seg_bounds(segs[12])
    t[14] = seg_bounds(segs[13])
    t[15] = seg_bounds(segs[14])

    # ── Bridge (lines 17–20) ──
    t[16] = seg_bounds(segs[15])
    t[17] = seg_bounds(segs[16])
    t[18] = seg_bounds(segs[17])
    t[19] = seg_bounds(segs[18])

    # ── C3 (lines 21–24) ──
    t[20] = seg_bounds(segs[19])
    t[21] = seg_bounds(segs[20])
    t[22] = seg_bounds(segs[21])
    t[23] = seg_bounds(segs[22])

    return t


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: song6.py WHISPER.json LYRICS.txt OUT.json")
    whisper_p = Path(sys.argv[1])
    lyrics_p  = Path(sys.argv[2])
    out_p     = Path(sys.argv[3])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyric_lines(lyrics_p)
    timings = build_timings(d, lyric_lines)

    last = max((e for x in timings if x for _, e in [x]), default=0.0)
    final = interpolate_unassigned(timings, total_duration=last + 1.0)

    matched = sum(1 for x in timings if x is not None)
    print(f"custom · song 6 · {matched}/24 lines matched "
          f"(V1 lines 1-2 from chunk-recovered tail; lines 3-24 direct from vocal-stem whisper)")
    out_p.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
