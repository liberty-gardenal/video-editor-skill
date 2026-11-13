"""install.sh and bin/vedit behaviour in a throw-away HOME (no real ~/.claude is touched)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="shell scripts")


def sh(args, home, extra_env=None):
    env = dict(os.environ, HOME=str(home), PATH="/usr/bin:/bin")
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", str(ROOT / "install.sh"), "--no-venv", *args], capture_output=True, text=True, env=env, cwd=home
    )


def test_install_and_uninstall_only_touch_own_links(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    foreign = tmp_path / "other-vedit"
    foreign.write_text("x")
    (home / ".local" / "bin").mkdir(parents=True)
    (home / ".local" / "bin" / "vedit").symlink_to(foreign)  # someone else's link
    r = sh([], home)
    assert r.returncode == 1 and "pulando" in r.stdout
    assert (home / ".local" / "bin" / "vedit").resolve() == foreign.resolve()  # untouched
    # skills (if any) were linked, and a second run after removing the foreign link is clean
    (home / ".local" / "bin" / "vedit").unlink()
    assert sh([], home).returncode == 0
    assert (home / ".local" / "bin" / "vedit").resolve() == (ROOT / "bin" / "vedit").resolve()
    assert sh([], home).returncode == 0  # idempotent: our own link is refreshed
    # a real file in the way is never replaced
    (home / ".local" / "bin" / "vedit").unlink()
    (home / ".local" / "bin" / "vedit").write_text("meu")
    r = sh([], home)
    assert r.returncode == 1 and (home / ".local" / "bin" / "vedit").read_text() == "meu"
    # uninstall leaves the foreign file and removes nothing else of ours that is not ours
    assert sh(["--uninstall"], home).returncode == 0
    assert (home / ".local" / "bin" / "vedit").read_text() == "meu"


def test_path_hint_lists_all_shells(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    out = sh([], home).stdout
    assert "export PATH=" in out and "fish_add_path" in out and f"{home}/.local/bin/vedit" in out


def test_uninstall_project_never_creates_directories(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    proj = tmp_path / "nao-existe"
    r = sh(["--uninstall", "--project", str(proj)], home)
    assert r.returncode == 0 and not proj.exists()
    proj.mkdir()
    assert sh(["--uninstall", "--project", str(proj)], home).returncode == 0
    assert list(proj.iterdir()) == []  # no .claude created either


def test_launcher_prefers_plugin_data_venv(tmp_path):
    venv_bin = tmp_path / "data" / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    fake = venv_bin / "python"
    fake.write_text("#!/bin/sh\necho FAKE-VENV-PYTHON\n")
    fake.chmod(0o755)
    env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(tmp_path / "data"))
    r = subprocess.run([str(ROOT / "bin" / "vedit"), "--version"], capture_output=True, text=True, env=env)
    assert "FAKE-VENV-PYTHON" in r.stdout


def test_setup_venv_location_and_cheap_packages(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "lib"))
    from vedit import workspace

    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    assert workspace.venv_dir() == tmp_path / "venv"
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA")
    assert workspace.venv_dir() == ROOT / ".venv"
    assert {"Pillow", "numpy"} == {p.split(">")[0] for p in workspace.CHEAP_PACKAGES}
    assert any(p.startswith("faster-whisper") for p in workspace.HEAVY_PACKAGES)
