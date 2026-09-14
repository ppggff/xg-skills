---
name: xg-dev-workflow
description: "Design-centric dev workflow for code work. Use when the user opens or works a requirement ('new requirement' / '开个需求' / 'design this change' / 'resume <slug>' / 'workflow retro'); parks a session before leaving ('park <slug>' / '交接给新 session' / '收工离场'); investigates code behavior ('investigate X' / '调查 X'); diagnoses a defect ('diagnose' / '定位这个 bug'); reviews new/changed code ('review X' / 'review 这些改动'); scans a region for deepening opportunities ('improve X' / '架构巡检' / '找 deepening 候选'); or distills redo-input from existing cards ('learn 001 002' / '从旧卡提炼重做输入' / '提炼这组卡的经验')."
---

# xg-dev-workflow

A lite, design-centric workflow for code work. One card = one directory of docs under `dev_root`; one
continuously updated working draft (`design.md`); explicitly confirmed goals and boundaries
(**commitments**); one execution authorization (**go**); then continuous execution in which only three
kinds of change come back to the human. The procedure is `references/steps/lite.md` — this file routes.
Every doc follows `references/conventions-core.md` (shared with xg-knowledge-lite, byte-identical) +
`references/doc-conventions.md`: load-bearing claims carry provenance (evidence-cited / 推断 / 假设), KB
cross-references keep the `[[wiki/<project>/<slug>]]` wikilink, diagrams are Mermaid
(`references/diagram-gotchas.md`). Hard rules — layout, config, dev_root versioning, usage logging, KB
boundary — live in `references/constraints.md`.

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
  (the design.md skeleton `new` copies) · `references/constraints.md`.
- **Shared, read as-is**: steps understand · evidence · investigate · diagnose · review (its lite branch) ·
  review-deep (L close-out; it dispatches `adversarial-critic.md`'s trio — the one legacy file a lite card
  may reach) · improve · learn · retro; `simplify-checks.md` · `model-tiering.md` · `id-schemes.md`
  (`Req-n` · `Fact-n` · `Inv-n` · `ADR-NNNN` · `Task-n`; two-form citation) · `split-isolate.md` (L cards:
  A↔B 判定 + 拆出五步); templates adr · facts · log · index · roadmap; `steps/implement.md` only for
  Environment recon · Test mode · Commit cadence (minus its card-qualified task tag — lite.md「Executing」
  forbids the tail) · Comment & artifact hygiene.
- **Never loaded for a lite card**: every other file under `references/steps/` and `references/templates/`
  (requirement · grill · design-grill · gate-digest · detail · plan · test · change · omission-check ·
  resume · park; `references/design-agenda.md` · `references/ask-routing-core.md`; templates requirement /
  design / detail / plan / test / decisions / progress) — they belong to `legacy/SKILL.md`.
- **Tooling**: `tools/workflow-status.py --check <project>/<NNN>` runs the lite subset (links · status-field ·
  progress-cap · lite-board-sync); the board renders a lite card as one cell from design.md `status`;
  `--trace` and `--digest` are not meaningful for a lite card (they still print five-phase scaffolding).

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
file or a card · test strategy · commit granularity · reading scope · dispatching a lens by risk · number
of ADRs. A step sentence that fixes one of these for a lite card is out of bounds — delete it at review.

## Subagents

Checklist / gather / verification work → `model: sonnet`; inference-heavy analysis → the session model
capped at opus (a fable session dispatches at `model: opus`); deterministic checks are scripted, not
delegated. Rationale and per-lens application: `references/model-tiering.md`.

## References

- `references/steps/lite.md` (≤150 lines) · `references/steps/discuss.md` (≤100) · `references/constraints.md`.
- `references/legacy/SKILL.md` — the frozen five-phase flow for 存量 cards; its steps and templates keep
  their paths under `references/steps/` and `references/templates/`.
- `references/conventions-core.md` · `doc-conventions.md` · `diagram-gotchas.md` — writing rules.
- `references/id-schemes.md` · `split-isolate.md` · `model-tiering.md` · `simplify-checks.md` ·
  `smell-catalog.md` · `frontend-testing.md`.
- `tools/` — `workflow-status.py` (board · `--check` · `--json`) · `viewer.py` · `commit-data-repos.py` ·
  `check-sync.py` · `check-code-refs.py` · `log-usage.py` · `resolve-project.py`.
