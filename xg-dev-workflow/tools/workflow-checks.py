#!/usr/bin/env python3
"""workflow-checks.py — the deterministic check domain (L2 of the status/checks split), lite half.

Check implementations behind `workflow-status.py --check`: the checks a lite card runs — links (o),
status-field (p), progress-cap (s), governance-carriers (ai), lite-board-sync (ah), lite-doc-form (aj) — plus the project
scope (o)(u)(v)(w) and the registry / exemption infrastructure. The 23 存量-only card checks (ledger,
grill, receipts, trace, doc-native blocks, …) were split out to legacy/legacy_checks.py (031,
2026-09-14) and are lazy-loaded by `_legacy()` only for a non-lite card, for `--manifest`, or when a
legacy name is asked for — output order and text for 存量 cards are unchanged (CARD_ORDER).
workflow-status.py remains the parsing layer + CLI entry and lazy-loads this module; every public
function takes `ws` = a live view of the workflow-status module (one-way dependency: checks read the
parsing layer, never the reverse — block_parse.py joins on the parsing side, now under legacy/).

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
  fold into the counting line (bucket 2). The 027/029 finding promotions are documented
  at their emission points in legacy/legacy_checks.py.

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


# ---- (j)-(m): gate-adjacent checks (021 T3) ----
GATED_DOCS = (("requirement.md", ("confirmed",)),
              ("design.md", ("frozen", "approved")),
              ("detail.md", ("baseline",)))


def _doc_status(path, ws):
    # real cards annotate status inline ("confirmed # …") — strip it
    return ws.frontmatter(path).get("status", "").split("#")[0].strip()


def _gated_docs(card_dir, ws):
    for name, gated in GATED_DOCS:
        path = os.path.join(card_dir, name)
        if os.path.exists(path) and _doc_status(path, ws) in gated:
            yield name, path


# ---- (o)-(t): card-scoped B/C checks (021 T5) ----
PHASE_DOC_NAMES = ("requirement.md", "design.md", "detail.md",
                   "plan.md", "test.md", "progress.md")
# link-domain placeholder exclusion — its own vocabulary, NOT the shared PLACEHOLDERS
# (that set has four other consumers with set-membership semantics)
LINK_PLACEHOLDER = re.compile(r"[…<>*]|\.\.\.|NNN|<slug>|<project>")
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
MDLINK = re.compile(r"\]\(([^)#\s]+)")
PROGRESS_CAP = 180        # template's ≈150-line cap + 20% buffer


def _strip_code(text):
    """Fenced blocks + inline code spans removed — a backticked mention is not a use."""
    return re.sub(r"`[^`]*`", "", re.sub(r"```.*?```", "", text, flags=re.S))


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


LITE_REVIEW_LINE = re.compile(r"(自审|review)", re.I)
LITE_REVIEW_DONE = re.compile(r"(✓|已做|完成|skip|跳过|无缺陷|findings)")


def _lite_done_clauses(nnn, card, ws):
    """(w)'s done-series for a lite row (030 Req-4): done ⇒ design.md `status: done` · a
    「测试与验证」section · a review record (notes/review-*.md, or a design.md line that names
    自审/review together with an outcome word)."""
    text = ws._read(os.path.join(card, "design.md"))
    status = ws.lite_status_word(card)
    out = []
    if status != "done":
        out.append("board-done: %s done but design.md status '%s'" % (nnn, status))
    if "## 测试与验证" not in text:
        out.append("board-done: %s done without 测试与验证 section" % nnn)
    reviewed = glob.glob(os.path.join(card, "notes", "review-*.md")) or any(
        LITE_REVIEW_LINE.search(l) and LITE_REVIEW_DONE.search(l) for l in text.splitlines())
    if not reviewed:
        out.append("board-done: %s done without review record (notes/review-*.md or a 自审/review outcome line)" % nnn)
    return out


def check_lite_board_sync(project, card_dir, ws):
    """(ah) lite-board-sync (030 Req-4): a lite card's board row state matches design.md
    `status` under draft→todo · executing/closing→active · done→done; `dropped` lives on the
    row only. Non-lite cards never run it (check_card_all gates by mode)."""
    project_dir = os.path.dirname(card_dir.rstrip("/"))
    nnn = os.path.basename(card_dir.rstrip("/"))[:3]
    row = ws.board(project_dir).get(nnn)
    if row is None:
        return [], ["lite-board-sync: %s no board row (project-level board-rows check covers it)" % nnn]
    state = row.get("state", "")
    if state == "dropped":
        return []
    status = ws.lite_status_word(card_dir)
    expect = ws.LITE_BOARD_STATE.get(status)
    if expect is None:
        return ["lite-board-sync: %s design.md status '%s' has no board mapping" % (nnn, status)]
    if state != expect:
        return ["lite-board-sync: %s board '%s' vs design.md status '%s' (expect '%s')"
                % (nnn, state, status, expect)]
    return []


def check_governance_carriers(project, card_dir, ws):
    """(ai) governance-carrier-conflict (030): requirement.md and design.md both carry a
    `governance` value and disagree — the entry rule and the tools read requirement.md, so a
    lite card that later grows a requirement.md would silently change mode. Silent when only
    one carrier has the key (every 存量 card), so their output is unchanged."""
    vals = {}
    for doc in ("requirement.md", "design.md"):
        v = ws.frontmatter(os.path.join(card_dir, doc)).get("governance", "").strip("\"'")
        if v:
            vals[doc] = v
    if len(vals) == 2 and vals["requirement.md"] != vals["design.md"]:
        return ["governance-carrier-conflict: requirement.md '%s' vs design.md '%s' (requirement.md wins)"
                % (vals["requirement.md"], vals["design.md"])]
    return []


# ---- (aj) lite doc-form (032 Req-5): the constraints.md rows marked (S: aj), one lite-only entry ----
LITE_DOC_FORM_CUTOFF = "2026-09-16"   # 032 go day; an older lite card sees hints unless its frontmatter carries `skill:`
LITE_DOC_FORM_DOCS = ("design.md", "plan.md", "facts.md", "progress.md")
LONG_FIELD_CHARS = 120                 # the frozen (ag) threshold, chars not bytes
INV_TRIGGER = re.compile(r"锁|信号|退出码|磁盘格式|输出形状|外部环境|不可逆"
                         r"|\b(lock|signal|exit code|disk format|output shape|external environment|irreversible)\b", re.I)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
CHANGE_DATE = re.compile(r"^\s*- 变更[:：]\s*(\d{4}-\d{2}-\d{2})", re.M)
CONFIRM_DATE = re.compile(r"^\s*- 确认[:：]\s*(\d{4}-\d{2}-\d{2})", re.M)
AUTH_SECTION = re.compile(r"^## 授权记录[^\n]*\n(.*?)(?=^## |\Z)", re.M | re.S)
FIELD_LINE = re.compile(r"^\s*- ([^\s:：()（）]{1,12})[:：]\s*(\S.*)$")   # `- 标签: 内容` on one line
CLAUSE_MARK = re.compile(r"^\s*- \([a-z]\) ", re.M)
INLINE_CLAUSE = re.compile(r"\([a-z]\)")
GO_ENTRY = re.compile(r"\*\*go(（续）|\(续\))?\*\*")
QUOTE = re.compile(r"原话[:：]\s*[「“\"]([^」”\"]+)[」”\"]")
INFERRED_GO = re.compile(r"(视为|视作|等同|即为)\s*(go|授权)")


def _skill_repo_head():
    """Short HEAD of the git repo this script lives in (a symlinked install resolves to the repo); "" when unknown."""
    import subprocess
    here = os.path.dirname(os.path.realpath(__file__))
    try:
        res = subprocess.run(["git", "-C", here, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return res.stdout.strip() if res.returncode == 0 else ""


def _visible(text):
    """Code spans and link targets removed before measuring — a backticked path is not prose length."""
    return re.sub(r"\]\([^)]*\)", "]", _strip_code(text))


def _req_blocks(text):
    """[(id, body)] — every `### Req-n` block up to the next `##`/`###` heading."""
    blocks, cur, buf = [], None, []
    for line in text.splitlines():
        m = re.match(r"^### (Req-\d+)\b", line)
        if m or (cur and re.match(r"^##+ ", line)):
            if cur:
                blocks.append((cur, "\n".join(buf)))
            cur, buf = (m.group(1) if m else None), []
            continue
        if cur:
            buf.append(line)
    if cur:
        blocks.append((cur, "\n".join(buf)))
    return blocks


def _field_value(body, label):
    """The payload of `- <label>:` in a block: the label line's tail plus its indented continuation."""
    out, on = [], False
    for ln in body.splitlines():
        m = re.match(r"^- ([^\s:：]+)[:：]\s*(.*)$", ln)
        if m:
            on = m.group(1) == label
            if on:
                out.append(m.group(2))
            continue
        if on and (ln.startswith("  ") or not ln.strip()):
            out.append(ln)
        else:
            on = False
    return "\n".join(out)


