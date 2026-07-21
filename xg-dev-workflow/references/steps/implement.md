# Step: 实现 (execute)

Forked from **incremental-implementation** (the test-after cycle) **+ `tdd`** (the red-green loop),
with the **Prove-It** bug pattern from **test-driven-development** — this phase carries **both**
cycles, picked per project (see Test mode). Adjusted: progress is logged to this requirement's
`progress.md`; respects cbdb change rules (minimal, module-local, reversible; no ABI/interface
changes unless requested) and its "describe, don't run" execution policy.

Updates: `progress.md` (template: `references/templates/progress.md`); code in the repo.

## Environment recon before the first slice
Before slice 1, establish and **record in `progress.md`** the exact build/test invocation
(toolchain location, container/exec wrapper, check command, baseline suite status) — resume must
be able to rebuild and re-verify from `progress.md` alone. Two hard-won specifics
(2026-07-11 retro): **run the baseline suite first** (a green baseline is what makes your first
red meaningful), and **never filter build output to errors only** — an implicit-declaration
*warning* is a load-time `undefined symbol` in a shared library; surface warnings on every build.

## Test mode — TDD vs test-after (decided per project)
Pick the mode from the project's **test-execution policy** and **record it in `progress.md`**
(State at a glance) so resume continues in the same mode:
- **Project runs tests by default** (most Go/TS/etc. repos — HatchDeck-style) → **TDD mode**
  (test-first, red-green observed).
- **Project is "describe, don't run"** (e.g. cbdb — tests are *described*, executed only when the
  human asks) → **test-after mode** (you can't *observe* red→green without running, so write the
  test after/alongside the code and defer the run).
- **Policy unknown or ambiguous → ask, don't infer.** No recorded policy (project CLAUDE.md, KB,
  a prior card's `progress.md`) → ask the human which mode **before slice 1**; record the answer
  in `progress.md` and capture it as the project's standing policy (project CLAUDE.md or KB) so
  the next card doesn't re-ask.

Both modes are **vertical / per-slice** — never "all code, then all tests" (that yields tests of
already-written, imagined behavior). They differ only in **intra-slice ordering** and **whether
red→green is observed now**. Unsure which mode → ask once, then record it.

### Cycle A — TDD mode (red-green loop from `tdd`; Prove-It from `test-driven-development`)
Per task slice: **RED → GREEN → REFACTOR → record → commit → next**.
1. **RED** — write a failing behavior test for the slice's acceptance criterion. It **must fail**
   (a test that passes immediately proves nothing). **Bug fix → Prove-It:** reproduce the bug with
   a failing test *before* attempting the fix.
2. **GREEN** — the minimal code to make it pass; don't over-engineer (P0).
3. **REFACTOR** — with tests green: extract duplication, **deepen modules** (small interface over
   deep implementation — the `codebase-design` skill has the vocabulary + testability checks), apply
   SOLID where natural; rerun the tests after each refactor step. **Never refactor while RED.**
4. **record** in `progress.md` → **commit** (one concern) → next slice.
Acceptance `[x]` only once the test is **observed passing**.

### Cycle B — test-after mode (forked from `incremental-implementation`, for "describe, don't run")
Per task slice: **Implement → Test → Verify → record → commit → next**.
1. **Implement** the smallest complete slice (P0 simplest-thing-that-works).
2. **Test** — write the behavior test right after the code (or, where it can't be authored without
   running, *describe* it); list the exact run commands as **suggested steps**, don't execute.
3. **Verify** — build/type/lint where those are runnable; the test's pass/fail is **deferred** —
   mark acceptance **`[ ]` until the human runs it**.
4. **record** in `progress.md` → **commit** (one concern) → next slice.

**Binary verify (both modes)** — acceptance is `[x]` (a test was **observed** passing) / `[!]`
(failed) / `[ ]` (unverified — includes "written but not yet run" in test-after mode). **No
subjective `[x]`**: a criterion has an observed-passing test or it doesn't.

## Autonomy (this phase runs without per-task gates)
Once the human says go on an approved plan, **roll through the slices autonomously — don't stop to
ask after each task.** The design/detail/plan gates already happened; the plan is mutable and yours
to refine. **Own the implementation-level decisions** (which local structure, naming, error path,
how to satisfy a `detail.md` contract): just make the call, ground it in evidence (M1), and record
it. Only **pause and escalate** when:
- a **design- or requirement-level fork** appears (the design looks wrong, or an `R-id` is
  ambiguous/contradicted) → stop and run change-management (M2); never fix it by quietly bending
  `design.md`;
