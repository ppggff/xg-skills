<!--
<card>/facts.md — the card's fact layer (F-id registry): load-bearing facts that decisions
rest on, kept OUTSIDE the freely-rewritable phase docs so a doc rewrite can never lose them
(design 010, ADR-0002). Phase docs cite entries as [F<n>].

Discipline: append-mostly — a correction is a NEW block plus the old block's status flipped
to superseded; a refinement that narrows (not invalidates) an earlier fact is a new block
saying so. Reusable cross-card module knowledge still graduates to the KB (xg-knowledge-lite);
this file holds only card-local facts.
-->

### F1 [VERIFIED]
- 事实: <one sentence — what is true>
- 来源: `func()` in `file.c` / `[[wiki/<project>/<slug>]]` / <how it was verified>

### F2 [推断]
- 事实: <…>
- 来源: <what it is inferred from; upgrade to VERIFIED when checked>
