---
name: xg-dev-workflow
description: "Design-centric dev workflow for code work. Use when the user opens or works a requirement ('new requirement' / '开个需求' / 'design this change' / 'resume <slug>' / 'workflow retro'); parks a session before leaving ('park <slug>' / '交接给新 session' / '收工离场'); investigates code behavior ('investigate X' / '调查 X'); diagnoses a defect ('diagnose' / '定位这个 bug'); reviews new/changed code ('review X' / 'review 这些改动'); scans a region for deepening opportunities ('improve X' / '架构巡检' / '找 deepening 候选'); or distills redo-input from existing cards ('learn 001 002' / '从旧卡提炼重做输入' / '提炼这组卡的经验')."
---

# xg-dev-workflow

A lite, design-centric workflow for code work. One card = one directory of docs under `dev_root`; one
continuously updated working draft (`design.md`); explicitly confirmed goals and boundaries
(**commitments**); one execution authorization (**go**); then continuous execution in which only three
kinds of change come back to the human. The procedure is `references/steps/lite.md` — this file routes.
Every doc follows `references/conventions-core.md` (shared with xg-knowledge-lite, byte-identical) and
`references/diagram-gotchas.md`; the closed list of hard rules — layout · ids · doc form · ADRs · go ·
operations · commits · dev_root versioning · config · KB boundary · usage logging · synced files · caps — is
`references/constraints.md` (every row script- or reader-checkable; everything else is the model's call).

## Entry — which flow does this card follow?

Applies to operations that advance or close out **one card** (resume · park · check · phase verbs ·
change). Read the card's frontmatter `governance` — from `requirement.md` when it exists, else from
`design.md`; a missing carrier counts as empty:
- `lite` → `references/steps/lite.md`, exclusively.
- anything else (`ledger` · `doc-gate` · `doc-native` · empty = legacy) → a 存量 card: read
  `references/legacy/SKILL.md` and follow it (frozen 2026-09-10; bug fixes only).

New cards are always lite (`governance: lite`). Read-only and cross-card verbs (investigate · diagnose ·
review · improve · learn · status · retro) never load `legacy/`, whatever card they take as input.
Trigger phrases ('design this change' / 'change the design' / 'new requirement') follow the card's mode, not a
verb name: on a lite card or with no card they mean ordinary drafting, an A→B walk, or opening a lite card.

## Files on the lite path

- **lite.md's companions**: `references/steps/discuss.md` (one question at a time · convergence ·
  understanding statement · lens dispatch · design-topic checklist) · `references/templates/design-lite.md`
  (the design.md skeleton `new` copies) · `references/constraints.md` · `references/lenses.md` (fresh-context lens
  prompt shapes; `smell-catalog.md` is its companion).
- **Shared verbs, read as-is**: steps investigate (the evidence rule lives there) · diagnose · review (its lite
  branch; L close-out lenses per `lenses.md`) · improve · learn · retro · split-isolate (L cards: A↔B 判定 + 拆出
  五步); templates design-lite · adr · facts · index · roadmap. Slice discipline (recon · test mode ·
  commit · comments) is lite.md「Executing」.
- **Never loaded for a lite card**: everything under `references/legacy/` (the frozen five-phase flow —
  `legacy/SKILL.md` with its steps, templates and refs, plus frozen forks of the shared files it cites) and
  `references/ask-routing-core.md` (legacy-only, kept at top level as a synced file).
- **Tooling**: `tools/workflow-status.py --check <project>/<NNN>` runs the lite subset (links · status-field ·
  progress-cap · governance-carriers · lite-board-sync — each naming its `constraints.md` row in `--manifest`);
  the board and the viewer render a lite card as one cell from design.md `status` (`status · Req n / 已验证 k`);
  `--trace` and `--digest` print one 不适用 line for a lite card (they render five-phase scaffolding).
  Other tools: `viewer.py` · `commit-data-repos.py` · `check-sync.py` · `check-code-refs.py` · `log-usage.py` ·
  `resolve-project.py`.

## Verbs

`xg-dev-workflow <verb> [args]`:
- `new <slug>` — open a lite card by hand (next `NNN` · dir · `design.md` copied from
  `templates/design-lite.md` with id / title / project / created filled · board row ·
  `notes/human-messages.md` at the first human message): lite.md「Open a card」, then「Drafting」.
- `resume [<slug>]` · `park [<slug>]` — lite.md「Park / resume」(存量 cards: legacy/SKILL.md).
- `check [<slug>]` — the lite check subset above (存量 cards: legacy's M3).
- `investigate <topic>` — the front door for any code-behavior question; KB-first, evidence-cited,
  read-only: `references/steps/investigate.md`.
- `diagnose <symptom>` — defect localization, repro loop before any theory: `references/steps/diagnose.md`.
- `review <target>` — judging new/changed code; also the lite close-out review: `references/steps/review.md`.
- `improve <project> [<region>…]` — read-only deepening scan, picks graduate via the roadmap:
  `references/steps/improve.md`.
- `learn <card>…` — distill redo-input from existing cards: `references/steps/learn.md`.
- `status [<project> …]` — the card view (`tools/workflow-status.py`; `tools/viewer.py` for the HTML view).
- `retro` — improve this skill: pruning pass · CHANGELOG entry · 体量行: `references/steps/retro.md`.
- `requirement` · `design` · `detail` · `plan` · `test` · `change` — legacy phase verbs; only
  `references/legacy/SKILL.md` defines them.

## What stays the model's call (自主区)

Section depth · drawing beyond lite.md's trigger · candidates beyond the by-size minimum · when to split a
file or a card · test strategy · commit granularity · reading scope · dispatching a lens by risk · the review
tier by stakes · anchoring a finding to a card when torn · spike vs open question · number of ADRs. A step
sentence that fixes one of these for a lite card is out of bounds — delete it at review. Numeric triggers,
minima and thresholds in the by-size table and the steps are human-set floors, not model items.

## Subagents

Checklist / gather / verification work → `model: sonnet`; inference-heavy analysis → the session model
capped at opus (a fable session dispatches at `model: opus`); deterministic checks are scripted, not
delegated. Per-lens application: `references/lenses.md`; the rationale is in CHANGELOG 2026-09-14 (期 2).
