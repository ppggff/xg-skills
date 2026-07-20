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
  workflow-status.py --trace <project>/<card>   # R→design→task→test→commit trace matrix
                                       # (<card> = NNN or a slug fragment; a card-dir path works too)
"""
import fnmatch
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


TASK_ROW_ID = re.compile(r"^(?:T|Task ?)?(\d{1,3})(?![\d-])", re.I)
DONE_PREFIXES = ("done", "[x]", "✅", "pass")


def _status_done(status):
    """007 R3 done-mapping: canonical + observed variants; unjudgeable → not done."""
    return status.strip().lower().startswith(DONE_PREFIXES)


def parse_tasks(progress_path):
    """Tolerant Task-status table parser (007 R9): columns keyed by header names, task
    rows identified by the id grammar; unrecognized shapes (e.g. phase rows under the
    heading) degrade to [] — never wrong-semantics rows.
    """
    sect = _section(_read(progress_path), r"Task status")
    lines = [ln for ln in sect.splitlines() if ln.lstrip().startswith("|")]
    if len(lines) < 2:
        return []
    header = [c.strip().lower() for c in lines[0].strip().strip("|").split("|")]

    def col(*names):
        for n in names:
            for i, h in enumerate(header):
                if n in h:
                    return i
        return None

    id_i = col("task", "id", "编号") or 0
    st_i = col("status", "状态", "state")
    no_i = col("notes", "备注", "说明")
    tasks = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) <= id_i or set(cells[id_i]) <= set("-: "):
            continue
        first = re.sub(r"[*`]", "", cells[id_i]).strip()
        m = TASK_ROW_ID.match(first)
        if not m:
            continue
        rest = first[m.end():].strip()
        status = cells[st_i] if st_i is not None and st_i < len(cells) else ""
        notes = cells[no_i] if no_i is not None and no_i < len(cells) else rest
        tasks.append({"id": "T" + m.group(1), "status": status,
                      "done": _status_done(status), "notes": notes})
    return tasks


def norm_blockers(value):
    """007 R1: placeholder blockers (无/None/—/…) normalize to "" at the data source,
    so renderers only test non-emptiness (no second placeholder vocabulary)."""
    s = value.strip().rstrip("。.")
    return "" if not s or s in PLACEHOLDERS or s.lower() == "none" else value


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

# The board's 整体状态 vocabulary (split-isolate.md B). "?" is the missing-row degradation,
# not a state; anything else off-vocabulary gets flagged instead of passing through silently.
CANON_STATES = {"backlog", "todo", "active", "blocked", "paused", "done", "dropped"}


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
                "blockers": norm_blockers(g.get("blockers", "")),
                "tasks": parse_tasks(os.path.join(c, "progress.md")),
                "effective_next": effective_next(state, g, nxt),
                "state_noncanonical": state != "?" and state not in CANON_STATES,
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
                  ("  ⚠ 整体状态非规范(backlog|todo|active|blocked|paused|done|dropped)"
                   if c["state_noncanonical"] else "") +
                  (f"  deps:{deps}" if deps not in ("—", "-", "") else ""))
            print(f"      {'  '.join(c['steps'])}")
            if c["now"]:
                print(f"      Now : {c['now'][:110]}")
            print(f"      Next: {c['effective_next'][:110]}")
            if c["blockers"] and c["blockers"].rstrip("。.") not in ("无", "None", "none", "—"):
                print(f"      ⚠️  {c['blockers'][:110]}")
        print()


# ---- trace (--trace): the R→design→task→test→commit matrix over the designated fields ----
# Derived on demand, never hand-maintained (SKILL.md「Conventions」: downstream→upstream mappings
# are recorded once; the reverse map is derived). Commit tracing rides implement.md's commit
# convention (product commit subjects carry the plan task id).

TASK_HEAD = re.compile(r"^###\s+(?:Task\s*|T)(\d+)\s*[::]?\s*(.*)$", re.M)
RID = re.compile(r"\bR(\d+)\b")


def _read(path):
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        return ""


def _section(text, title_pat):
    """Body of the first `## …` section whose title matches title_pat, else ""."""
    for m in re.finditer(r"^##\s+(.+)$", text, re.M):
        if re.search(title_pat, m.group(1)):
            start = m.end()
            nxt = re.search(r"^##\s", text[start:], re.M)
            return text[start:start + nxt.start()] if nxt else text[start:]
    return ""


def trace_requirement(card):
    """R-id → statement, from the 需求条目 table (first cell carries the id)."""
    items = {}
    for m in re.finditer(r"^\|\s*\[?(R\d+)\]?[^|]*\|([^|]*)\|",
                         _read(os.path.join(card, "requirement.md")), re.M):
        items.setdefault(m.group(1), re.sub(r"\*\*", "", m.group(2)).strip())
    return items


def _rows_by_rid(sect):
    out = {}
    for line in sect.splitlines():
        if not line.lstrip().startswith("|") or set(line.strip()) <= set("|-: "):
            continue
        for rid in RID.findall(line):
            out.setdefault("R" + rid, re.sub(r"\s*\|\s*", " · ", line).strip(" ·"))
    return out


def trace_design(card):
    """R-id → its How-it-meets row (design home) and its 验证策略 row."""
    text = _read(os.path.join(card, "design.md"))
    return (_rows_by_rid(_section(text, r"How it meets|如何满足")),
            _rows_by_rid(_section(text, r"验证策略|Verification strategy")))


def trace_plan(card):
    """T-id → {title, rids, state}, from plan.md task blocks (`### T<n>:` / `### Task <n>:`)."""
    text = _read(os.path.join(card, "plan.md"))
    tasks, heads = {}, list(TASK_HEAD.finditer(text))
    for i, m in enumerate(heads):
        block = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        nxt = re.search(r"^###\s", block, re.M)  # cut at Checkpoint/Final headings
        if nxt:
            block = block[:nxt.start()]
        imp = re.search(r"\*\*Implements:?\*\*[::]?\s*(.+)", block)
        boxes = re.findall(r"^\s*-\s*\[([ x!])\]", block, re.M)
        tasks[m.group(1)] = {
            "title": m.group(2).strip(),
            "rids": ["R" + r for r in RID.findall(imp.group(1))] if imp else [],
            "state": ("done" if boxes and all(b == "x" for b in boxes)
                      else "failed" if "!" in boxes else "todo" if boxes else "?"),
        }
    return tasks


def trace_test(card):
    """R-id → covered-by, from test.md coverage rows (first cell cites the id; last cell = test)."""
    cov = {}
    for line in _read(os.path.join(card, "test.md")).splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        for rid in RID.findall(cells[0]):
            cov.setdefault("R" + rid, cells[-1])
    return cov


def project_repo(project):
    """The project's first configured path (shared config) — the --trace repo fallback."""
    cfg = os.path.expanduser("~/.config/xg-knowledge-wiki/config.yaml")
    try:
        lines = open(cfg, encoding="utf-8").read().splitlines()
    except OSError:
        return None
    in_projects = in_target = False
    for line in lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_projects, in_target = line.strip().startswith("projects:"), False
            continue
        if not in_projects:
            continue
        if indent == 2:
            in_target = line.strip().rstrip(":") == project
            continue
        if in_target and line.strip().startswith("paths:"):
            tail = line.split(":", 1)[1].strip()
            if tail.startswith("["):
                first = tail.strip("[]").split(",")[0].strip().strip("\"'")
                if first:
                    return os.path.expanduser(first)
            continue
        if in_target and line.lstrip().startswith("-"):
            return os.path.expanduser(line.lstrip()[1:].strip().strip("\"'"))
    return None