- you're **blocked** (missing access/decision only the human can give); or
- a **`push`** is wanted — push is human-gated, so ask (per-task *commits* are autonomous; see Commit cadence).
Don't stop after each slice **nor** at the implement→test→评审 phase boundaries: this is the
**execution zone** (SKILL.md「Two zones」 + the Stop-at-gate carve-out), so on the one "go" you flow
implement → test → produce the M+ close-out review **report**, and your next *scheduled* human touch
is that report's fix decision — not a per-task or per-phase check-in. The design/详设 freeze was the
last binding human decision; `plan.md` was the one-time autonomy handoff.

## Harness task list (display mirror)
At the execution "go", TaskCreate one harness task per plan `T<n>` (+ the Final simplify sweep);
TaskUpdate in_progress/completed at the same beats as the `progress.md` updates. **Display-only
mirror**: `progress.md` remains the resume truth — never read the harness list as state (a fresh
session rebuilds it from `progress.md`, see `resume.md`). Other long-running walks (an
investigate campaign's phases, diagnose's phases, a large M2 affected-set) may mirror the same
way, under the same rule.

## Commit cadence
- **Commit after each task** once the slice is complete and its runnable checks pass — acceptance
  `[x]` in **TDD mode**, or `[ ]` pending-run in **test-after mode** (build/type/lint green, test
  written/described) — and **after each review fix** (when applying close-out-review fixes). **One
  concern per commit** (P1), additive & revertable (P5) — a clean per-task history is part of the
  autonomous run, and it's what lets a single task be reverted later.
- **Task-tag the subject, card-qualified** — a per-task product commit's subject carries
  `(<NNN> T<n>)` (e.g. `viewer: quick-open exact-substring operator (005 T3)`); a review-fix
  commit cites the finding instead (`(005 review #2)`). This is the last link of the derived
  trace chain — `workflow-status.py --trace` resolves R→task→commit through it; a bare `T<n>`
  without the card NNN collides across cards and only rates a loose match.
- **Commits are autonomous local commits** — don't ask before each (this cadence is the human's
  standing authorization for the execution zone). **`push` stays human-gated** — the irreversible,
  outward act — never push without an explicit request (global Git & MR Safety).
- **History is append-only:** new work = new follow-up commits; never amend / rebase / squash an
  already-made commit unless the human asks.
- **Respect an explicit project no-commit policy** if one exists (then checkpoint + ask instead);
  absent that, the per-task / per-fix cadence is the default. English commit message following the
  project's convention.

## Principles (P-rules; P — R stays reserved for requirement 条目)
- **P0 简单可靠 (首要)** — the simplest thing that is *reliable*; simple = easy to implement,
  test, and verify-correct. No abstraction before the third use; don't chase elegant-but-complex.
- **P0.6 Carry design qualities forward; don't over-handle anomalies** — performance / scale-up
  performance / testability / observability are set at design time — keep them in view, don't drop
  them in implementation. But **don't re-handle anomalies the design already eliminated or
  assigned** — implement the fallback the design specified, no redundant extra guards (反过度设计).
- **P0.5 Scope discipline** — touch only what the task needs; note adjacent issues, don't
  fix them (spawn a new requirement/KB note instead). Orphan asymmetry: clean up what your
  own change orphans (imports / variables / functions it made unused); pre-existing dead
  code stays — note it, don't delete unless asked.
- **P1 One thing at a time** — don't mix concerns in one increment/commit.
- **P2 Keep it compilable** — system builds and existing behavior holds after each slice.
- **P5 Rollback-friendly** — additive, independently revertable increments.

