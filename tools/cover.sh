#!/usr/bin/env bash
# Album-cover prompt helper.
#
# Reads image/prompts/<N>-<tag>.txt (horizontal) or
#       image/prompts/vertical/<N>-<tag>.txt (vertical),
# copies it to the clipboard (pbcopy on macOS), and prints it to stdout —
# so you can paste it straight into your image-gen tool (ChatGPT /
# Midjourney / Imagen / Sora / …).
#
# If OPENAI_API_KEY is set and you pass --api, it also calls gpt-image-1
# directly and saves the PNG to image/<N>.png (horizontal) or
# image/<N>-vertical.png (vertical).
#
# Usage:
#   tools/cover.sh <N>                    # horizontal prompt → clipboard + stdout
#   tools/cover.sh <N> vertical           # vertical (9:16 Shorts) prompt
#   tools/cover.sh <N> v                  # short alias for "vertical"
#   tools/cover.sh <N> --api              # also auto-generate (horizontal)
#   tools/cover.sh <N> vertical --api     # also auto-generate (vertical)
#   tools/cover.sh list                   # show all available prompts
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROMPTS_H="$ROOT/image/prompts"
PROMPTS_V="$ROOT/image/prompts/vertical"

cmd="${1:-}"
[[ -n "$cmd" ]] || { sed -n '2,22p' "$0"; exit 1; }

if [[ "$cmd" == "list" ]]; then
  echo "── horizontal ──"
  ls "$PROMPTS_H"/*.txt 2>/dev/null | xargs -n1 basename | sort -V
  echo
  echo "── vertical (9:16 Shorts) ──"
  ls "$PROMPTS_V"/*.txt 2>/dev/null | xargs -n1 basename | sort -V
  exit 0
fi

N="$cmd"
shift || true

# Pick orientation from arg 2 (if it's "vertical" / "v" / "horizontal" / "h").
ORIENT="horizontal"
if [[ "${1:-}" == "vertical" || "${1:-}" == "v" ]]; then
  ORIENT="vertical"; shift
elif [[ "${1:-}" == "horizontal" || "${1:-}" == "h" ]]; then
  ORIENT="horizontal"; shift
fi

case "$ORIENT" in
  horizontal) PROMPTS_DIR="$PROMPTS_H"; OUT_NAME="${N}.png" ;;
  vertical)   PROMPTS_DIR="$PROMPTS_V"; OUT_NAME="${N}-vertical.png" ;;
esac

matches=( "$PROMPTS_DIR/${N}-"*.txt )
if [[ ! -f "${matches[0]}" ]]; then
  echo "no $ORIENT prompt file for song $N (looked for $PROMPTS_DIR/${N}-*.txt)" >&2
  echo "available:" >&2
  ls "$PROMPTS_DIR"/*.txt 2>/dev/null | xargs -n1 basename | sort -V >&2 || true
  exit 1
fi
file="${matches[0]}"
tag="$(basename "$file" .txt)"

if [[ "${1:-}" == "--api" ]]; then
  [[ -n "${OPENAI_API_KEY:-}" ]] || { echo "--api requires OPENAI_API_KEY env var" >&2; exit 1; }
  out="$ROOT/image/$OUT_NAME"
  echo "→ calling gpt-image-1 for song $N ($tag, $ORIENT) …" >&2
  SIZE_FLAG=()
  [[ "$ORIENT" == "vertical" ]] && SIZE_FLAG=(--size 1024x1536)
  python3 "$ROOT/tools/gen_cover.py" "$file" "$out" "${SIZE_FLAG[@]}"
  echo "✓ saved $out" >&2
  exit 0
fi

# default: dump to stdout + clipboard
cat "$file"
if command -v pbcopy >/dev/null 2>&1; then
  pbcopy < "$file"
  bytes=$(wc -c < "$file" | tr -d ' ')
  echo "" >&2
  echo "─────────────────────────────────────────────" >&2
  echo "✓ song $N $ORIENT prompt ($tag) — $bytes chars copied to clipboard" >&2
  echo "  paste into your image-gen tool, save result as image/${OUT_NAME}" >&2
fi
