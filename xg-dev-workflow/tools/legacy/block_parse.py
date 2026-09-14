#!/usr/bin/env python3
"""Doc-native decision-block parser (026 LLD-1..3/6): the single parser every
downstream consumer (checks, generated views, digest) goes through.

Public surface: parse_doc_blocks(text, doc="") / card_blocks(card_dir) /
deps_graph(blocks) (LLD-6), plus the freeze-guard face family (029):
FACE_FIELDS / block_face(b) / face_text(b) / face_diffs(old, new) /
is_guarded(b) / norm_extras(b) / annots_prefix(old, new) — the single source
both defense lines ((ad) audit core in workflow-checks.py, diff_guard write
side in commit-data-repos.py) and (j)'s approved-text face compare against.
Pure parsing, no findings are ever silently dropped; anchor verification and
format checks consume this output and live in workflow-checks.py. Underscore
module name keeps `import block_parse` possible for sibling tools and tests
(tools/ scripts are hyphen-named and load via importlib; a library module is
the stated reason for the new naming form).
Not in sync-manifest — xg-dev-workflow only.

Block: {prefix, num, state, title, fields: {陈述/类型/why/provenance/depends-on},
annotations: [Annot], clauses: [(letter, text)], doc, head_line, extras}.
head_line is error-location only — no persistent carrier may store it (HLD-2).
Annot: {kind ∈ approved/变更/退役/澄清/来源, text, extra} — kind-specific slots
in extra. Tolerated non-semantic note lines (e.g. 附注) land in extras, never
flagged; the five annotation kinds are strictly validated (bad-annotation on
mismatch — 宁误报不漏检). Dangling depends-on stays with the checks layer:
transported Part A blocks keep 025-namespace deps (R21 …) legally until the
slice-2 归一, so deps_graph reports edges and cycles only.
"""
import os
import re
from collections import OrderedDict

PREFIXES = "Req|HLD|LLD|Task|Ask|Fact|Eff|Crit|Layer"
STATES = "proposed|approved|superseded|retired"
HEAD = re.compile(r"^### (%s)-(\d+) (%s)(?: — (.+))?\s*$" % (PREFIXES, STATES))
NEARMISS = re.compile(r"^### \S+-\d+\b")
CITE = re.compile(r"(?<!:)\[(%s)-(\d+)(?:-([a-z]))?\]" % PREFIXES)

FIELD = re.compile(r"^- (陈述|类型|why|provenance|depends-on):\s?(.*)$")
CLAUSE = re.compile(r"^- \(([a-z])\)\s?(.*)$")
NOTE_KEY = re.compile(r"^- (approved|变更|退役|澄清|来源):\s?(.*)$")

# Annotation grammar, LLD-2 verbatim. approved's ask-id slot is a closed set
# (HLD-1 strict; bare G is the transitional legacy form) and optional until the
# slice-2 归一 backfills the 41 legacy notes.
APPROVED = re.compile(
    r"^- approved: (\d{4}-\d\d-\d\d) gate ([0-9a-f]{7,40})"
    r" \((single|batch)(?: ((?:Ask-|G)\d+))?: 「(.+)」\)$")
# ask-id slot = Ask-<n> | G<n> only (review #7: the wider prefix set let a
# Req-/HLD- id pass (ac) yet fall out of the sweep index — silent drop)
CHANGE = re.compile(r"^- 变更: (.+) \(M2 ([0-9a-f]{7,40}), ([^)]+)\)$")
RETIRE = re.compile(r"^- 退役: (.+) \(M2 ([0-9a-f]{7,40}), ([^)]+)\)$")
CLARIFY = re.compile(
    r"^- 澄清: (.+)\(((?:人工「.+」|receipt [0-9a-f]{7,40})[,，].*)\)$")
SOURCE = re.compile(r"^- 来源: (\d{3}) R(\d+) approved .*verbatim\s*$")

PLACEHOLDERS = {"", "—", "-", "…", "无", "None"}
CARD_DOCS = ("requirement.md", "design.md", "detail.md")