def card_in_message(nnn, oneline):
    """True when the card number appears in the commit message text of a --oneline row.

    The abbreviated hash is excluded from the match: its hex digits can contain the
    card number by coincidence (e.g. hash a400654 vs card 006).
    """
    msg = oneline.split(" ", 1)[1] if " " in oneline else ""
    return nnn in msg


def task_commits(repo, tid, nnn=None):
    """Product commits citing T<n>/Task <n> (implement.md commit convention); best-effort.

    Two tiers: commits also naming the card NNN are strict hits (the card-qualified
    convention); bare T<n> hits are loose — cross-card T-ids collide, so they render
    with a ? marker. Returns (lines, "strict"|"loose").
    """
    import subprocess
    pat = r"(^|[^A-Za-z0-9])T(ask ?)?%s([^0-9]|$)" % tid
    try:
        out = subprocess.run(["git", "-C", repo, "log", "--all", "--oneline", "-E", "--grep", pat],
                             capture_output=True, text=True, timeout=10)
        lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
    except Exception:
        return [], "strict"
    if nnn:
        strict = [ln for ln in lines if card_in_message(nnn, ln)]
        if strict:
            return strict, "strict"
    return lines, "loose"


def resolve_card(root, arg):
    """`<project>/<card>` (card = NNN or slug fragment) or a card-dir path → (project, card_dir)."""
    if os.path.isdir(arg) and glob.glob(os.path.join(arg, "*.md")):
        d = os.path.abspath(arg)
        return os.path.basename(os.path.dirname(d)), d
    proj, _, card = arg.partition("/")
    pdir = os.path.join(root, proj)
    if not os.path.isdir(pdir):
        raise SystemExit(f"trace: no such project dir {pdir}")
    pats = [card + "*", "*" + card + "*"] if card else ["*"]
    for pat in pats:
        hits = sorted(glob.glob(os.path.join(pdir, "[0-9][0-9][0-9]-*")))
        hits = [h for h in hits if fnmatch.fnmatch(os.path.basename(h), pat)]
        if len(hits) == 1:
            return proj, hits[0]
        if len(hits) > 1:
            raise SystemExit("trace: ambiguous card, matches: " +
                             ", ".join(os.path.basename(h) for h in hits))
    raise SystemExit(f"trace: no card matching '{card}' under {pdir}")


