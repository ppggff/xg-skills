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
  workflow-status.py --check <project>/<card>   # deterministic checks: ledger (a)-(e) +
                                                #   design.md required sections (f) +
                                                #   facts.md marker integrity (g);
                                       # exit 1 on findings (M3 deterministic subset)
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
    pt_i = col("part")
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
        part = cells[pt_i] if pt_i is not None and pt_i < len(cells) else ""
        tasks.append({"id": "T" + m.group(1), "status": status,
                      "done": _status_done(status), "notes": notes,
                      "part": norm_part(part)})
    return tasks


def norm_part(value):
    """Part values normalize at the data source (norm_blockers' rule, 007 R1):
    markup (**bold**/`code`) stripped and placeholders (—/-/…) → "", so canonical
    names compare equal across design table / plan field / progress column."""
    s = re.sub(r"[*`]", "", value).strip()
    return "" if not s or s in PLACEHOLDERS else s


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
    # 010: ledger overlay — a level with pending decisions shows 待评审(n) and gates on
    # the review meeting; a level with no blocks falls back to frontmatter (axis-2).
    led = ledger_status(parse_ledger(card_dir)[0]) \
        if os.path.exists(p("decisions.md")) else {}

    def pending(level):
        lv = led.get(level)
        return len(lv["pending"]) if lv else 0

    def step(label, state, gate=None):
        nonlocal nxt
        steps.append(f"{label}:{state}")
        if nxt is None and gate:
            nxt = gate

    rs = req.get("status", "?" if not req else "drafting")
    n = pending("requirement")
    step("需求", rs + (f"·待评审({n})" if n else ""),
         f"GATE: 需求 {n} 决策待批" if n else (None if rs == "confirmed" else "GATE: 需求待 confirm"))
    if not des:
        step("设计", "—", "next: design")
    else:
        ds = des.get("status", "drafting")
        n = pending("design")
        step("设计", ds + (f"·待评审({n})" if n else ""),
             f"GATE: 设计 {n} 决策待批" if n else
             (None if ds in ("frozen", "approved") else "GATE: 设计待 approve/freeze"))
    n = pending("detail")
    step("详设", (det.get("status", "✓") if det else "—") + (f"·待评审({n})" if n else ""),
         f"GATE: 详设 {n} 决策待批" if n else None)  # optional phase: absence never gates
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
    step("测试", ts, None if ts == "passing" else "next: 测试 close-out")
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
                # 010: active ledger rows for the drawer ([] = no ledger); rides /api/board as-is
                "decisions": card_decisions(c),
                # 017 D1: governance mode (two-level cascade); board tile + drawer render it
                "governance": card_mode(c),
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

# `001 的 R34` names another card's item; harvesting it as a local R-id made the trace
# matrix invent rows (R31–R36 on a card whose own items stop at R22) and flag them
# `not-in-需求条目`. Strip cross-card references before any local-id harvest.
XCARD_REF = re.compile(r"\d{3}\s*的\s*[*`~]{0,2}R\d+")


def _strip_xcard(text):
    return XCARD_REF.sub("⟨xcard⟩", text)


RETIRED_ITEM = re.compile(r"\s*~*\s*retired\b", re.I)


def _read(path):
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        return ""


def _section(text, title_pat, level=2):
    """Body of the first heading at `level` (## or ###) matching title_pat, else "".
    Terminated by the next same-or-higher heading — for level=3 that regex is `^###?\\s`;
    a `^###\\s`-only terminator would swallow the following `##` section when the
    sub-section is last."""
    head = r"^%s\s+(.+)$" % ("#" * level)
    stop = r"^#{2,%d}\s" % level
    for m in re.finditer(head, text, re.M):
        if re.search(title_pat, m.group(1)):
            start = m.end()
            nxt = re.search(stop, text[start:], re.M)
            return text[start:start + nxt.start()] if nxt else text[start:]
    return ""


