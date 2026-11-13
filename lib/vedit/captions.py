"""Caption blocks from words.json + EDL, written as ASS and optional SRT."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from . import edl as edlmod
from .util import VeditError, ensure_parent, info

DEFAULT_Y = 0.62
DEFAULT_ACCENT = "#FFD400"
SENTENCE_END = (".", "?", "!", "…")
SOFT_BREAK = (",", ";", ":")

# Weightless words (articles, prepositions, conjunctions) in pt / en / es.
WEIGHTLESS = frozenset(
    """
    a o as os um uma uns umas de do da dos das em no na nos nas por pelo pela pelos pelas
    para pra com sem e ou mas que se ao aos à às num numa
    the an of in on at to for by with and or but nor so as if
    el la los las un una unos unas del al en con sin y o pero ni por para
    """.split()
)

STYLES = {
    "viral": {
        "max_words": 3, "size": 0.058, "outline": 0.0042, "bold": 1, "upper": True, "shadow": 0,
    },
    "limpo": {
        "max_words": 6, "size": 0.034, "outline": 0.0026, "bold": 0, "upper": False, "shadow": 1,
    },
}  # fmt: skip


def _strip_punct(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower())


def remap_words(words: list[dict], timeline: list[dict]) -> list[dict]:
    """Map word times from source to final timeline; drop words outside clips.

    Clips with ``speed`` compress/stretch the offset inside the clip; clips flagged
    ``skip_words`` (stills, or another source than the transcribed one) get no words.
    """
    out = []
    for w in words:
        try:
            wt, we = float(w["t"]), float(w["e"])
        except (KeyError, TypeError, ValueError) as exc:
            raise VeditError(f"words.json inválido: palavra sem 't'/'e' numéricos ({w!r}).") from exc
        mid = (wt + we) / 2
        for c in timeline:
            if c.get("skip_words"):
                continue
            if c["in"] <= mid < c["out"]:
                k = c.get("speed", 1.0)
                lo, hi = c["offset"], c["offset"] + c["duration"]
                t = min(max(c["offset"] + (wt - c["in"]) / k, lo), hi)
                e = min(max(c["offset"] + (we - c["in"]) / k, lo), hi)
                out.append({"w": str(w["w"]).strip(), "t": t, "e": max(e, t), "clip": c["index"]})
                break
    return [w for w in out if w["w"]]


def mark_word_clips(tl: list[dict], edl: dict, words_source: str | None = None) -> list[dict]:
    """Flag clips whose words must be ignored: other source than the transcribed one, or images."""
    main = words_source or edlmod.main_source_key(edl)
    for c in tl:
        src = c.get("source")
        other = bool(src and main and Path(src).name != Path(main).name)
        c["skip_words"] = other or bool(src and edlmod.is_image(src))
    return tl


def norm_word(w: str) -> str:
    """Case/accent-insensitive form of a word with punctuation removed."""
    d = unicodedata.normalize("NFKD", str(w))
    d = "".join(ch for ch in d if not unicodedata.combining(ch))
    return re.sub(r"[^\w]", "", d.lower())


def parse_highlight(spec) -> frozenset[str]:
    if not spec:
        return frozenset()
    parts = spec.split(",") if isinstance(spec, str) else list(spec)
    out = set()
    for p in parts:
        for tok in str(p).split():
            n = norm_word(tok)
            if n:
                out.add(n)
    return frozenset(out)


def ass_color(hex_rgb: str) -> str:
    """'#RRGGBB' -> ASS override colour '&HBBGGRR&' (ASS stores BGR)."""
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{b}{g}{r}&".upper()


def join_tokens(words: list[dict]) -> list[dict]:
    """Join '100' + '%' style tokens."""
    out: list[dict] = []
    for w in words:
        if out and re.fullmatch(r"[%‰°]+[.,;:!?]*", w["w"]) and out[-1]["clip"] == w["clip"]:
            out[-1]["w"] += w["w"]
            out[-1]["e"] = max(out[-1]["e"], w["e"])
        else:
            out.append(dict(w))
    return out


def group_words(words: list[dict], max_words: int, max_gap: float = 0.6) -> list[list[dict]]:
    blocks: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur and (w["clip"] != cur[-1]["clip"] or len(cur) >= max_words or w["t"] - cur[-1]["e"] > max_gap):
            blocks.append(cur)
            cur = []
        cur.append(w)
        txt = w["w"]
        if txt.endswith(SENTENCE_END) or (txt.endswith(SOFT_BREAK) and len(cur) >= 2):
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


def _ends_sentence(block: list[dict]) -> bool:
    return block[-1]["w"].endswith(SENTENCE_END + SOFT_BREAK)


def push_trailing_weightless(blocks: list[list[dict]], max_words: int) -> list[list[dict]]:
    """Move a dangling article/preposition at the end of a block to the start of the next one."""
    for i in range(len(blocks) - 1):
        b, nxt = blocks[i], blocks[i + 1]
        if (
            len(b) > 1
            and nxt[0]["clip"] == b[-1]["clip"]
            and len(nxt) < max_words
            and not b[-1]["w"].endswith(SENTENCE_END + SOFT_BREAK)
            and _strip_punct(b[-1]["w"]) in WEIGHTLESS
        ):
            nxt.insert(0, b.pop())
    return blocks


def merge_weightless(blocks: list[list[dict]], max_words: int) -> list[list[dict]]:
    """Merge one-word blocks made only of weightless words into a neighbour."""
    changed = True
    while changed:
        changed = False
        for i, b in enumerate(blocks):
            if len(b) != 1 or _strip_punct(b[0]["w"]) not in WEIGHTLESS:
                continue
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            prv = blocks[i - 1] if i > 0 else None
            if nxt and nxt[0]["clip"] == b[0]["clip"] and len(nxt) < max_words:
                blocks[i + 1] = b + nxt
                del blocks[i]
                changed = True
                break
            if prv and prv[0]["clip"] == b[0]["clip"] and len(prv) < max_words and not _ends_sentence(prv):
                prv.extend(b)
                del blocks[i]
                changed = True
                break
    return blocks


def build_blocks(
    words: list[dict],
    timeline: list[dict],
    max_words: int = 3,
    min_dur: float = 0.25,
) -> list[dict]:
    """Return caption blocks [{start, end, text, clip}] on the final timeline."""
    mapped = join_tokens(remap_words(words, timeline))
    groups = merge_weightless(push_trailing_weightless(group_words(mapped, max_words), max_words), max_words)
    clip_end = {c["index"]: c["offset"] + c["duration"] for c in timeline}
    blocks = [
        {
            "start": g[0]["t"],
            "end": max(g[-1]["e"], g[0]["t"]),
            "text": " ".join(w["w"] for w in g),
            "words": [w["w"] for w in g],
            "clip": g[0]["clip"],
        }
        for g in groups
    ]
    for i, b in enumerate(blocks):
        limit = clip_end[b["clip"]]
        if i + 1 < len(blocks):
            limit = min(limit, blocks[i + 1]["start"]) if blocks[i + 1]["clip"] == b["clip"] else limit
        if b["end"] - b["start"] < min_dur:
            b["end"] = max(b["end"], min(b["start"] + min_dur, limit))
        if i + 1 < len(blocks) and b["end"] > blocks[i + 1]["start"]:
            b["end"] = blocks[i + 1]["start"]
        b["end"] = max(b["end"], b["start"])
    return [b for b in blocks if b["end"] - b["start"] > 0.001]


# ----------------------------------------------------------------------- writers
def _ass_time(t: float) -> str:
    cs = int(round(t * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_ass(
    blocks, path, style: str, width: int, height: int, y: float, font: str,
    highlight=None, accent: str = DEFAULT_ACCENT,
) -> None:
    st = STYLES[style]
    size = int(round(height * st["size"]))
    outline = max(1, int(round(height * st["outline"])))
    margin_x = int(width * 0.06)
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
        f"{-st['bold']},0,0,0,100,100,0,0,1,{outline},{st['shadow']},5,{margin_x},{margin_x},0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    px, py = width // 2, int(round(height * y))
    hl = parse_highlight(highlight)
    acc, base = ass_color(accent), "&HFFFFFF&"
    for b in blocks:
        words = b.get("words") or b["text"].split()
        parts = []
        for w in words:
            t = w.upper() if st["upper"] else w
            t = t.replace("{", "(").replace("}", ")").replace("\\", "")
            if hl and norm_word(w) in hl:
                t = f"{{\\1c{acc}}}{t}{{\\1c{base}}}"
            parts.append(t)
        text = " ".join(parts)
        lines.append(
            f"Dialogue: 0,{_ass_time(b['start'])},{_ass_time(b['end'])},Default,,0,0,0,,"
            f"{{\\an5\\pos({px},{py})}}{text}"
        )
    ensure_parent(path)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_srt(blocks, path) -> None:
    out = []
    for i, b in enumerate(blocks, 1):
        out.append(f"{i}\n{_srt_time(b['start'])} --> {_srt_time(b['end'])}\n{b['text']}\n")
    ensure_parent(path)
    Path(path).write_text("\n".join(out), encoding="utf-8")


def make_captions(
    words_path,
    edl_path,
    output,
    srt: bool = False,
    style: str = "viral",
    max_words: int | None = None,
    y: float = DEFAULT_Y,
    font: str = "Arial",
    highlight=None,
    accent: str = DEFAULT_ACCENT,
) -> dict:
    if style not in STYLES:
        raise VeditError(f"Estilo desconhecido: {style} (use viral ou limpo)")
    wj = edlmod.load_json(words_path, "words.json")
    edl = edlmod.load_edl(edl_path)
    fps = edlmod.resolve_fps(edl, edl_path)
    tl = mark_word_clips(edlmod.timeline(edl, fps), edl, wj.get("source") if isinstance(wj, dict) else None)
    mw = max_words or STYLES[style]["max_words"]
    blocks = build_blocks(wj.get("words", []), tl, mw)
    hl = parse_highlight(highlight)
    if hl:
        found = {norm_word(w) for b in blocks for w in b["words"]} & hl
        for miss in sorted(hl - found):
            info(f"Aviso: a palavra '{miss}' (--highlight) não aparece em nenhuma legenda.")
    out_cfg = edl.get("output") or {}
    w, h = int(out_cfg.get("width", 1080)), int(out_cfg.get("height", 1920))
    write_ass(blocks, output, style, w, h, y, font, highlight=hl, accent=accent)
    srt_path = None
    if srt:
        srt_path = str(Path(output).with_suffix(".srt"))
        write_srt(blocks, srt_path)
    return {"ass": str(output), "srt": srt_path, "blocks": len(blocks), "highlighted": sorted(hl)}
