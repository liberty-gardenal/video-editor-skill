"""Final QC for a rendered vertical video."""

from __future__ import annotations

import math
import os
import re
import struct

from . import platforms as P
from .audio import edges
from .probe import probe
from .util import VeditError, measure_loudness, run_ffmpeg

PASS, WARN, FAIL = "ok", "aviso", "falha"
LABEL = {PASS: "[OK]    ", WARN: "[AVISO] ", FAIL: "[FALHA] "}


def mp4_atoms(path) -> list[tuple[str, int]]:
    """Top-level atoms as (type, offset). Raises ValueError for non-MP4 data."""
    atoms = []
    size_total = os.path.getsize(path)
    with open(path, "rb") as fh:
        pos = 0
        while pos + 8 <= size_total:
            fh.seek(pos)
            hdr = fh.read(8)
            size, kind = struct.unpack(">I4s", hdr)
            name = kind.decode("latin-1")
            if size == 1:
                size = struct.unpack(">Q", fh.read(8))[0]
            elif size == 0:
                size = size_total - pos
            if size < 8:
                raise ValueError("átomo inválido")
            atoms.append((name, pos))
            pos += size
    return atoms


def faststart_ok(path) -> bool | None:
    try:
        atoms = mp4_atoms(path)
    except (ValueError, struct.error, OSError):
        return None
    names = [a[0] for a in atoms]
    if "moov" not in names or "mdat" not in names:
        return None
    return names.index("moov") < names.index("mdat")


def _detect(path) -> dict:
    p = run_ffmpeg(
        ["-i", path, "-an", "-vf",
         "scale=270:-2,blackdetect=d=0.2:pix_th=0.10,freezedetect=n=0.003:d=1",
         "-f", "null", "-"],
    )  # fmt: skip
    t = p.stderr_text  # type: ignore[attr-defined]
    black = [
        (float(a), float(b), float(c))
        for a, b, c in re.findall(r"black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)", t)
    ]
    starts = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", t)]
    durs = [float(x) for x in re.findall(r"freeze_duration:\s*([\d.]+)", t)]
    freeze = list(zip(starts, durs, strict=False))
    if len(starts) > len(durs):  # freeze that lasts until the end of the file
        freeze.append((starts[-1], -1.0))
    return {"black": black, "freeze": freeze}


