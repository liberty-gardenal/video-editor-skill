"""Word-level transcription with faster-whisper and RMS-based start refinement."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from .probe import probe
from .util import VeditError, ensure_parent, ffmpeg_path, info, require_module

SR = 16000
WIN = 0.010  # 10 ms analysis windows


def decode_audio(path):
    """Decode to 16 kHz mono float32 numpy array via ffmpeg."""
    np = require_module("numpy", "numpy", "decodificar áudio para transcrição")
    cmd = [
        ffmpeg_path(), "-hide_banner", "-nostdin", "-v", "error", "-i", str(path),
        "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-",
    ]  # fmt: skip
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise VeditError("Não consegui decodificar o áudio da mídia (ela tem áudio?).")
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def window_db(audio, sr: int = SR):
    """RMS in dBFS for consecutive 10 ms windows."""
    np = require_module("numpy", "numpy", "analisar energia")
    n = int(sr * WIN)
    k = len(audio) // n
    if k == 0:
        return np.zeros(0)
    frames = audio[: k * n].reshape(k, n)
    rms = np.sqrt((frames**2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms)


def refine_starts(words: list[dict], audio, sr: int = SR, thr: float = -35.0) -> list[dict]:
    """Move each start to the real onset: first of 3 consecutive loud windows after >=40 ms silence.

    Starts only move forward and never past ``end - 40 ms``, so words never overlap or reorder.
    """
    db = window_db(audio, sr)
    out = [dict(w) for w in words]
    for w in out:
        lo = int(w["t"] / WIN)
        hi = min(int(min(w["e"] - 0.04, w["t"] + 0.4) / WIN), len(db) - 3)
        if hi <= lo:
            continue
        for i in range(max(lo, 4), hi + 1):
            if all(db[i - k] < thr for k in range(1, 5)) and all(db[i + k] >= thr for k in range(3)):
                w["t"] = round(max(i * WIN, w["t"]), 3)
                break
    prev_t = 0.0
    for w in out:
        w["t"] = max(w["t"], prev_t)
        w["e"] = max(w["e"], w["t"] + 0.01)
        prev_t = w["t"]
    return out


def choose_model(duration: float | None, model: str | None) -> str:
    if model:
        return model
    return "large-v3" if (duration or 0) <= 600 else "small"


def transcribe(media, output, model: str | None = None, lang: str | None = None, vad: bool = False) -> dict:
    fw = require_module("faster_whisper", "faster-whisper", "transcrever")
    meta = probe(media, audio_analysis=False)
    if not meta.get("has_audio"):
        raise VeditError("A mídia não tem áudio para transcrever.")
    name = choose_model(meta.get("audio_duration") or meta.get("duration"), model)
    device, ctype = "cpu", "int8"
    try:
        ct2 = require_module("ctranslate2", "ctranslate2", "detectar GPU")
        if ct2.get_cuda_device_count() > 0:
            device, ctype = "cuda", "float16"
    except VeditError:
        pass
    info(
        f"Transcrevendo com o modelo '{name}' ({device}/{ctype}). "
        "Na primeira vez o modelo é baixado (pode demorar)."
    )
    audio = decode_audio(media)
    wm = fw.WhisperModel(name, device=device, compute_type=ctype)
    segments, ti = wm.transcribe(
        audio,
        language=lang,
        word_timestamps=True,
        condition_on_previous_text=False,
        vad_filter=vad,
    )
    words = []
    for seg in segments:
        for w in seg.words or []:
            txt = w.word.strip()
            if txt and not math.isnan(w.start):
                words.append({"w": txt, "t": round(float(w.start), 3), "e": round(float(w.end), 3)})
    words = refine_starts(words, audio)
    data = {
        "language": getattr(ti, "language", lang),
        "duration": round(meta.get("duration") or len(audio) / SR, 3),
        "words": words,
    }
    ensure_parent(output)
    Path(output).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return {"output": str(output), "words": len(words), "model": name, "language": data["language"]}
