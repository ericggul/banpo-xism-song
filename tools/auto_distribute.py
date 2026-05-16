#!/usr/bin/env python3
"""
Generate timings.json for a song using:
  1. RMS energy curve in the vocal band (200–3500 Hz) at 0.5s windows
  2. Smoothed → threshold = peak - 8 dB
  3. intro_end = first sustained crossing above threshold
     outro_start = last sustained crossing above threshold
  4. Distribute lyric lines evenly across [intro_end, outro_start]
  5. Insert a ~1.5s blank gap between *lyric sections* (so the subtitle
     disappears during obvious instrumental transitions).

It's still a starting point — refine with tools/tap_timing.html.

Usage:
    auto_distribute.py AUDIO.mp3 LYRICS.txt OUT.json [--gap SECONDS]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


WINDOW_S = 0.5
SECTION_GAP_S = 1.5  # blank period between sections (no subtitle on screen)
SUSTAIN_S = 1.5      # min duration above threshold to count as "vocals started"
THRESHOLD_DB_BELOW_PEAK = 8.0


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    return float(out.strip())


def energy_curve(audio: Path, window_s: float = WINDOW_S) -> tuple[list[float], list[float]]:
    """Return (times, rms_db) at `window_s` resolution in the vocal band."""
    n = int(44100 * window_s)
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats",
            "-i", str(audio),
            "-af",
            f"aresample=44100,pan=mono|c0=0.5*c0+0.5*c1,"
            f"highpass=f=200,lowpass=f=3500,"
            f"asetnsamples={n}:p=0,"
            f"astats=metadata=1:reset=1,"
            f"ametadata=print:key=lavfi.astats.Overall.RMS_level",
            "-f", "null", "-",
        ],
        capture_output=True, text=True,
    )
    times: list[float] = []
    rms: list[float] = []
    cur_t: float | None = None
    for line in proc.stderr.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            cur_t = float(m.group(1))
            continue
        m = re.search(r"RMS_level=(-?[\d.]+|-inf|nan)", line)
        if m and cur_t is not None:
            v = m.group(1)
            try:
                rms.append(float(v))
            except ValueError:
                rms.append(-120.0)
            times.append(cur_t)
            cur_t = None
    return times, rms


def smooth(xs: list[float], k: int = 3) -> list[float]:
    if not xs:
        return xs
    out = []
    half = k // 2
    for i in range(len(xs)):
        lo = max(0, i - half)
        hi = min(len(xs), i + half + 1)
        out.append(sum(xs[lo:hi]) / (hi - lo))
    return out


def find_vocal_window(
    times: list[float],
    rms: list[float],
    total: float,
) -> tuple[float, float]:
    if not rms:
        return 0.0, total
    rms_s = smooth(rms, 3)
    peak = max(rms_s)
    threshold = peak - THRESHOLD_DB_BELOW_PEAK
    sustain_n = max(1, int(SUSTAIN_S / WINDOW_S))

    intro_end = None
    for i in range(len(rms_s) - sustain_n + 1):
        if all(rms_s[j] > threshold for j in range(i, i + sustain_n)):
            intro_end = times[i]
            break
    if intro_end is None:
        intro_end = 0.0

    outro_start = None
    for i in range(len(rms_s) - sustain_n, -1, -1):
        if all(rms_s[j] > threshold for j in range(i, i + sustain_n)):
            outro_start = times[i + sustain_n - 1] + WINDOW_S
            break
    if outro_start is None:
        outro_start = total

    # tiny safety margin so vocals aren't clipped
    intro_end = max(0.0, intro_end - 0.15)
    outro_start = min(total, outro_start + 0.25)
    return intro_end, outro_start


def parse_lyrics(path: Path) -> list[tuple[str, str]]:
    """Return [(section_name, line_text), ...] for *lyric* lines only."""
    lines: list[tuple[str, str]] = []
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
        lines.append((section, s))
    return lines


def distribute(
    intro_end: float,
    outro_start: float,
    sections: list[list[int]],  # list of section-line-indices
    gap_s: float = SECTION_GAP_S,
) -> list[dict]:
    """
    Allocate vocal time across sections proportionally to # of lines,
    leaving `gap_s` blank between sections (subtitle off-screen).
    """
    total_lines = sum(len(s) for s in sections)
    n_gaps = max(0, len(sections) - 1)
    available = (outro_start - intro_end) - n_gaps * gap_s
    if available <= 0:
        # song too short for the gap scheme — fall back to no gaps
        gap_s = 0.0
        available = outro_start - intro_end

    per_line = available / total_lines
    timings: list[dict | None] = [None] * total_lines
    cursor = intro_end
    for s_i, sec in enumerate(sections):
        for idx in sec:
            start = cursor
            end = cursor + per_line
            timings[idx] = {"start": round(start, 3), "end": round(end, 3)}
            cursor = end
        if s_i < len(sections) - 1:
            cursor += gap_s  # blank gap before next section
    return timings  # type: ignore


def main() -> None:
    args = sys.argv[1:]
    gap = SECTION_GAP_S
    if "--gap" in args:
        i = args.index("--gap")
        gap = float(args[i + 1])
        del args[i:i + 2]
    if len(args) != 3:
        sys.exit(__doc__)

    audio = Path(args[0])
    lyrics_p = Path(args[1])
    out = Path(args[2])

    total = ffprobe_duration(audio)
    times, rms = energy_curve(audio)
    intro_end, outro_start = find_vocal_window(times, rms, total)
    print(
        f"duration {total:.2f}s · "
        f"intro_end {intro_end:.2f}s · outro_start {outro_start:.2f}s · "
        f"vocal {outro_start - intro_end:.2f}s"
    )

    lyric_lines = parse_lyrics(lyrics_p)
    if not lyric_lines:
        sys.exit("no lyric lines parsed")

    # group line-indices by section
    sections: list[list[int]] = []
    cur_section = None
    for i, (sec, _) in enumerate(lyric_lines):
        if sec != cur_section:
            sections.append([])
            cur_section = sec
        sections[-1].append(i)

    timings = distribute(intro_end, outro_start, sections, gap_s=gap)
    out.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"wrote {out} · {len(timings)} lines · "
        f"{len(sections)} sections · gap {gap:.2f}s"
    )


if __name__ == "__main__":
    main()