def verify(
    path, platform: str | None = None, source: str | None = None, strict_edges: bool = False
) -> dict:
    if platform is not None and platform not in P.PLATFORMS:
        raise VeditError(f"Plataforma desconhecida: {platform} ({', '.join(P.PLATFORMS)})")
    plat = P.PLATFORMS[platform or P.DEFAULT_PLATFORM]
    checks: list[dict] = []

    def add(cid, status, msg, value=None):
        checks.append({"id": cid, "status": status, "message": msg, "value": value})

    m = probe(path, audio_analysis=False)
    if not m.get("has_video"):
        raise VeditError("O arquivo não tem vídeo.")
    w, h = m["width"], m["height"]
    ratio_ok = abs(w / h - P.ASPECT[0] / P.ASPECT[1]) < 0.005
    if not ratio_ok:
        add("aspect", FAIL, f"Proporção {w}x{h} não é 9:16.", [w, h])
    elif w < P.MIN_WIDTH or h < P.MIN_HEIGHT:
        add("resolution", FAIL, f"Resolução {w}x{h} abaixo do mínimo {P.MIN_WIDTH}x{P.MIN_HEIGHT}.", [w, h])
    else:
        add("resolution", PASS, f"Resolução {w}x{h} (9:16).", [w, h])

    fps = m["fps"]
    if m.get("variable_frame_rate"):
        add("fps", WARN, f"Taxa de quadros variável (média {fps:.2f}, nominal {m['r_frame_rate']:.2f}).", fps)
    elif fps < 24 or fps > 60.5:
        add("fps", WARN, f"Taxa de quadros incomum: {fps:.2f} fps.", fps)
    else:
        add("fps", PASS, f"{fps:.2f} fps.", fps)

    if m["codec"] != "h264":
        add("codec", FAIL, f"Codec de vídeo '{m['codec']}' (esperado h264).", m["codec"])
    elif (m.get("profile") or "").lower() not in ("high", "main", "constrained baseline", "baseline"):
        add("codec", WARN, f"Perfil H.264 incomum: {m.get('profile')}.", m.get("profile"))
    else:
        add("codec", PASS, f"H.264 {m.get('profile')}.", m["codec"])
    if m["pix_fmt"] != "yuv420p":
        add("pix_fmt", FAIL, f"pix_fmt '{m['pix_fmt']}' (esperado yuv420p).", m["pix_fmt"])
    else:
        add("pix_fmt", PASS, "pix_fmt yuv420p.", m["pix_fmt"])
    if m.get("hdr"):
        add("hdr", FAIL, "O arquivo ainda é HDR; converta para SDR bt709.", m.get("color_transfer"))

    fs = faststart_ok(path)
    if fs is None:
        add("faststart", WARN, "Não consegui verificar o faststart (arquivo não é MP4?).")
    elif fs:
        add("faststart", PASS, "Faststart ok (moov antes de mdat).", True)
    else:
        add("faststart", FAIL, "Sem faststart: o átomo moov está depois do mdat.", False)

    dur = m.get("duration") or 0
    if dur < plat["min_s"]:
        add(
            "duration",
            FAIL,
            f"Duração {dur:.1f}s menor que o mínimo ({plat['min_s']}s) para {plat['label']}.",
            dur,
        )
    elif dur > plat["max_s"]:
        add(
            "duration",
            FAIL,
            f"Duração {dur:.1f}s maior que o limite ({plat['max_s']}s) para {plat['label']}.",
            dur,
        )
    elif dur > plat["soft_max_s"]:
        add(
            "duration",
            WARN,
            f"Duração {dur:.1f}s acima do recomendado ({plat['soft_max_s']}s) para {plat['label']}.",
            dur,
        )
    else:
        add("duration", PASS, f"Duração {dur:.1f}s dentro dos limites de {plat['label']}.", dur)
    size_mb = m["size_bytes"] / 1e6
    if size_mb > plat["max_mb"]:
        add("size", FAIL, f"Arquivo com {size_mb:.0f} MB (limite padrão {plat['max_mb']} MB).", size_mb)

    if not m.get("has_audio"):
        add("audio", FAIL, "O arquivo não tem áudio.")
    else:
        if m["audio_codec"] != "aac" or m["audio_sample_rate"] != 48000:
            add(
                "audio_format",
                WARN,
                f"Áudio {m['audio_codec']} {m['audio_sample_rate']} Hz (esperado AAC 48000 Hz).",
            )
        else:
            add("audio_format", PASS, "Áudio AAC 48 kHz.")
        vd, ad = m.get("video_duration") or 0, m.get("audio_duration") or 0
        if abs(vd - ad) > 0.080:
            add(
                "av_sync",
                FAIL,
                f"Duração de vídeo ({vd:.3f}s) e áudio ({ad:.3f}s) diferem em {abs(vd - ad) * 1000:.0f} ms.",
                [vd, ad],
            )
        else:
            add("av_sync", PASS, f"Vídeo e áudio com a mesma duração (Δ {abs(vd - ad) * 1000:.0f} ms).")
        loud = measure_loudness(path)
        li, tp = loud["integrated_lufs"], loud["true_peak_dbtp"]
        if li is None or math.isinf(li):
            add("lufs", FAIL, "O áudio é silencioso (não consegui medir a loudness).", li)
        else:
            dl = abs(li - P.TARGET_LUFS)
            if dl > 3:
                add("lufs", FAIL, f"Loudness {li:.1f} LUFS, longe do alvo {P.TARGET_LUFS:.0f} LUFS.", li)
            elif dl > 1:
                add("lufs", WARN, f"Loudness {li:.1f} LUFS (alvo {P.TARGET_LUFS:.0f} ±1).", li)
            else:
                add("lufs", PASS, f"Loudness {li:.1f} LUFS.", li)
        if tp is None or math.isinf(tp):
            add("true_peak", WARN, "Não consegui medir o true peak.", tp)
        elif tp > -1.0:
            add("true_peak", FAIL, f"True peak {tp:.1f} dBTP acima de -1,0 (risco de clipping).", tp)
        elif tp > P.TARGET_TP + 0.3:
            add("true_peak", WARN, f"True peak {tp:.1f} dBTP (alvo {P.TARGET_TP} dBTP).", tp)
        else:
            add("true_peak", PASS, f"True peak {tp:.1f} dBTP.", tp)
        ed = edges(path)
        if ed["ok"]:
            add("audio_edges", PASS, ed["message"], [ed["start"]["rms_db"], ed["end"]["rms_db"]])
        else:
            note = (
                " Música ou ambiente na borda é aceitável; palavra truncada não: "
                "ouça o início e o fim (`vedit edges`)."
            )
            add("audio_edges", FAIL if strict_edges else WARN, ed["message"] + note,
                [ed["start"]["rms_db"], ed["end"]["rms_db"]])  # fmt: skip

    det = _detect(str(path))
    long_black = [b for b in det["black"] if b[2] >= 1.0]
    if long_black:
        add(
            "black",
            FAIL,
            f"Quadros pretos por {long_black[0][2]:.1f}s a partir de {long_black[0][0]:.1f}s.",
            det["black"],
        )
    elif det["black"]:
        add(
            "black",
            WARN,
            f"{len(det['black'])} trecho(s) preto(s) curtos (primeiro em {det['black'][0][0]:.1f}s).",
            det["black"],
        )
    else:
        add("black", PASS, "Sem quadros pretos.")
    long_freeze = [f for f in det["freeze"] if f[1] < 0 or f[1] > 3.0]
    if long_freeze:
        add(
            "freeze",
            WARN,
            f"Imagem congelada por mais de 3 s (a partir de {long_freeze[0][0]:.1f}s).",
            det["freeze"],
        )
    else:
        add("freeze", PASS, "Sem congelamentos longos.")

    if source:
        if not os.path.exists(source):
            add("source", WARN, f"Fonte não encontrada: {source}")
        else:
            sd = probe(source, audio_analysis=False).get("duration") or 0
            if sd and dur > sd + 0.1:
                add("source", WARN, f"O corte ({dur:.1f}s) é mais longo que a fonte ({sd:.1f}s).")
            else:
                add("source", PASS, f"Fonte encontrada ({sd:.1f}s).")

    status = (
        FAIL
        if any(c["status"] == FAIL for c in checks)
        else (WARN if any(c["status"] == WARN for c in checks) else PASS)
    )
    return {"file": str(path), "platform": platform or P.DEFAULT_PLATFORM, "status": status, "checks": checks}


def format_report(res: dict) -> str:
    lines = [f"Verificação de {res['file']} (plataforma: {res['platform']})", ""]
    for c in res["checks"]:
        lines.append(f"{LABEL[c['status']]}{c['message']}")
    nf = sum(c["status"] == FAIL for c in res["checks"])
    nw = sum(c["status"] == WARN for c in res["checks"])
    lines += ["", {PASS: "RESULTADO: aprovado.", WARN: f"RESULTADO: aprovado com {nw} aviso(s).",
                   FAIL: f"RESULTADO: REPROVADO ({nf} falha(s), {nw} aviso(s))."}[res["status"]]]  # fmt: skip
    return "\n".join(lines)
