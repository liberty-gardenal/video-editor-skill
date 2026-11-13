"""EDL loading, validation and frame-exact timeline helpers shared by cut/captions/metrics."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from .util import VeditError

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")
LAYOUTS = ("cover", "split", "fit")
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
    return edl


# --------------------------------------------------------------------- sources
def source_key(edl: dict, clip: dict | None = None) -> str:
    """The source string (as written in the EDL) that applies to ``clip``."""
    src = (clip or {}).get("source") or edl.get("source")
    if not src:
        raise VeditError("A EDL não tem 'source' (nem no topo, nem no clipe).")
    return src


def resolve_source(edl: dict, edl_path, clip: dict | None = None) -> str:
    src = source_key(edl, clip)
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
