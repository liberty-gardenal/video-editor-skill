"""Overlays (top/full/card) and the lower layout: validation (pure) and rendering (ffmpeg)."""

from __future__ import annotations

import json
import subprocess

import pytest

from conftest import _ff
from vedit import cut, probe, textproc, util
from vedit import edl as edlmod

FPS = 30
BASE = "0x2060c0"  # blue-ish base
OVER = "0xe02020"  # red overlay


def write(tmp_path, edl, name="e.json"):
    p = tmp_path / name
    p.write_text(json.dumps(edl), encoding="utf-8")
    return p


def base_edl(**kw):
    e = {"source": "b.mp4", "fps": FPS, "clips": [{"id": "a", "in": 0, "out": 6}]}
    e.update(kw)
    return e


def err(tmp_path, edl):
    with pytest.raises(util.VeditError) as ei:
        edlmod.load_edl(write(tmp_path, edl))
    return str(ei.value)


def ov(**kw):
    return {"source": "x.png", "at": 1, "dur": 1, **kw}


# ------------------------------------------------------------------ validation
@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda e: e["clips"][0].update(layout="lower", split_at=0.1), "'split_at' deve ficar entre 0.25 e 0.6"),
        (lambda e: e["clips"][0].update(split_at="x"), "'split_at' precisa ser um número"),
        (lambda e: e["clips"][0].update(caption_y=1.5), "'caption_y' deve ficar entre 0 e 1"),
        (lambda e: e.update(overlays="x"), "'overlays' da EDL deve ser uma lista"),
        (lambda e: e.update(overlays=[5]), "Overlay #1 da EDL deve ser um objeto"),
        (lambda e: e.update(overlays=[{"at": 1, "dur": 1}]), "Overlay #1: 'source' é obrigatório"),
        (lambda e: e.update(overlays=[{"source": "x.png", "dur": 1}]), "Overlay #1: falta 'at'"),
        (lambda e: e.update(overlays=[ov(), ov(at=3, dur=0)]), "Overlay #2: 'dur' deve ser maior que 0"),
        (lambda e: e.update(overlays=[ov(at=-1)]), "Overlay #1: 'at' deve ficar entre"),
        (lambda e: e.update(overlays=[ov(region="meio")]), "Overlay #1: 'region' desconhecida 'meio'"),
        (lambda e: e.update(overlays=[ov(source="x.mp4", **{"in": -1})]), "Overlay #1: 'in' deve ficar entre"),
        (lambda e: e.update(overlays=[ov(**{"in": 1})]), "'in' só vale para vídeo"),
        (lambda e: e.update(overlays=[ov(region="top", height=0.9)]), "'height' deve ficar entre"),
        (lambda e: e.update(overlays=[ov(region="top", feather=-1)]), "'feather' deve ficar entre"),
        (lambda e: e.update(overlays=[ov(crop_x=2)]), "'crop_x' deve ficar entre"),
        (lambda e: e.update(overlays=[ov(region="card", width=2)]), "'width' deve ficar entre"),
        (lambda e: e.update(overlays=[ov(region="card", y=0)]), "'y' deve ficar entre"),
        (lambda e: e.update(overlays=[ov(region="full", height=0.4)]), "'height' só vale com region 'top'"),
        (lambda e: e.update(overlays=[ov(region="top", width=0.5)]), "'width' só vale com region 'card'"),
        (lambda e: e.update(overlays=[ov(zoom=9)]), "Overlay #1: 'zoom' deve ficar entre"),
        (lambda e: e.update(overlays=[ov(zoom={"from": 1})]), "'zoom' em rampa precisa de 'from' e 'to'"),
        (lambda e: e.update(overlays=[ov(zoom="x")]), "Overlay #1: 'zoom' deve ser um número"),
        (lambda e: e.update(overlays=[ov(at=1, dur=2), ov(at=5, dur=1), ov(at=2.5, dur=1)]),
         "Overlays #1 e #3 se sobrepõem"),
    ],
)  # fmt: skip
def test_validation_errors(tmp_path, mutate, needle):
    e = base_edl()
    mutate(e)
    assert needle in err(tmp_path, e)


