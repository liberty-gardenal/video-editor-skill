"""Audio tools: loudness, master, mix, silences, edges."""

from __future__ import annotations

import json
import math
import re
import subprocess
from array import array
from pathlib import Path

from .probe import probe
from .util import (
    VeditError,
    ensure_parent,
    ffmpeg_path,
    log_path_for,
    measure_loudness,
    run_ffmpeg,
)


def _loudnorm_json(text: str) -> dict:
    m = list(re.finditer(r"\{[^{}]*\"input_i\"[^{}]*\}", text, re.S))
    if not m:
        raise VeditError("Não consegui ler a medição do loudnorm (a mídia tem áudio?).")
    return json.loads(m[-1].group(0))


def exact_len_filter(dur: float) -> str:
    """Audio filter that pads/trims to exactly ``dur`` seconds."""
    return f"apad=whole_dur={dur:.6f},atrim=end={dur:.6f},asetpts=PTS-STARTPTS"


def extract_audio(video, output, start: float | None = None, end: float | None = None) -> dict:
    """Write the audio track as 48 kHz PCM, keeping the channel layout of the source."""
    meta = probe(video, audio_analysis=False)
    if not meta.get("has_audio"):
        raise VeditError("A mídia não tem trilha de áudio.")
    if start is not None and end is not None and end <= start:
        raise VeditError("--end deve ser maior que --start.")
    ensure_parent(output)
    log = log_path_for(output, "extract")
    Path(log).write_text("", encoding="utf-8")
    args: list = ["-y"]
    if start:
        args += ["-ss", f"{start:.6f}"]
    if end is not None:
        args += ["-t", f"{end - (start or 0):.6f}"]
    args += ["-i", video, "-vn", "-map", "0:a:0", "-ar", "48000", "-c:a", "pcm_s24le", "-f", "wav", output]
    run_ffmpeg(args, log_path=log)
    out = probe(output, audio_analysis=False)
    return {
        "output": str(output),
        "duration": out.get("audio_duration") or out.get("duration"),
        "channels": out.get("audio_channels"),
        "sample_rate": out.get("audio_sample_rate"),
    }


def mux(video, audio, output) -> dict:
    """Video stream copied; audio re-encoded to AAC 48 kHz 192k, padded/trimmed to the video length."""
    vm = probe(video, audio_analysis=False)
    if not vm.get("has_video"):
        raise VeditError("O arquivo de --video não tem vídeo.")
    am = probe(audio, audio_analysis=False)
    if not am.get("has_audio"):
        raise VeditError("O arquivo de --audio não tem áudio.")
    dur = vm.get("video_duration") or vm.get("duration")
    if not dur:
        raise VeditError("Não consegui determinar a duração do vídeo.")
    ensure_parent(output)
    log = log_path_for(output, "mux")
    Path(log).write_text("", encoding="utf-8")
    g = f"[1:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,{exact_len_filter(dur)}[a]"
    run_ffmpeg(
        ["-y", "-i", video, "-i", audio, "-filter_complex", g, "-map", "0:v:0", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-ac", "2",
         "-t", f"{dur:.6f}", "-movflags", "+faststart", output],
        log_path=log,
    )  # fmt: skip
    out = probe(output, audio_analysis=False)
    return {
        "output": str(output),
        "duration": out.get("video_duration"),
        "audio_duration": out.get("audio_duration"),
    }


def master(video, output, lufs: float = -14.0, tp: float = -1.5, lra: float = 11.0) -> dict:
    meta = probe(video, audio_analysis=False)
    if not meta.get("has_audio"):
        raise VeditError("A mídia não tem trilha de áudio para masterizar.")
    ensure_parent(output)
    log = log_path_for(output, "master")
    Path(log).write_text("", encoding="utf-8")
    p1 = run_ffmpeg(
        ["-i", video, "-vn", "-af", f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:print_format=json",
         "-f", "null", "-"],
        log_path=log,
    )  # fmt: skip
    m = _loudnorm_json(p1.stderr_text)  # type: ignore[attr-defined]
    if m["input_i"] in ("-inf", "inf"):
        raise VeditError("O áudio é silencioso; não há o que normalizar.")
    af = (
        f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
        f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
        f":offset={m['target_offset']}:linear=true:print_format=summary,aresample=48000"
    )
    # Audio must end exactly where the video ends (loudnorm and AAC both add tail samples).
    ref = (meta.get("video_duration") if meta["has_video"] else meta.get("audio_duration")) or meta["duration"]
    af += f",{exact_len_filter(ref)}"
    args = ["-y", "-i", video, "-map", "0:v?" if meta["has_video"] else "0:a"]
    if meta["has_video"]:
        args += ["-map", "0:a:0", "-c:v", "copy"]
    args += ["-af", af, "-ar", "48000", "-t", f"{ref:.6f}"]
    if str(output).lower().endswith(".wav"):
        args += ["-c:a", "pcm_s24le"]
    else:
        args += ["-c:a", "aac", "-b:a", "192k"]
        if meta["has_video"]:
            args += ["-movflags", "+faststart"]
    run_ffmpeg([*args, output], log_path=log)
    after = measure_loudness(output)
    return {
        "output": str(output),
        "before": {"lufs": float(m["input_i"]), "true_peak": float(m["input_tp"])},
        "after": {"lufs": after["integrated_lufs"], "true_peak": after["true_peak_dbtp"]},
        "target": {"lufs": lufs, "true_peak": tp},
    }


