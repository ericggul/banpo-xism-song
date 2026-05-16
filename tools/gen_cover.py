#!/usr/bin/env python3
"""
Call OpenAI gpt-image-1 with a prompt file and save the result as PNG.

Usage:
    gen_cover.py PROMPT.txt OUT.png

Requires:
    OPENAI_API_KEY env var
    pip install openai  (auto-installed if missing)
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path


def ensure_openai():
    try:
        import openai  # noqa
    except ImportError:
        import subprocess
        print("installing openai SDK …", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "openai"])
        import openai  # noqa


def main():
    args = sys.argv[1:]
    size = "1536x1024"  # default: 3:2, closest to 16:9 widescreen
    if "--size" in args:
        i = args.index("--size")
        size = args[i + 1]; del args[i:i + 2]
    if len(args) != 2:
        sys.exit(__doc__)
    prompt_p = Path(args[0])
    out_p = Path(args[1])
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY not set")

    ensure_openai()
    from openai import OpenAI
    client = OpenAI()

    prompt = prompt_p.read_text(encoding="utf-8").strip()
    print(f"→ generating ({len(prompt)} char prompt, size {size}) …", file=sys.stderr)
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=size,
        quality="high",
        n=1,
    )
    b64 = result.data[0].b64_json
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_bytes(base64.b64decode(b64))
    print(f"✓ wrote {out_p}", file=sys.stderr)


if __name__ == "__main__":
    main()
