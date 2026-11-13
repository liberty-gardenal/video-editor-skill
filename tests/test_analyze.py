"""vedit analyze: synthetic clip with known hard cuts + hand-written words.json."""

from __future__ import annotations

import json

import pytest

from conftest import _ff
from vedit import analyze, cli


@pytest.fixture(scope="module")
def three_colours(tmp_path_factory):
    """9 s clip: black 0-3, white 3-6, gray 6-9 (hard cuts at 3 s and 6 s), with audio."""
    d = tmp_path_factory.mktemp("analyze")
    out = d / "colours.mp4"
    args = []
    for c in ("black", "white", "gray"):
        args += ["-f", "lavfi", "-i", f"color=c={c}:s=320x240:r=30:d=3"]
    _ff(*args, "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=48000:duration=9",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]", "-map", "[v]", "-map", "3:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-c:a", "aac", out)  # fmt: skip
    return out


def test_detect_cuts_and_shot_stats(three_colours):
    cuts = analyze.detect_cuts(three_colours, 0.3)
    assert len(cuts) == 2
    assert cuts[0] == pytest.approx(3.0, abs=0.1) and cuts[1] == pytest.approx(6.0, abs=0.1)
    st = analyze.shot_stats(cuts, 9.0)
    assert st["shots"] == 3 and st["cuts_first_5s"] == 1
    assert st["mean_shot_s"] == pytest.approx(3.0, abs=0.1)
    assert st["cuts_per_minute"] == pytest.approx(13.33, abs=0.1)


def test_shot_stats_no_cuts():
    st = analyze.shot_stats([], 10.0)
    assert st["cuts"] == 0 and st["max_shot_s"] == 10.0
    assert st["longest_no_cut"] == {"start": 0.0, "end": 10.0, "duration": 10.0}


def test_word_stats():
    words = [{"w": f"p{i}", "t": 0.2 + i * 0.4, "e": 0.5 + i * 0.4} for i in range(10)]
    words.append({"w": "fim", "t": 8.0, "e": 8.3})
    s = analyze.word_stats(words, 10.0)
    assert s["words"] == 11 and s["speech_starts_within_0_5s"] is True
    assert s["words_per_s"] == 1.1
    assert s["words_per_s_first_5s"] == pytest.approx(2.0)
    assert s["longest_pause"]["end"] == 8.0 and s["longest_pause"]["duration"] == pytest.approx(3.9)
    assert s["first_words"].startswith("p0 p1")
    assert analyze.word_stats([{"w": "a", "t": 1.2, "e": 1.4}], 10)["speech_starts_within_0_5s"] is False
    assert analyze.word_stats([], 10) == {"words": 0}


def test_cli_analyze_outputs(three_colours, tmp_path, capsys):
    wj = tmp_path / "words.json"
    wj.write_text(json.dumps({"words": [{"w": "oi", "t": 0.1, "e": 0.3}, {"w": "tudo", "t": 0.4, "e": 0.7}]}))
    out = tmp_path / "a"
    rc = cli.main(["analyze", str(three_colours), "-o", str(out), "--words", str(wj), "--json"])
    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    data = json.loads((out / "analise.json").read_text())
    assert len(data["cuts"]) == 2 and printed["cuts"] == data["cuts"]
    assert data["probe"]["width"] == 320 and data["loudness"]["integrated_lufs"] is not None
    assert data["speech"]["words"] == 2
    for name in ("gancho.jpg", "completo.jpg", "analise.md"):
        assert (out / name).stat().st_size > 0
    md = (out / "analise.md").read_text(encoding="utf-8")
    assert "O que observar nas pranchas" in md and "limite inferior" in md


def test_missing_video(tmp_path, capsys):
    assert cli.main(["analyze", str(tmp_path / "nope.mp4"), "-o", str(tmp_path / "o")]) == 1


