"""Reference teardown: measure the editing of an existing finished video."""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

from . import edl as edlmod
from .probe import probe
from .sheet import make_sheet
from .util import VeditError, fmt_ts, info, measure_loudness, run_ffmpeg

EARLY = 5.0  # seconds considered "the opening" for cut/word density

CHECKLIST = [
    "Legenda: posição vertical, tamanho, caixa alta ou baixa, cor e destaque de palavras.",
    "Layout: tela dividida (split), janela de b-roll, cards, enquadramento do locutor.",
    "Título fixo (pinned headline) ou texto de apoio que permanece na tela.",
    "Inserts (b-roll, motion, zoom) a cada 10 s: conte nas pranchas.",
    "Final: encerramento, CTA, loop ou corte seco.",
    "Gancho: o que aparece nos primeiros quadros (rosto, texto, imagem forte) e quando a fala começa.",
]

LIMITATION = (
    "A detecção de cena é um limite inferior: não vê dissolvências (dissolves), whip-pans nem motion "
    "graphics contínuos. 0 cortes detectados não significa vídeo estático; confira nas pranchas."
)


SCENE_NOTE = (
    "Abaixar o limiar de cena abaixo de 0.3 produz falsos cortes (jitter de zoom e de gesto); "
    "prefira `--region` a baixar o limiar."
)
LOW_CUTS_PER_S = 1 / 20  # whole-frame result below this triggers the automatic half-frame check
STACKED_NOTE = (
    "Resultado de tela cheia baixo: rodei também a metade de cima e a de baixo. Uma diferença "
    "grande entre as metades sugere layout empilhado (janela de b-roll sobre um locutor)."
)


def parse_region(spec) -> tuple[float, float]:
    """``'0:0.48'`` (or a (y0, y1) pair) -> fractions of the frame height."""
    try:
        if isinstance(spec, str):
            a, b = spec.split(":")
        else:
            a, b = spec
        y0, y1 = float(a), float(b)
    except (ValueError, TypeError):
        raise VeditError(f"--region inválido: {spec!r}. Use Y0:Y1 em frações da altura (ex.: 0:0.48).") from None
    if not 0 <= y0 < y1 <= 1:
        raise VeditError(f"--region inválido: {spec!r}. Precisa de 0 <= Y0 < Y1 <= 1.")
    return y0, y1


def merge_cuts(cuts: list[float], gap: float) -> list[float]:
    """Collapse detections closer than ``gap`` s to the first of each cluster (flash/blur dissolves)."""
    if gap <= 0:
        return list(cuts)
    out: list[float] = []
    for c in sorted(cuts):
        if not out or c - out[-1] >= gap:
            out.append(c)
    return out


def detect_cuts(video, threshold: float = 0.3, region: tuple[float, float] | None = None) -> list[float]:
    """Timestamps (s) where the scene score exceeds ``threshold`` (ffmpeg select + showinfo).

    ``region`` = (y0, y1) fractions of the height: detection runs on a crop of that band only.
    """
    vf = f"select='gt(scene,{threshold})',showinfo"
    if region:
        y0, y1 = region
        vf = f"crop=iw:trunc(ih*{y1 - y0:.4f}/2)*2:0:trunc(ih*{y0:.4f}/2)*2," + vf
    p = run_ffmpeg(["-i", video, "-an", "-vf", vf, "-f", "null", "-"])
    text = p.stderr_text  # type: ignore[attr-defined]
    cuts = [float(m.group(1)) for m in re.finditer(r"Parsed_showinfo.*?pts_time:\s*(-?[\d.]+)", text)]
    return [round(t, 3) for t in sorted(cuts) if t > 0]


def shot_stats(cuts: list[float], duration: float) -> dict:
    bounds = [0.0, *[c for c in cuts if 0 < c < duration], float(duration)]
    shots = [(a, b) for a, b in zip(bounds, bounds[1:], strict=False) if b > a]
    lens = [b - a for a, b in shots]
    if not lens:
        return {"cuts": 0, "shots": 0}
    a, b = max(shots, key=lambda s: s[1] - s[0])
    return {
        "cuts": len(cuts),
        "shots": len(lens),
        "mean_shot_s": round(statistics.mean(lens), 3),
        "median_shot_s": round(statistics.median(lens), 3),
        "min_shot_s": round(min(lens), 3),
        "max_shot_s": round(max(lens), 3),
        "cuts_first_5s": sum(1 for c in cuts if c <= EARLY),
        "cuts_per_minute": round(len(cuts) / duration * 60, 2) if duration else 0.0,
        "longest_no_cut": {"start": round(a, 3), "end": round(b, 3), "duration": round(b - a, 3)},
    }


