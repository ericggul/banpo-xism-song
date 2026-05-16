#!/usr/bin/env python3
"""
Build an .ass subtitle file from lyrics.txt + a timings file.

lyrics.txt format:
    blank lines separate sections
    a line wrapped in [] (e.g. [Verse], [Chorus]) renders as a small Section label
    everything else is a Lyric line

timings file: JSON list, one entry per *non-section* lyric line, in order.
    [{"start": 0.0, "end": 4.5}, ...]
    Section labels inherit the time-window of the next lyric line.

Usage:
    make_ass.py LYRICS.txt TIMINGS.json STYLE_TPL.ass OUT.ass
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def fmt_ts(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def parse_lyrics(text: str):
    """Yield (kind, text) where kind in {"section", "lyric"}."""
    section_re = re.compile(r"^\s*\[(.+)\]\s*$")
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = section_re.match(line)
        if m:
            yield ("section", m.group(1).strip())
        else:
            yield ("lyric", line)


def build_events(lyrics_path: Path, timings_path: Path) -> list[str]:
    items = list(parse_lyrics(lyrics_path.read_text(encoding="utf-8")))
    timings = json.loads(timings_path.read_text(encoding="utf-8"))

    lyric_indices = [i for i, (k, _) in enumerate(items) if k == "lyric"]
    if len(timings) != len(lyric_indices):
        sys.exit(
            f"timing count {len(timings)} != lyric line count {len(lyric_indices)}"
        )
    # map item-index -> timing
    timing_by_idx = {idx: timings[k] for k, idx in enumerate(lyric_indices)}

    # Pre-compute: which lyric-line indices belong to a chorus section
    chorus_lyric_items: set[int] = set()
    for s_i, (kind, text) in enumerate(items):
        if kind == "section" and "chorus" in text.lower():
            for j in range(s_i + 1, len(items)):
                if items[j][0] == "section":
                    break
                if items[j][0] == "lyric":
                    chorus_lyric_items.add(j)

    events: list[tuple[float, float, str, str]] = []  # (start, end, style, text)

    for i, (kind, text) in enumerate(items):
        if kind == "lyric":
            t = timing_by_idx[i]
            style = "LyricAlt" if i in chorus_lyric_items else "Lyric"
            events.append((float(t["start"]), float(t["end"]), style, text))
            continue

        # section header:
        # render ONLY inside the instrumental gap between the previous lyric's
        # end and the next lyric's start. First section (no previous lyric)
        # is suppressed entirely — keeps the intro 100% blank.
        next_lyric = next((j for j in lyric_indices if j > i), None)
        prev_lyric_end = None
        for j in reversed(lyric_indices):
            if j < i:
                prev_lyric_end = float(timing_by_idx[j]["end"])
                break

        if next_lyric is None or prev_lyric_end is None:
            continue
        nxt_start = float(timing_by_idx[next_lyric]["start"])
        gap = nxt_start - prev_lyric_end
        if gap < 0.6:
            continue
        events.append((prev_lyric_end + 0.1, nxt_start - 0.05, "Section", f"[ {text} ]"))

    # Build dialogue lines
    lines: list[str] = []
    for start, end, style, text in events:
        if style == "Section":
            payload = r"{\fad(200,200)}" + text
        elif style == "LyricAlt":
            payload = r"{\fad(80,120)\bord7\3c&H1020A0&}" + text
        else:
            payload = r"{\fad(80,120)}" + text
        lines.append(
            f"Dialogue: 0,{fmt_ts(start)},{fmt_ts(end)},{style},,0,0,0,,{payload}"
        )
    return lines


def main() -> None:
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    lyrics_p = Path(sys.argv[1])
    timings_p = Path(sys.argv[2])
    style_p = Path(sys.argv[3])
    out_p = Path(sys.argv[4])

    style_text = style_p.read_text(encoding="utf-8")
    if not style_text.endswith("\n"):
        style_text += "\n"

    events = build_events(lyrics_p, timings_p)
    out_p.write_text(style_text + "\n".join(events) + "\n", encoding="utf-8")
    print(f"wrote {out_p} ({len(events)} events)")


if __name__ == "__main__":
    main()
