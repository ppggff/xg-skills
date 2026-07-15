#!/usr/bin/env python3
"""Register a project + path mapping into ~/.config/xg-knowledge-wiki/config.yaml.

Usage:
  register-project.py <project-name> <path>

Behavior:
  - If config missing → create with `root: ~/knowledge` + this mapping
  - If `projects:` missing → append the section
  - If project exists → append path (no duplicate)
  - If project + exact path exist → no-op, exit 0

Output: one line summary of what changed. Exit 0 on success.
"""
import os
import sys
from pathlib import Path


CONFIG_PATH = Path.home() / ".config" / "xg-knowledge-wiki" / "config.yaml"


def normalize_path(p: str) -> str:
    """Preserve `~` for portability; strip trailing slashes."""
    p = p.rstrip("/")
    if p == "":
        p = "/"
    home = str(Path.home())
    if p.startswith(home):
        p = "~" + p[len(home):]
    return p


def write_with_yaml(name: str, path: str) -> bool:
    """Round-trip via PyYAML if available. Returns True on success."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return False

    data = {}
    if CONFIG_PATH.exists():
        text = CONFIG_PATH.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
    data.setdefault("root", "~/knowledge")
    projects = data.setdefault("projects", {})
    proj = projects.setdefault(name, {})
    paths = proj.setdefault("paths", [])
    if path not in paths:
        paths.append(path)
        action = "added"
    else:
        action = "no-op (already present)"

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"{action}: projects.{name}.paths += {path}")
    return True


def write_text_fallback(name: str, path: str) -> None:
    """Plain text manipulation when PyYAML is not installed.

    Tries to preserve existing config layout; appends entries in canonical form.
    """
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            f"root: ~/knowledge\nprojects:\n  {name}:\n    paths:\n      - {path}\n",
            encoding="utf-8",
        )
        print(f"created config: projects.{name}.paths += {path}")
        return

    text = CONFIG_PATH.read_text(encoding="utf-8")

    if "projects:" not in text:
        # Append the projects section
        if not text.endswith("\n"):
            text += "\n"
        text += f"projects:\n  {name}:\n    paths:\n      - {path}\n"
        CONFIG_PATH.write_text(text, encoding="utf-8")
        print(f"added projects section: projects.{name}.paths += {path}")
        return

    lines = text.splitlines()

    # Find projects: section bounds
    proj_start = None
    for i, line in enumerate(lines):
        if line.strip() == "projects:":
            proj_start = i
            break

    if proj_start is None:  # shouldn't reach
        lines.append(f"projects:\n  {name}:\n    paths:\n      - {path}")
        CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    # Find end of projects section (next top-level key or EOF)
    proj_end = len(lines)
    for i in range(proj_start + 1, len(lines)):
        line = lines[i]
        if line.strip() == "":
            continue
        if not line.startswith(" ") and not line.startswith("\t"):
            proj_end = i
            break

    # Within projects, find the target project header `  <name>:`
    name_header = f"  {name}:"
    target_idx = None
    for i in range(proj_start + 1, proj_end):
        if lines[i].rstrip() == name_header:
            target_idx = i
            break

    if target_idx is None:
        # Insert new project block before proj_end
        block = [f"  {name}:", "    paths:", f"      - {path}"]
        for j, b in enumerate(block):
            lines.insert(proj_end + j, b)
        CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"added project: projects.{name}.paths += {path}")
        return

    # Project exists — locate its paths: list
    paths_idx = None
    for i in range(target_idx + 1, proj_end):
        if lines[i].strip().startswith("paths:"):
            paths_idx = i
            break
        if lines[i].startswith("  ") and not lines[i].startswith("    "):
            break  # next project

    if paths_idx is None:
        # Add paths: under this project
        block = ["    paths:", f"      - {path}"]
        for j, b in enumerate(block):
            lines.insert(target_idx + 1 + j, b)
        CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"added paths to existing project: projects.{name}.paths += {path}")
        return

    # Scan existing paths to avoid dup
    item_end = paths_idx + 1
    while item_end < proj_end:
        ln = lines[item_end]
        if not ln.strip():
            item_end += 1
            continue
        if ln.lstrip().startswith("- "):
            existing = ln.lstrip()[2:].strip().strip("\"'")
            if existing == path:
                print(f"no-op (already present): projects.{name}.paths includes {path}")
                return
            item_end += 1
            continue
        break

    lines.insert(item_end, f"      - {path}")
    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"appended path: projects.{name}.paths += {path}")


def main():
    if len(sys.argv) != 3:
        print("usage: register-project.py <project-name> <path>", file=sys.stderr)
        sys.exit(64)

    name = sys.argv[1].strip()
    raw = sys.argv[2]
    if not name or "/" in name or ":" in name or " " in name:
        print(f"invalid project name: {name!r}", file=sys.stderr)
        sys.exit(65)

    path = normalize_path(raw)

    if write_with_yaml(name, path):
        return
    write_text_fallback(name, path)


if __name__ == "__main__":
    main()
