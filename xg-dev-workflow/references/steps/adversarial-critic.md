# Shared mechanism: adversarial fresh-context critic (the "sharp-cut" finder)

Used by **requirement** (grill), **design-grill**, and **review**; the criterion-conformance
judge (lens 4) additionally serves the 详设 baseline and execution-authorization gates
(「When to run」). A designer grills inside
their own frame and carries the blind spot through, so this mechanism makes the agent reach the
decisive cuts itself: re-derive from the problem, not from the proposal.

Each cut the human made fell into one of five shapes. For each, the move that surfaces it:

| Human cut (example) | Shape | Move that auto-surfaces it |
|---|---|---|
| "a failed delete doesn't lose data" | first-principles causal | **causal-coverage** lens |
| "delete always targets OLD → over-reach can't reach NEW" | composing known invariants | **invariant-ledger replay** lens |
| "use the existing `useChangedAOOpts` field" | find an existing mechanism | **search-before-build** lens |
| "per-file info isn't returned to QD" | unverified load-bearing assumption | **verify-the-assumption** rule |
| "the whole-segment signature lets it be simpler" | apply the problem's structure | **re-apply-the-signature** rule |

## Core move — spawn a fresh-context critic at each grill checkpoint

Don't grill your own proposal only from inside it. At each checkpoint, dispatch a **fresh
subagent that does NOT hold the current design/requirement frame** — give it only `{the problem
+ the specific claim/mechanism under test}` and one mandate: *attack from first principles —
what here is unnecessary, what is missing, what already exists?* A fresh context isn't anchored
to the proposal's assumptions, so it hits the blind spots the author can't see. Run it as a small
panel of fixed lenses — the attack lenses (1–3) at branch checkpoints (which ones per phase —
「When to run」), plus the **criterion-conformance judge** (lens 4) at gate-adjacent
checkpoints — **dispatched by stakes**: an **M+ design's
decision-level checkpoints** default to **one agent per lens, in parallel**; **XS/S designs and
edit-only rounds** default to the **single-agent multi-lens form** (accepting some secondary-lens
satisficing at low stakes — the reasoning below stands for M+; the conformance judge's output
stays a per-criterion verdict list even when folded into one agent). *Why one-each at M+:*
a mixed-mandate agent satisfices on its secondary lenses, and independent contexts
decorrelate blind spots; parallel dispatch keeps wall-clock and token cost roughly flat when
paired with the verified-facts pack below (it removes the only overlap, shared background
reads). Cross-lens composites
(a finding needing two lenses' evidence) are the **orchestrator's** job at adjudication — that
synthesis step exists anyway; don't keep the panel merged for it.

1. **Causal-coverage lens.** Enumerate the *minimal complete* set of causal paths to the
   goal/failure. Demand a **bijection** between what's being built/logged and those causes:
   flag anything that maps to *no* cause (unnecessary), and any cause with *no* coverage
   (a gap). → catches "you're handling something that can't cause the outcome".

2. **Invariant-ledger replay lens.** Load the project's established invariants (the KB
   **invariant ledger** for the subsystem — see below). Test every open concern / proposed
   mechanism against **each** invariant: "does invariant N make this moot or already-handled?"
   → catches concerns the agent treated as open while the pieces to close them were already in
   hand but never composed.

3. **Search-before-build lens.** Before designing any **new** cross-boundary mechanism (a
   signal, flag, propagation path, structure), grep the codebase for an **existing carrier**
   that already does it. → catches "we were about to invent what the system already ships".