def mix(
    voice, music, output, music_lufs: float = -27.0, duck: bool = False, voice_lufs: float | None = None
) -> dict:
    vmeta = probe(voice, audio_analysis=False)
    if not vmeta.get("has_audio"):
        raise VeditError("A voz não tem áudio.")
    dur = vmeta["audio_duration"] or vmeta["duration"]
    if not dur:
        raise VeditError("Não consegui determinar a duração da voz.")
    mloud = measure_loudness(music)["integrated_lufs"]
    if mloud is None or math.isinf(mloud):
        raise VeditError("A música é silenciosa.")
    gain = music_lufs - mloud
    ensure_parent(output)
    log = log_path_for(output, "mix")
    Path(log).write_text("", encoding="utf-8")
    fmt = "aformat=sample_fmts=fltp:channel_layouts=stereo"
    voice_chain = f"[0:a]aresample=48000,{fmt},apad=whole_dur={dur:.6f},atrim=end={dur:.6f}"
    music_chain = (
        f"[1:a]aresample=48000,{fmt},volume={gain:.3f}dB,"
        f"apad=whole_dur={dur:.6f},atrim=end={dur:.6f},asetpts=PTS-STARTPTS"
    )
    if duck:
        g = (
            f"{voice_chain},asplit=2[vo][vk];{music_chain}[mu];"
            "[mu][vk]sidechaincompress=threshold=0.02:ratio=4:attack=15:release=300[md];"
            "[vo][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,aresample=48000[out]"
        )
    else:
        g = (
            f"{voice_chain}[vo];{music_chain}[mu];"
            "[vo][mu]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,aresample=48000[out]"
        )
    codec = ["-c:a", "pcm_s24le"] if str(output).lower().endswith(".wav") else ["-c:a", "aac", "-b:a", "192k"]
    run_ffmpeg(
        ["-y", "-i", voice, "-stream_loop", "-1", "-i", music, "-filter_complex", g,
         "-map", "[out]", "-ar", "48000", "-t", f"{dur:.6f}", *codec, output],
        log_path=log,
    )  # fmt: skip
    return {"output": str(output), "duration": dur, "music_gain_db": round(gain, 2), "ducking": duck}


def silences(media, noise: float = -35.0, min_dur: float = 0.25, start=None, end=None) -> dict:
    args: list = []
    if start is not None:
        args += ["-ss", start]
    if end is not None:
        args += ["-to", end]
    args += ["-i", media, "-vn", "-af", f"silencedetect=noise={noise}dB:d={min_dur}", "-f", "null", "-"]
    p = run_ffmpeg(args)
    text = p.stderr_text  # type: ignore[attr-defined]
    off = float(start or 0)
    res, cur = [], None
    for line in text.splitlines():
        m = re.search(r"silence_start:\s*(-?[\d.]+)", line)
        if m:
            cur = max(float(m.group(1)), 0.0) + off
            continue
        m = re.search(r"silence_end:\s*(-?[\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)", line)
        if m:
            e = float(m.group(1)) + off
            res.append({"start": round(cur if cur is not None else off, 3), "end": round(e, 3),
                        "duration": round(float(m.group(2)), 3)})  # fmt: skip
            cur = None
    if cur is not None:
        total = probe(media, audio_analysis=False)["duration"] or cur
        e = float(end) if end is not None else total
        res.append({"start": round(cur, 3), "end": round(e, 3), "duration": round(e - cur, 3)})
    return {"noise_db": noise, "min_duration": min_dur, "silences": res}


def _pcm(path, start: float, dur: float, sr: int = 16000) -> array:
    cmd = [
        ffmpeg_path(), "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{max(start, 0):.4f}",
        "-t", f"{dur:.4f}", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-",
    ]  # fmt: skip
    p = subprocess.run(cmd, capture_output=True)
    a = array("h")
    a.frombytes(p.stdout[: len(p.stdout) // 2 * 2])
    return a


def rms_db(samples) -> float:
    if not len(samples):
        return -120.0
    ms = sum(s * s for s in samples) / len(samples)
    return 10 * math.log10(ms / (32768.0**2)) if ms > 0 else -120.0


def edges(clip, thr: float = -35.0, ms: int = 80) -> dict:
    meta = probe(clip, audio_analysis=False)
    if not meta.get("has_audio"):
        raise VeditError("O clipe não tem áudio.")
    dur = meta["audio_duration"] or meta["duration"]
    sr, n = 16000, int(16000 * ms / 1000)
    head = _pcm(clip, 0, ms / 1000, sr)[:n]
    tail_all = _pcm(clip, max(dur - 0.5, 0), 0.6, sr)
    tail = tail_all[-n:]
    h, t = rms_db(head), rms_db(tail)
    res = {
        "threshold_db": thr,
        "window_ms": ms,
        "start": {"rms_db": round(h, 1), "ok": h <= thr},
        "end": {"rms_db": round(t, 1), "ok": t <= thr},
    }
    res["ok"] = res["start"]["ok"] and res["end"]["ok"]
    msgs = []
    if not res["start"]["ok"]:
        msgs.append(f"Início com som alto ({h:.1f} dB > {thr} dB): provável palavra truncada no começo.")
    if not res["end"]["ok"]:
        msgs.append(f"Fim com som alto ({t:.1f} dB > {thr} dB): provável palavra truncada no fim.")
    res["message"] = " ".join(msgs) if msgs else "Início e fim caem em silêncio: OK."
    return res


def loudness(media) -> dict:
    m = measure_loudness(media)
    return {
        "integrated_lufs": m["integrated_lufs"],
        "true_peak_dbtp": m["true_peak_dbtp"],
        "lra": m["lra"],
    }
