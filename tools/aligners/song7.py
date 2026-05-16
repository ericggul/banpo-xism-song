#!/usr/bin/env python3
"""
Custom aligner for 반포자이즘-7 (4:06, 129 BPM, F# minor, 2020s Progressive House).

Longest track on the album. Whisper on the vocal stem got most of the song
but produced two failure modes:
  · 89.30–93.08: hallucinated "한글자막 by 한효정" (a frequent whisper
    artifact when it hears unclear Korean speech — substitutes a known
    subtitle credit phrase). Skipped.
  · V2 lines 9–11 missing between seg7 (line 8, ends 66.30s) and seg9
    (line 12, starts 110.64s). Targeted chunk transcribe (87–116s) on
    the vocal stem recovered them at 89.12–115.34s.
  · ~210s ad-lib "아 아 아 아 아 아" repeats (segs 15–25) — vocal sustain
    fills, not lyric content. Skipped.
  · C3 line 21 split awkwardly across segs 26+27+28; merge.

Original whisper segment layout (vocal-stem, abridged):
   0  16.00– 20.46   line 1
   1  22.44– 27.78   line 2
   2  30.66– 34.90   line 3
   3  36.52– 42.58   line 4
   4  44.86– 49.52   line 5
   5  52.10– 56.88   line 6
   6  59.04– 62.58   line 7
   7  62.58– 66.30   line 8
   8  89.30– 93.08   "한글자막…" hallucination — SKIP
   9 110.64–116.82   line 12
  10 116.82–122.88   line 13
  11 125.40–130.18   line 14
  12 132.30–135.80   line 15
  13 135.80–139.40   line 16
  14 161.10–178.48   lines 17+18+19+20 packed (split needed)
  15–25 ~201–211s    "아 아 아 …" sustain ad-libs — SKIP
  26 212.92–214.32   line 21 start (반포야)
  27 214.32–216.18   line 21 mid (반포야)
  28 216.18–218.02   line 21 end (너는 나의 변)
  29 220.68–225.44   line 22
  30 227.58–231.20   line 23
  31 231.20–234.82   line 24

Recovery sources:
  · timings/recovery/반포자이즘-7.v2.json  (V2 lines 9–12 word-level)
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

    # ── V1 + C1 (lines 1–8) ──
    for i in range(8):
        t[i] = seg_bounds(segs[i])

    # ── V2 (lines 9–12): chunk-recovered ──
    rec = json.loads((ROOT / "timings/recovery/반포자이즘-7.v2.json").read_text(encoding="utf-8"))
    # rec has 2 segments containing lines 9+10 (89.12–100.68) and 11+12 (103.62–115.34).
    rec_words_9_10 = [w for w in rec["segments"][0].get("words", [])]
    rec_words_11_12 = [w for w in rec["segments"][1].get("words", [])]
    v2a = split_segment_by_words(rec_words_9_10, [ln for _, ln in lyric_lines[8:10]])
    v2b = split_segment_by_words(rec_words_11_12, [ln for _, ln in lyric_lines[10:12]])
    t[8] = v2a[0]; t[9] = v2a[1]
    t[10] = v2b[0]; t[11] = v2b[1]

    # ── C2 (lines 13–16): seg 10–13 ──
    t[12] = seg_bounds(segs[10])
    t[13] = seg_bounds(segs[11])
    t[14] = seg_bounds(segs[12])
    t[15] = seg_bounds(segs[13])

    # ── Bridge (lines 17–20): seg 14 (one big segment, all 4 lines, split) ──
    bridge = split_segment_by_words(segs[14]["words"], [ln for _, ln in lyric_lines[16:20]])
    for i in range(4):
        t[16 + i] = bridge[i]

    # segs 15–25 are sustain ad-libs — SKIP

    # ── C3 (lines 21–24) ──
    # Line 21 "반포야 반포야 너는 나의 별" is split across segs 26, 27, 28.
    # Merge their words for a clean line bound.
    c3_l21_words = segs[26]["words"] + segs[27]["words"] + segs[28]["words"]
    if c3_l21_words:
        t[20] = (float(c3_l21_words[0]["start"]), float(c3_l21_words[-1]["end"]))
    t[21] = seg_bounds(segs[29])
    t[22] = seg_bounds(segs[30])
    t[23] = seg_bounds(segs[31])

    return t


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: song7.py WHISPER.json LYRICS.txt OUT.json")
    whisper_p = Path(sys.argv[1])
    lyrics_p  = Path(sys.argv[2])
    out_p     = Path(sys.argv[3])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyric_lines(lyrics_p)
    timings = build_timings(d, lyric_lines)

    last = max((e for x in timings if x for _, e in [x]), default=0.0)
    final = interpolate_unassigned(timings, total_duration=last + 1.0)

    matched = sum(1 for x in timings if x is not None)
    print(f"custom · song 7 · {matched}/24 lines matched "
          f"(V2 from chunk recovery; Bridge from word-split; C3 line 21 merged from 3 segments)")
    out_p.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
