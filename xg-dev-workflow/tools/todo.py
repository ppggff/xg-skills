#!/usr/bin/env python3
"""Read and write the viewer's todo files (<dev_root>/todo/*.md) from scripts and mods.

An item is a markdown task line the viewer reads (sv.js parseTodo / todoMeta):
  - [ ] <first line>[ @<project>] ➕ YYYY-MM-DD HH:MM:SS   (marks read with or without the seconds)
followed by the text's further lines as continuation lines indented four spaces (four, so a ``` line
is not a fence to the viewer). A continuation that starts with a backslash or looks like a task item
gets one more leading backslash, so the viewer never reads it as an item; reading drops one.

An item is found again by file + created stamp + key, the key being its first line with the date and
priority marks taken out and runs of whitespace folded (the viewer's todoMeta text). Continuations are
not part of the key: the viewer edits only an item's first line.

Usage (stdout is one JSON value; on failure exit 1 and one line on stderr):
  todo.py add [--project P | --cwd DIR] [--file inbox.md]   < text
      -> {file, created, key, text, listed, project}   (listed: the text `list` will read back for it)
  todo.py list [--open] [--project P]
      -> [{file, line, depth, done, created, key, text, project}]   (depth: the indent before the list marker)
  todo.py done --file F --created C --key K
      -> {ok: true, line} | {ok: false, reason: "not-found"}   (an invalid file name is a failure, exit 1)
Options: --dev-root DIR (default: the shared config's dev_root) · --now "YYYY-MM-DD HH:MM" (tests)
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

TODO_DIR = "todo"
INBOX = "inbox.md"
RETRIES = 3
# Mirrors of sv.js: TODO_RE, FENCE_RE, TODO_MARKS, and viewer.py TODO_NAME.
TODO_RE = re.compile(r"^(\s*(?:[-*+]|\d+[.)]) \[)( |x|X)(\] )(.*)$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
TODO_MARKS = re.compile(r"(?:➕|📅|✅)\s*\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?|⏫|🔼|🔽")
TODO_NAME = re.compile(r"[^/\\\x00-\x1f.][^/\\\x00-\x1f]{0,118}\.md")
TAG_RE = re.compile(r"(^|\s)[@#]([\w.-]+)")
LINK_RE = re.compile(r"\[\[[^\]]*\]\]|\[[^\]]*\]\([^)]*\)")
CREATED_RE = re.compile(r"➕\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)")
DONE_MARK_RE = re.compile(r"\s*✅\s*\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?\s*$")
TRAIL_TAG_RE = re.compile(r"\s@([\w.-]+)$")
# JS ends a line at \r, U+2028 and U+2029 too; the viewer would split an item there, so input is normalized.
NEWLINES_RE = re.compile("\r\n?|[\u2028\u2029]")
INDENT = "    "


class TodoError(Exception):
    pass


def _resolve_project_module():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("resolve_project", os.path.join(here, "resolve-project.py"))
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    return rp


def _config_text():
    rp = _resolve_project_module()
    cfg = rp.config_path()
    return rp, (cfg.read_text(encoding="utf-8") if cfg.exists() else None)


def default_dev_root() -> str:
    rp, text = _config_text()
    return os.path.expanduser(rp.parse_dev_root(text) if text is not None else rp.DEFAULT_DEV_ROOT)


def known_projects() -> set:
    rp, text = _config_text()
    return {name for name, _ in rp.parse_projects(text)} if text is not None else set()


def project_of_cwd(cwd: str):
    rp, text = _config_text()
    return rp.find_project(Path(cwd), rp.parse_projects(text)) if text is not None else None


def key_of(first: str) -> str:
    return re.sub(r"\s{2,}", " ", TODO_MARKS.sub("", first)).strip()


def tags_of(first: str) -> list:
    tags = []
    for m in TAG_RE.finditer(LINK_RE.sub(" ", first)):
        if m.group(2) not in tags:
            tags.append(m.group(2))
    return tags


def escape(line: str) -> str:
    return "\\" + line if line.startswith("\\") or TODO_RE.match(line) else line


def unescape(line: str) -> str:
    return line[1:] if line.startswith("\\") else line


def trailing_project(first: str, projects: set):
    m = TRAIL_TAG_RE.search(TODO_MARKS.sub("", first).rstrip())
    return m.group(1) if m and m.group(1) in projects else None


def render(text: str, project, stamp: str, projects: set) -> list:
    """The item's lines. A first line ending in a project tag gets one appended even when present, so that `parse`,
    which drops one trailing project tag as the script's own, gives the text back unchanged."""
    first, *rest = text.split("\n")
    ends = trailing_project(first, projects)
    tag = project if project and (project not in tags_of(first) or ends) else ends
    suffix = f" @{tag}" if tag else ""
    lines = [f"- [ ] {first}{suffix} ➕ {stamp}"]
    lines += [INDENT + escape(line) if line else "" for line in rest]
    return lines