def test_lower_layout_and_defaults_accepted(tmp_path):
    e = base_edl(overlays=[ov(), ov(at=3, dur=1, region="top", height=0.45, feather=0, zoom=1.2)])
    e["clips"][0].update(layout="lower", split_at=0.5, caption_y=0.9)
    edlmod.load_edl(write(tmp_path, e))
    assert edlmod.split_at({}) == 0.45
    # defaults: still gets a slow push-in, video does not
    assert edlmod.overlay_zoom({"source": "a.png"}) == (1.0, 1.08)
    assert edlmod.overlay_zoom({"source": "a.mp4"}) == (1.0, 1.0)


def test_touching_overlays_ok(tmp_path):
    edlmod.load_edl(write(tmp_path, base_edl(overlays=[ov(at=1, dur=1), ov(at=2, dur=1)])))


def test_overlay_past_timeline_end(tmp_path):
    e = edlmod.load_edl(write(tmp_path, base_edl(overlays=[ov(at=5.5, dur=1)])))
    tl = edlmod.timeline(e, FPS)
    with pytest.raises(util.VeditError, match="Overlay #1: at \\+ dur .* passa do fim"):
        edlmod.check_overlays_timeline(e, tl, FPS)


def warnings_for(tmp_path, e):
    e = edlmod.load_edl(write(tmp_path, e))
    return edlmod.edl_warnings(e, edlmod.timeline(e, FPS), FPS)


def test_warn_lower_without_top(tmp_path):
    e = base_edl(overlays=[ov(region="top", at=1, dur=1)])
    e["clips"][0]["layout"] = "lower"
    w = warnings_for(tmp_path, e)
    assert len(w) == 1 and "sem overlay 'top'" in w[0] and "'a'" in w[0]


def test_no_warning_when_top_covers_lower(tmp_path):
    e = base_edl(overlays=[ov(region="top", at=0, dur=3), ov(region="top", at=3, dur=3)])
    e["clips"][0]["layout"] = "lower"
    assert warnings_for(tmp_path, e) == []


def test_warn_top_over_non_lower(tmp_path):
    w = warnings_for(tmp_path, base_edl(overlays=[ov(region="top")]))
    assert len(w) == 1 and "vai cobrir o rosto" in w[0]
    assert warnings_for(tmp_path, base_edl(overlays=[ov(region="card"), ov(region="full", at=3)])) == []


def test_metrics_overlays(tmp_path):
    e = base_edl(overlays=[ov(at=2, dur=1), ov(at=4, dur=1)])
    m = textproc.metrics(write(tmp_path, e))
    assert m["overlays"] == 2
    assert m["overlays_per_min"] == 20.0
    assert m["overlays_per_10s"] == 3.33
    assert m["longest_without_visual_change"] == 2.0
    assert "overlays" not in textproc.metrics(write(tmp_path, base_edl(), "n.json"))


# ----------------------------------------------------------------------- media
def solid_video(path, color, size="320x240", dur=8):
    _ff("-f", "lavfi", "-i", f"color=c={color}:s={size}:r={FPS}:d={dur}",
        "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={dur}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-c:a", "aac", "-shortest", path)  # fmt: skip


def solid_png(path, color, size="400x300"):
    _ff("-f", "lavfi", "-i", f"color=c={color}:s={size}", "-frames:v", "1", path)


@pytest.fixture(scope="module")
def solids(tmp_path_factory):
    d = tmp_path_factory.mktemp("solids")
    solid_video(d / "base.mp4", BASE)
    solid_video(d / "red.mp4", OVER, dur=1)
    solid_png(d / "red.png", OVER)
    solid_png(d / "wide.png", "0x20c020", size="800x400")
    return d


def render(tmp_path, solids, clips, overlays=None, name="o.mp4", **extra):
    edl = {"source": str(solids / "base.mp4"), "fps": FPS, "output": {"width": 540, "height": 960},
           "clips": clips, **extra}  # fmt: skip
    if overlays is not None:
        edl["overlays"] = [{**o, "source": str(solids / o["source"])} for o in overlays]
    p = write(tmp_path, edl, name.replace(".mp4", ".json"))
    out = tmp_path / name
    res = cut.render(p, out)
    return out, res


def pixel(video, t, fx, fy, w=540, h=960):
    """RGB at fractional position (fx, fy) of the frame at time t."""
    proc = subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-nostdin", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
         "-vf", f"format=rgb24,crop=1:1:{int(fx * w)}:{int(fy * h)}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    )  # fmt: skip
    assert len(proc.stdout) == 3
    return tuple(proc.stdout)


