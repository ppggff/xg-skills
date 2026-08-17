#!/usr/bin/env python3
"""workflow-checks.py — the deterministic check domain (L2 of the status/checks split).

Check implementations behind `workflow-status.py --check`: the ledger checks (a)-(e),
design required sections (f), fact markers (g), part consistency (h), governance
mode (i). workflow-status.py remains the parsing layer + CLI entry and lazy-loads
this module; every public function takes `ws` = a live view of the workflow-status
module (one-way dependency: checks read the parsing layer, never the reverse).

Lives only in xg-dev-workflow/tools/ (not a synced copy).
"""
import glob
import os
import re

# ---- (f) design.md required-section existence — the scripted slice of M3's
# Design-completeness. Only the unconditional template sections; conditional ones
# (验证策略 is M+-only, 存储足迹 is storage-only, diagrams allow an ASCII fallback)
# stay in the M3 judgment subset.
DESIGN_SECTIONS_CUTOFF = "2026-07-31"   # grandfather: earlier designs were written pre-rule
DESIGN_REQUIRED_SECTIONS = (
    ("思路", r"思路"),
    ("速览", r"速览"),
    ("How it meets the requirement", r"How it meets|如何满足"),
    ("影响面", r"影响面|impact surface"),
)


def check_design_sections(card_dir, ws):
    """Missing-section findings for design.md; [] when absent or grandfathered."""
    path = os.path.join(card_dir, "design.md")
    if not os.path.exists(path):
        return []
    created = str(ws.frontmatter(path).get("created", ""))
    if not created or created < DESIGN_SECTIONS_CUTOFF:
        return []
    heads = " | ".join(m.group(1) for m in
                       re.finditer(r"^##+\s+(.+)$", ws._read(path), re.M))
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


def check_fact_markers(card_dir, ws):
    """(g) facts.md marker↔来源 integrity: a VERIFIED block whose own 来源 says the fact was
    inferred rather than checked — the mislabel that lets a citer trust an unverified premise.

    Scoped to 来源 and tolerant of the common correcting idiom (a VERIFIED block that says
    it supersedes an earlier 推断): a weak hedge is flagged only when 来源 carries no positive
    evidence token; self-attributed inference ("由 … 推断", "仍未实测") always flags.
    Superseded/retired blocks are exempt — their body documents the disproof.
    """
    text = ws._read(os.path.join(card_dir, "facts.md"))
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


def check_part_consistency(card_dir, ws):
    """(h) part consistency: with a new-format Parts table (R column present), every
    non-empty plan `Part:` value must name a canonical part; legacy tables (no R
    column) and un-split cards skip — 006-style plan-only Part grouping stays legal."""
    parts, _ = ws.trace_parts(card_dir)
    if not parts:
        return []
    return ["part-mismatch: T%s Part '%s' not in design Parts (%s)"
            % (tid, t["part"], ", ".join(parts))
            for tid, t in sorted(ws.trace_plan(card_dir).items(), key=lambda kv: int(kv[0]))
            if t["part"] and t["part"] not in parts]


GOVERNANCE_CUTOFF = "2026-08-10"     # cards created on/after must declare the field


def check_governance(card_dir, ws):
    """The four unconditional governance checks (i1)–(i4); report-only."""
    mode = ws.card_mode(card_dir)
    fm = ws.frontmatter(os.path.join(card_dir, "requirement.md"))
    has_ledger = os.path.exists(os.path.join(card_dir, "decisions.md"))
    findings = []
    if mode == "invalid":
        findings.append("bad-governance-value: %r" % fm.get("governance"))
    created = str(fm.get("created", ""))
    # bare string compare needs the canonical zero-padded form; a malformed date skips (i2)
    if (mode == "legacy" and re.match(r"\d{4}-\d{2}-\d{2}", created)
            and created >= GOVERNANCE_CUTOFF):
        findings.append("missing-governance-field")
    # real cards annotate status inline ("confirmed # 2026-07-11 human confirm") — strip it
    status = fm.get("status", "").split("#")[0].strip()
    if mode == "ledger" and status == "confirmed" and not has_ledger:
        findings.append("ledger-mode-no-ledger")
    if mode == "doc-gate" and has_ledger:
        findings.append("doc-gate-has-ledger")
    return findings


