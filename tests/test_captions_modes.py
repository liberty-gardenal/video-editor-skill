"""Caption modes (palavra/karaoke), case, emphasis, per-clip y, card silence and pinned headline."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess

import pytest

from vedit import burn, captions, cut, probe, util

HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_LIBASS = util.has_filter("ass") or util.has_filter("subtitles")
ACCENT_TAG = r"\1c&H00D4FF&"  # #FFD400 in ASS BGR
WORDS = "ola mundo isto e um teste. outra frase aqui".split()


def _setup(tmp_path, clips=None, overlays=None, words=WORDS, step=0.4):
    wj = tmp_path / "w.json"
    ws = [{"w": w, "t": 1.0 + i * step, "e": 1.0 + i * step + 0.3} for i, w in enumerate(words)]
    wj.write_text(json.dumps({"words": ws}))
    edl = {"source": "x.mp4", "fps": 30, "clips": clips or [{"in": 0.5, "out": 6.0}]}
    if overlays:
        edl["overlays"] = overlays
    ep = tmp_path / "e.json"
    ep.write_text(json.dumps(edl))
    return wj, ep


def _gen(tmp_path, clips=None, overlays=None, **kw):
    wj, ep = _setup(tmp_path, clips, overlays)
    out = tmp_path / "o.ass"
    res = captions.make_captions(wj, ep, out, **kw)
    return res, out.read_text(encoding="utf-8")


def _dialogues(text, style=None):
    rows = []
    for ln in text.splitlines():
        if not ln.startswith("Dialogue:"):
            continue
        p = ln[9:].split(",", 9)
        if style is None or p[3] == style:
            rows.append((burn._parse_ass_time(p[1]), burn._parse_ass_time(p[2]), p[9]))
    return rows


def _plain(txt):
    return re.sub(r"\{[^}]*\}", "", txt)


def test_default_bloco_unchanged_by_new_params(tmp_path):
    _, base = _gen(tmp_path)
    _, same = _gen(tmp_path, mode="bloco", case=None, emphasis=None)
    assert base == same
    assert "OLA MUNDO ISTO" in base and "Headline" not in base


def test_palavra_one_word_per_block(tmp_path):
    res, ass = _gen(tmp_path, mode="palavra")
    ev = _dialogues(ass)
    assert res["blocks"] == len(WORDS) == len(ev)
    assert [_plain(t) for _, _, t in ev][:3] == ["OLA", "MUNDO", "ISTO"]
    assert all(b <= a2 + 1e-6 for (_, b, _), (a2, _, _) in zip(ev, ev[1:], strict=False))


def test_karaoke_events_per_word_with_colour_on_active_word(tmp_path):
    _, ass = _gen(tmp_path, mode="karaoke")
    ev = _dialogues(ass)
    # first block = 3 words -> 3 events carrying the whole block text
    first = ev[:3]
    assert [_plain(t) for _, _, t in first] == ["OLA MUNDO ISTO"] * 3
    for k, (_, _, t) in enumerate(first):
        words = re.findall(r"(\{[^}]*\})?([A-Z]+)", t)
        coloured = [w for tag, w in words if tag.startswith("{" + ACCENT_TAG)]
        assert coloured == ["OLA MUNDO ISTO".split()[k]]
    # no gap / overlap between consecutive events of the same block
    assert first[0][1] == pytest.approx(first[1][0]) and first[1][1] == pytest.approx(first[2][0])
    # word timings follow the speech: second word starts at its own start (0.5 + 0.4 after remap)
    assert first[1][0] == pytest.approx(0.9, abs=0.011)


def test_karaoke_ignores_highlight_colour(tmp_path):
    _, ass = _gen(tmp_path, mode="karaoke", highlight="mundo")
    first = _dialogues(ass)[0][2]
    assert first.count(ACCENT_TAG) == 1


def test_case_modes(tmp_path):
    _, upper = _gen(tmp_path, case="upper", style="limpo")
    assert "OLA MUNDO ISTO" in upper
    _, lower = _gen(tmp_path, case="lower")
    assert "ola mundo isto" in lower
    _, keep = _gen(tmp_path, case="keep")
    assert "ola mundo isto" in keep
    # defaults per style: viral upper, limpo keep
    _, limpo = _gen(tmp_path, style="limpo")
    assert "ola mundo isto e um" in limpo
    _, sent = _gen(tmp_path, case="sentence", style="limpo")
    texts = [_plain(t) for _, _, t in _dialogues(sent)]
    assert texts[0].startswith("Ola mundo")
    assert any(t.startswith("Outra frase") for t in texts)
    assert not any("Mundo" in t or "Isto" in t for t in texts)


def test_emphasis_scales_word_and_keeps_highlight_colour(tmp_path):
    _, ass = _gen(tmp_path, emphasis="Mundo", highlight="mundo")
    line = _dialogues(ass)[0][2]
    assert r"{\1c&H00D4FF&}{\fscx130\fscy130}MUNDO{\fscx100\fscy100}{\1c&HFFFFFF&}" in line
    assert "OLA" in line and line.count("fscx130") == 1


def test_per_clip_y_and_lower_layout(tmp_path):
    clips = [
        {"in": 0.5, "out": 2.0, "caption_y": 0.30},
        {"in": 2.0, "out": 3.5, "layout": "lower"},
        {"in": 3.5, "out": 4.0, "layout": "lower", "split_at": 0.5},
        {"in": 4.0, "out": 6.0},
    ]
    wj, ep = _setup(tmp_path, clips)
    out = tmp_path / "o.ass"
    captions.make_captions(wj, ep, out, y=0.62, mode="palavra")
    ys = {int(m) for m in re.findall(r"\\pos\(540,(\d+)\)", out.read_text())}
    assert {576, 864, 1190} <= ys  # 0.30, 0.45, 0.62 of 1920
    clips[1]["caption_y"] = 0.2
    clips[2].pop("split_at")
    ep.write_text(json.dumps({"source": "x.mp4", "fps": 30, "clips": clips}))
    captions.make_captions(wj, ep, out, y=0.62, mode="palavra")
    assert 384 in {int(m) for m in re.findall(r"\\pos\(540,(\d+)\)", out.read_text())}


def test_card_overlay_silences_captions(tmp_path):
    ov = [
        {"at": 1.0, "dur": 1.0, "region": "card", "source": "c.png"},
        {"at": 3.0, "dur": 0.5, "region": "top", "source": "c.png"},
    ]
    res, ass = _gen(tmp_path, overlays=ov, mode="palavra")
    ev = _dialogues(ass)
    assert all(not (a < 2.0 and b > 1.0) for a, b, _ in ev)
    kept, ass_all = _gen(tmp_path, overlays=ov, mode="palavra", keep_under_cards=True)
    assert kept["blocks"] > res["blocks"] == len(ev)
    # non-card overlays never silence
    only_top = [{"at": 1.0, "dur": 1.0, "region": "top", "source": "c.png"}]
    assert _gen(tmp_path, overlays=only_top, mode="palavra")[0]["blocks"] == kept["blocks"]


def test_card_overlay_splits_block_and_clamps(tmp_path):
    ov = [{"at": 1.3, "dur": 0.3, "region": "card", "source": "c.png"}]
    _, ass = _gen(tmp_path, overlays=ov)
    ev = _dialogues(ass)
    assert all(not (a < 1.6 and b > 1.3) for a, b, _ in ev)


def test_headline_events_and_timing(tmp_path):
    res, ass = _gen(tmp_path, headline="TEXTO CURTO|SEGUNDA LINHA", headline_start=0.5, headline_end=3.0)
    assert res["headline"] is True
    assert "Style: Headline," in ass
    ev = _dialogues(ass, "Headline")
    assert len(ev) == 2
    assert all(a == pytest.approx(0.5) and b == pytest.approx(3.0) for a, b, _ in ev)
    assert [_plain(t) for _, _, t in ev] == ["TEXTO CURTO", "SEGUNDA LINHA"]
    ys = [int(re.search(r"\\pos\(540,(\d+)\)", t).group(1)) for _, _, t in ev]
    assert ys[0] < ys[1] and abs(sum(ys) / 2 - 0.12 * 1920) < 5
    # default end = whole video (5.5 s after the cut), no box -> outline style
    _, ass2 = _gen(tmp_path, headline="OI")
    ((a, b, _),) = _dialogues(ass2, "Headline")
    assert a == 0 and b == pytest.approx(5.5)
    assert re.search(r"Style: Headline,.*,1,\d+,0,5,", ass2)  # BorderStyle 1


def test_headline_box_style_and_fit_inside_safe_margins(tmp_path):
    long = "UMA MANCHETE MUITO MAIS LONGA QUE A LARGURA DA TELA INTEIRA DO VIDEO"
    _, ass = _gen(tmp_path, headline=long, headline_box="#D62828", headline_color="#FFFFFF")
    st = next(ln for ln in ass.splitlines() if ln.startswith("Style: Headline"))
    assert ",&H002828D6," in st  # box colour in OutlineColour (BGR)
    assert re.search(r",3,\d+,0,5,", st)  # BorderStyle 3
    ev = _dialogues(ass, "Headline")
    assert len(ev) >= 2  # wrapped
    size = int(re.search(r"\\fs(\d+)", ev[0][2]).group(1))
    assert size < int(1920 * captions.HEADLINE_SIZE) + 1
    measure = captions._text_measurer("Arial", size, True)
    pad = int(round(size * 0.2))
    assert all(measure(_plain(t)) + 2 * pad <= 1080 * (1 - 2 * captions.SAFE_MARGIN) + 1 for _, _, t in ev)


def test_pillow_parser_reads_new_constructs(tmp_path):
    _, ass = _gen(tmp_path, mode="karaoke", emphasis="mundo", headline="TESTE", headline_box="#D62828")
    (tmp_path / "k.ass").write_text(ass)
    parsed = burn.parse_ass(tmp_path / "k.ass")
    head = [e for e in parsed["events"] if e["style"] == "Headline"]
    assert len(head) == 1 and head[0]["fs"] and head[0]["layer"] == 1
    assert parsed["styles"]["Headline"]["border"] == 3
    assert parsed["styles"]["Headline"]["outline_color"] == (0xD6, 0x28, 0x28)
    k0 = parsed["events"][0]
    assert [c for _, c in k0["words"]] == [(255, 212, 0), None, None]
    assert k0["scales"] == [1.0, 1.3, 1.0]


def test_cli_validators():
    from vedit import cli

    p = cli.build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["captions", "w.json", "--edl", "e", "-o", "o", "--headline-y", "2"])
    with pytest.raises(SystemExit):
        p.parse_args(["captions", "w.json", "--edl", "e", "-o", "o", "--headline-box", "vermelho"])
    a = p.parse_args(
        ["captions", "w.json", "--edl", "e", "-o", "o", "--mode", "karaoke", "--headline-y", "0.2"]
    )
    assert a.mode == "karaoke" and a.headline_y == 0.2 and a.case is None


# ------------------------------------------------------------------------ media
def _grab(path, t, crop):
    r = subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-vf", crop,
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, check=True,
    )  # fmt: skip
    return r.stdout


def _burn_inputs(media, make_edl, tmp_path):
    edl = make_edl(media["vertical"], [{"id": "c1", "in": 0.0, "out": 6.0, "layout": "cover"}])
    clip = tmp_path / "clip.mp4"
    cut.render(edl, clip, preview=True)
    ws = [
        {"w": w, "t": 0.5 + i * 0.4, "e": 0.8 + i * 0.4}
        for i, w in enumerate("um dois tres quatro cinco".split())
    ]
    wj = tmp_path / "w.json"
    wj.write_text(json.dumps({"words": ws}))
    ass = tmp_path / "k.ass"
    captions.make_captions(
        wj, edl, ass, mode="karaoke", emphasis="tres", headline="MANCHETE DE TESTE|SEGUNDA LINHA",
        headline_box="#D62828", headline_end=5.0,
    )  # fmt: skip
    return clip, ass


def _check_burn(clip, out, method):
    res = burn.burn(clip, out.with_suffix(".ass"), out, force_fallback=method == "pillow")
    assert res["method"] == method
    assert probe.probe(out, audio_analysis=False)["duration"] == pytest.approx(
        probe.probe(clip, audio_analysis=False)["duration"], abs=0.1
    )
    # headline region (top ~12% of the frame) differs from the unburned clip
    crop = "crop=iw*0.9:ih*0.14:iw*0.05:ih*0.05"
    assert _grab(out, 1.0, crop) != _grab(clip, 1.0, crop)
    return res


@pytest.mark.skipif(not HAS_LIBASS, reason="sem libass")
def test_libass_burn_karaoke_and_headline(media, make_edl, tmp_path):
    clip, ass = _burn_inputs(media, make_edl, tmp_path)
    out = tmp_path / "lib.mp4"
    out.with_suffix(".ass").write_bytes(ass.read_bytes())
    _check_burn(clip, out, "libass")


@pytest.mark.skipif(not HAS_PIL, reason="Pillow ausente")
def test_pillow_burn_karaoke_and_headline(media, make_edl, tmp_path):
    clip, ass = _burn_inputs(media, make_edl, tmp_path)
    out = tmp_path / "pil.mp4"
    out.with_suffix(".ass").write_bytes(ass.read_bytes())
    _check_burn(clip, out, "pillow")
    # the headline box colour (#D62828) is actually drawn
    raw = subprocess.run(
        [util.ffmpeg_path(), "-v", "error", "-ss", "1.0", "-i", str(out), "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout  # fmt: skip
    px = {tuple(raw[i : i + 3]) for i in range(0, len(raw), 3 * 7)}
    assert any(abs(r - 214) < 14 and abs(g - 40) < 14 and abs(b - 40) < 14 for r, g, b in px)


# ------------------------------------------------------------ 0.3.0: pontuação, mute, bridge
def _texts(text):
    return [re.sub(r"\{[^}]*\}", "", r[2]) for r in _dialogues(text)]


def test_strip_display_punct_keeps_decimals_and_marks():
    f = captions.strip_display_punct
    assert f("fim.") == "fim" and f("a,") == "a" and f("...") == ""
    assert f("2,5") == "2,5" and f("3.14") == "3.14" and f("100%") == "100%"
    assert f("sério?") == "sério?" and f("sim!") == "sim!"


def test_captions_strip_punct_default_and_keep(tmp_path):
    _, ass = _gen(tmp_path, case="keep")
    assert "teste" in ass and "teste." not in ass
    _, ass2 = _gen(tmp_path, case="keep", keep_punct=True)
    assert "teste." in ass2


def test_trailing_dot_still_breaks_block(tmp_path):
    _, ass = _gen(tmp_path, case="keep", max_words=6)
    assert not any("teste outra" in t for t in _texts(ass))


def test_tags_and_fields_untouched_by_strip(tmp_path):
    _, ass = _gen(tmp_path, case="keep", highlight="teste", emphasis="mundo")
    for ln in ass.splitlines():
        if ln.startswith("Dialogue:"):
            assert len(ln[9:].split(",", 9)) == 10
    assert r"\1c&H00D4FF&" in ass and r"\fscx130" in ass


def test_mute_clips_and_drops_events():
    ev = [{"t0": 1.0, "t1": 3.0, "pos": "", "text": "a"}, {"t0": 3.0, "t1": 3.03, "pos": "", "text": "b"}]
    out = captions.mute_events(ev, captions.parse_mute("1.5-2.0,2.9-4"))
    spans = [(round(e["t0"], 2), round(e["t1"], 2), e["text"]) for e in out]
    assert spans == [(1.0, 1.5, "a"), (2.0, 2.9, "a")]


def test_mute_option_in_ass(tmp_path):
    _, plain = _gen(tmp_path, mode="palavra")
    _, muted = _gen(tmp_path, mode="palavra", mute="1.0-2.0")
    assert len(_dialogues(muted)) < len(_dialogues(plain))
    for a, b, _ in _dialogues(muted):
        assert b <= 1.0 + 0.01 or a >= 2.0 - 0.01


def test_bridge_gap_and_flag():
    ev = [{"t0": 0.0, "t1": 1.0, "text": "a"}, {"t0": 1.2, "t1": 2.0, "text": "b"}, {"t0": 2.6, "t1": 3, "text": "c"}]
    out = captions.bridge_events([dict(e) for e in ev])
    assert out[0]["t1"] == 1.2 and out[1]["t1"] == 2.0


def test_style_overrides(tmp_path):
    _, ass = _gen(tmp_path, size=77, outline=5, shadow=2)
    style = next(ln for ln in ass.splitlines() if ln.startswith("Style: Default"))
    f = style.split(",")
    assert f[2] == "77" and f[16] == "5" and f[17] == "2"
