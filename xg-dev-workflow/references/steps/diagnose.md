# Step: diagnose (the front door for defect localization)

Forked from **diagnosing-bugs** (feedback-loop-first debugging discipline). Adjusted: KB-first
entry (M5) + M1 evidence on every causal claim; the fix lands through **Prove-It** as an 实现
slice, never patched from inside this step; temporary instrumentation is allowed but tagged and
swept; durable findings route to the KB.

`investigate` answers "how does existing code behave"; `diagnose` answers "**why is observed
behavior wrong**" — a bug, a crash, a perf regression. An empirical question with no defect →
investigate's Spike; a defect → this step.

**Context branching (same shape as investigate):** active requirement (bug found in 实现/测试)
→ runs inside the execution zone — the fix is an 实现 slice, findings land in `progress.md`
Discovered issues; standalone → report + KB capture, and the fix waits for an explicit human go
(propose the diff, don't apply — the same boundary as investigate). Investigate's anchoring rule
applies (active only by explicit linkage; default standalone).

## Phase 1 — build the feedback loop (this is the skill)

Before any theory: **one command with a tight pass/fail signal that goes red on *this* bug.**
Bisection, hypotheses, and instrumentation all just consume it. Spend disproportionate effort
here — be aggressive and creative, and don't give up on the loop; build the right one and the bug
is mostly found.

Construction menu, roughly in order: failing test at whatever seam reaches the bug → CLI/HTTP
invocation with a fixture input, diffed against known-good → replay of a captured trace/payload
through the code path in isolation → throwaway harness (minimal subset of the system, one
function call) → property/fuzz loop (for "sometimes wrong output") → bisection harness
(`git bisect run` between two known states) → differential loop (same input through old vs new
version, diff outputs) → HITL script as last resort (a human must click → drive *them* with a
structured loop).

- **Trap rule:** catching yourself reading code to build a theory before this command exists —
  **stop**.
- **Tighten it:** faster (cache setup, skip unrelated init), sharper (assert the specific
  symptom, not "didn't crash"), deterministic (pin time, seed RNG, isolate fs/network). A
  2-second deterministic loop is a debugging superpower; a 30-second flaky one barely beats none.
- **Non-deterministic bugs:** the goal is a *higher reproduction rate*, not a clean repro — loop
  the trigger, parallelise, add stress, narrow timing windows, until it is debuggable.
- **Genuinely can't build one → stop and say so:** list what you tried; ask for the reproducing
  environment, a captured artifact (log dump, core, trace), or permission to add temporary
  instrumentation. Do not hypothesise without a loop.

**Done when** you can name one command, already run at least once (paste invocation + output),
that is: **red-capable** (asserts the user's exact symptom) · **deterministic** (or pinned-high
repro rate) · **fast** (seconds) · **agent-runnable**.

## Phase 2 — reproduce + minimise

Run the loop; watch it go red on the failure mode **the user described** — a nearby different
failure is the wrong bug and yields the wrong fix. Then shrink to the smallest scenario that
still goes red: cut inputs/callers/config/data one at a time, re-running after each cut, until
**every remaining element is load-bearing**. The minimal repro shrinks the hypothesis space and
becomes the regression test.

## Phase 3 — hypothesise (3–5, ranked, falsifiable)

Generate **3–5 ranked hypotheses** before testing any — single-hypothesis generation anchors on
the first plausible idea. Each states its prediction: "if X is the cause, changing Y makes the
bug disappear / Z makes it worse"; no prediction → discard or sharpen (M1: a hypothesis is 假设
until its prediction is tested). **Show the ranked list to the human** — domain knowledge often
re-ranks instantly ("we just deployed #3"); don't block on it if they're away.

## Phase 4 — instrument

Each probe maps to one prediction; **change one variable at a time**. Prefer debugger/REPL (one
breakpoint beats ten logs) > targeted logs at the boundaries that distinguish hypotheses; never
"log everything and grep". **Tag every debug log with one unique prefix** (e.g. `[DBG-a4f2]`)
so cleanup is a single grep — untagged logs survive. Product-code edits here are **temporary
instrumentation only** (tagged, swept in Phase 6); anything more escalates to the human.

**Perf branch:** for performance regressions, logs are usually the wrong probe — establish a
baseline measurement (timing harness, profiler, query plan), then bisect. Measure first, fix
second.

## Phase 5 — fix via Prove-It

Write the regression test **before** the fix, at a **correct seam** — one where the test
exercises the real bug pattern as it occurred at the call site (a too-shallow seam gives false
confidence). **No correct seam is itself a finding** — record it: the architecture is preventing
the bug from being locked down (a deepening candidate for the roadmap). Then: failing test →
fix (an 实现 slice when a card is active; standalone: propose the diff and wait) → test passes →
re-run the Phase-1 loop on the **original, un-minimised** scenario.

## Phase 6 — cleanup + capture

- [ ] Original repro no longer reproduces (Phase-1 loop green)
- [ ] Regression test passes (or the no-seam finding is recorded)
- [ ] All tagged instrumentation removed (grep the prefix); throwaway harnesses deleted
- [ ] The winning hypothesis stated in the fix's commit message — the next debugger learns
- [ ] Durable findings (mechanism, invariant, trap) → KB via xg-knowledge-lite Write; card
      active → `progress.md` Discovered issues row

Then ask: what would have prevented this bug? An architectural answer (no good seam, tangled
callers, hidden coupling) → a roadmap/KB note, written **after** the fix is in — you know more
now than when you started.

## Runtime override
`diagnose use:diagnosing-bugs` (the source skill) or `use:<your-skill>`.

## Done when
Phase-6 checklist all checked. Then run the omission check (M3). Log usage `--action diagnose`
(both contexts — like `review`, a diagnosis inside a requirement is still a diagnosis).
