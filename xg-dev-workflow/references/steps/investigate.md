# Step: investigate (the single front door for any code investigation)

This is the entry point the **global CLAUDE.md** routes *every* investigation to —
"调查 X", "how does Y behave", a concurrency/runtime/feasibility question, probing an
Open question. It does not introduce new rules; it **composes** two existing mechanisms
and branches on whether a requirement is active:

- **M1 evidence discipline** — `evidence.md` (the whole point of routing here).
- **M5 code understanding** — `understand.md` (concept-first, layered, KB-first).

## The discipline this verb enforces (M1, non-negotiable)
Base **every** conclusion on verified evidence from the actual code/tests. Never assume:
- **runtime values / concurrency behavior** — read the code path that runs, don't reason from a name;
- **function-pointer / hook / vtable targets** — a current assignment is not a constraint (swappable seam);
- **`#ifdef` / build gating** — confirm the cited code is live in the target build;
- **upstream library defaults** — a patched fork (Cloudberry/Greenplum on PostgreSQL) may have changed lock modes, defaults, call paths.

When something can't be verified, write `UNVERIFIED: …` explicitly rather than concluding.
For any "can't / infeasible" verdict, apply the **Feasibility-claims** guard in `evidence.md`
(mutable code, execution context, swappable seams, look-alike identities, verify the
subagent's *inference* not just its facts). For any negative result, apply the
**Negative-results** rule (search the symbol across all file types — incl. build configs,
catalog `.dat`/`.bki`, and registration sites — distinguish same keyword across modules/layers,
phrase as query-scoped). A negative that **justifies building new plumbing** must additionally
reach VERIFIED by a hop-by-hop trace before it earns that code (evidence.md **birth-certificate
rule**) — a query-scoped negative isn't enough there. For a verdict resting on a
function-pointer/hook seam, first dispatch
an agent to enumerate **every** registration/assignment site (evidence.md swappable-seam rule).

Before stating any feasibility or runtime/concurrency conclusion, produce the **claims table**
(Claim | Evidence `file:line` | VERIFIED/INFERRED/GUESS) from `evidence.md` — never assert on a
GUESS/INFERRED row; investigate it to VERIFIED first or carry it as `UNVERIFIED:`.

## Analysis, not just grep (logical reasoning is the deliverable)
grep/read **gather** evidence — they are not the answer. The output of an investigation is a
**logical analysis**, so you must:
- **Trace the path that actually runs** (control + data flow) end-to-end, not pattern-match on
  names: which function really executes at the seam, what value flows in, what each branch does.
  "N grep hits" is raw material, not a conclusion.
- **Build the causal chain** — state *why* the behavior happens, mechanism step by step; don't
  assert "it deadlocks / is safe / can't happen because X" without tracing X to the effect.
- **Apply the Synthesis lens** (`understand.md`: layer × module × hook × relationship) to fold the
  scattered facts into one structural judgment — where responsibility actually lives, the
  chokepoint, how cost/risk propagates.
- **Reason, then label** in the claims table: an INFERRED row is a *reasoning step* that itself
  needs checking, not merely a missing citation (re-derive it, per `evidence.md` verify-the-inference).
If you can only report what you grepped, you searched — you didn't investigate.

## Spike — a throwaway probe when reading can't settle it

Some questions are **empirical**: runtime/planner/API behavior that code-reading alone leaves
INFERRED (e.g. "is this qual pushed down in a dispatched plan?", "what does this hook receive at
runtime?"). Instead of parking a 待验/落地前验 row, run a **spike** — throwaway code that answers
the question (adapted from the `prototype` skill):

1. **Throwaway from day one, outside the product tree** — scratchpad or a clearly-marked
   disposable path; never committed. This keeps the verb's read-only-on-product-code contract:
   a probe that requires modifying product code to run is not a spike — that's implementation,
   escalate to the human.
2. **One command to run**; no persistence, no polish beyond runnable.
3. **Surface the observed state** — the probe prints what it saw; the run output is the evidence.
4. **The answer is the only deliverable**: it upgrades the claims-table row to VERIFIED (evidence
   = probe + output), lands in the notes/KB via the normal routing, and the probe code is deleted.

A **defect is not a spike question**: observed-wrong behavior (bug, crash, perf regression)
routes to the `diagnose` verb (`diagnose.md`, feedback-loop-first localization) — a spike
answers a neutral empirical question; a diagnosis chases a failure.

## Procedure
1. **Query the KB first** — open with an `xg-knowledge-lite` **Orient** pass (project-scoped
   warm-up: `wiki/index.md` section + `CONTEXT-MAP.md` + uncompiled-raw count) so you know which
   concepts exist, then Query/drill the relevant ones (concept → Sources raw). Prefer KB facts
   over training-data guesses; don't re-investigate what's already recorded. (Orient here is the
   warm-up step of this run — covered by this run's log record, not logged separately.)
2. **Investigate read-only** under full M1 — Explore subagent for targeted grep/read, or Plan
   Mode for a broader layered survey (see `understand.md` Layers + Synthesis lens). When you
   dispatch a subagent, put the Negative-results rule **in its prompt**, and re-derive any
   load-bearing negative/infeasibility yourself.
3. **Record + log — branches on context:**

   **What counts as "active" (anchoring rule, 2026-06-12):** a requirement is active **only by
   explicit linkage** — the human named the requirement (slug/NNN, or its topic unambiguously)
   in this ask, or this session was entered via `resume <slug>` / a phase verb for it. Mere
   existence of an in-flight requirement, topical relevance, or recency does **not** make it
   active — **default to standalone**. Don't retro-anchor: if a standalone finding later matters
   for a requirement, that requirement's design cites the notes/KB entry with a one-line link.
   The branch only affects *recording* (where notes land, which doc gets a row, which `--action`
   is logged) — the investigation itself is identical, so ambiguity never blocks investigating;
   if genuinely torn, ask one question **at recording time**, not before.
   (**Deliberately stricter than `review`'s anchoring:** a review target objectively IS some
   card's implementation — its commits can be checked against the board — so review asks when
   the match is plain; an investigation topic is merely *about* something a card also touches,
   and topical auto-anchoring would guess wrong, so investigate defaults standalone.)

   - **A requirement is active** → this **is** that requirement's M5/design step. Anchor it to
     the requirement dir (scratch in `notes/`), record verdict + evidence in `progress.md` →
     *Design iterations*, route reusable module truth to the KB (`[[wiki/<project>/<slug>]]`).
     Log `--action design`. **Stop at the phase boundary** — results inform design; do not roll
     into writing/freezing `design.md` (Stop-at-gate rule).
   - **No active requirement (standalone)** → capture reusable findings to the KB via
     `xg-knowledge-lite` Write (raw → compile if it shifts a concept); answer the human.
     Any scratch/phase notes go to `<dev_root>/<project>/investigations/` (see Cadence
     below) — **never into the repo**. Log `--action investigate`. No requirement dir is created.

## Cadence for a large/multi-step investigation
A broad question (many subsystems, several open sub-questions) is run **in phases**, not in one
shot:
1. Split it into named phases up front (e.g. "1 registration sites · 2 execution context · 3 lock
   path"). State the plan.
2. After **each** phase, append a concise findings summary — its claims table + verdict-so-far +
   what's still open — to a notes file, then **pause for the human's confirmation before the next
   phase**. Notes file:
   - requirement active → `<requirement>/notes/investigation-<topic>.md` (the prefix stays
     here — `notes/` doesn't self-describe; rolls up into `progress.md` Design iterations at
     the end);
     standalone → `<dev_root>/<project>/investigations/<topic>.md` (**no investigation-
     prefix** — the dir already says it; SKILL.md Layout). A large multi-phase investigation
     graduates to the **campaign dir** form `investigations/<topic>/` — charter + per-phase
     notes + progress — instead of one ever-growing file.
     **Never write scratch into the repo** (repo CLAUDE.md: new work → dev_root + KB only).
     Once findings are durable, compile them to the KB; the scratch may then be kept or removed.
3. Don't pre-conclude across the pause — each phase's table feeds the next; the final verdict
   waits until the human says continue and the last phase closes.

A small, single-question investigation skips the phasing — answer it under the discipline above
and record once. Phase only when the scope genuinely warrants checkpoints.

`investigate` never edits product code and never advances a phase — it only produces
understanding and a recorded evidence trail.
