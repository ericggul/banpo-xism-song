#!/usr/bin/env python3
"""
Extract objective audio features for every track so the cover-prompt
generator has something better than genre-name guesses to work with.

For each mp3 we collect:
  tempo_bpm        — librosa beat-tracker estimate
  key              — krumhansl-schmuckler chroma → "C major" / "A minor" / …
  mode             — "major" / "minor"
  rms_mean_db      — loudness
  rms_std_db       — dynamic-range proxy
  spectral_centroid_hz_mean — brightness proxy
  zcr_mean         — texture roughness (vocals/distortion)
  onset_rate_hz    — how often new events fire (energy density)
  intro_silence_s  — leading silence before first sustained energy
  outro_silence_s  — trailing silence after last sustained energy
  duration_s       — total length

Output: tracks/audio_features.json
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import librosa


KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
PITCHES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def estimate_key(y: np.ndarray, sr: int) -> tuple[str, str]:
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    best = ("", -1e9, "")
    for i in range(12):
        major = float(np.corrcoef(np.roll(KS_MAJOR, i), chroma)[0, 1])
        minor = float(np.corrcoef(np.roll(KS_MINOR, i), chroma)[0, 1])
        if major > best[1]:
            best = (f"{PITCHES[i]} major", major, "major")
        if minor > best[1]:
            best = (f"{PITCHES[i]} minor", minor, "minor")
    return best[0], best[2]


def silence_bounds(y: np.ndarray, sr: int, frame: int = 2048, hop: int = 512) -> tuple[float, float]:
    rms = librosa.feature.rms(y=y, frame_length=frame, hop_length=hop)[0]
    if rms.size == 0:
        return 0.0, 0.0
    peak = rms.max()
    thr = peak * 0.18  # silence ≲ 18 % of peak
    above = rms > thr
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    if not above.any():
        return 0.0, 0.0
    first = times[np.argmax(above)]
    last_idx = len(above) - 1 - np.argmax(above[::-1])
    last_active = times[last_idx]
    total = librosa.get_duration(y=y, sr=sr)
    return float(first), float(total - last_active)


def db(x: float) -> float:
    return 20.0 * math.log10(max(x, 1e-9))


def analyze(audio_path: Path) -> dict:
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(np.atleast_1d(tempo)[0])

    key, mode = estimate_key(y, sr)
    rms = librosa.feature.rms(y=y)[0]
    sc = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    zcr = librosa.feature.zero_crossing_rate(y=y)[0]

    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    onset_rate = float(len(onsets) / duration) if duration > 0 else 0.0

    intro_silence, outro_silence = silence_bounds(y, sr)

    return {
        "duration_s": round(duration, 2),
        "tempo_bpm": round(tempo_val, 1),
        "key": key,
        "mode": mode,
        "rms_mean_db": round(db(float(rms.mean())), 2),
        "rms_std_db": round(db(float(rms.std()) + 1e-9), 2),
        "spectral_centroid_hz_mean": round(float(sc.mean()), 1),
        "zcr_mean": round(float(zcr.mean()), 4),
        "onset_rate_hz": round(onset_rate, 2),
        "intro_silence_s": round(intro_silence, 2),
        "outro_silence_s": round(outro_silence, 2),
    }


def main():
    root = Path(__file__).resolve().parents[1]
    tracks = json.loads((root / "tracks/tracks.json").read_text(encoding="utf-8"))
    out = {}
    for t in tracks:
        slug = t["filename"]
        audio = root / "audio" / f"{slug}.mp3"
        if not audio.exists():
            print(f"  skip {slug} (no mp3)", file=sys.stderr)
            continue
        print(f"  analyzing {slug} …", file=sys.stderr)
        try:
            feats = analyze(audio)
        except Exception as e:
            print(f"    error: {e}", file=sys.stderr)
            continue
        feats["index"] = t["index"]
        feats["filename"] = slug
        feats["genre"] = t["genre"]
        out[str(t["index"])] = feats

    out_p = root / "tracks/audio_features.json"
    out_p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_p}", file=sys.stderr)


if __name__ == "__main__":
    main()
