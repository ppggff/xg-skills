#!/usr/bin/env python3
"""workflow-status.py — the card view: per-card pipeline position + next step.

Read-only aggregation over dev_root docs (nothing written or cached — the docs
stay the single source of truth): each card's phase-doc frontmatter, the kanban
整体状态/Deps, and progress.md's State-at-a-glance bullets. Backs the `status`
verb. When progress.md carries no Next-step bullet, the next step is derived
from the gate ladder (需求 confirm → 设计 freeze → 详设/plan → implement →
test → close-out review).

Lives only in xg-dev-workflow/tools/ (not a synced copy).

Usage:
  workflow-status.py [<project> ...]   # default: every project under dev_root
  workflow-status.py --root DIR        # override dev_root
  workflow-status.py --json            # machine-readable board ({project: [card…]}); backs the viewer
"""
import glob
import json
import os
import re
import sys


def dev_root():
    cfg = os.path.expanduser("~/.config/xg-knowledge-wiki/config.yaml")
    if os.path.exists(cfg):
        try:
            for line in open(cfg, encoding="utf-8"):
                m = re.match(r"dev_root:\s*(\S+)", line)  # top-level only
                if m:
                    return os.path.expanduser(m.group(1).strip().strip("\"'"))
        except Exception:
            pass
    return os.path.expanduser("~/dev-workflow")