# ---- ledger reference helpers (feed check_card's (a)) ----
LEDGER_ID = re.compile(r"\b(ADR-\d{4}\s+D\d+|ADR-\d{4}|R\d+|V\d+|S\d+|D\d+)\b")


def _id_level(i):
    return ("requirement" if i.startswith("R") or i.startswith("V") else
            "detail" if i.startswith("S") else "design")


def _id_cells(text, title_pat, cell_picks, ws, skip_retired=False):
    """Ledger ids from a table section, taken ONLY from the id-bearing cells (a prose
    mention in any other column is never a reference). skip_retired drops
    retirement-accounting rows (RETIRE_ID on the id cell / RETIRE_MARK on the next)."""
    refs = set()
    for line in ws._section(text, title_pat).splitlines():
        if not line.lstrip().startswith("|") or set(line.strip()) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if skip_retired and cells and (ws.RETIRE_ID.search(cells[0]) or
                (len(cells) > 1 and ws.RETIRE_MARK.match(cells[1].replace("**", "")))):
            continue
        for pick in cell_picks:
            if -len(cells) <= pick < len(cells):
                refs |= {m.group(1)
                         for m in LEDGER_ID.finditer(ws._strip_xcard(cells[pick]))}
    return refs


def _referenced_ids(card_dir, ws):
    """Designated-field references only: requirement 需求条目 id cells, design How-it-meets
    id cells + Parts-table R cells, detail 可追溯 详设项+R-id cells, plan Implements:,
    ledger depends-on lines. Retirement-accounting rows are skipped (_retired_req_ids /
    _id_cells skip_retired)."""
    refs = set(ws.trace_requirement(card_dir)) - ws._retired_req_ids(card_dir)
    refs |= _id_cells(ws._read(os.path.join(card_dir, "design.md")),
                      r"How it meets|如何满足", (0,), ws, skip_retired=True)
    refs |= set(ws.trace_parts(card_dir)[1])
    refs |= _id_cells(ws._read(os.path.join(card_dir, "detail.md")), r"可追溯", (0, -1),
                      ws, skip_retired=True)
    for t in ws.trace_plan(card_dir).values():
        refs |= set(t["rids"])
    for b in ws.parse_ledger(card_dir)[0]:
        refs |= set(b["deps"])
    return refs


APPROVE_NOTE = re.compile(r"^-\s*approved:\s*\d{4}-\d{2}-\d{2}\s+gate\s+\S+", re.M)
ADR_STATUS_MAP = {"proposed": "proposed", "accepted": "approved",
                  "superseded": "superseded", "deprecated": "retired"}


def check_card(project, card_dir, ws):
    """Compatibility aggregate — the original --check <project>/<card> finding list:
    design sections (f) + fact markers (g) + part consistency (h) + governance (i)
    + ledger (a)–(e), in the pre-split order. New code goes through check_card_all
    (per-check isolation + skips); this stays the findings-only surface tests and
    docs cite."""
    return (check_design_sections(card_dir, ws) + check_fact_markers(card_dir, ws)
            + check_part_consistency(card_dir, ws) + check_governance(card_dir, ws)
            + check_ledger(card_dir, ws))


