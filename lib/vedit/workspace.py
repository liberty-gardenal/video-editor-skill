"""setup (venv) and init (workspace) commands."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
from pathlib import Path

from .util import REPO_ROOT, VeditError, info

# Cheap packages installed by a plain `vedit setup`; heavy ones need `--all`.
CHEAP_PACKAGES = ["Pillow>=9.0", "numpy>=1.23"]
HEAVY_PACKAGES = ["faster-whisper>=1.0", "opencv-python>=4.8"]


def venv_dir() -> Path:
    """$CLAUDE_PLUGIN_DATA/venv when that variable is set, else <repo>/.venv."""
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if data:
        return Path(data) / "venv"
    return REPO_ROOT / ".venv"


def venv_python() -> Path:
    d = venv_dir()
    return d / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def setup(all_extras: bool = False) -> dict:
    vdir = venv_dir()
    if not venv_python().exists():
        info(f"Criando ambiente virtual em {vdir} ...")
        venv.EnvBuilder(with_pip=True).create(vdir)
    py = str(venv_python())
    packages = CHEAP_PACKAGES + (HEAVY_PACKAGES if all_extras else [])
    info("Instalando " + ", ".join(packages) + " ...")
    p = subprocess.run([py, "-m", "pip", "install", "-q", *packages])
    if p.returncode != 0:
        raise VeditError("Falha ao instalar os pacotes (veja a saída do pip acima).")
    return {"venv": str(vdir), "python": py, "installed": packages}


def init_workspace(path, source: str | None = None) -> dict:
    from .edl import fps_for_edl, fps_fraction
    from .probe import probe

    ws = Path(path)
    (ws / "out").mkdir(parents=True, exist_ok=True)
    (ws / "qc").mkdir(parents=True, exist_ok=True)
    fps = 30
    src_field = ""
    probe_data = None
    if source:
        probe_data = probe(source)
        if probe_data.get("fps_rational"):
            fps = fps_for_edl(fps_fraction(probe_data["fps_rational"]))
        try:  # keep the path relative to the EDL's folder so the workspace is portable
            src_field = os.path.relpath(source, ws.resolve())
        except ValueError:
            src_field = str(source)
    files = {
        "00-probe.json": "{}\n",
        "01-words.json": json.dumps({"language": None, "duration": 0, "words": []}) + "\n",
        "02-digest.md": "",
        "03-moments.json": json.dumps({"moments": []}, indent=2) + "\n",
        "04-edl.json": json.dumps(
            {"source": src_field, "fps": fps, "output": {"width": 1080, "height": 1920}, "clips": []},
            indent=2,
        ) + "\n",
    }  # fmt: skip
    created = []
    for name, content in files.items():
        f = ws / name
        if not f.exists():
            f.write_text(content, encoding="utf-8")
            created.append(name)
    if probe_data is not None:
        (ws / "00-probe.json").write_text(
            json.dumps(probe_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return {"workspace": str(ws), "created": created, "fps": fps}