## Review lens (apply before marking a slice done)
Slice-level self-review lives here; a formal review of the whole change (at phase end /
before merge) goes through the `review` verb (`review.md`) instead.
Self-review against the angles that catch real systems bugs — verify each against code, not memory:
- **Safe, not just live** — for any "skip / ignore / optimize-away" decision, classify it as safety vs liveness; prefer fail-safe (defer / refuse / block) over fail-unsafe (proceed on a guess). State whether a residual imperfection self-heals and on what that depends.
- **Upstream-replication completeness** — when code mirrors kernel/library logic, enumerate ALL branches of the original (not just the obvious one) and replicate each; then audit EVERY site that copies the pattern, not only the one in hand.
- **Pattern-sweep on fix** — when a bug stems from a repeated pattern in-repo (a misused shared class/idiom, a copy-pasted call shape), grep and fix EVERY instance in one pass — not just the one reported; weigh hardening the shared primitive so the pattern can't recur. (A user re-reporting "still broken over here" after a one-spot fix is the signal you skipped the sweep.)
- **Authority / namespace ownership** — a value owned by one node/space is validated by that authority; consumers record it, never re-derive a guard in the wrong space (e.g. no cross-XID-space comparison).
- **Concurrency** — any decision using a snapshot taken before a lock can race with concurrent mutation between snapshot and use. **Read-then-write / check-then-act is atomic only inside one transaction**: a connection-pool serialization cap (e.g. `SetMaxOpenConns(1)`) serializes individual statements, not multi-statement sequences — the connection returns to the pool between calls, so a concurrent request can interleave between your read and the dependent write. Wrap dependent read→write in a single tx, or collapse to one conditional statement.
- **Lock discipline** — no blocking syscalls / I/O (e.g. fsync) under an LWLock.
- **Dead abstraction / deletion test** (`codebase-design`) — is each hook/abstraction load-bearing? **Delete it in your head:** if complexity vanishes it was a pass-through (remove it); if it reappears across N callers it earns its keep. One adapter = hypothetical seam, two = real — don't keep a seam/port that only ever has one implementation. **Same test on a new function's own generality — caller audit:** for each new static/private function, check every parameter (and mode/branch) against its actual callers; a parameter every caller passes constant/NULL, or a mode no caller reaches, is unused generality — delete it and add it back when the second caller needs it (YAGNI, P0). (2026-07-21: a 4-value dispatch helper whose only caller always asked for 2.)
- **Causal chain** — don't claim "it deadlocks / works because X" without tracing the mechanism.

