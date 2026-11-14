"""Tests that need ffmpeg: probe, cut, burn, master, edges, verify, sheet, mix, silences."""

from __future__ import annotations

import importlib.util
import json
import subprocess

import pytest

from conftest import make_av
from vedit import audio, burn, captions, cut, probe, sheet, util, verify
from vedit import edl as edlmod

HAS_PIL = importlib.util.find_spec("PIL") is not None
FPS = 30
# Tag frames as PQ/bt2020 (setparams works on old and new ffmpeg; -color_trc alone does not).
HDR_TAGS = [
    "-vf", "setparams=color_trc=smpte2084:colorspace=bt2020nc:color_primaries=bt2020",
    "-pix_fmt", "yuv420p10le",
]  # fmt: skip


def frames_of(path):
    return probe.probe(path, audio_analysis=False)["nb_frames"]


def good_clip(media, make_edl, layout="cover", **extra):
    clip = {"id": "c1", "in": 3.0, "out": 7.0, "layout": layout, "crop_x": 0.5, **extra}
    return make_edl(media["landscape"], [clip])


# ---------------------------------------------------------------------- probe
def test_probe_landscape(media):
    p = probe.probe(media["landscape"])
    assert (p["width"], p["height"]) == (1920, 1080)
    assert p["avg_frame_rate"] == 30.0
    assert p["nb_frames"] == 600
    assert p["rotation"] == 0
    assert p["hdr"] is False
    assert p["audio_channels"] == 1
    assert p["integrated_lufs"] is not None


def test_probe_detects_hdr_and_real_fps(tmp_path):
    f = tmp_path / "hdr.mp4"
    make_av(
        f,
        "320x180",
        dur=2,
        extra=HDR_TAGS,
    )
    p = probe.probe(f, audio_analysis=False)
    assert p["hdr"] is True
    assert p["color_transfer"] == "smpte2084"


# ------------------------------------------------------------------------ cut
@pytest.mark.parametrize("layout", ["cover", "split", "fit"])
def test_cut_layouts_frame_exact(media, make_edl, tmp_path, layout):
    edl = make_edl(
        media["landscape"],
        [
            {"id": "a", "in": 1.01, "out": 3.49, "layout": layout, "crop_x": 0.2, "zoom": 1.2},
            {"id": "b", "in": 5.0, "out": 6.5, "layout": layout, "crop_x": 0.8},
        ],
    )
    out = tmp_path / "o.mp4"
    res = cut.render(edl, out)
    exp = round(3.49 * FPS) - round(1.01 * FPS) + round(6.5 * FPS) - round(5.0 * FPS)
    p = probe.probe(out, audio_analysis=False)
    assert (p["width"], p["height"]) == (1080, 1920)
    assert p["nb_frames"] == exp == res["frames"]
    assert p["pix_fmt"] == "yuv420p"
    assert abs(p["audio_duration"] - exp / FPS) < 0.05
    assert p["audio_sample_rate"] == 48000


def test_cut_crop_x_keyframes_and_preview(media, make_edl, tmp_path):
    edl = make_edl(
        media["landscape"],
        [{"id": "a", "in": 2, "out": 6, "layout": "cover",
          "crop_x": [{"t": 0, "x": 0.1}, {"t": 2.0, "x": 0.9}]}],
    )  # fmt: skip
    out = tmp_path / "p.mp4"
    cut.render(edl, out, preview=True)
    p = probe.probe(out, audio_analysis=False)
    assert (p["width"], p["height"]) == (540, 960)
    assert p["nb_frames"] == 120


def test_split_refuses_vertical_source(media, make_edl, tmp_path):
    edl = make_edl(media["vertical"], [{"in": 0, "out": 2, "layout": "split"}])
    with pytest.raises(util.VeditError, match="vertical"):
        cut.render(edl, tmp_path / "x.mp4")


@pytest.mark.parametrize("layout", ["cover", "fit"])
def test_vertical_source(media, make_edl, tmp_path, layout):
    edl = make_edl(media["vertical"], [{"in": 0, "out": 2, "layout": layout}])
    out = tmp_path / "v.mp4"
    cut.render(edl, out)
    p = probe.probe(out, audio_analysis=False)
    assert (p["width"], p["height"]) == (1080, 1920)


def test_cut_hdr_to_sdr(tmp_path):
    src = tmp_path / "hdr.mp4"
    make_av(
        src,
        "640x360",
        dur=3,
        extra=HDR_TAGS,
    )
    edl = tmp_path / "e.json"
    edl.write_text(json.dumps({"source": str(src), "fps": 30, "clips": [{"in": 0, "out": 2}]}))
    out = tmp_path / "sdr.mp4"
    res = cut.render(edl, out)
    assert res["hdr_converted"]
    p = probe.probe(out, audio_analysis=False)
    assert p["hdr"] is False and p["pix_fmt"] == "yuv420p"


