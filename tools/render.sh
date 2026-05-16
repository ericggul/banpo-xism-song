#!/usr/bin/env bash
# Render one lyric video: image (still) + audio + ASS subtitles → mp4 (YouTube-ready).
#
# Two orientations:
#   horizontal (default) — 1920×1080, lyrics bottom of frame, used for full
#                          YouTube uploads.
#   vertical (VERTICAL=1) — 1080×1920, lyrics middle of frame, used for
#                          YouTube Shorts / Reels / TikTok.
#
# Usage:
#   tools/render.sh <song-slug> [--no-zoom]
#   VERTICAL=1 tools/render.sh <song-slug>
#
# Expects:
#   audio/<slug>.mp3
#   timings/<slug>.ass         (horizontal) — built via tools/make_ass.py
#   timings/<slug>-vertical.ass (vertical)
#   image/<N>.png  OR  image/<slug>.png            (horizontal)
#   image/<N>-vertical.png  OR  image/<slug>-vertical.png  (vertical)
# Writes:
#   output/<slug>.mp4           (horizontal)
#   output/<slug>-vertical.mp4  (vertical)
#
# Image resolution order (first hit wins):
#   1. $IMAGE env var (if set)
#   2. image/<slug>[-vertical].png        e.g. image/반포자이즘-2-vertical.png
#   3. image/<N>[-vertical].png           where N is parsed from slug "반포자이즘-N"
#   4. image/1[-vertical].png             fallback
set -euo pipefail

SLUG="${1:?usage: render.sh <song-slug>}"
ZOOM=1
[[ "${2:-}" == "--no-zoom" ]] && ZOOM=0

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUDIO="$ROOT/audio/${SLUG}.mp3"
mkdir -p "$ROOT/output"

if [[ "${VERTICAL:-0}" == "1" ]]; then
  CANVAS_W=1080
  CANVAS_H=1920
  IMG_SUFFIX="-vertical"
  ASS="$ROOT/timings/${SLUG}-vertical.ass"
  OUT="$ROOT/output/${SLUG}-vertical.mp4"
else
  CANVAS_W=1920
  CANVAS_H=1080
  IMG_SUFFIX=""
  ASS="$ROOT/timings/${SLUG}.ass"
  OUT="$ROOT/output/${SLUG}.mp4"
fi

# auto-resolve image for this song + orientation
# For VERTICAL=1 we look (in order):
#   image/vertical/<slug>.png
#   image/vertical/<N>.png
#   image/<slug>-vertical.png
#   image/<N>-vertical.png
#   image/vertical/1.png
#   image/1.png  (last-resort fallback, will be cropped to vertical canvas)
# For horizontal:
#   image/<slug>.png
#   image/<N>.png
#   image/1.png
N_FROM_SLUG=""
if [[ "$SLUG" =~ ^반포자이즘-([0-9]+)$ ]]; then
  N_FROM_SLUG="${BASH_REMATCH[1]}"
fi

resolve_image() {
  local candidates=()
  if [[ "${VERTICAL:-0}" == "1" ]]; then
    candidates+=(
      "$ROOT/image/vertical/${SLUG}.png"
      "$ROOT/image/${SLUG}-vertical.png"
    )
    [[ -n "$N_FROM_SLUG" ]] && candidates+=(
      "$ROOT/image/vertical/${N_FROM_SLUG}.png"
      "$ROOT/image/${N_FROM_SLUG}-vertical.png"
    )
    candidates+=( "$ROOT/image/vertical/1.png" "$ROOT/image/1-vertical.png" "$ROOT/image/1.png" )
  else
    candidates+=( "$ROOT/image/${SLUG}.png" )
    [[ -n "$N_FROM_SLUG" ]] && candidates+=( "$ROOT/image/${N_FROM_SLUG}.png" )
    candidates+=( "$ROOT/image/1.png" )
  fi
  for c in "${candidates[@]}"; do
    if [[ -f "$c" ]]; then echo "$c"; return; fi
  done
}

if [[ -n "${IMAGE:-}" ]]; then
  : # user-specified
else
  IMAGE="$(resolve_image)"
fi
echo "→ using image: ${IMAGE#$ROOT/}"
echo "→ canvas: ${CANVAS_W}×${CANVAS_H}"

[[ -f "$IMAGE" ]] || { echo "missing image: $IMAGE" >&2; exit 1; }
[[ -f "$AUDIO" ]] || { echo "missing audio: $AUDIO" >&2; exit 1; }
[[ -f "$ASS"   ]] || { echo "missing ass:   $ASS"   >&2; exit 1; }

# libass can't easily handle colons/non-ASCII in the ass=... filter argument.
# Workaround: cd into the .ass directory and reference it by basename.
ASS_DIR="$(dirname "$ASS")"
ASS_NAME="$(basename "$ASS")"

if [[ "$ZOOM" == "1" ]]; then
  VFILTER="[0:v]scale=${CANVAS_W}:${CANVAS_H}:force_original_aspect_ratio=increase,crop=${CANVAS_W}:${CANVAS_H},zoompan=z='min(zoom+0.0004,1.08)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${CANVAS_W}x${CANVAS_H}:fps=30,ass='${ASS_NAME}'[v]"
else
  VFILTER="[0:v]scale=${CANVAS_W}:${CANVAS_H}:force_original_aspect_ratio=increase,crop=${CANVAS_W}:${CANVAS_H},fps=30,ass='${ASS_NAME}'[v]"
fi

# Audio: copy the source mp3 stream directly into the mp4 container with NO
# re-encoding (`-c:a copy`). This preserves the original mp3 bit-for-bit so
# the rendered video has exactly the same audio quality as the source mp3.
# Re-encoding to AAC (which the previous build did at 192k) is a generation
# of lossy compression that audibly degrades the track — especially
# noticeable on dense / electronic / mastered material. mp4 + mp3 is
# supported natively by all modern players including YouTube (YouTube will
# transcode internally anyway, so giving it the cleanest source possible
# is best).
cd "$ASS_DIR"
ffmpeg -y -hide_banner \
  -loop 1 -framerate 30 -i "$IMAGE" \
  -i "$AUDIO" \
  -filter_complex "$VFILTER" \
  -map "[v]" -map 1:a \
  -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p \
  -c:a copy \
  -shortest -movflags +faststart \
  "$OUT"

echo "rendered → $OUT"