def trace_requirement(card):
    """R-id → statement, from the 需求条目 table (first cell carries the id).

    The id cell may be wrapped in markdown emphasis or strikethrough — `**R21**`
    (a newly added item) and `~~R16~~` (a retired row) are both id cells; missing
    them made the trace matrix report a false `not-in-需求条目` for every such row.
    """
    items = {}
    for m in re.finditer(r"^\|\s*(?:\*\*|~~|\[)?\s*(R\d+)[^|]*\|([^|]*)\|",
                         _read(os.path.join(card, "requirement.md")), re.M):
        items.setdefault(m.group(1), re.sub(r"\*\*", "", m.group(2)).strip())
    return items


def _rows_by_rid(sect):
    out = {}
    for line in sect.splitlines():
        if not line.lstrip().startswith("|") or set(line.strip()) <= set("|-: "):
            continue
        for rid in RID.findall(_strip_xcard(line)):
            out.setdefault("R" + rid, re.sub(r"\s*\|\s*", " · ", line).strip(" ·"))
    return out


def trace_design(card):
    """R-id → its How-it-meets row (design home) and its 验证策略 row."""
    text = _read(os.path.join(card, "design.md"))
    return (_rows_by_rid(_section(text, r"How it meets|如何满足")),
            _rows_by_rid(_section(text, r"验证策略|Verification strategy")))


def trace_parts(card):
    """(parts, {R-id: [part, …]}) from design.md's Decomposition/Parts table.
    Header-keyed (parse_tasks style); the `R` column doubles as the new-format
    marker — a table without it (legacy, e.g. a pre-015 card) parses as un-split."""
    sect = _section(_read(os.path.join(card, "design.md")),
                    r"Decomposition\s*/\s*Parts", level=3)
    lines = [ln for ln in sect.splitlines() if ln.lstrip().startswith("|")]
    if len(lines) < 2:
        return [], {}
    header = [c.strip().lower() for c in lines[0].strip().strip("|").split("|")]
    part_i = next((i for i, h in enumerate(header) if "part" in h), None)
    r_i = next((i for i, h in enumerate(header) if h == "r"), None)
    if part_i is None or r_i is None:
        return [], {}
    parts, r2p = [], {}
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) <= max(part_i, r_i) or set(cells[part_i]) <= set("-: "):
            continue
        name = norm_part(cells[part_i])
        if not name:
            continue
        if name not in parts:
            parts.append(name)
        for rid in RID.findall(cells[r_i]):
            lst = r2p.setdefault("R" + rid, [])
            if name not in lst:
                lst.append(name)
    return parts, r2p


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
        part = re.search(r"\*\*Part:?\*\*[::]?\s*(.+)", block)
        boxes = re.findall(r"^\s*-\s*\[([ x!])\]", block, re.M)
        tasks[m.group(1)] = {
            "title": m.group(2).strip(),
            "rids": ["R" + r for r in RID.findall(imp.group(1))] if imp else [],
            "part": norm_part(part.group(1)) if part else "",
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
    """Single-source trace derivation (007): per-R rows consumed by the CLI text
    renderer, `--trace --json`, and the viewer's /api/trace.

    Per-task / per-R `commit_state` is four-valued: strict / loose / none (checked,
    no hit) / unchecked (no repo anchor — never counted as a gap). Commit lists are
    complete; display truncation belongs to renderers.
    """
    import datetime
    reqs = trace_requirement(card_dir)
    home, verify = trace_design(card_dir)
    parts, r2p = trace_parts(card_dir)
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
                          "part": t["part"],
                          "commits": lines, "commit_state": commit_state}

    by_r = {}
    for tid, t in tasks.items():
        for r in t["rids"]:
            by_r.setdefault(r, []).append(tid)
    all_r = sorted(set(reqs) | set(home) | set(by_r) | set(cov), key=lambda r: int(r[1:]))

    dstates = {b["id"]: b["state"] for b in parse_ledger(card_dir)[0]
               if b["state"] in ACTIVE_STATES}   # 010: per-R ledger state on trace rows
    rows = []
    for r in all_r:
        tids = by_r.get(r, [])
        states = [task_rows[t]["commit_state"] for t in tids]
        commit_state = ("unchecked" if not repo else
                        "strict" if "strict" in states else
                        "loose" if "loose" in states else "none")
        # A retired item has no design home / task / test by construction — flagging it
        # as a gap points the gate reader at rows that are already resolved.
        flags = [] if RETIRED_ITEM.match(reqs.get(r, "")) else \
                [w for cond, w in ((r not in reqs, "not-in-需求条目"),
                                  (r not in home, "no-design-home"),
                                  (r not in by_r, "no-task"),
                                  (r not in cov, "no-test-coverage")) if cond]
        rows.append({"rid": r, "text": reqs.get(r, ""),
                     "design": home.get(r, ""), "verify": verify.get(r, ""),
                     "test": cov.get(r, ""), "tasks": [task_rows[t] for t in tids],
                     "parts": r2p.get(r, []),
                     "dstate": dstates.get(r, ""), "flags": flags,
                     "present": {"design": r in home, "verify": r in verify,
                                 "task": bool(tids), "test": r in cov,
                                 "commit": commit_state}})
    orphans = [t for t, v in sorted(tasks.items(), key=lambda kv: int(kv[0]))
               if not v["rids"]]
    return {"card": f"{project}/{os.path.basename(card_dir)}", "repo": repo or "",
            "repo_anchor": bool(repo), "parts": parts,
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "rows": rows, "orphans": orphans, "error": ""}