def test_cut_source_without_audio(tmp_path):
    src = tmp_path / "mute.mp4"
    subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi", "-i",
         "testsrc2=size=640x360:rate=30:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", src],
        check=True,
    )  # fmt: skip
    edl = tmp_path / "e.json"
    edl.write_text(json.dumps({"source": str(src), "fps": 30, "clips": [{"in": 0, "out": 1}]}))
    out = tmp_path / "o.mp4"
    cut.render(edl, out)
    assert probe.probe(out, audio_analysis=False)["has_audio"]


# ---------------------------------------------------------------------- burn
def _burn_inputs(media, make_edl, tmp_path):
    edl = good_clip(media, make_edl)
    clip = tmp_path / "clip.mp4"
    cut.render(edl, clip)
    words = [
        {"w": w, "t": 4.0 + i * 0.4, "e": 4.3 + i * 0.4} for i, w in enumerate("um dois tres quatro".split())
    ]
    wj = tmp_path / "w.json"
    wj.write_text(json.dumps({"words": words}))
    ass = tmp_path / "c.ass"
    captions.make_captions(wj, edl, ass, style="viral")
    return clip, ass


def test_burn_auto(media, make_edl, tmp_path):
    clip, ass = _burn_inputs(media, make_edl, tmp_path)
    if not (util.has_filter("ass") or util.has_filter("subtitles")) and not HAS_PIL:
        pytest.skip("sem libass e sem Pillow")
    out = tmp_path / "b.mp4"
    res = burn.burn(clip, ass, out)
    assert res["method"] == ("libass" if util.has_filter("ass") or util.has_filter("subtitles") else "pillow")
    assert frames_of(out) == frames_of(clip)


@pytest.mark.skipif(not HAS_PIL, reason="Pillow ausente")
def test_burn_pillow_fallback_draws_text(media, make_edl, tmp_path):
    clip, ass = _burn_inputs(media, make_edl, tmp_path)
    out = tmp_path / "b.mp4"
    res = burn.burn(clip, ass, out, force_fallback=True)
    assert res["method"] == "pillow"
    assert frames_of(out) == frames_of(clip)

    # a frame inside the first caption must differ from the clip without captions
    def grab(path, t):
        r = subprocess.run(
            [util.ffmpeg_path(), "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1",
             "-vf", "crop=900:300:90:1200", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            capture_output=True, check=True,
        )  # fmt: skip
        return r.stdout

    assert grab(out, 0.3) != grab(clip, 0.3)


# -------------------------------------------------------------- master/verify
def test_master_and_verify_pass(media, make_edl, tmp_path):
    edl = good_clip(media, make_edl)
    clip = tmp_path / "clip.mp4"
    cut.render(edl, clip)
    out = tmp_path / "m.mp4"
    res = audio.master(clip, out)
    assert abs(res["after"]["lufs"] - (-14.0)) <= 1.0
    p = probe.probe(out, audio_analysis=False)
    assert p["audio_sample_rate"] == 48000
    rep = verify.verify(out, platform="reels")
    assert rep["status"] != "falha", verify.format_report(rep)
    assert verify.faststart_ok(out) is True


def test_verify_fails_wrong_resolution(media, make_edl, tmp_path):
    edl = good_clip(media, make_edl)
    out = tmp_path / "prev.mp4"
    cut.render(edl, out, preview=True)
    rep = verify.verify(out)
    assert rep["status"] == "falha"
    assert any(c["id"] in ("resolution", "aspect") and c["status"] == "falha" for c in rep["checks"])


def test_verify_cli_exit_codes(media, make_edl, tmp_path):
    import os
    import sys

    edl = good_clip(media, make_edl)
    out = tmp_path / "prev.mp4"
    cut.render(edl, out, preview=True)
    env = dict(os.environ, PYTHONPATH=str(__import__("pathlib").Path(cut.__file__).parents[1]))
    r = subprocess.run([sys.executable, "-m", "vedit", "verify", str(out), "--json"], env=env,
                       capture_output=True, text=True)  # fmt: skip
    assert r.returncode == 1
    assert json.loads(r.stdout)["status"] == "falha"


def test_faststart_detection(media, tmp_path):
    slow = tmp_path / "slow.mp4"
    subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-y", "-i", str(media["vertical"]), "-c", "copy", slow],
        check=True,
    )  # no +faststart -> moov at the end
    assert verify.faststart_ok(slow) is False


