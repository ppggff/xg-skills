#!/usr/bin/env python3
"""workflow-checks.py — the deterministic check domain (L2 of the status/checks split).

Check implementations behind `workflow-status.py --check`: the ledger checks (a)-(e),
design required sections (f), fact markers (g), part consistency (h), governance
mode (i), the gate-adjacent/trace family (j)-(ab), and the doc-native block family
(ac) format core / (ad) git anchor / (ae) citations & generated views (026). workflow-status.py remains the parsing
layer + CLI entry and lazy-loads this module; every public function takes `ws` = a
live view of the workflow-status module (one-way dependency: checks read the parsing
layer, never the reverse — block_parse.py joins on the parsing side).

Exemption classes — the single source of the three-way not-applicable taxonomy.
A check that cannot judge an object emits a structured exemption record instead of
silently returning; each emission point states its class and reason in place:
- not-yet-due: a lifecycle predicate hasn't fired (card not past a gate, status not
  reached, governance mode not applicable) — silence is the correct semantics;
  default output: none.
- grandfathered: a forward-only cutoff or a legacy carrier shape permanently exempts
  the object (pre-cutoff card, old board/grill-log format) — default output: folded
  into the per-card counting line (bucket 1).
- carrier-missing: an expected carrier is absent, or a present carrier is
  structurally undecidable (missing doc/section/anchor) — a real coverage hole;
  default output: already-visible skip lines stay verbatim, previously-silent paths
  fold into the counting line (bucket 2).

Lives only in xg-dev-workflow/tools/ (not a synced copy).
"""
import collections
import glob
import os
import re

EXEMPTION_CLASSES = ("not-yet-due", "grandfathered", "carrier-missing")
# cls ∈ EXEMPTION_CLASSES · check = registry id · reason = short phrase ·
# scope ∈ ("card", "project") · card = dir basename ("" at project scope) ·
# gated = card passed ≥1 gate (rendering's counting-line predicate; True at
# project scope). Check functions emit (cls, reason) pairs; _run_entries stamps
# the check id; the aggregators stamp scope/card/gated.
Exemption = collections.namedtuple("Exemption", "cls check reason scope card gated")

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
    """Missing-section findings for design.md; not-applicable paths emit exemptions
    (missing carrier / no own created date — judged before the cutoff, whose bare
    string compare would otherwise swallow it / pre-cutoff design)."""
    path = os.path.join(card_dir, "design.md")
    if not os.path.exists(path):
        return [], [], [("carrier-missing", "design.md missing")]
    created = str(ws.frontmatter(path).get("created", ""))
    if not created:
        return [], [], [("carrier-missing", "design.md without created date")]
    if created < DESIGN_SECTIONS_CUTOFF:
        return [], [], [("grandfathered",
                         "design created pre-%s" % DESIGN_SECTIONS_CUTOFF)]
    heads = " | ".join(m.group(1) for m in
                       re.finditer(r"^##+\s+(.+)$", ws._read(path), re.M))
    return ["missing-section: design.md " + name
            for name, pat in DESIGN_REQUIRED_SECTIONS
            if not re.search(pat, heads, re.I)], []


# trailing annotation after ] is legal (longrun_test 002 idiom: `### F24 [VERIFIED] —— note`)
FACT_HEAD = re.compile(r"^###\s+((?:Fact-|F)\d+)\s+\[([^\]]+)\]", re.M)  # Fact- = 026 归一形, F = legacy
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
        return [], [], [("carrier-missing", "facts.md missing/empty")]
    findings, exs, heads = [], [], list(FACT_HEAD.finditer(text))
    for i, m in enumerate(heads):
        marker = m.group(2)
        if "VERIFIED" not in marker.upper() or re.search(r"superseded|retired", marker, re.I):
            continue
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        src = FACT_SOURCE.search(body)
        if not src:
            exs.append(("carrier-missing", "VERIFIED block without 来源 field"))
            continue
        src = src.group(1)
        hit = FACT_SELF_INFER.search(src)
        if not hit and not FACT_POSITIVE.search(src):
            hit = FACT_HEDGE.search(src)
        if hit:
            findings.append("fact-marker: %s marked [%s] but 来源 says '%s'"
                            % (m.group(1), marker, hit.group(0).strip()))
    return findings, [], exs


def check_part_consistency(card_dir, ws):
    """(h) part consistency: with a new-format Parts table (R column present), every
    non-empty plan `Part:` value must name a canonical part; legacy tables (no R
    column) and un-split cards skip — 006-style plan-only Part grouping stays legal."""
    parts, _ = ws.trace_parts(card_dir)
    if not parts:
        # classify the empty result: a Parts table lacking the R column is the
        # legacy shape; anything else is the legal un-split常态
        sect = ws._section(ws._read(os.path.join(card_dir, "design.md")),
                           r"Decomposition\s*/\s*Parts", level=3)
        lines = [ln for ln in sect.splitlines() if ln.lstrip().startswith("|")]
        header = ([c.strip().lower() for c in lines[0].strip().strip("|").split("|")]
                  if lines else [])
        if len(lines) >= 2 and any("part" in h for h in header) \
                and not any(h == "r" for h in header):
            return [], [], [("grandfathered", "legacy Parts table (no R column)")]
        return [], [], [("not-yet-due", "un-split card (no Parts table)")]
    return ["part-mismatch: T%s Part '%s' not in design Parts (%s)"
            % (tid, t["part"], ", ".join(parts))
            for tid, t in sorted(ws.trace_plan(card_dir).items(), key=lambda kv: int(kv[0]))
            if t["part"] and t["part"] not in parts], []


GOVERNANCE_CUTOFF = "2026-08-10"     # cards created on/after must declare the field


def check_governance(card_dir, ws):
    """The four unconditional governance checks (i1)–(i4); report-only."""
    mode = ws.card_mode(card_dir)
    fm = ws.frontmatter(os.path.join(card_dir, "requirement.md"))
    has_ledger = os.path.exists(os.path.join(card_dir, "decisions.md"))
    findings, exs = [], []
    if mode == "invalid":
        findings.append("bad-governance-value: %r" % fm.get("governance"))
    created = str(fm.get("created", ""))
    # bare string compare needs the canonical zero-padded form; a malformed date skips (i2)
    if mode == "legacy":
        if not re.match(r"\d{4}-\d{2}-\d{2}", created):
            exs.append(("carrier-missing", "(i2) created missing/malformed"))
        elif created < GOVERNANCE_CUTOFF:
            exs.append(("grandfathered", "(i2) pre-%s card" % GOVERNANCE_CUTOFF))
        else:
            findings.append("missing-governance-field")
    else:
        exs.append(("not-yet-due", "(i2) governed card, field check off"))
    # real cards annotate status inline ("confirmed # 2026-07-11 human confirm") — strip it
    status = fm.get("status", "").split("#")[0].strip()
    if mode != "ledger":
        exs.append(("not-yet-due", "(i3) mode not ledger"))
    elif status != "confirmed":
        exs.append(("not-yet-due", "(i3) requirement not confirmed"))
    elif not has_ledger:
        findings.append("ledger-mode-no-ledger")
    if mode != "doc-gate":
        exs.append(("not-yet-due", "(i4) mode not doc-gate"))
    elif has_ledger:
        findings.append("doc-gate-has-ledger")
    return findings, [], exs


# ---- ledger reference helpers (feed check_card's (a)) ----
LEDGER_ID = re.compile(r"\b(ADR-\d{4}\s+D\d+|ADR-\d{4}|R\d+|V\d+|S\d+|D\d+)\b")


def _id_level(i):
    return ("requirement" if i.startswith("R") or i.startswith("V") else
            "detail" if i.startswith("S") else "design")


def _id_cells(text, title_pat, cell_picks, ws, skip_retired=False):
    """Ledger ids from a table section, taken ONLY from the id-bearing cells (a prose
    mention in any other column is never a reference). Row parsing + retirement
    detection come from the parsing layer's table_rows() (027 HLD-1 single point);
    cell choice stays the designated cell_picks and the id grammar stays LEDGER_ID."""
    refs = set()
    for row in ws.table_rows(ws._section(text, title_pat)):
        if skip_retired and row["retired"]:
            continue
        cells = row["cells"]
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
        # a dead block's fields are no longer 载重 — its deps don't revive as
        # references (027 T2: R5[retired]→R3 kept a false superseded-ref alive)
        if b["state"] in ws.ACTIVE_STATES:
            refs |= set(b["deps"])
    return refs


def _dep_cycles(graph):
    """Cycle paths in a {node: [dep, …]} graph (white/grey/black DFS); shared by the
    ledger (c) check and the board (w) check."""
    cycles, color = [], {}

    def dfs(n, stack):
        color[n] = 1
        for d in graph.get(n, []):
            if color.get(d) == 1:
                cycles.append(stack + [d])
            elif color.get(d) is None and d in graph:
                dfs(d, stack + [d])
        color[n] = 2

    for n in graph:
        if color.get(n) is None:
            dfs(n, [n])
    return cycles


APPROVE_NOTE = re.compile(r"^-\s*approved:\s*\d{4}-\d{2}-\d{2}\s+gate\s+\S+", re.M)
ADR_STATUS_MAP = {"proposed": "proposed", "accepted": "approved",
                  "superseded": "superseded", "deprecated": "retired"}


def check_card(project, card_dir, ws):
    """Compatibility aggregate — the original --check <project>/<card> finding list:
    design sections (f) + fact markers (g) + part consistency (h) + governance (i)
    + ledger (a)–(e), in the pre-split order. New code goes through check_card_all
    (per-check isolation + skips); this stays the findings-only surface tests and
    docs cite."""
    return (check_design_sections(card_dir, ws)[0] + check_fact_markers(card_dir, ws)[0]
            + check_part_consistency(card_dir, ws)[0] + check_governance(card_dir, ws)[0]
            + check_ledger(card_dir, ws)[0])


def _no_ledger_exemption(card_dir, ws):
    """Absence of decisions.md classified by governance mode — a doc-gate card
    forbids the carrier, a doc-native card retired it (blocks are the ledger,
    026), a ledger card truly lacks it, a legacy card predates the mechanism.
    Shared by (a) and (x) (D3's 同构 made explicit, review #9)."""
    mode = ws.card_mode(card_dir)
    if mode == "doc-gate":
        return ("not-yet-due", "doc-gate card, ledger is a forbidden carrier")
    if mode in DOC_NATIVE_MODES:
        return ("not-yet-due", "doc-native card, ledger retired — blocks are the ledger")
    if mode == "ledger":
        return ("carrier-missing", "ledger card without decisions.md")
    return ("grandfathered", "legacy card without decisions.md")


def check_ledger(card_dir, ws):
    """The ledger checks (a)–(e); semantic contradiction stays M3 judgment.
    No decisions.md → no findings (old-card semantics, never flagged); the
    absence classifies via _no_ledger_exemption."""
    if not os.path.exists(os.path.join(card_dir, "decisions.md")):
        return [], [], [_no_ledger_exemption(card_dir, ws)]
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

    exs = []
    for ref in sorted(_referenced_ids(card_dir, ws)):                        # (a)
        if _id_level(ref) not in levels_present:
            # level not ledger-managed yet (degradation axis 2)
            exs.append(("carrier-missing", "(a) referenced level not ledger-managed"))
            continue
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
        if level not in levels_present:
            exs.append(("carrier-missing", "(b) level has no ledger blocks"))
            continue
        if not os.path.exists(path):
            exs.append(("carrier-missing", "(b) phase doc missing for ledger level"))
            continue
        status = ws.frontmatter(path).get("status", "")
        if (status in done_words) != all_approved(level):
            findings.append(f"status-mismatch: {doc} '{status}' vs ledger {level}")

    adr_files = sorted(glob.glob(os.path.join(card_dir, "adr", "*.md")))     # (b) ADR 行
    if not adr_files:
        exs.append(("carrier-missing", "(b-ADR) no adr dir or empty"))
    for f in adr_files:
        m = re.search(r"^Status:\s*(\w+)", ws._read(f), re.M)
        adr_id = "ADR-" + os.path.basename(f)[:4]
        act = [b for b in blocks if (b["id"] == adr_id or b["id"].startswith(adr_id + " "))
               and b["state"] in ws.ACTIVE_STATES]
        if not m:
            exs.append(("carrier-missing", "(b-ADR) ADR without Status line"))
            continue
        if not act:
            exs.append(("carrier-missing", "(b-ADR) ADR without active ledger block"))
            continue
        word = ADR_STATUS_MAP.get(m.group(1).lower())
        if word is None:
            exs.append(("carrier-missing", "(b-ADR) ADR status value unparsable"))
        if word == "approved" and any(b["state"] == "proposed" for b in act):
            findings.append(f"status-mismatch: {os.path.basename(f)} accepted vs pending rows")
        elif word == "proposed" and all(b["state"] == "approved" for b in act):
            findings.append(f"status-mismatch: {os.path.basename(f)} proposed vs approved rows")
        elif word in ("superseded", "retired"):   # file claims dead, rows still active
            findings.append(f"status-mismatch: {os.path.basename(f)} {m.group(1)} vs active rows")

    graph = {i: (active[i]["deps"] if active[i] else []) for i in by_id}     # (c)
    findings += ["dep-cycle: " + " → ".join(p) for p in _dep_cycles(graph)]

    for b in blocks:                                                          # (d)
        if b["state"] == "approved" and not APPROVE_NOTE.search(b["body"]):
            findings.append("bad-approve-note: " + b["id"])
    return findings, [], exs


