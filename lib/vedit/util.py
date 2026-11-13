"""Shared helpers: tool discovery, ffmpeg runner, parsing, lazy imports."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from functools import cache
from pathlib import Path

EXE = ".exe" if os.name == "nt" else ""
REPO_ROOT = Path(__file__).resolve().parents[2]


class VeditError(Exception):
    """User-facing error (message is printed in pt-BR, exit code 1)."""


def info(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def dump_json(obj, fp=None) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2), file=fp or sys.stdout)


# --------------------------------------------------------------- tool discovery
def _path_candidates(name: str) -> list[str]:
    seen: list[str] = []
    real: set[str] = set()
    for d in os.get_exec_path():
        p = Path(d) / (name + EXE)
        try:
            if p.is_file() and os.access(p, os.X_OK):
                rp = os.path.realpath(p)
                if rp not in real:
                    real.add(rp)
                    seen.append(str(p))
        except OSError:
            continue
    return seen


@cache
def filters_of(ffmpeg: str) -> frozenset[str]:
    """Return the set of filter names reported by ``ffmpeg -filters`` (whole names)."""
    try:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=30
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    names = set()
    for line in out.splitlines():
        tok = line.split()
        if len(tok) >= 3 and len(tok[0]) == 3 and set(tok[0]) <= set("TSC.|") and tok[1] != "=":
            names.add(tok[1])
    return frozenset(names)


@cache
def ffmpeg_path() -> str:
    env = os.environ.get("VEDIT_FFMPEG")
    if env:
        found = shutil.which(env) or (env if os.path.isfile(env) else None)
        if not found:
            raise VeditError(f"VEDIT_FFMPEG aponta para um arquivo inexistente: {env}")
        return found
    cands = _path_candidates("ffmpeg")
    if not cands:
        raise VeditError("ffmpeg não encontrado no PATH. Rode `vedit doctor` para ver como instalar.")
    if len(cands) > 1:
        for c in cands:
            if "ass" in filters_of(c):
                return c
    return cands[0]


@cache
def ffprobe_path() -> str:
    env = os.environ.get("VEDIT_FFPROBE")
    if env:
        found = shutil.which(env) or (env if os.path.isfile(env) else None)
        if not found:
            raise VeditError(f"VEDIT_FFPROBE aponta para um arquivo inexistente: {env}")
        return found
    if os.environ.get("VEDIT_FFMPEG"):
        sib = Path(ffmpeg_path()).with_name("ffprobe" + EXE)
        if sib.is_file():
            return str(sib)
    sib = Path(ffmpeg_path()).with_name("ffprobe" + EXE)
    if sib.is_file():
        return str(sib)
    cands = _path_candidates("ffprobe")
    if not cands:
        raise VeditError("ffprobe não encontrado. Rode `vedit doctor` para ver como instalar.")
    return cands[0]


def has_filter(name: str) -> bool:
    return name in filters_of(ffmpeg_path())


def tool_version(path: str) -> str:
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=15).stdout
        return out.splitlines()[0] if out else ""
    except (OSError, subprocess.SubprocessError):
        return ""


# ------------------------------------------------------------------- running
def _tail(text: str, n: int = 30) -> str:
    return "\n".join(text.strip().splitlines()[-n:])


def run_ffmpeg(
    args, log_path: str | Path | None = None, cwd: str | None = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run ffmpeg. Full stderr goes to ``log_path``; on failure the last 30 lines are shown."""
    cmd = [ffmpeg_path(), "-hide_banner", "-nostdin", "-nostats", *map(str, args)]
    p = subprocess.run(cmd, capture_output=True, cwd=cwd)
    err = p.stderr.decode("utf-8", "replace")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write("$ " + " ".join(cmd) + "\n" + err + "\n")
    if check and p.returncode != 0:
        extra = f"\nLog completo: {log_path}" if log_path else ""
        raise VeditError(f"ffmpeg falhou (código {p.returncode}). Últimas 30 linhas:\n{_tail(err)}{extra}")
    p.stderr_text = err  # type: ignore[attr-defined]
    return p


