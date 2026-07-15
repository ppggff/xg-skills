#!/usr/bin/env python3
"""check-code-refs.py — flag workflow/KB doc references leaked into code.

Code comments must not reference workflow/KB docs — .md files, dev_root /
~/knowledge paths, [[wiki/...]] links, ADR-NNNN — or line numbers; they rot
and leak private paths (implement.md "Comment & artifact hygiene"). Bare
legacy-dir names (plan/, problem/) are NOT matched: too collision-prone with
real code paths. Issue/ticket refs (#1234, JIRA-42) are fine and not flagged.

Advisory, not auto-strip: a hit in a tool whose domain IS the docs (e.g. a
KB script naming index.md) is legitimate — judge each hit.

Lives only in xg-dev-workflow/tools/ (not a synced copy).

Usage:
  check-code-refs.py                 # scan added lines of the working diff vs HEAD
  check-code-refs.py --base <ref>    # diff against <ref> instead
  check-code-refs.py <file>...       # scan whole files

Prints `file:line: [pattern] match`; quiet when clean. Exit 1 on hits, 0 clean.
"""
import re
import subprocess
import sys

DOC_EXTS = (".md", ".markdown", ".rst", ".txt")
# repo-public docs are stable anchors (like issue refs), not workflow leaks
PUBLIC_DOCS = {"readme.md", "changelog.md", "contributing.md", "license.md",
               "code_of_conduct.md", "security.md"}
PATTERNS = [
    (re.compile(r"\[\[(?:wiki|raw)/[^\]\n]*\]*"), "KB wikilink"),
    (re.compile(r"\bADR-?\d+\b", re.I), "ADR reference"),
    # (?<!xg-): the skill's own directory name xg-dev-workflow is not a leaked path
    (re.compile(r"[\w./~-]*(?:(?<!xg-)dev-workflow|dev_root)[\w./-]*"), "dev_root path"),
    (re.compile(r"~/knowledge[\w./-]*"), "KB path"),
    (re.compile(r"\b[\w-]+\.md\b"), ".md reference"),
    (re.compile(r"\b[\w-]+\.(?:c|h|cc|cpp|go|py|rs|ts|tsx|js|java)\s*:\s*\d+"), "file:line"),
    (re.compile(r"\bline\s+\d+\b", re.I), "line-number reference"),
]


def is_code_file(path):
    # Skip docs and vendored/minified blobs: a minified *.min.js is generated third-party code,
    # not hand-authored comments, so the doc-reference rule doesn't apply (its packed short
    # identifiers false-match the dotted-filename patterns).
    p = path.lower()
    return not p.endswith(DOC_EXTS) and not p.endswith(".min.js")


def scan_line(path, lineno, text, hits):
    for rx, label in PATTERNS:
        for m in rx.finditer(text):
            if label == ".md reference" and m.group(0).lower() in PUBLIC_DOCS:
                continue  # allowlisted; keep looking for a real hit on this line
            hits.append(f"{path}:{lineno}: [{label}] {m.group(0).strip()}")
            break


def scan_diff(base):
    out = subprocess.run(
        ["git", "diff", "-U0", base, "--"],
        capture_output=True, text=True,
    ).stdout
    hits, path, lineno = [], None, 0
    for line in out.splitlines():
        # header check needs the space: added content "++counter" arrives as "+++counter"
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+++ "):
            path = None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+"):
            if path and is_code_file(path):
                scan_line(path, lineno, line[1:], hits)
            lineno += 1
    return hits


def scan_files(paths):
    hits = []
    for p in paths:
        if not is_code_file(p):
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for i, text in enumerate(f, 1):
                    scan_line(p, i, text.rstrip("\n"), hits)
        except OSError as e:
            print(f"(skipped {p}: {e})", file=sys.stderr)
    return hits


def main():
    args = sys.argv[1:]
    base = "HEAD"
    if args[:1] == ["--base"] and len(args) >= 2:
        base, args = args[1], args[2:]
    hits = scan_files(args) if args else scan_diff(base)
    for h in hits:
        print(h)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
