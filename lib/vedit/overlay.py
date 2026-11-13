"""Overlay layer (b-roll window, full-frame cutaway, proof card) added to the base timeline.

Everything is expressed as extra inputs plus filter-graph text appended to ``cut``'s graph, so the
base timeline and the overlays are encoded in a single pass (no extra lossy generation).
Overlays are video-only: the base audio is never touched.
"""

from __future__ import annotations

from fractions import Fraction

from . import edl as edlmod
from .util import VeditError

DIM = {"saturation": 0.35, "brightness": -0.2, "blur": 20}  # base look under a proof card
CARD_MAX_H = 0.9  # card never taller than this fraction of the frame


def feather_px(feather: float, OH: int) -> int:
    """Feather in output pixels (the EDL value is given at 1920 tall), even and >= 0."""
    return max(0, int(round(feather * OH / 1920.0)) // 2 * 2)


def card_size(W: int, H: int, OW: int, OH: int, width: float) -> tuple[int, int]:
    """Card size keeping the source aspect: ``width`` of the frame wide, capped in height."""
    from .cut import even

    cw = even(width * OW)
    ch = even(cw * H / W)
    if ch > CARD_MAX_H * OH:
        ch = even(CARD_MAX_H * OH)
        cw = even(ch * W / H)
    return cw, ch


def build(edl: dict, edl_path, ovs: list[dict], first_input: int, OW: int, OH: int, frac: Fraction,
          base_label: str, out_label: str, cache: dict) -> tuple[list, list[str], list[str]]:
    """Return (ffmpeg input args, overlay-source graphs, compositing graphs) for the snapped overlays.

    The source graphs must come *before* the base timeline's graphs in the filter script: with the
    base first, ffmpeg starves the overlay inputs and the overlays never show.
    """
    from .cut import _clip_info, _region_chain, even, hdr_chain

    fps = float(frac)
    fps_s = edlmod.fps_str(frac)
    inputs: list = []
    prep: list[str] = []
    graphs: list[str] = []
    prev = base_label
    for k, ov in enumerate(ovs):
        j = first_input + k
        lab = ov["label"]
        src = edlmod.resolve_path(ov["o"]["source"], edl_path)
        meta = _clip_info(src, cache)
        still = edlmod.is_image(src)
        W, H = meta["width"], meta["height"]
        n, s = ov["frames"], ov["start"]
        if not still:
            vdur = meta.get("video_duration") or meta.get("duration") or 0
            if vdur and ov["in"] >= vdur:
                raise VeditError(f"Overlay {lab}: 'in' ({ov['in']:g}s) está depois do fim da fonte ({vdur:.2f}s).")
            inputs += ["-ss", f"{ov['in']:.6f}", "-t", f"{ov['frames'] / fps + 0.5:.6f}", "-i", src]
        else:
            inputs += ["-loop", "1", "-framerate", fps_s, "-t", f"{n / fps + 0.5:.6f}", "-i", src]
        hdr_f = ""
        if meta.get("hdr"):
            hdr_f = hdr_chain(meta.get("color_transfer"))[0] + ","
        region = ov["region"]
        if region == "full":
            rw, rh = OW, OH
        elif region == "top":
            rw, rh = OW, even(round(ov["height"] * OH))
        else:
            rw, rh = card_size(W, H, OW, OH, ov["width"])
        shift = float(Fraction(s) / frac)
        chain = _region_chain(W, H, rw, rh, ov["crop_x"], ov["zoom"], 0, n, fps_s)
        tail = ""
        fe = feather_px(ov["feather"], OH) if region == "top" else 0
        if fe:
            tail = (
                ",format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':"
                f"a='255*clip(({rh}-Y-0.5)/{fe},0,1)'"
            )
        prep.append(
            f"[{j}:v:0]setpts=PTS-STARTPTS,fps={fps_s},"
            f"tpad=stop_mode=clone:stop_duration={n / fps + 0.5:.6f},trim=end_frame={n},"
            f"setpts=PTS-STARTPTS,{hdr_f}{chain}{tail},setpts=PTS+{shift:.6f}/TB[ov{k}]"
        )
        en = f"enable='between(n,{s},{s + n - 1})'"
        nxt = f"vo{k}"
        if region == "card":
            x = (OW - rw) // 2
            y = min(max(int(round(ov["y"] * OH - rh / 2)), 0), OH - rh)
            graphs.append(
                f"[{prev}]hue=s={DIM['saturation']}:{en},eq=brightness={DIM['brightness']}:{en},"
                f"boxblur={DIM['blur']}:2:{en}[dim{k}]"
            )
            graphs.append(f"[dim{k}][ov{k}]overlay={x}:{y}:eof_action=pass:{en}[{nxt}]")
        else:
            graphs.append(f"[{prev}][ov{k}]overlay=0:0:eof_action=pass:{en}[{nxt}]")
        prev = nxt
    graphs.append(f"[{prev}]format=yuv420p,setsar=1[{out_label}]")
    return inputs, prep, graphs