def run_ffprobe_json(path: str | Path, *extra: str) -> dict:
    cmd = [ffprobe_path(), "-v", "error", "-print_format", "json", *extra, str(path)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise VeditError(f"ffprobe não conseguiu ler '{path}':\n{_tail(p.stderr, 10)}")
    return json.loads(p.stdout or "{}")


# ------------------------------------------------------------------- parsing
def parse_rate(s) -> float:
    if not s:
        return 0.0
    s = str(s)
    if "/" in s:
        a, _, b = s.partition("/")
        try:
            return float(a) / float(b) if float(b) else 0.0
        except ValueError:
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_time(s: str) -> float:
    """Accepts seconds ('12.5'), 'mm:ss(.s)' or 'hh:mm:ss(.s)'."""
    s = str(s).strip()
    parts = s.split(":")
    try:
        total = 0.0
        for p in parts:
            total = total * 60 + float(p)
        return total
    except ValueError as exc:
        raise VeditError(f"Tempo inválido: '{s}'") from exc


def arg_time(s: str) -> float:
    """argparse ``type=`` wrapper around parse_time (never leaks VeditError)."""
    try:
        return parse_time(s)
    except VeditError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def arg_ranges(s: str) -> list[tuple[float, float]]:
    try:
        return parse_ranges(s)
    except VeditError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def arg_color(s: str) -> str:
    """Accept '#RRGGBB' / 'RRGGBB' and return normalised '#RRGGBB'."""
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(s).strip())
    if not m:
        raise argparse.ArgumentTypeError(f"Cor inválida: '{s}' (use #RRGGBB, ex.: #FFD400)")
    return "#" + m.group(1).upper()


def fmt_ts(t: float) -> str:
    """mm:ss.s"""
    t = max(0.0, t)
    m = int(t // 60)
    return f"{m:02d}:{t - m * 60:04.1f}"


def parse_ranges(spec: str) -> list[tuple[float, float]]:
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        a, sep, b = part.partition("-")
        if not sep:
            raise VeditError(f"Janela inválida: '{part}' (use inicio-fim)")
        out.append((parse_time(a), parse_time(b)))
    return out


def parse_ebur128(text: str) -> dict:
    """Parse the Summary block printed by the ebur128 filter."""
    idx = text.rfind("Summary:")
    block = text[idx:] if idx >= 0 else text

    def grab(label: str):
        m = re.search(rf"^\s*{label}:\s+(-?inf|-?[\d.]+)", block, re.M)
        if not m:
            return None
        return float("-inf") if "inf" in m.group(1) else float(m.group(1))

    return {
        "integrated_lufs": grab("I"),
        "lra": grab("LRA"),
        "true_peak_dbtp": grab("Peak"),
    }


def measure_loudness(path, start: float | None = None, end: float | None = None) -> dict:
    args: list = []
    if start is not None:
        args += ["-ss", start]
    if end is not None:
        args += ["-to", end]
    args += ["-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]
    p = run_ffmpeg(args)
    res = parse_ebur128(p.stderr_text)  # type: ignore[attr-defined]
    if res["integrated_lufs"] is None:
        raise VeditError("Não consegui medir a loudness (a mídia tem áudio?).")
    return res


# ---------------------------------------------------------------- lazy imports
def require_module(module: str, pip_name: str, purpose: str):
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise VeditError(
            f"O pacote opcional '{pip_name}' é necessário para {purpose} e não está instalado.\n"
            f"Instale com: {'vedit setup' if pip_name in ('Pillow', 'numpy') else 'vedit setup --all'}"
        ) from exc


def log_path_for(output: str | Path, tag: str = "ffmpeg") -> Path:
    out = Path(output)
    return out.with_name(f"{out.stem}.{tag}.log")


def ensure_parent(path: str | Path) -> None:
    Path(path).resolve().parent.mkdir(parents=True, exist_ok=True)