4. **Criterion-conformance judge (gate-adjacent).** Runs before **every decision-zone gate ask**
   (需求 confirm · 设计 freeze · 详设 baseline · the execution authorization after `plan.md` —
   gate-digest.md's list) and whenever a round marks a criterion closed. Input is only
   `{the upstream criteria text, the artifact}` — for design freeze the criteria are the
   requirement's 条目 + Effect list; for requirement confirm they are the requirement's **own**
   criteria that the phase claims closed. Mandate: adjudicate **per criterion** — does the
   demanded product actually exist, under the **same enumeration key**, with **all rows present
   and each row evidenced**? Verdicts: `satisfied @<doc §>` / `not satisfied (<what's missing>)` /
   `key-mismatch (<declared key> vs <delivered key>)`. It judges conformance, not quality, and
   **never accepts the artifact's own claims ("已核实" / "done") as evidence** — the author being
   the satisfier is exactly the failure mode it exists to break (the archetype: a writer-axis
   criterion closed with a DDL-keyed probe table and self-ticked "已完成 N 条" — the key swap
   then survived every in-context pass). → catches self-reported satisfaction and silent key
   narrowing.

**Receipts.** Every panel run leaves a one-line receipt — the grill row (`G<n>`) or round it
served, lenses dispatched, one-line verdicts — in the grill-log (or, when the conversation is
the log, in the round's closing message). The gate digest's 已验证 section cites these receipts;
a decision-level checkpoint with no receipt means the panel didn't run, and the gate ask is not
presentable (gate-digest.md). This is enforcement, not bookkeeping: a full requirement + design
cycle once ran with zero dispatches while this file prescribed them, and both gates passed on
self-certified work.

## Three standing rules the orchestrator applies inline (no subagent needed)

- **Verify-the-assumption.** Every load-bearing "X is available / true at point Y" gets an
  investigate (grep + read, or KB) **before** the design leans on it — never assume data
  reaches a place just because it exists upstream.
- **Re-apply-the-signature.** Keep the failure/problem signature (and key constraints) as a
  first-class object and re-apply it to **every** scope / granularity / completeness decision —
  the problem's specific structure often makes the general-optimal answer unnecessary.
- **Class-to-constraint.** The **second** finding of the same *shape* (e.g. two one-sided
  rules, two unguarded wrapper boundaries) is not two bugs — it is an uninstantiated
  **structural constraint**. Name the class, pin it as a rule/invariant in the doc under grill,
  and let subsequent rounds check the rule instead of hunting instances.

## Artifacts to maintain

- **Causal-coverage table** — `cause ↔ mechanism/log`, bijective; the deliverable of lens 1.
- **Assumptions-to-verify list** — each load-bearing assumption + its verification status.
- **Panel receipts** — one line per dispatch (grill row/round · lenses · verdicts); see
  「Receipts」above. Lens 4 additionally leaves its per-criterion verdict list.
- **Verified-facts pack** — the accumulated CONFIRMED findings and positive verifications of
  this grill (claim + `file:func` citation each), kept in the grill log. **Every subsequent
  dispatch attaches the pack and scopes the mandate to the delta + integration seams**; agents
  treat packed facts as given (spot-check only when a new finding contradicts one), never
  re-derive them from scratch. This is what keeps multi-round grills from re-verifying the
  same kernel chains three times.

## The invariant ledger (per subsystem, lives in the KB)

Lens 2 only works if the invariants are written down. Maintain a per-subsystem **invariant
ledger** as a curated KB doc (`[[wiki/<project>/<subsystem>-invariants]]` — a CONTEXT-MAP-class
project doc: directly appended, evidence-cited, **not** a recomputed concept): one line per
established invariant. The design/grill/review steps **load and replay it**.
After an investigation establishes a durable invariant, add it to the ledger — that is how the
agent's starting point gets sharper over time.

**Maintain it as you go, not at as-built.** An invariant confirmed during a grill/adjudication
lands in the ledger **in the same session** (one evidence-cited line); do not defer the ledger
to implementation landing. Deferral is what forces the next round's agents to re-verify from
zero. (Concept articles may still wait for as-built;
the *ledger line* may not.)

## Honest limit

Domain intuition (sensing *which* symbol exists, *which* simplification the structure permits)
isn't fully automatable. These moves **trigger the search and re-derivation** that approximate
it; they surface *more* of the cuts autonomously, not all. The thicker the KB ledger and concept
notes, the better the starting points — invest there.

## When to run

- **requirement grill** — lenses 1 (causal, against the *real* intent/effect) + 3, and the
  three standing rules, at each branch checkpoint; lens 2 once the touched subsystem is known;
  lens 4 before the confirm ask (against the requirement's own claimed-closed criteria).
- **design-grill** — full attack-lens panel + the standing rules at each design-tree
  checkpoint, before freezing; lens 4 before the freeze ask (against requirement 条目 + Effect).
  **Tiered:** the full panel targets **decision-level** checkpoints (a new or changed
  ADR-class mechanism). A doc **rewrite that implements an already-grilled decision** gets a
  **lightweight consistency pass** instead: one agent (Agent tool `model: sonnet`, low
  effort — SKILL.md「Subagent model assignment」), mandate =
  hunt surviving old-semantics text and doc↔doc contradictions (no kernel re-verification);
  escalate a finding to code-verification only when it implicates code truth.
- **详设 baseline · execution authorization** — no attack-lens panel of their own (these phases
  run no grill); lens 4 only, before the gate ask, against that gate's criteria — 详设: the
  design decisions/contracts the detail claims covered; plan: the R-id/design↔task trace the
  plan claims complete.
- **review** — the three attack lenses are fixed members of the lens fan-out (see `review.md`).
