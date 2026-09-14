# Step: diagnose — the front door for defect localization

`investigate` answers "how does existing code behave"; `diagnose` answers "**why is observed behavior
wrong**" — a bug, a crash, a perf regression. A neutral empirical question with no defect is
investigate's spike. Forked from **diagnosing-bugs** (feedback-loop-first), with KB-first entry, the
evidence rule on every causal claim, and the fix landing through Prove-It as an ordinary slice.

**Context**: on an active card (defect found while executing) the fix is an ordinary slice and the
findings land in `design.md`「待解问题与证据」/ the plan; standalone → report + KB capture, and the fix
waits for an explicit go (propose the diff, don't apply). Anchoring as in `investigate.md` step 3.

## Phase 1 — build the feedback loop (this is the skill)

Before any theory: **one command with a tight pass/fail signal that goes red on *this* bug.**
Bisection, hypotheses and instrumentation all consume it; spend disproportionate effort here and
don't give up — build the right loop and the bug is mostly found. Menu, roughly in order: a failing
test at whatever seam reaches the bug → a CLI / HTTP call with a fixture input diffed against known-good
→ replaying a captured trace / payload through the path in isolation → a throwaway harness (one function
call) → a property / fuzz loop ("sometimes wrong") → `git bisect run` between two known states → a
differential loop (same input, old vs new) → a human-in-the-loop script as last resort.
- **Trap rule**: catching yourself reading code to build a theory before this command exists — stop.
- A wrapped tool's signal is its own per-run log directory, not the wrapper's stdout or a FATAL grep.
- **Tighten**: faster (cache setup, skip unrelated init) · sharper (assert the exact symptom, not "didn't
  crash") · deterministic (pin time, seed RNG, isolate fs / network). A 2-second deterministic loop is a
  superpower; a 30-second flaky one barely beats none.
- Non-deterministic bugs: aim for a **higher reproduction rate**, not a clean repro — loop the trigger,
  parallelize, add stress, narrow timing windows until it is debuggable.
- Genuinely can't build one → stop and say so: list what you tried; ask for the reproducing
  environment, a captured artifact (log dump, core, trace) or permission to add temporary
  instrumentation. Never hypothesize without a loop.

**Done when** you can name one command, already run at least once (paste invocation + output), that is
**red-capable** (the user's exact symptom) · **deterministic** (or a pinned-high repro rate) · **fast**
(seconds) · **agent-runnable**.

## Phase 2 — reproduce, then minimize

Watch the loop go red on the failure **the user described** — a nearby different failure is the wrong
bug and yields the wrong fix. Then cut inputs / callers / config / data one at a time, re-running after
each cut, until every remaining element is load-bearing: the minimal repro shrinks the hypothesis space
and becomes the regression test.

## Phase 3 — hypothesize (3–5, ranked, falsifiable)

Generate 3–5 ranked hypotheses before testing any — a single hypothesis anchors on the first plausible
idea. Each states its prediction ("if X is the cause, changing Y makes it disappear / Z makes it worse");
no prediction → discard or sharpen (a hypothesis is 假设 until tested). Show the list to the human — domain
knowledge re-ranks instantly ("we just deployed #3") — without blocking on them.

## Phase 4 — instrument

One probe per prediction, **one variable at a time**. Debugger / REPL (one breakpoint beats ten logs) >
targeted logs at the boundaries that separate hypotheses; never "log everything and grep". Tag every
debug log with one unique prefix (`[DBG-a4f2]`) so cleanup is a single grep. Product-code edits here are
temporary instrumentation only — tagged, swept in Phase 6; anything more escalates. **Perf regression**:
logs are the wrong probe — baseline measurement (timing harness, profiler, query plan), then bisect.
Two heuristics when a fix isn't landing: after ~2 wrong guesses about a black-box dependency (CSS,
renderer, library) read its shipped source instead of guessing a third time; a symptom you would pin on
the platform that also reproduces on the reference engine is your own code — use the reference as the
forensic oracle and don't change what you can't reproduce.

## Phase 5 — fix via Prove-It

Regression test **before** the fix, at a **correct seam** — one that exercises the bug pattern as it
occurred at the call site (a too-shallow seam gives false confidence). No correct seam is itself a
finding — the architecture prevents locking the bug down — record it as a roadmap candidate. Then:
failing test → fix (a slice on an active card; standalone: propose and wait) → test passes → re-run the
Phase-1 loop on the **original, un-minimized** scenario.

## Phase 6 — clean up and capture

- [ ] original repro no longer reproduces (Phase-1 loop green)
- [ ] regression test passes (or the no-seam finding is recorded)
- [ ] all tagged instrumentation removed (grep the prefix); throwaway harnesses deleted
- [ ] the winning hypothesis stated in the fix's commit message — the next debugger learns
- [ ] durable findings (mechanism · invariant · trap) → KB via xg-knowledge-lite Write; card active →
      a line in `design.md`「待解问题与证据」

Then ask what would have prevented this bug; an architectural answer (no good seam, tangled callers,
hidden coupling) becomes a roadmap / KB note written **after** the fix — you know more now.

Runtime override: `diagnose use:diagnosing-bugs` (the source skill) or `use:<your-skill>`.
Done when the Phase-6 list is all checked. Log `--action diagnose` in both contexts — a diagnosis inside
a card is still a diagnosis.
