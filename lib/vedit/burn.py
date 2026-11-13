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


def parse_ass(path) -> dict:
    """Minimal reader for ASS files written by `vedit captions`."""
    text = Path(path).read_text(encoding="utf-8-sig")
    res = {"w": 1080, "h": 1920}
    for key, name in (("w", "PlayResX"), ("h", "PlayResY")):
        m = re.search(rf"^{name}:\s*(\d+)", text, re.M)
        if m:
            res[key] = int(m.group(1))
    style = {"font": "Arial", "size": 64, "bold": False, "outline": 4, "shadow": 0}
    fmt = None
    for line in text.splitlines():
        if line.startswith("Format:") and "Fontname" in line:
            fmt = [c.strip() for c in line[7:].split(",")]
        elif line.startswith("Style:") and fmt:
            vals = [v.strip() for v in line[6:].split(",")]
            row = dict(zip(fmt, vals, strict=False))
            style.update(
                font=row.get("Fontname", "Arial"),
                size=float(row.get("Fontsize", 64)),
                bold=row.get("Bold", "0") not in ("0", ""),
                outline=float(row.get("Outline", 4)),
                shadow=float(row.get("Shadow", 0)),
            )
            break
    events = []
    for line in text.splitlines():
        if not line.startswith("Dialogue:"):
            continue
        parts = line[9:].split(",", 9)
        if len(parts) < 10:
            continue
        txt = parts[9]
        pos = re.search(r"\\pos\((-?[\d.]+),(-?[\d.]+)\)", txt)
        clean = re.sub(r"\{[^}]*\}", "", txt).replace("\\N", " ")
        events.append(
            {
                "start": _parse_ass_time(parts[1]),
                "end": _parse_ass_time(parts[2]),
                "text": clean,
                "words": _colored_words(txt),
                "pos": (float(pos.group(1)), float(pos.group(2))) if pos else None,
            }
        )
    return {"res": res, "style": style, "events": events}


_COLOR_TAG = re.compile(r"\\1?c&H(?:[0-9A-Fa-f]{2})?([0-9A-Fa-f]{6})&")


def _colored_words(txt: str) -> list[tuple[str, tuple[int, int, int] | None]]:
    """Split an ASS text into (word, rgb|None) following inline \\c override tags (ASS is BGR)."""
    words: list[tuple[str, tuple[int, int, int] | None]] = []
    color = None
    for tag, text in re.findall(r"(\{[^}]*\})|([^{]+)", txt):
        if tag:
            for m in _COLOR_TAG.finditer(tag):
                bgr = m.group(1)
                rgb = (int(bgr[4:6], 16), int(bgr[2:4], 16), int(bgr[0:2], 16))
                color = None if rgb == (255, 255, 255) else rgb
            continue
        for w in text.replace("\\N", " ").split():
            words.append((w, color))
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


def _wrap(draw, words, font, max_w: int) -> list[list]:
    """Greedy word wrap; ``words`` is a list of (text, color)."""
    lines: list[list] = []
    cur: list = []
    for w in words:
        trial = " ".join(x[0] for x in [*cur, w])
        if cur and draw.textlength(trial, font=font) > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines or [[]]


def render_frame(Image, ImageDraw, ImageFont, size_wh, ev, style, res, font_name):
    """Render one caption block onto a transparent RGBA image of the video size.

    Words coloured by inline ASS tags (``vedit captions --highlight``) are drawn in that colour.
    """
    vw, vh = size_wh
    k = vh / res["h"]
    fsize = max(8, int(round(style["size"] * k)))
    outline = max(1, int(round(style["outline"] * k)))
    font = _load_font(ImageFont, font_name, fsize, style["bold"])
    img = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    words = ev.get("words") or [(w, None) for w in ev["text"].split()]
    lines = _wrap(d, words, font, int(vw * 0.88))
    px, py = ev["pos"] or (res["w"] / 2, res["h"] * 0.7)
    cx, cy = px * vw / res["w"], py * vh / res["h"]
    line_h = int(fsize * 1.15)
    y0 = cy - line_h * len(lines) / 2
    space = d.textlength(" ", font=font)
    for i, line in enumerate(lines):
        widths = [d.textlength(w, font=font) for w, _ in line]
        x = cx - (sum(widths) + space * max(len(line) - 1, 0)) / 2
        yy = y0 + line_h * i + line_h / 2
        for (w, col), wd in zip(line, widths, strict=True):
            fill = (*col, 255) if col else (255, 255, 255, 255)
            d.text((x, yy), w, font=font, fill=fill, anchor="lm",
                   stroke_width=outline, stroke_fill=(0, 0, 0, 255))  # fmt: skip
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

        t = 0.0
        last = blank
        for i, ev in enumerate(events):
            if ev["start"] > t + 0.0005:
                add(blank, ev["start"] - t)
            png = tdp / f"c{i:05d}.png"
            render_frame(PIL_Image, ImageDraw, ImageFont, (vw, vh), ev, parsed["style"],
                         parsed["res"], font).save(png)  # fmt: skip
            add(png, max(ev["end"] - max(ev["start"], t), 0.04))
            t = max(ev["end"], ev["start"] + 0.04)
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
