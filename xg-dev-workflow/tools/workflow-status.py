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
  workflow-status.py --check <project>/<card>   # deterministic checks (a)-(t)+(x)(y), card scope
  workflow-status.py --check <project>          # project scope: (o)(u)(v)(w) + every card
                                       # exit 1 on findings; skips print but never gate
                                       # (M3 deterministic subset; bodies in workflow-checks.py)
  workflow-status.py --digest <project>/<card>  # gate-ask digest skeleton from the pending
                                       # block set (doc-native cards, 026 HLD-9); chat-use
                                       # stdout, never a file
  workflow-status.py --manifest        # check-family manifest (026 HLD-11) — registry meta
                                       # rendered human-readable; SoT stays in code
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
        # markup-tolerant state parse (021 G6, norm_part's rule): **paused** reads as
        # paused everywhere downstream (canonical match, effective_next, viewer)
        rows[m.group(1)] = {"phase": m.group(2).strip(),
                            "state": re.sub(r"[*`]", "", m.group(3)).strip(),
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

# Closed vocabularies whose template comments are grep-checked mirrors (021 G6 — the
# closed list lives ONLY here; templates/index.md and templates/test.md restate them,
# edited in the same batch as any change here). PHASE_CANON's consumer is that mirror
# grep itself (no runtime check keys on Phase yet); TEST_STATUS_DONE_OK is the (w)
# done-gate subset of TEST_STATUS_CANON.
# Phase column: prefix-matched — a suffix annotation (`测试 (XS/S)`) is free text.
PHASE_CANON = ("需求", "设计", "详设", "实现", "测试", "评审")
TEST_STATUS_CANON = ("planned", "passing", "failing", "described")
TEST_STATUS_DONE_OK = ("passing", "described")


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
                # 020 D6: 应有载体×存在性 — the learn coverage-table skeleton; additive
                "carriers": card_carriers(c),
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
RID = re.compile(r"\b(?:Req-|R)(\d+)\b")   # dual notation: R<n> legacy · Req-<n> doc-native


def _rid_form(text):
    """The card's R-id display form inferred from where the match came from —
    Req-<n> when the token was the doc-native form, else R<n>."""
    return "Req-" if "Req-" in text else "R"


def _expand_rid_ranges(cell):
    """`Req-1..Req-23` / `R1..R11` range notation appends its expansion (HLD-1).
    Deliberately separate from block_parse.expand_ranges: this one also speaks the
    legacy bare-R grammar, which is outside the block domain's prefix set."""
    out = cell
    for m in re.finditer(r"(Req-|R)(\d+)\.\.(?:Req-|R)(\d+)", cell):
        out += " " + " ".join("%s%d" % (m.group(1), n)
                              for n in range(int(m.group(2)), int(m.group(3)) + 1))
    return out


def rid_key(rid):
    """Numeric sort key over both notations."""
    return int(re.search(r"(\d+)$", rid).group(1))

# `NNN 的 R<n>` names another card's item; harvesting it as a local R-id made the
# trace matrix invent rows and flag them `not-in-需求条目`. Same for the shorthand
# `其 R<n>` (antecedent card named earlier in the sentence) and `M<n> R<n>` (another
# mechanism's item). Strip cross-context references before any local-id harvest.
XCARD_REF = re.compile(
    r"\d{3}\s*的\s*[*`~]{0,2}(?:Req-|R)\d+"      # NNN 的 R<n>
    r"|\b\d{3}\s+[*`~]{0,2}(?:Req-|R)\d+"        # NNN R<n> shorthand (e.g. 024 R6)
    r"|其\s*[*`~]{0,2}(?:Req-|R)\d+|\bM\d+\s+(?:Req-|R)\d+")


def _strip_xcard(text):
    return XCARD_REF.sub("⟨xcard⟩", text)


# Retirement accounting (M2 撤销 keeps the id and marks the row; templates/requirement.md
# pins the recognized forms): the id cell struck (`~~R9~~`) or itself carrying `retired`,
# or the first content cell beginning `retired …` / `~~…~~ retired …`. Deliberately
# cell-scoped — a live row merely mentioning "retired" mid-prose stays a reference, so
# superseded-ref/dangling-id still fire on live rows citing dead ids.
RETIRE_ID = re.compile(r"~~|retired\b", re.I)
# struck span(s) + optional separator punctuation (— · : …), then `retired`; callers
# strip `**` first. Must anchor at cell start — mid-prose "retired" is not accounting.
RETIRE_MARK = re.compile(r"^\s*(?:~~[^~]*~~[^\w~]*)*retired\b", re.I)


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
    for m in re.finditer(r"^\|\s*(?:\*\*|~~|\[)?\s*(Req-\d+|R\d+)[^|]*\|([^|]*)\|",
                         _read(os.path.join(card, "requirement.md")), re.M):
        items.setdefault(m.group(1), re.sub(r"\*\*", "", m.group(2)).strip())
    return items


def _retired_req_ids(card_dir):
    """R-ids whose 需求条目 row is retirement accounting (RETIRE_ID / RETIRE_MARK)."""
    out = set()
    for m in re.finditer(r"^\|([^|\n]*)\|([^|\n]*)\|",
                         _read(os.path.join(card_dir, "requirement.md")), re.M):
        idc, stmt = m.group(1), m.group(2)
        rid = re.search(r"R\d+", _strip_xcard(idc))
        if rid and (RETIRE_ID.search(idc) or RETIRE_MARK.match(stmt.replace("**", ""))):
            out.add(rid.group(0))
    return out


def _rows_by_rid(sect):
    """R-id → its carrying line in the section. Table rows and prose lines both
    count — the doc-native How-it-meets Part B/C mapping is prose with [Req-n]
    arrows, as much a design home as a table row (ranges expanded)."""
    out = {}
    for line in sect.splitlines():
        if set(line.strip()) <= set("|-: ") or line.startswith("#"):
            continue
        for m in RID.finditer(_expand_rid_ranges(_strip_xcard(line))):
            out.setdefault(m.group(0), re.sub(r"\s*\|\s*", " · ", line).strip(" ·"))
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
        for m in RID.finditer(_expand_rid_ranges(cells[r_i])):
            lst = r2p.setdefault(m.group(0), [])
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
        # continuation lines (indented) belong to the field — a wrapped Implements
        # list must not silently drop its tail rids
        imp = re.search(r"\*\*Implements:?\*\*[::]?\s*(.+(?:\n[ \t]+\S[^\n]*)*)", block)
        part = re.search(r"\*\*Part:?\*\*[::]?\s*(.+)", block)
        boxes = re.findall(r"^\s*-\s*\[([ x!])\]", block, re.M)
        tasks[m.group(1)] = {
            "title": m.group(2).strip(),
            "rids": [m.group(0) for m in RID.finditer(imp.group(1))] if imp else [],
            "part": norm_part(part.group(1)) if part else "",
            "state": ("done" if boxes and all(b == "x" for b in boxes)
                      else "failed" if "!" in boxes else "todo" if boxes else "?"),
        }
    return tasks


def trace_test(card):
    """R-id → covered-by, from test.md coverage rows (first cell cites the id; last
    cell = test). Doc-native cards key coverage by Effect with the R-ids in a
    verifies column — there every cell is scanned (ranges expanded)."""
    cov = {}
    docnative = card_mode(card) in DOC_NATIVE_MODES
    for line in _read(os.path.join(card, "test.md")).splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        scan = " ".join(cells[:-1]) if docnative else cells[0]
        for m in RID.finditer(_expand_rid_ranges(_strip_xcard(scan))):
            cov.setdefault(m.group(0), cells[-1])
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
    all_r = sorted(set(reqs) | set(home) | set(by_r) | set(cov), key=rid_key)

    dstates = {b["id"]: b["state"] for b in parse_ledger(card_dir)[0]
               if b["state"] in ACTIVE_STATES}   # 010: per-R ledger state on trace rows
    retired = _retired_req_ids(card_dir)
    rows = []
    for r in all_r:
        tids = by_r.get(r, [])
        states = [task_rows[t]["commit_state"] for t in tids]
        commit_state = ("unchecked" if not repo else
                        "strict" if "strict" in states else
                        "loose" if "loose" in states else "none")
        # A retired item has no design home / task / test by construction — flagging it
        # as a gap points the gate reader at rows that are already resolved.
        flags = [] if r in retired else \
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
ACTIVE_STATES = ("proposed", "approved")


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


# (i) governance mode — two-level cascade: frontmatter field first; no field → the
# decisions.md-existence axis, i.e. "legacy", pre-existing behavior untouched. The field
# lives only in requirement.md frontmatter; invalid values behave as legacy downstream
# and are flagged by check_governance (workflow-checks.py).
# "doc-native-pilot": card 026's self-hosted trial mode — decisions live in the phase docs,
# no decisions.md/facts.md (mode-specific checks treat it as non-ledger; full semantics land
# via card 026, until then its cards are guarded by their card-local crosscheck).
GOVERNANCE_VALUES = ("ledger", "doc-gate", "doc-native-pilot", "doc-native")


def card_mode(card_dir):
    """'ledger' | 'doc-gate' | 'legacy' (existence axis rules) | 'invalid'."""
    gov = frontmatter(os.path.join(card_dir, "requirement.md")).get("governance", "")
    if not gov:
        return "legacy"
    return gov if gov in GOVERNANCE_VALUES else "invalid"


# 021 G7/L2-2: SKILL.md「Layout」's project-root half, same single-mirror-home discipline
# as CARD_CARRIERS below (a Layout change edits both tuples in one batch). Dotfiles are
# OS artifacts, not workflow strays. Consumed by the (v) root-strays check.
PROJECT_ROOT_FILES = ("index.md", "roadmap.md")
PROJECT_ROOT_DIRS = ("investigations", "reviews", "notes", "legacy")

# 020 D6: machine-readable mirror of SKILL.md「Layout」's card-dir listing, in Layout order.
# The closed carrier-list mapping lives ONLY here — a Layout change edits this tuple in the
# same batch (invariant 6(a)); step files and templates never copy it.
# modes: "" = every mode; else the space-separated carrier-mode keys it belongs to
# (ledger / doc-gate / doc-native — doc-native covers the pilot value too, 026 HLD-13/14).
CARD_CARRIERS = (                     # (name, kind, modes)
    ("requirement.md", "file", ""),
    ("decisions.md", "file", "ledger"),
    ("facts.md", "file", "ledger doc-native"),
    ("design.md", "file", ""),
    ("adr/", "dir", ""),
    ("detail.md", "file", ""),
    ("plan.md", "file", ""),
    ("progress.md", "file", ""),
    ("log.md", "file", ""),
    ("test.md", "file", ""),
    ("notes/grill-*.md", "glob", "doc-native"),
    ("notes/review-*.md", "glob", ""),
    ("notes/part-check-*.md", "glob", ""),
)


# The doc-native pair is deliberately re-declared in workflow-checks.py (L2 cannot
# import L1 at module load — it reads the live view at call time) and in
# commit-data-repos.py (standalone by design); this tuple is the L1 original.
DOC_NATIVE_MODES = ("doc-native-pilot", "doc-native")


def _carrier_mode_key(mode):
    """card_mode value → CARD_CARRIERS modes key (pilot folds into doc-native)."""
    return "doc-native" if mode in DOC_NATIVE_MODES else mode


def _carrier_exists(card_dir, name, kind):
    path = os.path.join(card_dir, name)
    if kind == "dir":
        return os.path.isdir(path)
    if kind == "glob":
        return bool(glob.glob(path))
    return os.path.isfile(path)


def _enumerate_actual(card_dir):
    """Full enumeration for legacy/invalid modes: every actual .md carrier (adr/
    contents ride the dir row; the two notes globs keep family granularity).
    Callers drop names their mode already lists."""
    extras = []
    for dirpath, _dirnames, filenames in os.walk(card_dir):
        rel_dir = os.path.relpath(dirpath, card_dir)
        if rel_dir == "adr" or rel_dir.startswith("adr" + os.sep):
            continue
        for f in sorted(filenames):
            if not f.endswith(".md"):
                continue
            # family-glob exclusion is single-level only — glob.glob on the family row
            # doesn't cross "/", so a nested notes/review-X/y.md must enumerate here
            if rel_dir == "notes" and (fnmatch.fnmatch(f, "review-*.md") or
                                       fnmatch.fnmatch(f, "part-check-*.md")):
                continue
            rel = f if rel_dir == "." else os.path.join(rel_dir, f).replace(os.sep, "/")
            extras.append((rel, "file"))
    return sorted(extras)


def _nonmd_dir_rows(card_dir):
    """notes/ non-.md artifacts, one row per directory (存在性 + 指针 = the dir path);
    discovery rows — never part of an expected set."""
    rows = []
    notes = os.path.join(card_dir, "notes")
    for dirpath, _dirnames, filenames in os.walk(notes):
        if any(not f.endswith(".md") for f in filenames):
            rel = os.path.relpath(dirpath, card_dir).replace(os.sep, "/")
            rows.append((rel + "/", "nonmd-dir"))
    return sorted(rows)


def card_carriers(card_dir):
    """020 D6: 应有载体 × 存在性 — the `learn` coverage-table skeleton.
    ledger/doc-gate → that mode's closed list + notes/*.md discovery (Layout's notes/
    line; expected=False); legacy → existence-axis inferred list (decisions.md present
    → ledger list, absent → doc-gate list) ∪ full enumeration, both markers kept;
    invalid → full enumeration only (governance="invalid" is the warning signal
    downstream — never treated as "no marker"). Purely additive --json field; stable
    order = expected rows in Layout order (when a set exists), discovery extras sorted
    after them, non-md dir rows last."""
    mode = card_mode(card_dir)
    if mode in GOVERNANCE_VALUES:
        mode_key = _carrier_mode_key(mode)
    elif mode == "legacy":
        mode_key = "ledger" if os.path.exists(os.path.join(card_dir, "decisions.md")) \
            else "doc-gate"
    else:                                          # invalid: no expected set
        mode_key = None
    entries = []
    if mode_key is not None:
        for name, kind, modes in CARD_CARRIERS:
            if modes and mode_key not in modes.split():
                continue
            entries.append({"name": name, "kind": kind, "expected": True,
                            "exists": _carrier_exists(card_dir, name, kind)})
    if mode in GOVERNANCE_VALUES:
        # closed-list modes still surface actual notes/*.md (top level) as discovery —
        # grill logs etc. are real carriers the learn mining face must see (Layout notes/)
        listed = {e["name"] for e in entries}
        family_globs = [n[len("notes/"):] for n in listed if n.startswith("notes/") and "*" in n]
        for f in sorted(glob.glob(os.path.join(card_dir, "notes", "*.md"))):
            base = os.path.basename(f)
            if fnmatch.fnmatch(base, "review-*.md") or \
               fnmatch.fnmatch(base, "part-check-*.md") or \
               any(fnmatch.fnmatch(base, g) for g in family_globs):
                continue
            if "notes/" + base not in listed:
                entries.append({"name": "notes/" + base, "kind": "file",
                                "expected": False, "exists": True})
    if mode in ("legacy", "invalid"):
        listed = {e["name"] for e in entries}
        for name, kind in _enumerate_actual(card_dir):
            if name not in listed:
                entries.append({"name": name, "kind": kind,
                                "expected": False, "exists": True})
        if mode == "invalid":
            listed = {e["name"] for e in entries}
            for name, kind, _ in CARD_CARRIERS:
                if name not in listed and _carrier_exists(card_dir, name, kind):
                    entries.append({"name": name, "kind": kind,
                                    "expected": False, "exists": True})
    for name, kind in _nonmd_dir_rows(card_dir):
        entries.append({"name": name, "kind": kind, "expected": False, "exists": True})
    return entries


# ---- doc-native blocks (026): generated views over tools/block_parse.py ----
_BLOCK_PARSE = None


def _block_parse():
    """Lazy-load block_parse.py (same dir) — the doc-native block grammar (026)."""
    global _BLOCK_PARSE
    if _BLOCK_PARSE is None:
        try:
            import block_parse as mod
        except ImportError:
            import importlib.util
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "block_parse.py")
            spec = importlib.util.spec_from_file_location("block_parse", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        _BLOCK_PARSE = mod
    return _BLOCK_PARSE


INDEX_BEGIN = ("<!-- index:begin — generated by notes/crosscheck.py"
               " --write-index; do not hand-edit -->")
INDEX_END = "<!-- index:end -->"


def render_index(blocks, scope="requirement"):
    """Doc-native generated index (026 LLD-6): blocks (id→Block mapping or
    list) → the 条目节首 index table between the index markers. The default
    scope filters to requirement.md blocks and stays byte-identical to the
    crosscheck (c7) generator output (marker text still names crosscheck until
    its retirement re-homes generation — manifest 记账)."""
    items = blocks.values() if hasattr(blocks, "values") else list(blocks)
    rows = ["| id | 标题 | state |", "|---|---|---|"]
    for b in items:
        if scope and b.get("doc") and b["doc"] != scope + ".md":
            continue
        rows.append("| %s-%s | %s | %s |"
                    % (b["prefix"], b["num"], b["title"], b["state"]))
    return "\n".join([INDEX_BEGIN] + rows + [INDEX_END])


# ---- digest generator (026 HLD-9): gate-ask skeleton from the pending block set ----
DIGEST_MAX_LINES = 70
DIGEST_LEVELS = (("requirement.md", "requirement 级"), ("design.md", "design 级"),
                 ("detail.md", "detail 级"))
JUDGE_CARD = """- **问题**：（一句白话——禁编号回指/未定义行话承载主句）
- **选项与代价**：（各一行）
- **推荐及理由**：
- **不决的后果**：""".splitlines()


def _head_sentence(text, cap=80):
    """Verbatim prefix of a field for a one-line row — a quoted prefix, never a
    rewrite ([Req-28]); truncation is marked."""
    first = text.split("。", 1)[0].strip()
    return first[:cap] + ("…" if len(first) > cap or "。" in text else "")


def digest_text(card_dir, max_lines=DIGEST_MAX_LINES):
    """Gate-ask digest skeleton (026 HLD-9): the pending (proposed) block set,
    fetched through this generated-view layer, rendered into gate-digest.md's
    seven fixed sections. Mechanical content only — §2 rows (grouped
    requirement → design → detail, doc order within each; one line per block:
    id + title + the 陈述 head sentence, quoted verbatim), the fold rule (over
    the line budget, 照案 groups fold largest-first into a count + doc
    pointer; the §5 真判 four-line card slots never fold), and labeled slots
    for everything judgment-authored (self-check lines, tier promotion,
    stakes). The author promotes 真判/拿不准 items out of §2 at gate time."""
    blocks, findings = _block_parse().card_blocks(card_dir)
    pending = [b for b in blocks.values() if b["state"] == "proposed"]
    groups = []
    for doc, label in DIGEST_LEVELS:
        rows = ["- [%s-%s] %s — %s" % (b["prefix"], b["num"], b["title"],
                                       _head_sentence(b["fields"].get("陈述", "")))
                for b in pending if b["doc"] == doc]
        if rows:
            groups.append([doc, label, rows, False])
    out = ["# Gate digest — %s（pending %d 块%s）"
           % (os.path.basename(card_dir.rstrip("/")), len(pending),
              "；parse findings %d — 先修再问" % len(findings) if findings else ""),
           "",
           "## 1 · Grill / 自检状态",
           "-（出题人填：verifier · receipt 指针 · verdict，一行一条，≤10 行；末行 = 自检结论）",
           ""]
    body_budget = max_lines - len(out) - 24  # fixed tail sections below
    while sum(len(g[2]) for g in groups if not g[3]) + len(groups) > max(body_budget, 0) \
            and any(not g[3] for g in groups):
        big = max((g for g in groups if not g[3]), key=lambda g: len(g[2]))
        big[3] = True
    out.append("## 2 · Decision cards（依赖序：requirement → design → detail）")
    if not pending:
        out.append("-（无 pending 块——本 gate 为再批/收口形）")
    for doc, label, rows, folded in groups:
        out.append("### %s" % label)
        if folded:
            out.append("-（照案组折叠：%d 块 pending — 见 %s 各块原文；真判项仍须提升到 §5）"
                       % (len(rows), doc))
        else:
            out += rows
    out += ["",
            "## 3 · Phase attachments",
            "-（按 phase step 规定附：trace gap summary / 拆分审视 verdict / 枚举判据表……）",
            "",
            "## 4 · 假设 closure sweep",
            "-（载重 假设/推断 逐条：discharged / carried-with-a-home）",
            "",
            "## 5 · 待你判（真判/拿不准——由出题人从 §2 提升；每项四行自含，白话）"]
    out += JUDGE_CARD
    out += ["",
            "## 6 · Open questions",
            "-（留白项 + 所取默认）",
            "",
            "## 7 · Gate ask + receipts",
            "-（doc 路径 + receipts commit + 回 go 授权语——partial approve 合法性按卡模式）"]
    return "\n".join(out)


def render_manifest():
    """--manifest (026 HLD-11): the check-family registry rendered human-readable.
    SoT = the registry rows' meta in workflow-checks.py (CARD_CHECKS/PROJECT_CHECKS
    + EXTRA_MANIFEST); a registry row with no meta prints META-MISSING — the E5
    全行齐 enforcement. Ends with the net-count line (E5 净减判定)."""
    wc = _checks()
    lines = ["| 检查 | 字母 | 查什么 | 何时跑 | 机械/判断 | 依据 | 去向 |",
             "|---|---|---|---|---|---|---|"]
    for scope, entries in (("card", wc.CARD_CHECKS), ("project", wc.PROJECT_CHECKS)):
        for row in entries:
            cid = row[0]
            meta = row[2] if len(row) > 2 else None
            if not meta:
                lines.append("| %s (%s) | META-MISSING | | | | | |" % (cid, scope))
                continue
            lines.append("| %s | %s | %s | %s | %s | %s | %s |"
                         % (cid, meta["letter"], meta["what"], meta["when"],
                            meta["nature"], meta["basis"], meta["disp"]))
    lines.append("")
    lines.append("| 非注册项 | 去向 |")
    lines.append("|---|---|")
    for name, disp in wc.EXTRA_MANIFEST:
        lines.append("| %s | %s |" % (name, disp))
    retired = sum(1 for _n, d in wc.EXTRA_MANIFEST if d.startswith(("退役", "化解")))
    added = 3  # (ac)(ad)(ae) — the 026 additions
    lines.append("")
    lines.append("净减判定 (Eff-5): 退役/化解 %d > 新增 %d → %s"
                 % (retired, added, "净减成立" if retired > added else "未净减"))
    return "\n".join(lines)


# ---- deterministic checks: bodies live in workflow-checks.py (L2 of the split);
# these thin delegators keep the module surface (tests, run_check, monkeypatching)
# stable and inject the live L1 view so L2 never importlib-loads a second instance ----
_CHECKS = None


class _L1View:
    """Live attribute view over this module's globals — works whether or not the
    module was registered in sys.modules (tests/viewer load it via importlib)."""
    def __getattr__(self, name):
        try:
            return globals()[name]
        except KeyError:
            raise AttributeError(name) from None


_L1 = _L1View()


def _checks():
    """Lazy-load workflow-checks.py (same dir) — the check domain."""
    global _CHECKS
    if _CHECKS is None:
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "workflow-checks.py")
        spec = importlib.util.spec_from_file_location("workflow_checks", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CHECKS = mod
    return _CHECKS


def check_design_sections(card_dir):
    return _checks().check_design_sections(card_dir, _L1)


def check_fact_markers(card_dir):
    return _checks().check_fact_markers(card_dir, _L1)


def check_part_consistency(card_dir):
    return _checks().check_part_consistency(card_dir, _L1)


def check_governance(card_dir):
    return _checks().check_governance(card_dir, _L1)


def check_card(project, card_dir):
    return _checks().check_card(project, card_dir, _L1)


def run_check(root, arg, verbose_skips=False):
    """--check CLI, three-tier dispatch (021 design): an arg containing "/" → card
    scope via resolve_card; a bare name that is a project dir under root → project
    scope (project-level checks + every card — the full-sweep form), taking priority
    over resolve_card's card-dir/single-card branches; anything else → resolve_card
    legacy behavior. Prints findings (⚠), carrier skips (skip:, verbatim), then the
    exemption tier: by default one two-bucket counting line per gate-passed card
    (grandfathered · carrier-silent; not-yet-due never prints) plus one project-level
    line; --verbose-skips itemizes every exemption instead (no gate predicate).
    Exit 1 iff findings — a skip/exemption is visible but never gates. The ok tail's
    N counts printed skip lines (counting lines included), not exemption instances.
    Catches its own exceptions — the top-level never-crash wrapper clamps exceptions
    (only) to exit 0, so an unhandled error here would silently pass the check."""
    proj_scope = False
    try:
        if "/" not in arg.rstrip("/") and \
                os.path.isdir(os.path.join(root, arg.rstrip("/"))):
            name = arg.rstrip("/")
            proj_scope = True
            findings, skips, exemptions = _checks().check_project(
                name, os.path.join(root, name), _L1)
        else:
            project, card_dir = resolve_card(root, arg)
            findings, skips, exemptions = _checks().check_card_all(project, card_dir, _L1)
    except SystemExit:
        raise
    except Exception as e:
        findings, skips, exemptions = ["check-error: %s" % e], [], []
    for f in findings:
        print("⚠ " + f)
    printed = 0
    for s in skips:
        print("skip: " + s)
        printed += 1
    seen, uniq = set(), []
    for e in exemptions:   # (check, card, class, reason) dedup — per-item loop hits fold
        k = (e.check, e.card, e.cls, e.reason)
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    if verbose_skips:
        for e in uniq:
            pre = "%s: " % e.card if e.card and proj_scope else ""
            print("skip: %s%s: %s [%s]" % (pre, e.check, e.reason, e.cls))
            printed += 1
    else:
        counted = {}   # card "" = the project-level line
        for e in uniq:
            if e.cls == "not-yet-due" or not e.gated:
                continue
            n, m = counted.get(e.card, (0, 0))
            counted[e.card] = (n + 1, m) if e.cls == "grandfathered" else (n, m + 1)
        for card in sorted(counted):
            n, m = counted[card]
            buckets = " · ".join(filter(None, ["%d grandfathered" % n if n else "",
                                               "%d carrier-silent" % m if m else ""]))
            pre = "%s: " % card if card and proj_scope else "project " if not card else ""
            print("skip: %sexempt: %s (--verbose-skips)" % (pre, buckets))
            printed += 1
    if findings:
        return 1
    print("check: ok" + (" (%d skipped)" % printed if printed else ""))
    return 0


def main():
    args, want, root_arg, as_json, trace_arg, i = sys.argv[1:], [], None, False, None, 0
    check_arg, verbose_skips, digest_arg, manifest_flag = None, False, None, False
    while i < len(args):
        a = args[i]
        if a == "--manifest":
            manifest_flag = True
            i += 1
            continue
        if a in ("--root", "--trace", "--check", "--digest"):
            # a value is required and must not look like a flag — a misplaced switch
            # would otherwise be swallowed as the argument (R9)
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                print("workflow-status: %s requires a value" % a, file=sys.stderr)
                return 2
            if a == "--root":
                root_arg = args[i + 1]
            elif a == "--trace":
                trace_arg = args[i + 1]
            elif a == "--digest":
                digest_arg = args[i + 1]
            else:
                check_arg = args[i + 1]
            i += 2
            continue
        if a.startswith("--root="):
            root_arg = a.split("=", 1)[1]
        elif a.startswith("--trace="):
            trace_arg = a.split("=", 1)[1]
        elif a.startswith("--digest="):
            digest_arg = a.split("=", 1)[1]
        elif a.startswith("--check="):
            check_arg = a.split("=", 1)[1]
        elif a == "--json":
            as_json = True
        elif a == "--verbose-skips":
            verbose_skips = True
        elif a.startswith("--"):
            print("workflow-status: unknown flag %r" % a, file=sys.stderr)
            return 2
        else:
            want.append(a)
        i += 1
    root = os.path.expanduser(root_arg) if root_arg else dev_root()
    if manifest_flag:
        print(render_manifest())
        return 0
    if digest_arg:
        print(digest_text(resolve_card(root, digest_arg)[1]))
        return 0
    if check_arg:
        return run_check(root, check_arg, verbose_skips)
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