# ---------------------------------------------------------------------- edges
def test_edges(media, make_edl, tmp_path):
    ok = tmp_path / "ok.mp4"
    cut.render(good_clip(media, make_edl), ok, preview=True)
    assert audio.edges(ok)["ok"]
    bad = tmp_path / "bad.mp4"  # starts in the middle of a tone burst
    edl = make_edl(media["landscape"], [{"in": 4.5, "out": 8.2}], name="bad.json")
    cut.render(edl, bad, preview=True)
    res = audio.edges(bad)
    assert not res["ok"] and not res["start"]["ok"]


# --------------------------------------------------------------- misc tools
def test_silences(media):
    res = audio.silences(media["landscape"])
    first = res["silences"][0]
    assert 2.3 < first["start"] < 2.7 and 3.8 < first["end"] < 4.2


def test_sheet_with_guides(media, tmp_path):
    guides = tmp_path / "g.json"
    guides.write_text(json.dumps([{"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.2}]))
    out = tmp_path / "s.jpg"
    res = sheet.make_sheet(media["landscape"], out, every=4, cols=3, width=240, guides=guides)
    assert out.exists() and out.stat().st_size > 1000
    assert res["frames"] == 5


def test_mix_exact_duration(media, tmp_path):
    voice = tmp_path / "v.wav"
    music = tmp_path / "m.wav"
    subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=300:d=6", voice],
        check=True,
    )
    subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=120:d=2", music],
        check=True,
    )
    out = tmp_path / "mix.wav"
    audio.mix(voice, music, out, duck=True)
    p = probe.probe(out, audio_analysis=False)
    assert abs(p["audio_duration"] - 6.0) < 0.05
    assert p["audio_sample_rate"] == 48000


# ------------------------------------------------------------ A/V length
def av_gap(path):
    p = probe.probe(path, audio_analysis=False)
    return abs(p["video_duration"] - p["audio_duration"])


def test_av_lengths_match_after_cut_burn_master(media, make_edl, tmp_path):
    edl = make_edl(
        media["landscape"],
        [{"id": "a", "in": 1.0, "out": 7.0}, {"id": "b", "in": 9.0, "out": 13.5, "speed": 1.5}],
    )
    clip, burned, mastered = tmp_path / "c.mp4", tmp_path / "b.mp4", tmp_path / "m.mp4"
    cut.render(edl, clip, preview=True)
    wj = tmp_path / "w.json"
    wj.write_text(json.dumps({"words": [{"w": "oi", "t": 1.5, "e": 1.9}, {"w": "tchau", "t": 2, "e": 2.4}]}))
    ass = tmp_path / "c.ass"
    captions.make_captions(wj, edl, ass)
    burn.burn(clip, ass, burned)
    audio.master(burned, mastered)
    for f in (clip, burned, mastered):
        assert av_gap(f) < 0.040, (f.name, av_gap(f))
    if HAS_PIL:
        pil = tmp_path / "bp.mp4"
        burn.burn(clip, ass, pil, force_fallback=True)
        assert av_gap(pil) < 0.040


def test_mux_and_extract_audio(media, make_edl, tmp_path):
    clip = tmp_path / "c.mp4"
    cut.render(good_clip(media, make_edl), clip, preview=True)
    wav = tmp_path / "voz.wav"
    res = audio.extract_audio(clip, wav, start=0.5, end=2.5)
    p = probe.probe(wav, audio_analysis=False)
    assert p["audio_sample_rate"] == 48000 and p["audio_codec"].startswith("pcm")
    assert abs(p["audio_duration"] - 2.0) < 0.02 and res["channels"] == 2
    long_wav = tmp_path / "long.wav"  # longer than the video -> must be trimmed
    subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=200:d=9", long_wav], check=True
    )
    out = tmp_path / "mux.mp4"
    audio.mux(clip, long_wav, out)
    m = probe.probe(out, audio_analysis=False)
    assert m["audio_codec"] == "aac" and m["audio_sample_rate"] == 48000 and m["codec"] == "h264"
    assert av_gap(out) < 0.040
    assert verify.faststart_ok(out) is True
    short_wav = tmp_path / "short.wav"  # shorter than the video -> must be padded
    subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=200:d=1", short_wav], check=True
    )
    audio.mux(clip, short_wav, out)
    assert av_gap(out) < 0.040