def render_trace(project, card_dir):
    d = trace_data(project, card_dir)
    print(f"🔗 {d['card']}" + (f"  repo: {d['repo']}" if d["repo"] else ""))
    W = 100

    def prow(row, multi=False):
        flags = ["⚠ " + f for f in row["flags"]]
        mark = " ↔" if multi else ""
        print(f"{row['rid']}{mark}  {row['text'][:64]}" + ("  " + " ".join(flags) if flags else ""))
        if row["design"]:
            print(f"    design : {row['design'][:W]}")
        if row["verify"]:
            print(f"    verify : {row['verify'][:W]}")
        for t in row["tasks"]:
            print(f"    task   : T{t['tid']} [{t['state']}] {t['title'][:64]}")
            label = "commit" if t["commit_state"] == "strict" else "commit?"  # loose = bare-T cross-card risk
            for c in t["commits"][:6]:
                print(f"      {label}: {c[:W]}")

    if d["parts"]:
        groups = [(p, [r for r in d["rows"] if p in r["parts"]]) for p in d["parts"]]
        rest = [r for r in d["rows"] if not r["parts"]]
        if rest:
            groups.append(("—", rest))
        for pname, rows in groups:
            print(f"▣ Part: {pname}")
            for row in rows:
                prow(row, multi=len(row["parts"]) > 1)
    else:
        for row in d["rows"]:
            prow(row)
    if d["orphans"]:
        print("—  tasks with no R-id (scaffolding?): " + ", ".join("T" + t for t in d["orphans"]))
    if not d["repo_anchor"]:
        print("(commits skipped — no git repo anchor: progress.md `repo:` or config projects path)")
    return 0


# ---- decision ledger (010): decisions.md parsing + --check (deterministic subset) ----
# Ledger contract: templates/decisions.md. Only block headers and designated fields are
# parsed; a prose mention of an id is never a reference. Cards without decisions.md keep
# the pre-ledger semantics untouched; a level with no blocks falls back to frontmatter
# (progressive adoption — both degradation axes, design 010).

LEDGER_HEAD = re.compile(
    r"^###\s+(R\d+|V\d+|S\d+|D\d+|ADR-\d{4}(?:\s+D\d+)?)\s+"
    r"\[(requirement|design|detail)\]\s+"
    r"(proposed|approved|superseded|retired)\s*$", re.M)
