#!/usr/bin/env python3
"""workflow-checks.py — the deterministic check domain (L2 of the status/checks split).

Check implementations behind `workflow-status.py --check`: the ledger checks (a)-(e),
design required sections (f), fact markers (g), part consistency (h), governance
mode (i). workflow-status.py remains the parsing layer + CLI entry and lazy-loads
this module; every public function takes `ws` = a live view of the workflow-status
module (one-way dependency: checks read the parsing layer, never the reverse).

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
FACT_HEAD = re.compile(r"^###\s+(F\d+)\s+\[([^\]]+)\]", re.M)
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


def check_ledger(card_dir, ws):
    """The ledger checks (a)–(e); semantic contradiction stays M3 judgment.
    No decisions.md → no findings (old-card semantics, never flagged); the absence
    classifies by governance mode — a doc-gate card forbids the carrier (its
    presence is the finding), a ledger card truly lacks it, a legacy card predates
    the mechanism."""
    if not os.path.exists(os.path.join(card_dir, "decisions.md")):
        mode = ws.card_mode(card_dir)
        if mode == "doc-gate":
            return [], [], [("not-yet-due",
                             "doc-gate card, ledger is a forbidden carrier")]
        if mode == "ledger":
            return [], [], [("carrier-missing", "ledger card without decisions.md")]
        return [], [], [("grandfathered", "legacy card without decisions.md")]
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
    """Card created date, format-guarded like (i2): malformed values normalize to ""
    so every caller's no-created-date branch owns them — a bare string compare on a
    malformed date (e.g. "2026-8-1") would otherwise mis-bucket the card around its
    cutoff."""
    created = str(ws.frontmatter(os.path.join(card_dir, "requirement.md")).get("created", ""))
    return created if re.match(r"\d{4}-\d{2}-\d{2}", created) else ""


def _grill_logs(card_dir):
    return sorted(glob.glob(os.path.join(card_dir, "notes", "grill-*.md")))


def check_transcription_markers(project, card_dir, ws):
    """(j) A1 — gate form only: a doc whose status passed its gate carries zero exact
    （落纸补充） markers (approve clears them; mid-flight placement stays M3 judgment)."""
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


def _grill_resolved_ids(text):
    """(canonical?, ids): canonical grill-log table = header row with both `id` and
    `status` columns (grill.md's seven-column form); ids = ledger-id targets of
    `resolved → <id>` status cells. Non-id targets (doc-§ form) stay judgment."""
    canonical, ids, lines, i = False, set(), text.splitlines(), 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("|"):
            header = [c.strip().lower() for c in ln.strip("|").split("|")]
            if "id" in header and "status" in header:
                canonical = True
                st = header.index("status")
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    if len(cells) > st and "resolved" in cells[st]:
                        ids |= {m.group(1)
                                for m in GRILL_RESOLVED_ID.finditer(cells[st])}
                    i += 1
                continue
        i += 1
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
                              if gov == "doc-gate" else True)
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
    if shape_era and gov not in ("ledger", "doc-gate"):
        exs.append(("not-yet-due", "legacy governance, notation not judged"))
    findings, ids, noncanon = [], set(), 0
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
    if not shape_era and noncanon == len(logs):
        # aggregation-only early return — no new emission point
        return [], [], exs
    if ids and not os.path.exists(os.path.join(card_dir, "decisions.md")):
        # canonical table on a ledger-less card: no home to check against (#13)
        return findings, ["grill-reverse: no-ledger for resolved ids"], exs
    blocks = {b["id"] for b in ws.parse_ledger(card_dir)[0]}
    return (findings + ["resolved-no-home: " + i for i in sorted(ids - blocks)],
            [], exs)


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
            m = _PREMISE_VALUE.search(scan)
            if not m:
                findings.append("receipt-bad-premises: %s" % label)
            elif m.group(1) == "facts-pack" and not re.search(r"\[F\d+\]", scan):
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
        mode = ws.card_mode(card_dir)
        if mode == "doc-gate":
            return [], [], [("not-yet-due",
                             "doc-gate card, ledger is a forbidden carrier")]
        if mode == "ledger":
            return [], [], [("carrier-missing", "ledger card without decisions.md")]
        return [], [], [("grandfathered", "legacy card without decisions.md")]
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
_GID = re.compile(r"G\d+(?:[a-z]|\.\d+)?")
_GID_RANGE = re.compile(r"G(\d+)\s*[–-]\s*G?(\d+)\b")


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
    table in the card's grill-logs (G ids are card-unique). Canonical judgment is
    _grill_resolved_ids' header criterion (id + status columns) — no second
    definition; the header's own column positions supply the cells."""
    index, any_canonical = {}, False
    for f in _grill_logs(card_dir):
        lines = ws._read(f).splitlines()
        i = 0
        while i < len(lines):
            ln = lines[i].strip()
            if ln.startswith("|"):
                header = [c.strip().lower() for c in ln.strip("|").split("|")]
                if "id" in header and "status" in header:
                    any_canonical = True
                    st, ch = header.index("status"), (header.index("chosen")
                                                      if "chosen" in header else -1)
                    idc = header.index("id")
                    i += 1
                    while i < len(lines) and lines[i].strip().startswith("|"):
                        cells = [c.strip() for c in
                                 lines[i].strip().strip("|").split("|")]
                        gid = cells[idc].strip("`* ") if idc < len(cells) else ""
                        if _GID.fullmatch(gid):
                            index.setdefault(gid, {
                                "status": cells[st] if st < len(cells) else "",
                                "chosen": cells[ch] if 0 <= ch < len(cells) else ""})
                        i += 1
                    continue
            i += 1
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
    Mode-agnostic; created-only pre-gate predicate."""
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
            if "人工" not in line or _accounting_line(line, ws):
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
_PAREN_COUNT = re.compile(r"（\s*(\d+|[一二三四五六七八九十])\s*[类条项处种个]）")
_CJK_NUM = {c: i for i, c in enumerate("零一二三四五六七八九十")}
_LIST_RUN = re.compile(r"[^、／（）：:；;。|]+(?:[、／][^、／（）：:；;。|]+)+")


def _weight_tokens(cell):
    """Digit + Chinese-numeral runs from a statement cell; inline code spans and
    R-id forms stripped first (an id's digits are not a weight claim — 003 原型)."""
    scan = re.sub(r"\bR\d+\b", "", _INLINE_CODE_SPAN.sub("", cell))
    return _WEIGHT_TOKEN.findall(scan)


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
FREF = re.compile(r"\[F(\d+)\]")
XFREF = re.compile(r"\[(\d{3}):F(\d+)\]")   # cross-card form [NNN:F<n>] (021 D4)
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
    for r in sorted(set(reqs) | set(home) | by_r | set(cov), key=lambda x: int(x[1:])):
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
    return findings, [], exs


# existence harvest is marker-agnostic (012-era heads carry no [marker]); a head naming
# superseded/retired is excluded either way — marker INTEGRITY stays (g)'s job
FACT_HEAD_ANY = re.compile(r"^###\s+F(\d+)\b(.*)$", re.M)


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


# ---- check registry & runners (the L3 entry surface) ----
# Each entry: (id, fn(project, card_dir, ws) -> (findings, skips)). A skip carries its
# reason and never affects the exit code; a check whose carrier predicate doesn't fire
# returns ([], []). Contract invariants (design 021): per-check exception isolation —
# a raising check contributes `check-error:<id>` to findings and the rest still run;
# a check never emits both a finding and a skip for the same condition.

CARD_CHECKS = (
    # signature adapters only — each function owns its full return shape
    ("design-sections", lambda p, c, ws: check_design_sections(c, ws)),
    ("fact-markers", lambda p, c, ws: check_fact_markers(c, ws)),
    ("part-consistency", lambda p, c, ws: check_part_consistency(c, ws)),
    ("governance", lambda p, c, ws: check_governance(c, ws)),
    ("ledger", lambda p, c, ws: check_ledger(c, ws)),
    ("transcription-marker", check_transcription_markers),      # (j) A1
    ("grill-reverse", check_grill_reverse),                     # (k) A2
    ("panel-receipts", check_panel_receipts),                   # (l) A3
    ("docgate-gateline", check_docgate_gateline),               # (m) A5
    ("supersede-residue", check_supersede_residue),             # (n) A4′
    ("links", check_links),                                     # (o) B1 card half
    ("status-field", check_status_field),                       # (p) B2′
    ("r-trace", check_r_trace),                                 # (q) B6
    ("fact-refs", check_fact_refs),                             # (r) B7
    ("progress-cap", check_progress_cap),                       # (s) B8
    ("adr-hygiene", check_adr_hygiene),                         # (t) C4
    ("ledger-rows", check_ledger_rows),                         # (x) 024
    ("grill-signature", check_grill_signature),                 # (y) 024
)

PROJECT_CHECKS = (
    ("links", check_project_links),                             # (o) B1 project half
    ("board-rows", check_board_rows),                           # (u) B3
    ("root-strays", check_root_strays),                         # (v) B4
    ("board-monotonic", check_board_monotonic),                 # (w) B5
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
    for cid, fn in entries:
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