# ---- (j)-(m): gate-adjacent checks (021 T3) ----
GATED_DOCS = (("requirement.md", ("confirmed",)),
              ("design.md", ("frozen", "approved")),
              ("detail.md", ("baseline",)))
# Exact full-width literal; self-documenting variants (「落纸补充」,（落纸补充标记）) don't
# match, and backtick-quoted mentions are stripped before counting (mention ≠ use).
TRANSCRIPTION_MARKER = "（落纸补充）"
DISCUSSION_FIRST_CUTOFF = "2026-08-11"   # 019: grill-log mandatory-persist start
RECEIPT_STRUCT_CUTOFF = "2026-08-17"     # 021 landing: structural anchor required from here
GRILL_SHAPE_CUTOFF = "2026-08-18"        # 022 landing: canonical-shape finding era (gated cards)
GRILL_CANON_COLS = ("id", "question", "recommended", "chosen", "why", "depends-on", "status")
RECEIPT_ANCHOR = re.compile(r"^(?:#{2,4}\s+Panel receipt|\*\*Panel receipt)", re.M | re.I)
RECEIPT_LOOSE = re.compile(r"receipt", re.I)
GATE_LINE = re.compile(r"（gate[^）\n]{1,60}）")
GRILL_RESOLVED_ID = re.compile(r"→\s*((?:ADR-\d{4}(?:\s+D\d+)?)|[RVSD]\d+)")


def _doc_status(path, ws):
    # real cards annotate status inline ("confirmed # …") — strip it
    return ws.frontmatter(path).get("status", "").split("#")[0].strip()


def _gated_docs(card_dir, ws):
    for name, gated in GATED_DOCS:
        path = os.path.join(card_dir, name)
        if os.path.exists(path) and _doc_status(path, ws) in gated:
            yield name, path


def _card_created(card_dir, ws):
    """Card created date — delegate to the parsing layer's card_created() (moved
    there in 027: the trace path consumes it too; the format guard lives with it)."""
    return ws.card_created(card_dir)


def _grill_logs(card_dir):
    return sorted(glob.glob(os.path.join(card_dir, "notes", "grill-*.md")))


def check_transcription_markers(project, card_dir, ws):
    """(j) A1 — gate form only: a doc whose status passed its gate carries zero exact
    （落纸补充） markers (approve clears them; mid-flight placement stays M3 judgment).
    Doc-native branch (review #2, HLD-13(1)): the gate predicate is per BLOCK —
    an approved block's own text carries zero markers regardless of doc status
    (partial approve keeps the doc pre-gate while blocks are already binding)."""
    if ws.card_mode(card_dir) in DOC_NATIVE_MODES:
        blocks, _ = ws._block_parse().card_blocks(card_dir)
        findings = []
        for bid, b in blocks.items():
            if b["state"] != "approved":
                continue
            body = "\n".join([b["title"]] + list(b["fields"].values())
                             + [c[1] for c in b["clauses"]])
            n = body.count(TRANSCRIPTION_MARKER)
            if n:
                findings.append("stray-marker: %s %d×%s in approved block"
                                % (bid, n, TRANSCRIPTION_MARKER))
        return findings, [], []
    findings, exs = [], []
    for name, gated in GATED_DOCS:
        path = os.path.join(card_dir, name)
        if not os.path.exists(path):
            exs.append(("carrier-missing", "phase doc missing"))
            continue
        if _doc_status(path, ws) not in gated:
            exs.append(("not-yet-due", "doc not past its gate"))
            continue
        n = _strip_code(_strip_comments(ws._read(path))).count(TRANSCRIPTION_MARKER)
        if n:
            findings.append("stray-marker: %s %d×%s past gate"
                            % (name, n, TRANSCRIPTION_MARKER))
    return findings, [], exs


def _canonical_tables(text):
    """Yield (header, data_rows) for every canonical grill table in text — header
    row holding both `id` and `status` columns (grill.md's seven-column form; the
    single canonical judgment, shared by every consumer). header = lower-cased
    cell list; data_rows = stripped cell lists (separator rows included — callers
    that key off a non-matching cell skip them naturally)."""
    lines, i = text.splitlines(), 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("|"):
            header = [c.strip().lower() for c in ln.strip("|").split("|")]
            if "id" in header and "status" in header:
                rows = []
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    rows.append([c.strip() for c in
                                 lines[i].strip().strip("|").split("|")])
                    i += 1
                yield header, rows
                continue
        i += 1


def _grill_resolved_ids(text):
    """(canonical?, ids): ids = ledger-id targets of `resolved → <id>` status
    cells across canonical tables. Non-id targets (doc-§ form) stay judgment."""
    canonical, ids = False, set()
    for header, rows in _canonical_tables(text):
        canonical, st = True, header.index("status")
        for cells in rows:
            if len(cells) > st and "resolved" in cells[st]:
                ids |= {m.group(1) for m in GRILL_RESOLVED_ID.finditer(cells[st])}
    return canonical, ids


def _grill_shape_era(card_dir, ws):
    """(022) the shape contract binds a card created on/after GRILL_SHAPE_CUTOFF
    that has passed any gate (aligned with A3's activation predicate)."""
    created = _card_created(card_dir, ws)
    return (created >= GRILL_SHAPE_CUTOFF
            and any(True for _ in _gated_docs(card_dir, ws)))


GRILL_MISPLACED = re.compile(r"resolved\s*→")
GRILL_DOCSEC_REF = re.compile(r"→\s*\S+\.md\s*§\S")
_INLINE_CODE_SPAN = re.compile(r"`[^`]*`")


def _grill_shape_findings(name, text, gov=""):
    """(022 R1/R3/R4/R8/R10) per-file shape core: the file must hold a
    canonical table (header with `id`+`status`), every canonical table carries
    all seven columns, `resolved →` outside a canonical table is a misplaced
    decision row, and an arrow-bearing status cell must match the card's
    governance notation (ledger → ledger-id form; doc-gate → `<file>.md §…`
    form, notation only — R8). Bare `resolved`/`open`/`deferred` cells are
    alignment rows, exempt (grill.md). Per-file verdict — a mixed card's
    deviant file is not masked by a conforming sibling (the #15 discipline,
    now at finding severity). Line-wise span strip (fences toggled, inline
    code spans masked per line) keeps line numbers — mention in backticks is
    not use."""
    findings, lines = [], text.splitlines()
    canonical_rows, has_canonical = set(), False
    fence, i = False, 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("```"):
            fence = not fence
            i += 1
            continue
        if not fence and ln.startswith("|"):
            header = [c.strip().lower() for c in ln.strip("|").split("|")]
            if "id" in header and "status" in header:
                has_canonical = True
                missing = [c for c in GRILL_CANON_COLS if c not in header]
                if missing:
                    findings.append("column-drop: %s missing %s"
                                    % (name, ",".join(missing)))
                st = header.index("status")
                canonical_rows.add(i)
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    canonical_rows.add(i)
                    cells = [c.strip() for c in
                             lines[i].strip().strip("|").split("|")]
                    if len(cells) > st and "→" in cells[st]:
                        ok = (GRILL_RESOLVED_ID.search(cells[st])
                              if gov == "ledger" else
                              GRILL_DOCSEC_REF.search(cells[st])
                              if gov == "doc-gate" or gov in DOC_NATIVE_MODES
                              else True)   # HLD-13(5): doc-native shares the doc-form
                        if not ok:
                            findings.append(
                                "notation-mismatch: %s line %d (%s card)"
                                % (name, i + 1, gov))
                    i += 1
                continue
        i += 1
    if not has_canonical:
        findings.insert(0, "non-canonical-grill-log: %s (shape contract)" % name)
    fence = False
    for idx, raw in enumerate(lines):
        s = raw.strip()
        if s.startswith("```"):
            fence = not fence
            continue
        if fence or idx in canonical_rows:
            continue
        if GRILL_MISPLACED.search(_INLINE_CODE_SPAN.sub("", raw)):
            findings.append("misplaced-decision-row: %s line %d" % (name, idx + 1))
    return findings


_QG_ID = re.compile(r"(?<![A-Za-z0-9])[RG]\d+(?![0-9])")


def _question_gloss_hints(name, text):
    """(k) D22 question-gloss hook, report-only: a canonical-table question cell
    holding an R/G id with no parenthetical gloss at all is a bare backreference
    (R6's heaviest clarification-tax form) — a hint on the skips stream (visible,
    never gates), not a finding. Coarse filter: any 括注 passes, gloss content
    quality stays unjudged. Own cutoff (QUESTION_GLOSS_CUTOFF, landing day + 1):
    grill rows are history — question cells are never gloss-backfilled."""
    hints = []
    for header, rows in _canonical_tables(text):
        if "question" not in header:
            continue
        qi, idi = header.index("question"), header.index("id")
        for cells in rows:
            if len(cells) > qi and cells[0] and not set(cells[0]) <= set("|-: "):
                q = cells[qi]
                if _QG_ID.search(q) and "（" not in q and "(" not in q:
                    hints.append("question-gloss: %s %s bare id, no gloss"
                                 % (name, cells[idi] if idi < len(cells) else "?"))
    return hints


def check_grill_reverse(project, card_dir, ws):
    """(k) A2 — transcription reverse fidelity, canonical-table form only: every
    grill-log `resolved → <ledger-id>` row has a decisions.md block (any state —
    existence, not approval). Pre-GRILL_SHAPE_CUTOFF (or ungated) cards: other
    table shapes skip per file. From the shape era on (022): a file without a
    canonical table is a finding, and canonical tables must carry all seven
    columns — the skip branches stay untouched outside the era (skip ≠ pass)."""
    created = _card_created(card_dir, ws)
    if not created:
        # judged before the cutoff — '' < cutoff is vacuously true and used to
        # mislabel this as a pre-cutoff card
        return [], ["grill-reverse: no-created-date"], []
    if created < DISCUSSION_FIRST_CUTOFF:
        return [], [], [("grandfathered",
                         "pre-%s card" % DISCUSSION_FIRST_CUTOFF)]
    logs = _grill_logs(card_dir)
    if not logs:
        return [], ["grill-reverse: no-grill-log"], []
    shape_era = _grill_shape_era(card_dir, ws)
    exs = []
    if created < GRILL_SHAPE_CUTOFF:
        exs.append(("grandfathered",
                    "shape core off (pre-%s)" % GRILL_SHAPE_CUTOFF))
    elif not shape_era:
        exs.append(("not-yet-due", "shape core off (card not past a gate)"))
    gov = str(ws.frontmatter(os.path.join(card_dir, "requirement.md"))
              .get("governance", "")).split("#")[0].strip()
    if shape_era and gov not in ("ledger", "doc-gate") and gov not in DOC_NATIVE_MODES:
        exs.append(("not-yet-due",
                    "governance %s — notation not judged" % (gov or "legacy")))
    findings, hints, ids, noncanon = [], [], set(), 0
    for f in logs:
        text = ws._read(f)
        c, s = _grill_resolved_ids(text)
        if c:
            ids |= s
        elif not shape_era:   # per-file verdict — a mixed set must not read as fully checked (#15)
            noncanon += 1
            exs.append(("grandfathered" if created < GRILL_SHAPE_CUTOFF
                        else "not-yet-due",
                        "non-canonical-grill-log (%s)" % os.path.basename(f)))
        if shape_era:
            findings += _grill_shape_findings(os.path.basename(f), text, gov)
        if created >= QUESTION_GLOSS_CUTOFF:
            hints += _question_gloss_hints(os.path.basename(f), text)
    if not shape_era and noncanon == len(logs):
        # aggregation-only early return — no new emission point (the gloss hook
        # scans canonical tables only, so hints are vacuously empty here)
        return [], [], exs
    if ids and not os.path.exists(os.path.join(card_dir, "decisions.md")):
        # canonical table on a ledger-less card: no home to check against (#13)
        return findings, ["grill-reverse: no-ledger for resolved ids"] + hints, exs
    blocks = {b["id"] for b in ws.parse_ledger(card_dir)[0]}
    return (findings + ["resolved-no-home: " + i for i in sorted(ids - blocks)],
            hints, exs)


RECEIPT_BLOCK_ANCHOR = re.compile(r"^(#{2,4}\s+Panel receipt|\*\*Panel receipt\*\*)")
RECEIPT_HEADING = re.compile(r"^#{1,6}\s")
RECEIPT_KEYS = ("round =", "round type", "lenses =", "re-dispatch =")
# 024 (l) extension — era-gated on the card's created (RECEIPT_PREMISE_CUTOFF),
# inheriting (l)'s gated predicate; premises additionally carries a value-domain
# core, suspicions is presence-only (timing/content evidence stays with the
# round header, human-judged — D14)
RECEIPT_PREMISE_KEYS = ("premises =", "suspicions =")
_PREMISE_VALUE = re.compile(r"premises\s*=\s*(problem\+claim|facts-pack|UNVERIFIED)")
RECEIPT_DISP = re.compile(r"^-\s*(adopted|refuted|open)\b(.*)$")
RECEIPT_DISP_MARK = {"adopted": "→", "refuted": "—", "open": "→"}