APPROVE_NOTE = re.compile(r"^-\s*approved:\s*\d{4}-\d{2}-\d{2}\s+gate\s+\S+", re.M)
ACTIVE_STATES = ("proposed", "approved")
LEDGER_ID = re.compile(r"\b(ADR-\d{4}\s+D\d+|ADR-\d{4}|R\d+|V\d+|S\d+|D\d+)\b")


def parse_ledger(card_dir):
    """decisions.md → (blocks, findings). Block: {id, level, state, deps, body}.
    A `###` line that doesn't parse as a block header is a bad-header finding."""
    text = _read(os.path.join(card_dir, "decisions.md"))
    if not text:
        return [], []
    findings = ["bad-header: " + m.group(0).strip()[:60]
                for m in re.finditer(r"^###\s.*$", text, re.M)
                if not LEDGER_HEAD.match(m.group(0))]
    blocks, heads = [], list(LEDGER_HEAD.finditer(text))
    for i, m in enumerate(heads):
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        dep = re.search(r"^-[ \t]*depends-on:[ \t]*(.+)$", body, re.M)
        blocks.append({"id": m.group(1), "level": m.group(2), "state": m.group(3),
                       "deps": [d.strip() for d in dep.group(1).split(",")
                                if d.strip() and d.strip() not in PLACEHOLDERS]
                       if dep else [],
                       "body": body})
    return blocks, findings


def ledger_status(blocks):
    """{level: {total(active), approved, pending[ids], superseded}} — the aggregation
    card_status folds into phase labels (T3)."""
    out = {}
    for b in blocks:
        lv = out.setdefault(b["level"],
                            {"total": 0, "approved": 0, "pending": [], "superseded": 0})
        if b["state"] not in ACTIVE_STATES:
            lv["superseded"] += 1
            continue
        lv["total"] += 1
        if b["state"] == "approved":
            lv["approved"] += 1
        else:
            lv["pending"].append(b["id"])
    return out


def _id_level(i):
    return ("requirement" if i.startswith("R") or i.startswith("V") else
            "detail" if i.startswith("S") else "design")


def card_decisions(card_dir):
    """Active ledger rows for display: [{id, level, state, text(陈述)}]. A dup-active id
    collapses to ONE `conflict` row — the display never picks a winner (ADR-0001 D3
    rejected last-wins); --check reports the dup for repair."""
    by_id = {}
    for b in parse_ledger(card_dir)[0]:
        if b["state"] not in ACTIVE_STATES:
            continue
        m = re.search(r"^-\s*陈述:\s*(.+)$", b["body"], re.M)
        by_id.setdefault(b["id"], []).append(
            {"id": b["id"], "level": b["level"], "state": b["state"],
             "text": m.group(1).strip() if m else ""})
    return [rs[0] if len(rs) == 1 else
            {"id": i, "level": rs[0]["level"], "state": "conflict", "text": ""}
            for i, rs in by_id.items()]


def _id_cells(text, title_pat, cell_picks):
    """Ledger ids from a table section, taken ONLY from the id-bearing cells (a prose
    mention in any other column is never a reference)."""
    refs = set()
    for line in _section(text, title_pat).splitlines():
        if not line.lstrip().startswith("|") or set(line.strip()) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        for pick in cell_picks:
            if -len(cells) <= pick < len(cells):
                refs |= {m.group(1)
                         for m in LEDGER_ID.finditer(_strip_xcard(cells[pick]))}
    return refs


