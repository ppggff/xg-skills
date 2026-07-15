#!/usr/bin/env python3
"""kb-backlog.py — surface uncompiled raw articles in the xg-knowledge-lite KB.

Lives only in xg-knowledge-lite/tools/ (not a synced copy).

A raw article (`raw/<project>/<slug>.md`) is considered *compiled* when either:
  - its frontmatter carries a non-empty `compiled_to:` (Compile back-annotates
    `[[wiki/...]]`; `compiled_to: deferred — <why>` marks a deliberate deferral
    and also suppresses the flag), or
  - some wiki *concept* references it via the wikilink `[[raw/<project>/<slug>]]`
    (concepts cite their source raws in a Sources section). Curated docs
    (CONTEXT-MAP.md, architecture.md, *-invariants.md) and index.md/log.md do
    NOT count — an invariant ledger citing a raw as evidence is not synthesis.

Everything else is *uncompiled* backlog. Also flags raw files missing YAML
frontmatter (a format defect that breaks Lint / compile tracking).

Designed to run from a SessionStart/Stop hook: prints a compact per-project
summary, stays quiet when nothing is pending, and always exits 0 so it can
never block a session.

Usage:
  kb-backlog.py            # human summary (quiet if clean)
  kb-backlog.py --all      # show every project, even fully-compiled ones
  kb-backlog.py --root DIR # override KB root (default: config or ~/knowledge)
"""
import os
import re
import sys
import glob

def kb_root():
    for i, a in enumerate(sys.argv):
        if a == "--root" and i + 1 < len(sys.argv):
            return os.path.expanduser(sys.argv[i + 1])
    # try config
    cfg = os.path.expanduser("~/.config/xg-knowledge-wiki/config.yaml")
    if os.path.exists(cfg):
        try:
            text = open(cfg, encoding="utf-8").read()
            try:
                import yaml  # type: ignore
                val = (yaml.safe_load(text) or {}).get("root")
                if val:
                    return os.path.expanduser(str(val))
            except ImportError:
                for line in text.splitlines():
                    m = re.match(r"root:\s*(\S+)", line)  # top-level only, no indent
                    if m:
                        return os.path.expanduser(m.group(1).strip().strip('"\''))
        except Exception:
            pass
    return os.path.expanduser("~/knowledge")

def has_frontmatter(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.readline().strip() == "---"
    except Exception:
        return False

def has_compiled_to(path):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(2000)
        # only look inside the frontmatter block
        if not head.startswith("---"):
            return False
        end = head.find("\n---", 3)
        fm = head[:end] if end != -1 else head
        return re.search(r"^compiled_to:\s*\S", fm, re.M) is not None
    except Exception:
        return False

def main():
    root = kb_root()
    raw_root = os.path.join(root, "raw")
    wiki_root = os.path.join(root, "wiki")
    show_all = "--all" in sys.argv
    if not os.path.isdir(raw_root):
        return 0

    # Only concept files count as synthesis (see module docstring).
    NON_CONCEPT = {"index.md", "log.md", "CONTEXT-MAP.md", "architecture.md"}
    referenced = set()
    for wf in glob.glob(os.path.join(wiki_root, "**", "*.md"), recursive=True):
        base = os.path.basename(wf)
        if base in NON_CONCEPT or base.endswith("-invariants.md"):
            continue
        try:
            txt = open(wf, encoding="utf-8").read()
        except Exception:
            continue
        for m in re.finditer(r"\[\[raw/([^/\]|]+)/([^\]|#]+)", txt):
            referenced.add((m.group(1).strip(), m.group(2).strip()))

    rows = []  # (project, total, uncompiled[list], nofm[list], wiki_count)
    total_uncompiled = 0
    for proj_dir in sorted(glob.glob(os.path.join(raw_root, "*"))):
        if not os.path.isdir(proj_dir):
            continue
        project = os.path.basename(proj_dir)
        raws = sorted(glob.glob(os.path.join(proj_dir, "*.md")))
        if not raws:
            continue
        uncompiled, nofm = [], []
        for r in raws:
            slug = os.path.basename(r)[:-3]
            if not has_frontmatter(r):
                nofm.append(slug)
            if has_compiled_to(r) or (project, slug) in referenced:
                continue
            uncompiled.append(slug)
        wiki_count = len(glob.glob(os.path.join(wiki_root, project, "*.md")))
        total_uncompiled += len(uncompiled)
        rows.append((project, len(raws), uncompiled, nofm, wiki_count))

    pending = [r for r in rows if r[2] or r[3]]
    if not pending and not show_all:
        return 0  # quiet when clean

    print("📚 KB compile backlog (xg-knowledge-lite):")
    for project, total, uncompiled, nofm, wiki_count in (rows if show_all else pending):
        print(f"  {project}: {total} raw / {wiki_count} wiki"
              f" · {len(uncompiled)} uncompiled" + (f" · {len(nofm)} no-frontmatter" if nofm else ""))
        for s in uncompiled:
            tag = " [NO frontmatter]" if s in nofm else ""
            print(f"      - {s}{tag}")
        for s in nofm:
            if s not in uncompiled:
                print(f"      - {s} [NO frontmatter, but compiled]")
    if total_uncompiled:
        print(f"  → run `xg-knowledge-lite compile <project>` to synthesize, "
              f"or note as deliberately-deferred.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # never block a session
        print(f"(kb-backlog: skipped — {e})", file=sys.stderr)
        sys.exit(0)
