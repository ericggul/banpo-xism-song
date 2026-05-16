#!/usr/bin/env python3
"""
Custom aligner for 반포자이즘-3 (2:06, 129 BPM, F# major, 2025 house × electronic hip-hop).

Fast dense track — whisper crams 4–7 lyric lines into each segment, drops
lines 12, 21, 22 entirely, and produces an "ActAct…" hallucination.

  · seg0 (15.90–29.98): Verse 1 lines 1–4 → split.
  · seg1 (30.00–57.30): Chorus 1 (lines 5–8) + Verse 2 lines 9–11 = 7 lines
                       → split. Line 12 ("자이의 문턱 넘고 싶어") is dropped
                       by whisper entirely; interpolate.
  · seg2 (60.84–75.62): Chorus 2 (lines 13–16) → split.
  · seg3 (75.62–83.56): Bridge lines 17–18 → split.
  · seg4 (84.12–91.24): Bridge lines 19–20 → split.
  · seg5 (115.22–116.62): "ActActAct…" hallucination — SKIP.
  · seg6 (116.62–118.80): Chorus 3 line 23 (partial — whisper missed lines
                          21, 22). Interpolate lines 21, 22 in the gap
                          between line 20 end (91.24s) and line 23 start
                          (116.62s) — that's a 25-second instrumental drop
                          before the final chorus.
  · seg7 (118.80–122.46): Chorus 3 line 24.

Whisper segment layout:
   0  15.90– 29.98   Verse 1 (lines 1–4)         [split]
   1  30.00– 57.30   Chorus 1 + V2 1–3 (5–11)    [split, 7 lines]
   2  60.84– 75.62   Chorus 2 (lines 13–16)      [split]
   3  75.62– 83.56   Bridge lines 17–18          [split]
   4  84.12– 91.24   Bridge lines 19–20          [split]
   5 115.22–116.62   "ActAct…" hallucination     SKIP
   6 116.62–118.80   Chorus 3 line 23
   7 118.80–122.46   Chorus 3 line 24

Skipped lyrics (interpolated by linear fill):
  · line 12  (between seg1 end 57.30s and seg2 start 60.84s)
  · lines 21, 22  (between seg4 end 91.24s and seg6 start 116.62s)
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

    # ── Verse 1 (lines 1–4): split seg0 ──
    v1 = split_segment_by_words(segs[0]["words"], [ln for _, ln in lyric_lines[0:4]])
    for i in range(4):
        t[i] = v1[i]

    # ── Chorus 1 + Verse 2 lines 1–3 (lines 5–11): split seg1 ──
    big = split_segment_by_words(segs[1]["words"], [ln for _, ln in lyric_lines[4:11]])
    for i in range(7):
        t[4 + i] = big[i]

    # line 12 ("자이의 문턱 넘고 싶어") — not in whisper output, interpolate

    # ── Chorus 2 (lines 13–16): split seg2 ──
    c2 = split_segment_by_words(segs[2]["words"], [ln for _, ln in lyric_lines[12:16]])
    for i in range(4):
        t[12 + i] = c2[i]

    # ── Bridge lines 17–18: split seg3 ──
    b1 = split_segment_by_words(segs[3]["words"], [ln for _, ln in lyric_lines[16:18]])
    t[16] = b1[0]
    t[17] = b1[1]

    # ── Bridge lines 19–20: split seg4 ──
    b2 = split_segment_by_words(segs[4]["words"], [ln for _, ln in lyric_lines[18:20]])
    t[18] = b2[0]
    t[19] = b2[1]

    # seg5 "ActAct…" hallucination — skip

    # lines 21, 22 — whisper missed entirely, interpolate

    # ── Chorus 3 tail (lines 23–24) ──
    t[22] = seg_bounds(segs[6])
    t[23] = seg_bounds(segs[7])

    return t


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: song3.py WHISPER.json LYRICS.txt OUT.json")
    whisper_p = Path(sys.argv[1])
    lyrics_p  = Path(sys.argv[2])
    out_p     = Path(sys.argv[3])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyric_lines(lyrics_p)
    timings = build_timings(d, lyric_lines)

    last = max((e for x in timings if x for _, e in [x]), default=0.0)
    final = interpolate_unassigned(timings, total_duration=last + 1.0)

    matched = sum(1 for x in timings if x is not None)
    print(f"custom · song 3 · {matched}/24 lines matched (lines 12, 21, 22 interpolated; seg5 hallucination skipped)")
    out_p.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