# ----------------------------------------------------- EDL: sources/speed/zoom
def test_multi_source_still_speed_zoom_ramp(media, tmp_path):
    still = tmp_path / "foto.png"
    subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=800x600", "-frames:v", "1",
         still],
        check=True,
    )  # fmt: skip
    mute = tmp_path / "mute.mp4"
    subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi", "-i",
         "testsrc2=size=640x360:rate=24:duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", mute],
        check=True,
    )  # fmt: skip
    edl = tmp_path / "edl.json"  # relative paths + no top-level source
    for f in (media["landscape"], media["vertical"]):
        (tmp_path / f.name).symlink_to(f)
    edl.write_text(json.dumps({
        "fps": 25,
        "clips": [
            {"id": "a", "source": "landscape.mp4", "in": 1, "out": 3, "zoom": {"from": 1.0, "to": 1.15}},
            {"id": "s", "source": "foto.png", "in": 0, "out": 1.5},
            {"id": "m", "source": "mute.mp4", "in": 0, "out": 2, "speed": 0.5, "layout": "split"},
            {"id": "v", "source": "vertical.mp4", "in": 0, "out": 2, "speed": 2, "layout": "fit"},
            {"id": "z", "source": "landscape.mp4", "in": 4, "out": 6, "layout": "split",
             "zoom": {"from": 1.0, "to": 1.2}, "crop_x": [{"t": 0, "x": 0.3}, {"t": 1, "x": 0.7}]},
        ],
    }))  # fmt: skip
    out = tmp_path / "o.mp4"
    res = cut.render(edl, out, preview=True)
    assert res["frames"] == 50 + 38 + 100 + 25 + 50 and res["sources"] == 4
    p = probe.probe(out, audio_analysis=False)
    assert p["nb_frames"] == res["frames"] and (p["width"], p["height"]) == (540, 960)
    assert p["fps"] == 25.0 and av_gap(out) < 0.040


def test_atempo_chain_covers_range():
    assert cut.atempo_chain(0.25) == "atempo=0.5,atempo=0.500000"
    assert cut.atempo_chain(4.0) == "atempo=2.0,atempo=2.000000"
    assert cut.atempo_chain(1.5) == "atempo=1.500000"


def test_cut_validates_out_against_source(media, make_edl, tmp_path):
    edl = make_edl(media["vertical"], [{"id": "fim", "in": 6, "out": 9}])  # source is 8 s
    with pytest.raises(util.VeditError, match="fim.*out"):
        cut.render(edl, tmp_path / "x.mp4")
    edl = make_edl(media["vertical"], [{"id": "tarde", "in": 9, "out": 10}], name="e2.json")
    with pytest.raises(util.VeditError, match="tarde.*in"):
        cut.render(edl, tmp_path / "x.mp4")


def test_fps_rational_and_float_forms_both_accepted(tmp_path):
    src = tmp_path / "ntsc.mp4"
    make_av(src, "320x180", dur=4, fps="30000/1001")
    assert probe.probe(src, audio_analysis=False)["fps_rational"] == "30000/1001"
    for form in ("30000/1001", 29.97):
        edl = tmp_path / "e.json"
        edl.write_text(json.dumps({"source": str(src), "fps": form, "clips": [{"in": 0, "out": 2}]}))
        out = tmp_path / "o.mp4"
        res = cut.render(edl, out, preview=True)
        assert res["frames"] == round(2 * 30000 / 1001)
        assert probe.probe(out, audio_analysis=False)["avg_frame_rate"] == pytest.approx(29.97, abs=0.005)
    edl.write_text(json.dumps({"source": str(src), "clips": [{"in": 0, "out": 2}]}))  # no fps: probed
    assert edlmod.resolve_fps(edlmod.load_edl(edl), edl) == pytest.approx(30000 / 1001)


def test_init_writes_probed_fps(tmp_path):
    src = tmp_path / "ntsc.mp4"
    make_av(src, "320x180", dur=2, fps="30000/1001")
    from vedit import workspace

    workspace.init_workspace(tmp_path / "ws", str(src))
    edl = json.loads((tmp_path / "ws" / "04-edl.json").read_text())
    assert edl["fps"] == "30000/1001"
    assert json.loads((tmp_path / "ws" / "00-probe.json").read_text())["fps_rational"] == "30000/1001"


