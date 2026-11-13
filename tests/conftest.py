"""Shared fixtures: synthetic media generated with ffmpeg lavfi (nothing is committed)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from vedit import util  # noqa: E402


def _ff(*args):
    subprocess.run(
        [util.ffmpeg_path(), "-hide_banner", "-nostdin", "-v", "error", "-y", *map(str, args)],
        check=True,
    )


# Speech-like audio: 440 Hz tone during [0, 2.5) of every 4 s, silence otherwise.
GATED_AUDIO = "sine=frequency=440:sample_rate=48000:duration={d}"
GATE = "volume='lt(mod(t,4),2.5)':eval=frame"


def make_av(path: Path, size: str, dur: int = 20, fps: int = 30, extra=()):
    _ff(
        "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={fps}:duration={dur}",
        "-f", "lavfi", "-i", GATED_AUDIO.format(d=dur),
        "-af", GATE, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k", *extra, path,
    )  # fmt: skip


@pytest.fixture(scope="session")
def media(tmp_path_factory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("media")
    landscape = d / "landscape.mp4"
    vertical = d / "vertical.mp4"
    make_av(landscape, "1920x1080")
    make_av(vertical, "720x1280", dur=8)
    return {"landscape": landscape, "vertical": vertical, "dir": d}


@pytest.fixture()
def tmp(tmp_path) -> Path:
    return tmp_path


def write_edl(path: Path, source: Path, clips: list[dict], fps: int = 30) -> Path:
    edl = {"source": str(source), "fps": fps, "output": {"width": 1080, "height": 1920}, "clips": clips}
    path.write_text(json.dumps(edl), encoding="utf-8")
    return path


@pytest.fixture()
def make_edl(tmp_path):
    def _make(source, clips, name="edl.json"):
        return write_edl(tmp_path / name, source, clips)

    return _make
