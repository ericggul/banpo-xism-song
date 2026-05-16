# banpo-xism-song

B급 lyric videos for 반포자이즘 (19 variations, same lyrics, different audio).
Single static image + per-song audio + burnt-in ASS subtitles via ffmpeg.

```
audio/         19 mp3 variations
image/         1.png — the static background
lyrics/        lyrics.txt — canonical lyrics (one file, all songs share it)
style/         b_kyu.ass.tpl — ASS styles (B급 yellow text, thick outline, fade)
timings/       per-song .json (line starts/ends) + generated .ass
tools/         python + bash + html helpers
output/        rendered .mp4
```

## Workflow per song

1. **Auto-distribute** rough line timings from audio duration + silence detection.
2. **(Optional) Refine** with the browser tap tool — load audio, tap `Space` at each line start.
3. **Build .ass** from lyrics + timings + style template.
4. **Render** mp4: still image + audio + burnt-in subs.

Steps 1, 3, 4 are a single command:

```bash
tools/build.sh 반포자이즘-1
```

The first run auto-distributes timings (`timings/<slug>.json`), builds the ASS,
and renders the mp4. Re-runs reuse the existing `timings/<slug>.json` so you
can hand-edit it (or replace it via the tap tool) and just re-run `build.sh`.

## Refining timings

```bash
cd $(pwd)
python3 -m http.server 8000
# open http://localhost:8000/tools/tap_timing.html
# click "load defaults" — plays song 1 + loads lyrics
# tap Space at the start of each lyric line
# download timings.json → save as timings/반포자이즘-1.json
# re-run tools/build.sh 반포자이즘-1
```

Keys: `Space` mark · `Backspace` undo · `Enter` play/pause · `←/→` ±2s · `↑/↓` speed · `R` replay current line.

## Re-rendering ASS only (no mp4)

```bash
NO_RENDER=1 tools/build.sh 반포자이즘-1
```

## Custom image per song

```bash
IMAGE=image/something-else.png tools/render.sh 반포자이즘-1
```

## All 19 songs at once

```bash
for f in audio/*.mp3; do
  slug=$(basename "$f" .mp3)
  tools/build.sh "$slug"
done
```

(Once song 1's timings are dialled in, you can also reuse the same timings.json
for variations of identical length — `cp timings/반포자이즘-1.json timings/반포자이즘-2.json`
— but durations differ, so usually each gets its own pass.)

## Style tweaks

Edit `style/b_kyu.ass.tpl` — fontnames, sizes, colours (ASS uses `&HAABBGGRR&`).
The `make_ass.py` script wraps the lyrics in additional override tags
(`\fad`, `\bord`, `\3c`) — adjust there if you want different per-style effects.

B급 ideas not yet wired up:
- karaoke `\k` per-syllable colour fill (needs syllable-level timing — out of scope for v1)
- random per-line `\an` alignment (sometimes top, sometimes bottom-left)
- 궁서체 mixed into every 4th line
- `\frz` slight rotation