def is_continuation(line: str) -> bool:
    return line.startswith(INDENT) and not TODO_RE.match(line)


def parse(text: str, file: str, projects: set) -> list:
    """Every task item outside code fences, with the continuation lines this script writes."""
    lines = text.split("\n")
    items, fence, i = [], None, 0
    while i < len(lines):
        line = lines[i]
        f = FENCE_RE.match(line)
        if fence is None:
            if f and not (f.group(1)[0] == "`" and "`" in f.group(2)):
                fence = f.group(1)
                i += 1
                continue
        else:
            if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence) and not f.group(2).strip():
                fence = None
            i += 1
            continue
        m = TODO_RE.match(line)
        if not m:
            i += 1
            continue
        first = m.group(4)
        more, j = [], i + 1
        while j < len(lines):
            nxt = lines[j]
            if is_continuation(nxt):
                more.append(unescape(nxt[len(INDENT):]))
            elif nxt == "" and is_continuation(next((l for l in lines[j + 1:] if l != ""), "")):
                more.append("")
            else:
                break
            j += 1
        tags = tags_of(first)
        created = CREATED_RE.search(first)
        shown = re.sub(r"\s{2,}", " ", TODO_MARKS.sub("", first)).strip()   # as the viewer's todoMeta shows it
        if trailing_project(first, projects):
            shown = shown[:TRAIL_TAG_RE.search(shown).start()]
        items.append({"file": file, "line": i, "depth": len(m.group(1)) - len(m.group(1).lstrip()), "done": m.group(2) != " ",
                      "created": created.group(1) if created else "", "key": key_of(first),
                      "text": "\n".join([shown] + more), "project": tags[0] if tags else None})
        i = j
    return items


def read_file(path: str):
    """(text, stamp); an absent file reads as ("", None). The stamp comes from the open file, so a replace between
    reading and stamping cannot pair old text with the new file's stamp."""
    try:
        with open(path, encoding="utf-8") as f:
            st = os.fstat(f.fileno())
            return f.read(), (st.st_ino, st.st_mtime_ns)
    except FileNotFoundError:
        return "", None


def file_stamp(path: str):
    try:
        st = os.stat(path)
        return st.st_ino, st.st_mtime_ns
    except FileNotFoundError:
        return None


def lock_path(tdir: str) -> str:
    """Outside the todo dir (a versioned docs tree) and at a fixed place, so every caller shares it; one per todo dir."""
    digest = hashlib.sha1(os.path.realpath(tdir).encode("utf-8")).hexdigest()[:12]
    return str(Path.home() / ".config" / "xg-knowledge-wiki" / "todo-locks" / f"{digest}.lock")


def check_plain(tdir: str, path: str):
    """As the viewer refuses: a link could carry the write outside the docs tree."""
    if os.path.islink(tdir) or (os.path.exists(tdir) and not os.path.isdir(tdir)):
        raise TodoError("todo/ is not a plain directory")
    if os.path.islink(path):
        raise TodoError(f"{os.path.basename(path)} is a link")