def frontmatter(path):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(1500)
    except OSError:
        return {}
    if not head.startswith("---"):
        return {}
    end = head.find("\n---", 3)
    fields = {}
    for line in head[:end if end != -1 else None].splitlines():
        m = re.match(r"(\w+):\s*(.+)", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


GLANCE_KEYS = [("now", r"Now doing|当前"), ("next", r"Next step|下一步|Next\b"),
               ("blockers", r"Blockers?|阻塞"), ("phase", r"Phase")]


def glance(progress_path):
    out = {}
    try:
        text = open(progress_path, encoding="utf-8").read()
    except OSError:
        return out
    sect = re.split(r"^## ", text, flags=re.M)
    body = next((s for s in sect if s.startswith("State at a glance")), "")
    for key, pat in GLANCE_KEYS:
        m = re.search(r"^- \*\*(?:%s)[^*]*\*\*[::]?\s*(.+)" % pat, body, re.M)
        if m:
            out[key] = re.sub(r"\*\*", "", m.group(1)).strip()
    return out


def board(project_dir):
    rows = {}
    try:
        text = open(os.path.join(project_dir, "index.md"), encoding="utf-8").read()
    except OSError:
        return rows
    for m in re.finditer(r"^\|\s*(\d{3})\s*\|([^|]*)\|([^|]*)\|([^|]*)\|", text, re.M):
        rows[m.group(1)] = {"phase": m.group(2).strip(), "state": m.group(3).strip(),
                            "deps": m.group(4).strip()}
    return rows


def card_status(card_dir):
    p = lambda name: os.path.join(card_dir, name)
    req = frontmatter(p("requirement.md"))
    des = frontmatter(p("design.md"))
    det = frontmatter(p("detail.md"))
    prog = frontmatter(p("progress.md"))
    tst = frontmatter(p("test.md"))
    has_plan = os.path.exists(p("plan.md"))
    reviews = glob.glob(p("notes/review-*.md"))
    g = glance(p("progress.md"))
    skip_note = False
    try:
        ptext = open(p("progress.md"), encoding="utf-8").read()
        skip_note = "review skipped" in ptext or "pre-gate done" in ptext
    except OSError:
        pass

    steps, nxt = [], None

    def step(label, state, gate=None):
        nonlocal nxt
        steps.append(f"{label}:{state}")
        if nxt is None and gate:
            nxt = gate

    rs = req.get("status", "?" if not req else "drafting")
    step("需求", rs, None if rs == "confirmed" else "GATE: 需求待 confirm")
    if not des:
        step("设计", "—", "next: design")
    else:
        ds = des.get("status", "drafting")
        step("设计", ds, None if ds in ("frozen", "approved") else "GATE: 设计待 approve/freeze")
    step("详设", det.get("status", "✓") if det else "—",
         None)  # optional phase: absence is legal (XS/S), never gates
    if not has_plan:
        step("实现", "—", "next: plan (详设 for M+ structural first)")
    else:
        ps = prog.get("status", "?")
        cur = prog.get("current_task", "")[:24]
        step("实现", ps + (f"@{cur}" if cur and ps == "in-progress" else ""),
             "next: implement — continue plan tasks" if ps in ("not-started", "in-progress") else
             ("BLOCKED — see progress" if ps == "blocked" else
              ("implement 状态不明(progress frontmatter 缺 status)— 看 progress.md" if ps == "?" else None)))
    ts = tst.get("status", "—") if tst else "—"
    step("测试", ts, None if ts == "passing" else "next: 测试 consolidation")
    if reviews:
        step("评审", "✓")
    elif skip_note:
        step("评审", "skipped")
    else:
        step("评审", "—", "next: close-out review (M+) or record skip")
    if nxt is None:
        nxt = "done — nothing pending"
    return steps, g, nxt


PLACEHOLDERS = {"…", "...", "—", "-", "无", "TBD", "待定"}


def effective_next(board_state, g, derived):
    # a human-set done outranks derived gates; progress's own Next-step outranks both
    nxt = g.get("next", "").strip().rstrip("。.")
    if nxt and nxt not in PLACEHOLDERS:
        return g["next"]
    if board_state == "done":
        return "—(board=done;derived: " + derived + ")" if not derived.startswith("done") else "—"
    return derived


def iter_cards(root, want=None):
    """Yield one dict per card — the machine-readable board (shared by the text view and --json).

    `want` (a project-name list) preserves the caller's order and, mirroring the pre-refactor
    text view, enumerates the named projects directly (no index.md gate). With no `want`, glob
    every project that has an index.md, sorted. Fields are pinned by the viewer's /api/board
    schema (see _serve_board in viewer.py); missing frontmatter degrades to "?"/"" (never a
    missing key). Duplicate NNN prefixes in one project → stderr warning (board() keys by bare
    NNN, so the row would be shared; steps/now stay per-dir correct).
    """
    if want:
        projects = [p for p in want if os.path.isdir(os.path.join(root, p))]
    else:
        projects = sorted(os.path.basename(d) for d in glob.glob(os.path.join(root, "*"))
                          if os.path.isfile(os.path.join(d, "index.md")))
    for proj in projects:
        pdir = os.path.join(root, proj)
        cards = sorted(glob.glob(os.path.join(pdir, "[0-9][0-9][0-9]-*")))
        rows = board(pdir)
        seen = set()
        for c in cards:
            nnn = os.path.basename(c)[:3]
            if nnn in seen:
                print(f"warning: duplicate card NNN {proj}/{nnn} — board row shared",
                      file=sys.stderr)
            seen.add(nnn)
            row = rows.get(nnn, {})
            state = row.get("state", "?")
            steps, g, nxt = card_status(c)
            yield {
                "project": proj, "nnn": nnn, "dir": os.path.basename(c),
                "phase": row.get("phase", "?"), "state": state, "deps": row.get("deps", "—"),
                "steps": steps,
                "now": g.get("now", ""), "next_progress": g.get("next", ""),
                "blockers": g.get("blockers", ""),
                "effective_next": effective_next(state, g, nxt),
                # 003/R6: optional card→branch, deep-linked to that branch in the gitweb companion
                "branch": frontmatter(os.path.join(c, "progress.md")).get("branch", ""),
            }


def render_text(cards):
    by_proj = {}
    for c in cards:
        by_proj.setdefault(c["project"], []).append(c)
    for proj, cs in by_proj.items():
        print(f"📋 {proj}")
        for c in cs:
            deps = c["deps"]
            print(f"  {c['dir']}  [{c['state']}]" +
                  (f"  deps:{deps}" if deps not in ("—", "-", "") else ""))
            print(f"      {'  '.join(c['steps'])}")
            if c["now"]:
                print(f"      Now : {c['now'][:110]}")
            print(f"      Next: {c['effective_next'][:110]}")
            if c["blockers"] and c["blockers"].rstrip("。.") not in ("无", "None", "none", "—"):
                print(f"      ⚠️  {c['blockers'][:110]}")
        print()


def main():
    args, want, root_arg, as_json, i = sys.argv[1:], [], None, False, 0
    while i < len(args):
        a = args[i]
        if a == "--root" and i + 1 < len(args):
            root_arg, i = args[i + 1], i + 2
            continue
        if a.startswith("--root="):
            root_arg = a.split("=", 1)[1]
        elif a == "--json":
            as_json = True
        elif not a.startswith("--"):
            want.append(a)
        i += 1
    root = os.path.expanduser(root_arg) if root_arg else dev_root()
    cards = list(iter_cards(root, want or None))
    if as_json:
        grouped = {}
        for c in cards:
            grouped.setdefault(c["project"], []).append(c)
        print(json.dumps(grouped, ensure_ascii=False))
    else:
        render_text(cards)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"(workflow-status: {e})", file=sys.stderr)
        sys.exit(0)
