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


def _crosses(barriers, a: dict, b: dict) -> bool:
    """True when a barrier interval (s, e) lies between word ``a`` and the next word ``b``."""
    ma, mb = (a["t"] + a["e"]) / 2, (b["t"] + b["e"]) / 2
    return any(ma < s and mb >= e for s, e in barriers)


def group_words(words: list[dict], max_words: int, max_gap: float = 0.6, barriers=()) -> list[list[dict]]:
    blocks: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur and (
            w["clip"] != cur[-1]["clip"]
            or len(cur) >= max_words
            or w["t"] - cur[-1]["e"] > max_gap
            or (barriers and _crosses(barriers, cur[-1], w))
        ):
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
    barriers=(),
) -> list[dict]:
    """Return caption blocks [{start, end, text, words, times, sstart, clip}] on the final timeline.

    ``barriers`` are timeline intervals (s, e) where captions must stay silent (proof cards):
    words whose midpoint falls inside are dropped, no block crosses one, and block times are
    clamped outside it.
    """
    mapped = join_tokens(remap_words(words, timeline))
    mapped = [w for w in mapped if not any(s <= (w["t"] + w["e"]) / 2 < e for s, e in barriers)]
    for i, w in enumerate(mapped):
        w["sstart"] = i == 0 or mapped[i - 1]["w"].endswith(SENTENCE_END)
    groups = merge_weightless(
        push_trailing_weightless(group_words(mapped, max_words, barriers=barriers), max_words), max_words
    )
    clip_end = {c["index"]: c["offset"] + c["duration"] for c in timeline}
    blocks = [
        {
            "start": g[0]["t"],
            "end": max(g[-1]["e"], g[0]["t"]),
            "text": " ".join(w["w"] for w in g),
            "words": [w["w"] for w in g],
            "times": [(w["t"], w["e"]) for w in g],
            "sstart": [w["sstart"] for w in g],
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
        for bs, be in barriers:
            if b["start"] < bs < b["end"]:
                b["end"] = bs
            elif bs <= b["start"] < be:
                b["start"] = min(be, b["end"])
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


MODES = ("bloco", "palavra", "karaoke")
CASES = ("upper", "lower", "sentence", "keep")
EMPHASIS_SCALE = 130
HEADLINE_SIZE = 0.064
SAFE_MARGIN = 0.06
DEFAULT_SPLIT_AT = 0.45


def _ass_style(name, font, size, primary, outline_col, bold, border, outline, shadow, margin_x) -> str:
    def c(hex_rgb):
        return "&H00" + ass_color(hex_rgb)[2:-1]

    return (
        f"Style: {name},{font},{size},{c(primary)},{c(primary)},{c(outline_col)},&H80000000,"
        f"{-bold},0,0,0,100,100,0,0,{border},{outline},{shadow},5,{margin_x},{margin_x},0,1"
    )


def apply_case(word: str, case: str, sentence_start: bool = False) -> str:
    if case == "upper":
        return word.upper()
    if case == "lower":
        return word.lower()
    if case == "sentence":
        w = word.lower()
        if sentence_start:
            for i, ch in enumerate(w):
                if ch.isalpha():
                    return w[:i] + ch.upper() + w[i + 1 :]
        return w
    return word


def _clean(t: str) -> str:
    return t.replace("{", "(").replace("}", ")").replace("\\", "")


_DROP_PUNCT = re.compile(r"(?<!\d)[.,]|[.,](?!\d)")
BRIDGE_GAP = 0.35
MIN_FRAGMENT = 0.04


def strip_display_punct(word: str) -> str:
    """Remove '.' and ',' from a displayed word, keeping decimals ('2,5') and '?', '!', '%'."""
    return _DROP_PUNCT.sub("", word)


def parse_mute(spec) -> list[tuple[float, float]]:
    """'a-b,c-d' (or a list of pairs) -> sorted intervals in output-timeline seconds."""
    if not spec:
        return []
    if isinstance(spec, str):
        from .util import parse_ranges

        spec = parse_ranges(spec)
    out = []
    for a, b in spec:
        if b <= a:
            raise VeditError(f"Janela de --mute inválida: {a}-{b} (o fim deve ser maior que o início).")
        out.append((float(a), float(b)))
    return sorted(out)


def bridge_events(events: list[dict], gap: float = BRIDGE_GAP) -> list[dict]:
    """Extend an event up to the next start when the gap between them is > 0 and < ``gap``."""
    ev = sorted(events, key=lambda e: e["t0"])
    for a, b in zip(ev, ev[1:], strict=False):
        d = b["t0"] - a["t1"]
        if 0.001 < d < gap:
            a["t1"] = b["t0"]
    return ev


def mute_events(events: list[dict], mute) -> list[dict]:
    """Clip events against the mute intervals; fragments shorter than MIN_FRAGMENT are dropped."""
    out = []
    for e in events:
        frags = [(e["t0"], e["t1"])]
        for ms, me in mute:
            nxt = []
            for a, b in frags:
                if me <= a or ms >= b:
                    nxt.append((a, b))
                    continue
                if ms > a:
                    nxt.append((a, ms))
                if me < b:
                    nxt.append((me, b))
            frags = nxt
        out += [{**e, "t0": a, "t1": b} for a, b in frags if b - a >= MIN_FRAGMENT]
    return out


def _text_measurer(font: str, size: int, bold: bool):
    """Return text -> width in px (Pillow when available, else a conservative estimate)."""
    try:
        from PIL import ImageFont

        from .burn import find_font_file

        path = find_font_file(font, bold)
        if path:
            f = ImageFont.truetype(path, size)
            return lambda t: f.getlength(t) * 1.04
    except Exception:  # noqa: BLE001 - any failure falls back to the estimate
        pass
    return lambda t: len(t) * size * 0.64


def fit_headline(lines: list[str], width: int, height: int, font: str, box: bool) -> tuple[int, list[str]]:
    """Pick a font size and wrapping so every headline line fits inside the horizontal safe margins."""
    size0 = int(round(height * HEADLINE_SIZE))
    pad = int(round(size0 * 0.2)) if box else 0
    avail = width * (1 - 2 * SAFE_MARGIN) - 2 * pad
    widest = max(_text_measurer(font, size0, True)(ln) for ln in lines)
    size = size0 if widest <= avail else max(int(size0 * avail / widest), int(size0 * 0.6))
    measure = _text_measurer(font, size, True)
    out: list[str] = []
    for ln in lines:
        cur = ""
        for w in ln.split():
            trial = f"{cur} {w}".strip()
            if cur and measure(trial) > avail:
                out.append(cur)
                cur = w
            else:
                cur = trial
        out.append(cur)
    return size, out


def _karaoke_spans(b: dict) -> list[tuple[float, float]]:
    """Per-word (start, end) with no gaps: each word lasts until the next begins; the last until block end."""
    n = len(b["words"])
    times = b.get("times") or [(b["start"], b["end"])] * n
    starts: list[float] = []
    for t, _e in times:
        lo = starts[-1] if starts else b["start"]
        starts.append(min(max(t, lo, b["start"]), b["end"]))
    starts[0] = b["start"]
    ends = [*starts[1:], b["end"]]
    return list(zip(starts, ends, strict=True))


def write_ass(
    blocks,
    path,
    style: str,
    width: int,
    height: int,
    y: float,
    font: str,
    highlight=None,
    accent: str = DEFAULT_ACCENT,
    mode: str = "bloco",
    case: str | None = None,
    emphasis=None,
    headline: dict | None = None,
    keep_punct: bool = False,
    mute=None,
    size: float | None = None,
    outline: float | None = None,
    shadow: float | None = None,
    bridge: bool = True,
) -> None:
    st = STYLES[style]
    case = case or ("upper" if st["upper"] else "keep")
    size = int(round(height * st["size"])) if size is None else size
    outline = max(1, int(round(height * st["outline"]))) if outline is None else outline
    shadow = st["shadow"] if shadow is None else shadow
    margin_x = int(width * SAFE_MARGIN)
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
        f"{-st['bold']},0,0,0,100,100,0,0,1,{outline},{shadow},5,{margin_x},{margin_x},0,1",
    ]
    head_events: list[str] = []
    if headline:
        box = headline.get("box")
        hsize, hlines = fit_headline(headline["lines"], width, height, font, bool(box))
        pad = int(round(hsize * 0.2))
        lines.append(
            _ass_style("Headline", font, hsize, headline.get("color") or "#FFFFFF", box or "#000000", 1,
                       3 if box else 1, pad if box else max(outline, int(round(hsize * 0.07))), 0, margin_x)
        )  # fmt: skip
        line_h = int(round(hsize * 1.15)) + (2 * pad - 2 if box else 0)
        t0 = headline.get("start", 0.0)
        t1 = headline["end"]
        total = line_h * len(hlines)
        cy = min(max(height * headline.get("y", 0.12), total / 2 + height * 0.03), height * 0.97 - total / 2)
        for i, ln in enumerate(hlines):
            ly = int(round(cy - total / 2 + line_h * (i + 0.5)))
            head_events.append(
                f"Dialogue: 1,{_ass_time(t0)},{_ass_time(t1)},Headline,,0,0,0,,"
                f"{{\\an5\\pos({width // 2},{ly})\\fs{hsize}}}{_clean(ln)}"
            )
    lines += [
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    hl = parse_highlight(highlight)
    em = parse_highlight(emphasis)
    acc, base = ass_color(accent), "&HFFFFFF&"
    karaoke = mode == "karaoke"
    cap_events: list[dict] = []
    for b in blocks:
        words = b.get("words") or b["text"].split()
        sstart = b.get("sstart") or [False] * len(words)
        px, py = width // 2, int(round(height * b.get("y", y)))
        spans = _karaoke_spans(b) if karaoke else [(b["start"], b["end"])]
        for k, (t0, t1) in enumerate(spans):
            if t1 - t0 <= 0.001 and len(spans) > 1:
                continue
            parts = []
            for i, w in enumerate(words):
                shown = w if keep_punct else strip_display_punct(w)
                if not shown:
                    continue
                t = _clean(apply_case(shown, case, sstart[i] if i < len(sstart) else False))
                if em and norm_word(w) in em:
                    t = f"{{\\fscx{EMPHASIS_SCALE}\\fscy{EMPHASIS_SCALE}}}{t}{{\\fscx100\\fscy100}}"
                if (karaoke and i == k) or (not karaoke and hl and norm_word(w) in hl):
                    t = f"{{\\1c{acc}}}{t}{{\\1c{base}}}"
                parts.append(t)
            if parts:
                cap_events.append({"t0": t0, "t1": t1, "pos": f"{{\\an5\\pos({px},{py})}}", "text": " ".join(parts)})
    if bridge:
        cap_events = bridge_events(cap_events)
    cap_events = mute_events(cap_events, parse_mute(mute))
    for e in cap_events:
        lines.append(f"Dialogue: 0,{_ass_time(e['t0'])},{_ass_time(e['t1'])},Default,,0,0,0,,{e['pos']}{e['text']}")
    lines += head_events
    ensure_parent(path)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_srt(blocks, path) -> None:
    out = []
    for i, b in enumerate(blocks, 1):
        out.append(f"{i}\n{_srt_time(b['start'])} --> {_srt_time(b['end'])}\n{b['text']}\n")
    ensure_parent(path)
    Path(path).write_text("\n".join(out), encoding="utf-8")


def _clip_y(tl: list[dict], default: float) -> dict[int, float]:
    """Per-clip caption y: ``caption_y``, else ``split_at`` (default 0.45) for ``layout: lower``."""
    out: dict[int, float] = {}
    for c in tl:
        raw = c["clip"] if isinstance(c.get("clip"), dict) else {}
        v = raw.get("caption_y")
        if v is None and raw.get("layout") == "lower":
            v = raw.get("split_at", DEFAULT_SPLIT_AT)
        try:
            out[c["index"]] = float(v) if v is not None else default
        except (TypeError, ValueError):
            out[c["index"]] = default
    return out


def _card_barriers(edl: dict) -> list[tuple[float, float]]:
    out = []
    for ov in edl.get("overlays") or []:
        if isinstance(ov, dict) and ov.get("region") == "card":
            try:
                at, dur = float(ov["at"]), float(ov["dur"])
            except (KeyError, TypeError, ValueError):
                continue
            out.append((at, at + dur))
    return sorted(out)


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
    mode: str = "bloco",
    case: str | None = None,
    emphasis=None,
    keep_under_cards: bool = False,
    headline: str | None = None,
    headline_y: float = 0.12,
    headline_start: float = 0.0,
    headline_end: float | None = None,
    headline_box: str | None = None,
    headline_color: str | None = None,
    keep_punct: bool = False,
    mute=None,
    size: float | None = None,
    outline: float | None = None,
    shadow: float | None = None,
    bridge: bool = True,
) -> dict:
    if style not in STYLES:
        raise VeditError(f"Estilo desconhecido: {style} (use viral ou limpo)")
    if mode not in MODES:
        raise VeditError(f"Modo desconhecido: {mode} (use {', '.join(MODES)})")
    if case is not None and case not in CASES:
        raise VeditError(f"Caixa desconhecida: {case} (use {', '.join(CASES)})")
    mute = parse_mute(mute)
    wj = edlmod.load_json(words_path, "words.json")
    edl = edlmod.load_edl(edl_path)
    fps = edlmod.resolve_fps(edl, edl_path)
    tl = mark_word_clips(edlmod.timeline(edl, fps), edl, wj.get("source") if isinstance(wj, dict) else None)
    mw = 1 if mode == "palavra" else (max_words or STYLES[style]["max_words"])
    barriers = [] if keep_under_cards else _card_barriers(edl)
    blocks = build_blocks(wj.get("words", []), tl, mw, barriers=barriers)
    clip_y = _clip_y(tl, y)
    for b in blocks:
        if clip_y.get(b["clip"], y) != y:
            b["y"] = clip_y[b["clip"]]
    hl = parse_highlight(highlight)
    em = parse_highlight(emphasis)
    shown = {norm_word(w) for b in blocks for w in b["words"]}
    if hl and mode == "karaoke":
        info("Aviso: em --mode karaoke a cor de destaque é a da palavra ativa; --highlight não pinta.")
        hl = frozenset()
    for flag, wanted in (("--highlight", hl), ("--emphasis", em)):
        for miss in sorted(wanted - shown):
            info(f"Aviso: a palavra '{miss}' ({flag}) não aparece em nenhuma legenda.")
    out_cfg = edl.get("output") or {}
    w, h = int(out_cfg.get("width", 1080)), int(out_cfg.get("height", 1920))
    head = None
    if headline:
        hlines = [ln.strip() for ln in headline.split("|") if ln.strip()]
        if not hlines:
            raise VeditError("--headline está vazio.")
        total = tl[-1]["offset"] + tl[-1]["duration"] if tl else 0.0
        head = {
            "lines": hlines, "y": headline_y, "start": headline_start,
            "end": total if headline_end is None else headline_end,
            "box": headline_box, "color": headline_color,
        }  # fmt: skip
    write_ass(blocks, output, style, w, h, y, font, highlight=hl, accent=accent, mode=mode, case=case,
              emphasis=em, headline=head, keep_punct=keep_punct, mute=mute, size=size, outline=outline,
              shadow=shadow, bridge=bridge)  # fmt: skip
    srt_path = None
    if srt:
        srt_path = str(Path(output).with_suffix(".srt"))
        write_srt(blocks, srt_path)
    return {
        "ass": str(output), "srt": srt_path, "blocks": len(blocks), "highlighted": sorted(hl),
        "mode": mode, "headline": bool(head),
    }  # fmt: skip
