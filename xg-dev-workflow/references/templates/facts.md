<!--
<card>/facts.md — the card's fact layer (F-id registry): load-bearing facts that decisions
rest on, kept OUTSIDE the freely-rewritable phase docs so a doc rewrite can never lose them
(design 010, ADR-0002). Phase docs cite entries as [F<n>].

Reader = Claude (both zones — cited evidence base; humans reach it by drill-down from a
[F<n>] citation, never as a reading assignment). Written by grill/investigate rounds
(grill.md「载重事实入账」).

Discipline: append-mostly — a correction is a NEW block plus the old block's status flipped
to superseded; a refinement that narrows (not invalidates) an earlier fact is a new block
saying so. Reusable cross-card module knowledge still graduates to the KB (xg-knowledge-lite);
this file holds only card-local facts.

Cross-card narrow flip (learn consumption — steps/learn.md + steps/requirement.md beat 1):
when a NEW card's re-verification refutes a fact it reused from this file, the consumer flips
this block's marker to SUPERSEDED + one pointer line in the same batch — marker + pointer
only, never body edits (the named exception to learn's input-card read-only).

Marker integrity: the marker and 来源 must agree — a block whose 来源 says it was inferred or
untested cannot be [VERIFIED] (`workflow-status.py --check` (g) enforces this). A feasibility
claim about an external tool/runtime reaches VERIFIED only by running it (evidence.md).
-->

### F1 [VERIFIED]
- 事实: <one sentence — what is true>
- 来源: `func()` in `file.c` / `[[wiki/<project>/<slug>]]` / <how it was verified>

### F2 [推断]
- 事实: <…>
- 来源: <what it is inferred from; upgrade to VERIFIED when checked>
