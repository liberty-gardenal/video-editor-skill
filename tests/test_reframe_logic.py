"""Pure logic of the experimental reframe module (no OpenCV needed)."""

from __future__ import annotations

import importlib.util

import pytest

from vedit import reframe

np = pytest.importorskip("numpy") if importlib.util.find_spec("numpy") else None
pytestmark = pytest.mark.skipif(np is None, reason="numpy ausente")


def test_tracks_merge_when_fragmented():
    box = (0, 0, 50, 50)
    faces = [[(100, 0, 50, 50)], [(102, 0, 50, 50)], [], [], [], [], [(104, 0, 50, 50)]]
    tracks = reframe.merge_tracks(reframe.build_tracks(faces, 640))
    assert len(tracks) == 1 and set(tracks[0]) == {0, 1, 6}
    assert box


def test_two_far_faces_stay_separate():
    faces = [[(50, 0, 40, 40), (500, 0, 40, 40)] for _ in range(5)]
    tracks = reframe.merge_tracks(reframe.build_tracks(faces, 640))
    assert len(tracks) == 2


def test_active_speaker_follows_audio_not_size():
    rng = np.random.default_rng(1)
    n = 60
    energy = np.zeros(n)
    energy[:30] = rng.random(30)
    energy[30:] = rng.random(30)
    a0 = np.where(np.arange(n) < 30, energy, 0.02) + 0.001 * rng.random(n)
    a1 = np.where(np.arange(n) >= 30, energy, 0.02) + 0.001 * rng.random(n)
    who = reframe.pick_speaker(np, [a0, a1], energy)
    assert who[10] == 0 and who[55] == 1


def test_keyframes_sparse_and_restart():
    xs = [0.3] * 10 + [0.7] * 20
    kfs = reframe.smooth_keyframes(xs)
    assert kfs[0] == {"t": 0.0, "x": 0.3}
    assert len(kfs) <= 3 and kfs[-1]["x"] > 0.5
    ts = [k["t"] for k in kfs]
    assert all(b - a >= 1.5 for a, b in zip(ts, ts[1:], strict=False))
