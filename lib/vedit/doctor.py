"""Environment diagnostics: what works, what is missing, how to fix it per OS."""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from . import util

HF_URL = "https://github.com/heygen-com/hyperframes"

FILTERS = [
    ("ass", "legenda queimada via libass (sem ele, o fallback Pillow é usado)"),
    ("subtitles", "legenda via libass"),
    ("drawtext", "carimbo de tempo nas pranchas (opcional)"),
    ("loudnorm", "normalização de loudness (obrigatório para master)"),
    ("arnndn", "redução de ruído (opcional)"),
    ("zscale", "conversão HDR→SDR com tone mapping (sem ele, usa colorspace)"),
    ("tonemap", "tone mapping HDR"),
    ("sidechaincompress", "ducking da música (mix)"),
    ("freezedetect", "detecção de imagem congelada (verify)"),
    ("blackdetect", "detecção de quadros pretos (verify)"),
    ("drawbox", "guias na prancha (sheet --guides)"),
]

OPTIONAL = [
    ("faster_whisper", "faster-whisper", "transcribe"),
    ("PIL", "Pillow", "legenda sem libass"),
    ("numpy", "numpy", "transcribe / legenda sem libass / reframe"),
    ("cv2", "opencv-python", "reframe (experimental)"),
]


def os_kind() -> str:
    s = platform.system()
    if s == "Darwin":
        return "macos"
    if s == "Windows":
        return "windows"
    try:
        if "microsoft" in Path("/proc/version").read_text().lower():
            return "wsl"
    except OSError:
        pass
    return "linux"


FIX_FFMPEG = {
    "macos": "macOS: `brew install ffmpeg` (se usar Homebrew) ou baixe um build estático em "
             "https://evermeet.cx/ffmpeg/ e ponha no PATH; ou defina VEDIT_FFMPEG/VEDIT_FFPROBE.",
    "linux": "Linux: `sudo apt install ffmpeg` (Debian/Ubuntu), `sudo dnf install ffmpeg` (Fedora) "
             "ou um build estático de https://johnvansickle.com/ffmpeg/.",
    "wsl": "Windows (WSL): dentro do WSL, `sudo apt install ffmpeg`.",
}  # fmt: skip
FIX_LIBASS = (
    "Use um ffmpeg com libass: macOS `brew install ffmpeg` ou build estático (evermeet.cx); "
    "Linux `sudo apt install ffmpeg` ou build estático (johnvansickle.com); Windows-WSL "
    "`sudo apt install ffmpeg`. Aponte para ele com VEDIT_FFMPEG. Sem libass, "
    "`vedit burn` usa o fallback Pillow (instale com `vedit setup`)."
)


def _fix_all(kind_map: dict) -> str:
    return "\n      ".join(kind_map.values())


def _cmd_ok(cmd: list[str], timeout: int = 25) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, (p.stdout or p.stderr).strip().splitlines()[0] if (
            p.stdout or p.stderr
        ).strip() else ""
    except (OSError, subprocess.SubprocessError):
        return False, ""


def find_hyperframes_plugin() -> str | None:
    root = Path.home() / ".claude" / "plugins"
    if not root.is_dir():
        return None
    base_depth = len(root.parts)
    for dirpath, dirnames, _ in os.walk(root):
        if len(Path(dirpath).parts) - base_depth > 7:
            dirnames[:] = []
            continue
        for d in dirnames:
            if d.lower() == "hyperframes" or d.lower().startswith("hyperframes"):
                return str(Path(dirpath) / d)
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git")]
    return None


def find_chrome() -> str | None:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    for p in (
        "/Applications/Google Chrome.app",
        "/Applications/Chromium.app",
        "/usr/bin/google-chrome",
    ):
        if os.path.exists(p):
            return p
    puppeteer = Path.home() / ".cache" / "puppeteer"
    if puppeteer.is_dir():
        return str(puppeteer)
    return None