def word_stats(words: list[dict], duration: float) -> dict:
    ws = sorted((w for w in words if "t" in w), key=lambda w: w["t"])
    if not ws:
        return {"words": 0}
    early = min(EARLY, duration) or EARLY
    pause = {"duration": 0.0, "start": None, "end": None}
    for prev, nxt in zip(ws, ws[1:], strict=False):
        gap = nxt["t"] - float(prev.get("e", prev["t"]))
        if gap > pause["duration"]:
            pause = {"duration": round(gap, 3), "start": round(float(prev.get("e", prev["t"])), 3),
                     "end": round(nxt["t"], 3)}  # fmt: skip
    first = float(ws[0]["t"])
    return {
        "words": len(ws),
        "words_per_s": round(len(ws) / duration, 2) if duration else None,
        "words_per_s_first_5s": round(sum(1 for w in ws if w["t"] < early) / early, 2),
        "longest_pause": pause,
        "first_words": " ".join(str(w.get("w", "")) for w in ws[:12]),
        "first_word_at": round(first, 3),
        "speech_starts_within_0_5s": first <= 0.5,
    }


def _load_words(path) -> list[dict]:
    data = edlmod.load_json(path, "words.json")
    words = data.get("words") if isinstance(data, dict) else data
    if not isinstance(words, list):
        raise VeditError("words.json deve ter a lista 'words' (palavras com w, t, e).")
    return words


def _cut_report(video, duration, scene, merge, region=None) -> tuple[list[float], dict]:
    raw = detect_cuts(video, scene, region)
    cuts = merge_cuts(raw, merge)
    st = shot_stats(cuts, duration)
    st["raw_detections"] = len(raw)
    return cuts, st


