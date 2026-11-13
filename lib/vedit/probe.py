"""Media probing: real frame rate, rotation, HDR, audio stats."""

from __future__ import annotations

import math
import operator
import subprocess
from array import array

from .util import (
    ffmpeg_path,
    measure_loudness,
    parse_rate,
    run_ffprobe_json,
)

HDR_TRANSFERS = ("arib-std-b67", "smpte2084")


def _rotation(stream: dict) -> int:
    rot = None
    for sd in stream.get("side_data_list") or []:
        if "rotation" in sd:
            rot = sd["rotation"]
    if rot is None:
        tag = (stream.get("tags") or {}).get("rotate")
        if tag is not None:
            try:
                rot = float(tag)
            except ValueError:
                rot = None
    return int(round(rot)) % 360 if rot is not None else 0


def _rational(avg, nominal, fallback: float) -> str:
    """Exact frame rate as ffprobe reports it ('30000/1001'), snapped to NTSC when approximate."""
    from .edl import fps_fraction, fps_str

    for cand in (avg, nominal):
        if cand and parse_rate(cand) > 0:
            return fps_str(fps_fraction(cand))
    return fps_str(fps_fraction(fallback)) if fallback else "30"


def lr_correlation(path, seconds: float = 120.0) -> float | None:
    """Pearson-like correlation between left and right channels (first ``seconds``)."""
    cmd = [
        ffmpeg_path(), "-hide_banner", "-nostdin", "-v", "error", "-t", str(seconds),
        "-i", str(path), "-vn", "-ac", "2", "-ar", "8000", "-f", "s16le", "-",
    ]  # fmt: skip
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0 or len(p.stdout) < 64:
        return None
    a = array("h")
    a.frombytes(p.stdout[: len(p.stdout) // 4 * 4])
    left, right = a[0::2], a[1::2]
    sxy = sum(map(operator.mul, left, right))
    sxx = sum(map(operator.mul, left, left))
    syy = sum(map(operator.mul, right, right))
    if sxx == 0 or syy == 0:
        return None
    return round(sxy / math.sqrt(sxx * syy), 4)


def probe(path, audio_analysis: bool = True, count_frames: bool = False) -> dict:
    extra = ["-show_format", "-show_streams"]
    if count_frames:
        extra.append("-count_frames")
    data = run_ffprobe_json(path, *extra)
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    vs = next(
        (
            s for s in streams
            if s.get("codec_type") == "video"
            and not (s.get("disposition") or {}).get("attached_pic")
        ),
        None,
    )  # fmt: skip
    aus = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(fmt.get("duration") or 0) or None
    out: dict = {
        "path": str(path),
        "format": fmt.get("format_name"),
        "duration": duration,
        "size_bytes": int(fmt.get("size") or 0),
        "has_video": vs is not None,
        "has_audio": aus is not None,
    }
    if vs:
        avg = parse_rate(vs.get("avg_frame_rate"))
        nominal = parse_rate(vs.get("r_frame_rate"))
        nb = vs.get("nb_read_frames") if count_frames else vs.get("nb_frames")
        nb_frames = int(nb) if nb and str(nb).isdigit() else None
        vdur = float(vs.get("duration") or 0) or duration
        estimated = False
        if nb_frames is None and vdur and (avg or nominal):
            nb_frames = int(round(vdur * (avg or nominal)))
            estimated = True
        if not avg and nb_frames and vdur:
            avg = nb_frames / vdur
        rot = _rotation(vs)
        w, h = int(vs.get("width", 0)), int(vs.get("height", 0))
        if rot in (90, 270):
            w, h = h, w
        trc = vs.get("color_transfer")
        out.update(
            {
                "width": w,
                "height": h,
                "coded_width": int(vs.get("width", 0)),
                "coded_height": int(vs.get("height", 0)),
                "rotation": rot,
                "avg_frame_rate": round(avg, 4),
                "r_frame_rate": round(nominal, 4),
                "fps": round(avg or nominal, 4),
                "fps_rational": _rational(vs.get("avg_frame_rate"), vs.get("r_frame_rate"), avg or nominal),
                "variable_frame_rate": bool(avg and nominal and abs(avg - nominal) / avg > 0.02),
                "nb_frames": nb_frames,
                "nb_frames_estimated": estimated,
                "video_duration": vdur,
                "codec": vs.get("codec_name"),
                "profile": vs.get("profile"),
                "pix_fmt": vs.get("pix_fmt"),
                "color_space": vs.get("color_space"),
                "color_transfer": trc,
                "color_primaries": vs.get("color_primaries"),
                "hdr": trc in HDR_TRANSFERS,
                "video_bit_rate": int(vs.get("bit_rate") or 0) or None,
            }
        )
    if aus:
        adur = float(aus.get("duration") or 0) or duration
        out.update(
            {
                "audio_codec": aus.get("codec_name"),
                "audio_channels": int(aus.get("channels", 0)),
                "audio_sample_rate": int(aus.get("sample_rate", 0) or 0),
                "audio_duration": adur,
                "audio_bit_rate": int(aus.get("bit_rate") or 0) or None,
            }
        )
        if audio_analysis:
            out["lr_correlation"] = lr_correlation(path) if out["audio_channels"] >= 2 else None
            try:
                m = measure_loudness(path)
                out["integrated_lufs"] = m["integrated_lufs"]
                out["true_peak_dbtp"] = m["true_peak_dbtp"]
                out["lra"] = m["lra"]
            except Exception:  # noqa: BLE001 - analysis is best effort
                out["integrated_lufs"] = None
    return out