def _long_lines(rel, text):
    """long-cell hits: table cells and one-line `- 标签: 内容` payloads over LONG_FIELD_CHARS (code-stripped)."""
    out, fenced = [], False
    for lineno, raw in enumerate(text.splitlines(), 1):
        ln = raw.strip()
        if ln.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            for i, c in enumerate(cells):
                n = len(_visible(c))
                if n > LONG_FIELD_CHARS:
                    out.append("doc-form/long-cell: %s line %d col %d — %d chars" % (rel, lineno, i + 1, n))
            continue
        m = FIELD_LINE.match(raw)
        if m:
            n = len(_visible(m.group(2)))
            if n > LONG_FIELD_CHARS:
                out.append("doc-form/long-cell: %s line %d field %s — %d chars" % (rel, lineno, m.group(1), n))
    return out


def check_lite_doc_form(project, card_dir, ws):
    """(aj) 032 Req-5 — the reader rules constraints.md marks (S: aj), as one check with tagged findings:
    long-cell (Doc-3) · inline-clause (Id-1) · inv-missing (Doc-8, done cards) · observations-missing (Lay-3,
    done cards) · fact-home (Id-3) · go-quote (Go-1) · change-unconfirmed (Go-2) · messages-stale (Lay-3) ·
    lens-missing (Go-4) — plus two hints that never gate: skill-behind (Lay-2) and an inferred-go wording.
    Gate: created >= LITE_DOC_FORM_CUTOFF or a `skill:` field; an older card gets the findings as skips and one
    grandfathered exemption. Runs for lite cards only (LITE_ONLY_CHECKS)."""
    design_path = os.path.join(card_dir, "design.md")
    design = ws._read(design_path)
    if not design:
        return [], [], [("carrier-missing", "design.md missing/empty")]
    skill = ws.frontmatter(design_path).get("skill", "").split("#", 1)[0].strip().strip("\"'")
    created = ws.card_created(card_dir)
    gate = bool(skill) or (bool(created) and created >= LITE_DOC_FORM_CUTOFF)
    status = ws.lite_status_word(card_dir)
    notes = os.path.join(card_dir, "notes")
    messages = ws._read(os.path.join(notes, "human-messages.md"))
    hits, hints = [], []

    for rel in LITE_DOC_FORM_DOCS:
        text = design if rel == "design.md" else ws._read(os.path.join(card_dir, rel))
        if text:
            hits += _long_lines(rel, text)

    inv_present = bool(re.search(r"^### Inv-\d+", design, re.M))
    for rid, body in _req_blocks(design):
        if INLINE_CLAUSE.search(_field_value(body, "陈述")) and not CLAUSE_MARK.search(body):
            hits.append("doc-form/inline-clause: %s has (x) clauses with no line-leading `- (x)` marker" % rid)
        if status == "done" and not inv_present:
            m = INV_TRIGGER.search(_strip_code(body))
            if m:
                hits.append("doc-form/inv-missing: %s mentions '%s' but the card has no Inv block" % (rid, m.group(0)))
        confirms = CONFIRM_DATE.findall(body)
        for d in sorted(set(CHANGE_DATE.findall(body))):
            if not any(c >= d for c in confirms):
                hits.append("doc-form/change-unconfirmed: %s 变更 %s has no 确认 on or after it" % (rid, d))

    if status == "done" and not os.path.exists(os.path.join(notes, "observations.md")):
        hits.append("doc-form/observations-missing: done card without notes/observations.md")
    facts = sorted(set(re.findall(r"\bFact-\d+\b", _strip_code(design))))
    if facts and not os.path.exists(os.path.join(card_dir, "facts.md")):
        hits.append("doc-form/fact-home: %s cited in design.md but facts.md is absent" % ", ".join(facts[:3]))

    m = AUTH_SECTION.search(design)
    auth = m.group(1) if m else ""
    msgs_norm = " ".join(messages.split())
    for entry in re.split(r"^- ", auth, flags=re.M)[1:]:
        when = DATE.search(entry)
        when = when.group(0) if when else "?"
        if GO_ENTRY.search(entry):
            q = QUOTE.search(entry)
            if not q:
                hits.append("doc-form/go-quote: 授权记录 go entry %s has no 人原话：「…」" % when)
            elif " ".join(q.group(1).split()) not in msgs_norm:
                hits.append("doc-form/go-quote: 授权记录 go entry %s quotes 「%s」 which is not in notes/human-messages.md"
                            % (when, q.group(1)[:40]))
        m = INFERRED_GO.search(entry)
        if m:
            hints.append("lite-doc-form: 授权记录 entry %s reads like an inferred go ('%s') — Go-1 wants the human's words"
                         % (when, m.group(0)))
    if status in ("executing", "closing", "done") and not glob.glob(os.path.join(notes, "lens-*.md")) \
            and not re.search(r"lens[:：]\s*未做", auth):
        hits.append("doc-form/lens-missing: %s card without notes/lens-*.md or a `lens: 未做（原因）` in 授权记录" % status)

    msg_dates = re.findall(r"^- (\d{4}-\d{2}-\d{2})", messages, re.M)
    changes = CHANGE_DATE.findall(design)
    if msg_dates and changes and max(msg_dates) < max(changes):
        hits.append("doc-form/messages-stale: notes/human-messages.md last date %s is older than the newest 变更 %s"
                    % (max(msg_dates), max(changes)))
    if skill:
        head = _skill_repo_head()
        if head and not (head.startswith(skill) or skill.startswith(head)):
            hints.append("lite-doc-form: skill-behind — skill: %s trails the skill repo HEAD %s; re-read SKILL.md · lite.md · constraints.md"
                         % (skill, head))

    if gate:
        return hits, hints, []
    return [], ["lite-doc-form (pre-cutoff hint): " + h for h in hits] + hints, \
        [("grandfathered", "pre-cutoff lite card: doc-form findings shown as hints")]


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
        if ws.card_mode(card) == "lite":
            findings += _lite_done_clauses(nnn, card, ws)
            continue
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