def _receipt_block_findings(name, text, premise_era=False):
    """(022 R5) structure core per anchored receipt block: the four header key
    substrings present (six in the premise era); a disposition list line's lead
    word carries its mark on the same line (a parenthetical qualifier between
    word and mark is fine); each block holds ≥1 disposition line or the literal
    "no findings". Only lead-word lines are constrained — lens-4 verdict lists,
    tables, and free bullets stay unparsed (021 R2-adjacent tolerance, panel
    L2-4/T-3). Premise era adds the value-domain core: premises value starts in
    {problem+claim, facts-pack, UNVERIFIED}; facts-pack demands an [F<n>] in the
    same block."""
    lines = text.splitlines()
    anchors = [i for i, ln in enumerate(lines)
               if RECEIPT_BLOCK_ANCHOR.match(ln.strip())]
    findings = []
    for start in anchors:
        end = len(lines)
        for j in range(start + 1, len(lines)):
            s = lines[j].strip()
            if RECEIPT_HEADING.match(s) or RECEIPT_BLOCK_ANCHOR.match(s):
                end = j
                break
        block = "\n".join(lines[start:end])
        label = "%s block@%d" % (name, start + 1)
        missing = [k for k in RECEIPT_KEYS if k not in block]
        if premise_era:
            # mention ≠ use: dispositions cite the keys in backticks — strip
            # code spans before presence/value judgment (new keys only; the
            # four legacy keys keep their raw-substring semantics untouched)
            scan = _INLINE_CODE_SPAN.sub("", block)
            missing += [k for k in RECEIPT_PREMISE_KEYS if k not in scan]
        if missing:
            findings.append("receipt-missing-key: %s (%s)"
                            % (label, ",".join(missing)))
        if premise_era and "premises =" in scan:
            # D13 letter: value domain and the facts-pack [F<n>] demand judge the
            # HEADER segment — up to the first disposition line (review #2)
            hdr = next((k for k, ln in enumerate(lines[start:end])
                        if RECEIPT_DISP.match(ln.strip())), end - start)
            header_seg = _INLINE_CODE_SPAN.sub(
                "", "\n".join(lines[start:start + hdr]))
            m = _PREMISE_VALUE.search(header_seg)
            if not m:
                findings.append("receipt-bad-premises: %s" % label)
            elif m.group(1) == "facts-pack" and \
                    not re.search(r"\[(?:Fact-|F)\d+\]", header_seg):
                findings.append("receipt-premises-no-fact: %s" % label)
        disp = 0
        for raw in lines[start:end]:
            m = RECEIPT_DISP.match(raw.strip())
            if not m:
                continue
            disp += 1
            if RECEIPT_DISP_MARK[m.group(1)] not in m.group(2):
                findings.append("receipt-bad-disposition: %s (%s)"
                                % (label, raw.strip()[:40]))
        if disp == 0 and "no findings" not in block:
            findings.append("receipt-no-dispositions: %s" % label)
    return findings


def check_panel_receipts(project, card_dir, ws):
    """(l) A3 — receipt presence: a card that passed any gate and keeps a grill-log
    must hold ≥1 receipt block; zero blocks = self-certified gate, the primary
    failure. Structural anchor from RECEIPT_STRUCT_CUTOFF on; earlier cards judged
    by the loose word anchor (their receipts predate the pinned form). From
    GRILL_SHAPE_CUTOFF on (022): each anchored block additionally passes the
    per-block structure core (_receipt_block_findings)."""
    created = _card_created(card_dir, ws)
    if not created:
        # judged before the cutoff (see check_grill_reverse) — was mislabeled pre-cutoff
        return [], ["panel-receipts: no-created-date"], []
    if created < DISCUSSION_FIRST_CUTOFF:
        return [], [], [("grandfathered",
                         "pre-%s card" % DISCUSSION_FIRST_CUTOFF)]
    if not any(True for _ in _gated_docs(card_dir, ws)):
        return [], [], [("not-yet-due", "card not past a gate")]
    logs = _grill_logs(card_dir)
    if not logs:
        return [], ["panel-receipts: no-grill-log"], []
    exs = []
    loose = created < RECEIPT_STRUCT_CUTOFF
    if loose:
        exs.append(("grandfathered",
                    "loose receipt anchor (pre-%s)" % RECEIPT_STRUCT_CUTOFF))
    anchor = RECEIPT_LOOSE if loose else RECEIPT_ANCHOR
    if not any(anchor.search(ws._read(f)) for f in logs):
        return ["no-receipts: gated card, grill-log without receipt block"], [], exs
    if created < GRILL_SHAPE_CUTOFF:
        exs.append(("grandfathered",
                    "receipt block core off (pre-%s)" % GRILL_SHAPE_CUTOFF))
        return [], [], exs
    findings = []
    for f in logs:
        text = ws._read(f)
        if RECEIPT_ANCHOR.search(text) and \
                not any(RECEIPT_BLOCK_ANCHOR.match(ln.strip())
                        for ln in text.splitlines()):
            # near-form anchor passed the presence gate but yields zero blocks —
            # the block core silently checks nothing there
            exs.append(("carrier-missing",
                        "receipt anchor near-form, block core off (%s)"
                        % os.path.basename(f)))
        findings += _receipt_block_findings(os.path.basename(f), text,
                                            created >= RECEIPT_PREMISE_CUTOFF)
    return findings, [], exs


def check_docgate_gateline(project, card_dir, ws):
    """(m) A5 — doc-gate audit anchor: each gated doc carries a `（gate <hash>）`
    Change-log line (017 S4); detail.md's container is its Change-notes section so
    only the pattern is required there."""
    if ws.card_mode(card_dir) != "doc-gate":
        return [], [], [("not-yet-due", "mode not doc-gate")]
    findings, exs = [], []
    for name, gated in GATED_DOCS:
        path = os.path.join(card_dir, name)
        if not os.path.exists(path):
            exs.append(("carrier-missing", "gated doc missing"))
            continue
        if _doc_status(path, ws) not in gated:
            exs.append(("not-yet-due", "doc not past its gate"))
            continue
        text = _strip_comments(ws._read(path))
        if name == "detail.md":
            target = ws._section(text, r"Change notes|Change log")
            if not target:
                exs.append(("carrier-missing",
                            "detail.md without Change-notes section, full text scanned"))
                target = text
        else:
            target = ws._section(text, r"Change log")
            if not target:
                findings.append("no-changelog-section: " + name)
                continue
        if not GATE_LINE.search(target):
            findings.append("no-gate-line: " + name)
    return findings, [], exs


# ---- (n): resident supersede-residue sweep (021 T4, A4′) ----
_CSP = None


def _csp():
    """Lazy-load check-superseded-phrases.py (same dir) — the sweep tool owns term
    extraction (terms_from_card) and scanning; this check is its resident face."""
    global _CSP
    if _CSP is None:
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "check-superseded-phrases.py")
        spec = importlib.util.spec_from_file_location("check_superseded_phrases", path)
        _CSP = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_CSP)
    return _CSP


# Decision-zone docs only: the retired-semantics contract lives there; plan/test/progress
# narrate implementation history and legitimately mention old identifiers (T9 baseline:
# sweeping them produced hundreds of adjudicated-history hits).
SWEEP_DOCS = ("requirement.md", "design.md", "detail.md")


def _mask_history(text, ws):
    """Blank the Change log / Change notes bodies preserving line numbers —
    history quotes of old phrasing are exempt (omission-check的 supersede 项).
    Span-sliced, not content-replaced — a body re-appearing verbatim elsewhere
    must not get masked with it (021 review #12)."""
    for pat in (r"Change log", r"Change notes"):
        for m in re.finditer(r"^##\s+(.+)$", text, re.M):
            if re.search(pat, m.group(1)):
                start = m.end()
                nxt = re.search(r"^##\s", text[start:], re.M)
                end = start + nxt.start() if nxt else len(text)
                body = text[start:end]
                text = text[:start] + "\n" * body.count("\n") + text[end:]
                break
    return text


def check_supersede_residue(project, card_dir, ws):
    """(n) A4′ — resident conditional sweep: with machine-readable retired-phrasing
    anchors present, scan the decision-zone docs for surviving old phrasing. History
    containers are masked; notes/, adr/ and ledger/facts files stay out of scope —
    the M2-time full sweep remains `check-superseded-phrases.py`. Pre-021 cards skip
    entirely: their anchors fed one-shot human-adjudicated sweeps, and re-raising
    adjudicated mentions forever is noise (T9 baseline: 151 such hits); from 021 on a
    retained mention is backticked (mention ≠ use) or reworded. No anchors → predicate
    off; a superseding ADR missing its 被取代表述 section surfaces as the extractor's
    finding."""
    created = _card_created(card_dir, ws)
    if not created or created < RECEIPT_STRUCT_CUTOFF:
        # pre-021/no-created cards classify whole-check (the card-level rows own
        # this era); csp's per-path side channel is forwarded in the active era only
        has_anchors = _csp().terms_from_card(card_dir)[:2] != ([], [])
        if not created:
            # judged apart from the cutoff — was folded into (and mislabeled as)
            # the pre-021 branch
            if has_anchors:
                return [], ["supersede-residue: no-created-date (anchors not swept)"], []
            return [], [], [("carrier-missing", "no created date, sweep off")]
        if has_anchors:
            return [], [], [("grandfathered",
                             "pre-021 anchors (one-shot swept at their M2)")]
        return [], [], [("carrier-missing",
                         "no retired-phrase anchors (pre-021 card)")]
    terms, findings, exs = _csp().terms_from_card(card_dir)
    if not terms:
        return findings, [], exs + [("carrier-missing", "no retired-phrase anchors")]
    for name in SWEEP_DOCS:
        text = ws._read(os.path.join(card_dir, name))
        if not text:
            exs.append(("carrier-missing", "sweep doc missing/empty"))
            continue
        in_fence = False
        for i, line in enumerate(_mask_history(text, ws).splitlines(), 1):
            # per-line mention stripping (021 review #2): the promised backtick
            # escape hatch — fenced blocks and inline spans are mentions, not uses
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            scan = _INLINE_CODE_SPAN.sub("", line)
            for t in terms:
                if t in scan:
                    findings.append("superseded-phrase: %s:%d [%s]" % (name, i, t))
    return findings, [], exs


# ---- (x)/(y): doc↔ledger row-level + grill-signature checks (024) ----
# Per-concern cutoffs (the six-step ladder precedent); both new checks activate on
# created-only predicates — pre-gate: an era card is bound while still drafting
# (learn L2's "gate 前机械清单" requires the check to fire before approval).
LEDGER_ROWS_CUTOFF = "2026-08-19"       # (x) binds cards created from here
GRILL_SIGNATURE_CUTOFF = "2026-08-19"   # (y) same date, separate concern
RECEIPT_PREMISE_CUTOFF = "2026-08-19"   # premises=/suspicions= receipt-key era ((l) extension)
QUESTION_GLOSS_CUTOFF = "2026-08-20"    # D22 hook: grill rows are history — no gloss backfill


def check_ledger_rows(project, card_dir, ws):
    """(x) ledger-rows — doc↔ledger row-level consistency, reverse direction only:
    the forward direction (doc row with no / only-dead ledger block) is (a)'s
    dangling-id ∪ superseded-ref, so "双向相等" is delivered by the (a)+(x) pair.
    判定1, state-tiered: an approved requirement-level R block with no active
    需求条目 row is a finding; a proposed block with none is not-yet-due (write
    cadence — the row may legitimately land only at transcription time). V-prefix
    ids and retired/superseded accounting stay out of the judgment set. Carrier
    before mode: absence of decisions.md classifies by governance (check_ledger's
    structure); no 需求条目 table / no requirement-level R blocks → carrier-missing."""
    created = _card_created(card_dir, ws)
    if not created:
        return [], [], [("carrier-missing", "no created date, row check off")]
    if created < LEDGER_ROWS_CUTOFF:
        return [], [], [("grandfathered", "pre-%s card" % LEDGER_ROWS_CUTOFF)]
    if not os.path.exists(os.path.join(card_dir, "decisions.md")):
        return [], [], [_no_ledger_exemption(card_dir, ws)]
    reqs = ws.trace_requirement(card_dir)
    if not reqs:
        return [], [], [("carrier-missing", "no 需求条目 table")]
    rblocks = [b for b in ws.parse_ledger(card_dir)[0]
               if b["level"] == "requirement" and not b["id"].startswith("V")]
    if not rblocks:
        return [], [], [("carrier-missing", "no requirement-level ledger blocks")]
    rows = set(reqs) - ws._retired_req_ids(card_dir)
    findings, exs = [], []
    for b in rblocks:
        if b["id"] in rows or b["state"] not in ws.ACTIVE_STATES:
            continue
        if b["state"] == "approved":
            findings.append("block-no-row: " + b["id"])
        else:
            exs.append(("not-yet-due",
                        "proposed block %s awaiting its row" % b["id"]))
    # 判定2/判定3 — coarse filter over active statement cells (masked history);
    # covered form = weight-token drift; a whole-clause addition carrying no
    # digits is a KNOWN false negative (structural counting stays Future)
    active_block = {}
    for b in rblocks:
        if b["state"] in ws.ACTIVE_STATES:
            active_block.setdefault(b["id"], b)
    masked = _mask_history(ws._read(os.path.join(card_dir, "requirement.md")), ws)
    seen = set()
    for m in re.finditer(r"^\|\s*(?:\*\*|~~|\[)?\s*(R\d+)[^|]*\|([^|]*)\|", masked, re.M):
        rid, cell = m.group(1), m.group(2)
        if rid in seen or rid not in rows or rid not in active_block:
            continue   # retired accounting exempt; dangling rows are (a)'s domain
        seen.add(rid)
        body = active_block[rid]["body"]
        for tok in _weight_tokens(cell):
            if tok not in body:
                findings.append("row-token-missing: %s [%s]" % (rid, tok))
        findings += _paren_count_findings(rid, cell)
    return findings, [], exs