def _referenced_ids(card_dir):
    """Designated-field references only: requirement 需求条目 id cells, design How-it-meets
    id cells + Parts-table R cells, detail 可追溯 详设项+R-id cells, plan Implements:,
    ledger depends-on lines."""
    refs = set(trace_requirement(card_dir))
    refs |= _id_cells(_read(os.path.join(card_dir, "design.md")),
                      r"How it meets|如何满足", (0,))
    refs |= set(trace_parts(card_dir)[1])
    refs |= _id_cells(_read(os.path.join(card_dir, "detail.md")), r"可追溯", (0, -1))
    for t in trace_plan(card_dir).values():
        refs |= set(t["rids"])
    for b in parse_ledger(card_dir)[0]:
        refs |= set(b["deps"])
    return refs


ADR_STATUS_MAP = {"proposed": "proposed", "accepted": "approved",
                  "superseded": "superseded", "deprecated": "retired"}

# (f) design.md required-section existence — the scripted slice of M3's Design-completeness.
# Only the unconditional template sections; conditional ones (验证策略 is M+-only, 存储足迹 is
# storage-only, diagrams allow an ASCII fallback) stay in the M3 judgment subset.
DESIGN_SECTIONS_CUTOFF = "2026-07-31"   # grandfather: earlier designs were written pre-rule
DESIGN_REQUIRED_SECTIONS = (
    ("思路", r"思路"),
    ("速览", r"速览"),
    ("How it meets the requirement", r"How it meets|如何满足"),
    ("影响面", r"影响面|impact surface"),
)


def check_design_sections(card_dir):
    """Missing-section findings for design.md; [] when absent or grandfathered."""
    path = os.path.join(card_dir, "design.md")
    if not os.path.exists(path):
        return []
    created = str(frontmatter(path).get("created", ""))
    if not created or created < DESIGN_SECTIONS_CUTOFF:
        return []
    heads = " | ".join(m.group(1) for m in
                       re.finditer(r"^##+\s+(.+)$", _read(path), re.M))
    return ["missing-section: design.md " + name
            for name, pat in DESIGN_REQUIRED_SECTIONS
            if not re.search(pat, heads, re.I)]


FACT_HEAD = re.compile(r"^###\s+(F\d+)\s+\[([^\]]+)\]\s*$", re.M)
# Scoped to the 来源 field: only how THIS fact was obtained can contradict its marker.
FACT_SOURCE = re.compile(r"^-\s*(?:来源|source)\s*[:：](.*?)(?=^-\s|\Z)", re.M | re.S)
# Self-attributed inference — flags regardless of any citation alongside it.
FACT_SELF_INFER = re.compile(r"由.{0,40}?推断|推断而来|据此推断|仍未实测|未实测|未做实测|untested")
# Weaker hedges: only a smell when the 来源 offers no positive evidence token.
FACT_HEDGE = re.compile(r"推断|未验证|未经验证|猜测|inferred|assumed")
FACT_POSITIVE = re.compile(r"实测|实读|已核|复核|verified|measured|`[^`]+`|\[\[[^\]]+\]\]")


def check_fact_markers(card_dir):
    """(g) facts.md marker↔来源 integrity: a VERIFIED block whose own 来源 says the fact was
    inferred rather than checked — the mislabel that lets a citer trust an unverified premise.

    Scoped to 来源 and tolerant of the common correcting idiom (a VERIFIED block that says
    it supersedes an earlier 推断): a weak hedge is flagged only when 来源 carries no positive
    evidence token; self-attributed inference ("由 … 推断", "仍未实测") always flags.
    Superseded/retired blocks are exempt — their body documents the disproof.
    """
    text = _read(os.path.join(card_dir, "facts.md"))
    if not text:
        return []
    findings, heads = [], list(FACT_HEAD.finditer(text))
    for i, m in enumerate(heads):
        marker = m.group(2)
        if "VERIFIED" not in marker.upper() or re.search(r"superseded|retired", marker, re.I):
            continue
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        src = FACT_SOURCE.search(body)
        if not src:
            continue
        src = src.group(1)
        hit = FACT_SELF_INFER.search(src)
        if not hit and not FACT_POSITIVE.search(src):
            hit = FACT_HEDGE.search(src)
        if hit:
            findings.append("fact-marker: %s marked [%s] but 来源 says '%s'"
                            % (m.group(1), marker, hit.group(0).strip()))
    return findings