def near(a, b, tol=40):
    return all(abs(x - y) <= tol for x, y in zip(a, b, strict=False))


CLIP = [{"id": "a", "in": 0, "out": 6, "layout": "cover"}]


def test_base_color_reference(tmp_path, solids):
    out, _ = render(tmp_path, solids, CLIP)
    ref = pixel(out, 1.0, 0.5, 0.5)
    assert near(ref, (0x20, 0x60, 0xC0), 25)


def test_top_overlay_covers_top_only(tmp_path, solids):
    out, res = render(tmp_path, solids, CLIP, [{"source": "red.png", "at": 2, "dur": 2, "region": "top"}])
    base = pixel(out, 1.0, 0.5, 0.5)
    assert res["overlays"] == 1
    assert near(pixel(out, 3.0, 0.5, 0.2), (0xE0, 0x20, 0x20), 30)  # top covered
    assert near(pixel(out, 3.0, 0.5, 0.8), base, 12)  # bottom still base
    assert near(pixel(out, 1.0, 0.5, 0.2), base, 12)  # before
    assert near(pixel(out, 4.5, 0.5, 0.2), base, 12)  # after


def test_top_feather_blends_bottom_edge(tmp_path, solids):
    out, _ = render(tmp_path, solids, CLIP, [{"source": "red.png", "at": 2, "dur": 2, "region": "top"}])
    base = pixel(out, 1.0, 0.5, 0.5)
    edge = pixel(out, 3.0, 0.5, 0.45 - 4 / 960)  # last rows of the window: mostly base
    assert not near(edge, (0xE0, 0x20, 0x20), 30) and not near(edge, base, 6)
    hard, _ = render(tmp_path, solids, CLIP, [{"source": "red.png", "at": 2, "dur": 2, "region": "top",
                                               "feather": 0}], name="hard.mp4")  # fmt: skip
    assert near(pixel(hard, 3.0, 0.5, 0.45 - 4 / 960), (0xE0, 0x20, 0x20), 30)


def test_full_overlay_window(tmp_path, solids):
    out, _ = render(tmp_path, solids, CLIP, [{"source": "red.mp4", "at": 2, "dur": 1.5, "region": "full"}])
    base = pixel(out, 1.0, 0.5, 0.5)
    red = (0xE0, 0x20, 0x20)
    for fx, fy in ((0.5, 0.05), (0.5, 0.5), (0.5, 0.95)):
        assert near(pixel(out, 2.5, fx, fy), red, 30)
        assert near(pixel(out, 1.9, fx, fy), base, 12)
        assert near(pixel(out, 3.8, fx, fy), base, 12)
    # video shorter than dur (1 s vs 1.5 s) holds its last frame
    assert near(pixel(out, 3.4, 0.5, 0.5), red, 30)


def test_card_overlay_dims_base(tmp_path, solids):
    out, _ = render(tmp_path, solids, CLIP, [{"source": "red.png", "at": 2, "dur": 2, "region": "card"}])
    base = pixel(out, 1.0, 0.5, 0.5)
    assert near(pixel(out, 3.0, 0.5, 0.36), (0xE0, 0x20, 0x20), 30)  # card centre
    around = pixel(out, 3.0, 0.5, 0.9)
    assert sum(around) < sum(base) - 40  # dimmed
    assert max(around) - min(around) < max(base) - min(base) - 40  # desaturated
    assert near(pixel(out, 1.0, 0.5, 0.9), base, 12)
    assert near(pixel(out, 4.5, 0.5, 0.9), base, 12)
    assert near(pixel(out, 3.0, 0.03, 0.36), around, 25)  # outside the 78% width


def test_card_keeps_aspect(tmp_path, solids):
    # 2:1 still at 78% of 540 wide is ~421x210: rows far from the centre are not covered
    out, _ = render(tmp_path, solids, CLIP, [{"source": "wide.png", "at": 2, "dur": 1, "region": "card"}])
    green = (0x20, 0xC0, 0x20)
    assert near(pixel(out, 2.5, 0.5, 0.36), green, 30)
    assert not near(pixel(out, 2.5, 0.5, 0.36 + 0.16), green, 40)  # 154 px below centre > 105 px half-height