SIGNATURE_SCAN_DOCS = ("requirement.md", "decisions.md", "facts.md", "design.md",
                       "detail.md", "plan.md", "test.md")
# left boundary keeps PG16-style substrings from minting phantom ids (review #3;
# same lookbehind as _QG_ID); fullmatch callers are unaffected (nothing precedes pos 0)
_GID = re.compile(r"(?<![A-Za-z0-9])G\d+(?:[a-z]|\.\d+)?")
_GID_RANGE = re.compile(r"(?<![A-Za-z0-9])G(\d+)\s*[–-]\s*G?(\d+)\b")


def _line_gids(line):
    """G-ids referenced on one line: longest-match grammar (G6b never degrades to
    G6), slash lists fall out of findall, en-dash/hyphen ranges expand. Extraction
    runs BEFORE any code-span strip — backtick-quoted G-ids are references here
    (the corpus majority form). The range cap guards prose dashes."""
    ids = set(_GID.findall(line))
    for m in _GID_RANGE.finditer(line):
        a, b = int(m.group(1)), int(m.group(2))
        if a < b and b - a <= 200:
            ids |= {"G%d" % k for k in range(a, b + 1)}
    return ids


def _accounting_line(line, ws):
    """Supersede/retire accounting carriers: the judgment has migrated — residue is
    (n)/M2 domain, not a closure demand."""
    ls = line.strip()
    if re.match(r"-\s*(retired|superseded):", ls):
        return True
    if ls.startswith("|"):
        cells = [c.strip() for c in ls.strip("|").split("|")]
        return bool(cells and (ws.RETIRE_ID.search(cells[0]) or
                    (len(cells) > 1 and
                     ws.RETIRE_MARK.match(cells[1].replace("**", "")))))
    return False


def _grill_id_index(card_dir, ws):
    """(any_canonical, {G-id: {"status", "chosen"}}) — union over every canonical
    table in the card's grill-logs (G ids are card-unique). Canonical judgment
    lives once in _canonical_tables; the header's own column positions supply
    the cells."""
    index, any_canonical = {}, False
    for f in _grill_logs(card_dir):
        for header, rows in _canonical_tables(ws._read(f)):
            any_canonical = True
            if "chosen" not in header:
                # closure is structurally undecidable without a chosen column —
                # rows stay out of the index so their ids resolve to
                # carrier-missing, never a finding (023 taxonomy; review #1);
                # the column drop itself is (k)'s column-drop in the gated era
                continue
            idc, st = header.index("id"), header.index("status")
            ch = header.index("chosen")
            for cells in rows:
                gid = cells[idc].strip("`* ") if idc < len(cells) else ""
                if _GID.fullmatch(gid):
                    index.setdefault(gid, {
                        "status": cells[st] if st < len(cells) else "",
                        "chosen": cells[ch] if ch < len(cells) else ""})
    return any_canonical, index


def check_grill_signature(project, card_dir, ws):
    """(y) grill-signature — closure of human-signature references: a top-level-doc
    line co-locating 人工 and a G-id claims a human grill decision; the referenced
    row (union id index over all grill-logs) must be closed — status not open
    (lexically anchored on the cell's first word) and chosen non-empty
    (placeholder-aware). There is no separate deferred rule: a deferred row is
    excluded from passing by the chosen-non-empty condition alone. Scan domain =
    the seven top-level card files (notes/, log.md, progress.md excluded); history
    masked (a Change-log-only reference is never checked — _mask_history's
    boundary); accounting lines and non-active ledger blocks are out of scope.
    Absence in every form — no grill-log, no canonical table, id not in the union
    index — is carrier-missing (prune compatibility, 019 D3, outranks wrong-id
    detection; typos stay M3 judgment). Closure is shape, not fidelity (lens 4).
    Doc-native cards branch to the ask-id-keyed v2 (026 LLD-5); legacy/doc-gate
    keep the 人工-co-location key and scan domain untouched. Created-only
    pre-gate predicate."""
    if ws.card_mode(card_dir) in DOC_NATIVE_MODES:
        return check_grill_docnative(card_dir, ws)
    created = _card_created(card_dir, ws)
    if not created:
        return [], [], [("carrier-missing", "no created date, signature check off")]
    if created < GRILL_SIGNATURE_CUTOFF:
        return [], [], [("grandfathered", "pre-%s card" % GRILL_SIGNATURE_CUTOFF)]
    refs = {}
    for name in SIGNATURE_SCAN_DOCS:
        text = ws._read(os.path.join(card_dir, name))
        if not text:
            continue
        if name == "decisions.md":
            head = text.split("### ", 1)[0]
            scan = head.splitlines()
            for b in ws.parse_ledger(card_dir)[0]:
                if b["state"] in ws.ACTIVE_STATES:
                    scan += b["body"].splitlines()
        else:
            scan = _mask_history(text, ws).splitlines()
        for line in scan:
            # 待人工 (awaiting-human) is a pending marker, not a signature —
            # a line whose every 人工 sits inside 待人工 makes no closure claim
            # (review #7, human-approved D7 precision fix)
            if "人工" not in line.replace("待人工", "") or _accounting_line(line, ws):
                continue
            for gid in _line_gids(line):
                refs.setdefault(gid, name)
    if not _grill_logs(card_dir):
        return [], [], [("carrier-missing", "no grill-log, signatures not checkable")]
    any_canonical, index = _grill_id_index(card_dir, ws)
    if not any_canonical:
        return [], [], [("carrier-missing", "grill-log without canonical table")]
    findings, exs = [], []
    for gid in sorted(refs, key=lambda g: (int(re.match(r"G(\d+)", g).group(1)), g)):
        row = index.get(gid)
        if row is None:
            exs.append(("carrier-missing",
                        "signature id %s not in grill-log index" % gid))
            continue
        chosen = row["chosen"].strip("* ")
        if re.match(r"open\b", row["status"].strip(), re.I) \
                or not chosen or chosen in ws.PLACEHOLDERS:
            findings.append("signature-open: %s (%s)" % (gid, refs[gid]))
    return findings, [], exs


_WEIGHT_TOKEN = re.compile(r"\d+|[一二三四五六七八九十百千万亿零两]+")
# non-weight digit carriers stripped before token extraction (024 review #6,
# human-approved D6 strip-list extension): dates, ADR ids, uppercase-letter id
# forms (R/G/E/F/D/T/S/L/V…, incl. suffixed G6b/G3.1), § references
_TOKEN_STRIP = re.compile(
    r"\d{4}-\d{2}-\d{2}|ADR-\d{4}"
    r"|(?<![A-Za-z0-9])[A-Z]{1,3}\d+(?:[a-z]|\.\d+)?(?![0-9])"
    r"|§\d+")
_PAREN_COUNT = re.compile(r"（\s*(\d+|[一二三四五六七八九十])\s*[类条项处种个]）")
_CJK_NUM = {c: i for i, c in enumerate("零一二三四五六七八九十")}
_LIST_RUN = re.compile(r"[^、／（）：:；;。|]+(?:[、／][^、／（）：:；;。|]+)+")


def _weight_tokens(cell):
    """Digit + Chinese-numeral runs from a statement cell; code spans, id forms,
    dates, ADR ids and § refs are stripped first (their digits are not weight
    claims — 003 原型 + review #6); tokens dedup per cell (one finding per
    distinct missing token)."""
    scan = _TOKEN_STRIP.sub("", _INLINE_CODE_SPAN.sub("", cell))
    return list(dict.fromkeys(_WEIGHT_TOKEN.findall(scan)))


def _paren_count_findings(rid, cell):
    """判定3, opportunistic: a `（<数>[类条项处种个]）` claim is checked only when the
    same cell holds a locatable closed list (、/／-separated run, ≥2 items — the
    longest run counts); no locatable list → not accounted (the notation is not
    mandatory)."""
    scan = _INLINE_CODE_SPAN.sub("", cell)
    claims = _PAREN_COUNT.findall(scan)
    if not claims:
        return []
    listable = _PAREN_COUNT.sub("", scan)
    runs = [r.count("、") + r.count("／") + 1 for r in _LIST_RUN.findall(listable)]
    if not runs:
        return []
    n = max(runs)
    out = []
    for c in claims:
        want = int(c) if c.isdigit() else _CJK_NUM[c]
        if want != n:
            out.append("count-mismatch: %s claims %d, list has %d" % (rid, want, n))
    return out


# ---- (o)-(t): card-scoped B/C checks (021 T5) ----
PHASE_DOC_NAMES = ("requirement.md", "design.md", "detail.md",
                   "plan.md", "test.md", "progress.md")
# link-domain placeholder exclusion — its own vocabulary, NOT the shared PLACEHOLDERS
# (that set has four other consumers with set-membership semantics)
LINK_PLACEHOLDER = re.compile(r"[…<>*]|\.\.\.|NNN|<slug>|<project>")
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
MDLINK = re.compile(r"\]\(([^)#\s]+)")
FREF = re.compile(r"\[(?:Fact-|F)(\d+)\]")
XFREF = re.compile(r"\[(\d{3}):(?:Fact-|F)(\d+)\]")   # cross-card form [NNN:F<n>] (021 D4)
PROGRESS_CAP = 180        # template's ≈150-line cap + 20% buffer
ADR_BODY_CAP = 240        # omission-check's ~200-line lean body + 20% buffer


def _strip_code(text):
    """Fenced blocks + inline code spans removed — a backticked mention is not a use."""
    return re.sub(r"`[^`]*`", "", re.sub(r"```.*?```", "", text, flags=re.S))


