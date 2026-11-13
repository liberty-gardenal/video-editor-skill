"""Every `vedit ...` command shown in the markdown docs must parse with the real CLI.

Parse only: nothing is executed. Placeholders ($vars, <x>, ...) are replaced by dummy tokens.
"""

from __future__ import annotations

import contextlib
import io
import re
import shlex
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from vedit.cli import build_parser  # noqa: E402

SKIP_DIRS = {".venv", ".git", ".pytest_cache", "node_modules", ".ruff_cache"}
SHELL_LANGS = {"", "bash", "sh", "shell", "console", "zsh"}
# Tried in order for every placeholder token: path-like, number, range, color.
CANDIDATES = ["dummy.mp4", "1", "1-2", "#FFD400"]


def md_files():
    return sorted(p for p in ROOT.rglob("*.md") if not SKIP_DIRS & set(p.relative_to(ROOT).parts))


def fenced_lines(path: Path):
    """Yield (lineno, text) logical lines of shell-ish fenced blocks, `\\` continuations joined."""
    in_fence, lang, buf, start = False, "", [], 0
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("```"):
            if in_fence:
                in_fence = False
                if buf:
                    yield start, " ".join(buf)
                    buf = []
            else:
                in_fence, lang = True, stripped[3:].strip().lower()
            continue
        if not in_fence or lang not in SHELL_LANGS:
            continue
        if not buf:
            start = n
        if raw.rstrip().endswith("\\"):
            buf.append(raw.rstrip()[:-1].strip())
            continue
        buf.append(stripped)
        yield start, " ".join(buf)
        buf = []


def tokenize(line: str):
    lex = shlex.shlex(line.lstrip("$ ").strip(), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = "#"
    return list(lex)


def extract_commands(line: str):
    """Return the argv (after `vedit`) of every vedit invocation in a shell line."""
    toks = tokenize(line)
    out = []
    for i, t in enumerate(toks):
        if t != "vedit" and not t.endswith("/vedit"):
            continue
        argv = []
        for u in toks[i + 1 :]:
            if re.fullmatch(r"[();<>|&]+", u) or u in {"do", "done", "then", "fi"}:
                break
            argv.append(u)
        if argv and argv[-1].isdigit() and len(toks) > i + 1 + len(argv) and re.fullmatch(r"[<>&]+", toks[i + 1 + len(argv)]):
            argv.pop()  # `2>&1`: the fd number is not an argument
        out.append(argv)
    return out


def is_placeholder(tok: str) -> bool:
    return "$" in tok or tok == "..." or tok == "…" or re.search(r"<[^>]+>", tok) is not None


def try_parse(argv, candidate):
    argv = [candidate if is_placeholder(a) else a for a in argv]
    try:
        with contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()):
            build_parser().parse_args(argv)
    except SystemExit:
        return err.getvalue().strip().splitlines()[-1:] or ["erro"]
    return None


def collect():
    for path in md_files():
        for lineno, line in fenced_lines(path):
            try:
                cmds = extract_commands(line)
            except ValueError as exc:
                yield path, lineno, line, None, str(exc)
                continue
            for argv in cmds:
                yield path, lineno, line, argv, None


def test_fenced_vedit_commands_parse():
    failures, checked = [], 0
    for path, lineno, line, argv, err in collect():
        rel = f"{path.relative_to(ROOT)}:{lineno}"
        if argv is None:
            failures.append(f"{rel}: não consegui tokenizar ({err}): {line}")
            continue
        checked += 1
        msgs = [try_parse(argv, c) for c in CANDIDATES]
        if all(m is not None for m in msgs):
            failures.append(f"{rel}: vedit {' '.join(argv)}  ->  {msgs[0][-1]}")
    assert checked > 30, "poucos comandos encontrados; o extrator quebrou?"
    assert not failures, "\n" + "\n".join(failures)


def test_inline_vedit_mentions_exist():
    """Backticked `vedit <sub> --flag` in prose: subcommand and flags must exist."""
    parser = build_parser()
    subs = next(a for a in parser._actions if hasattr(a, "choices") and a.choices).choices
    bad = []
    for path in md_files():
        in_fence = False
        for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if raw.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for span in re.findall(r"`([^`]*\bvedit [^`]*)`", raw):
                m = re.search(r"\bvedit ([a-z][a-z-]*)((?: [^ ]+)*)", span)
                if not m:
                    continue
                sub, rest = m.group(1), m.group(2).split()
                if sub not in subs:
                    bad.append(f"{path.relative_to(ROOT)}:{n}: subcomando inexistente '{sub}' em `{span}`")
                    continue
                known = set(subs[sub]._option_string_actions)
                for tok in rest:
                    flag = tok.split("=")[0]
                    if flag.startswith("-") and re.fullmatch(r"--?[A-Za-z][\w-]*", flag) and flag not in known:
                        bad.append(f"{path.relative_to(ROOT)}:{n}: flag '{flag}' não existe em `vedit {sub}`")
    assert not bad, "\n" + "\n".join(bad)


@pytest.mark.parametrize("pattern", [r"/Users/", r"/home/[a-z]", r"@gmail"])
def test_no_personal_paths(pattern):
    hits = [
        str(p.relative_to(ROOT))
        for p in md_files()
        if re.search(pattern, p.read_text(encoding="utf-8"))
    ]
    assert not hits, hits


def test_skills_and_agents_do_not_reference_docs():
    hits = []
    for base in ("skills", "agents"):
        for p in (ROOT / base).rglob("*.md"):
            if re.search(r"(?<![\w/.-])docs/", p.read_text(encoding="utf-8")):
                hits.append(str(p.relative_to(ROOT)))
    assert not hits, hits
