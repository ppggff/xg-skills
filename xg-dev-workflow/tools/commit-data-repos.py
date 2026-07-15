#!/usr/bin/env python3
"""Local-commit the two data repos (KB + workflow docs) — never push.

Used two ways:
  1. The skill's gate-driven cadence calls it (or runs git directly) after a doc/KB write.
  2. The optional Stop-hook safety net calls it at session end to sweep anything uncommitted.

Reads the shared config (~/.config/xg-knowledge-wiki/config.yaml):
  root:     -> KB repo        (default ~/knowledge)
  dev_root: -> workflow docs  (default ~/dev-workflow)

For each existing dir: lazily `git init` (+ a minimal .gitignore) if it isn't a repo yet,
then `git add -A && git commit` only if there's something to commit. **Never pushes, never
amends/rebases** (push + history-rewrite stay human-gated, per global Git & MR Safety).

NOT a byte-identical synced script — it lives only here (xg-dev-workflow/tools/).

Usage:
  commit-data-repos.py [--message MSG] [--reason TEXT] [--only kb|docs]
Exit 0 always (a commit failure on one repo is reported, doesn't abort the other).
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULTS = {"root": "~/knowledge", "dev_root": "~/dev-workflow"}
GITIGNORE = ".DS_Store\n*.swp\n*.swo\n*~\n__pycache__/\n"


def config_path() -> Path:
    return Path.home() / ".config" / "xg-knowledge-wiki" / "config.yaml"


def _load(text: str):
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        return None


def parse_key(text: str, key: str, default: str) -> str:
    """Read a top-level scalar key (root:/dev_root:) — PyYAML when present, else a tiny parser."""
    data = _load(text)
    if data is not None:
        return str(data.get(key) or default)
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith(f"{key}:") and not raw.startswith(" "):
            val = s.split(":", 1)[1].split("#", 1)[0].strip().strip("\"'")
            if val:
                return val
    return default


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True,
    )


def is_repo(repo: Path) -> bool:
    # Must be its own work-tree toplevel: merely being inside an ancestor's
    # work tree would send `git add -A` up into that repo.
    res = git(repo, "rev-parse", "--show-toplevel")
    if res.returncode != 0:
        return False
    try:
        return Path(res.stdout.strip()).resolve() == repo.resolve()
    except OSError:
        return False


def commit_repo(repo: Path, label: str, message: str) -> str:
    if not repo.exists():
        return f"{label}: {repo} does not exist — skipped"
    inited = False
    if not is_repo(repo):
        if git(repo, "init").returncode != 0:
            return f"{label}: git init failed — skipped"
        gi = repo / ".gitignore"
        if not gi.exists():
            gi.write_text(GITIGNORE, encoding="utf-8")
        inited = True
    # anything to commit?
    status = git(repo, "status", "--porcelain")
    if status.returncode != 0:
        return f"{label}: git status failed — skipped"
    if not status.stdout.strip() and not inited:
        return f"{label}: clean — nothing to commit"
    git(repo, "add", "-A")
    msg = ("init: " + label + " repo\n\n" + message) if inited else message
    res = git(repo, "commit", "-m", msg)
    if res.returncode != 0:
        # e.g. nothing staged after add (rare) — report, don't fail hard
        return f"{label}: nothing committed ({res.stdout.strip() or res.stderr.strip()})"
    head = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    return f"{label}: committed {head}{' (initialized)' if inited else ''}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--message", default=None)
    ap.add_argument("--reason", default=None)
    ap.add_argument("--only", choices=["kb", "docs"], default=None)
    a = ap.parse_args()

    cp = config_path()
    text = cp.read_text(encoding="utf-8") if cp.exists() else ""
    kb = Path(os.path.expanduser(parse_key(text, "root", DEFAULTS["root"])))
    docs = Path(os.path.expanduser(parse_key(text, "dev_root", DEFAULTS["dev_root"])))

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    default_msg = a.message or f"auto: data snapshot {stamp}"
    if a.reason:
        default_msg += f"\n\n{a.reason}"

    targets = []
    if a.only in (None, "kb"):
        targets.append((kb, "knowledge (KB)"))
    if a.only in (None, "docs"):
        targets.append((docs, "dev-workflow (docs)"))

    for repo, label in targets:
        print(commit_repo(repo, label, default_msg))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        sys.exit(0)  # even an argparse usage error must not block the session
    except Exception as e:
        # never block the session ("Exit 0 always")
        print(f"(commit-data-repos: skipped — {e})", file=sys.stderr)
        sys.exit(0)
