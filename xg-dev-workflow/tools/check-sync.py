#!/usr/bin/env python3
"""check-sync: verify the declared byte-identical file sets (017 R8/D3).

Lives only in xg-dev-workflow/tools/ (not a synced copy). Sets are declared in
tools/sync-manifest.txt — one set per non-comment line, whitespace-separated paths.
Path forms:
  - repo-relative (resolved against the repo root, two levels up from this file)
  - ``~``-prefixed (home)
  - ``$KB/``-prefixed — resolved via the shared config's ``root:`` (the KB root)
Read-only: never writes or fixes anything. A set whose ``$KB``/home/config side is
absent is skipped with a NOTICE (fresh machine is not a failure); a missing
repo-relative member is a DRIFT (a rename must update the manifest in the same batch).
Exit codes: 0 clean, 1 any DRIFT, 2 usage/manifest error.
"""

import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.expanduser("~/.config/xg-knowledge-wiki/config.yaml")
DEFAULT_KB_ROOT = "~/knowledge"


def kb_root_from_config(config_path=CONFIG_PATH):
    """Read `root:` from the shared config; None when the config is absent."""
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^root:\s*(.+?)\s*$", line)
                if m:
                    return os.path.expanduser(m.group(1).strip("'\""))
    except OSError:
        return None
    return os.path.expanduser(DEFAULT_KB_ROOT)


def parse_manifest(path):
    sets = []
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            members = line.split()
            if len(members) < 2:
                raise ValueError(f"{path}:{lineno}: a set needs >=2 paths")
            sets.append((lineno, members))
    return sets


def resolve(token, repo_root, kb_root):
    """Return (path or None, notice-reason or None)."""
    if token.startswith("$KB/"):
        if kb_root is None:
            return None, "no KB config"
        return os.path.join(kb_root, token[len("$KB/"):]), None
    if token.startswith("~"):
        return os.path.expanduser(token), None
    return os.path.join(repo_root, token), None


def check(manifest, repo_root, kb_root):
    """Yield ('DRIFT'|'NOTICE', message) for every finding."""
    for lineno, members in parse_manifest(manifest):
        resolved, skip_reason = [], None
        for tok in members:
            path, notice = resolve(tok, repo_root, kb_root)
            if notice:
                skip_reason = f"{tok}: {notice}"
                break
            optional = tok.startswith(("$KB/", "~"))
            if not os.path.exists(path):
                if optional:
                    skip_reason = f"{tok}: absent on this machine"
                    break
                yield "DRIFT", f"set@{lineno}: {tok} missing (rename? update manifest)"
                resolved = []
                break
            resolved.append((tok, path))
        if skip_reason:
            yield "NOTICE", f"set@{lineno} skipped — {skip_reason}"
            continue
        if len(resolved) < 2:
            continue
        base_tok, base_path = resolved[0]
        with open(base_path, "rb") as f:
            base = f.read()
        for tok, path in resolved[1:]:
            with open(path, "rb") as f:
                if f.read() != base:
                    yield "DRIFT", f"set@{lineno}: {tok} != {base_tok}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", default=os.path.join(REPO_ROOT, "xg-dev-workflow", "tools", "sync-manifest.txt"))
    ap.add_argument("--repo-root", default=REPO_ROOT, help=argparse.SUPPRESS)
    ap.add_argument("--kb-root", default=None, help="override the KB root (default: shared config)")
    args = ap.parse_args(argv)

    if not os.path.exists(args.manifest):
        print(f"check-sync: manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    kb_root = os.path.expanduser(args.kb_root) if args.kb_root else kb_root_from_config()

    drift = False
    try:
        for kind, msg in check(args.manifest, args.repo_root, kb_root):
            print(f"{kind} {msg}")
            drift = drift or kind == "DRIFT"
    except ValueError as e:
        print(f"check-sync: {e}", file=sys.stderr)
        return 2
    if not drift:
        print("check-sync: ok")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