## Simplify sweep (once, after the last slice — M+; XS/S may skip)
All slices done and checks green → run one **behavior-preserving** simplification pass over the
whole change — reuse, dead code, altitude/abstraction cleanups, a final comment pass — with the
green suite as the safety net; re-run the full suite after; commit it separately (P1). Bindable:
`use:simplify` (or a code-simplifier agent). The per-slice guards (P0, deletion test) still apply
during slices — the sweep is the whole-diff pass they can't do.
**"Whole change" = the card's whole diff vs its integration point** (`origin/<main>` or the
merge-base with it), the same base the close-out review pins (`review.md` step 1) — **not** the
last session's slices. A multi-session card is the trap: sweeping only the latest commits leaves
earlier sessions' reuse/dead-code/altitude untouched. `git diff $(git merge-base origin/<main>
HEAD)..HEAD` is the diff to sweep.
- **Reuse/cohesion is the sweep's core — a comment pass is not a sweep** (2026-07-21 retro, card
  002: a sweep run as a one-line lint nit let two reuse/cohesion misses reach the human). When the
  change added helpers/abstractions, the pass must concretely answer, over the whole diff:
  - **New helper/constant → grep the touched module for the same logic first.** A new `arch→prefix`
    helper beside an existing one that already computes it is a *merge*, not a new method.
  - **New cross-cutting concern → match the shape of its just-built sibling.** If this change made
    concern X a backend/interface hook, concern Y of the same shape is a hook too — not an
    `if type == :foo` special-case in the caller.
  A comments-only sweep diff on a change that introduced helpers/abstractions didn't run: state
  the reuse/cohesion you checked, not just "swept".
**test-after / "describe, don't run" projects: non-structural cleanups only** (comments, dead
code, naming) — a structural refactor without a runnable net carries asymmetric risk; note the
skipped candidates in `progress.md` for the human. Record the sweep (or its skip) in
`progress.md`; then 测试.

## Diagnosis (when a fix isn't landing)
- **Stop blind-iterating on a black-box dependency after ~2 misses — read its shipped source.** Two failed guesses at *why* a third-party component (CSS / renderer / library) misbehaves means you're modeling it wrong; open its shipped CSS/JS/source for its actual model instead of guessing a third time. (HatchDeck MS2: 5 blind CSS iterations failed on a tmux-green background; the fix came only from reading `@wterm/dom`'s shipped CSS — `.term-grid` inherited the bottom-right cell's color. Same shape in MS1/MS3 — prior-art source drove the ADRs; don't assume a dep's capabilities, e.g. modernc JSON1.)
- **If a bug reproduces on the reference engine, it's your code, not the platform.** A symptom you'd pin on the target platform (mobile Safari, a specific OS) that *also* reproduces on desktop Chromium is your own logic — use the reference engine as a forensic oracle: read computed styles / bytes / values on both for differential diagnosis, get ground-truth data on the real device before editing, and don't change what you can't reproduce. (HatchDeck MS2: per-char scroll "vibration" reproduced on desktop → own snap overshooting a 12px padding, not iOS; Chromium-vs-iOS diff proved the green background was iOS-paint-specific.)

## Comment & artifact hygiene
- **Comments** — no references to uncommitted docs (`plan/`, `problem/`, `progress/`, `knowledge/`, `*.md`), no ADR references (`ADR-NNNN` — they live in dev_root), and no specific line numbers (`file.c:NNN`, "line N"); bare file/function names are fine. An **issue/ticket reference is allowed** (a tracker ID or URL — `#1234`, `JIRA-42`, the issue link): it's stable and public, unlike workflow docs, so it's the right anchor when a comment needs to point outward. After editing, run **`tools/check-code-refs.py`** (no args = the working diff's added lines; deterministic — don't improvise a grep) and strip the leaks it reports. Leave pre-existing hits and issue refs (the script doesn't flag those); a hit in a tool whose domain IS the docs (e.g. a KB script naming `index.md`) is legitimate — judge it, don't auto-strip.
- **代码即文档 (code as documentation)** — comments are few but necessary. Allowed set: file/module
  docstring, function docstrings, step/section markers, and **why-notes** for a constraint the code
  can't show (invariant, non-obvious ordering, trap). Nothing that narrates what the next line
  does, restates a docstring, or argues the change is correct. **Density = the surrounding
  file's.** Follow the surrounding code's idioms (prior-art from 详设); don't invent new usage
  without a reason. Both design and code should be clean and elegant.
  Two why-note cases the last review round showed get missed (2026-07-21): a **field/guard with
  several load-bearing uses but no single line naming why it exists** (a reviewer can't tell it's
  load-bearing → wastes a round confirming) — name the why once at its definition; and **code
  that diverges from, or repairs a bug in, a patched-fork upstream** (this tree is PostgreSQL 14.4
  + Greenplum) — a one-line why-note with the **upstream commit SHA** is allowed (a stable public
  anchor, like an issue ref) so a later fork-merge can reconcile.
- **Comment pass (per slice, same sweep as the grep above)** — re-read every comment this slice
  added and delete the ones outside the allowed set. Generation defaults over-comment; the pass is
  mandatory, not optional polish (global CLAUDE.md「Code Comments」states the same rule for all
  projects).
- **Generated test artifacts** — for input/output `.source` tests, the regenerated `sql/*.sql` + `expected/*.out` are gitignored, not committed; edit only the `.source` sources (see project memory for the convention + the input-only edge case).

## Logging to progress.md (M4)
After each slice update: task status table, changed files (+ why), any design iteration or
discovered issue. `progress.md` is the resume contract — keep it current, not a diary.

**Plan churn (M2 case B):** refining a task in place is silent, but **deleting / merging /
deferring a task — or invalidating an already-`[x]` acceptance — gets a one-line `log.md` `[实现]`
entry (what + why)**. Free-to-edit doesn't mean trace-free: a silently-dropped task leaves resume
and the close-out review unable to tell "done" from "forgotten".

## Evidence (M1)
Framework/API-specific code → verify against the authoritative source and cite it (see
`evidence.md`); don't write framework calls from memory.

## Runtime override
`use:agent-skills:build` or `use:<your-skill>`. **`use:tdd`** takes that skill's **red-green loop
only** — skip its Planning step (interface / behaviors-to-test / approval are already frozen by
需求/设计/详设; re-running it would re-litigate the design).

## Done when
- All plan tasks done & verified; `progress.md` current; no out-of-scope churn; **the simplify
  sweep ran (or its skip is recorded in `progress.md`)** — it's a gate item, not optional polish,
  because a skipped sweep is exactly how altitude/dead-code/dup cleanups slip to a later manual
  review (2026-07-21 retro: card 005 shipped 5 such items an end-of-phase sweep would have
  caught). Then run the omission check (M3) and proceed to 测试.
