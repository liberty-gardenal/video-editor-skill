"""Command line entry point for vedit."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

from . import __version__
from .util import VeditError, arg_color, arg_ranges, arg_time, dump_json, info


def _out(args, data, text: str | None = None) -> None:
    if getattr(args, "json", False) or text is None:
        dump_json(data)
    else:
        print(text)


def cmd_doctor(args):
    from . import doctor

    res = doctor.run_doctor()
    if args.json:
        dump_json(res)
    else:
        print(doctor.format_report(res))
    return 0 if res["ok"] else 1


def cmd_setup(args):
    from . import workspace

    res = workspace.setup(all_extras=args.all)
    _out(args, res, f"Ambiente pronto em {res['venv']}. Rode `vedit doctor` para conferir.")


def cmd_init(args):
    from . import workspace

    res = workspace.init_workspace(args.workspace, args.source)
    _out(args, res, f"Pasta da run pronta: {res['workspace']}")


def cmd_probe(args):
    from .probe import probe

    dump_json(probe(args.media, audio_analysis=not args.no_audio, count_frames=args.count_frames))


def cmd_sheet(args):
    from .sheet import make_sheet

    res = make_sheet(
        args.video, args.output, every=args.every, start=args.start, end=args.end,
        cols=args.cols, width=args.width, guides=args.guides,
    )  # fmt: skip
    _out(args, res, f"Prancha gravada em {res['output']} ({res['frames']} quadros).")


def cmd_transcribe(args):
    from .transcribe import transcribe

    res = transcribe(args.media, args.output, model=args.model, lang=args.lang, vad=args.vad)
    _out(args, res, f"{res['words']} palavras gravadas em {res['output']}.")


def cmd_digest(args):
    from .textproc import digest

    text = digest(args.words, every=args.every, windows=args.windows)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        info(f"Digest gravado em {args.output}")
        if args.json:
            dump_json({"output": args.output})
    elif args.json:
        dump_json({"digest": text})
    else:
        sys.stdout.write(text)


def cmd_silences(args):
    from .audio import silences

    dump_json(
        silences(args.media, args.noise, args.min,
                 start=args.start, end=args.end)
    )  # fmt: skip


def cmd_edges(args):
    from .audio import edges

    res = edges(args.clip, thr=args.noise, ms=args.ms)
    _out(args, res, ("OK: " if res["ok"] else "FALHA: ") + res["message"])
    return 0 if res["ok"] else 1


def cmd_cut(args):
    from .cut import render

    res = render(args.edl, args.output, preview=args.preview)
    _out(args, res, f"Pronto: {res['output']} ({res['duration']:.2f}s, {res['frames']} quadros).")


def cmd_reframe(args):
    from .reframe import reframe

    dump_json(reframe(args.edl, write=args.write))


def cmd_captions(args):
    from .captions import make_captions

    res = make_captions(
        args.words, args.edl, args.output, srt=args.srt, style=args.style,
        max_words=args.max_words, y=args.y, font=args.font,
        highlight=args.highlight, accent=args.accent,
    )  # fmt: skip
    _out(args, res, f"{res['blocks']} blocos gravados em {res['ass']}.")


def cmd_burn(args):
    from .burn import burn

    res = burn(args.video, args.ass, args.output, font=args.font, force_fallback=args.fallback)
    _out(args, res, f"Legenda queimada ({res['method']}): {res['output']}")


def cmd_loudness(args):
    from .audio import loudness

    res = loudness(args.media)
    _out(
        args, res,
        f"{res['integrated_lufs']:.1f} LUFS | true peak {res['true_peak_dbtp']:.1f} dBTP | "
        f"LRA {res['lra']:.1f} LU",
    )  # fmt: skip


def cmd_master(args):
    from .audio import master

    res = master(args.video, args.output, lufs=args.lufs, tp=args.tp)
    a = res["after"]
    _out(
        args,
        res,
        f"Masterizado: {a['lufs']:.1f} LUFS, true peak {a['true_peak']:.1f} dBTP -> {res['output']}",
    )


def cmd_extract_audio(args):
    from .audio import extract_audio

    res = extract_audio(args.video, args.output, start=args.start, end=args.end)
    _out(args, res, f"Áudio gravado em {res['output']} ({res['duration']:.2f}s, {res['channels']} canal(is)).")


def cmd_mux(args):
    from .audio import mux

    res = mux(args.video, args.audio, args.output)
    _out(args, res, f"Mux gravado em {res['output']} ({res['duration']:.2f}s).")


def cmd_mix(args):
    from .audio import mix

    res = mix(args.voice, args.music, args.output, music_lufs=args.music_lufs, duck=args.duck)
    _out(args, res, f"Mix gravado em {res['output']} ({res['duration']:.2f}s).")


def cmd_metrics(args):
    from .textproc import metrics

    dump_json(metrics(args.edl, args.words))


def cmd_verify(args):
    from .verify import format_report, verify

    res = verify(args.video, platform=args.platform, source=args.source, strict_edges=args.strict_edges)
    if args.json:
        dump_json(res)
    else:
        print(format_report(res))
    return 1 if res["status"] == "falha" else 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="vedit",
        description="Ferramentas de edição de vídeo para a skill editor-de-video.",
    )
    ap.add_argument("--version", action="version", version=f"vedit {__version__}")
    sub = ap.add_subparsers(dest="cmd", metavar="<comando>")

    def add(name, fn, help_, **kw):
        p = sub.add_parser(name, help=help_, description=kw.pop("description", help_), **kw)
        p.set_defaults(fn=fn)
        return p

    def js(p):
        p.add_argument("--json", action="store_true", help="saída de máquina (JSON)")

    p = add("doctor", cmd_doctor, "diagnostica ffmpeg, filtros, opcionais e como corrigir")
    js(p)
    p = add("setup", cmd_setup, "cria .venv e instala dependências")
    p.add_argument("--all", action="store_true", help="inclui os pacotes opcionais")
    js(p)
    p = add("init", cmd_init, "cria a pasta de uma run")
    p.add_argument("workspace")
    p.add_argument("--source", help="mídia de origem (grava 00-probe.json e preenche a EDL)")
    js(p)
    p = add("probe", cmd_probe, "metadados reais da mídia (JSON)")
    p.add_argument("media")
    p.add_argument("--no-audio", action="store_true", help="pula loudness e correlação L/R")
    p.add_argument("--count-frames", action="store_true", help="conta quadros decodificando")
    js(p)
    p = add("sheet", cmd_sheet, "prancha de quadros (contact sheet)")
    p.add_argument("video")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--every", type=float, default=5.0)
    p.add_argument("--start", type=arg_time)
    p.add_argument("--end", type=arg_time)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--width", type=int, default=480)
    p.add_argument("--guides", help="JSON com retângulos em frações (x,y,w,h)")
    js(p)
    p = add("transcribe", cmd_transcribe, "transcrição por palavra (faster-whisper)")
    p.add_argument("media")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--model", help="padrão: large-v3 até 10 min, senão small")
    p.add_argument("--lang")
    p.add_argument("--vad", action="store_true", help="liga o filtro VAD do whisper")
    js(p)
    p = add("digest", cmd_digest, "texto compacto com tempos para o modelo ler")
    p.add_argument("words")
    p.add_argument("-o", "--output")
    p.add_argument("--windows", type=arg_ranges, help='ex.: "12-45,80-120" (mostra tempo por palavra)')
    p.add_argument("--every", type=float, default=15.0)
    js(p)
    p = add("silences", cmd_silences, "lista de silêncios (JSON)")
    p.add_argument("media")
    p.add_argument("--noise", type=float, default=-35.0)
    p.add_argument("--min", type=float, default=0.25)
    p.add_argument("--start", type=arg_time)
    p.add_argument("--end", type=arg_time)
    js(p)
    p = add("edges", cmd_edges, "confere se início e fim do clipe caem em silêncio")
    p.add_argument("clip")
    p.add_argument("--noise", type=float, default=-35.0, help="limiar em dB RMS")
    p.add_argument("--ms", type=int, default=80, help="janela de verificação")
    js(p)
    p = add("cut", cmd_cut, "renderiza a EDL (sempre recodifica)")
    p.add_argument("--edl", required=True)
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--preview", action="store_true", help="540x960 rápido")
    js(p)
    p = add(
        "reframe", cmd_reframe, "[EXPERIMENTAL] enquadramento por locutor ativo (requer OpenCV)",
        description="[EXPERIMENTAL] Detecta rostos e o locutor ativo; sugere crop_x por subsegmento. "
        "Revise o resultado com `vedit sheet` antes de confiar.",
    )  # fmt: skip
    p.add_argument("--edl", required=True)
    p.add_argument("--write", action="store_true", help="grava crop_x na EDL")
    js(p)
    p = add("captions", cmd_captions, "gera legenda ASS (e SRT) a partir de words.json + EDL")
    p.add_argument("words")
    p.add_argument("--edl", required=True)
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--srt", action="store_true")
    p.add_argument("--style", choices=["viral", "limpo"], default="viral")
    p.add_argument("--max-words", type=int, help="padrão: 3 (viral) ou 6 (limpo)")
    p.add_argument("--y", type=float, default=0.62, help="posição vertical (fração da altura; padrão 0.62)")
    p.add_argument("--font", default="Arial")
    p.add_argument("--highlight", help='palavras em destaque, ex.: "palavra1,palavra2" (sem caixa/acento)')
    p.add_argument("--accent", type=arg_color, default="#FFD400", help="cor do destaque (padrão #FFD400)")
    js(p)
    p = add("burn", cmd_burn, "queima a legenda no vídeo (libass ou fallback Pillow)")
    p.add_argument("video")
    p.add_argument("ass")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--font", help="fonte do fallback Pillow (padrão: a do .ass)")
    p.add_argument("--fallback", action="store_true", help="força o fallback Pillow")
    js(p)
    p = add("loudness", cmd_loudness, "LUFS integrado, true peak e LRA")
    p.add_argument("media")
    js(p)
    p = add("master", cmd_master, "loudnorm em duas passadas; vídeo copiado")
    p.add_argument("video")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--lufs", type=float, default=-14.0)
    p.add_argument("--tp", type=float, default=-1.5)
    js(p)
    p = add("mix", cmd_mix, "música sob a voz, com ducking opcional")
    p.add_argument("--voice", required=True)
    p.add_argument("--music", required=True)
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--music-lufs", type=float, default=-27.0)
    p.add_argument("--duck", action="store_true")
    js(p)
    p = add("extract-audio", cmd_extract_audio, "extrai o áudio em WAV 48 kHz (estéreo mantido)")
    p.add_argument("video")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--start", type=arg_time)
    p.add_argument("--end", type=arg_time)
    js(p)
    p = add("mux", cmd_mux, "junta vídeo (copiado) e áudio (AAC) com a duração exata do vídeo")
    p.add_argument("--video", required=True)
    p.add_argument("--audio", required=True)
    p.add_argument("-o", "--output", required=True)
    js(p)
    p = add("metrics", cmd_metrics, "ritmo da edição (palavras/s, cortes/min)")
    p.add_argument("--edl", required=True)
    p.add_argument("--words")
    js(p)
    p = add("verify", cmd_verify, "QC final do vídeo (sai com código 1 se reprovar)")
    p.add_argument("video")
    p.add_argument("--platform", choices=["reels", "tiktok", "shorts", "meta-ads"])
    p.add_argument("--source")
    p.add_argument("--strict-edges", action="store_true", help="borda de áudio com som vira FALHA (padrão: aviso)")
    js(p)
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    try:
        rc = args.fn(args)
        return int(rc or 0)
    except VeditError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrompido.", file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 0
    except OSError as e:
        if os.environ.get("VEDIT_DEBUG"):
            traceback.print_exc()
        print(f"Erro de arquivo: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 - last resort: never show a raw traceback by default
        if os.environ.get("VEDIT_DEBUG"):
            traceback.print_exc()
        print(
            f"Erro inesperado: {type(e).__name__}: {e}\n(rode com VEDIT_DEBUG=1 para o traceback)",
            file=sys.stderr,
        )
        return 1
