"""EDL loading, validation and frame-exact timeline helpers shared by cut/captions/metrics."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from .util import VeditError

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")
LAYOUTS = ("cover", "split", "fit", "lower")
REGIONS = ("full", "top", "card")
SPLIT_AT_DEFAULT, SPLIT_AT_MIN, SPLIT_AT_MAX = 0.45, 0.25, 0.6
TOP_HEIGHT_DEFAULT = 0.45
FEATHER_DEFAULT = 60  # px at 1920 tall; scaled with the output height
CARD_WIDTH_DEFAULT, CARD_Y_DEFAULT = 0.78, 0.36
STILL_ZOOM_DEFAULT = (1.0, 1.08)
SPEED_MIN, SPEED_MAX = 0.25, 4.0
ZOOM_MAX = 4.0

# NTSC rates are stored as rationals so frame counts stay exact over long clips.
_NTSC = (Fraction(24000, 1001), Fraction(30000, 1001), Fraction(48000, 1001), Fraction(60000, 1001))


# ------------------------------------------------------------------------- fps
def fps_fraction(value) -> Fraction:
    """Number ('25', 29.97) or rational string ('30000/1001') -> exact Fraction (NTSC snapped)."""
    if isinstance(value, bool):
        raise VeditError(f"fps inválido: {value!r}")
    try:
        if isinstance(value, str) and "/" in value:
            a, _, b = value.strip().partition("/")
            f = Fraction(int(a), int(b))
        elif isinstance(value, str):
            f = Fraction(value.strip())
        else:
            f = Fraction(value)
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise VeditError(f"fps inválido: {value!r} (use um número ou uma fração como 30000/1001).") from exc
    if f <= 0 or f > 240:
        raise VeditError(f"fps fora do intervalo aceito: {value!r}.")
    for n in _NTSC:
        if abs(float(f - n)) < 0.005:
            return n
    return f if f.denominator == 1 else f.limit_denominator(100000)


def fps_str(f: Fraction) -> str:
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def parse_fps(value) -> float:
    return float(fps_fraction(value))


def fps_for_edl(f: Fraction):
    """Value written into an EDL: an int for whole rates, a rational string otherwise."""
    return f.numerator if f.denominator == 1 else fps_str(f)


def is_image(path) -> bool:
    return str(path).lower().endswith(IMAGE_EXTS)


# --------------------------------------------------------------------- loading
def load_json(path, what: str = "arquivo"):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise VeditError(f"{what} não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VeditError(f"{what} inválido ({path}): {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise VeditError(f"Não consegui ler {what} ({path}): {exc}") from exc


def _num(c: dict, key: str, label) -> float:
    try:
        v = c[key]
        if isinstance(v, bool):
            raise TypeError
        return float(v)
    except KeyError as exc:
        raise VeditError(f"Clipe '{label}' da EDL sem '{key}'.") from exc
    except (TypeError, ValueError) as exc:
        raise VeditError(f"Clipe '{label}': '{key}' precisa ser um número (recebi {c[key]!r}).") from exc


def zoom_range(c: dict, label=None) -> tuple[float, float]:
    """Clip zoom as (start, end): a number is static, {"from": a, "to": b} is a linear ramp."""
    z = c.get("zoom", 1.0)
    label = label if label is not None else c.get("id", "?")
    if z is None:
        return 1.0, 1.0
    try:
        if isinstance(z, dict):
            if "from" not in z or "to" not in z:
                raise VeditError(f"Clipe '{label}': 'zoom' em rampa precisa de 'from' e 'to'.")
            z0, z1 = float(z["from"]), float(z["to"])
        elif isinstance(z, bool):
            raise TypeError
        else:
            z0 = z1 = float(z)
    except (TypeError, ValueError) as exc:
        raise VeditError(
            f"Clipe '{label}': 'zoom' deve ser um número ou {{\"from\": 1.0, \"to\": 1.1}} (recebi {z!r})."
        ) from exc
    if not (1.0 <= z0 <= ZOOM_MAX and 1.0 <= z1 <= ZOOM_MAX):
        raise VeditError(f"Clipe '{label}': 'zoom' deve ficar entre 1.0 e {ZOOM_MAX}.")
    return z0, z1


def clip_speed(c: dict, label=None) -> float:
    label = label if label is not None else c.get("id", "?")
    v = c.get("speed", 1.0)
    if v is None:
        return 1.0
    try:
        if isinstance(v, bool):
            raise TypeError
        s = float(v)
    except (TypeError, ValueError) as exc:
        raise VeditError(f"Clipe '{label}': 'speed' precisa ser um número (recebi {v!r}).") from exc
    if not (SPEED_MIN <= s <= SPEED_MAX):
        raise VeditError(f"Clipe '{label}': 'speed' deve ficar entre {SPEED_MIN} e {SPEED_MAX} (recebi {s}).")
    return s


def _validate_crop_x(cx, label) -> None:
    if cx is None:
        return
    if isinstance(cx, bool):
        raise VeditError(f"Clipe '{label}': 'crop_x' inválido.")
    if isinstance(cx, (int, float)):
        return
    if not isinstance(cx, list):
        raise VeditError(f"Clipe '{label}': 'crop_x' deve ser um número ou uma lista de {{t, x}}.")
    for k in cx:
        if not isinstance(k, dict) or "t" not in k or "x" not in k:
            raise VeditError(f"Clipe '{label}': cada keyframe de 'crop_x' precisa de 't' e 'x'.")
        try:
            float(k["t"])
            float(k["x"])
        except (TypeError, ValueError) as exc:
            raise VeditError(f"Clipe '{label}': 't' e 'x' do keyframe de 'crop_x' precisam ser números.") from exc


def load_edl(path) -> dict:
    edl = load_json(path, "EDL")
    if not isinstance(edl, dict):
        raise VeditError("A EDL precisa ser um objeto JSON com a chave 'clips'.")
    clips = edl.get("clips")
    if not isinstance(clips, list) or not clips:
        raise VeditError("A EDL precisa ter ao menos um clipe em 'clips'.")
    top = edl.get("source")
    if top is not None and not isinstance(top, str):
        raise VeditError("'source' da EDL deve ser um caminho (texto).")
    if "fps" in edl and edl["fps"] not in (None, ""):
        fps_fraction(edl["fps"])
    out_cfg = edl.get("output")
    if out_cfg is not None:
        if not isinstance(out_cfg, dict):
            raise VeditError("'output' da EDL deve ser um objeto {width, height}.")
        for k in ("width", "height"):
            try:
                if int(out_cfg.get(k, 1)) < 2:
                    raise ValueError
            except (TypeError, ValueError) as exc:
                raise VeditError(f"'output.{k}' da EDL deve ser um inteiro positivo.") from exc
    for i, c in enumerate(clips):
        if not isinstance(c, dict):
            raise VeditError(f"Clipe #{i + 1} da EDL deve ser um objeto.")
        label = c.get("id", i + 1)
        a, b = _num(c, "in", label), _num(c, "out", label)
        if a < 0:
            raise VeditError(f"Clipe '{label}': 'in' não pode ser negativo.")
        if b <= a:
            raise VeditError(f"Clipe '{label}': 'out' deve ser maior que 'in'.")
        layout = c.get("layout", "cover")
        if layout not in LAYOUTS:
            raise VeditError(f"Layout desconhecido no clipe '{label}': {layout!r} (use {', '.join(LAYOUTS)}).")
        src = c.get("source")
        if src is not None and (not isinstance(src, str) or not src):
            raise VeditError(f"Clipe '{label}': 'source' deve ser um caminho (texto).")
        if not src and not top:
            raise VeditError(f"Clipe '{label}' sem 'source' e a EDL não tem 'source' no topo.")
        clip_speed(c, label)
        zoom_range(c, label)
        _validate_crop_x(c.get("crop_x"), label)
        _validate_lower_fields(c, label)
    _validate_overlays(edl)
    return edl


def _frac(c: dict, key: str, label: str, lo: float, hi: float, what: str = "Clipe"):
    """Optional numeric field within [lo, hi]; returns None when absent."""
    v = c.get(key)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise VeditError(f"{what} {label}: '{key}' precisa ser um número (recebi {v!r}).")
    if not (lo <= float(v) <= hi):
        raise VeditError(f"{what} {label}: '{key}' deve ficar entre {lo:g} e {hi:g} (recebi {v}).")
    return float(v)


def _validate_lower_fields(c: dict, label) -> None:
    _frac(c, "split_at", f"'{label}'", SPLIT_AT_MIN, SPLIT_AT_MAX)
    _frac(c, "caption_y", f"'{label}'", 0.0, 1.0)


def split_at(c: dict) -> float:
    v = c.get("split_at")
    return SPLIT_AT_DEFAULT if v is None else float(v)


def overlay_zoom(o: dict, label: str = "?") -> tuple[float, float]:
    """Overlay zoom (start, end): defaults to a slow push-in for stills, static for video."""
    z = o.get("zoom")
    if z is None:
        return STILL_ZOOM_DEFAULT if is_image(o.get("source", "")) else (1.0, 1.0)
    try:
        if isinstance(z, dict):
            if "from" not in z or "to" not in z:
                raise VeditError(f"Overlay {label}: 'zoom' em rampa precisa de 'from' e 'to'.")
            z0, z1 = float(z["from"]), float(z["to"])
        elif isinstance(z, bool):
            raise TypeError
        else:
            z0 = z1 = float(z)
    except (TypeError, ValueError) as exc:
        raise VeditError(
            f"Overlay {label}: 'zoom' deve ser um número ou {{\"from\": 1.0, \"to\": 1.08}} (recebi {z!r})."
        ) from exc
    if not (1.0 <= z0 <= ZOOM_MAX and 1.0 <= z1 <= ZOOM_MAX):
        raise VeditError(f"Overlay {label}: 'zoom' deve ficar entre 1.0 e {ZOOM_MAX}.")
    return z0, z1


def overlay_label(i: int) -> str:
    return f"#{i + 1}"


def overlay_params(o: dict) -> dict:
    """Overlay fields with defaults applied (assumes validation already passed)."""

    def g(k, d):
        return d if o.get(k) is None else o[k]

    return {
        "region": g("region", "full"),
        "at": float(o["at"]),
        "dur": float(o["dur"]),
        "in": float(g("in", 0.0)),
        "height": float(g("height", TOP_HEIGHT_DEFAULT)),
        "feather": float(g("feather", FEATHER_DEFAULT)),
        "crop_x": float(g("crop_x", 0.5)),
        "width": float(g("width", CARD_WIDTH_DEFAULT)),
        "y": float(g("y", CARD_Y_DEFAULT)),
        "zoom": overlay_zoom(o),
    }


def _validate_overlays(edl: dict) -> None:
    ovs = edl.get("overlays")
    if ovs is None:
        return
    if not isinstance(ovs, list):
        raise VeditError("'overlays' da EDL deve ser uma lista.")
    spans = []
    for i, o in enumerate(ovs):
        lab = overlay_label(i)
        if not isinstance(o, dict):
            raise VeditError(f"Overlay {lab} da EDL deve ser um objeto.")
        src = o.get("source")
        if not isinstance(src, str) or not src:
            raise VeditError(f"Overlay {lab}: 'source' é obrigatório (caminho de vídeo ou imagem).")
        for k in ("at", "dur"):
            if k not in o:
                raise VeditError(f"Overlay {lab}: falta '{k}'.")
        at = _frac(o, "at", lab, 0.0, 1e9, "Overlay")
        dur = _frac(o, "dur", lab, 0.0, 1e9, "Overlay")
        if dur <= 0:
            raise VeditError(f"Overlay {lab}: 'dur' deve ser maior que 0.")
        region = o.get("region", "full")
        if region not in REGIONS:
            raise VeditError(f"Overlay {lab}: 'region' desconhecida {region!r} (use {', '.join(REGIONS)}).")
        _frac(o, "in", lab, 0.0, 1e9, "Overlay")
        if o.get("in") is not None and is_image(src):
            raise VeditError(f"Overlay {lab}: 'in' só vale para vídeo (a fonte é uma imagem).")
        _frac(o, "height", lab, 0.2, 0.7, "Overlay")
        _frac(o, "feather", lab, 0.0, 400.0, "Overlay")
        _frac(o, "crop_x", lab, 0.0, 1.0, "Overlay")
        _frac(o, "width", lab, 0.3, 1.0, "Overlay")
        _frac(o, "y", lab, 0.1, 0.9, "Overlay")
        for k, ok in (("height", "top"), ("feather", "top"), ("width", "card"), ("y", "card")):
            if o.get(k) is not None and region != ok:
                raise VeditError(f"Overlay {lab}: '{k}' só vale com region '{ok}' (esta é '{region}').")
        overlay_zoom(o, lab)
        spans.append((at, at + dur, i))
    spans.sort()
    for (a0, a1, ia), (b0, b1, ib) in zip(spans, spans[1:], strict=False):
        if b0 < a1 - 1e-6:
            lo, hi = sorted((ia, ib))
            raise VeditError(
                f"Overlays {overlay_label(lo)} e {overlay_label(hi)} se sobrepõem no tempo "
                f"({a0:g}–{a1:g}s e {b0:g}–{b1:g}s); overlays não podem se sobrepor."
            )


def overlay_frames(edl: dict, fps: float) -> list[dict]:
    """Frame-snapped overlays (sorted by start): index, start/end frame, params."""
    out = []
    for i, o in enumerate(edl.get("overlays") or []):
        p = overlay_params(o)
        s = int(round(p["at"] * fps))
        n = max(1, int(round(p["dur"] * fps)))
        out.append({"index": i, "label": overlay_label(i), "start": s, "frames": n, "end": s + n, "o": o, **p})
    out.sort(key=lambda x: x["start"])
    for a, b in zip(out, out[1:], strict=False):
        if b["start"] < a["end"]:
            raise VeditError(
                f"Overlays {a['label']} e {b['label']} se sobrepõem no tempo; overlays não podem se sobrepor."
            )
    return out


def check_overlays_timeline(edl: dict, tl: list[dict], fps: float) -> list[dict]:
    """Error if an overlay ends after the timeline; returns the frame-snapped overlays."""
    total = sum(t["frames"] for t in tl)
    ovs = overlay_frames(edl, fps)
    for ov in ovs:
        if ov["end"] > total:
            raise VeditError(
                f"Overlay {ov['label']}: at + dur ({ov['at'] + ov['dur']:g}s) passa do fim da "
                f"timeline ({total / fps:g}s)."
            )
    return ovs


def edl_warnings(edl: dict, tl: list[dict], fps: float) -> list[str]:
    """Non-fatal editorial warnings (pt-BR) about lower clips and top overlays."""
    ovs = overlay_frames(edl, fps)
    warns: list[str] = []
    for t in tl:
        s = round(t["offset"] * fps)
        e = s + t["frames"]
        lay = t["clip"].get("layout", "cover")
        tops = sorted((max(o["start"], s), min(o["end"], e)) for o in ovs if o["region"] == "top")
        tops = [(a, b) for a, b in tops if a < b]
        if lay == "lower":
            gaps, pos = [], s
            for a, b in tops:
                if a > pos:
                    gaps.append((pos, a))
                pos = max(pos, b)
            if pos < e:
                gaps.append((pos, e))
            gaps = [g for g in gaps if g[1] - g[0] > 2]
            if gaps:
                txt = ", ".join(f"{a / fps:.1f}–{b / fps:.1f}s" for a, b in gaps[:4])
                warns.append(
                    f"Clipe '{t['id']}' (layout 'lower') tem trechos sem overlay 'top' ({txt}): "
                    "a parte de cima fica só com o fundo desfocado."
                )
        elif tops:
            txt = ", ".join(f"{a / fps:.1f}–{b / fps:.1f}s" for a, b in tops[:4])
            warns.append(
                f"Overlay 'top' sobre o clipe '{t['id']}' (layout '{lay}', {txt}): vai cobrir o rosto; "
                "use layout 'lower' nesse clipe."
            )
    return warns


# --------------------------------------------------------------------- sources
def source_key(edl: dict, clip: dict | None = None) -> str:
    """The source string (as written in the EDL) that applies to ``clip``."""
    src = (clip or {}).get("source") or edl.get("source")
    if not src:
        raise VeditError("A EDL não tem 'source' (nem no topo, nem no clipe).")
    return src


def resolve_source(edl: dict, edl_path, clip: dict | None = None) -> str:
    return resolve_path(source_key(edl, clip), edl_path)


def resolve_path(src: str, edl_path) -> str:
    p = Path(src)
    if p.is_absolute() and p.exists():
        return str(p)
    here = Path(edl_path).resolve().parent
    for base in (here, here.parent, Path.cwd()):
        cand = base / src
        if cand.exists():
            return str(cand)
    raise VeditError(f"Fonte da EDL não encontrada: {src}")


def main_source_key(edl: dict) -> str | None:
    return edl.get("source") or (edl["clips"][0].get("source") if edl.get("clips") else None)


def resolve_fps(edl: dict, edl_path) -> float:
    """EDL fps if present, else the probed fps of the first video source (else 30)."""
    f = resolve_fps_fraction(edl, edl_path)
    return float(f)


def resolve_fps_fraction(edl: dict, edl_path) -> Fraction:
    v = edl.get("fps")
    if v not in (None, ""):
        return fps_fraction(v)
    from .probe import probe

    for c in edl["clips"]:
        key = c.get("source") or edl.get("source")
        if not key or is_image(key):
            continue
        meta = probe(resolve_source(edl, edl_path, c), audio_analysis=False)
        if meta.get("has_video") and meta.get("fps_rational"):
            return fps_fraction(meta["fps_rational"])
    return Fraction(30)


# -------------------------------------------------------------------- timeline
def timeline(edl: dict, fps: float) -> list[dict]:
    """Frame-snapped clips with their offset in the final timeline.

    ``in``/``out`` are source seconds; ``frames``/``duration`` are the output length after ``speed``.
    """
    out = []
    offset_frames = 0
    for i, c in enumerate(edl["clips"]):
        label = c.get("id", i + 1)
        speed = clip_speed(c, label)
        in_f = int(round(float(c["in"]) * fps))
        out_f = int(round(float(c["out"]) * fps))
        src_n = out_f - in_f
        if src_n < 1:
            raise VeditError(f"Clipe '{label}' tem menos de 1 quadro.")
        n = max(1, int(round(src_n / speed)))
        out.append(
            {
                "id": c.get("id", f"c{i + 1}"),
                "index": i,
                "in_frame": in_f,
                "out_frame": out_f,
                "src_frames": src_n,
                "frames": n,
                "in": in_f / fps,
                "out": out_f / fps,
                "src_duration": src_n / fps,
                "duration": n / fps,
                "offset": offset_frames / fps,
                "speed": speed,
                "source": c.get("source") or edl.get("source"),
                "clip": c,
            }
        )
        offset_frames += n
    return out


def keyframes(crop_x, n_frames: int, fps: float, default: float = 0.5) -> list[tuple[int, float]]:
    """Normalise crop_x (number or [{t, x}]) to [(frame_offset, x)], t relative to clip start."""
    if crop_x is None:
        return [(0, default)]
    if isinstance(crop_x, (int, float)):
        return [(0, float(crop_x))]
    pts = sorted(((float(k["t"]), float(k["x"])) for k in crop_x), key=lambda p: p[0])
    if not pts:
        return [(0, default)]
    res: list[tuple[int, float]] = []
    for t, x in pts:
        f = min(max(int(round(t * fps)), 0), n_frames - 1)
        if res and res[-1][0] == f:
            res[-1] = (f, x)
        else:
            res.append((f, x))
    if res[0][0] > 0:
        res.insert(0, (0, res[0][1]))
    else:
        res[0] = (0, res[0][1])
    return res