# Registry meta (026 HLD-11): the manifest's SoT rides the registry rows — fields
# 查什么 / 何时跑 / 机械或判断 / 依据 / 去向; `--manifest` renders them, a row with
# no meta renders META-MISSING (E5's 全行齐 enforcement).
def _m(letter, what, when, basis, disp="保留", nature="机械", misfire="既有套件"):
    return {"letter": letter, "what": what, "when": when, "nature": nature,
            "basis": basis, "disp": disp, "misfire": misfire}


CARD_ORDER = (
    "design-sections",
    "fact-markers",
    "part-consistency",
    "governance",
    "ledger",
    "transcription-marker",
    "grill-reverse",
    "panel-receipts",
    "docgate-gateline",
    "supersede-residue",
    "links",
    "status-field",
    "r-trace",
    "fact-refs",
    "progress-cap",
    "adr-hygiene",
    "ledger-rows",
    "grill-signature",
    "home-pointer",
    "req-handoff",
    "detail-disposition",
    "block-format",
    "block-anchor",
    "block-views",
    "checkbox-monotonic",
    "long-cell",
    "governance-carriers",
    "lite-board-sync",
    "lite-doc-form",
)   # output order of every card check — lite and legacy interleaved exactly as before the 031 split

# The six checks a lite card runs; the 23 存量-only ones live in
# legacy/legacy_checks.py ENTRIES and are assembled into CARD_ORDER by card_entries() / __getattr__.
LITE_ENTRIES = {
    "links": ("links", check_links,
     _m("(o)", "链接/wikilink 解析（卡半）", "always", "Lay-6 · 021")),
    "status-field": ("status-field", check_status_field,
     _m("(p)", "frontmatter status 在场/值域", "doc 在场", "Lay-2 · 021")),
    "progress-cap": ("progress-cap", check_progress_cap,
     _m("(s)", "progress 行数帽（活卡）", "活卡", "Lay-5 · 021")),
    "governance-carriers": ("governance-carriers", check_governance_carriers,
     _m("(ai)", "requirement.md 与 design.md 两载体 governance 同在且不同（requirement.md 胜出）", "两载体都写了字段的卡", "Lay-2 · card 030", misfire="GovernanceCarrierConflict")),
    "lite-board-sync": ("lite-board-sync", check_lite_board_sync,
     _m("(ah)", "lite 卡看板行整体状态 ↔ design.md status 映射一致（draft→todo · executing/closing→active · done→done；dropped 只在行上）",
        "lite 卡（非 lite 卡不跑，输出零变化）", "Lay-4 · card 030", misfire="LiteBoardSync")),
    "lite-doc-form": ("lite-doc-form", check_lite_doc_form,
     _m("(aj)", "lite 卡文档形（constraints 的 S: aj 行）：单格/字段行 >120 字符 · Req 块行内 (x) 无行首 marker · done 卡关键词 Req 无 Inv 块 · "
        "done 卡缺 notes/observations.md · Fact-n 在 design.md 无 facts.md · 授权记录 go 条目无原话或原话不在 human-messages · 变更 无同日后 确认 · "
        "human-messages 日期早于最新 变更 · 无 lens 记录；提示级：skill: 落后 HEAD · 「视为 go」措辞",
        "lite 卡；created ≥ 2026-09-16 或带 skill: 字段 → findings，更早的卡 → skips 提示", "Lay-2 · Lay-3 · Id-1 · Id-3 · Doc-3 · Doc-4 · Doc-8 · Go-1 · Go-2 · Go-4 · card 032",
        misfire="LiteDocForm")),
}

