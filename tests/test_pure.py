"""Pure-Python tests (no ffmpeg needed): captions, digest, geometry, EDL, ASS parsing."""

from __future__ import annotations

import importlib.util
import json

import pytest

from vedit import captions, cut, textproc, util
from vedit import edl as edlmod

TL = [
    {"index": 0, "id": "c1", "in": 10.0, "out": 14.0, "duration": 4.0, "offset": 0.0},
    {"index": 1, "id": "c2", "in": 30.0, "out": 33.0, "duration": 3.0, "offset": 4.0},
]


def W(w, t, e=None):
    return {"w": w, "t": t, "e": e if e is not None else t + 0.3}


def test_remap_drops_outside_and_shifts():
    words = [W("fora", 5), W("a", 10.5), W("b", 13.5), W("meio", 20), W("c", 30.2)]
    got = captions.remap_words(words, TL)
    assert [w["w"] for w in got] == ["a", "b", "c"]
    assert got[0]["t"] == pytest.approx(0.5)
    assert got[2]["t"] == pytest.approx(4.2)


def test_blocks_never_cross_clip_and_no_overlap():
    words = [W(f"w{i}", 10 + i * 0.5) for i in range(7)] + [W(f"x{i}", 30 + i * 0.4) for i in range(4)]
    blocks = captions.build_blocks(words, TL, max_words=3)
    for a, b in zip(blocks, blocks[1:], strict=False):
        assert a["end"] <= b["start"] + 1e-9
    for b in blocks:
        assert len(b["text"].split()) <= 3
        assert b["end"] > b["start"]
        c = TL[b["clip"]]
        assert c["offset"] - 1e-9 <= b["start"] and b["end"] <= c["offset"] + c["duration"] + 1e-9
    assert not any("w" in b["text"] and "x" in b["text"] for b in blocks)


def test_group_by_punctuation_and_percent_join():
    words = [W("isso", 10), W("é", 10.3), W("100", 10.6), W("%", 10.9), W("certo.", 11.2), W("Sim", 11.6)]
    blocks = captions.build_blocks(words, TL, max_words=5)
    texts = [b["text"] for b in blocks]
    assert "isso é 100% certo." in texts and "Sim" in texts


def test_weightless_single_word_merged():
    words = [W("vamos", 10), W("embora.", 10.3), W("de", 10.8), W("casa", 11.1), W("agora", 11.4)]
    blocks = captions.build_blocks(words, TL, max_words=3)
    assert all(b["text"].lower() not in ("de", "a", "o") for b in blocks)
    assert any(b["text"].startswith("de casa") for b in blocks)


def test_min_duration_when_room():
    words = [W("oi", 10, 10.05), W("tchau", 11.5, 11.8)]
    blocks = captions.build_blocks(words, TL, max_words=1)
    assert blocks[0]["end"] - blocks[0]["start"] >= 0.25 - 1e-9


def test_write_ass_srt_and_parse(tmp_path):
    from vedit import burn

    blocks = [{"start": 0.0, "end": 1.0, "text": "olá mundo", "clip": 0}]
    ass = tmp_path / "a.ass"
    captions.write_ass(blocks, ass, "viral", 1080, 1920, 0.7, "Arial")
    parsed = burn.parse_ass(ass)
    assert parsed["res"] == {"w": 1080, "h": 1920}
    assert parsed["events"][0]["text"] == "OLÁ MUNDO"
    assert parsed["events"][0]["pos"] == (540.0, 1344.0)
    assert "\\fad" not in ass.read_text()  # hard cut, no fade
    srt = tmp_path / "a.srt"
    captions.write_srt(blocks, srt)
    assert "00:00:00,000 --> 00:00:01,000" in srt.read_text()


def test_make_captions_files(tmp_path):
    wj = tmp_path / "w.json"
    wj.write_text(json.dumps({"words": [W("oi", 1.0), W("mundo", 1.4)]}))
    edl = tmp_path / "e.json"
    edl.write_text(json.dumps({"source": "x.mp4", "fps": 30, "clips": [{"in": 0.5, "out": 3.0}]}))
    res = captions.make_captions(wj, edl, tmp_path / "o.ass", srt=True, style="limpo")
    assert res["blocks"] == 1 and (tmp_path / "o.srt").exists()


