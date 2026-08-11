# Design agenda — data for the discussion-first flow

The static data consumed by `steps/grill.md`「Discussion-first flow」and
`steps/adversarial-critic.md`「When to run」. **Data only** — flow rules stay in `grill.md`;
contract duties referenced here live in their protocol files (the part topic's A↔B/seam
duties in `steps/design-grill.md`). Rows are open for accretion: add topics, axes, and round
types here without touching protocol files.

## Topic library (agenda topics)

An index over three existing enumerations — design-grill's lens walk, the design template's
conditional sections, and the freeze-gate checklist — not a fourth list. `attr`: **panorama**
(full spread in one round) / **detail** (one question at a time). `fixed`: contract-fixed —
the agenda negotiation may reorder but never drop it.

| Topic | attr | fixed | Lens / section hook (existing home) |
|---|---|---|---|
| Module & layer split | panorama | — | design-grill step lenses: module-depth; template Chosen approach |
| Happy path / data-flow walk | panorama | — | template Diagrams (data-flow walk) |
| Part decomposition | panorama | **fixed** | design-grill Part decomposition: A↔B 判定 + seam freeze (duties live there) |
| State & lifecycle | panorama | — | design-grill lenses: lifecycle walk (opt-in) |
| Concurrency / ordering | detail | — | design-grill lenses: correctness |
| Data model & storage footprint | panorama | — | template 存储足迹 |
| Failure & recovery paths | panorama | — | design-grill lenses: 异常完整性 |
| Compat & migration | detail | — | template 影响面 (兼容/ABI 面) |
| Ops / observability | detail | — | design-grill lenses: 可观测性 |
| Performance & scale | detail | — | design-grill lenses: 性能 + 规模放大 |
| 拆分审视 (requirement side) | detail | **fixed** | requirement step 8 (mandatory beat) |
| Freeze-checklist review | detail | **fixed** | design-grill freeze gate (前置清单) |

Topics outside the library are welcome — name them at the agenda negotiation; a recurring one
earns a row here.

## Driving axis

The axis is the *reason* behind the proposed topic order — a heuristic for **ordering
topics**, never a rule for cutting modules (per-part/per-layer drivers may differ and surface
inside the topics). Initial call at the understanding statement's close; rechecked at the
agenda negotiation. The classes are open — add one when a problem doesn't fit:

- **Flow-driven** → happy path leads; modules follow the flow's stages.
- **Data/state-driven** → data model / state machine leads; modules follow data boundaries.
- **Constraint-driven** (compat, ordering, resource caps) → constraint topics lead; they cut
  away candidate splits first.
- **No dominant axis** (common on XS/S) → default order = the library's row order, or the
  negotiation picks directly.

Related wording: design-grill 方案优先's "normal flow OR a dominant anomaly flow is the hard
part" is the flow-facet special case of this axis — the two cross-reference, never merge.

## Round-type check mapping (When-to-run hook)

Consumed by `adversarial-critic.md`「When to run」's discussion-mode row. **Override relation:
this table governs in-discussion dispatch cadence only — ADR-class new/changed-mechanism
checkpoints and the pre-freeze pass still take the full attack-lens panel** (decision-level
duties never narrow).

| Round type | Dispatched lenses | Inline rules / judgments |
|---|---|---|
| Understanding statement | lens 2 invariant replay (once the subsystem is known) | verify-the-assumption on load-bearing claims |
| Candidate spread | lens 3 search-before-build (each candidate's "new" parts) | comparison-table provenance; recommendation pre-check |
| Agenda negotiation | — (lens 4 rechecks agenda completeness at the gate) | — |
| Constraint-class topic | invariant replay, single agent | — |
| Structure-class topic (module split / parts) | module-depth | A↔B 判定 |
| Detail fork / rewrite-only / mid-topic force-close | lightweight text-consistency (When to run's Tiered form) | — |
| Requirement beats | per the existing requirement row (lenses 1+3 + standing rules) | — |
| Pre-freeze | full attack-lens panel + lens 4 (unchanged) | — |

Batch dispatch: same-class small topics may share one end-of-cluster dispatch — the receipt
lands no later than the cluster's last round-end and names the rounds covered; ADR-class
checkpoints are never batched. Per-topic dispatch is the default.

## XS/S items table (sizing scaling)

Per-item disposition of the discussion-first obligations on XS/S cards. Logging and receipts
never scale away with sizing (017 R1).

| # | Obligation | XS/S disposition |
|---|---|---|
| 1 | Understanding statement | keep, compressed to one paragraph |
| 2 | Candidate spread | simplify: S = 1+1 (pick + one-line rejected alt); XS with an obvious single solution = one explanatory sentence |
| 3 | Agenda negotiation | skip — default order applies |
| 4 | Agenda topic rounds | shrink naturally (few topics; no extra rule) |
| 5 | Driving-axis call | skip — default order |
| 6 | grill-log persisted from round 1 | **keep** (017 R1) |
| 7 | Per-item G rows + recommendations | keep |
| 8 | Round-type check dispatch | existing scaling: single-agent form |
| 9 | Transcription-fidelity two-way check | existing scaling: the gate's lens 4 single agent covers it (doc-gate per-resolution writes make the forward check hold by construction) |
| 10 | (落纸补充) marker + mini-round | keep (zero cost) |
| 11 | Requirement two beats | simplify: XS may merge into one spread; gate merging per SKILL.md rules |
| 12 | Skeleton doc at phase start | keep (zero cost) |
| 13 | Per-round convergence verdict | keep (existing duty) |
| 14 | Mid-topic force-close backstop | keep (rarely triggers on small cards) |
