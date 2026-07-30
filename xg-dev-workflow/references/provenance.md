# Step provenance — what each vendored step was forked from

Reference for rebinding/retro work (not needed at run time). Each vendored step in
`references/steps/` is a forked, lightly-adjusted copy of the source skill(s) below; the fork is
ours and editable anytime (see SKILL.md「Step binding」). "Provenance" here = vendoring history —
distinct from the claim-provenance markers (evidence / 推断 / 假设) used in phase docs.

| Step | Forked from | Why |
|---|---|---|
| requirement | interview-me / grill-me + grill-with-docs + spec-driven-development | interactive one-question-at-a-time elicitation of real intent, interleaved with code understanding, docs updated inline, testable success criteria |
| design-grill | grill-with-docs | stress-tests design vs domain model, updates docs inline |
| adr | documentation-and-adrs + grill-with-docs ADR-FORMAT | canonical ADR criteria, lifecycle, minimal template |
| detail | feature-dev code-architect (implementation blueprint) + spec-driven-development PLAN phase | concrete structures + rationale (LLD) between module contracts and task sequencing: component/data-structure design, mechanisms, data flow, critical details |
| plan | planning-and-task-breakdown | vertical-slice tasks, deps, scope sizing |
| implement | incremental-implementation (test-after cycle) + `tdd` (red-green loop) + test-driven-development (Prove-It bug pattern) | per-slice execution in **two modes by project**: TDD red-green where tests run, test-after / deferred-run for "describe, don't run"; thin slices, keep-compilable, rollback-friendly. `use:tdd` overrides with its loop only — Planning is already frozen upstream. |
| test | `tdd` (behavior-via-interface, vertical) + test-driven-development (pyramid / sizes) | **close-out** layer over the skeleton-first `test.md`: coverage + integration/联调/manual + pyramid + results (the per-slice red-green loop lives in 实现) |
| understand | xg-knowledge-lite + Plan Mode / Explore subagent | concept-first, layered comprehension |
| investigate | — (authored inline; composes understand + evidence; **Spike** section adapted from `prototype`) | single front door for any investigation; M1 discipline + context branch; throwaway spike probe for empirical questions |
| diagnose | diagnosing-bugs | feedback-loop-first defect localization: a red-capable repro loop before any theory, 3–5 ranked falsifiable hypotheses, tagged instrumentation, minimise-until-load-bearing; fix routed through Prove-It as an 实现 slice |
| improve | — (authored inline; composes the investigate skeleton + evidence discipline + the adversarial-critic refutation pattern; probe methodology informed by improve-codebase-architecture bare-run observations, not forked) | read-only deepening scan: bounded region, negative list, per-candidate refutation, roadmap-only exit |
| review | review (user skill) + official code-review plugin + code-review-and-quality | lens fan-out; confidence-scored verification (≥80 filter, false-positive exemplars); five-axis menu; KB-context injection + adjudication + positive-verification section from the 2026-06-12 review-session retro |
| evidence | source-driven-development | citation discipline, no guessing |
| change / omission-check / resume / retro | — (authored inline) | not covered by any third-party skill |