def test_digest_compact(tmp_path):
    words = [W(f"p{i}", i * 0.4) for i in range(200)]
    words[50]["w"] = "fim."
    wj = tmp_path / "w.json"
    wj.write_text(json.dumps({"language": "pt", "duration": 80, "words": words}))
    text = textproc.digest(wj, every=15)
    lines = text.strip().splitlines()
    assert lines[1].startswith("[00:00.0] ")
    assert 3 <= len(lines) <= 12
    win = textproc.digest(wj, windows=[(10, 12)])
    assert "p25@10.00" in win and "p31@" not in win


# -------------------------------------------------------------------- geometry
def test_cover_crop_clamped_and_even():
    for cx in (-1, 0, 0.5, 1, 2):
        cw, ch, x, y = cut.cover_crop(1920, 1080, 1080, 1920, cx)
        assert cw % 2 == 0 and ch % 2 == 0 and x % 2 == 0 and y % 2 == 0
        assert 0 <= x and x + cw <= 1920 and y + ch <= 1080
        assert abs(cw / ch - 9 / 16) < 0.01
    assert cut.cover_crop(1920, 1080, 1080, 1920, 0)[2] == 0
    assert cut.cover_crop(1920, 1080, 1080, 1920, 1)[2] + cut.cover_crop(1920, 1080, 1080, 1920, 1)[0] == 1920


def test_split_geometry_and_vertical_refusal():
    top, bot, _ = cut.split_geometry(1920, 1080, 1080, 1920, 0.5)
    assert top + bot == 1920 and top == 608
    with pytest.raises(util.VeditError):
        cut.split_geometry(720, 1280, 1080, 1920, 0.5)


def test_keyframes_piecewise():
    kf = edlmod.keyframes([{"t": 1.0, "x": 0.3}, {"t": 2.0, "x": 0.7}], 90, 30)
    assert kf == [(0, 0.3), (30, 0.3), (60, 0.7)] or kf == [(0, 0.3), (60, 0.7)]
    assert kf[0][0] == 0
    assert edlmod.keyframes(0.4, 90, 30) == [(0, 0.4)]


def test_timeline_frame_snapping():
    edl = {"clips": [{"in": 1.01, "out": 2.52}, {"in": 5, "out": 6}]}
    tl = edlmod.timeline(edl, 30)
    assert tl[0]["frames"] == round(2.52 * 30) - round(1.01 * 30)
    assert tl[1]["offset"] == pytest.approx(tl[0]["duration"])


def test_ebur128_parser():
    txt = "noise\n  Summary:\n\n  Integrated loudness:\n    I:         -14.2 LUFS\n    Threshold: -24.2 LUFS\n\n" \
          "  Loudness range:\n    LRA:         3.1 LU\n\n  True peak:\n    Peak:       -1.6 dBFS\n"  # fmt: skip
    r = util.parse_ebur128(txt)
    assert r == {"integrated_lufs": -14.2, "lra": 3.1, "true_peak_dbtp": -1.6}


def test_filter_name_parsing_is_whole_word(monkeypatch):
    class R:
        stdout = (
            "Filters:\n  T.. = Timeline support\n"
            " ... lowpass           A->A       Apply a low-pass filter.\n"
            " ... bass              A->A       Boost or cut lower frequencies.\n"
        )

    util.filters_of.cache_clear()
    monkeypatch.setattr(util.subprocess, "run", lambda *a, **k: R())
    names = util.filters_of("fake-ffmpeg")
    assert "ass" not in names and "bass" in names and "lowpass" in names
    util.filters_of.cache_clear()


