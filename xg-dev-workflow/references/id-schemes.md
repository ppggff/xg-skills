# ID schemes (the full registry)

The workflow's fixed ID prefixes — **one letter, one meaning**. SKILL.md「Conventions」keeps the
core five resident (`NNN` / `ADR-NNNN` / `R<n>` / `T<n>` / `M1`–`M6`); this file holds the full
scheme, consulted when naming. A new scheme picks an **unused** letter and lands here.

## Prefixes

- `NNN` — card dir · `ADR-NNNN` — decision records · `T<n>` — plan tasks.
- `R<n>` — requirement 条目; **R is reserved** for requirements.
- `G<n>` — grill-log questions, **continuous across rounds**; round-scoped form `G<round>.<n>`,
  never a new letter per round.
- `L<n>` — abstraction layers (design) · `D<n>` — design decisions/子决策 (ADR-scoped:
  `ADR-NNNN D<n>`).
- `MS<n>` — milestones/分期 — bare `M<n>` stays this skill's mechanisms `M1`–`M6`.
- `S<n>` — 详设 (detail/structure) 级决策条目 (numbered in `detail.md`, ledger level `detail`;
  approved carries baseline force — see `templates/decisions.md`). Number only items that enter
  the ledger, not every spec line.
- `P<n>` — implement's principles (`implement.md` Principles).
- `F<n>` — a doc's centralized fact-list (事实清单) entries — the provenance 集中制 form.
- Review findings: `#<n>` within a report's 修复决策表, severity spelled out
  (High/Med/Low — no H/M/L shorthand).

## Rules

- **Symbol budget** — a prime evolution (`X'`→`X''`) survives **one** generation; the next
  supersession renames/consolidates instead of adding another prime. Introducing a second
  staging/tier scheme alongside an existing one requires a one-line statement of their relation
  at first use, and its letter must not collide with the list above.
- **Modules and parts are named** (the name carries the meaning); `Mod<n>` / `Part <n> (<名>)`
  only when a table/diagram needs a compact id — never bare `M<n>`/`D<n>`/`P<n>` for them.
  Mermaid node ids are diagram-local — exempt.
- **Cross-scheme mappings are recorded downstream→upstream only**, each in its doc's designated
  field (design「How it meets」· detail 可追溯 · plan `Implements:` · test Coverage rows ·
  `ADR-NNNN D<n>`); the reverse map is derived (grep / M3), never hand-maintained — an upstream
  doc doesn't list who cites it (same one-way principle as workflow→KB links; M2 propagates
  along exactly these fields).
