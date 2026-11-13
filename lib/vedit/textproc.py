"""words.json helpers: digest and metrics."""

from __future__ import annotations

from . import edl as edlmod
from .util import fmt_ts

SENT_END = (".", "?", "!", "…")


def digest(words_path, every: float = 15.0, windows=None) -> str:
    data = edlmod.load_json(words_path, "words.json")
    words = data.get("words", [])
    head = f"# idioma={data.get('language', '?')} duração={fmt_ts(float(data.get('duration') or 0))}"
    if windows:
        lines = [head + " (janelas, palavra@início em segundos)"]
        for a, b in windows:
            lines.append(f"## {fmt_ts(a)} - {fmt_ts(b)}")
            sel = [w for w in words if w["t"] >= a and w["t"] < b]
            row, row_start, prev_e = [], None, None
            for w in sel:
                if row_start is None:
                    row_start = w["t"]
                if prev_e is not None and w["t"] - prev_e >= 0.5:
                    row.append(f"(pausa {w['t'] - prev_e:.1f}s)")
                row.append(f"{w['w']}@{w['t']:.2f}")
                prev_e = w["e"]
                if w["t"] - row_start >= 5 and w["w"].endswith(SENT_END + (",",)):
                    lines.append(f"[{fmt_ts(row_start)}] " + " ".join(row))
                    row, row_start = [], None
            if row:
                lines.append(f"[{fmt_ts(row_start)}] " + " ".join(row))
        return "\n".join(lines) + "\n"
    lines = [head]
    cur, start, prev_e = [], None, None
    for w in words:
        if start is None:
            start = w["t"]
        gap = w["t"] - prev_e if prev_e is not None else 0
        elapsed = w["t"] - start
        if cur and elapsed >= every * 1.5:
            lines.append(f"[{fmt_ts(start)}] " + " ".join(cur))
            cur, start = [], w["t"]
        if gap >= 1.0 and cur:
            cur.append(f"(pausa {gap:.1f}s)")
        cur.append(w["w"])
        prev_e = w["e"]
        if w["w"].endswith(SENT_END) and (w["e"] - start) >= every * 0.5:
            lines.append(f"[{fmt_ts(start)}] " + " ".join(cur))
            cur, start = [], None
    if cur:
        lines.append(f"[{fmt_ts(start)}] " + " ".join(cur))
    return "\n".join(lines) + "\n"


def metrics(edl_path, words_path=None) -> dict:
    edl = edlmod.load_edl(edl_path)
    fps = edlmod.resolve_fps(edl, edl_path)
    tl = edlmod.timeline(edl, fps)
    total = sum(c["duration"] for c in tl)
    res = {
        "clips": len(tl),
        "duration": round(total, 3),
        "cuts": len(tl) - 1,
        "cuts_per_min": round((len(tl) - 1) / (total / 60), 2) if total else 0,
        "longest_uncut": round(max(c["duration"] for c in tl), 3),
        "per_clip": [{"id": c["id"], "duration": round(c["duration"], 3)} for c in tl],
    }
    if words_path:
        wj = edlmod.load_json(words_path, "words.json")
        words = wj.get("words", [])
        from .captions import mark_word_clips

        mark_word_clips(tl, edl, wj.get("source"))
        n = 0
        for c in tl:
            if c["skip_words"]:
                continue
            n += sum(1 for w in words if c["in"] <= (w["t"] + w["e"]) / 2 < c["out"])
        res["words"] = n
        res["words_per_sec"] = round(n / total, 2) if total else 0
    return res
