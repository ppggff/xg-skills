#!/usr/bin/env python3
"""Resolve a code-directory cwd to a project name, and resolve the workflow dev_root.

Shares the config file with xg-knowledge-lite: ~/.config/xg-knowledge-wiki/config.yaml
so project names line up between the knowledge base and the dev workflow.

KEEP IN SYNC: identical copies live at xg-dev-workflow/tools/ and xg-knowledge-lite/tools/
— edit one, copy to the other (cp, byte-identical). This version is the superset
(--dev-root is a no-op concern for the KB but harmless).

Usage:
  resolve-project.py                 # print project for $PWD
  resolve-project.py <cwd>           # print project for an explicit cwd
  resolve-project.py --dev-root      # print the configured dev_root (default ~/dev-workflow)
  resolve-project.py --kb-root       # print the configured KB root (default ~/knowledge)

Project resolution:
  1. Read config `projects:` (name -> {paths: [...]}).
  2. Pick the project whose path is the longest prefix of cwd.
  3. Hit -> print name, exit 0. Miss -> exit 1 (ask user + register).
  4. Config missing/unreadable -> exit 2.

dev_root resolution: config `dev_root:` if present, else default ~/dev-workflow (exit 0).
"""
import os
import sys
from pathlib import Path

DEFAULT_DEV_ROOT = "~/dev-workflow"
DEFAULT_KB_ROOT = "~/knowledge"


def config_path() -> Path:
    return Path.home() / ".config" / "xg-knowledge-wiki" / "config.yaml"


def _load(text: str):
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        return None


def parse_projects(text: str):
    """Return list[(name, [abs_paths])]; PyYAML when available, else a tiny parser."""
    data = _load(text)
    if data is not None:
        projects = data.get("projects") or {}
        result = []
        for name, info in projects.items():
            if not isinstance(info, dict):
                continue
            paths = info.get("paths") or []
            if isinstance(paths, str):
                paths = [paths]
            result.append(
                (str(name), [Path(os.path.expanduser(p)).resolve(strict=False) for p in paths])
            )
        return result

    # Fallback: indentation-based mini parser (projects: -> <name>: -> paths: -> - item)
    result = []
    in_projects = False
    name = None
    paths = []
    in_paths = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            if name is not None:
                result.append((name, paths))
                name, paths = None, []
            in_projects = line.strip().startswith("projects:")
            in_paths = False
            continue
        if not in_projects:
            continue
        if indent == 2 and line.rstrip().endswith(":"):
            if name is not None:
                result.append((name, paths))
            name = line.strip().rstrip(":").strip()
            paths = []
            in_paths = False
            continue
        if indent == 4 and line.strip().startswith("paths:"):
            in_paths = True
            tail = line.split(":", 1)[1].strip()
            if tail.startswith("[") and tail.endswith("]"):
                for x in tail[1:-1].split(","):
                    x = x.strip().strip("\"'")
                    if x:
                        paths.append(Path(os.path.expanduser(x)).resolve(strict=False))
                in_paths = False
            continue
        if in_paths and indent >= 6 and line.lstrip().startswith("-"):
            item = line.lstrip()[1:].strip().strip("\"'")
            if item:
                paths.append(Path(os.path.expanduser(item)).resolve(strict=False))
    if name is not None:
        result.append((name, paths))
    return result


def parse_dev_root(text: str) -> str:
    data = _load(text)
    if data is not None:
        return str(data.get("dev_root") or DEFAULT_DEV_ROOT)
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("dev_root:") and not raw.startswith(" "):
            val = s.split(":", 1)[1].strip().strip("\"'")
            if val:
                return val
    return DEFAULT_DEV_ROOT


def parse_kb_root(text: str) -> str:
    """The knowledge-base root (config `root:`), mirror of parse_dev_root."""
    data = _load(text)
    if data is not None:
        return str(data.get("root") or DEFAULT_KB_ROOT)
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("root:") and not raw.startswith(" "):
            val = s.split(":", 1)[1].strip().strip("\"'")
            if val:
                return val
    return DEFAULT_KB_ROOT


def find_project(cwd: Path, projects):
    cwd = cwd.resolve(strict=False)
    best, best_len = None, -1
    for name, paths in projects:
        for p in paths:
            try:
                cwd.relative_to(p)
            except ValueError:
                continue
            if len(str(p)) > best_len:
                best, best_len = name, len(str(p))
    return best


def main():
    args = sys.argv[1:]
    cp = config_path()
    text = cp.read_text(encoding="utf-8") if cp.exists() else None

    if args and args[0] == "--dev-root":
        # default works even without a config file
        print(os.path.expanduser(parse_dev_root(text) if text is not None else DEFAULT_DEV_ROOT))
        sys.exit(0)

    if args and args[0] == "--kb-root":
        print(os.path.expanduser(parse_kb_root(text) if text is not None else DEFAULT_KB_ROOT))
        sys.exit(0)

    if len(args) > 1:
        print("usage: resolve-project.py [<cwd>] | --dev-root | --kb-root", file=sys.stderr)
        sys.exit(64)

    if text is None:
        print(f"config missing or unreadable: {cp}", file=sys.stderr)
        sys.exit(2)

    projects = parse_projects(text)
    if not projects:
        sys.exit(1)

    cwd = Path(args[0]) if args else Path.cwd()
    name = find_project(cwd, projects)
    if name:
        print(name)
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