def check_part_consistency(card_dir):
    """(h) part consistency: with a new-format Parts table (R column present), every
    non-empty plan `Part:` value must name a canonical part; legacy tables (no R
    column) and un-split cards skip — 006-style plan-only Part grouping stays legal."""
    parts, _ = trace_parts(card_dir)
    if not parts:
        return []
    return ["part-mismatch: T%s Part '%s' not in design Parts (%s)"
            % (tid, t["part"], ", ".join(parts))
            for tid, t in sorted(trace_plan(card_dir).items(), key=lambda kv: int(kv[0]))
            if t["part"] and t["part"] not in parts]


# (i) governance mode — 017 D1/S1/S2: two-level cascade (frontmatter field first; no
# field → the decisions.md-existence axis, i.e. "legacy", pre-017 behavior untouched).
# The field lives only in requirement.md frontmatter; invalid values behave as legacy
# downstream and are flagged by (i1).
GOVERNANCE_CUTOFF = "2026-08-10"     # cards created on/after must declare the field
GOVERNANCE_VALUES = ("ledger", "doc-gate")


def card_mode(card_dir):
    """'ledger' | 'doc-gate' | 'legacy' (existence axis rules) | 'invalid'."""
    gov = frontmatter(os.path.join(card_dir, "requirement.md")).get("governance", "")
    if not gov:
        return "legacy"
    return gov if gov in GOVERNANCE_VALUES else "invalid"


def check_governance(card_dir):
    """The four unconditional governance checks (i1)–(i4); report-only."""
    mode = card_mode(card_dir)
    fm = frontmatter(os.path.join(card_dir, "requirement.md"))
    has_ledger = os.path.exists(os.path.join(card_dir, "decisions.md"))
    findings = []
    if mode == "invalid":
        findings.append("bad-governance-value: %r" % fm.get("governance"))
    created = str(fm.get("created", ""))
    if mode == "legacy" and created and created >= GOVERNANCE_CUTOFF:
        findings.append("missing-governance-field")
    if mode == "ledger" and fm.get("status") == "confirmed" and not has_ledger:
        findings.append("ledger-mode-no-ledger")
    if mode == "doc-gate" and has_ledger:
        findings.append("doc-gate-has-ledger")
    return findings


