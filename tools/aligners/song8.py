#!/usr/bin/env python3
"""
Custom aligner for 반포자이즘-8 (3:03, 70 BPM, A# major, Korean Drama OST).

Slowest of the album's K-drama OSTs — 70 BPM, lots of held notes.
Whisper-on-vocal-stem packed V1 lines 1–3 into one big segment, lost
lines 4–7 (and produced one "한글자막 by 한효정" hallucination near 55s).
Chunk-transcribe at 28–65s recovered lines 4 (tail-shared with 3) + 5–8.

Recovery (chunk 28–65s):
  · "별들 아래 꿈꾸네 높은 순위 속에 날 세우고 싶어" 28.00–38.30s
       — tail of line 3 + full line 4
  · "반포야 반포야 너는 나의 별" 40.38–45.20s — line 5
  · "자이야 자이야 나를 안아줘" 47.06–51.84s — line 6
  · "상급지의 왕관 내가 쓸래" 53.28–59.62s — line 7
  · "학군지도 나를 반겨" 60.88–64.54s — line 8 (matches original seg2)

Original whisper segment layout (vocal-stem):
   0  13.40– 29.98   lines 1+2+3 packed (split needed)
   1  53.50– 58.70   "한글자막…" hallucination — SKIP
   2  61.26– 65.82   line 8 (overlaps chunk-recovered line 8)
   3  68.16– 72.66   line 9
   4  74.38– 79.50   line 10
   5  79.50– 87.24   line 11
   6  87.24– 93.76   line 12
   7  95.48–100.16   line 13
   8 102.38–107.06   line 14
   9 107.06–114.52   line 15
  10 116.20–120.80   line 16
  11 122.46–127.58   line 17
  12 129.24–134.80   line 18
  13 134.80–141.40   line 19
  14 141.40–148.70   line 20
  15 153.76–158.74   line 21
  16 160.50–165.24   line 22
  17 166.78–173.12   line 23
  18 173.12–178.92   line 24

Recovery source: timings/recovery/반포자이즘-8.v1c1.json
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

    rec = json.loads((ROOT / "timings/recovery/반포자이즘-8.v1c1.json").read_text(encoding="utf-8"))
    rec_segs = rec["segments"]
    # rec[0] = "별들 아래 꿈꾸네 높은 순위 속에 날 세우고 싶어" 28.00-38.30 = tail line 3 + line 4
    # rec[1] = "반포야 반포야 너는 나의 별" 40.38-45.20 = line 5
    # rec[2] = "자이야 자이야 나를 안아줘" 47.06-51.84 = line 6
    # rec[3] = "상급지의 왕관 내가 쓸래" 53.28-59.62 = line 7
    # rec[4] = "학군지도 나를 반겨" 60.88-64.54 = line 8

    # ── V1 lines 1+2: split from seg0 first 2/3 ──
    # seg0 (13.40-29.98) holds lines 1,2,3 — but line 3's tail is in recovery
    # rec[0]. To get clean splits: line 3 ends at where rec[0] ends transcribing
    # "꿈꾸네" word. Use combined word lists.
    seg0_words = segs[0]["words"]
    rec0_words = rec_segs[0].get("words", [])
    # Combined words covering lines 1, 2, 3 + tail of seg0 + rec0 prefix.
    # Simpler: just split seg0 into 3 (lines 1, 2, 3). Then take line 4 from
    # rec[0]'s end portion. Line 3 may straddle but split_segment_by_words
    # uses NW alignment so it'll pick a good boundary.
    v1_split = split_segment_by_words(seg0_words, [ln for _, ln in lyric_lines[0:3]])
    t[0] = v1_split[0]
    t[1] = v1_split[1]
    t[2] = v1_split[2]

    # ── Line 4: from rec[0], take after "꿈꾸네" — use word boundaries ──
    # rec[0] words contain the line-3-tail + line-4. Find the boundary.
    # Simpler: split rec[0] into 2 sub-lines (line 3, line 4) and take line 4.
    # But line 3 is mostly in seg0 already. So just take a clean "line 4" via
    # word-split with lines 3+4 as targets and pick the second.
    rec0_split = split_segment_by_words(rec0_words, [ln for _, ln in lyric_lines[2:4]])
    if rec0_split[1] is not None:
        t[3] = rec0_split[1]

    # ── C1 (lines 5–8): from recovery ──
    t[4] = (rec_segs[1]["start"], rec_segs[1]["end"])
    t[5] = (rec_segs[2]["start"], rec_segs[2]["end"])
    t[6] = (rec_segs[3]["start"], rec_segs[3]["end"])
    # line 8: prefer original seg2 (more complete text) over rec[4] (partial)
    t[7] = seg_bounds(segs[2])

    # ── V2 (lines 9–12) ──
    t[8]  = seg_bounds(segs[3])
    t[9]  = seg_bounds(segs[4])
    t[10] = seg_bounds(segs[5])
    t[11] = seg_bounds(segs[6])

    # ── C2 (lines 13–16) ──
    t[12] = seg_bounds(segs[7])
    t[13] = seg_bounds(segs[8])
    t[14] = seg_bounds(segs[9])
    t[15] = seg_bounds(segs[10])

    # ── Bridge (lines 17–20) ──
    t[16] = seg_bounds(segs[11])
    t[17] = seg_bounds(segs[12])
    t[18] = seg_bounds(segs[13])
    t[19] = seg_bounds(segs[14])

    # ── C3 (lines 21–24) ──
    t[20] = seg_bounds(segs[15])
    t[21] = seg_bounds(segs[16])
    t[22] = seg_bounds(segs[17])
    t[23] = seg_bounds(segs[18])

    return t


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: song8.py WHISPER.json LYRICS.txt OUT.json")
    whisper_p = Path(sys.argv[1])
    lyrics_p  = Path(sys.argv[2])
    out_p     = Path(sys.argv[3])

    d = json.loads(whisper_p.read_text(encoding="utf-8"))
    lyric_lines = parse_lyric_lines(lyrics_p)
    timings = build_timings(d, lyric_lines)

    last = max((e for x in timings if x for _, e in [x]), default=0.0)
    final = interpolate_unassigned(timings, total_duration=last + 1.0)

    matched = sum(1 for x in timings if x is not None)
    print(f"custom · song 8 · {matched}/24 lines matched "
          f"(V1 via seg0 word-split; line 4 + C1 from chunk recovery)")
    out_p.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}")


if __name__ == "__main__":
    main()