@pytest.mark.skipif(importlib.util.find_spec("numpy") is None, reason="numpy ausente")
def test_refine_starts_moves_to_onset():
    import numpy as np

    from vedit import transcribe

    sr = 16000
    audio = np.zeros(sr * 2, dtype=np.float32)
    t = np.arange(int(0.5 * sr)) / sr
    audio[int(1.0 * sr) : int(1.5 * sr)] = 0.3 * np.sin(2 * np.pi * 300 * t)
    words = [{"w": "a", "t": 0.85, "e": 1.5}, {"w": "b", "t": 1.6, "e": 1.9}]
    out = transcribe.refine_starts(words, audio, sr)
    assert 0.98 <= out[0]["t"] <= 1.03
    assert out[1]["t"] >= out[0]["t"] and out[1]["t"] == pytest.approx(1.6)


# ------------------------------------------------------- fps / EDL validation
def test_fps_forms():
    from fractions import Fraction

    assert edlmod.fps_fraction("30000/1001") == Fraction(30000, 1001)
    assert edlmod.fps_fraction(29.97) == Fraction(30000, 1001)
    assert edlmod.fps_fraction("25") == 25 and edlmod.fps_str(edlmod.fps_fraction(25.0)) == "25"
    assert edlmod.fps_for_edl(Fraction(30000, 1001)) == "30000/1001" and edlmod.fps_for_edl(Fraction(25)) == 25
    for bad in ("abc", "0", -5, "1/0", True, 9999):
        with pytest.raises(util.VeditError):
            edlmod.fps_fraction(bad)


def _edl(tmp_path, data):
    p = tmp_path / "e.json"
    p.write_text(json.dumps(data))
    return p


@pytest.mark.parametrize(
    ("edl", "match"),
    [
        ({"source": "a.mp4", "clips": [{"id": "x", "out": 3}]}, "x.*'in'"),
        ({"source": "a.mp4", "clips": [{"id": "x", "in": 3, "out": 3}]}, "x.*'out'.*maior"),
        ({"source": "a.mp4", "clips": [{"id": "x", "in": 1, "out": 3, "layout": "wide"}]}, "Layout.*x"),
        ({"source": "a.mp4", "clips": [{"id": "x", "in": 1, "out": 3, "crop_x": [{"x": 0.2}]}]}, "'t' e 'x'"),
        ({"source": "a.mp4", "clips": [{"id": "x", "in": 1, "out": 3, "speed": 9}]}, "speed"),
        ({"source": "a.mp4", "clips": [{"id": "x", "in": 1, "out": 3, "zoom": {"from": 1}}]}, "from.*to"),
        ({"source": "a.mp4", "clips": [{"id": "x", "in": 1, "out": 3, "zoom": 0.5}]}, "zoom"),
        ({"clips": [{"id": "x", "in": 1, "out": 3}]}, "sem 'source'"),
        ({"source": "a.mp4", "clips": [{"id": "x", "in": "abc", "out": 3}]}, "número"),
        ({"source": "a.mp4", "clips": []}, "ao menos um clipe"),
        ({"source": "a.mp4", "fps": "x", "clips": [{"in": 1, "out": 3}]}, "fps"),
        ([1, 2], "objeto"),
    ],
)
def test_malformed_edl_is_a_friendly_error(tmp_path, edl, match):
    with pytest.raises(util.VeditError, match=match):
        edlmod.load_edl(_edl(tmp_path, edl))


def test_edl_source_optional_when_every_clip_has_one(tmp_path):
    edl = edlmod.load_edl(_edl(tmp_path, {"clips": [{"in": 0, "out": 1, "source": "a.mp4"}]}))
    assert edlmod.source_key(edl, edl["clips"][0]) == "a.mp4"


def test_timeline_speed_and_zoom_range():
    edl = {"clips": [{"in": 0, "out": 2, "speed": 0.5}, {"in": 0, "out": 2, "speed": 2, "zoom": {"from": 1, "to": 1.1}}]}
    tl = edlmod.timeline(edl, 25)
    assert [t["frames"] for t in tl] == [100, 25] and [t["src_frames"] for t in tl] == [50, 50]
    assert tl[1]["offset"] == pytest.approx(4.0)
    assert edlmod.zoom_range(edl["clips"][1]) == (1.0, 1.1) and edlmod.zoom_range({"zoom": 1.3}) == (1.3, 1.3)


