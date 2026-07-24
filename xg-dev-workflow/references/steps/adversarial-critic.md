# Shared mechanism: adversarial fresh-context critic (the "sharp-cut" finder)

Used by **requirement** (grill), **design-grill**, and **review**. A designer grills inside
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
panel of three fixed lenses, **dispatched by stakes**: an **M+ design's decision-level
checkpoints** default to **one agent per lens, in parallel**; **XS/S designs and edit-only
rounds** default to the **single-agent three-lens form** (accepting some secondary-lens
satisficing at low stakes — the reasoning below stands for M+). *Why one-each at M+:*
a mixed-mandate agent satisfices on its secondary lenses, and three independent contexts
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

## Three artifacts to maintain

- **Causal-coverage table** — `cause ↔ mechanism/log`, bijective; the deliverable of lens 1.
- **Assumptions-to-verify list** — each load-bearing assumption + its verification status.
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
  three standing rules, at each branch checkpoint; lens 2 once the touched subsystem is known.
- **design-grill** — full three-lens panel + the standing rules at each design-tree
  checkpoint, before freezing. **Tiered:** the full panel targets **decision-level** checkpoints (a new or changed
  ADR-class mechanism). A doc **rewrite that implements an already-grilled decision** gets a
  **lightweight consistency pass** instead: one agent (Agent tool `model: sonnet`, low
  effort — SKILL.md「Subagent model assignment」), mandate =
  hunt surviving old-semantics text and doc↔doc contradictions (no kernel re-verification);
  escalate a finding to code-verification only when it implicates code truth.
- **review** — the three lenses are fixed members of the lens fan-out (see `review.md`).
