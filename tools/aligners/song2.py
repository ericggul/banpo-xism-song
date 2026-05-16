#!/usr/bin/env python3
"""
Custom aligner for 반포자이즘-2 (2:45, 152 BPM, D major, Alternative / dream-pop / sadcore ballad).

Whisper layout for this track has three quirks:

  1. seg2 (12.46–24.46s) crams Verse 1 lines 3+4 into one segment. Word-level
     NW split required.
  2. seg12 (82.18–85.74s) transcribed as "반포야 너는 나의 별" but is actually
     line 14 ("자이야 자이야 나를 안아줘") — whisper misheard "자이야" as
     "반포야". The time slot is correct, just trust it for line 14.
  3. seg15 (99.60–101.00s, only 1.4s) is a hallucinated early echo of line 18
     ("반포의 꿈이 나를 깨우네"). The real line 18 is seg17 (105.98–111.56s).
     Skip seg15.
  4. seg24–27 are outro hallucinations ("하꾼지", empty, "감사합니다"). Skip.

Whisper segment layout (24 real + 4 outro hallucinations):
   0   0.00–  5.08   line 1
   1   6.36– 11.38   line 2
   2  12.46– 24.46   Verse 1 lines 3+4 (split needed)
   3  24.46– 29.56   line 5
   4  31.38– 35.36   line 6
   5  36.60– 41.86   line 7
   6  43.30– 48.06   line 8
   7  50.42– 55.64   line 9
   8  56.66– 61.74   line 10
   9  63.16– 67.74   line 11
  10  68.84– 74.02   line 12
  11  75.60– 79.68   line 13
  12  82.18– 85.74   line 14 (whisper misheard 자이야→반포야 — trust the time slot)
  13  87.12– 91.68   line 15
  14  93.86– 97.68   line 16
  15  99.60–101.00   echo hallucination — SKIP
  16 101.00–105.98   line 17
  17 105.98–111.56   line 18
  18 113.38–117.68   line 19
  19 118.68–125.48   line 20
  20 125.48–130.36   line 21
  21 132.44–136.40   line 22
  22 137.48–142.86   line 23
  23 143.48–149.12   line 24
  24+ outro hallucinations — SKIP
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

    # ── Verse 1 (lines 1–4) ──
    t[0] = seg_bounds(segs[0])
    t[1] = seg_bounds(segs[1])
    # seg2 contains lines 3+4 — split by words
    v1_tail = split_segment_by_words(segs[2]["words"], [ln for _, ln in lyric_lines[2:4]])
    t[2] = v1_tail[0]
    t[3] = v1_tail[1]

    # ── Chorus 1 (lines 5–8) ──
    t[4] = seg_bounds(segs[3])
    t[5] = seg_bounds(segs[4])
    t[6] = seg_bounds(segs[5])
    t[7] = seg_bounds(segs[6])

    # ── Verse 2 (lines 9–12) ──
    t[8]  = seg_bounds(segs[7])
    t[9]  = seg_bounds(segs[8])
    t[10] = seg_bounds(segs[9])
    t[11] = seg_bounds(segs[10])

    # ── Chorus 2 (lines 13–16) ──
    t[12] = seg_bounds(segs[11])
    # seg12 misheard but time slot is correct for line 14
    t[13] = seg_bounds(segs[12])
    t[14] = seg_bounds(segs[13])
    t[15] = seg_bounds(segs[14])

    # seg15 is a hallucinated echo of line 18 — skip

    # ── Bridge (lines 17–20) ──
    t[16] = seg_bounds(segs[16])
    t[17] = seg_bounds(segs[17])
    t[18] = seg_bounds(segs[18])
    t[19] = seg_bounds(segs[19])

    # ── Chorus 3 (lines 21–24) ──
    t[20] = seg_bounds(segs[20])
    t[21] = seg_bounds(segs[21])
    t[22] = seg_bounds(segs[22])
    t[23] = seg_bounds(segs[23])

    # seg24+ are outro hallucinations — ignored automatically (not referenced)

    return t


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: song2.py WHISPER.json LYRICS.txt OUT.json")
    whisper_p = Path(sys.argv[1])
    lyrics_p  = Path(sys.argv[2])
    out_p     = Path(sys.argv[3])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyric_lines(lyrics_p)
    timings = build_timings(d, lyric_lines)

    last = max((e for x in timings if x for _, e in [x]), default=0.0)
    final = interpolate_unassigned(timings, total_duration=last + 1.0)

    matched = sum(1 for x in timings if x is not None)
    print(f"custom · song 2 · {matched}/24 lines matched (seg15 dup + outro hallucinations skipped)")
    out_p.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
