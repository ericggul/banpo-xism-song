# CLAUDE.md — banpo-xism-song

Lyric-video pipeline for 19 song variations, same lyrics. See README.md for the human workflow.

## What this repo does

Each song = 1 mp3 (in `audio/`) + 1 shared lyrics file (`lyrics/lyrics.txt`) + 1 shared image (`image/1.png`) + per-song timings (`timings/<slug>.json`). Output is a 1920×1080 H.264 mp4 with burnt-in ASS subtitles.

## Commands

```bash
# all-in-one: auto-time + build .ass + render mp4
tools/build.sh 반포자이즘-1

# ASS only (after editing timings/<slug>.json by hand or via the tap tool)
NO_RENDER=1 tools/build.sh 반포자이즘-1

# render only (after editing the .ass directly)
tools/render.sh 반포자이즘-1

# render without ken-burns zoom
tools/render.sh 반포자이즘-1 --no-zoom

# custom image
IMAGE=image/foo.png tools/render.sh 반포자이즘-1
```

## File-format invariants

- `lyrics/lyrics.txt`: one displayed line per line. Blank lines separate sections. Lines wrapped in `[...]` (e.g. `[Verse]`, `[Chorus]`) are section labels — rendered as small ghost captions, *not* counted as lyric lines.
- `timings/<slug>.json`: a JSON list of `{"start": float, "end": float}` — exactly one entry per non-section lyric line, in order. Count must match `lyrics.txt` lyric-line count or `make_ass.py` exits.
- `style/b_kyu.ass.tpl`: ASS header (Script Info + V4+ Styles + Events Format line) with **no** Dialogue events. `make_ass.py` appends Dialogue lines.

## Style mapping inside make_ass.py

- Lyric lines in a `[Chorus]` section → `LyricAlt` style (bigger, thicker outline, different colour) for pop.
- Lyric lines elsewhere → `Lyric` style.
- Section headers → `Section` style, faded in/out 1.8s before the next lyric line.

If you add a new style to the template, you also need to teach `make_ass.py` when to apply it.

## ASS notes (libass-specific gotchas)

- ffmpeg passes `ass=<filename>` to libass; colons, brackets, and non-ASCII paths confuse the filtergraph parser, so `render.sh` `cd`s into `timings/` and references the file by basename.
- Times: `H:MM:SS.cs` (centiseconds, two digits).
- Colours: `&HAABBGGRR&` — alpha first, then BGR. `&H0000F0FF&` = opaque yellow (#FFF000).
- Inline overrides: `{\fad(in,out)}`, `{\bord<N>}`, `{\3c&HBBGGRR&}` (outline colour), `{\1c&HBBGGRR&}` (primary colour), `{\k<centiseconds>}` (karaoke).
- For real karaoke (per-syllable colour fill) you need to break a line into `{\k20}글자{\k15}글자...` tokens that sum to the line duration in cs. We don't do this yet — line-level timing is the v1 target.

## Adding a new song

1. Drop `audio/<slug>.mp3`.
2. `tools/build.sh <slug>` → produces `timings/<slug>.json` (auto), `timings/<slug>.ass`, `output/<slug>.mp4`.
3. Inspect the mp4. If timing is off, either:
   - hand-edit `timings/<slug>.json` (it's plain JSON, line N maps to lyric line N) and re-run `tools/build.sh <slug>`, or
   - use `tools/tap_timing.html` (needs a local http server because file-system fetch is blocked by browsers).

## Adding a new lyric *line* (or changing the lyrics)

- Edit `lyrics/lyrics.txt`. Every `timings/*.json` will now be out of sync.
- Easiest fix: delete affected `timings/<slug>.json` and re-run `tools/build.sh <slug>` to re-auto-distribute.

## Things deliberately out of scope (v1)

- Per-syllable karaoke `\k` fill (needs forced alignment — could add `aeneas` later).
- Animated backgrounds / video B-roll.
- Auto-upload to YouTube (use `youtube-upload` or just drag-drop).
- Whisper transcription — vocals over a backing track are unreliable, and we already have ground-truth lyrics.

## When you (Claude Code) are asked to "do song N"

Default to:

```bash
tools/build.sh 반포자이즘-N
```

If the user reports bad timing, do **not** re-run auto_distribute — it'll just produce the same result. Either ask them to use the tap tool, or hand-edit `timings/반포자이즘-N.json` based on what they describe.
