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
    findings += ["dep-cycle: " + " → ".join(p) for p in _dep_cycles(graph)]

    for b in blocks:                                                          # (d)
        if b["state"] == "approved" and not APPROVE_NOTE.search(b["body"]):
            findings.append("bad-approve-note: " + b["id"])
    return findings


# ---- (j)-(m): gate-adjacent checks (021 T3) ----
GATED_DOCS = (("requirement.md", ("confirmed",)),
              ("design.md", ("frozen", "approved")),
              ("detail.md", ("baseline",)))
# Exact full-width literal; self-documenting variants (「落纸补充」,（落纸补充标记）) don't
# match, and backtick-quoted mentions are stripped before counting (mention ≠ use).
TRANSCRIPTION_MARKER = "（落纸补充）"
DISCUSSION_FIRST_CUTOFF = "2026-08-11"   # 019: grill-log mandatory-persist start
RECEIPT_STRUCT_CUTOFF = "2026-08-17"     # 021 landing: structural anchor required from here
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
    return str(ws.frontmatter(os.path.join(card_dir, "requirement.md")).get("created", ""))


def _grill_logs(card_dir):
    return sorted(glob.glob(os.path.join(card_dir, "notes", "grill-*.md")))


def check_transcription_markers(project, card_dir, ws):
    """(j) A1 — gate form only: a doc whose status passed its gate carries zero exact
    （落纸补充） markers (approve clears them; mid-flight placement stays M3 judgment)."""
    findings = []
    for name, path in _gated_docs(card_dir, ws):
        n = _strip_code(ws._read(path)).count(TRANSCRIPTION_MARKER)
        if n:
            findings.append("stray-marker: %s %d×%s past gate"
                            % (name, n, TRANSCRIPTION_MARKER))
    return findings, []


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


def check_grill_reverse(project, card_dir, ws):
    """(k) A2 — transcription reverse fidelity, canonical-table form only: every
    grill-log `resolved → <ledger-id>` row has a decisions.md block (any state —
    existence, not approval). Other table shapes skip (021 freeze panel: three
    incompatible shapes in the wild; the format contract is deferred)."""
    created = _card_created(card_dir, ws)
    if not created or created < DISCUSSION_FIRST_CUTOFF:
        return [], ["grill-reverse: pre-%s card" % DISCUSSION_FIRST_CUTOFF]
    logs = _grill_logs(card_dir)
    if not logs:
        return [], ["grill-reverse: no-grill-log"]
    canonical, ids = False, set()
    for f in logs:
        c, s = _grill_resolved_ids(ws._read(f))
        canonical |= c
        ids |= s
    if not canonical:
        return [], ["grill-reverse: non-canonical-grill-log"]
    blocks = {b["id"] for b in ws.parse_ledger(card_dir)[0]}
    return ["resolved-no-home: " + i for i in sorted(ids - blocks)], []


def check_panel_receipts(project, card_dir, ws):
    """(l) A3 — receipt presence: a card that passed any gate and keeps a grill-log
    must hold ≥1 receipt block; zero blocks = self-certified gate, the primary
    failure. Structural anchor from RECEIPT_STRUCT_CUTOFF on; earlier cards judged
    by the loose word anchor (their receipts predate the pinned form)."""
    created = _card_created(card_dir, ws)
    if not created or created < DISCUSSION_FIRST_CUTOFF:
        return [], ["panel-receipts: pre-%s card" % DISCUSSION_FIRST_CUTOFF]
    if not any(True for _ in _gated_docs(card_dir, ws)):
        return [], []
    logs = _grill_logs(card_dir)
    if not logs:
        return [], ["panel-receipts: no-grill-log"]
    anchor = RECEIPT_ANCHOR if created >= RECEIPT_STRUCT_CUTOFF else RECEIPT_LOOSE
    if any(anchor.search(ws._read(f)) for f in logs):
        return [], []
    return ["no-receipts: gated card, grill-log without receipt block"], []