# --------------------------------------------------------------- captions
@pytest.mark.skipif(not HAS_PIL, reason="Pillow ausente")
def test_pillow_fallback_colours_only_highlighted_word(tmp_path):
    from PIL import Image, ImageDraw, ImageFont

    blocks = [{"start": 0.0, "end": 1.0, "text": "um DOIS tres", "words": ["um", "dois", "tres"], "clip": 0}]
    ass = tmp_path / "h.ass"
    captions.write_ass(blocks, ass, "viral", 1080, 1920, 0.5, "Arial", highlight="Dóis", accent="#FFD400")
    ev = burn.parse_ass(ass)["events"][0]
    assert [c for _, c in ev["words"]] == [None, (255, 212, 0), None]
    img = burn.render_frame(Image, ImageDraw, ImageFont, (270, 480), ev, burn.parse_ass(ass)["style"],
                            {"w": 1080, "h": 1920}, "Arial")  # fmt: skip
    px = {c[:3] for _, c in img.getcolors(maxcolors=1_000_000) if c[3] == 255}
    assert (255, 212, 0) in px and (255, 255, 255) in px


@pytest.mark.skipif(not (util.has_filter("ass") or util.has_filter("subtitles")), reason="sem libass")
def test_libass_burn_with_highlight(media, make_edl, tmp_path):
    clip, _ = _burn_inputs(media, make_edl, tmp_path)
    wj = tmp_path / "w.json"
    edl = good_clip(media, make_edl)
    ass = tmp_path / "hl.ass"
    captions.make_captions(wj, edl, ass, highlight="DOIS,quatro")
    out = tmp_path / "hl.mp4"
    assert burn.burn(clip, ass, out)["method"] == "libass"
    assert frames_of(out) == frames_of(clip)


# ------------------------------------------------------------------ verify
def test_verify_edges_warning_vs_strict(media, make_edl, tmp_path):
    bad = tmp_path / "bad.mp4"  # starts in the middle of a tone burst
    edl = make_edl(media["landscape"], [{"in": 4.5, "out": 8.2}], name="bad.json")
    cut.render(edl, bad, preview=True)

    def edge_status(strict):
        rep = verify.verify(bad, strict_edges=strict)
        return next(c for c in rep["checks"] if c["id"] == "audio_edges")

    soft, hard = edge_status(False), edge_status(True)
    assert soft["status"] == "aviso" and "truncada" in soft["message"]
    assert hard["status"] == "falha"


def test_verify_handles_missing_true_peak(media, make_edl, tmp_path, monkeypatch):
    clip = tmp_path / "c.mp4"
    cut.render(good_clip(media, make_edl), clip, preview=True)
    real = verify.measure_loudness

    def fake(path, *a, **k):
        return {**real(path, *a, **k), "true_peak_dbtp": None}

    monkeypatch.setattr(verify, "measure_loudness", fake)
    rep = verify.verify(clip)
    tp = next(c for c in rep["checks"] if c["id"] == "true_peak")
    assert tp["status"] == "aviso"


def test_ffmpeg_extra_candidates_prefer_libass(monkeypatch, tmp_path):
    from vedit import util as u

    fake = tmp_path / "ffmpeg"
    fake.write_text("")
    fake.chmod(0o755)
    other = tmp_path / "other"
    other.write_text("")
    other.chmod(0o755)
    monkeypatch.delenv("VEDIT_FFMPEG", raising=False)
    monkeypatch.setattr(u, "_path_candidates", lambda n: [str(fake), str(other)])
    monkeypatch.setattr(u, "filters_of", lambda p: frozenset({"ass"}) if p == str(other) else frozenset())
    u.ffmpeg_path.cache_clear()
    try:
        assert u.ffmpeg_path() == str(other)
        monkeypatch.setenv("VEDIT_FFMPEG", str(fake))
        u.ffmpeg_path.cache_clear()
        assert u.ffmpeg_path() == str(fake)
    finally:
        u.ffmpeg_path.cache_clear()


def _alpha_overlay(path, size="720x1280", dur=8):
    subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi", "-i",
         f"color=c=red@0.5:s={size}:r=30:d={dur},format=yuva444p10le",
         "-c:v", "prores_ks", "-profile:v", "4444", str(path)],
        check=True,
    )  # fmt: skip


def test_composite_validations_and_render(media, tmp_path):
    from vedit import composite as comp

    ov = tmp_path / "ov.mov"
    _alpha_overlay(ov)
    out = tmp_path / "o.mp4"
    res = comp.composite(media["vertical"], ov, out)
    assert abs(res["duration"] - 8.0) < 0.1
    # overlay without alpha is refused
    with pytest.raises(util.VeditError, match="alpha"):
        comp.composite(media["vertical"], media["vertical"], tmp_path / "x.mp4")
    # resolution mismatch is refused
    ov2 = tmp_path / "ov2.mov"
    _alpha_overlay(ov2, size="360x640")
    with pytest.raises(util.VeditError, match="Resolução"):
        comp.composite(media["vertical"], ov2, tmp_path / "y.mp4")