def _strip_comments(text):
    """HTML comments removed — template guidance riding in <!-- --> is never doc
    content (021 review #4: a comment's literal（gate …）satisfied the audit-anchor
    check)."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def _kb_root():
    cfg = os.path.expanduser("~/.config/xg-knowledge-wiki/config.yaml")
    try:
        with open(cfg, encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"root:\s*(\S+)", line)
                if m:
                    return os.path.expanduser(m.group(1).strip().strip("\"'"))
    except OSError:
        pass
    return os.path.expanduser("~/knowledge")


def _aliases(path):
    """frontmatter aliases values — flow form (`aliases: [a, b]`) and block form
    (`aliases:` + `- a` lines; 021 review #7)."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read(1500).splitlines()
    except OSError:
        return []
    for i, line in enumerate(lines):
        m = re.match(r"aliases:\s*(.*)", line)
        if not m:
            continue
        tail = m.group(1).strip()
        if tail:
            return [a.strip().strip("\"'") for a in tail.strip("[]").split(",")]
        vals = []
        for nxt in lines[i + 1:]:
            mm = re.match(r"\s+-\s+(.+)", nxt)
            if not mm:
                break
            vals.append(mm.group(1).strip().strip("\"'"))
        return vals
    return []


def _kb_resolves(kb, target):
    """kb/<layer>/<project>/<slug>(.md) exists, or an aliases: frontmatter names the slug."""
    if os.path.exists(os.path.join(kb, target + ".md")) or \
       os.path.exists(os.path.join(kb, target)):
        return True
    parent, slug = os.path.split(target.rstrip("/"))
    return any(slug in _aliases(f)
               for f in glob.glob(os.path.join(kb, parent, "*.md")))


def _wiki_targets(stripped):
    """Canonical-form wikilinks only (layer/project/slug — must contain '/'): bare-slug
    legacy links and prose [[…]] emphasis are not the machine contract (T9 baseline)."""
    return [t.strip() for t in WIKILINK.findall(stripped)
            if "/" in t and not LINK_PLACEHOLDER.search(t)]


def _rel_targets(stripped):
    """Path-shaped relative links only: `](x)` in prose (footnotes, commit hashes,
    Chinese brackets) is not a link claim — require ./ ../ , a slash, or .md."""
    return [p for p in MDLINK.findall(stripped)
            if not LINK_PLACEHOLDER.search(p)
            and not re.match(r"[a-z]+://|mailto:|~|/", p)
            and (p.startswith(("./", "../")) or "/" in p or p.endswith(".md"))]


def check_links(project, card_dir, ws):
    """(o) B1 card half — every [[wikilink]] resolves in the KB (aliases honored),
    every relative link resolves on disk. KB root unreachable ⇒ the whole check
    skips (never a partial finding+skip mix)."""
    kb = _kb_root()
    if not os.path.isdir(kb):
        return [], ["links: no-kb-root"], []
    findings, exs = [], []
    for name in PHASE_DOC_NAMES:
        text = ws._read(os.path.join(card_dir, name))
        if not text:
            exs.append(("carrier-missing", "phase doc missing/empty"))
            continue
        stripped = _strip_code(text)
        if any("/" not in t for t in WIKILINK.findall(stripped)
               if not LINK_PLACEHOLDER.search(t)):
            exs.append(("grandfathered", "bare-slug wikilink not validated"))
        for t in _wiki_targets(stripped):
            if not _kb_resolves(kb, t):
                findings.append("broken-wikilink: %s [[%s]]" % (name, t))
        for p in _rel_targets(stripped):
            if not os.path.exists(os.path.normpath(os.path.join(card_dir, p))):
                findings.append("broken-link: %s %s" % (name, p))
    return findings, [], exs


def check_status_field(project, card_dir, ws):
    """(p) B2′ — every existing phase doc declares frontmatter `status` (the one
    machine-read field left after `updated:` was dropped, 021 R4)."""
    findings, exs = [], []
    for name in PHASE_DOC_NAMES:
        path = os.path.join(card_dir, name)
        if not os.path.exists(path):
            exs.append(("carrier-missing", "phase doc missing"))
        elif not ws.frontmatter(path).get("status"):
            findings.append("missing-status: " + name)
    return findings, [], exs


TRACE_CUTOFF = "2026-07-28"   # 011 template-explicitness: the R-id spine became mandatory
                              # in design/plan/test then; earlier docs carry it sparsely


def check_r_trace(project, card_dir, ws):
    """(q) B6 — R-trace existence, four dimensions with per-dimension predicates:
    not-in-需求条目 always (the XCARD_REF-class detection); design home once design.md
    is frozen/approved (mid-draft gaps are the freeze gate's business); ≥1 plan task /
    ≥1 test row once those docs exist — these three only for cards created on/after
    TRACE_CUTOFF. Prose-only requirements (no 需求条目 table) and retired R-ids exempt."""
    reqs = ws.trace_requirement(card_dir)
    if not reqs:
        return [], [], [("carrier-missing", "no 需求条目 table")]
    created = _card_created(card_dir, ws)
    exs = []
    if not created:
        exs.append(("carrier-missing", "no created date, downstream trace off"))
    elif created < TRACE_CUTOFF:
        exs.append(("grandfathered",
                    "downstream trace off (pre-%s)" % TRACE_CUTOFF))
    downstream = bool(created) and created >= TRACE_CUTOFF
    if downstream:
        dpath = os.path.join(card_dir, "design.md")
        if not os.path.exists(dpath):
            exs.append(("carrier-missing", "design.md missing, no-design-home off"))
        elif _doc_status(dpath, ws) not in ("frozen", "approved"):
            exs.append(("not-yet-due", "design not frozen, no-design-home off"))
        if not os.path.exists(os.path.join(card_dir, "plan.md")):
            exs.append(("carrier-missing", "plan.md missing, no-task off"))
        if not os.path.exists(os.path.join(card_dir, "test.md")):
            exs.append(("carrier-missing", "test.md missing, no-test-coverage off"))
    retired = ws._retired_req_ids(card_dir)
    home, _verify = ws.trace_design(card_dir)
    tasks = ws.trace_plan(card_dir)
    by_r = set()
    for t in tasks.values():
        by_r |= set(t["rids"])
    cov = ws.trace_test(card_dir)
    findings = []
    for r in sorted(set(reqs) | set(home) | by_r | set(cov), key=ws.rid_key):
        if r in retired:
            exs.append(("grandfathered", "retired R-id excluded"))
            continue
        if r not in reqs:
            findings.append("trace: %s not-in-需求条目" % r)
            continue
        if not downstream:
            continue
        if _doc_status(os.path.join(card_dir, "design.md"), ws) in ("frozen", "approved") \
                and r not in home:
            findings.append("trace: %s no-design-home" % r)
        if os.path.exists(os.path.join(card_dir, "plan.md")) and r not in by_r:
            findings.append("trace: %s no-task" % r)
        if os.path.exists(os.path.join(card_dir, "test.md")) and r not in cov:
            findings.append("trace: %s no-test-coverage" % r)
    if downstream and ws.card_mode(card_dir) in DOC_NATIVE_MODES \
            and os.path.exists(os.path.join(card_dir, "test.md")):
        # per-Effect granularity (026 Req-37 机械半, riding (q) — no new check):
        # every Effect id keys a coverage row (first cell) in test.md
        req_text = ws._read(os.path.join(card_dir, "requirement.md"))
        test_text = ws._read(os.path.join(card_dir, "test.md"))
        keyed = set()
        for line in test_text.splitlines():
            if line.lstrip().startswith("|"):
                cell = line.strip().strip("|").split("|", 1)[0]
                keyed |= set(re.findall(r"(?<![A-Za-z])(?:Eff-|E)(\d+)(?![0-9A-Za-z])", cell))
        for eid in set(EFFECT_ID.findall(req_text)):
            if re.search(r"(\d+)$", eid).group(1) not in keyed:
                findings.append("trace: %s no-coverage-row" % eid)
    return findings, [], exs


# existence harvest is marker-agnostic (012-era heads carry no [marker]); a head naming
# superseded/retired is excluded either way — marker INTEGRITY stays (g)'s job
FACT_HEAD_ANY = re.compile(r"^###\s+(?:Fact-|F)(\d+)\b(.*)$", re.M)


def _fact_ids(card_dir, ws):
    """Active facts.md block ids ∪ doc-local「事实清单」ids, as ints."""
    ids = set()
    text = ws._read(os.path.join(card_dir, "facts.md"))
    for m in FACT_HEAD_ANY.finditer(text):
        if not re.search(r"superseded|retired", m.group(2), re.I):
            ids.add(int(m.group(1)))
    for name in PHASE_DOC_NAMES:
        text = ws._read(os.path.join(card_dir, name))
        sect = ws._section(text, r"事实清单") or ws._section(text, r"事实清单", level=3)
        ids |= {int(n) for n in re.findall(r"\bF(\d+)\b", sect)}
    return ids


def check_fact_refs(project, card_dir, ws):
    """(r) B7 — [F<n>] citations resolve: bare form against THIS card's active facts
    (facts.md ∪ doc-local 事实清单); cross-card [NNN:F<n>] (021 D4) against the target
    card's fact carriers. A citation with no carrier anywhere is a finding — the
    non-silent form R9 assigns this check."""
    own = None   # lazy — most docs have no refs
    findings, exs = [], []
    for name in PHASE_DOC_NAMES:
        text = ws._read(os.path.join(card_dir, name))
        if not text:
            exs.append(("carrier-missing", "phase doc missing/empty"))
            continue
        stripped = _strip_code(text)
        stripped_x = XFREF.sub("", stripped)
        for n in {int(x) for x in FREF.findall(stripped_x)}:
            if own is None:
                own = _fact_ids(card_dir, ws)
            if n not in own:
                findings.append("dangling-fref: [F%d] (%s)" % (n, name))
        for nnn, n in {(a, int(b)) for a, b in XFREF.findall(stripped)}:
            hits = glob.glob(os.path.join(os.path.dirname(card_dir), nnn + "-*"))
            if not hits or n not in _fact_ids(hits[0], ws):
                findings.append("dangling-fref: [%s:F%d] (%s)" % (nnn, n, name))
    return findings, [], exs


def check_progress_cap(project, card_dir, ws):
    """(s) B8 — progress.md stays a snapshot: over-cap flags on live cards only
    (done/dropped cards' prune duty ended with the card, 021 D5)."""
    path = os.path.join(card_dir, "progress.md")
    if not os.path.exists(path):
        return [], [], [("carrier-missing", "progress.md missing")]
    state = ws.board(os.path.dirname(card_dir)).get(
        os.path.basename(card_dir)[:3], {}).get("state", "").strip("*").strip()
    if state in ("done", "dropped"):
        return [], [], [("not-yet-due", "closed card (done/dropped), cap not judged")]
    n = ws._read(path).count("\n") + 1
    if n > PROGRESS_CAP:
        return ["progress-over-cap: %d lines (cap %d)" % (n, PROGRESS_CAP)], []
    return [], []


def check_adr_hygiene(project, card_dir, ws):
    """(t) C4 — ADR hygiene: no `## Amendment` block (changes are superseding ADRs);
    body ≤ ADR_BODY_CAP lines; a superseded ADR keeps ≤2 lines referencing its
    superseder (the forward pointer, not a running commentary)."""
    adr_files = sorted(glob.glob(os.path.join(card_dir, "adr", "*.md")))
    if not adr_files:
        return [], [], [("carrier-missing", "no adr dir or empty")]
    findings, exs = [], []
    for f in adr_files:
        base = "adr/" + os.path.basename(f)
        text = ws._read(f)
        if re.search(r"^##\s*Amendment", text, re.M):
            findings.append("adr-amendment: " + base)
        n = text.count("\n") + 1
        if n > ADR_BODY_CAP:
            findings.append("adr-over-cap: %s %d lines (cap %d)" % (base, n, ADR_BODY_CAP))
        m = re.search(r"^Status:\s*superseded\s*(?:by\s*(ADR-\d{4}))?", text, re.M | re.I)
        if m and not m.group(1):
            exs.append(("carrier-missing",
                        "superseded without 'by ADR-NNNN' pointer"))
        if m and m.group(1):
            refs = sum(1 for ln in text.splitlines() if m.group(1) in ln)
            if refs > 2:
                findings.append("adr-forward-ref: %s %d lines cite %s"
                                % (base, refs, m.group(1)))
    return findings, [], exs


# ---- (z)/(aa) 028: home-pointer + requirement handoff carrier ----

# a 归宿 cell that cites a table must name a row inside it (or cite a decision id);
# a bare table pointer is a dangling home — the row it needs may not exist at all
# calibrated against every card in dev_root: engaging the row dimension AT ALL
# (any 行 / 本表 / 该表) is the discriminator — narrower forms produced false positives
ROW_NAMED = re.compile(r"行|\d+\s*[条项]|本表|该表")
DECISION_REF = re.compile(r"`[DS]\d+`")
# the 需求条目 provenance column handing work to the design phase
HANDOFF = re.compile(r"归\s*(设计|`?design)|由设计(定|阶段)|设计阶段(须|再|要|给出|确认|定)|留给设计")


def _design_table_sections(card_dir, ws):
    """Named design.md sections whose body is a table (≥3 pipe lines), keyed by the
    short name a 归宿 cell would cite (heading text before ' ——' / a paren gloss)."""
    text = ws._read(os.path.join(card_dir, "design.md"))
    keys = {}
    heads = list(re.finditer(r"^###?\s+(.+?)\s*$", text, re.M))
    for i, m in enumerate(heads):
        body = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        if len([ln for ln in body.split("\n") if ln.strip().startswith("|")]) < 3:
            continue
        key = re.split(r"（|\(| ——", m.group(1))[0].strip()
        if len(key) >= 3:
            keys[key] = m.group(1)
    return keys


def check_home_pointer(project, card_dir, ws):
    """(z) 028 — 「How it meets」归宿 cells resolve to a row, not just a table: a cell
    citing a named table section must name a row in it (「X」行 / 逐行 / N 行) or cite a
    `D<n>`/`S<n>`. A bare table pointer reads as a home while the row may not exist —
    the table's enumeration key can be a different kind of thing than the R's subject.
    Judged once design.md is frozen/approved (mid-draft gaps are the freeze gate's
    business), on cards created on/after TRACE_CUTOFF."""
    dpath = os.path.join(card_dir, "design.md")
    if not os.path.exists(dpath):
        return [], [], [("carrier-missing", "design.md missing")]
    created = _card_created(card_dir, ws)
    if not created:
        return [], [], [("carrier-missing", "no created date")]
    if created < TRACE_CUTOFF:
        return [], [], [("grandfathered", "pre-%s card" % TRACE_CUTOFF)]
    if _doc_status(dpath, ws) not in ("frozen", "approved"):
        return [], [], [("not-yet-due", "design not frozen")]
    text = ws._read(dpath)
    parts = text.split("## How it meets the requirement")
    if len(parts) < 2:
        return [], [], [("carrier-missing", "no 「How it meets」 section")]
    keys = _design_table_sections(card_dir, ws)
    if not keys:
        return [], [], [("carrier-missing", "no table sections to point at")]
    findings = []
    for ln in parts[1].split("\n## ")[0].split("\n"):
        m = re.match(r"^\|\s*\[?(R\d+)\]?[^|]*\|\s*(.*?)\s*\|\s*$", ln)
        if not m:
            continue
        rid, home = m.group(1), m.group(2)
        cited = sorted(k for k in keys if k in home)
        if not cited or ROW_NAMED.search(home) or DECISION_REF.search(home):
            continue
        findings.append("home-pointer: %s cites 「%s」 without naming a row"
                        % (rid, cited[0]))
    return findings, [], []


def check_req_handoff(project, card_dir, ws):
    """(aa) 028 — work handed to a later phase needs a carrier that phase reads: a
    需求条目 row whose **provenance** column hands work to design while its 陈述 does
    not is flagged. The design agenda is driven by the R statement, Open questions and
    the `G<n>` queue — never by the provenance column, so a handoff parked there is
    invisible to the phase meant to do it. Cards created on/after TRACE_CUTOFF."""
    path = os.path.join(card_dir, "requirement.md")
    if not os.path.exists(path):
        return [], [], [("carrier-missing", "requirement.md missing")]
    created = _card_created(card_dir, ws)
    if not created:
        return [], [], [("carrier-missing", "no created date")]
    if created < TRACE_CUTOFF:
        return [], [], [("grandfathered", "pre-%s card" % TRACE_CUTOFF)]
    rows = 0
    findings = []
    for ln in ws._read(path).split("\n"):
        if not re.match(r"^\|\s*R\d+\s*\|", ln):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        rows += 1
        if HANDOFF.search(cells[-1]) and not HANDOFF.search(cells[1]):
            findings.append("req-handoff: %s hands work to design in provenance only"
                            % cells[0])
    if not rows:
        return [], [], [("carrier-missing", "no 需求条目 table")]
    return findings, [], []


# ---- (ab) 029: at the design freeze the 详设 disposition must be visible ----

# presence-only: the note names 详设 and says what happens to it
DETAIL_WORD = re.compile(r"详设|detail\.md")
DETAIL_DISPOSITION = re.compile(r"skip|跳过|不做|免|planned|计划|待写|要写|排入|下一步")


def check_detail_disposition(project, card_dir, ws):
    """(ab) 029 — a frozen design closes the 详设 window, so the disposition must be
    visible by then: either `detail.md` exists (the M+ path was taken) or `progress.md`
    names 详设 with what happens to it. `governance:` is pre-filled from *apparent*
    sizing at `new`; a card that outgrew it silently keeps the default, and the only
    other machine signal for a skipped 详设/评审 fires at `done` — long past the point
    where 详设 could still have been written. The 评审 half stays with that done-time
    check; this one owns just the window that closes at freeze — so a card already
    `done` is exempt (nothing actionable left), and it fires only while the card is
    still in flight."""
    dpath = os.path.join(card_dir, "design.md")
    if not os.path.exists(dpath):
        return [], [], [("carrier-missing", "design.md missing")]
    created = _card_created(card_dir, ws)
    if not created:
        return [], [], [("carrier-missing", "no created date")]
    if created < TRACE_CUTOFF:
        return [], [], [("grandfathered", "pre-%s card" % TRACE_CUTOFF)]
    if _doc_status(dpath, ws) not in ("frozen", "approved"):
        return [], [], [("not-yet-due", "design not frozen")]
    if os.path.exists(os.path.join(card_dir, "detail.md")):
        return [], [], []
    rows = ws.board(os.path.dirname(card_dir))
    state = str(rows.get(os.path.basename(card_dir)[:3], {}).get("state", "")).strip()
    if state == "done":
        # the window closed long ago; the done-time close-out check owns what is left
        return [], [], [("not-yet-due", "card done, detail window closed")]
    ptext = " ".join(ws._read(os.path.join(card_dir, "progress.md")).split())
    if not ptext:
        return [], [], [("carrier-missing", "progress.md missing")]
    if DETAIL_WORD.search(ptext) and DETAIL_DISPOSITION.search(ptext):
        return [], [], []
    return (["detail-disposition: design frozen, no detail.md and no 详设 disposition "
             "recorded"], [], [])


# ---- (u)-(w) + B1 project half: project-scoped checks (021 T6) ----

def _new_board_format(project_dir, ws):
    """Discriminator (021 L2-4 显式化): the index header carries an 整体状态 column;
    old-format boards are exempt from board-shape checks."""
    text = ws._read(os.path.join(project_dir, "index.md"))
    return text, any(ln.lstrip().startswith("|") and "整体状态" in ln
                     for ln in text.splitlines())


def check_project_links(project, project_dir, ws):
    """(o) B1 project half — index.md/roadmap.md wikilinks + relative links."""
    kb = _kb_root()
    if not os.path.isdir(kb):
        return [], ["links: no-kb-root"], []
    findings, exs = [], []
    for name in ("index.md", "roadmap.md"):
        text = ws._read(os.path.join(project_dir, name))
        if not text:
            exs.append(("carrier-missing", "project doc missing/empty"))
            continue
        stripped = _strip_code(text)
        for t in _wiki_targets(stripped):
            if not _kb_resolves(kb, t):
                findings.append("broken-wikilink: %s [[%s]]" % (name, t))
        for p in _rel_targets(stripped):
            if not os.path.exists(os.path.normpath(os.path.join(project_dir, p))):
                findings.append("broken-link: %s %s" % (name, p))
    return findings, [], exs


def check_board_rows(project, project_dir, ws):
    """(u) B3 — card dir ↔ board row, both directions (the missing-row degradation
    iter_cards already computes, promoted to findings). Old-format boards exempt."""
    text, new_format = _new_board_format(project_dir, ws)
    if not text:
        return ["no-index: index.md missing"], []
    if not new_format:
        return [], [], [("grandfathered", "old-format board")]
    rows = ws.board(project_dir)
    dirs = {os.path.basename(d)[:3]: os.path.basename(d)
            for d in sorted(glob.glob(os.path.join(project_dir, "[0-9][0-9][0-9]-*")))
            if os.path.isdir(d)}
    findings = ["board-missing-row: " + name
                for nnn, name in dirs.items() if nnn not in rows]
    findings += ["board-orphan-row: " + nnn
                 for nnn in rows if nnn not in dirs]
    return findings, []


def check_root_strays(project, project_dir, ws):
    """(v) B4 — the project root holds only the Layout set (whitelist mirror:
    PROJECT_ROOT_FILES/DIRS in workflow-status.py); a stray gets flagged with the
    Layout homes to pick from."""
    findings = []
    for entry in sorted(os.listdir(project_dir)):
        if entry.startswith("."):
            continue
        path = os.path.join(project_dir, entry)
        if os.path.isdir(path):
            if entry in ws.PROJECT_ROOT_DIRS or re.match(r"\d{3}-", entry):
                continue
        elif entry in ws.PROJECT_ROOT_FILES:
            continue
        findings.append("root-stray: %s (homes: notes/ · investigations/ · legacy/)" % entry)
    return findings, []


def _deps_tokens(cell):
    """NNN edges only when the whole cell follows the Deps grammar (`NNN` tokens,
    optional parenthetical note); a free-text cell (`是 005 的前置`) yields no edges —
    digits inside prose are not dependency claims."""
    toks = [t for t in re.split(r"[,\s，、;；·]+", cell.strip())
            if t and t not in ("—", "-")]
    out = []
    for t in toks:
        m = re.fullmatch(r"(\d{3})(?:\([^)]*\)|（[^）]*）)?", t)
        if not m:
            return []
        out.append(m.group(1))
    return out


def check_board_monotonic(project, project_dir, ws):
    """(w) B5 — the machine-decidable board subset (021 D6): Deps acyclic ·
    整体状态 canonical (post markup-strip) · done ⇒ close-out review doc or skip note
    · done ⇒ test.md status ∈ TEST_STATUS_CANON's passing set. Old-format exempt."""
    text, new_format = _new_board_format(project_dir, ws)
    if not text:
        # index absence is (u)'s no-index finding — classified covered-by, not re-emitted
        return [], []
    if not new_format:
        return [], [], [("grandfathered", "old-format board")]
    rows = ws.board(project_dir)
    graph = {nnn: _deps_tokens(row.get("deps", "")) for nnn, row in rows.items()}
    findings = ["board-dep-cycle: " + " → ".join(p) for p in _dep_cycles(graph)]
    skips, exs = [], []

    dirs = {os.path.basename(d)[:3]: d
            for d in sorted(glob.glob(os.path.join(project_dir, "[0-9][0-9][0-9]-*")))
            if os.path.isdir(d)}
    for nnn, row in sorted(rows.items()):
        state = row.get("state", "")
        if not state:
            exs.append(("carrier-missing", "board row state empty"))
        elif state == "?":
            exs.append(("not-yet-due", "board row state '?'"))
        elif state not in ws.CANON_STATES:
            findings.append("board-state: %s '%s' non-canonical" % (nnn, state))
        if state != "done":
            exs.append(("not-yet-due", "not done, done-series off"))
            continue
        if nnn not in dirs:
            # a done row with no dir is (u)'s board-orphan-row finding — covered-by
            continue
        card = dirs[nnn]
        reviews = glob.glob(os.path.join(card, "notes", "review-*.md"))
        # whitespace-normalized: the skip-note phrase may wrap across lines
        ptext = " ".join(ws._read(os.path.join(card, "progress.md")).split())
        skip_note = "review skipped" in ptext or "pre-gate done" in ptext
        if not reviews and not skip_note:
            findings.append("board-done: %s done without close-out review/skip note" % nnn)
        # carrier-missing is a visible skip, not a silent pass (R9; 018 precedent:
        # an XS drill card may carry no test.md — review/skip-note owns close-out)
        if os.path.exists(os.path.join(card, "test.md")):
            tstatus = _doc_status(os.path.join(card, "test.md"), ws)
            if tstatus not in ws.TEST_STATUS_DONE_OK:
                findings.append("board-done: %s test.md status '%s' not in %s"
                                % (nnn, tstatus, "/".join(ws.TEST_STATUS_DONE_OK)))
        else:
            skips.append("board-monotonic: %s done without test.md" % nnn)
    return findings, skips, exs


# ---- doc-native block checks (026 slice 1): format core (ac) + git anchor (ad) ----

DOC_NATIVE_MODES = ("doc-native-pilot", "doc-native")   # pilot = 026 self-host; doc-native = post-collapse single track
ANCHOR_FIELDS = ("陈述", "类型", "why", "provenance", "depends-on")
# 026 slice 2 (T9): ask-id becomes mandatory by TIME BOUNDARY — a note whose gate
# date is on/after the cutoff must carry the ask-id slot (the pre-cutoff存量 stays
# optional; the carrier-existence predicate was refuted as a self-report escape
# hatch — grill-implement.md T8 lens receipt). Nine-column grill tables bind
# per-file from the same day (LLD-7 cutoff value fixed here).
ASK_ID_CUTOFF = "2026-08-27"
GRILL_NINECOL_CUTOFF = "2026-08-27"
TIER_VOCAB = ("照案", "真判", "拿不准")
UNSURE_ROUND_CAP = 5   # HLD-7 拿不准组规模阈值 (M6-calibrated)


def _dn_gate(card_dir, ws):
    """Shared (ac)/(ad) gating predicate: non-doc-native cards skip, visibly."""
    if ws.card_mode(card_dir) not in DOC_NATIVE_MODES:
        return [("not-yet-due", "mode not doc-native")]
    return None


def _git(card_dir, *args):
    """dev_root git call (workflow-status idiom: -C + timeout + except → None;
    callers turn None into a visible skip, never a pass)."""
    import subprocess
    try:
        return subprocess.run(["git", "-C", card_dir] + list(args),
                              capture_output=True, text=True, timeout=10)
    except Exception:
        return None


def check_block_format(card_dir, ws):
    """(ac) doc-native block format core: parse-class findings surfaced
    (bad-header / duplicate-id / bad-annotation — the caller-side hard stop,
    LLD-3); every approved-state block carries ≥1 valid approved annotation
    (mode + verbatim in place — E10; ask-id optional until the slice-2 归一);
    each approved annotation's date equals its gate commit's author date
    (lens4 D8). Unresolvable hashes are (ad)'s 历史不可达 — not re-judged here."""
    skip = _dn_gate(card_dir, ws)
    if skip:
        return [], [], skip
    blocks, findings = ws._block_parse().card_blocks(card_dir)
    findings, exs, dated, git_gone = list(findings), [], {}, False
    for bid, b in blocks.items():
        notes = [a for a in b["annotations"] if a["kind"] == "approved"]
        if b["state"] == "approved" and not notes:
            findings.append("approved-note-missing: %s" % bid)
        if not any(a["kind"] == "来源" for a in b["annotations"]):
            # (c6) 升格: authored blocks carry 类型 + provenance (transported ride 025's)
            for field in ("类型", "provenance"):
                if not b["fields"].get(field, "").strip():
                    findings.append("field-missing: %s %s" % (bid, field))
        for a in notes:
            h = a["extra"]["hash"]
            if h not in dated:
                out = _git(card_dir, "show", "-s", "--format=%ad",
                           "--date=format:%Y-%m-%d", h)
                if out is None:
                    git_gone = True
                dated[h] = (out.stdout.strip()
                            if out is not None and out.returncode == 0 else None)
            if dated[h] and dated[h] != a["extra"]["date"]:
                findings.append("note-date-mismatch: %s %s note %s vs commit %s"
                                % (bid, h[:12], a["extra"]["date"], dated[h]))
            if not a["extra"].get("ask_id") and a["extra"]["date"] >= ASK_ID_CUTOFF:
                # time-boundary mandate (T9): post-cutoff notes carry the ask-id
                # slot; the pre-cutoff存量 stays optional (LLD-2 过渡组)
                findings.append("ask-id-missing: %s gate %s (post-%s note)"
                                % (bid, h[:12], ASK_ID_CUTOFF))
            if dated[h] is None and not git_gone:
                # review #3: an unresolvable note hash with git alive is a
                # finding, never a silent pass (021 R9)
                findings.append("note-hash-unresolved: %s %s" % (bid, h[:12]))
        if b["annotations"] and b["annotations"][-1]["kind"] == "变更":
            # review #3 代际链 (HLD-3): an in-place rewrite ends with its
            # re-approve note — a trailing 变更 is a visibly pending state
            findings.append("pending-reapproval: %s (末注记为 变更，缺再批 approved)" % bid)
    if git_gone:
        exs.append(("carrier-missing", "git unavailable — note-date half skipped"))
    findings += _derived_status_findings(card_dir, ws, blocks)
    return findings, [], exs


BINDING_STATUS = {"requirement.md": ("confirmed",), "design.md": ("frozen", "approved"),
                  "detail.md": ("baseline",)}


def _derived_status_findings(card_dir, ws, blocks):
    """Review #2 (HLD-13(2) + the error-matrix hard-red row): on a doc whose
    frontmatter status carries binding force, a proposed block outside a
    「提议变更」section is a derived-status regression — the un-approve/rewrite
    shape the injection test proved invisible."""
    findings = []
    for doc, binding in BINDING_STATUS.items():
        path = os.path.join(card_dir, doc)
        status = ws.frontmatter(path).get("status", "").split("#")[0].strip()
        if status not in binding:
            continue
        text = ws._read(path)
        spans = []
        lines = text.split("\n")
        for i, ln in enumerate(lines):
            m = re.match(r"^(#+)\s.*提议变更", ln)
            if m:
                depth = len(m.group(1))
                j = i + 1
                while j < len(lines) and not re.match(r"^#{1,%d}\s" % depth, lines[j]):
                    j += 1
                spans.append((i + 1, j + 1))   # 1-based head_line range
        for bid, b in blocks.items():
            if b["doc"] != doc or b["state"] != "proposed":
                continue
            if any(a <= b["head_line"] < z for a, z in spans):
                continue
            findings.append("derived-status-regression: %s proposed under %s doc"
                            % (bid, status))
    return findings


def _file_created(card_dir, relpath):
    """First-commit author date (YYYY-MM-DD) of a card file, via dev_root git;
    None when git can't answer (callers classify, never pass silently)."""
    out = _git(card_dir, "log", "--reverse", "--format=%ad",
               "--date=format:%Y-%m-%d", "--", relpath)
    if out is None or out.returncode != 0 or not out.stdout.strip():
        return None
    return out.stdout.splitlines()[0].strip()


_ASK_ROW_ID = re.compile(r"^(?:Ask-|G)(\d+)$")


def _grill_rows_docnative(card_dir, ws):
    """Doc-native grill index: (rows, ninecol_files, legacy_files). Nine-column
    tables feed the full row (tier/round core); seven-column 存量 tables still
    feed id+status — the sweep's reverse-existence half must see them, or a
    batch-note row in a grandfathered file misreads as pruned (review #6)."""
    rows, ninecol, legacy = [], [], []
    for f in _grill_logs(card_dir):
        base = os.path.basename(f)
        has9 = False
        for header, trows in _canonical_tables(ws._read(f)):
            nine = "tier" in header and "round" in header
            has9 = has9 or nine
            idc = header.index("id")
            cols = {k: header.index(k)
                    for k in (("status", "tier", "round") if nine else ("status",))}
            for cells in trows:
                m = _ASK_ROW_ID.match(cells[idc].strip("`* ")) if idc < len(cells) else None
                if not m:
                    continue
                row = {"id": "Ask-" + m.group(1), "file": base, "nine": nine,
                       "tier": "", "round": ""}
                row.update({k: (cells[i].strip() if i < len(cells) else "")
                            for k, i in cols.items()})
                rows.append(row)
        (ninecol if has9 else legacy).append(base)
    return rows, ninecol, legacy


def check_grill_docnative(card_dir, ws):
    """(y) v2 — the doc-native branch (026 LLD-5 + Req-12 同批三核), nine-column
    rows only; legacy/doc-gate cards never reach here (mode gate in (y)):
    sweep: an approved note's ask-id whose grill row is still `open` →
    signature-open (transcribed-while-open, the 003 six-row hole); a noted id
    with no row is prune-legal — the block note is the回溯锚 (visible skip).
    tier 在场核: nine-col rows carry a closed-vocab tier and a positive round.
    batch-table rule: a round holding a 照案 batch table (≥2 照案 rows) must not
    hold a 真判 row (solo-and-batch legally share a gate round — freeze round 9
    shape — so mode↔tier is NOT 1:1; only the table form is the accident shape).
    拿不准 rows per (file, round) cap at UNSURE_ROUND_CAP (HLD-7).
    Nine-column era binds per-file: a doc-native grill file created on/after
    GRILL_NINECOL_CUTOFF must carry tier+round (older files grandfather)."""
    rows, ninecol, legacy = _grill_rows_docnative(card_dir, ws)
    findings, exs = [], []
    for base in legacy:
        created = _file_created(card_dir, os.path.join("notes", base))
        if created is None:
            exs.append(("carrier-missing", "%s: created date unknown, nine-col era unjudged" % base))
        elif created >= GRILL_NINECOL_CUTOFF:
            findings.append("column-drop: %s missing tier,round (nine-col era)" % base)
        else:
            exs.append(("grandfathered", "%s: pre-%s grill file" % (base, GRILL_NINECOL_CUTOFF)))
    groups = {}
    for r in rows:
        if not r["nine"]:
            continue   # 存量七列行只服务 reverse-existence，tier/round 核不追溯
        if r["tier"] not in TIER_VOCAB:
            findings.append("tier-vocab: %s tier '%s' (%s)" % (r["id"], r["tier"], r["file"]))
        if not re.fullmatch(r"[1-9]\d*", r["round"]):
            findings.append("round-invalid: %s round '%s' (%s)" % (r["id"], r["round"], r["file"]))
        groups.setdefault((r["file"], r["round"]), []).append(r)
    for (base, rnd), grp in sorted(groups.items()):
        ancase = [r for r in grp if r["tier"] == "照案"]
        if len(ancase) >= 2 and any(r["tier"] == "真判" for r in grp):
            findings.append("batch-round-tier2: %s round %s holds a 照案 table + 真判 row"
                            % (base, rnd))
        if sum(1 for r in grp if r["tier"] == "拿不准") > UNSURE_ROUND_CAP:
            findings.append("unsure-over-cap: %s round %s > %d"
                            % (base, rnd, UNSURE_ROUND_CAP))
    index = {r["id"]: r for r in rows}
    blocks, _ = ws._block_parse().card_blocks(card_dir)
    noted = {}
    for bid, b in blocks.items():
        for a in b["annotations"]:
            if a["kind"] == "approved" and a["extra"].get("ask_id"):
                m = _ASK_ROW_ID.match(a["extra"]["ask_id"])
                if m:
                    key = "Ask-" + m.group(1)
                    noted.setdefault(key, (bid, a["extra"]["mode"]))
    for aid, (bid, mode) in sorted(noted.items()):
        row = index.get(aid)
        if row is None:
            if mode == "batch":
                # HLD-14: a round row that carried a batch release may not be
                # pruned — the sweep's audit key would vanish with it (review #6)
                findings.append("batch-row-pruned: %s (noted in %s)" % (aid, bid))
            else:
                exs.append(("carrier-missing",
                            "%s not in grill rows — solo prune-legal, block %s note is the anchor"
                            % (aid, bid)))
        elif re.match(r"open\b", row["status"], re.I):
            findings.append("signature-open: %s noted in %s while row open" % (aid, bid))
    return findings, [], exs


EFFECT_ID = re.compile(r"^- \[[ x!]\] (Eff-\d+|E\d+)[::]", re.M)


def check_block_views(card_dir, ws):
    """(ae) doc-native citations & generated views (the crosscheck (c3)/(c5)/(c7)
    升格): bracket citations [Xxx-n] over the three phase docs resolve — block
    prefixes against card_blocks, Fact-n (and the transitional [F<n>] alias)
    against facts.md headers, Eff-n against the requirement Effect list; Ask-n
    citations are prune-legal (grill rows may be pruned — the (y) v2 anchor rule)
    and never findings. Every active Req block is covered by a "verifies" clause
    or opts out via a 验收随 disposition in its 陈述 (Effect coverage). The
    requirement's generated index between the index markers must equal
    render_index(blocks) byte-exactly (generated views are never hand-edited)."""
    skip = _dn_gate(card_dir, ws)
    if skip:
        return [], [], skip
    bp = ws._block_parse()
    blocks, _ = bp.card_blocks(card_dir)
    findings, exs = [], []
    texts = {}
    for name in ("requirement.md", "design.md", "detail.md"):
        texts[name] = ws._read(os.path.join(card_dir, name))
    alltext = "\n".join(texts.values())
    ftext = ws._read(os.path.join(card_dir, "facts.md"))
    fact_ids = set(re.findall(r"^### (?:Fact-|F)(\d+) ", ftext, re.M))  # 双记法（review #8）
    _edges, cycles = bp.deps_graph(blocks)   # (c)-equivalent for doc-native (review #8)
    findings += ["dep-cycle: " + " → ".join(p) for p in cycles]
    dead = {bid for bid, b in blocks.items() if b["state"] in ("superseded", "retired")}
    for bid, b in blocks.items():
        if b["state"] != "approved":
            continue
        cited = set(re.findall(r"\[((?:Req|HLD|LLD)-\d+)", "\n".join(b["fields"].values())))
        for c in sorted(cited & dead):
            findings.append("superseded-ref: %s cites %s (载重字段引已死块)" % (bid, c))
    eff_ids = set(EFFECT_ID.findall(texts["requirement.md"]))
    for pref, num, _clause in set(re.findall(
            r"(?<!:)\[(Req|HLD|LLD|Task|Ask|Fact|Eff|Crit|Layer)-(\d+)(-[a-z])?\]",
            alltext)):
        cid = "%s-%s" % (pref, num)
        if pref == "Fact":
            if num not in fact_ids:
                findings.append("dangling-cite: [%s] (facts.md)" % cid)
        elif pref == "Eff":
            if cid not in eff_ids:
                findings.append("dangling-cite: [%s] (Effect list)" % cid)
        elif pref == "Ask":
            continue  # prune-legal — block annotations are the anchor
        elif cid not in blocks:
            findings.append("dangling-cite: [%s]" % cid)
    for num in set(re.findall(r"\[F(\d+)\]", alltext)):
        if num not in fact_ids:
            findings.append("dangling-cite: [F%s] (facts.md alias)" % num)
    covered = set()
    for clause in re.findall(r"verifies ([^)]+)\)", texts["requirement.md"]):
        covered |= set(bp.expand_ranges(clause))
    for bid, b in blocks.items():
        if b["doc"] != "requirement.md" or b["state"] in ("superseded", "retired"):
            continue
        if bid not in covered and "验收随" not in b["fields"].get("陈述", ""):
            findings.append("effect-uncovered: %s (no verifies clause, no 验收随)" % bid)
    if ws.INDEX_BEGIN in texts["requirement.md"]:
        cur = texts["requirement.md"]
        cur = cur[cur.index(ws.INDEX_BEGIN): cur.index(ws.INDEX_END) + len(ws.INDEX_END)]
        if cur != ws.render_index(blocks):
            findings.append("index-stale: requirement 条目 index != render_index output")
    else:
        exs.append(("carrier-missing", "no generated index markers"))
    return findings, [], exs


def check_block_anchor(card_dir, ws):
    """(ad) git anchor core (LLD-4): per block with an approved annotation, the
    explicit baseline = last 变更 annotation's landing hash, else the last
    approved annotation's gate hash (first-approval receipts snapshots carry
    the approved text in proposed state — hence the proposed→approved state
    exemption; any other state change needs a same-batch 变更/退役 note).
    Compare face = the five load-bearing fields, field-by-field, working tree
    vs `git show <baseline>:<doc>` parsed in locate mode (titles optional in
    the HEAD grammar). Titles and annotation lines never compare. Failures:
    文本被改 / 历史不可达 / 基线处块缺席. One git show per (baseline, doc)."""
    skip = _dn_gate(card_dir, ws)
    if skip:
        return [], [], skip
    probe = _git(card_dir, "rev-parse", "--show-toplevel")
    if probe is None or probe.returncode != 0:
        return [], [], [("carrier-missing", "git unavailable/non-repo — anchor skipped")]
    top = os.path.realpath(probe.stdout.strip())   # macOS /var symlink alias
    bp = ws._block_parse()
    blocks, _ = bp.card_blocks(card_dir)   # parse findings are (ac)'s
    findings, exs, cache, ancestry = [], [], {}, {}
    for bid, b in blocks.items():
        approved = [a for a in b["annotations"] if a["kind"] == "approved"]
        if not approved:
            exs.append(("not-yet-due", "block-anchor: %s no approved note" % bid))
            continue
        changes = [a for a in b["annotations"] if a["kind"] == "变更"]
        base = (changes[-1] if changes else approved[-1])["extra"]["hash"]
        rel = os.path.relpath(
            os.path.realpath(os.path.join(card_dir, b["doc"])), top)
        key = (base, rel)
        if key not in cache:
            out = _git(card_dir, "show", "%s:%s" % (base, rel))
            if out is None or out.returncode != 0:
                cache[key] = None
            else:
                snap_blocks, _f = bp.parse_doc_blocks(out.stdout, doc=b["doc"])
                cache[key] = {"%s-%s" % (x["prefix"], x["num"]): x
                              for x in snap_blocks}
        snap = cache[key]
        if snap is None:
            findings.append("历史不可达: %s baseline %s:%s" % (bid, base[:12], rel))
            continue
        old = snap.get(bid)
        if old is None:
            findings.append("基线处块缺席: %s not at %s:%s" % (bid, base[:12], rel))
            continue
        if base not in ancestry:
            anc = _git(card_dir, "merge-base", "--is-ancestor", base, "HEAD")
            ancestry[base] = bool(anc is not None and anc.returncode == 0)
        if not ancestry[base]:
            # review #13 ([LLD-4] premise): a reachable object off HEAD's history
            # is not a legal baseline — forged-branch shape
            findings.append("历史不可达: %s baseline %s 非 HEAD 祖先" % (bid, base[:12]))
            continue
        for f in ANCHOR_FIELDS:
            if old["fields"].get(f, "") != b["fields"].get(f, ""):
                findings.append("文本被改: %s field %s vs baseline %s"
                                % (bid, f, base[:12]))
        if old["state"] != b["state"]:
            # review #1: the exemption is SAME-BATCH — the state-change event's
            # own 变更/退役 note must be the block's LAST annotation; a stale
            # historical note never grants a standing pass (TA-1, injection-proven)
            last_kind = b["annotations"][-1]["kind"] if b["annotations"] else None
            legal = ((old["state"] == "proposed" and b["state"] == "approved")
                     or last_kind in ("变更", "退役"))
            if not legal:
                findings.append("文本被改: %s state %s→%s without同批 变更/退役 note"
                                % (bid, old["state"], b["state"]))
    return findings, [], exs


# ---- long-cell hint (ag, 028): load-bearing slot length, report-only ----

LONG_CELL_CHARS = 120        # len() chars, never bytes (028 Fact-3); M6-calibrated
LONG_CELL_CUTOFF = "2026-08-29"   # landing day + 1 — grill rows are history, no backfill
LONG_CELL_DOCS = ("requirement.md", "design.md", "detail.md")


def _long_table_cells(text):
    """Fence-aware generic per-cell scan (028 HLD-1): (lineno, col, len) for every
    over-threshold data cell of every markdown table; a header naming `chosen`
    exempts that column (human-quote audit face, HLD-4)."""
    hits, fenced = [], False
    header, chosen_i = None, None
    for lineno, raw in enumerate(text.splitlines(), 1):
        ln = raw.strip()
        if ln.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if not ln.startswith("|"):
            header, chosen_i = None, None
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            chosen_i = header.index("chosen") if "chosen" in header else None
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        for i, cell in enumerate(cells):
            if i == chosen_i:
                continue
            if len(cell) > LONG_CELL_CHARS:
                hits.append((lineno, header[i] if i < len(header) else "col%d" % i,
                             len(cell)))
    return hits


def check_long_cells(card_dir, ws):
    """(ag) 028: over-long load-bearing slots — report-only hints on the skips
    stream (visible, never gates; the (k) gloss-hint precedent). Faces: table
    cells across the three card docs + notes/grill-*.md, plus single-line block
    field payloads on doc-native docs. Pre-gate activation per file:
    created >= LONG_CELL_CUTOFF; created unknown → carrier-missing."""
    hints, exs, live = [], [], set()
    files = [n for n in LONG_CELL_DOCS
             if os.path.exists(os.path.join(card_dir, n))]
    files += sorted(os.path.relpath(f, card_dir).replace(os.sep, "/") for f in
                    glob.glob(os.path.join(card_dir, "notes", "grill-*.md")))
    for rel in files:
        created = _file_created(card_dir, rel)
        if created is None:
            exs.append(("carrier-missing",
                        "%s: created date unknown, long-cell era unjudged" % rel))
            continue
        if created < LONG_CELL_CUTOFF:
            exs.append(("grandfathered", "%s: pre-%s long-cell" % (rel, LONG_CELL_CUTOFF)))
            continue
        live.add(rel)
        try:
            with open(os.path.join(card_dir, rel), encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        for lineno, col, n in _long_table_cells(text):
            hints.append("long-cell: %s line %d %s列 — %d字符" % (rel, lineno, col, n))
    if ws.card_mode(card_dir) in DOC_NATIVE_MODES:
        blocks, _ = ws._block_parse().card_blocks(card_dir)
        for bid, b in blocks.items():
            if b["doc"] not in live:
                continue   # pre-cutoff/unknown docs already classified above
            for fname, val in b["fields"].items():
                if "\n" not in val and len(val) > LONG_CELL_CHARS:
                    hints.append("long-cell: %s %s field %s — %d字符"
                                 % (b["doc"], bid, fname, len(val)))
    return [], hints, exs


# ---- check registry & runners (the L3 entry surface) ----
# Each entry: (id, fn(project, card_dir, ws) -> (findings, skips)). A skip carries its
# reason and never affects the exit code; a check whose carrier predicate doesn't fire
# returns ([], []). Contract invariants (design 021): per-check exception isolation —
# a raising check contributes `check-error:<id>` to findings and the rest still run;
# a check never emits both a finding and a skip for the same condition.

# Registry meta (026 HLD-11): the manifest's SoT rides the registry rows — fields
# 查什么 / 何时跑 / 机械或判断 / 依据 / 去向; `--manifest` renders them, a row with
# no meta renders META-MISSING (E5's 全行齐 enforcement).
def _m(letter, what, when, basis, disp="保留", nature="机械", misfire="既有套件"):
    return {"letter": letter, "what": what, "when": when, "nature": nature,
            "basis": basis, "disp": disp, "misfire": misfire}


CARD_CHECKS = (
    # signature adapters only — each function owns its full return shape
    ("design-sections", lambda p, c, ws: check_design_sections(c, ws),
     _m("(f)", "design.md 必备节在场", "design 在场", "011")),
    ("fact-markers", lambda p, c, ws: check_fact_markers(c, ws),
     _m("(g)", "facts VERIFIED 标注↔来源一致（Fact-/F 双记法）", "facts.md 在场", "010/026")),
    ("part-consistency", lambda p, c, ws: check_part_consistency(c, ws),
     _m("(h)", "plan Part 值 ⊆ design Parts 表", "新格式 Parts 表在场", "015")),
    ("governance", lambda p, c, ws: check_governance(c, ws),
     _m("(i)", "governance 字段值域/级联", "cutoff 后卡", "017/026")),
    ("ledger", lambda p, c, ws: check_ledger(c, ws),
     _m("(a)-(e)", "账本 id/派生状态/环/注记形/单活块", "ledger 存量卡",
        "010", disp="存量保留（doc-native 无账本，(ac)/(ad) 接棒）")),
    ("transcription-marker", check_transcription_markers,
     _m("(j)", "落纸补充 marker 过 gate 清零", "gate 后 doc", "021")),
    ("grill-reverse", check_grill_reverse,
     _m("(k)", "grill 表形/notation + resolved 反向存在", "022 cutoff 后", "022")),
    ("panel-receipts", check_panel_receipts,
     _m("(l)", "receipt 块在场 + 结构核（premises/suspicions）", "gate 过卡", "021/024")),
    ("docgate-gateline", check_docgate_gateline,
     _m("(m)", "doc-gate 卡 gate 行", "doc-gate 卡", "017")),
    ("supersede-residue", check_supersede_residue,
     _m("(n)", "被取代表述驻留扫描", "锚在场", "021")),
    ("links", check_links,
     _m("(o)", "链接/wikilink 解析（卡半）", "always", "021")),
    ("status-field", check_status_field,
     _m("(p)", "frontmatter status 在场/值域", "doc 在场", "021")),
    ("r-trace", check_r_trace,
     _m("(q)", "R-id 四维 trace（R/Req 双记法；doc-native 生成索引作条目源）",
        "条目在场；下游维 cutoff 后", "021/026")),
    ("fact-refs", check_fact_refs,
     _m("(r)", "[F/Fact/NNN:F] 引用解析", "phase doc 在场", "021/026")),
    ("progress-cap", check_progress_cap,
     _m("(s)", "progress 行数帽（活卡）", "活卡", "021")),
    ("adr-hygiene", check_adr_hygiene,
     _m("(t)", "ADR Status 词/Supersedes 形", "adr/ 在场", "021")),
    ("ledger-rows", check_ledger_rows,
     _m("(x)", "doc↔账本行级一致（双写比对）", "ledger 存量卡",
        "024", disp="存量保留（doc-native 单写面无此税——结构性消解）")),
    ("grill-signature", check_grill_signature,
     _m("(y)", "签名闭合：legacy=人工共位键 v1；doc-native=ask-id 键 v2 + tier/round 核 + batch-prune 禁",
        "cutoff 后卡", "024/026", misfire="DocNativeGrillV2/ReviewFixesC")),
    ("home-pointer", check_home_pointer,
     _m("(z)", "归宿 cell 行级解析", "028 cutoff 后 frozen 卡", "028")),
    ("req-handoff", check_req_handoff,
     _m("(aa)", "需求条目 handoff 载体（provenance 列夹带）", "条目在场", "028")),
    ("detail-disposition", check_detail_disposition,
     _m("(ab)", "设计 freeze 后详设处置在案", "frozen 在卡", "029")),
    ("block-format", lambda p, c, ws: check_block_format(c, ws),
     _m("(ac)", "block 文法/注记五类/E10 在场/日期核/ask-id 时间界/字段在场/derived-status/代际链（(c2)(c6)(c8) 升格）",
        "doc-native 卡", "026 LLD-2", misfire="DocNativeBlockChecks/ReviewFixes")),
    ("block-anchor", lambda p, c, ws: check_block_anchor(c, ws),
     _m("(ad)", "已批块显式基线锚定核（三分类 + 同批豁免 + 祖先判）", "doc-native 卡",
        "026 LLD-4", misfire="DocNativeReviewFixes（注入五景）")),
    ("block-views", lambda p, c, ws: check_block_views(c, ws),
     _m("(ae)", "引用解析/Effect 覆盖/生成索引一致/环/死引（(c3)(c5)(c7) 升格 + (a)(c) 等价）",
        "doc-native 卡", "026 T14", misfire="DocNativeBlockViews")),
    ("long-cell", lambda p, c, ws: check_long_cells(c, ws),
     _m("(ag)", "载重格位超长单行 hint（表格 cell/block 单行字段 >120 字符；skips 流不 gate；(af) 留给 plan 勾选单调核候选）",
        "cutoff 后文件（created-only）", "card 028", misfire="LongCellHint")),
)

PROJECT_CHECKS = (
    ("links", check_project_links,
     _m("(o)", "链接解析（项目半）", "always", "021")),
    ("board-rows", check_board_rows,
     _m("(u)", "看板行↔卡目录双向", "always", "021")),
    ("root-strays", check_root_strays,
     _m("(v)", "项目根杂散文件", "always", "021")),
    ("board-monotonic", check_board_monotonic,
     _m("(w)", "看板机器子集（环/状态词/done 系列）", "新格式看板", "021")),
)

# Non-registry manifest rows (026 Req-36): the crosscheck family's dispositions +
# the six roadmap absorption candidates — each lands or explicitly rolls back.
EXTRA_MANIFEST = (
    ("crosscheck (c1)", "退役 → (i)/(p) 覆盖（frontmatter 核）"),
    ("crosscheck (c2)", "退役 → (ac) parse findings（升格）"),
    ("crosscheck (c3)", "退役 → (ae) dangling-cite（升格）"),
    ("crosscheck (c4)", "卡内保留至 026 收口（025 archive frozen-hash——本卡专属），随卡退役归档"),
    ("crosscheck (c5)", "退役 → (ae) effect-uncovered（升格）"),
    ("crosscheck (c6)", "退役 → (ac) field-missing（升格）"),
    ("crosscheck (c7)", "退役 → (ae) index-stale（升格；render_index 已迁 workflow-status）"),
    ("crosscheck (c8)", "退役 → (ac) bad-header（升格）"),
    ("APPROVE_NOTE 正则", "存量保留（check_ledger (d) 用）；doc-native 域由 block_parse 文法接管"),
    ("护栏 2 手工 digest", "退役 → --digest 生成器（026 T7）"),
    ("roadmap: check-code-refs ledger-id 缺口", "落地（COMMENT_PATTERNS += 卡上下文 id 引用，026 T14）"),
    ("roadmap: trace loose 匹配收紧", "显式回退——观察困扰频次（roadmap 原判据，无表决面）"),
    ("roadmap: R-id 整行扫描并入括号 id", "显式回退——随 loose 收紧同判观察"),
    ("roadmap: 存量账本 findings 语义张力", "化解——doc-native 单写面下无双写张力（新轨结构性消解）"),
    ("roadmap: 载体在但契约不判 5 处升 finding", "显式回退——升 finding 需独立裁（023 R5/Out 禁动判定逻辑）"),
    ("roadmap: M3 脚本化", "落地——(a)-(ae) 检查族 + --manifest 即其形（026）"),
)


def _normalize(res):
    """Return-shape adapter: bare findings list / (findings, skips) /
    (findings, skips, exemptions) all normalize to the 3-tuple — incremental
    migration stays legal, the two legacy streams' content untouched."""
    if isinstance(res, list):
        return res, [], []
    if len(res) == 2:
        return res[0], res[1], []
    return res


def _run_entries(entries, args, ws):
    findings, skips, exemptions = [], [], []
    for cid, fn, *_meta in entries:
        try:
            f, s, exs = _normalize(fn(*args, ws))
        except Exception as e:
            findings.append("check-error:%s: %s" % (cid, e))
            continue
        findings += f
        skips += s
        exemptions += [(cls, cid, reason) for cls, reason in exs]
    return findings, skips, exemptions


def check_card_all(project, card_dir, ws):
    """All card-scoped checks, per-check isolated. Returns (findings, skips,
    exemptions); card attribution rides the record's fields, never a string
    prefix (the skips stream keeps its prefix behavior)."""
    findings, skips, raw = _run_entries(CARD_CHECKS, (project, card_dir), ws)
    base = os.path.basename(card_dir.rstrip("/"))
    gated = any(True for _ in _gated_docs(card_dir, ws))
    exemptions = [Exemption(cls, check, reason, "card", base, gated)
                  for cls, check, reason in raw]
    return findings, skips, exemptions


def check_project(project, project_dir, ws):
    """Project scope: project-level checks + every card's card-scoped set (the
    full-sweep form R8's 存量全量跑 runs on). Card rows are prefixed with their
    dir name so a sweep finding stays attributable."""
    findings, skips, raw = _run_entries(PROJECT_CHECKS, (project, project_dir), ws)
    exemptions = [Exemption(cls, check, reason, "project", "", True)
                  for cls, check, reason in raw]
    for card_dir in sorted(glob.glob(os.path.join(project_dir, "[0-9][0-9][0-9]-*"))):
        if not os.path.isdir(card_dir):
            continue
        base = os.path.basename(card_dir)
        f, s, e = check_card_all(project, card_dir, ws)
        findings += ["%s: %s" % (base, x) for x in f]
        skips += ["%s: %s" % (base, x) for x in s]
        exemptions += e
    return findings, skips, exemptions
