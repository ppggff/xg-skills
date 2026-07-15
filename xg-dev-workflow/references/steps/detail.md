# Step: 详设 (detailed design / LLD)

Forked from **feature-dev `code-architect`** (implementation blueprint) + **spec-driven-development**'s
PLAN phase (the technical plan that spec-driven keeps separate from TASKS). Adjusted: the
artifact is this requirement's `detail.md`; it sits **below** the frozen `design.md` and
**above** the mutable `plan.md`; reusable concepts/terminology still route to
xg-knowledge-lite; the M1 evidence rule (no 望文生义) is enforced; ends with the **baseline
gate** (review, not freeze).

Output: `detail.md` (template: `references/templates/detail.md`).

Read-only on product code: this phase produces `detail.md` only — code changes wait for the
execution authorization at the plan gate.

## Why this step exists

`design.md` is frozen at **module altitude** — it deliberately defers concrete code
(struct fields, SQL, algorithms, signatures). `plan.md` is a **task sequence** (slices, deps,
acceptance) and is the wrong place to *invent* and *justify* those structures. Without this
step the concrete schema/algorithm gets crammed into a task description with no "why", and
the rationale overflows into ADRs that weren't meant to carry it. 详设 is the home for
**concrete structures + their rationale**: it answers "什么结构、为什么" and "怎么操作、为什么".

**Optional.** A structure-light change (XS/S) skips straight to `plan`. Do this step when the
requirement introduces non-trivial data structures, on-disk/wire formats, or multi-step
algorithms whose correctness depends on the details.

## Altitude (lower than design — concrete is required here)

- **Concrete is the point.** Real column names + types + keys + indexes; actual function/hook
  signatures; the real SQL; the step-by-step algorithm with locking and error handling. This
  is exactly what `design.md` forbade — here it is mandatory.
- **Still trace upward.** Every structure/mechanism ties back to a `design.md` module/contract
  and to a requirement 条目 (R-id). If a detail has no design home, the design is wrong → stop and
  run change-management (M2), don't quietly invent architecture here.
- **Division of labour with ADRs** — an ADR records a *hard-to-reverse, surprising decision +
  its alternatives*; `detail.md` holds the *full concrete spec*. For a call that already has an
  ADR, **reference it** ("medium = local table, see ADR-0001") and don't re-argue it. For the
  many small-but-load-bearing choices that don't each merit an ADR (a column's type, the PK,
  hash-load vs point-query, an error path's direction), **justify them here in one line each**.

## Procedure

1. **Read-only first (M1/M5).** Re-read `design.md` + ADRs + requirement 条目 (R-ids). Query
   xg-knowledge-lite for the touched subsystems. Investigate existing code (Plan Mode / Explore
   subagent) for the concrete seams you're about to specify — signatures, existing schemas,
   precedents. Cite evidence (`func()` in `file.c`, KB `[[wiki/<project>/<slug>]]`); mark
   anything unverified `UNVERIFIED` rather than guessing. **Prior-art / 惯用法匹配**: for each
   structure/interface you'll specify, find an existing precedent in the repo (same pattern) and
   follow it — match the surrounding style + project constraints; **don't invent a new usage
   unless necessary, and state the reason when you do**. "Mirror this `file:func`" is the contract
   for the implementer.
2. **Specify data structures.** For each: definition (schema / types / keys / indexes /
   in-memory layout) **and a one-line why**. Cover what makes the structure correct — what each
   field holds, why that type, why that key, what invariant each enforces.
3. **Specify mechanisms / algorithms.** For each key operation: trigger point → step sequence →
   locking/transaction context → error & edge handling → idempotency point. Reference the ADR
   for any decision it embodies. Prefer fail-safe over fail-live; name the safe direction.
4. **Specify code-level interfaces.** Function/hook signatures, the actual SQL/DDL — the
   concrete code `design.md` deferred. Keep them consistent with the design's contract table.
5. **Fill the boundary/error matrix.** missing / concurrent / partial-failure / cancel →
   the behaviour, always pointed at the safe direction. This is where edge cases get enumerated
   *before* the plan slices them.
6. **Traceability.** Each detail item ↔ a design module/contract ↔ a requirement 条目 (R-id). A row
   with no upward link is a smell (either dead detail or missing design).
7. **Baseline gate:** present `detail.md` and STOP for human review. On approval set
   `status: baseline`. Thereafter it is **mutable** — refine it as implementation reality bites,
   but **append a dated note** for each change explaining why. Only when a change implicates the
   *architecture* (`design.md`) does it route back through change-management (M2).
   **Convergence signal for review rounds:** a review/grill round that surfaces only
   detail-level fixes with **no architecture回弹** (frozen `design.md` stays valid) means the LLD
   has converged — bank the fixes and baseline; don't spin further rounds. (HatchDeck M1: 2 detail
   rounds fixed real concurrency gaps D1-12/E1-6, all detail-level → baseline.)

## Relationship to neighbours

- Upstream `design.md` is **frozen**; `detail.md` must conform to it, never silently extend it.
- Downstream `plan.md` **references** `detail.md`: tasks point at the structures/algorithms
  defined here instead of redefining them. A task description should read "implement the
  FloorTable schema (详设 §数据结构)", not restate the columns.

## Runtime override
`detail use:feature-dev:code-architect` (blueprint generation) or `use:<your-skill>`.

## Done when
- Every non-trivial structure and mechanism is concretely specified **with a one-line why**;
  code-level interfaces match the design contract; the boundary/error matrix is filled; every
  item traces to a design module + requirement 条目 (R-id); ADRs referenced (not duplicated);
  `status: baseline`. Then run the omission check (M3).