def test_remap_words_respects_speed_and_source():
    edl = {"source": "a.mp4", "clips": [{"in": 10, "out": 14, "speed": 2}, {"in": 0, "out": 2, "source": "b.mp4"}]}
    tl = captions.mark_word_clips(edlmod.timeline(edl, 25), edl)
    got = captions.remap_words([W("x", 12.0, 12.2), W("y", 0.5, 0.7)], tl)
    assert [w["w"] for w in got] == ["x"] and got[0]["t"] == pytest.approx(1.0)


# -------------------------------------------------------------- highlight
def test_highlight_matching_and_ass_colour_is_bgr(tmp_path):
    assert captions.norm_word("Ação,") == "acao" and captions.norm_word("100%") == "100"
    assert captions.parse_highlight("Ação, dois palavra tres") == {"acao", "dois", "palavra", "tres"}
    assert captions.ass_color("#FFD400") == "&H00D4FF&"
    blocks = [{"start": 0, "end": 1, "text": "a ação, boa", "words": ["a", "ação,", "boa"], "clip": 0}]
    ass = tmp_path / "h.ass"
    captions.write_ass(blocks, ass, "limpo", 1080, 1920, 0.62, "Arial", highlight="ACAO", accent="#10203A")
    line = [ln for ln in ass.read_text().splitlines() if ln.startswith("Dialogue")][0]
    assert line.endswith("a {\\1c&H3A2010&}ação{\\1c&HFFFFFF&} boa")
    plain = tmp_path / "p.ass"
    captions.write_ass(blocks, plain, "limpo", 1080, 1920, 0.62, "Arial")
    assert "\\1c" not in plain.read_text()


def test_captions_default_y_is_062():
    import inspect

    assert inspect.signature(captions.make_captions).parameters["y"].default == 0.62
    from vedit import cli

    args = cli.build_parser().parse_args(["captions", "w.json", "--edl", "e.json", "-o", "o.ass"])
    assert args.y == 0.62 and args.accent == "#FFD400" and args.highlight is None


# ------------------------------------------------------------------- CLI
def test_every_subcommand_accepts_json():
    import argparse

    from vedit import cli

    ap = cli.build_parser()
    subs = next(a for a in ap._actions if isinstance(a, argparse._SubParsersAction)).choices
    assert {"extract-audio", "mux"} <= set(subs)
    missing = [n for n, sp in subs.items() if "--json" not in sp._option_string_actions]
    assert not missing


@pytest.mark.parametrize(
    "argv",
    [["sheet", "v.mp4", "-o", "s.jpg", "--start", "abc"], ["silences", "m.mp4", "--end", "x:y"],
     ["digest", "w.json", "--windows", "12"], ["captions", "w", "--edl", "e", "-o", "o", "--accent", "azul"]],
)
def test_bad_argument_values_are_argparse_errors(argv, capsys):
    from vedit import cli

    with pytest.raises(SystemExit) as e:
        cli.build_parser().parse_args(argv)
    assert e.value.code == 2
    assert "Traceback" not in capsys.readouterr().err


def test_unexpected_exception_is_short_message(monkeypatch, capsys):
    from vedit import cli

    def boom(args):
        raise RuntimeError("falhou feio")

    monkeypatch.setattr(cli, "cmd_loudness", boom)
    monkeypatch.delenv("VEDIT_DEBUG", raising=False)
    assert cli.main(["loudness", "x.mp4"]) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err and "VEDIT_DEBUG=1" in err and "falhou feio" in err


def test_platform_limits():
    from vedit import platforms

    assert platforms.PLATFORMS["reels"]["max_s"] == 180
    assert platforms.PLATFORMS["tiktok"]["max_mb"] == 500


def test_malformed_edl_cli_has_no_traceback(tmp_path):
    from test_doctor import run

    edl = _edl(tmp_path, {"source": "a.mp4", "clips": [{"id": "x", "in": 5, "out": 1}]})
    r = run("cut", "--edl", str(edl), "-o", str(tmp_path / "o.mp4"))
    assert r.returncode == 1 and "Traceback" not in r.stderr and "'x'" in r.stderr