def check_ledger(card_dir, ws):
    """The ledger checks (a)–(e); semantic contradiction stays M3 judgment.
    No decisions.md → [] (old-card semantics, never flagged)."""
    if not os.path.exists(os.path.join(card_dir, "decisions.md")):
        return []
    blocks, findings = ws.parse_ledger(card_dir)
    by_id = {}
    for b in blocks:
        by_id.setdefault(b["id"], []).append(b)
    active = {}
    for i, bs in by_id.items():
        act = [b for b in bs if b["state"] in ws.ACTIVE_STATES]
        if len(act) > 1:
            findings.append("dup-active: " + i)                              # (e)
        active[i] = act[-1] if act else None
    levels_present = {b["level"] for b in blocks}

    for ref in sorted(_referenced_ids(card_dir, ws)):                        # (a)
        if _id_level(ref) not in levels_present:
            continue  # level not ledger-managed yet (degradation axis 2)
        if ref not in by_id:
            findings.append("dangling-id: " + ref)
        elif active[ref] is None:
            findings.append("superseded-ref: " + ref)

    def all_approved(level):
        act = [b for b in blocks if b["level"] == level and b["state"] in ws.ACTIVE_STATES]
        return bool(act) and all(b["state"] == "approved" for b in act)

    for level, doc, done_words in (("requirement", "requirement.md", ("confirmed",)),
                                   # "approved" kept for pre-011 cards; template enum is drafting|frozen|superseded
                                   ("design", "design.md", ("frozen", "approved")),
                                   ("detail", "detail.md", ("baseline",))):    # (b)
        path = os.path.join(card_dir, doc)
        if level not in levels_present or not os.path.exists(path):
            continue
        status = ws.frontmatter(path).get("status", "")
        if (status in done_words) != all_approved(level):
            findings.append(f"status-mismatch: {doc} '{status}' vs ledger {level}")

    for f in sorted(glob.glob(os.path.join(card_dir, "adr", "*.md"))):       # (b) ADR 行
        m = re.search(r"^Status:\s*(\w+)", ws._read(f), re.M)
        adr_id = "ADR-" + os.path.basename(f)[:4]
        act = [b for b in blocks if (b["id"] == adr_id or b["id"].startswith(adr_id + " "))
               and b["state"] in ws.ACTIVE_STATES]
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


# ---- check registry & runners (the L3 entry surface) ----
# Each entry: (id, fn(project, card_dir, ws) -> (findings, skips)). A skip carries its
# reason and never affects the exit code; a check whose carrier predicate doesn't fire
# returns ([], []). Contract invariants (design 021): per-check exception isolation —
# a raising check contributes `check-error:<id>` to findings and the rest still run;
# a check never emits both a finding and a skip for the same condition.

CARD_CHECKS = (
    ("design-sections", lambda p, c, ws: (check_design_sections(c, ws), [])),
    ("fact-markers", lambda p, c, ws: (check_fact_markers(c, ws), [])),
    ("part-consistency", lambda p, c, ws: (check_part_consistency(c, ws), [])),
    ("governance", lambda p, c, ws: (check_governance(c, ws), [])),
    ("ledger", lambda p, c, ws: (check_ledger(c, ws), [])),
)

PROJECT_CHECKS = ()


def _run_entries(entries, args, ws):
    findings, skips = [], []
    for cid, fn in entries:
        try:
            f, s = fn(*args, ws)
        except Exception as e:
            findings.append("check-error:%s: %s" % (cid, e))
            continue
        findings += f
        skips += s
    return findings, skips


def check_card_all(project, card_dir, ws):
    """All card-scoped checks, per-check isolated. Returns (findings, skips)."""
    return _run_entries(CARD_CHECKS, (project, card_dir), ws)


def check_project(project, project_dir, ws):
    """Project scope: project-level checks + every card's card-scoped set (the
    full-sweep form R8's 存量全量跑 runs on). Card rows are prefixed with their
    dir name so a sweep finding stays attributable."""
    findings, skips = _run_entries(PROJECT_CHECKS, (project, project_dir), ws)
    for card_dir in sorted(glob.glob(os.path.join(project_dir, "[0-9][0-9][0-9]-*"))):
        if not os.path.isdir(card_dir):
            continue
        base = os.path.basename(card_dir)
        f, s = check_card_all(project, card_dir, ws)
        findings += ["%s: %s" % (base, x) for x in f]
        skips += ["%s: %s" % (base, x) for x in s]
    return findings, skips
