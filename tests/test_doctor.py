import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "lib"))
    return subprocess.run([sys.executable, "-m", "vedit", *args], capture_output=True, text=True, env=env)


def test_doctor_json():
    r = run("doctor", "--json")
    data = json.loads(r.stdout)
    names = {c["name"] for c in data["checks"]}
    assert {"python", "ffmpeg", "ffprobe", "filtro:ass", "filtro:drawtext", "hyperframes"} <= names
    assert data["ok"] is (r.returncode == 0)
    hf = next(c for c in data["checks"] if c["name"] == "hyperframes")
    assert hf["required"] is False
    # "ass" must be detected as a whole filter name, never as a substring of lowpass/bass
    ass = next(c for c in data["checks"] if c["name"] == "filtro:ass")
    assert isinstance(ass["ok"], bool)


def test_launcher_runs():
    r = subprocess.run([str(ROOT / "bin" / "vedit"), "--version"], capture_output=True, text=True)
    assert r.returncode == 0 and "vedit" in r.stdout


def test_init_workspace(tmp_path):
    r = run("init", str(tmp_path / "ws"))
    assert r.returncode == 0
    ws = tmp_path / "ws"
    for name in ("00-probe.json", "01-words.json", "02-digest.md", "03-moments.json", "04-edl.json"):
        assert (ws / name).exists()
    assert (ws / "out").is_dir() and (ws / "qc").is_dir()


def test_doctor_reports_interpreter_and_zscale_warning(monkeypatch):
    from vedit import doctor, util

    res = doctor.run_doctor()
    interp = next(c for c in res["checks"] if c["name"] == "interpretador")
    assert sys.executable in interp["detail"] and res["interpreter"] == sys.executable
    real = util.filters_of(util.ffmpeg_path())
    monkeypatch.setattr(util, "filters_of", lambda ff: frozenset(real - {"zscale"}))
    z = next(c for c in doctor.run_doctor()["checks"] if c["name"] == "filtro:zscale")
    assert not z["ok"] and "tone mapping" in z["detail"] and "zscale" in z["fix"]