def analyze(video, outdir, scene: float = 0.3, hook_seconds: float = 6.0, words=None,
            transcribe: bool = False, regions=None, merge: float = 0.15) -> dict:  # fmt: skip
    if not Path(video).is_file():
        raise VeditError(f"Vídeo não encontrado: {video}")
    if not 0 < scene < 1:
        raise VeditError("--scene deve estar entre 0 e 1 (ex.: 0.3).")
    if hook_seconds <= 0:
        raise VeditError("--hook-seconds deve ser maior que 0.")
    if merge < 0:
        raise VeditError("--merge não pode ser negativo (0 desliga).")
    parsed = [parse_region(r) for r in regions or []]
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    meta = probe(video, audio_analysis=False)
    if not meta.get("has_video"):
        raise VeditError("A mídia não tem vídeo.")
    duration = meta.get("video_duration") or meta.get("duration") or 0.0
    if duration <= 0:
        raise VeditError("Não consegui determinar a duração do vídeo.")

    res: dict = {
        "video": str(video),
        "probe": {
            "duration": round(duration, 3), "width": meta["width"], "height": meta["height"],
            "fps": meta["fps"], "video_codec": meta.get("codec"), "audio_codec": meta.get("audio_codec"),
        },
        "scene_threshold": scene,
        "merge_s": merge,
    }  # fmt: skip
    info("Detectando cortes...")
    cuts, res["shots"] = _cut_report(video, duration, scene, merge)
    res["cuts"] = cuts
    res["regions_auto"] = False
    if not parsed and len(cuts) < duration * LOW_CUTS_PER_S:
        parsed = [(0.0, 0.5), (0.5, 1.0)]
        res["regions_auto"] = True
    res["regions"] = []
    for y0, y1 in parsed:
        info(f"Detectando cortes na faixa {y0:g}:{y1:g}...")
        rc, rs = _cut_report(video, duration, scene, merge, (y0, y1))
        res["regions"].append({"y0": y0, "y1": y1, "cuts": rc, "shots": rs})

    res["loudness"] = None
    if meta.get("has_audio"):
        try:
            m = measure_loudness(video)
            res["loudness"] = {"integrated_lufs": m["integrated_lufs"],
                               "true_peak_dbtp": m["true_peak_dbtp"], "lra": m["lra"]}  # fmt: skip
        except VeditError:
            pass

    if transcribe and not words:
        from .transcribe import transcribe as run_transcribe

        words = out / "words.json"
        run_transcribe(video, words)
    res["speech"] = word_stats(_load_words(words), duration) if words else None

    info("Gerando pranchas...")
    hook_end = min(float(hook_seconds), duration)
    hook = make_sheet(video, out / "gancho.jpg", every=0.5, start=0, end=hook_end, cols=4, width=360)
    full_every = max(1.0, duration / 52)
    full = make_sheet(video, out / "completo.jpg", every=full_every, cols=8, width=240, max_frames=64)
    res["sheets"] = {"gancho": hook, "completo": full, "completo_every_s": round(full_every, 2)}

    (out / "analise.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "analise.md").write_text(format_markdown(res), encoding="utf-8")
    res["output_dir"] = str(out)
    return res


def _speech_lines(sp) -> list[str]:
    if not sp:
        return ["- Fala: não medida (use `--words words.json` ou `--transcribe`)."]
    if not sp["words"]:
        return ["- Fala: nenhuma palavra encontrada."]
    p = sp["longest_pause"]
    return [
        f"- Palavras: {sp['words']} ({sp['words_per_s']}/s no total; {sp['words_per_s_first_5s']}/s nos primeiros 5 s)",
        f"- Maior pausa entre palavras: {p['duration']} s ({fmt_ts(p['start'])} a {fmt_ts(p['end'])})"
        if p["start"] is not None
        else "- Maior pausa entre palavras: n/d",
        f"- Fala começa em {sp['first_word_at']} s ({'dentro' if sp['speech_starts_within_0_5s'] else 'fora'} de 0,5 s)",
        f'- Primeiras palavras: "{sp["first_words"]}"',
    ]


def format_markdown(res: dict) -> str:
    pr, sh, ld = res["probe"], res["shots"], res.get("loudness")
    lines = [
        "# Análise de referência", "",
        f"Vídeo: `{res['video']}`", "",
        "## Ficha técnica", "",
        f"- Duração: {pr['duration']} s | {pr['width']}x{pr['height']} | {pr['fps']} fps",
        f"- Codecs: vídeo {pr['video_codec']}, áudio {pr['audio_codec'] or 'sem áudio'}", "",
        f"## Cortes (limiar de cena {res['scene_threshold']})", "",
        f"- Cortes detectados: {sh['cuts']} ({sh.get('shots', 0)} planos; "
        f"{sh.get('raw_detections', sh['cuts'])} detecções brutas, mescladas a menos de {res.get('merge_s', 0)} s)",
    ]  # fmt: skip
    if sh.get("shots"):
        ln = sh["longest_no_cut"]
        lines += [
            f"- Plano: média {sh['mean_shot_s']} s, mediana {sh['median_shot_s']} s, "
            f"mín {sh['min_shot_s']} s, máx {sh['max_shot_s']} s",
            f"- Cortes nos primeiros 5 s: {sh['cuts_first_5s']}",
            f"- Cortes por minuto: {sh['cuts_per_minute']}",
            f"- Maior trecho sem corte: {ln['duration']} s ({fmt_ts(ln['start'])} a {fmt_ts(ln['end'])})",
        ]
    if res["cuts"]:
        lines += ["", "Tempos (s): " + ", ".join(f"{c:g}" for c in res["cuts"])]
    if res.get("regions"):
        lines += ["", "## Cortes por faixa da tela", ""]
        if res.get("regions_auto"):
            lines += [STACKED_NOTE, ""]
        for r in res["regions"]:
            rs = r["shots"]
            lines.append(
                f"- Faixa y {r['y0']:g} a {r['y1']:g}: {rs['cuts']} cortes ({rs.get('raw_detections', rs['cuts'])} "
                f"detecções brutas)" + (f", plano mediano {rs['median_shot_s']} s" if rs.get("shots") else "")
            )
            if r["cuts"]:
                lines.append("  Tempos (s): " + ", ".join(f"{c:g}" for c in r["cuts"]))
    lines += ["", "## Áudio", ""]
    if ld:
        lines.append(
            f"- Loudness {ld['integrated_lufs']} LUFS | true peak {ld['true_peak_dbtp']} dBTP | LRA {ld['lra']}"
        )
    else:
        lines.append("- Sem medição de loudness (sem áudio).")
    lines += ["", "## Fala", "", *_speech_lines(res.get("speech"))]
    lines += [
        "", "## Pranchas", "",
        "- `gancho.jpg`: primeiros segundos, um quadro a cada 0,5 s.",
        f"- `completo.jpg`: vídeo inteiro, um quadro a cada ~{res['sheets']['completo_every_s']} s.",
        "", "## O que observar nas pranchas", "",
        "Estas medições não enxergam o que está na imagem. Olhe as pranchas e anote:", "",
        *[f"- [ ] {c}" for c in CHECKLIST],
        "", "## Limitações", "", f"- {LIMITATION}", f"- {SCENE_NOTE}", "",
    ]  # fmt: skip
    return "\n".join(lines)


def format_report(res: dict) -> str:
    sh, ld = res["shots"], res.get("loudness")
    parts = [f"Análise gravada em {res['output_dir']}",
             f"  {res['probe']['duration']} s, {res['probe']['width']}x{res['probe']['height']}, "
             f"{sh['cuts']} cortes ({sh.get('raw_detections', sh['cuts'])} detecções brutas)"]  # fmt: skip
    if sh.get("shots"):
        parts.append(f"  plano médio {sh['mean_shot_s']} s, mediana {sh['median_shot_s']} s, "
                     f"{sh['cuts_per_minute']} cortes/min, {sh['cuts_first_5s']} nos primeiros 5 s")  # fmt: skip
    for r in res.get("regions", []):
        parts.append(f"  faixa y {r['y0']:g}-{r['y1']:g}: {r['shots']['cuts']} cortes")
    if ld:
        parts.append(f"  {ld['integrated_lufs']} LUFS, pico {ld['true_peak_dbtp']} dBTP")
    sp = res.get("speech")
    if sp and sp["words"]:
        parts.append(
            f"  {sp['words']} palavras, {sp['words_per_s']}/s; fala começa em {sp['first_word_at']} s"
        )
    parts.append("  Aviso: a detecção de cena é um limite inferior; veja as pranchas (analise.md).")
    return "\n".join(parts)
