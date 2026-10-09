#!/usr/bin/env python3
"""Record which card the current Claude Code session is working on.

One pointer file per session: ~/.config/xg-knowledge-wiki/active-card/<session_id>, holding one
line `<project>/<NNN-slug>` (the card dir relative to dev_root), or absent. The workflow writes it when
it enters a card (new / resume) and removes it when it leaves (park / close-out); readers such as the
xg-hud mod only read it.

Usage:
  active-card.py set <project>/<NNN>          # or <project>/<NNN-slug>
  active-card.py clear
  active-card.py get                          # prints the pointer, or nothing
Options: --session ID (default $CLAUDE_CODE_SESSION_ID) · --dev-root DIR · --state-dir DIR

Without a session id every command prints a note to stderr and exits 0: recording the active card must
never block the workflow.
"""
import argparse
import importlib.util
import os
import re
import sys
import tempfile
import time
from pathlib import Path

STALE_DAYS = 30
SESSION_RE = re.compile(r"^[A-Za-z0-9_-]+$")
CARD_RE = re.compile(r"^\d{3}-")
# The one-line form readers accept; a card whose dir name falls outside it is refused rather than recorded unreadable.
POINTER_RE = re.compile(r"^(?!\.\.?/)[A-Za-z0-9_.-]+/\d{3}-[A-Za-z0-9_.-]+$")


def default_dev_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("resolve_project", os.path.join(here, "resolve-project.py"))
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    cfg = rp.config_path()
    text = cfg.read_text(encoding="utf-8") if cfg.exists() else None
    return os.path.expanduser(rp.parse_dev_root(text) if text is not None else rp.DEFAULT_DEV_ROOT)


def default_state_dir() -> str:
    return str(Path.home() / ".config" / "xg-knowledge-wiki" / "active-card")


def resolve_card(dev_root: str, target: str) -> str | None:
    """`<project>/<NNN>` or `<project>/<NNN-slug>` -> `<project>/<NNN-slug>` when that card dir exists."""
    project, _, card = target.partition("/")
    base = Path(dev_root) / project
    if project in ("", ".", "..") or not card or "/" in card or not base.is_dir():
        return None
    for entry in sorted(base.iterdir()):
        if entry.is_dir() and CARD_RE.match(entry.name) and (entry.name == card or entry.name[:3] == card.zfill(3)):
            found = f"{project}/{entry.name}"
            return found if POINTER_RE.match(found) else None
    return None


def prune(state_dir: Path, keep: str) -> None:
    cutoff = time.time() - STALE_DAYS * 86400
    for entry in state_dir.iterdir():
        if entry.name != keep and entry.is_file() and entry.stat().st_mtime < cutoff:
            entry.unlink(missing_ok=True)


def write_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv=None) -> int:
    try:
        return run(argv)
    except (OSError, UnicodeError) as err:
        # Recording the active card must never block the workflow: an IO failure is reported, not raised.
        print(f"active-card: {err}; nothing changed", file=sys.stderr)
        return 0


def run(argv) -> int:
    ap = argparse.ArgumentParser(description="Record the card the current session works on.")
    ap.add_argument("--session")
    ap.add_argument("--dev-root")
    ap.add_argument("--state-dir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("set").add_argument("card")
    sub.add_parser("clear")
    sub.add_parser("get")
    args = ap.parse_args(argv)

    session = args.session or os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not session:
        print("active-card: no CLAUDE_CODE_SESSION_ID; nothing recorded", file=sys.stderr)
        return 0
    if not SESSION_RE.match(session):
        print(f"active-card: not a session id: {session!r}", file=sys.stderr)
        return 2
    state_dir = Path(args.state_dir or default_state_dir())
    pointer = state_dir / session

    if args.cmd == "get":
        if pointer.is_file():
            print(pointer.read_text(encoding="utf-8").strip())
        return 0
    if args.cmd == "clear":
        pointer.unlink(missing_ok=True)
        return 0

    card = resolve_card(args.dev_root or default_dev_root(), args.card)
    if card is None:
        print(f"active-card: no card dir for {args.card!r} under dev_root", file=sys.stderr)
        return 2
    state_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(pointer, card + "\n")
    try:
        prune(state_dir, session)
    except OSError:
        pass
    print(card)
    return 0


if __name__ == "__main__":
    sys.exit(main())