def check_card(project, card_dir):
    """The deterministic checks: ledger (a)–(e) + design sections (f) + fact markers (g)
    + part consistency (h) + governance mode (i); semantic contradiction stays M3
    judgment. No decisions.md → ledger checks skipped (old-card semantics, never
    flagged); (f)/(g)/(h)/(i) run regardless of the ledger."""
    section_findings = (check_design_sections(card_dir) + check_fact_markers(card_dir)
                        + check_part_consistency(card_dir) + check_governance(card_dir))
    if not os.path.exists(os.path.join(card_dir, "decisions.md")):
        return section_findings
    blocks, findings = parse_ledger(card_dir)
    findings = section_findings + findings
    by_id = {}
    for b in blocks:
        by_id.setdefault(b["id"], []).append(b)
    active = {}
    for i, bs in by_id.items():
        act = [b for b in bs if b["state"] in ACTIVE_STATES]
        if len(act) > 1:
            findings.append("dup-active: " + i)                              # (e)
        active[i] = act[-1] if act else None
    levels_present = {b["level"] for b in blocks}

    for ref in sorted(_referenced_ids(card_dir)):                            # (a)
        if _id_level(ref) not in levels_present:
            continue  # level not ledger-managed yet (degradation axis 2)
        if ref not in by_id:
            findings.append("dangling-id: " + ref)
        elif active[ref] is None:
            findings.append("superseded-ref: " + ref)

    def all_approved(level):
        act = [b for b in blocks if b["level"] == level and b["state"] in ACTIVE_STATES]
        return bool(act) and all(b["state"] == "approved" for b in act)

    for level, doc, done_words in (("requirement", "requirement.md", ("confirmed",)),
                                   # "approved" kept for pre-011 cards; template enum is drafting|frozen|superseded
                                   ("design", "design.md", ("frozen", "approved")),
                                   ("detail", "detail.md", ("baseline",))):    # (b)
        path = os.path.join(card_dir, doc)
        if level not in levels_present or not os.path.exists(path):
            continue
        status = frontmatter(path).get("status", "")
        if (status in done_words) != all_approved(level):
            findings.append(f"status-mismatch: {doc} '{status}' vs ledger {level}")

    for f in sorted(glob.glob(os.path.join(card_dir, "adr", "*.md"))):       # (b) ADR 行
        m = re.search(r"^Status:\s*(\w+)", _read(f), re.M)
        adr_id = "ADR-" + os.path.basename(f)[:4]
        act = [b for b in blocks if (b["id"] == adr_id or b["id"].startswith(adr_id + " "))
               and b["state"] in ACTIVE_STATES]
        if not m or not act:
            continue
        word = ADR_STATUS_MAP.get(m.group(1).lower())
        if word == "approved" and any(b["state"] == "proposed" for b in act):
            findings.append(f"status-mismatch: {os.path.basename(f)} accepted vs pending rows")
        elif word == "proposed" and all(b["state"] == "approved" for b in act):
            findings.append(f"status-mismatch: {os.path.basename(f)} proposed vs approved rows")
        elif word in ("superseded", "retired"):   # file claims dead, rows still active
            findings.append(f"status-mismatch: {os.path.basename(f)} {m.group(1)} vs active rows")

    graph = {i: (active[i]["deps"] if active[i] else []) for i in by_id}     # (c)
    color = {}

    def dfs(n, stack):
        color[n] = 1
        for d in graph.get(n, []):
            if color.get(d) == 1:
                findings.append("dep-cycle: " + " → ".join(stack + [d]))
            elif color.get(d) is None and d in graph:
                dfs(d, stack + [d])
        color[n] = 2

    for n in graph:
        if color.get(n) is None:
            dfs(n, [n])

    for b in blocks:                                                          # (d)
        if b["state"] == "approved" and not APPROVE_NOTE.search(b["body"]):
            findings.append("bad-approve-note: " + b["id"])
    return findings


def run_check(root, arg):
    """--check CLI: print findings, exit 1 when any. Catches its own exceptions —
    the top-level never-crash wrapper clamps exceptions (only) to exit 0, so an
    unhandled error here would silently pass the check."""
    try:
        project, card_dir = resolve_card(root, arg)
        findings = check_card(project, card_dir)
    except SystemExit:
        raise
    except Exception as e:
        findings = ["check-error: %s" % e]
    for f in findings:
        print("⚠ " + f)
    if findings:
        return 1
    print("check: ok")
    return 0


def main():
    args, want, root_arg, as_json, trace_arg, i = sys.argv[1:], [], None, False, None, 0
    check_arg = None
    while i < len(args):
        a = args[i]
        if a in ("--root", "--trace", "--check") and i + 1 < len(args):
            if a == "--root":
                root_arg = args[i + 1]
            elif a == "--trace":
                trace_arg = args[i + 1]
            else:
                check_arg = args[i + 1]
            i += 2
            continue
        if a.startswith("--root="):
            root_arg = a.split("=", 1)[1]
        elif a.startswith("--trace="):
            trace_arg = a.split("=", 1)[1]
        elif a.startswith("--check="):
            check_arg = a.split("=", 1)[1]
        elif a == "--json":
            as_json = True
        elif not a.startswith("--"):
            want.append(a)
        i += 1
    root = os.path.expanduser(root_arg) if root_arg else dev_root()
    if check_arg:
        return run_check(root, check_arg)
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