def run_doctor() -> dict:
    kind = os_kind()
    checks: list[dict] = []

    def add(name, ok, detail, required=False, fix=None, level=None):
        lvl = level or ("ok" if ok else ("erro" if required else "aviso"))
        checks.append({"name": name, "ok": ok, "required": required, "level": lvl,
                       "detail": detail, "fix": fix})  # fmt: skip

    py = sys.version_info
    add("python", py >= (3, 10), f"Python {py.major}.{py.minor}.{py.micro}", True,
        "Instale Python 3.10 ou superior (python.org, `apt install python3`, `brew install python`).")  # fmt: skip

    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    where = f"venv em {sys.prefix}" if in_venv else "Python do sistema (sem venv)"
    add("interpretador", True, f"{sys.executable} ({where})")

    ff = fp = None
    try:
        ff = util.ffmpeg_path()
        add("ffmpeg", True, f"{ff} — {util.tool_version(ff)}", True)
    except util.VeditError as e:
        add("ffmpeg", False, str(e), True, _fix_all(FIX_FFMPEG))
    try:
        fp = util.ffprobe_path()
        add("ffprobe", True, fp, True)
    except util.VeditError as e:
        add("ffprobe", False, str(e), True, _fix_all(FIX_FFMPEG))

    if ff:
        names = util.filters_of(ff)
        for fname, why in FILTERS:
            ok = fname in names
            fix = None
            if not ok:
                fix = (
                    FIX_LIBASS
                    if fname in ("ass", "subtitles")
                    else (
                        "Instale/aponte para um ffmpeg completo: " + FIX_FFMPEG.get(kind, FIX_FFMPEG["linux"])
                    )
                )
            detail = why
            if fname == "zscale" and not ok:
                detail = (
                    "zscale ausente: vídeo HDR será convertido SEM tone mapping adequado "
                    "(imagem lavada ou contrastada demais)"
                )
                fix = (
                    "Use um ffmpeg compilado com libzimg (zscale): " + FIX_FFMPEG.get(kind, FIX_FFMPEG["linux"])
                    + " Aponte para ele com VEDIT_FFMPEG/VEDIT_FFPROBE."
                )
            add(f"filtro:{fname}", ok, detail, required=False, fix=fix)

    for mod, pip_name, why in OPTIONAL:
        ok = importlib.util.find_spec(mod) is not None
        add(f"opcional:{pip_name}", ok, why, False,
            None if ok else ("vedit setup" if mod in ("PIL", "numpy") else "vedit setup --all"))  # fmt: skip

    node = shutil.which("node")
    npx = shutil.which("npx")
    add("node", bool(node), node or "Node.js não encontrado (necessário só para HyperFrames/motion)", False,
        None if node else "macOS: `brew install node`; Linux/WSL: https://nodejs.org ou `sudo apt install nodejs npm`.")  # fmt: skip
    hf_ok, hf_detail = False, ""
    if npx:
        hf_ok, hf_detail = _cmd_ok([npx, "--no-install", "hyperframes", "--version"])
        if hf_ok:
            hf_detail = f"npx hyperframes {hf_detail}"
    if not hf_ok:
        plug = find_hyperframes_plugin()
        if plug:
            hf_ok, hf_detail = True, f"plugin do Claude Code em {plug}"
    add("hyperframes", hf_ok, hf_detail or "HyperFrames não encontrado", False,
        None if hf_ok else f"Veja {HF_URL} e rode `npx hyperframes --help` para os comandos de instalação.")  # fmt: skip
    chrome = find_chrome()
    add("chrome", bool(chrome), chrome or "Chrome/Chromium não encontrado (usado pelo HyperFrames)", False,
        None if chrome else "Instale o Google Chrome ou Chromium (macOS: baixe em google.com/chrome; Linux/WSL: `sudo apt install chromium`).")  # fmt: skip

    ok_all = all(c["ok"] for c in checks if c["required"])
    return {
        "ok": ok_all,
        "os": kind,
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "venv": sys.prefix if in_venv else None,
        "checks": checks,
    }


def format_report(res: dict) -> str:
    sym = {"ok": "[OK]   ", "aviso": "[AVISO]", "erro": "[ERRO] "}
    lines = [f"vedit doctor — sistema: {res['os']}", ""]
    for c in res["checks"]:
        lines.append(f"{sym[c['level']]} {c['name']}: {c['detail']}")
        if c["fix"] and not c["ok"]:
            lines.append(f"         como corrigir: {c['fix']}")
    lines.append("")
    lines.append(
        "Tudo que é obrigatório está ok." if res["ok"] else "Faltam itens obrigatórios (marcados [ERRO])."
    )
    return "\n".join(lines)