def test_still_zoom_ramp_renders(tmp_path, solids):
    out, _ = render(tmp_path, solids, CLIP, [{"source": "red.png", "at": 1, "dur": 2, "region": "full",
                                              "zoom": {"from": 1.0, "to": 1.5}}])  # fmt: skip
    assert near(pixel(out, 2.0, 0.5, 0.5), (0xE0, 0x20, 0x20), 30)
    out2, _ = render(tmp_path, solids, CLIP, [{"source": "red.png", "at": 1, "dur": 2}], name="d.mp4")
    assert near(pixel(out2, 2.0, 0.5, 0.5), (0xE0, 0x20, 0x20), 30)  # default still push-in


def test_lower_layout_puts_speaker_in_bottom(tmp_path, solids):
    # source: left half red, right half blue; cover at crop_x 0.5 keeps the seam in the middle.
    src = tmp_path / "halves.mp4"
    _ff("-f", "lavfi", "-i", f"color=c=0xe02020:s=160x240:r={FPS}:d=3", "-f", "lavfi",
        "-i", f"color=c=0x20c020:s=160x240:r={FPS}:d=3", "-filter_complex", "[0][1]hstack",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", src)  # fmt: skip
    edl = {"source": str(src), "fps": FPS, "output": {"width": 540, "height": 960},
           "clips": [{"id": "a", "in": 0, "out": 2, "layout": "lower", "crop_x": 0.5}]}  # fmt: skip
    out = tmp_path / "l.mp4"
    cut.render(write(tmp_path, edl), out)
    red, green = (0xE0, 0x20, 0x20), (0x20, 0xC0, 0x20)
    assert near(pixel(out, 1.0, 0.25, 0.8), red, 30) and near(pixel(out, 1.0, 0.75, 0.8), green, 30)
    top_l, top_r = pixel(out, 1.0, 0.25, 0.1), pixel(out, 1.0, 0.75, 0.1)
    assert max(top_l) < 200 and not near(top_l, red, 30)  # darkened, blurred filler
    assert top_l[0] > top_l[1] and top_r[1] > top_r[0]  # same shot's colours, not black
    assert sum(top_l) > 60


def test_lower_with_split_at(tmp_path, solids):
    out, _ = render(tmp_path, solids, [{"id": "a", "in": 0, "out": 3, "layout": "lower", "split_at": 0.6}],
                    [{"source": "red.png", "at": 0, "dur": 3, "region": "top", "height": 0.6, "feather": 0}])  # fmt: skip
    assert near(pixel(out, 1.0, 0.5, 0.5), (0xE0, 0x20, 0x20), 30)
    assert near(pixel(out, 1.0, 0.5, 0.8), (0x20, 0x60, 0xC0), 30)


def test_many_overlays_and_av_length(tmp_path, solids):
    clips = [{"id": "a", "in": 0, "out": 7, "layout": "cover"}]
    regions = ("top", "full", "card")
    ovs = [{"source": "red.png", "at": 0.5 + 0.5 * k, "dur": 0.4, "region": regions[k % 3]} for k in range(12)]
    plain, _ = render(tmp_path, solids, clips, name="plain.mp4")
    out, res = render(tmp_path, solids, clips, ovs, name="many.mp4")
    assert res["overlays"] == 12
    a, b = probe.probe(plain, audio_analysis=False), probe.probe(out, audio_analysis=False)
    assert a["nb_frames"] == b["nb_frames"] == 210
    assert abs(a["duration"] - b["duration"]) < 0.04
    assert abs(b["audio_duration"] - b["duration"]) < 0.04
    assert abs(a["audio_duration"] - b["audio_duration"]) < 0.04
    # 12th overlay (k=11 -> card) at 6.0s, and a gap between overlays shows base
    assert near(pixel(out, 6.2, 0.5, 0.36), (0xE0, 0x20, 0x20), 30)
    assert near(pixel(out, 0.95, 0.5, 0.2), pixel(out, 0.2, 0.5, 0.2), 12)


def test_overlay_past_end_fails_at_render(tmp_path, solids):
    with pytest.raises(util.VeditError, match="passa do fim da timeline"):
        render(tmp_path, solids, CLIP, [{"source": "red.png", "at": 5.5, "dur": 1}])