def _annot(kind, payload, line):
    """Validate one annotation line against its kind's grammar; None on mismatch."""
    if kind == "approved":
        m = APPROVED.match(line)
        return m and {"kind": kind, "text": payload,
                      "extra": {"date": m.group(1), "hash": m.group(2),
                                "mode": m.group(3), "ask_id": m.group(4),
                                "verbatim": m.group(5)}}
    if kind in ("变更", "退役"):
        m = (CHANGE if kind == "变更" else RETIRE).match(line)
        return m and {"kind": kind, "text": payload,
                      "extra": {"why": m.group(1), "hash": m.group(2),
                                "尾注": m.group(3)}}
    if kind == "澄清":
        m = CLARIFY.match(line)
        return m and {"kind": kind, "text": payload,
                      "extra": {"正文": m.group(1), "凭据": m.group(2)}}
    m = SOURCE.match(line)
    return m and {"kind": "来源", "text": payload,
                  "extra": {"源卡": m.group(1), "源id": "R" + m.group(2)}}


def parse_doc_blocks(text, doc=""):
    """text → (blocks, findings). Single line-scan, pure, idempotent, doc order.
    Near-miss headers MUST be reported (bad-header); duplicate ids keep the
    first occurrence effective (finding, parsing continues); indented lines
    continue the open field/annotation/clause (LLD-3)."""
    blocks, findings, seen = [], [], set()
    cur, open_slot = None, None  # open_slot: (kind, ref) for continuation lines
    for lineno, raw in enumerate(text.splitlines(), 1):
        m = HEAD.match(raw)
        if m:
            cur = {"prefix": m.group(1), "num": m.group(2), "state": m.group(3),
                   "title": m.group(4) or "", "fields": {}, "annotations": [],
                   "clauses": [], "doc": doc, "head_line": lineno, "extras": []}
            bid = "%s-%s" % (m.group(1), m.group(2))
            if bid in seen:
                findings.append("duplicate-id: %s%s" % (bid, _at(doc)))
            seen.add(bid)
            blocks.append(cur)
            open_slot = None
            continue
        if NEARMISS.match(raw):
            findings.append("bad-header: %s%s line %d" % (raw.strip()[:60], _at(doc), lineno))
            cur, open_slot = None, None
            continue
        if raw.startswith("#"):
            cur, open_slot = None, None
            continue
        if cur is None:
            continue
        if raw[:1].isspace() and raw.strip():
            # continuation / nested sub-bullet: belongs to the open item's payload
            if open_slot == "field":
                key = cur["_open_field"]
                cur["fields"][key] += "\n" + raw
            elif open_slot == "annot":
                cur["annotations"][-1]["text"] += "\n" + raw
            elif open_slot == "clause":
                letter, txt = cur["clauses"][-1]
                cur["clauses"][-1] = (letter, txt + "\n" + raw)
            else:
                cur["extras"].append(raw)
            continue
        m = FIELD.match(raw)
        if m:
            key = m.group(1)
            if key in cur["fields"]:
                findings.append("duplicate-field: %s-%s %s%s"
                                % (cur["prefix"], cur["num"], key, _at(doc)))
            else:
                cur["fields"][key] = m.group(2)
                cur["_open_field"] = key
                open_slot = "field"
            continue
        m = NOTE_KEY.match(raw)
        if m:
            annot = _annot(m.group(1), m.group(2), raw)
            if annot:
                cur["annotations"].append(annot)
                open_slot = "annot"
            else:
                findings.append("bad-annotation: %s-%s %s%s line %d"
                                % (cur["prefix"], cur["num"], m.group(1), _at(doc), lineno))
                open_slot = None
            continue
        m = CLAUSE.match(raw)
        if m:
            cur["clauses"].append((m.group(1), m.group(2)))
            open_slot = "clause"
            continue
        if raw.strip():
            cur["extras"].append(raw)
            open_slot = None
    for b in blocks:
        b.pop("_open_field", None)
    return blocks, findings


def _at(doc):
    return " @%s" % doc if doc else ""


def card_blocks(card_dir):
    """card dir → (OrderedDict[id, Block], findings): requirement → design →
    detail, doc order within each; cross-doc id collision keeps the first
    occurrence + finding (lens4 F14). requirement.md is mandatory on a
    doc-native card (missing/empty → finding); design/detail are lazily
    created and silently absent before their phase."""
    out, findings = OrderedDict(), []
    for name in CARD_DOCS:
        path = os.path.join(card_dir, name)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            text = ""
        if not text.strip():
            if name == "requirement.md":
                findings.append("doc-missing: requirement.md")
            continue
        blocks, fs = parse_doc_blocks(text, doc=name)
        findings += fs
        for b in blocks:
            bid = "%s-%s" % (b["prefix"], b["num"])
            if bid in out:
                if out[bid]["doc"] != name:
                    findings.append("duplicate-id-cross-doc: %s (kept %s)"
                                    % (bid, out[bid]["doc"]))
            else:
                out[bid] = b
    return out, findings