def check_docgate_gateline(project, card_dir, ws):
    """(m) A5 — doc-gate audit anchor: each gated doc carries a `（gate <hash>）`
    Change-log line (017 S4); detail.md's container is its Change-notes section so
    only the pattern is required there."""
    if ws.card_mode(card_dir) != "doc-gate":
        return [], []
    findings = []
    for name, path in _gated_docs(card_dir, ws):
        text = ws._read(path)
        if name != "detail.md" and not ws._section(text, r"Change log"):
            findings.append("no-changelog-section: " + name)
            continue
        if not GATE_LINE.search(text):
            findings.append("no-gate-line: " + name)
    return findings, []


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
    history quotes of old phrasing are exempt (omission-check的 supersede 项)."""
    for pat in (r"Change log", r"Change notes"):
        sect = ws._section(text, pat)
        if sect:
            text = text.replace(sect, "\n" * sect.count("\n"))
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
        if _csp().terms_from_card(card_dir) != ([], []):
            return [], ["supersede-residue: pre-021 anchors (one-shot swept at their M2)"]
        return [], []
    terms, findings = _csp().terms_from_card(card_dir)
    if not terms:
        return findings, []
    for name in SWEEP_DOCS:
        text = ws._read(os.path.join(card_dir, name))
        if not text:
            continue
        for i, line in enumerate(_mask_history(text, ws).splitlines(), 1):
            for t in terms:
                if t in line:
                    findings.append("superseded-phrase: %s:%d [%s]" % (name, i, t))
    return findings, []


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


def _kb_root():
    cfg = os.path.expanduser("~/.config/xg-knowledge-wiki/config.yaml")
    try:
        for line in open(cfg, encoding="utf-8"):
            m = re.match(r"root:\s*(\S+)", line)
            if m:
                return os.path.expanduser(m.group(1).strip().strip("\"'"))
    except OSError:
        pass
    return os.path.expanduser("~/knowledge")


def _kb_resolves(kb, target):
    """kb/<layer>/<project>/<slug>(.md) exists, or an aliases: frontmatter names the slug."""
    if os.path.exists(os.path.join(kb, target + ".md")) or \
       os.path.exists(os.path.join(kb, target)):
        return True
    parent, slug = os.path.split(target.rstrip("/"))
    for f in glob.glob(os.path.join(kb, parent, "*.md")):
        aliases = ""
        try:
            for line in open(f, encoding="utf-8"):
                m = re.match(r"aliases:\s*(.+)", line)
                if m:
                    aliases = m.group(1)
                    break
        except OSError:
            continue
        if slug in [a.strip().strip("\"'") for a in aliases.strip("[]").split(",")]:
            return True
    return False


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


def _doc_links(card_dir, ws):
    """Per doc: (wikilink targets, relative link paths), code-stripped."""
    for name in PHASE_DOC_NAMES:
        text = ws._read(os.path.join(card_dir, name))
        if not text:
            continue
        stripped = _strip_code(text)
        yield name, _wiki_targets(stripped), _rel_targets(stripped)


def check_links(project, card_dir, ws):
    """(o) B1 card half — every [[wikilink]] resolves in the KB (aliases honored),
    every relative link resolves on disk. KB root unreachable ⇒ the whole check
    skips (never a partial finding+skip mix)."""
    kb = _kb_root()
    if not os.path.isdir(kb):
        return [], ["links: no-kb-root"]
    findings = []
    for name, wikis, rels in _doc_links(card_dir, ws):
        for t in wikis:
            if not _kb_resolves(kb, t):
                findings.append("broken-wikilink: %s [[%s]]" % (name, t))
        for p in rels:
            if not os.path.exists(os.path.normpath(os.path.join(card_dir, p))):
                findings.append("broken-link: %s %s" % (name, p))
    return findings, []


def check_status_field(project, card_dir, ws):
    """(p) B2′ — every existing phase doc declares frontmatter `status` (the one
    machine-read field left after `updated:` was dropped, 021 R4)."""
    findings = []
    for name in PHASE_DOC_NAMES:
        path = os.path.join(card_dir, name)
        if os.path.exists(path) and not ws.frontmatter(path).get("status"):
            findings.append("missing-status: " + name)
    return findings, []


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
        return [], []
    downstream = _card_created(card_dir, ws) >= TRACE_CUTOFF
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
    return findings, []


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
        sect = ws._section(ws._read(os.path.join(card_dir, name)), r"事实清单")
        ids |= {int(n) for n in re.findall(r"\bF(\d+)\b", sect)}
    return ids


def check_fact_refs(project, card_dir, ws):
    """(r) B7 — [F<n>] citations resolve: bare form against THIS card's active facts
    (facts.md ∪ doc-local 事实清单); cross-card [NNN:F<n>] (021 D4) against the target
    card's fact carriers. A citation with no carrier anywhere is a finding — the
    non-silent form R9 assigns this check."""
    own = None   # lazy — most docs have no refs
    findings = []
    for name in PHASE_DOC_NAMES:
        text = ws._read(os.path.join(card_dir, name))
        if not text:
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
    return findings, []


def check_progress_cap(project, card_dir, ws):
    """(s) B8 — progress.md stays a snapshot: over-cap flags on live cards only
    (done/dropped cards' prune duty ended with the card, 021 D5)."""
    path = os.path.join(card_dir, "progress.md")
    if not os.path.exists(path):
        return [], []
    state = ws.board(os.path.dirname(card_dir)).get(
        os.path.basename(card_dir)[:3], {}).get("state", "").strip("*").strip()
    if state in ("done", "dropped"):
        return [], []
    n = ws._read(path).count("\n") + 1
    if n > PROGRESS_CAP:
        return ["progress-over-cap: %d lines (cap %d)" % (n, PROGRESS_CAP)], []
    return [], []


def check_adr_hygiene(project, card_dir, ws):
    """(t) C4 — ADR hygiene: no `## Amendment` block (changes are superseding ADRs);
    body ≤ ADR_BODY_CAP lines; a superseded ADR keeps ≤2 lines referencing its
    superseder (the forward pointer, not a running commentary)."""
    findings = []
    for f in sorted(glob.glob(os.path.join(card_dir, "adr", "*.md"))):
        base = "adr/" + os.path.basename(f)
        text = ws._read(f)
        if re.search(r"^##\s*Amendment", text, re.M):
            findings.append("adr-amendment: " + base)
        n = text.count("\n") + 1
        if n > ADR_BODY_CAP:
            findings.append("adr-over-cap: %s %d lines (cap %d)" % (base, n, ADR_BODY_CAP))
        m = re.search(r"^Status:\s*superseded\s*(?:by\s*(ADR-\d{4}))?", text, re.M | re.I)
        if m and m.group(1):
            refs = sum(1 for ln in text.splitlines() if m.group(1) in ln)
            if refs > 2:
                findings.append("adr-forward-ref: %s %d lines cite %s"
                                % (base, refs, m.group(1)))
    return findings, []


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
        return [], ["links: no-kb-root"]
    findings = []
    for name in ("index.md", "roadmap.md"):
        text = ws._read(os.path.join(project_dir, name))
        if not text:
            continue
        stripped = _strip_code(text)
        for t in _wiki_targets(stripped):
            if not _kb_resolves(kb, t):
                findings.append("broken-wikilink: %s [[%s]]" % (name, t))
        for p in _rel_targets(stripped):
            if not os.path.exists(os.path.normpath(os.path.join(project_dir, p))):
                findings.append("broken-link: %s %s" % (name, p))
    return findings, []


def check_board_rows(project, project_dir, ws):
    """(u) B3 — card dir ↔ board row, both directions (the missing-row degradation
    iter_cards already computes, promoted to findings). Old-format boards exempt."""
    text, new_format = _new_board_format(project_dir, ws)
    if not text:
        return ["no-index: index.md missing"], []
    if not new_format:
        return [], []
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
    toks = [t for t in re.split(r"[,\s，、;；]+", cell.strip())
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
    if not text or not new_format:
        return [], []
    rows = ws.board(project_dir)
    graph = {nnn: _deps_tokens(row.get("deps", "")) for nnn, row in rows.items()}
    findings = ["board-dep-cycle: " + " → ".join(p) for p in _dep_cycles(graph)]

    dirs = {os.path.basename(d)[:3]: d
            for d in sorted(glob.glob(os.path.join(project_dir, "[0-9][0-9][0-9]-*")))
            if os.path.isdir(d)}
    for nnn, row in sorted(rows.items()):
        state = row.get("state", "")
        if state and state != "?" and state not in ws.CANON_STATES:
            findings.append("board-state: %s '%s' non-canonical" % (nnn, state))
        if state != "done" or nnn not in dirs:
            continue
        card = dirs[nnn]
        reviews = glob.glob(os.path.join(card, "notes", "review-*.md"))
        ptext = ws._read(os.path.join(card, "progress.md"))
        skip_note = "review skipped" in ptext or "pre-gate done" in ptext
        if not reviews and not skip_note:
            findings.append("board-done: %s done without close-out review/skip note" % nnn)
        # existence-qualified (018 precedent: an XS drill card may carry no test.md at
        # all — the review/skip-note constraint above owns close-out discipline)
        if os.path.exists(os.path.join(card, "test.md")):
            tstatus = _doc_status(os.path.join(card, "test.md"), ws)
            if tstatus not in ("passing", "described"):
                findings.append("board-done: %s test.md status '%s' not in (passing, described)"
                                % (nnn, tstatus))
    return findings, []


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
)

PROJECT_CHECKS = (
    ("links", check_project_links),                             # (o) B1 project half
    ("board-rows", check_board_rows),                           # (u) B3
    ("root-strays", check_root_strays),                         # (v) B4
    ("board-monotonic", check_board_monotonic),                 # (w) B5
)


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
