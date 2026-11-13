"""Burn ASS captions: libass when available, Pillow + overlay otherwise."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .probe import probe
from .util import (
    VeditError,
    ensure_parent,
    has_filter,
    info,
    log_path_for,
    require_module,
    run_ffmpeg,
)

ENCODE = [
    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18",
    "-preset", "medium", "-c:a", "copy", "-movflags", "+faststart",
]  # fmt: skip


def _ass_rgb(v: str) -> tuple[int, int, int]:
    """'&H00BBGGRR' style colour -> (r, g, b)."""
    h = re.sub(r"[^0-9A-Fa-f]", "", v).rjust(8, "0")[-6:]
    return int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)


def parse_ass(path) -> dict:
    """Minimal reader for ASS files written by `vedit captions`."""
    text = Path(path).read_text(encoding="utf-8-sig")
    res = {"w": 1080, "h": 1920}
    for key, name in (("w", "PlayResX"), ("h", "PlayResY")):
        m = re.search(rf"^{name}:\s*(\d+)", text, re.M)
        if m:
            res[key] = int(m.group(1))
    default = {"font": "Arial", "size": 64, "bold": False, "outline": 4, "shadow": 0,
               "border": 1, "primary": (255, 255, 255), "outline_color": (0, 0, 0)}  # fmt: skip
    styles: dict[str, dict] = {}
    fmt = None
    for line in text.splitlines():
        if line.startswith("Format:") and "Fontname" in line:
            fmt = [c.strip() for c in line[7:].split(",")]
        elif line.startswith("Style:") and fmt:
            vals = [v.strip() for v in line[6:].split(",")]
            row = dict(zip(fmt, vals, strict=False))
            styles[row.get("Name", "Default")] = {
                "font": row.get("Fontname", "Arial"),
                "size": float(row.get("Fontsize", 64)),
                "bold": row.get("Bold", "0") not in ("0", ""),
                "outline": float(row.get("Outline", 4)),
                "shadow": float(row.get("Shadow", 0)),
                "border": int(float(row.get("BorderStyle", 1))),
                "primary": _ass_rgb(row.get("PrimaryColour", "&H00FFFFFF")),
                "outline_color": _ass_rgb(row.get("OutlineColour", "&H00000000")),
            }
    style = styles.get("Default") or next(iter(styles.values()), default)
    events = []
    for line in text.splitlines():
        if not line.startswith("Dialogue:"):
            continue
        parts = line[9:].split(",", 9)
        if len(parts) < 10:
            continue
        txt = parts[9]
        pos = re.search(r"\\pos\((-?[\d.]+),(-?[\d.]+)\)", txt)
        fs = re.search(r"\\fs(\d+(?:\.\d+)?)", txt)
        clean = re.sub(r"\{[^}]*\}", "", txt).replace("\\N", " ")
        cw = _colored_words(txt)
        events.append(
            {
                "start": _parse_ass_time(parts[1]),
                "end": _parse_ass_time(parts[2]),
                "layer": int(parts[0]) if parts[0].strip().lstrip("-").isdigit() else 0,
                "style": parts[3].strip(),
                "text": clean,
                "words": [(w, c) for w, c, _ in cw],
                "scales": [sc for _, _, sc in cw],
                "fs": float(fs.group(1)) if fs else None,
                "pos": (float(pos.group(1)), float(pos.group(2))) if pos else None,
            }
        )
    return {"res": res, "style": style, "styles": styles, "events": events}


_COLOR_TAG = re.compile(r"\\1?c&H(?:[0-9A-Fa-f]{2})?([0-9A-Fa-f]{6})&")
_SCALE_TAG = re.compile(r"\\fscx(\d+(?:\.\d+)?)")


def _colored_words(txt: str) -> list[tuple[str, tuple[int, int, int] | None, float]]:
    """Split an ASS text into (word, rgb|None, scale) following inline \\c and \\fscx tags (ASS is BGR)."""
    words: list[tuple[str, tuple[int, int, int] | None, float]] = []
    color = None
    scale = 1.0
    for tag, text in re.findall(r"(\{[^}]*\})|([^{]+)", txt):
        if tag:
            for m in _COLOR_TAG.finditer(tag):
                bgr = m.group(1)
                rgb = (int(bgr[4:6], 16), int(bgr[2:4], 16), int(bgr[0:2], 16))
                color = None if rgb == (255, 255, 255) else rgb
            for m in _SCALE_TAG.finditer(tag):
                scale = float(m.group(1)) / 100
            continue
        for w in text.replace("\\N", " ").split():
            words.append((w, color, scale))
    return words


def _parse_ass_time(s: str) -> float:
    h, m, rest = s.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def find_font_file(name: str, bold: bool) -> str | None:
    """Locate a TTF/OTF file for ``name`` without bundling fonts."""
    fc = shutil.which("fc-match")
    if fc:
        try:
            out = subprocess.run(
                [fc, "-f", "%{file}", f"{name}:{'bold' if bold else 'regular'}"],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()  # fmt: skip
            if out and os.path.isfile(out):
                return out
        except (OSError, subprocess.SubprocessError):
            pass
    sfx = "Bold" if bold else "Regular"
    home = Path.home()
    cands = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{sfx}.ttf",
        f"/usr/share/fonts/liberation/LiberationSans-{sfx}.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        str(home / "Library/Fonts/Arial.ttf"),
    ]  # fmt: skip
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def _load_font(ImageFont, name: str, size: int, bold: bool):
    f = find_font_file(name, bold)
    if f:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _wrap(draw, words, font_for, max_w: int) -> list[list]:
    """Greedy word wrap; ``words`` is a list of (text, color, scale)."""
    lines: list[list] = []
    cur: list = []
    cur_w = 0.0
    space = draw.textlength(" ", font=font_for(1.0))
    for w in words:
        wd = draw.textlength(w[0], font=font_for(w[2]))
        if cur and cur_w + space + wd > max_w:
            lines.append(cur)
            cur, cur_w = [w], wd
        else:
            cur_w += (space if cur else 0) + wd
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines or [[]]


def render_frame(Image, ImageDraw, ImageFont, size_wh, ev, style, res, font_name):
    """Render one ASS event onto a transparent RGBA image of the video size.

    Words coloured by inline ASS tags (highlight / karaoke) are drawn in that colour, words with
    ``\\fscx`` are drawn larger, and ``BorderStyle 3`` styles (headline box) get an opaque box.
    """
    vw, vh = size_wh
    k = vh / res["h"]
    fsize = max(8, int(round((ev.get("fs") or style["size"]) * k)))
    outline = max(1, int(round(style["outline"] * k)))
    boxed = style.get("border") == 3
    base_fill = (*style.get("primary", (255, 255, 255)), 255)
    cache: dict[float, object] = {}

    def font_for(scale: float):
        if scale not in cache:
            cache[scale] = _load_font(ImageFont, font_name, max(8, int(round(fsize * scale))), style["bold"])
        return cache[scale]

    img = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    words = ev.get("words") or [(w, None) for w in ev["text"].split()]
    scales = ev.get("scales") or [1.0] * len(words)
    words = [(w, c, sc) for (w, c), sc in zip(words, scales, strict=False)]
    lines = _wrap(d, words, font_for, int(vw * 0.88))
    px, py = ev["pos"] or (res["w"] / 2, res["h"] * 0.7)
    cx, cy = px * vw / res["w"], py * vh / res["h"]
    line_h = int(fsize * max((sc for _, _, sc in words), default=1.0) * 1.15)
    y0 = cy - line_h * len(lines) / 2
    space = d.textlength(" ", font=font_for(1.0))
    for i, line in enumerate(lines):
        widths = [d.textlength(w, font=font_for(sc)) for w, _, sc in line]
        total = sum(widths) + space * max(len(line) - 1, 0)
        x = cx - total / 2
        yy = y0 + line_h * i + line_h / 2
        if boxed:
            box = (*style.get("outline_color", (0, 0, 0)), 255)
            d.rectangle((x - outline, yy - line_h / 2 - outline + 1, x + total + outline,
                         yy + line_h / 2 + outline - 1), fill=box)  # fmt: skip
        for (w, col, sc), wd in zip(line, widths, strict=True):
            fill = (*col, 255) if col else base_fill
            kw = {} if boxed else {"stroke_width": outline, "stroke_fill": (0, 0, 0, 255)}
            d.text((x, yy), w, font=font_for(sc), fill=fill, anchor="lm", **kw)
            x += wd + space
    return img


def _escape_filter_path(p: str) -> str:
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def burn(video, ass, output, font: str | None = None, force_fallback: bool = False) -> dict:
    meta = probe(video, audio_analysis=False)
    if not meta.get("has_video"):
        raise VeditError("O arquivo não tem vídeo.")
    # Audio is stream-copied, so cap the output at the video length: the audio can never outlast it.
    vdur = meta.get("video_duration") or meta.get("duration") or 0
    tcap = ["-t", f"{vdur:.6f}"] if vdur else []
    ensure_parent(output)
    log = log_path_for(output, "burn")
    Path(log).write_text("", encoding="utf-8")
    use_lib = (has_filter("ass") or has_filter("subtitles")) and not force_fallback
    if use_lib:
        with tempfile.TemporaryDirectory() as td:
            shutil.copy(ass, Path(td) / "cap.ass")
            name = "ass" if has_filter("ass") else "subtitles"
            vf = f"{name}=cap.ass"
            run_ffmpeg(
                ["-y", "-i", os.path.abspath(video), "-vf", vf, "-map", "0:v:0", "-map", "0:a?",
                 *tcap, *ENCODE, os.path.abspath(output)],
                log_path=log, cwd=td,
            )  # fmt: skip
        return {"output": str(output), "method": "libass"}
    info("ffmpeg sem libass: usando o fallback Pillow + overlay.")
    PIL_Image = require_module("PIL.Image", "Pillow", "queimar legenda sem libass")
    ImageDraw = require_module("PIL.ImageDraw", "Pillow", "queimar legenda sem libass")
    ImageFont = require_module("PIL.ImageFont", "Pillow", "queimar legenda sem libass")
    vw, vh, dur = meta["width"], meta["height"], vdur
    parsed = parse_ass(ass)
    font = font or parsed["style"]["font"]
    events = sorted(parsed["events"], key=lambda e: e["start"])
    if not events:
        raise VeditError("A legenda não tem nenhum bloco (Dialogue).")
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        blank = tdp / "blank.png"
        PIL_Image.new("RGBA", (vw, vh), (0, 0, 0, 0)).save(blank)
        lines = []

        def add(path: Path, duration: float):
            lines.append(f"file '{path.as_posix()}'\nduration {duration:.4f}")

        # Events may overlap (headline over captions): one composited frame per interval.
        cuts = sorted({0.0, *(e["start"] for e in events), *(e["end"] for e in events)})
        points: list[float] = []
        for c in cuts:
            if not points or c - points[-1] >= 0.015:
                points.append(c)
        t = 0.0
        last = blank
        shared: dict[int, object] = {}  # events spanning several intervals are rendered once
        spans = {i: sum(1 for a, b in zip(points, points[1:], strict=False) if ev["start"] <= a and b <= ev["end"] + 0.015)
                 for i, ev in enumerate(events)}  # fmt: skip
        done: dict[tuple, Path] = {}
        for a, b in zip(points, points[1:], strict=False):
            if a >= dur and dur:
                break
            active = tuple(
                i for i, ev in enumerate(events) if ev["start"] <= a + 0.0005 and b <= ev["end"] + 0.015
            )
            if not active:
                add(blank, b - t)
                t = b
                continue
            if active not in done:
                comp = PIL_Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
                for i in sorted(active, key=lambda j: events[j]["layer"]):
                    ev = events[i]
                    layer = shared.get(i)
                    if layer is None:
                        sty = parsed["styles"].get(ev["style"], parsed["style"])
                        layer = render_frame(PIL_Image, ImageDraw, ImageFont, (vw, vh), ev, sty,
                                             parsed["res"], font)  # fmt: skip
                        if spans[i] > 1:
                            shared[i] = layer
                    comp.alpha_composite(layer)
                png = tdp / f"c{len(done):05d}.png"
                comp.save(png)
                done[active] = png
            add(done[active], b - t)
            t = b
        add(blank, max(dur - t, 0) + 1.0)
        lines.append(f"file '{last.as_posix()}'")
        lst = tdp / "list.txt"
        lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
        run_ffmpeg(
            ["-y", "-i", os.path.abspath(video), "-f", "concat", "-safe", "0", "-i", str(lst),
             "-filter_complex",
             "[1:v]format=rgba[cap];[0:v][cap]overlay=0:0:format=auto:eof_action=repeat:shortest=0[v]",
             "-map", "[v]", "-map", "0:a?", *tcap, *ENCODE, os.path.abspath(output)],
            log_path=log,
        )  # fmt: skip
    return {"output": str(output), "method": "pillow"}