# Freeze-guard compare face (029 HLD-1): the five load-bearing fields plus
# title and the clause list. Replaces the retired per-side ANCHOR_FIELDS /
# GUARD_FIELDS constants.
FACE_FIELDS = ("陈述", "类型", "why", "provenance", "depends-on")


def block_face(b):
    """The comparable freeze-guard face of one block: fields dict restricted
    to FACE_FIELDS + title + clause list."""
    return {"fields": {f: b["fields"].get(f, "") for f in FACE_FIELDS},
            "title": b["title"],
            "clauses": list(b["clauses"])}


def face_text(b):
    """The face as one text blob ((j)'s marker-scan body)."""
    face = block_face(b)
    return "\n".join([face["title"]] + list(face["fields"].values())
                     + [c[1] for c in face["clauses"]])


def face_diffs(old, new):
    """Field-level diff labels between two blocks' faces. Title compares only
    when the OLD (baseline/HEAD) block has one — the shape grandfather for
    pre-归一 blocks whose titles were backfilled after approval (029 HLD-1)."""
    fo, fn = block_face(old), block_face(new)
    diffs = [f for f in FACE_FIELDS if fo["fields"][f] != fn["fields"][f]]
    if fo["title"] and fo["title"] != fn["title"]:
        diffs.append("title")
    if fo["clauses"] != fn["clauses"]:
        diffs.append("clauses")
    return diffs


def is_guarded(b):
    """Union selection predicate (029 HLD-6): a block enters freeze guarding
    when its state word says approved OR it carries an approved annotation —
    either alone must not drop it from the guarded set."""
    return b["state"] == "approved" or any(
        a["kind"] == "approved" for a in b["annotations"])


def norm_extras(b):
    """extras normalized for hint comparison (029 HLD-7): per-line strip,
    blank lines dropped — reflow/indent churn never reads as a change."""
    return [ln.strip() for ln in b["extras"] if ln.strip()]


def annots_prefix(old, new):
    """append-only annotation discipline as a machine predicate (029 HLD-4):
    old block's (kind, text) sequence is a prefix of new's."""
    o = [(a["kind"], a["text"]) for a in old["annotations"]]
    n = [(a["kind"], a["text"]) for a in new["annotations"]]
    return n[:len(o)] == o


def expand_ranges(clause):
    """`Req-1..Req-23` range notation → the individual ids (HLD-1); single ids
    pass through. Consumes any citation-list string."""
    ids = []
    rng = re.compile(r"(%s)-(\d+)\.\.(?:%s)-(\d+)" % (PREFIXES, PREFIXES))
    for pref, a, b in rng.findall(clause):
        ids += ["%s-%d" % (pref, n) for n in range(int(a), int(b) + 1)]
    rest = rng.sub("", clause)
    ids += ["%s-%s" % (pref, n)
            for pref, n in re.findall(r"(%s)-(\d+)" % PREFIXES, rest)]
    return ids


def deps_graph(blocks):
    """blocks (mapping id→Block, or iterable of Block) → (edges, cycles).
    edges: {id: [dep, …]} from each block's depends-on field (placeholders
    dropped); cycles via the checks-side _dep_cycles shape (white/grey/black
    DFS, same output form). Dangling refs are visible as edge targets absent
    from edges' keys — classified by the checks layer, not here."""
    items = blocks.values() if hasattr(blocks, "values") else list(blocks)
    edges = {}
    for b in items:
        bid = "%s-%s" % (b["prefix"], b["num"])
        deps = b["fields"].get("depends-on", "")
        edges.setdefault(bid, [])
        for d in deps.split(","):
            d = d.strip()
            if d and d not in PLACEHOLDERS:
                edges[bid].append(d)
    cycles, color = [], {}

    def dfs(n, stack):
        color[n] = 1
        for d in edges.get(n, []):
            if color.get(d) == 1:
                cycles.append(stack + [d])
            elif color.get(d) is None and d in edges:
                dfs(d, stack + [d])
        color[n] = 2

    for n in edges:
        if color.get(n) is None:
            dfs(n, [n])
    return edges, cycles
