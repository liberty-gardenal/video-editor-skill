"""Contact sheet (prancha) via ffmpeg select/fps + tile."""

from __future__ import annotations

import math
from pathlib import Path

from . import edl as edlmod
from .probe import probe
from .util import VeditError, ensure_parent, has_filter, run_ffmpeg


def _guide_filters(guides_path) -> list[str]:
    data = edlmod.load_json(guides_path, "guides")
    rects = data.get("rects", data.get("guides")) if isinstance(data, dict) else data
    if not isinstance(rects, list):
        raise VeditError("O arquivo de guias deve ser uma lista de retângulos (frações 0-1).")
    out = []
    for r in rects:
        x, y, w, h = (float(r[k]) for k in ("x", "y", "w", "h"))
        color = str(r.get("color", "red")).replace(":", "")
        out.append(f"drawbox=x=iw*{x}:y=ih*{y}:w=iw*{w}:h=ih*{h}:color={color}@0.85:t=3")
    return out


def make_sheet(video, output, every=5.0, start=None, end=None, cols=4, width=480, guides=None,
               max_frames: int = 48) -> dict:  # fmt: skip
    meta = probe(video, audio_analysis=False)
    total = meta.get("duration") or 0
    s = float(start or 0)
    e = float(end) if end is not None else total
    if e <= s:
        raise VeditError("Intervalo inválido para a prancha (fim <= início).")
    span = e - s
    count = max(1, min(max_frames, int(round(span / every)) or 1))
    spacing = span / count
    rows = math.ceil(count / cols)
    ensure_parent(output)
    fps = meta.get("fps") or 30.0
    # Frame indexes (relative to the seek point) at the centre of each of `count` equal slices.
    idx = sorted({int(round((spacing * (k + 0.5)) * fps)) for k in range(count)})
    sel = "+".join(f"eq(n\\,{i})" for i in idx)
    base = [f"select='{sel}'", f"scale={int(width)}:-2"]
    if guides:
        base += _guide_filters(guides)

    def run(with_text: bool):
        chain = list(base)
        if with_text:
            chain.append(
                "drawtext=text='%{pts\\:hms\\:" + f"{s:.3f}" + "}':x=6:y=h-th-6:"
                "fontsize=h/14:fontcolor=white:box=1:boxcolor=black@0.6"
            )
        chain.append(f"tile={cols}x{rows}:padding=4:margin=4:color=black")
        run_ffmpeg(
            ["-y", "-ss", f"{s:.4f}", "-t", f"{span:.4f}", "-i", video, "-an",
             "-vf", ",".join(chain), "-frames:v", "1", "-q:v", "3", output],
        )  # fmt: skip

    stamped = has_filter("drawtext")
    if stamped:
        try:
            run(True)
        except VeditError:
            stamped = False
            run(False)
    else:
        run(False)
    return {"output": str(Path(output)), "frames": count, "cols": cols, "rows": rows,
            "timestamps": stamped}  # fmt: skip
