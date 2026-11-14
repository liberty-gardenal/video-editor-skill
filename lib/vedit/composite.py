"""Composite: transparent motion track over a base video, subtitles on top, optional SFX mix."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from .burn import _quote_filter_value
from .probe import probe
from .util import VeditError, ensure_parent, has_filter, info, log_path_for, run_ffmpeg


def composite(
    video, overlay, output, subs=None, fontsdir: str | None = None, sfx=None, sfx_gain: float = 0.0
) -> dict:
    base = probe(video, audio_analysis=False)
    ov = probe(overlay, audio_analysis=False)
    if not base.get("has_video"):
        raise VeditError("O arquivo de --video não tem vídeo.")
    if not ov.get("has_video"):
        raise VeditError("O arquivo de --overlay não tem vídeo.")
    if not str(ov.get("pix_fmt") or "").startswith("yuva"):
        raise VeditError(
            f"O overlay precisa ter canal alpha (pix_fmt yuva*), mas é '{ov.get('pix_fmt')}'. "
            "Renderize o motion transparente (ProRes 4444 ou VP9 com alpha)."
        )
    if (base["width"], base["height"]) != (ov["width"], ov["height"]):
        raise VeditError(
            f"Resolução diferente: vídeo {base['width']}x{base['height']}, overlay {ov['width']}x{ov['height']}."
        )
    bdur = base.get("video_duration") or base.get("duration") or 0
    odur = ov.get("video_duration") or ov.get("duration") or 0
    frame = 1 / (base.get("fps") or 30)
    if bdur and odur and abs(bdur - odur) > frame:
        info(f"Aviso: o overlay dura {odur:.2f}s e o vídeo {bdur:.2f}s (diferença maior que 1 quadro).")
    if subs and not (has_filter("ass") or has_filter("subtitles")):
        raise VeditError("Este ffmpeg não tem libass; rode `vedit doctor` para ver como instalar.")
    if fontsdir and not os.path.isdir(fontsdir):
        raise VeditError(f"--fontsdir não é uma pasta: {fontsdir}")
    if sfx and not probe(sfx, audio_analysis=False).get("has_audio"):
        raise VeditError("O arquivo de --sfx não tem áudio.")
    if sfx and not base.get("has_audio"):
        raise VeditError("O vídeo base não tem áudio para misturar com o --sfx.")
    ensure_parent(output)
    log = log_path_for(output, "composite")
    Path(log).write_text("", encoding="utf-8")
    mov = Path(output).suffix.lower() == ".mov"
    vf = "[1:v]format=yuva420p[o];[0:v][o]overlay=0:0:format=auto"
    with tempfile.TemporaryDirectory() as td:
        if subs:
            shutil.copy(subs, Path(td) / "leg.ass")
            vf += ",subtitles=leg.ass"
            if fontsdir:
                vf += f":fontsdir={_quote_filter_value(os.path.abspath(fontsdir))}"
        g = vf + ",format=yuv420p[v]"
        args = ["-y", "-i", os.path.abspath(video), "-i", os.path.abspath(overlay)]
        if sfx:
            args += ["-i", os.path.abspath(sfx)]
            sfx_chain = f"[2:a]volume={sfx_gain}dB[s];" if sfx_gain else ""
            s_lbl = "[s]" if sfx_gain else "[2:a]"
            g += f";{sfx_chain}[0:a]{s_lbl}amix=inputs=2:normalize=0:duration=first[a]"
            amap = "[a]"
        else:
            amap = "0:a?"
        acodec = ["-c:a", "pcm_s16le"] if mov else ["-c:a", "aac", "-ar", "48000", "-b:a", "192k"]
        args += ["-filter_complex", g, "-map", "[v]", "-map", amap]
        if bdur:
            args += ["-t", f"{bdur:.6f}"]
        args += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", *acodec]
        if not mov:
            args += ["-movflags", "+faststart"]
        run_ffmpeg([*args, os.path.abspath(output)], log_path=log, cwd=td)
    out = probe(output, audio_analysis=False)
    return {"output": str(output), "duration": out.get("video_duration"), "subs": bool(subs), "sfx": bool(sfx)}
