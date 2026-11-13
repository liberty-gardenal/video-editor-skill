"""Render an EDL: frame-exact re-encoding cut with vertical layouts."""

from __future__ import annotations

from pathlib import Path

from . import edl as edlmod
from . import overlay
from .probe import probe
from .util import (
    VeditError,
    ensure_parent,
    has_filter,
    info,
    log_path_for,
    run_ffmpeg,
)

FADE = 0.010  # audio micro-fade at each join, seconds


def even(v: float) -> int:
    return max(2, int(v) // 2 * 2)


def cover_crop(W, H, OW, OH, crop_x, zoom=1.0):
    """Return (cw, ch, x, y): 9:16 crop window inside WxH, never leaving the frame."""
    target = OW / OH
    if W / H >= target:
        ch, cw = H, even(H * target)
    else:
        cw, ch = W, even(W / target)
    cw, ch = min(cw, even(W)), min(ch, even(H))
    if zoom and zoom > 1:
        cw, ch = even(cw / zoom), even(ch / zoom)
    cx = min(max(float(crop_x), 0.0), 1.0) * W
    x = min(max(int(round(cx - cw / 2)), 0), W - cw)
    y = (H - ch) // 2
    return cw, ch, x // 2 * 2, y // 2 * 2


def split_geometry(W, H, OW, OH, crop_x, zoom=1.0):
    """Return (top_h, bottom_h, (cw, ch, x, y)) for the split layout."""
    if W <= H:
        raise VeditError(
            "O layout 'split' exige fonte horizontal (largura maior que a altura); "
            f"esta fonte já é vertical ({W}x{H}). Use 'cover' ou 'fit'."
        )
    top_h = even(round(OW * H / W))
    bot_h = OH - top_h
    if bot_h < 100:
        raise VeditError("Sobra pouco espaço embaixo para o crop do layout 'split'.")
    cw, ch, x, y = cover_crop(W, H, OW, bot_h, crop_x, zoom)
    return top_h, bot_h, (cw, ch, x, y)


def fit_geometry(W, H, OW, OH):
    if W / H >= OW / OH:
        return OW, even(OW * H / W)
    return even(OH * W / H), OH


def hdr_chain(transfer: str | None) -> tuple[str, str]:
    """Return (filter chain, human note) converting HDR to SDR bt709."""
    if has_filter("zscale"):
        tin = transfer or "smpte2084"
        chain = (
            f"zscale=tin={tin}:pin=bt2020:min=bt2020nc:t=linear:npl=100,"
            "format=gbrpf32le,tonemap=tonemap=hable:desat=0,"
            "zscale=p=bt709:t=bt709:m=bt709:r=tv,format=yuv420p"
        )
        return chain, "HDR→SDR com zscale+tonemap"
    chain = "setparams=color_trc=bt709,colorspace=all=bt709:iall=bt2020:fast=1,format=yuv420p"
    return chain, "HDR→SDR aproximado (filtro zscale ausente; usando colorspace)"


UP = 2  # upscale factor before zoompan: keeps the per-frame crop steps below one output pixel


def _crop_scale(cw, ch, x, y, w, h):
    return f"crop={cw}:{ch}:{x}:{y},scale={w}:{h}:flags=lanczos,setsar=1"


def _ramp_chain(W, H, OW, rh, cx, z0, z1, off, n, fps_s):
    """Smooth linear zoom: crop the zoom-1 window, upscale, then zoompan with per-frame z."""
    cw, ch, x, y = cover_crop(W, H, OW, rh, cx, 1.0)
    uw, uh = OW * UP, rh * UP
    cxb = (min(max(float(cx), 0.0), 1.0) * W - x) * uw / cw
    z = f"{z0:.5f}+({z1 - z0:.5f})*({off}+on)/{max(n - 1, 1)}"
    px = f"min(max({cxb:.3f}-iw/zoom/2,0),iw-iw/zoom)"
    return (
        f"crop={cw}:{ch}:{x}:{y},scale={uw}:{uh}:flags=lanczos,"
        f"zoompan=z='{z}':x='{px}':y='(ih-ih/zoom)/2':d=1:s={OW}x{rh}:fps={fps_s},setsar=1"
    )


def _region_chain(W, H, OW, rh, cx, zoom, off, n, fps_s):
    z0, z1 = zoom
    if abs(z1 - z0) > 1e-9:
        return _ramp_chain(W, H, OW, rh, cx, z0, z1, off, n, fps_s)
    cw, ch, x, y = cover_crop(W, H, OW, rh, cx, z0)
    return _crop_scale(cw, ch, x, y, OW, rh)


def lower_geometry(OW, OH, split_at, feather):
    """Return (speaker region top y, speaker region height) for the lower layout.

    The speaker region starts ``feather`` px above ``split_at`` so a ``top`` overlay's feathered
    edge blends into the speaker instead of into the blurred filler.
    """
    from .overlay import feather_px

    sy = even(round(split_at * OH))
    top = max(sy - feather_px(feather, OH), 0)
    return top, OH - top


def _blur_fill(W, H, OW, OH, cx):
    """Blurred, darkened full-frame copy of the shot (cheap: blur at 1/6 scale)."""
    cw, ch, x, y = cover_crop(W, H, OW, OH, cx, 1.0)
    sw, sh = even(OW / 6), even(OH / 6)
    return (
        f"crop={cw}:{ch}:{x}:{y},scale={sw}:{sh},boxblur=4:2,"
        f"scale={OW}:{OH}:flags=bicubic,eq=brightness=-0.22:saturation=0.85,setsar=1"
    )


def _layout_graph(label_in, label_out, layout, W, H, OW, OH, kfs, n, zoom, uid, fps_s="30", split_at=0.45):
    """Filter graph text for one clip's video after trim; kfs = [(frame, crop_x)], zoom = (z0, z1)."""
    bounds = [f for f, _ in kfs] + [n]
    pieces = []
    if layout == "fit":
        fw, fh = fit_geometry(W, H, OW, OH)
        return (
            f"[{label_in}]split[{uid}bg][{uid}fg];"
            f"[{uid}bg]scale={OW}:{OH}:force_original_aspect_ratio=increase,"
            f"crop={OW}:{OH},boxblur=24:6,setsar=1[{uid}bgb];"
            f"[{uid}fg]scale={fw}:{fh}:flags=lanczos,setsar=1[{uid}fgs];"
            f"[{uid}bgb][{uid}fgs]overlay=(W-w)/2:(H-h)/2:shortest=1[{label_out}]"
        )
    k = len(kfs)
    parts = []
    split_labels = "".join(f"[{uid}s{i}]" for i in range(k))
    if k > 1:
        parts.append(f"[{label_in}]split={k}{split_labels}")
    for i, (_, cx) in enumerate(kfs):
        src = f"{uid}s{i}" if k > 1 else label_in
        seg_out = f"{uid}p{i}"
        trim = ""
        if k > 1:
            trim = f"trim=start_frame={bounds[i]}:end_frame={bounds[i + 1]},setpts=PTS-STARTPTS,"
        if layout == "cover":
            chain = _region_chain(W, H, OW, OH, cx, zoom, bounds[i], n, fps_s)
            parts.append(f"[{src}]{trim}{chain}[{seg_out}]")
        elif layout == "lower":
            ly, lh = lower_geometry(OW, OH, split_at, edlmod.FEATHER_DEFAULT)
            chain = _region_chain(W, H, OW, lh, cx, zoom, bounds[i], n, fps_s)
            parts.append(
                f"[{src}]{trim}split[{seg_out}a][{seg_out}b];"
                f"[{seg_out}a]{_blur_fill(W, H, OW, OH, cx)}[{seg_out}bg];"
                f"[{seg_out}b]{chain}[{seg_out}fg];"
                f"[{seg_out}bg][{seg_out}fg]overlay=0:{ly}:shortest=1[{seg_out}]"
            )
        else:  # split
            top_h, bot_h, _ = split_geometry(W, H, OW, OH, cx, zoom[0])
            chain = _region_chain(W, H, OW, bot_h, cx, zoom, bounds[i], n, fps_s)
            parts.append(
                f"[{src}]{trim}split[{seg_out}t][{seg_out}b];"
                f"[{seg_out}t]scale={OW}:{top_h}:flags=lanczos,setsar=1[{seg_out}ts];"
                f"[{seg_out}b]{chain}[{seg_out}bs];"
                f"[{seg_out}ts][{seg_out}bs]vstack=inputs=2[{seg_out}]"
            )
        pieces.append(f"[{seg_out}]")
    if k > 1:
        parts.append("".join(pieces) + f"concat=n={k}:v=1:a=0[{label_out}]")
    else:
        parts[-1] = parts[-1][: parts[-1].rfind("[")] + f"[{label_out}]"
    return ";".join(parts)


def atempo_chain(speed: float) -> str:
    """atempo only accepts 0.5-2.0 per stage; chain stages for the rest of the 0.25-4.0 range."""
    parts, s = [], float(speed)
    while s > 2.0 + 1e-9:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5 - 1e-9:
        parts.append("atempo=0.5")
        s *= 2.0
    parts.append(f"atempo={s:.6f}")
    return ",".join(parts)


def _clip_info(path: str, cache: dict) -> dict:
    if path not in cache:
        try:
            meta = probe(path, audio_analysis=False)
        except VeditError as exc:
            if edlmod.is_image(path):
                raise VeditError(
                    f"Não consegui abrir a imagem '{Path(path).name}'. Este ffmpeg talvez não decodifique "
                    "o formato (ex.: HEIC); converta para jpg ou png."
                ) from exc
            raise
        if not meta.get("has_video"):
            raise VeditError(f"A fonte '{Path(path).name}' não tem vídeo.")
        if edlmod.is_image(path):
            meta = {**meta, "has_audio": False, "duration": None, "video_duration": None, "hdr": False}
        cache[path] = meta
    return cache[path]


def build_command(edl: dict, edl_path, output: str, preview: bool):
    """Return (ffmpeg args, summary)."""
    frac = edlmod.resolve_fps_fraction(edl, edl_path)
    fps = float(frac)
    fps_s = edlmod.fps_str(frac)
    out_cfg = edl.get("output") or {}
    OW, OH = int(out_cfg.get("width", 1080)), int(out_cfg.get("height", 1920))
    if preview:
        OW, OH = 540, 960
    OW, OH = even(OW), even(OH)
    tl = edlmod.timeline(edl, fps)

    cache: dict = {}
    inputs: list = []
    graphs: list[str] = []
    labels: list[str] = []
    hdr_notes: list[str] = []
    sources: set[str] = set()
    for t in tl:
        c = t["clip"]
        i, n, d = t["index"], t["frames"], t["duration"]
        src = edlmod.resolve_source(edl, edl_path, c)
        sources.add(src)
        info_ = _clip_info(src, cache)
        still = edlmod.is_image(src)
        W, H = info_["width"], info_["height"]
        if not still:
            sdur = info_.get("video_duration") or info_.get("duration") or 0
            if sdur and t["in"] >= sdur:
                raise VeditError(
                    f"Clipe '{t['id']}': 'in' ({t['in']:.2f}s) está depois do fim da fonte ({sdur:.2f}s)."
                )
            if sdur and t["out"] > sdur + 1.0 / fps:
                raise VeditError(
                    f"Clipe '{t['id']}': 'out' ({t['out']:.2f}s) passa do fim da fonte ({sdur:.2f}s)."
                )
        layout = c.get("layout", "cover")
        zoom = edlmod.zoom_range(c, t["id"])
        speed = t["speed"]
        hdr_f = ""
        if info_.get("hdr"):
            hdr_f, note = hdr_chain(info_.get("color_transfer"))
            hdr_f += ","
            hdr_notes.append(note)
        if still:
            inputs += ["-loop", "1", "-framerate", fps_s, "-t", f"{d + 0.5:.6f}", "-i", src]
        else:
            inputs += ["-ss", f"{t['in']:.6f}", "-t", f"{t['src_duration'] + 0.5:.6f}", "-i", src]
        kfs = edlmod.keyframes(c.get("crop_x", 0.5), n, fps)
        vin = f"v{i}in"
        slow = f"setpts=PTS/{speed:.6f}," if abs(speed - 1.0) > 1e-9 else ""
        graphs.append(
            f"[{i}:v:0]setpts=PTS-STARTPTS,{slow}fps={fps_s},"
            f"tpad=stop_mode=clone:stop_duration=0.5,trim=end_frame={n},"
            f"setpts=PTS-STARTPTS,{hdr_f}setsar=1[{vin}]"
        )
        graphs.append(_layout_graph(vin, f"v{i}l", layout, W, H, OW, OH, kfs, n, zoom, f"c{i}", fps_s, edlmod.split_at(c)))
        graphs.append(f"[v{i}l]format=yuv420p,setsar=1[v{i}]")
        fade_st = max(d - FADE, 0)
        if info_.get("has_audio") and not still:
            tempo = atempo_chain(speed) + "," if abs(speed - 1.0) > 1e-9 else ""
            asrc = f"[{i}:a:0]asetpts=PTS-STARTPTS,{tempo}"
        else:
            asrc = "anullsrc=r=48000:cl=stereo,"
        graphs.append(
            f"{asrc}aresample=48000:first_pts=0,"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"apad=whole_dur={d:.6f},atrim=end={d:.6f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d={FADE},afade=t=out:st={fade_st:.6f}:d={FADE}[a{i}]"
        )
        labels.append(f"[v{i}][a{i}]")
    total_frames = sum(t["frames"] for t in tl)
    total_dur = total_frames / fps
    ovs = edlmod.check_overlays_timeline(edl, tl, fps)
    if ovs:
        ov_inputs, ov_prep, ov_graphs = overlay.build(
            edl, edl_path, ovs, len(tl), OW, OH, frac, "vcat", "vout", cache
        )
        inputs += ov_inputs
        graphs[:0] = ov_prep  # overlay sources first: see overlay.build
        graphs.append("".join(labels) + f"concat=n={len(tl)}:v=1:a=1[vcat][acat]")
        graphs += ov_graphs
    else:
        graphs.append("".join(labels) + f"concat=n={len(tl)}:v=1:a=1[vout][acat]")
    # Audio length is forced to the exact video length (concat rounding, per-clip padding).
    graphs.append(f"[acat]apad=whole_dur={total_dur:.6f},atrim=end={total_dur:.6f},asetpts=PTS-STARTPTS[aout]")
    crf, preset = ("28", "veryfast") if preview else ("18", "medium")
    args = [
        "-y", *inputs,
        "-filter_complex", ";".join(graphs),
        "-map", "[vout]", "-map", "[aout]",
        "-r", fps_s, "-t", f"{total_dur:.6f}",
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-crf", crf, "-preset", preset,
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-ac", "2",
        "-movflags", "+faststart",
        output,
    ]  # fmt: skip
    summary = {
        "output": output,
        "width": OW,
        "height": OH,
        "fps": fps,
        "clips": len(tl),
        "frames": total_frames,
        "duration": total_dur,
        "sources": len(sources),
        "hdr_converted": bool(hdr_notes),
        "hdr_note": hdr_notes[0] if hdr_notes else None,
        "preview": preview,
        "overlays": len(ovs),
        "warnings": edlmod.edl_warnings(edl, tl, fps),
    }
    return args, summary


def render(edl_path, output, preview: bool = False) -> dict:
    edl = edlmod.load_edl(edl_path)
    ensure_parent(output)
    args, summary = build_command(edl, edl_path, str(output), preview)
    log = log_path_for(output)
    Path(log).write_text("", encoding="utf-8")
    info(
        f"Renderizando {summary['clips']} clipe(s), {summary['duration']:.2f}s "
        f"({summary['width']}x{summary['height']}"
        f"{', prévia' if preview else ''}). Log: {log}"
    )
    for w in summary["warnings"]:
        info(f"AVISO: {w}")
    if summary["hdr_note"]:
        info(f"Fonte HDR detectada: {summary['hdr_note']}")
    run_ffmpeg(args, log_path=log)
    return summary
