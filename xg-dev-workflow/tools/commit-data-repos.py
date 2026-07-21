#!/usr/bin/env python3
"""Local-commit the two data repos (KB + workflow docs) — never push.

Used two ways:
  1. The skill's gate-driven cadence calls it (or runs git directly) after a doc/KB write.
  2. The optional Stop-hook safety net calls it at session end to sweep anything uncommitted.

Reads the shared config (~/.config/xg-knowledge-wiki/config.yaml):
  root:     -> KB repo        (default ~/knowledge)
  dev_root: -> workflow docs  (default ~/dev-workflow)

For each existing dir: lazily `git init` (+ a minimal .gitignore) if it isn't a repo yet.
`--project NAME` commits only that project's paths (>=1 commit per repo); without it,
dirty paths are grouped by project and committed one group per commit (message suffixed
` [<group>]`), so one call never mixes two projects' — or two parallel sessions' — files
into the same commit. **Never pushes, never amends/rebases** (push + history-rewrite stay
human-gated, per global Git & MR Safety).

NOT a byte-identical synced script — it lives only here (xg-dev-workflow/tools/).

Usage:
  commit-data-repos.py [--message MSG] [--reason TEXT] [--only kb|docs] [--project NAME]
`--project NAME` scopes the commit to that project's paths only (both repos) — the
gate-commit mode; paths outside NAME stay uncommitted (warned, not lost). Omit it for
the sweep safety net.
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


def scoped_pathspecs(kind: str, project: str) -> list:
    """project name -> pathspec prefixes for this repo's layout (R4).

    Pure prefix mapping — dev_root/KB lay out by project as the first path level, so
    this needs no read of the shared config's `projects:` map (that maps product-repo
    paths, not these data-repo subdirs).
    """
    if kind == "kb":
        return [f"raw/{project}", f"wiki/{project}"]
    return [project]


def parse_porcelain_z(raw: str) -> list:
    """`git status --porcelain -z` output -> flat list of touched paths.

    -z avoids core.quotePath mangling non-ASCII paths. A rename/copy entry (XY where
    X or Y is R/C) carries an extra NUL-terminated orig-path field after the path;
    skip it — the new path is what matters for scoping.
    """
    fields = raw.split("\0")
    paths = []
    i = 0
    while i < len(fields) and fields[i]:
        entry = fields[i]
        status, path = entry[:2], entry[3:]
        paths.append(path)
        if status[0] in ("R", "C"):
            i += 1
        i += 1
    return paths


def group_of(path: str, kind: str) -> str:
    """First-level project group for a touched path; '(root)' for unowned files (R6)."""
    parts = path.split("/")
    if kind == "kb":
        if len(parts) >= 3 and parts[0] in ("raw", "wiki"):
            return parts[1]
        return "(root)"
    if len(parts) >= 2:
        return parts[0]
    return "(root)"


def existing_pathspecs(repo: Path, pathspecs: list) -> list:
    """Filter to pathspecs git actually knows about (on disk or tracked) — R1/R4 guard.

    `git add -A -- <ps>...` / `git commit -- <ps>...` abort the WHOLE call if ANY
    pathspec matches nothing at all (fatal, exit 128) — even when other pathspecs in
    the same call would have matched. Filtering first turns an unknown project, or a
    project missing one of the two KB subdirs, into a clean empty/partial scope
    instead of a hard git failure (verified against real git, not assumed).
    """
    kept = []
    for ps in pathspecs:
        if (repo / ps).exists() or git(repo, "ls-files", "--", ps).stdout.strip():
            kept.append(ps)
    return kept


def sweep_groups(repo: Path, kind: str) -> dict:
    """All touched paths in `repo`, grouped by project ('(root)' for unowned) — R2/R6.

    `-uall` expands a brand-new untracked directory into its individual files —
    without it git reports just the directory (e.g. `wiki/`), which would misgroup an
    entirely-new project's files into '(root)'.
    """
    status = git(repo, "status", "--porcelain", "-uall", "-z")
    groups = {}
    for path in parse_porcelain_z(status.stdout):
        groups.setdefault(group_of(path, kind), []).append(path)
    return groups


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


def _add_commit(repo: Path, pathspecs: list, message: str) -> subprocess.CompletedProcess:
    """Stage and commit exactly `pathspecs` (D4: the same pathspec on both `add` and
    `commit` — scoping only `add` would still let a path a concurrent session staged in
    its own add→commit window get swept into this commit at commit time)."""
    git(repo, "add", "-A", "--", *pathspecs)
    return git(repo, "commit", "-m", message, "--", *pathspecs)


def _commit_scoped(repo: Path, label: str, kind: str, message: str, project: str, inited: bool) -> list:
    """`--project` mode (R1/R3/R4): commit only `project`'s pathspecs, ≤1 commit."""
    pathspecs = existing_pathspecs(repo, scoped_pathspecs(kind, project))
    if inited:
        pathspecs = pathspecs + [".gitignore"]  # D3: never lost to scoping
    if not pathspecs:
        return [f"{label}: nothing to commit for project {project}"]
    msg = ("init: " + label + " repo\n\n" + message) if inited else message
    res = _add_commit(repo, pathspecs, msg)
    if res.returncode != 0:
        return [f"{label}: nothing committed for project {project} "
                f"({res.stdout.strip() or res.stderr.strip()})"]
    head = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    lines = [f"{label}: committed {head} (project {project}){' (initialized)' if inited else ''}"]
    leftover = parse_porcelain_z(git(repo, "status", "--porcelain", "-uall", "-z").stdout)
    if leftover:
        lines.append(f"{label}: {len(leftover)} path(s) left uncommitted "
                      f"(out of scope for --project {project}): " + ", ".join(leftover))
    return lines