def trace_data(project, card_dir):
    """Single-source trace derivation (007 design, ADR-0001): per-R rows consumed by
    the CLI text renderer, `--trace --json`, and the viewer's /api/trace.

    Per-task / per-R `commit_state` is four-valued: strict / loose / none (checked,
    no hit) / unchecked (no repo anchor — never counted as a gap). Commit lists are
    complete; display truncation belongs to renderers.
    """
    import datetime
    reqs = trace_requirement(card_dir)
    home, verify = trace_design(card_dir)
    tasks = trace_plan(card_dir)
    cov = trace_test(card_dir)
    repo = frontmatter(os.path.join(card_dir, "progress.md")).get("repo", "") or \
        project_repo(project)
    if repo:
        repo = os.path.expanduser(repo)
        if not os.path.isdir(os.path.join(repo, ".git")):
            repo = None
    nnn = os.path.basename(card_dir)[:3]

    task_rows = {}
    for tid, t in tasks.items():
        if repo:
            lines, tier = task_commits(repo, tid, nnn)
            commit_state = tier if lines else "none"
        else:
            lines, commit_state = [], "unchecked"
        task_rows[tid] = {"tid": tid, "title": t["title"], "state": t["state"],
                          "commits": lines, "commit_state": commit_state}

    by_r = {}
    for tid, t in tasks.items():
        for r in t["rids"]:
            by_r.setdefault(r, []).append(tid)
    all_r = sorted(set(reqs) | set(home) | set(by_r) | set(cov), key=lambda r: int(r[1:]))

    rows = []
    for r in all_r:
        tids = by_r.get(r, [])
        states = [task_rows[t]["commit_state"] for t in tids]
        commit_state = ("unchecked" if not repo else
                        "strict" if "strict" in states else
                        "loose" if "loose" in states else "none")
        flags = [w for cond, w in ((r not in reqs, "not-in-需求条目"),
                                   (r not in home, "no-design-home"),
                                   (r not in by_r, "no-task"),
                                   (r not in cov, "no-test-coverage")) if cond]
        rows.append({"rid": r, "text": reqs.get(r, ""),
                     "design": home.get(r, ""), "verify": verify.get(r, ""),
                     "test": cov.get(r, ""), "tasks": [task_rows[t] for t in tids],
                     "flags": flags,
                     "present": {"design": r in home, "verify": r in verify,
                                 "task": bool(tids), "test": r in cov,
                                 "commit": commit_state}})
    orphans = [t for t, v in sorted(tasks.items(), key=lambda kv: int(kv[0]))
               if not v["rids"]]
    return {"card": f"{project}/{os.path.basename(card_dir)}", "repo": repo or "",
            "repo_anchor": bool(repo),
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "rows": rows, "orphans": orphans, "error": ""}


def render_trace(project, card_dir):
    d = trace_data(project, card_dir)
    print(f"🔗 {d['card']}" + (f"  repo: {d['repo']}" if d["repo"] else ""))
    W = 100
    for row in d["rows"]:
        flags = ["⚠ " + f for f in row["flags"]]
        print(f"{row['rid']}  {row['text'][:64]}" + ("  " + " ".join(flags) if flags else ""))
        if row["design"]:
            print(f"    design : {row['design'][:W]}")
        if row["verify"]:
            print(f"    verify : {row['verify'][:W]}")
        for t in row["tasks"]:
            print(f"    task   : T{t['tid']} [{t['state']}] {t['title'][:64]}")
            label = "commit" if t["commit_state"] == "strict" else "commit?"  # loose = bare-T cross-card risk
            for c in t["commits"][:6]:
                print(f"      {label}: {c[:W]}")
    if d["orphans"]:
        print("—  tasks with no R-id (scaffolding?): " + ", ".join("T" + t for t in d["orphans"]))
    if not d["repo_anchor"]:
        print("(commits skipped — no git repo anchor: progress.md `repo:` or config projects path)")
    return 0


def main():
    args, want, root_arg, as_json, trace_arg, i = sys.argv[1:], [], None, False, None, 0
    while i < len(args):
        a = args[i]
        if a in ("--root", "--trace") and i + 1 < len(args):
            if a == "--root":
                root_arg = args[i + 1]
            else:
                trace_arg = args[i + 1]
            i += 2
            continue
        if a.startswith("--root="):
            root_arg = a.split("=", 1)[1]
        elif a.startswith("--trace="):
            trace_arg = a.split("=", 1)[1]
        elif a == "--json":
            as_json = True
        elif not a.startswith("--"):
            want.append(a)
        i += 1
    root = os.path.expanduser(root_arg) if root_arg else dev_root()
    if trace_arg:
        if as_json:
            print(json.dumps(trace_data(*resolve_card(root, trace_arg)), ensure_ascii=False))
            return 0
        return render_trace(*resolve_card(root, trace_arg))
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