PROJECT_CHECKS = (
    ("links", check_project_links,
     _m("(o)", "链接解析（项目半）", "always", "Lay-6 · 021")),
    ("board-rows", check_board_rows,
     _m("(u)", "看板行↔卡目录双向", "always", "Lay-1 · 021")),
    ("root-strays", check_root_strays,
     _m("(v)", "项目根杂散文件", "always", "Lay-1 · 021")),
    ("board-monotonic", check_board_monotonic,
     _m("(w)", "看板机器子集（环/状态词/done 系列）", "新格式看板", "Lay-4 · 021")),
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
    ("roadmap: trace loose 匹配收紧", "已落地 027 T3——loose 剔他卡紧邻归属形，残余带 ?"),
    ("roadmap: R-id 整行扫描并入括号 id", "已落地 027 T1——cutoff 后卡表格行窄采（table_rows 单点）"),
    ("roadmap: 存量账本 findings 语义张力", "已化解 027 T2——词形放宽 + 死块 deps 不算引用，存量 18 条消噪"),
    ("roadmap: 载体在但契约不判 5 处升 finding", "已裁并落地 027 T5——四形升档（per-concern cutoff），(d) 撤档（Ask-45：doc-native 无前向对象）"),
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


LITE_CHECKS = ("links", "status-field", "progress-cap", "governance-carriers", "lite-board-sync", "lite-doc-form")   # what a lite card runs
LITE_ONLY_CHECKS = ("lite-board-sync", "lite-doc-form")   # never run for other modes — their output stays byte-identical


class LegacyChecksUnavailable(RuntimeError):
    """legacy/legacy_checks.py could not be loaded — raised to the CLI (exit 2), never folded into a finding."""


class _SelfView:
    """Live attribute view over this module's globals, injected into the legacy half as `wc` — the same
    shape as workflow-status._L1View; the one-way import direction forbids sharing one class."""
    def __getattr__(self, name):
        try:
            return globals()[name]
        except KeyError:
            raise AttributeError(name) from None


_LEGACY = None


def _legacy():
    """Lazy-load legacy/legacy_checks.py — the 23 存量-only card checks. Reached only by a non-lite
    card, by CARD_CHECKS read whole (--manifest, tests) or by a legacy name; a lite card never gets here."""
    global _LEGACY
    if _LEGACY is None:
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy", "legacy_checks.py")
        try:
            spec = importlib.util.spec_from_file_location("legacy_checks", path)
            mod = importlib.util.module_from_spec(spec)
            mod.wc = _SelfView()
            spec.loader.exec_module(mod)
        except Exception as e:
            raise LegacyChecksUnavailable("%s: %s" % (path, e)) from e
        _LEGACY = mod
    return _LEGACY


def card_entries(lite):
    """Card-check entries in CARD_ORDER: a lite card runs LITE_CHECKS only (legacy half untouched);
    every other card runs all but LITE_ONLY_CHECKS. A test may pin `CARD_CHECKS` on this module —
    then that tuple is the registry, as before the split."""
    keep = (lambda cid: cid in LITE_CHECKS) if lite else (lambda cid: cid not in LITE_ONLY_CHECKS)
    pinned = globals().get("CARD_CHECKS")
    if pinned is not None:
        return tuple(e for e in pinned if keep(e[0]))
    if lite:
        return tuple(LITE_ENTRIES[cid] for cid in CARD_ORDER if cid in LITE_CHECKS)
    legacy = _legacy().ENTRIES_BY_ID
    return tuple(LITE_ENTRIES.get(cid) or legacy[cid] for cid in CARD_ORDER if keep(cid))


def __getattr__(name):
    """The full CARD_CHECKS registry and every legacy check name resolve through the legacy half."""
    if name == "CARD_CHECKS":
        legacy = _legacy().ENTRIES_BY_ID
        return tuple(LITE_ENTRIES.get(cid) or legacy[cid] for cid in CARD_ORDER)
    if name.startswith("__"):
        raise AttributeError(name)
    return getattr(_legacy(), name)


def check_card_all(project, card_dir, ws):
    """All card-scoped checks, per-check isolated. Returns (findings, skips,
    exemptions); card attribution rides the record's fields, never a string
    prefix (the skips stream keeps its prefix behavior). A lite card (trial
    mode, steps/lite.md) runs only LITE_CHECKS — every phase-shape check is
    built on the five-phase docs it does not have — and books one exemption."""
    lite = ws.card_mode(card_dir) == "lite"
    entries = card_entries(lite)
    findings, skips, raw = _run_entries(entries, (project, card_dir), ws)
    if lite:
        raw = raw + [("not-yet-due", "lite", "lite card: mode checks not applicable")]
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
