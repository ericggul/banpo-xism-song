# 반포자이즘 album cover — master prompt system

Reference: `image/1.png` (cover for song 1, K-pop synth-pop).

All 21 covers share the **same composition** (girl, balcony, Banpo skyline,
yellow-orange "반포자이즘" logotype bottom-right). Only the **tone** shifts
per track — calibrated against each song's actual audio features (BPM, key,
mode, spectral centroid, onset density, intro silence) extracted from the
mp3s by `tools/analyze_audio.py`.

## Source files

- `tools/build_prompts.py` — the generator. Edit tone profiles or per-track
  flavor here; re-run to regenerate every `.txt`.
- `tracks/tracks.json` — track metadata (genre / duration / language).
- `tracks/audio_features.json` — `librosa`-extracted per-track features.
- `image/prompts/<N>-<tag>.txt` — generated prompt files (one per cover).

## Regenerating

```bash
# 1. (only if mp3s changed) re-extract audio features
python3 tools/analyze_audio.py

# 2. (re)generate all 21 prompts
python3 tools/build_prompts.py

# 3. dump prompt for a song to clipboard + stdout
tools/cover.sh <N>
```

## Per-track tone map

| #  | Genre                                         | BPM | Key       | Tone tag             |
|---:|-----------------------------------------------|----:|-----------|----------------------|
|  1 | K-Pop synth-driven                             | 136 | D# major  | `synth-pop` (ref)    |
|  2 | Alt-pop / dream-pop / sadcore                  | 152 | D major   | `ballad`             |
|  3 | 2025 house × electronic hip-hop                | 129 | F# major  | `house-hip-hop`      |
|  4 | K-Pop synth-driven (minor variation)           |  92 | E minor   | `synth-pop`          |
|  5 | 90s East-Coast hip-hop                         |  99 | E minor   | `90s-hip-hop`        |
|  6 | Electropop / dark indie pop                    |  89 | C minor   | `dark-indie`         |
|  7 | 2020s progressive house                        | 129 | F# minor  | `prog-house`         |
|  8 | Korean drama OST — slowest of the album        |  70 | A# major  | `kdrama-ost-spring`  |
|  9 | K-Pop hip-hop (glossy bling)                   | 129 | C major   | `kpop-hh-glossy`     |
| 10 | Europop 2000s (glitter)                        | 103 | B minor   | `europop-glitter`    |
| 11 | 2025 house × hh — warmer dawn rooftop          | 123 | E major   | `house-hip-hop`      |
| 12 | Berlin house / hardcore / minimal              | 123 | C minor   | `berlin-minimal`     |
| 13 | Korean drama OST — winter climax               | 144 | A# major  | `kdrama-ost-winter`  |
| 14 | 1930s jazz & blues                             | 108 | C# major  | `30s-jazz`           |
| 15 | Europop 2000s — sad after-party                |  89 | F minor   | `europop-sad-disco`  |
| 16 | Korean drama OST — autumn farewell             | 152 | D major   | `kdrama-ost-autumn`  |
| 17 | K-Pop hip-hop (late-night trap chill)          |  89 | A# major  | `kpop-hh-misty`      |
| 18 | K-Pop synth-driven (cyber-pink variation)      | 136 | D# major  | `synth-pop`          |
| 19 | Japanese anime ED (bonus)                      |  89 | F major   | `anime-ed`           |
| 20 | 1980s French song (bonus)                      | 129 | C major   | `80s-french`         |
| 21 | Late 90s Berlin house (bonus)                  | 129 | F minor   | `berlin-90s`         |

Same genre/BPM clusters (1↔18, 3↔11, 9↔17, 10↔15, 8↔13↔16) deliberately get
*different* sub-tone tags + outfit / weather variations so they don't render
identically.

## Orientation variants

Each track has two prompt files:
- `image/prompts/<N>-<tag>.txt`           — 16:9 horizontal (1920×1080, YouTube standard)
- `image/prompts/vertical/<N>-<tag>.txt`  — 9:16 vertical (1080×1920, YouTube Shorts / Reels / TikTok)

Both share the same TONE / THIS-TRACK / AUDIO-DERIVED-NOTES blocks; only the
locked composition block differs (re-framed for the target aspect ratio).
Use the same track for the same cover concept — outfit, palette, lighting,
expression, logotype style must match between H and V so they read as the
same album cover in two crops.

## Usage flow per cover

1. Horizontal: `tools/cover.sh <N>` → prompt copied to clipboard
   Vertical:   `tools/cover.sh <N> vertical` (or `v`)
2. Paste into your image-gen tool (ChatGPT / Midjourney / Imagen / Sora / …)
3. Save the result as:
   - `image/<N>.png`             for horizontal
   - `image/<N>-vertical.png`    for vertical
4. `tools/build.sh 반포자이즘-<N>` → final lyric mp4 in `output/`
   (For vertical Shorts rendering: see WORKFLOW.md — vertical render is a
    separate ffmpeg call with 1080×1920 canvas + the vertical image.)

See `WORKFLOW.md` for the full pipeline.
