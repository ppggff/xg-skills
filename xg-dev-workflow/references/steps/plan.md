# Step: 实现 plan

Forked from **planning-and-task-breakdown**. Adjusted: output is this requirement's
`plan.md` (explicitly **mutable**, vs the frozen `design.md`); tasks reference design ADRs;
verification respects the project's test-execution policy (e.g. cbdb's "describe, don't run").

Output: `plan.md` (template: `references/templates/plan.md`).

## Procedure
1. **Read-only first** — re-read `design.md` + ADRs + `detail.md` (if the 详设 phase ran);
   map dependencies between the pieces they call for. **Don't redefine structures here** —
   tasks *reference* `detail.md` for schema/algorithm/signatures ("implement the `<SomeTable>`
   schema, 详设 §数据结构"), not restate them. If there's no `detail.md` and the structures are
   non-trivial, consider running `detail` first.
2. **Dependency graph** — order bottom-up: build foundations first.
3. **Slice vertically** — each task is one complete path that leaves the system working
   and testable, not a horizontal layer ("all the schema", "all the API").
   **Wide-refactor exception (expand–contract, from `to-tickets`):** one mechanical change whose
   blast radius fans across the whole codebase (rename a column, retype a shared symbol) can't
   land green as a vertical slice. Sequence it instead: **expand** (add the new form beside the
   old — nothing breaks) → **migrate** in batches sized by blast radius (per package/dir; each
   batch one task blocked on the expand, checks stay green because the old form still exists) →
   **contract** (delete the old form once no caller remains, blocked on every migrate batch).
4. **Write tasks** with: description, **the `R-id`(s) it implements** (traces to `requirement.md`
   「需求条目」), acceptance criteria (testable), verification (test/build/manual), dependencies,
   files likely touched, scope (XS–L; L → split). A task title containing "and" is usually two
   tasks. Cross-check: every `R-id` is implemented by ≥1 task.
5. **Checkpoint** every 2–3 tasks (builds/tests green, end-to-end works).
6. **Risks & open questions** table.
7. **Execution-authorization ask** — present via the gate digest (`gate-digest.md`); for this
   gate the cards are: scope of what will be touched (files/modules), the riskiest slices, the
   test mode chosen, any plan-level open risk, and a one-line **model tip** — the execution
   zone is spec-driven work suited to a cheaper session model: after go, optionally switch
   `/model sonnet` + `/advisor opus` (Sonnet executes; Opus is consulted at decision points;
   subagents inherit the advisor), ideally in a fresh session (`resume <slug>`); switch back
   when re-entering a decision gate. The human's go here is the one-time autonomy
   handoff (SKILL.md「Two zones」). May arrive merged with the 详设 baseline when the human
   opted in (SKILL.md「Requirement sizing」Gate merging).

Guardrail: this plan must stay faithful to the frozen design. If planning reveals the
design is wrong, **stop and run change-management (M2)** — don't quietly diverge. The plan is
freely editable, but task churn (delete / merge / defer, or invalidating an `[x]`) is logged to
`log.md` per M2 case B (`change.md`; routine refinement is silent).

## Runtime override
`plan use:agent-skills:plan` or `use:<your-skill>`.

## Done when
- Every task has acceptance + verification + scope; order respects dependencies;
  checkpoints exist; plan traces to the design. Then run the omission check (M3).