def _mk(path, filter_complex, inputs, dur):
    args = []
    for i in inputs:
        args += ["-f", "lavfi", "-i", i]
    _ff(*args, "-filter_complex", filter_complex, "-map", "[v]", "-t", str(dur),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", path)  # fmt: skip
    return path


@pytest.fixture(scope="module")
def stacked(tmp_path_factory):
    """30 s, 320x480: static gray bottom half; top half is black then dark gray (0x30) at 10 s, black at 20 s."""
    d = tmp_path_factory.mktemp("stacked")
    ins = ["color=c=black:s=320x240:r=30:d=10", "color=c=0x303030:s=320x240:r=30:d=10",
           "color=c=black:s=320x240:r=30:d=10", "color=c=0x404040:s=320x240:r=30:d=30"]  # fmt: skip
    fc = "[0:v][1:v][2:v]concat=n=3:v=1:a=0[t];[t][3:v]vstack[v]"
    return _mk(d / "stacked.mp4", fc, ins, 30)


@pytest.fixture(scope="module")
def flash(tmp_path_factory):
    """10 s: black, white for 0.08 s at 5 s, then black again (two detections 0.08 s apart)."""
    d = tmp_path_factory.mktemp("flash")
    ins = ["color=c=black:s=320x240:r=50:d=5", "color=c=white:s=320x240:r=50:d=0.08",
           "color=c=black:s=320x240:r=50:d=4.92"]  # fmt: skip
    return _mk(d / "flash.mp4", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]", ins, 10)


def test_region_finds_cuts_whole_frame_misses(stacked, tmp_path):
    assert analyze.detect_cuts(stacked, 0.3) == []
    top = analyze.detect_cuts(stacked, 0.3, (0.0, 0.5))
    assert len(top) == 2 and top[0] == pytest.approx(10.0, abs=0.1)
    assert analyze.detect_cuts(stacked, 0.3, (0.5, 1.0)) == []
    res = analyze.analyze(stacked, tmp_path / "r", regions=["0:0.5"])
    assert res["regions"][0]["cuts"] == top and res["regions"][0]["shots"]["cuts"] == 2
    assert res["regions_auto"] is False
    md = (tmp_path / "r" / "analise.md").read_text(encoding="utf-8")
    assert "Faixa y 0 a 0.5" in md and "0.3" in md


def test_auto_halves_when_few_cuts(stacked, tmp_path):
    res = analyze.analyze(stacked, tmp_path / "a")
    assert res["regions_auto"] is True
    assert [(r["y0"], r["y1"]) for r in res["regions"]] == [(0.0, 0.5), (0.5, 1.0)]
    assert res["regions"][0]["shots"]["cuts"] == 2 and res["regions"][1]["shots"]["cuts"] == 0
    assert "empilhado" in (tmp_path / "a" / "analise.md").read_text(encoding="utf-8")


def test_no_auto_halves_with_enough_cuts(three_colours, tmp_path):
    res = analyze.analyze(three_colours, tmp_path / "n")  # 2 cuts in 9 s
    assert res["regions"] == [] and res["regions_auto"] is False


def test_merge_cuts_unit():
    assert analyze.merge_cuts([5.0, 5.08, 8.0], 0.15) == [5.0, 8.0]
    assert analyze.merge_cuts([5.0, 5.08, 8.0], 0) == [5.0, 5.08, 8.0]


def test_flash_merged(flash, tmp_path):
    raw = analyze.analyze(flash, tmp_path / "raw", merge=0)
    merged = analyze.analyze(flash, tmp_path / "m")
    assert raw["shots"]["raw_detections"] == 2 and raw["shots"]["cuts"] == 2
    assert merged["shots"]["raw_detections"] == 2 and merged["shots"]["cuts"] == 1
    assert merged["cuts"][0] == pytest.approx(5.0, abs=0.1)


def test_bad_region(three_colours, tmp_path):
    with pytest.raises(analyze.VeditError):
        analyze.analyze(three_colours, tmp_path / "x", regions=["0.6:0.2"])