def group_pathspecs(group: str, kind: str, paths: list) -> list:
    """Pathspec for one sweep group — a project prefix, or the literal paths for '(root)'
    (unowned files share no common prefix to scope by)."""
    if group == "(root)":
        return paths
    return scoped_pathspecs(kind, group)


def _commit_sweep(repo: Path, label: str, kind: str, message: str, inited: bool) -> list:
    """No `--project`: safety-net sweep (R2) — one commit per project group, `(root)`
    catching unowned stragglers (R6). A freshly-`init`-ed `.gitignore` is itself unowned,
    so `sweep_groups()` already places it in `(root)` — D3 falls out for free, no
    special-casing needed."""
    groups = sweep_groups(repo, kind)
    if not groups and not inited:
        return [f"{label}: clean — nothing to commit"]
    lines = []
    for group in sorted(groups, key=lambda g: (g == "(root)", g)):
        pathspecs = existing_pathspecs(repo, group_pathspecs(group, kind, groups[group]))
        if not pathspecs:
            continue
        msg = f"{message} [{group}]"
        res = _add_commit(repo, pathspecs, msg)
        if res.returncode != 0:
            lines.append(f"{label}: nothing committed for group {group} "
                          f"({res.stdout.strip() or res.stderr.strip()})")
            continue
        head = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
        lines.append(f"{label}: committed {head} [{group}]")
    return lines or [f"{label}: clean — nothing to commit"]


def commit_repo(repo: Path, label: str, kind: str, message: str, project: str = None) -> list:
    if not repo.exists():
        return [f"{label}: {repo} does not exist — skipped"]
    inited = False
    if not is_repo(repo):
        if git(repo, "init").returncode != 0:
            return [f"{label}: git init failed — skipped"]
        gi = repo / ".gitignore"
        if not gi.exists():
            gi.write_text(GITIGNORE, encoding="utf-8")
        inited = True

    if project is not None:
        return _commit_scoped(repo, label, kind, message, project, inited)
    return _commit_sweep(repo, label, kind, message, inited)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--message", default=None)
    ap.add_argument("--reason", default=None)
    ap.add_argument("--only", choices=["kb", "docs"], default=None)
    ap.add_argument("--project", default=None,
                    help="scoped mode (R3): commit only this project's paths, "
                         "in both repos (R4). Omit for the sweep safety net.")
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
        targets.append((kb, "knowledge (KB)", "kb"))
    if a.only in (None, "docs"):
        targets.append((docs, "dev-workflow (docs)", "docs"))

    for repo, label, kind in targets:
        for line in commit_repo(repo, label, kind, default_msg, project=a.project):
            print(line)
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
