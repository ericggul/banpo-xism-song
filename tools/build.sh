#!/usr/bin/env bash
# One-shot: audio → whisper transcript (cached) → align to known lyrics
#        → timings.json → .ass → mp4.
#
# Override behaviour:
#   V=1 | V=2 | V=3 (default)  pick aligner:
#       v1 = LCS over flat syllable stream (legacy)
#       v2 = monotonic segment walk + local NW (legacy)
#       v3 = global DP alignment + hallucination de-dup (default)
#   TIMINGS=path/to.json   skip whisper+align, use given timings file
#   NO_RENDER=1            stop after .ass (skip mp4 render)
#   FORCE_WHISPER=1        ignore cached *.whisper.json and re-transcribe
#   FORCE_ALIGN=1          ignore cached timings.json and re-align
#   DEMUCS=1               run Demucs vocal separation before whisper.
#                          Strongly recommended for tracks where whisper
#                          hallucinates intro / instrumental sections as
#                          repeated syllables ("마 마 마…", "나 나 나…").
#                          Caches the vocal stem in
#                          timings/demucs/<slug>.vocals.wav.
#   VERTICAL=1             render the 9:16 YouTube Shorts variant instead
#                          of the default 16:9 horizontal. Reuses the same
#                          timings.json (lyric timing is aspect-independent)
#                          but applies style/b_kyu_vertical.ass.tpl and
#                          looks for image/<N>-vertical.png. Writes
#                          timings/<slug>-vertical.ass +
#                          output/<slug>-vertical.mp4.
#
# Usage: tools/build.sh <song-slug>
set -euo pipefail

SLUG="${1:?usage: build.sh <song-slug>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Pick the python interpreter that actually has mlx_whisper installed —
# different shells (login vs interactive, conda vs system) can resolve
# `python3` to different binaries on macOS, so probe a few common paths.
if [[ -z "${PY:-}" ]]; then
  for cand in \
      python3 \
      /opt/homebrew/Caskroom/miniconda/base/bin/python3 \
      /opt/homebrew/bin/python3 \
      /usr/local/bin/python3; do
    if command -v "$cand" >/dev/null 2>&1 \
       && "$cand" -c "import mlx_whisper" >/dev/null 2>&1; then
      PY="$cand"; break
    fi
  done
fi
if [[ -z "${PY:-}" ]]; then
  echo "ERROR: no python with mlx_whisper installed found." >&2
  echo "Install it into the python you intend to use:" >&2
  echo "  /opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pip install mlx-whisper" >&2
  exit 1
fi
echo "→ python: $PY"
export PY

AUDIO="$ROOT/audio/${SLUG}.mp3"
LYRICS="${LYRICS:-$ROOT/lyrics/lyrics.txt}"
WHISPER="$ROOT/timings/${SLUG}.whisper.json"
TIMINGS="${TIMINGS:-$ROOT/timings/${SLUG}.json}"

if [[ "${VERTICAL:-0}" == "1" ]]; then
  STYLE="${STYLE:-$ROOT/style/b_kyu_vertical.ass.tpl}"
  ASS="$ROOT/timings/${SLUG}-vertical.ass"
  echo "→ orientation: VERTICAL (9:16 Shorts)"
else
  STYLE="${STYLE:-$ROOT/style/b_kyu.ass.tpl}"
  ASS="$ROOT/timings/${SLUG}.ass"
  echo "→ orientation: horizontal (16:9)"
fi

[[ -f "$AUDIO" ]]  || { echo "missing audio: $AUDIO" >&2; exit 1; }
[[ -f "$LYRICS" ]] || { echo "missing lyrics: $LYRICS" >&2; exit 1; }

V="${V:-3}"
case "$V" in
  1) ALIGNER="$ROOT/tools/align_lyrics.py" ;;
  2) ALIGNER="$ROOT/tools/align_lyrics_v2.py" ;;
  3) ALIGNER="$ROOT/tools/align_lyrics_v3.py" ;;
  *) echo "unknown V=$V (use 1, 2, or 3)" >&2; exit 1 ;;
esac

# Per-song custom aligner override. If tools/aligners/song<N>.py exists for
# this track, it wins over the default v3. Each per-song aligner is
# hand-tuned to that track's whisper failure modes (intro hallucinations,
# missing verses, mid-line splits, etc.).
if [[ "$SLUG" =~ ^반포자이즘-([0-9]+)$ ]]; then
  CUSTOM_FILE="$ROOT/tools/aligners/song${BASH_REMATCH[1]}.py"
  if [[ -f "$CUSTOM_FILE" ]]; then
    ALIGNER="$CUSTOM_FILE"
    echo "→ aligner: tools/aligners/song${BASH_REMATCH[1]}.py (custom)"
  else
    echo "→ aligner: v$V (default)"
  fi
else
  echo "→ aligner: v$V (default)"
fi

if [[ ! -f "$TIMINGS" || "${FORCE_ALIGN:-0}" == "1" ]]; then
  if [[ "${FORCE_WHISPER:-0}" == "1" ]]; then rm -f "$WHISPER"; fi
  T_ARGS=("$AUDIO" "$WHISPER")
  [[ "${DEMUCS:-0}" == "1" ]] && T_ARGS+=(--demucs)
  "$PY" "$ROOT/tools/transcribe.py" "${T_ARGS[@]}"
  "$PY" "$ALIGNER" "$WHISPER" "$LYRICS" "$TIMINGS"
else
  echo "→ using existing timings: $TIMINGS"
fi

"$PY" "$ROOT/tools/make_ass.py" "$LYRICS" "$TIMINGS" "$STYLE" "$ASS"

if [[ "${NO_RENDER:-0}" != "1" ]]; then
  VERTICAL="${VERTICAL:-0}" bash "$ROOT/tools/render.sh" "$SLUG"
fi
