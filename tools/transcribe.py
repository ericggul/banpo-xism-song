#!/usr/bin/env python3
"""
Run mlx-whisper on a single audio file and dump the raw segments+words.

Cached: if WHISPER.json already exists and is newer than the audio, no-op.

Usage:
    transcribe.py AUDIO.mp3 OUT.json [--model REPO] [--prompt "..."] [--demucs]

--demucs runs Demucs (htdemucs) to extract the vocal stem before whisper.
Strongly recommended for tracks where whisper hallucinates ("마 마 마…",
"나 나 나…") over the bare mp3 — the synth-heavy / processed-vocal
production confuses the model, and the isolated vocal stem fixes it.

The full Korean lyrics are baked into the default initial_prompt so
whisper biases its decoding toward the right words even on noisy tracks.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path


DEFAULT_PROMPT = (
    "반포의 빛이 나를 부르네 자이의 품에 안기고 싶어 강남의 별들 아래 꿈꾸네 "
    "높은 순위 속에 날 세우고 싶어 반포야 반포야 너는 나의 별 자이야 자이야 나를 안아줘 "
    "상급지의 왕관 내가 쓸래 학군지도 나를 반겨줄래 강바람 속에 흩날리는 꿈 "
    "부동산 지도 속 반짝이는 점 하급지는 뒤로 상급지로 달려 자이의 문턱 넘고 싶어 "
    "순위의 숫자에 내 마음이 춤춰 반포의 꿈이 나를 깨우네 자이의 이름을 가슴에 새기며 "
    "내 미래를 이곳에 맡기고 싶어"
)


def run_demucs(audio: Path) -> Path:
    """Extract vocal stem via Demucs, cached under timings/<slug>.vocals.wav."""
    out_dir = audio.parent.parent / "timings" / "demucs"
    out_dir.mkdir(parents=True, exist_ok=True)
    cached = out_dir / f"{audio.stem}.vocals.wav"
    if cached.exists() and cached.stat().st_mtime >= audio.stat().st_mtime:
        print(f"[cache] vocal stem up-to-date: {cached}")
        return cached

    import subprocess
    work = out_dir / "_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    print(f"→ demucs htdemucs (extracting vocal stem from {audio.name}) …")
    subprocess.check_call([
        sys.executable, "-m", "demucs",
        "--two-stems", "vocals",
        "-n", "htdemucs",
        "-o", str(work),
        str(audio),
    ])
    src = work / "htdemucs" / audio.stem / "vocals.wav"
    if not src.exists():
        sys.exit(f"demucs did not produce {src}")
    shutil.move(str(src), str(cached))
    shutil.rmtree(work)
    return cached


def main() -> None:
    args = sys.argv[1:]
    model = "mlx-community/whisper-large-v3-turbo"
    prompt = DEFAULT_PROMPT
    use_demucs = False
    while "--model" in args:
        i = args.index("--model"); model = args[i+1]; del args[i:i+2]
    while "--prompt" in args:
        i = args.index("--prompt"); prompt = args[i+1]; del args[i:i+2]
    while "--demucs" in args:
        use_demucs = True; args.remove("--demucs")
    if len(args) != 2:
        sys.exit(__doc__)

    audio = Path(args[0])
    out = Path(args[1])
    if out.exists() and out.stat().st_mtime >= audio.stat().st_mtime:
        print(f"[cache] {out} up-to-date — skipping whisper")
        return

    audio_for_whisper = audio
    if use_demucs:
        audio_for_whisper = run_demucs(audio)

    import mlx_whisper  # heavy import: do it after the cache check

    t = time.time()
    print(f"transcribing {audio_for_whisper.name} via {model} ...")
    result = mlx_whisper.transcribe(
        str(audio_for_whisper),
        path_or_hf_repo=model,
        language="ko",
        word_timestamps=True,
        initial_prompt=prompt,
        condition_on_previous_text=False,
        temperature=0.0,
        no_speech_threshold=0.5,
        verbose=False,
    )
    print(f"done in {time.time()-t:.1f}s, {len(result['segments'])} segments")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