def edit(tdir: str, name: str, change):
    """Read, change and atomically replace one todo file under a lock shared by this script's writers.

    `change(text)` returns (new_text, result) or (None, result) to leave the file alone. A file whose mtime
    moved since it was read (the viewer, an editor) is read again, up to RETRIES times.
    """
    path = os.path.join(tdir, name)
    check_plain(tdir, path)
    os.makedirs(tdir, exist_ok=True)
    lock = lock_path(tdir)
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    fd_lock = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd_lock, fcntl.LOCK_EX)
        for _ in range(RETRIES):
            text, stamp = read_file(path)
            new, result = change(text)
            if new is None:
                return result
            if file_stamp(path) != stamp:
                continue
            fd, tmp = tempfile.mkstemp(dir=tdir, prefix=".todo.", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(new)
                if file_stamp(path) != stamp:
                    os.unlink(tmp)
                    continue
                os.replace(tmp, path)
            except BaseException:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise
            return result
    finally:
        os.close(fd_lock)
    raise TodoError(f"{name} kept changing while being written; nothing written")


def check_name(name: str) -> str:
    if not TODO_NAME.fullmatch(name) or len(name.encode("utf-8")) > 240:
        raise TodoError(f"not a todo file name: {name!r}")
    return name


def cmd_add(args, tdir: str, stamp: str):
    name = check_name(args.file)
    text = NEWLINES_RE.sub("\n", sys.stdin.read()).strip("\n")
    if not text.strip():
        raise TodoError("empty text")
    project = args.project or (project_of_cwd(args.cwd) if args.cwd else None)
    projects = known_projects()
    lines = render(text, project, stamp, projects)
    item = parse("\n".join(lines), name, projects)[0]

    def append(old):
        base = old if old.strip() else "# todo\n\n"
        if not base.endswith("\n"):
            base += "\n"
        new = base + "\n".join(lines) + "\n"
        if not any(one["line"] == base.count("\n") for one in parse(new, name, projects)):
            raise TodoError(f"an unclosed code fence in {name} would hide the item; nothing written")
        return new, None

    edit(tdir, name, append)
    return {"file": name, "created": item["created"], "key": item["key"], "text": text, "listed": item["text"], "project": project}


def todo_files(tdir: str) -> list:
    try:
        names = sorted(os.listdir(tdir))
    except FileNotFoundError:
        return []
    return [n for n in names if TODO_NAME.fullmatch(n) and os.path.isfile(os.path.join(tdir, n))
            and not os.path.islink(os.path.join(tdir, n))]


def cmd_list(args, tdir: str):
    projects = known_projects()
    items = []
    for name in todo_files(tdir):
        try:
            text = read_file(os.path.join(tdir, name))[0]
        except UnicodeDecodeError:
            print(f"todo.py: skipped {name}: not UTF-8", file=sys.stderr)
            continue
        items += parse(text, name, projects)
    if args.open:
        items = [i for i in items if not i["done"]]
    if args.project:
        items = [i for i in items if args.project in tags_of(i["key"])]
    return items


def cmd_done(args, tdir: str, stamp: str):
    name = check_name(args.file)
    check_plain(tdir, os.path.join(tdir, name))
    if not os.path.isfile(os.path.join(tdir, name)):
        return {"ok": False, "reason": "not-found"}
    today = stamp[:10]

    def tick(text):
        for item in parse(text, name, set()):
            if not item["done"] and item["created"] == args.created and item["key"] == args.key:
                lines = text.split("\n")
                m = TODO_RE.match(lines[item["line"]])
                body = DONE_MARK_RE.sub("", m.group(4)).rstrip()
                lines[item["line"]] = f"{m.group(1)}x{m.group(3)}{body} ✅ {today}"
                return "\n".join(lines), {"ok": True, "line": item["line"]}
        return None, {"ok": False, "reason": "not-found"}

    return edit(tdir, name, tick)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="todo.py", description="Read and write <dev_root>/todo/*.md items.")
    ap.add_argument("--dev-root")
    ap.add_argument("--now", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--project")
    a.add_argument("--cwd")
    a.add_argument("--file", default=INBOX)
    li = sub.add_parser("list")
    li.add_argument("--open", action="store_true")
    li.add_argument("--project")
    d = sub.add_parser("done")
    d.add_argument("--file", required=True)
    d.add_argument("--created", required=True)
    d.add_argument("--key", required=True)
    args = ap.parse_args(argv)

    stamp = args.now or time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        tdir = os.path.join(args.dev_root or default_dev_root(), TODO_DIR)
        if args.cmd == "add":
            out = cmd_add(args, tdir, stamp)
        elif args.cmd == "list":
            out = cmd_list(args, tdir)
        else:
            out = cmd_done(args, tdir, stamp)
    except (TodoError, OSError, ValueError) as e:
        print(f"todo.py: {e}", file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
