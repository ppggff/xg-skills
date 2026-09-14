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
stays a per-criterion verdict list even when folded into one agent). Lens agents follow
SKILL.md「Subagent model assignment」— session model capped at opus (a fable session
dispatches lenses at `model: opus`; the orchestrator adjudicates on the session model). *Why one-each at M+:*
a mixed-mandate agent satisfices on its secondary lenses, and independent contexts
decorrelate blind spots; parallel dispatch keeps wall-clock and token cost roughly flat when
paired with the verified-facts pack below (it removes the only overlap, shared background
reads). Cross-lens composites
(a finding needing two lenses' evidence) are the **orchestrator's** job at adjudication — that
synthesis step exists anyway; don't keep the panel merged for it. **At adjudication, re-measure
a finding's numeric/enumerative factual claims before adopting them** (counts, "all N are X",
corpus-wide absences) — panels sample and misstate totals; the claim's *direction* is usually
right, the *number* often isn't. **Fact layer vs inference layer — direction/attribution/
generalization get the same treatment (026 Req-19):** adopting a finding separates its facts
from the generalization, attribution or direction claims riding them — the latter are the
adjudicator's **own inferences** and need independent grounds, exactly like the numbers.
Two same-shaped instances self-generalized become a **candidate rule put through a grill
ask** (Class-to-constraint below) — never the panel's generalization adopted as given.

**Dispatch closure — load-bearing-premise tightening (024 R4).** The prompt's closure
({problem + claim} + the verified-facts pack) is also the **only legal source for load-bearing
premises** (numbers, durations, scale, environment facts): a premise the dispatcher
synthesizes from anywhere else is marked `UNVERIFIED` inside the prompt or left out. This is a
tightening example of the existing closure, not a new authorization — "it appears somewhere in
a phase doc" never launders a premise into a lens prompt (the 003 accident form: an unsourced
"几个月" reached all four lens prompts). The dispatch template carries evidence.md's existing
**Negative-results duty** into every subagent prompt (a negative result states query + scope —
the wiring point for dispatch-tree misses). Mechanical face = the receipt header's
`premises =` key (「Receipts」).

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
   **Transcription fidelity (discussion-first cards).** At the 需求 confirm / 设计 freeze ask
   the judge additionally audits both directions — forward: every decision-level doc item
   traces to its anchor (ledger row + receipts commit; doc-gate cards: doc § + checkpoint/
   receipts commit), and decision-level items carrying the（落纸补充）marker = 0; reverse:
   every resolved decision row (`→ <id>` / `→ <doc §>` annotation, grill.md) has a doc home.
   夹带/漏记 report as `not satisfied` subtypes (the verdict vocabulary stays three-valued);
   the verdict list + forward/reverse tables land in the receipts; gap rows route to the
   digest's §5 待你判. Input gains {the grill-log's resolved decision rows (`resolved → <id>`
   status cells — grill.md's canonical table) + decisions.md + the human-message verbatim
   pack below}. **Mechanical half-steps are
   scripted, not re-judged** (021): `workflow-status.py --check` covers the marker count
   ((j) stray-marker), the reverse id-existence half ((k) resolved-no-home), receipt presence
   ((l) no-receipts) and the doc-gate audit line ((m)); the judge runs the check and audits
   the semantic fidelity on top — never hand-greps those four.
   **Human-message verbatim pack (024 D21).** Before every decision-zone gate ask the
   dispatcher packs the phase's **complete human chat messages** into the lens 4 prompt —
   verbatim, in chronological order, with a count line reconcilable against the message count
   (all-or-nothing packing is what makes selective packing auditable). With the human's actual
   words visible, the fidelity audit checks each pending/approved row's G-row chosen against
   an **individually given** human answer — one answer transcribed as N approvals is the
   finding (R13's bundling risk: a bundled reply read as N item-approvals). **Explicit
   exemption (026 Req-3):** a compliant batch release is NOT that finding — when the ask was
   an enumerated batch table with a per-row recommendation and the reply is a general answer
   naming the group (三要素齐备, ask-routing-core.md), the one reply legally approves exactly
   the listed 照案 rows; anything outside the listed rows (拿不准 rows included) stays held
   to the individually-given standard.

**Receipts.** Every panel run leaves a receipt in the grill-log (or, for a **generic** grill
whose conversation is the log, in the round's closing message — decision-zone discussion-first
runs always persist). **A persisted receipt block opens with a structural anchor** — a line
starting `### Panel receipt` (any heading level ≥ ##) or `**Panel receipt**` — pinned (021)
so the presence check can find it: `--check` (l) flags a gated card whose grill-log holds
zero anchored blocks (`no-receipts`). Then the block body: a header line — the grill row (`G<n>`) or round it served + **round
type** + lenses dispatched + **re-dispatch yes/no with grounds** (the verified-facts pack /
dead-findings line that justifies the scope) — then **one line per finding with its
disposition**:
`adopted → G<n>/D<n>` (became a question or ledger row) · `refuted — <one-sentence why>` ·
`open → G<n>`.
**Pinned lexicon (machine-checked from the 022 shape cutoff on):** the header carries the four
key substrings `round =` · `round type` · `lenses =` · `re-dispatch =` (order and separators
free); each finding's disposition is a `- `-led list line whose lead word is followed **on the
same line** by its mark — `adopted … →` / `refuted … —` / `open … →` (a parenthetical qualifier
between word and mark is fine: `adopted（轻）→`); a clean run carries the literal `no findings`.
**From the 024 receipt-premise cutoff** the header additionally carries `premises =` — value
starts in the closed set `problem+claim` / `facts-pack` (then the block names an `[F<n>]`) /
`UNVERIFIED…` (the premise-closure trace, R4) — and `suspicions =` — a rewrite round's
round-header suspicion-list count, else `n/a-非 rewrite 轮` (R5; presence machine-checked,
timing/content stay with the round header).
`--check` (l) verifies each anchored block structurally; wording quality stays human/M6.
The refuted-with-why lines are the content a verdict-only receipt loses:
they are what stops a dead concern from being re-found every pass, and the only audit trail
M6 has of panel quality. A clean run stays one line ("no findings").
The gate digest's lead「Grill / 自检状态」section's
已验证 self-check lines cite these receipts;
a decision-level checkpoint with no receipt means the panel didn't run, and the gate ask is not
presentable (gate-digest.md). This is enforcement, not bookkeeping: a full requirement + design
cycle once ran with zero dispatches while this file prescribed them, and both gates passed on
self-certified work.
**Finding citation form:** cite a panel finding as `panel <phase-round> #<n>` — never a bare
`F<n>`, which collides with the facts-alias `[F<n>]` citation domain (two panels' own F-numbers
also collide across phases; the round qualifier is what disambiguates).
**Cite-side duty:** a later doc/phase citing a panel finding names a **locatable** receipt
(grill-log line / round-closing message); a panel reference that cannot be located is an
unverified claim (M1), not evidence — treat it as such before building on it.

## Approved-block rubric (026 Req-35 — the anti-误绿 target list)

A lens dispatched at a gate-adjacent or review checkpoint on a card with approved decision
blocks/rows expands this **fixed rubric mechanically over the active approved set** — every
block gets the four questions, so "who attacks 批了但落地了吗" is never unassigned (the 003
R22 误绿 shape: the attack target stayed implicit in the lens prompt and nobody owned it):

1. **落地了吗** — does the demanded artifact exist, at the named home, doing what the 陈述 says?
2. **可证伪吗** — does its acceptance have a failure mode a test/negative sample can trigger?
3. **与他行矛盾吗** — against the other approved blocks and the invariant ledger.
4. **测试覆盖了吗** — a coverage row/test cites it (the (q)/(ae) mechanical half feeds this).

**Incremental application**: rows touched since the last pass get the full four; the rest are
sampled. Card-specific targets land as blocks or grill rows — **never a checklist file** (a
seventh mirror). The review step's test-adequacy lens takes this rubric as its target list.

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
- **Panel receipts** — per dispatch: header (grill row/round · lenses) + one finding-level
  disposition line each (adopted / refuted-with-why / open); see
  「Receipts」above. Lens 4 additionally leaves its per-criterion verdict list.
- **Verified-facts pack** — the accumulated CONFIRMED findings and positive verifications of
  this grill (claim + `file:func` citation each), kept in the grill log. **Every subsequent
  dispatch attaches the pack and scopes the mandate to the delta + integration seams**; agents
  treat packed facts as given (spot-check only when a new finding contradicts one), never
  re-derive them from scratch. This is what keeps multi-round grills from re-verifying the
  same kernel chains three times. The pack also carries a **dead-findings section** — each
  refuted finding as one line (claim + why-dead, lifted from the receipts) — so later
  dispatches don't re-raise a concern already adjudicated dead; an agent may resurrect one
  only with new evidence against the recorded why.

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
  **Dispatch at the round that produces an expensive-to-redo artifact, not at the gate.** An
  enumeration/classification table, a per-site disposition list, a layering decision later
  phases build on — these are checked when produced; a finding that invalidates the artifact's
  *axis* or a batch of its rows costs one round then and a rebuild of everything stacked on it
  at freeze time. Applies even when the round felt like evidence work rather than a decision.
  **Tiered:** the full panel targets **decision-level** checkpoints (a new or changed
  ADR-class mechanism). A doc **rewrite that implements an already-grilled decision** gets a
  **lightweight consistency pass** instead: one agent (Agent tool `model: sonnet`, low
  effort — SKILL.md「Subagent model assignment」), mandate =
  hunt surviving old-semantics text and doc↔doc contradictions (no kernel re-verification);
  escalate a finding to code-verification only when it implicates code truth.
  **Rewrite rounds add the dispatcher's own suspicion list (024 R5):** before dispatching the
  pass, the dispatcher self-lists 「本轮改动可能自造的矛盾」(incl. cross-doc reference points)
  in the **grill-log round header** — backtick any decision id inside the list, a bare
  `resolved → <id>` form would misparse as a decision row — and folds the list into the pass
  mandate: what the dispatcher touched is information the agent cannot reconstruct (003
  Round 9: self-listing closed in one round what generic hunting took two). Feeding the
  list's terms to `check-superseded-phrases.py --terms` is a suggested move, not a duty.
  The receipt's `suspicions =` key carries the list's count (presence machine-checked;
  timing and content evidence stay with the round header, human-judged). Interlocks with
  grill.md「Whole-doc rewrite」's rewrite-list discipline.
- **discussion-first rounds (requirement/design)** — dispatch per the **round-type mapping**
  in `references/legacy/design-agenda.md`. Override relation: the mapping governs in-discussion
  cadence only — ADR-class new/changed-mechanism checkpoints and the pre-freeze pass keep the
  full attack-lens panel (decision-level duties never narrow). Same-class small topics may
  share one end-of-cluster dispatch: the receipt lands no later than the cluster's last
  round-end and names the rounds covered; ADR-class checkpoints never batch.
- **详设 baseline · execution authorization** — no attack-lens panel of their own (these phases
  run no grill); lens 4 only, before the gate ask, against that gate's criteria — 详设: the
  design decisions/contracts the detail claims covered (porting-type detail adds a
  comparison dispatch — references/legacy/steps/detail.md's porting exception); plan: the R-id/design↔task
  trace the plan claims complete.
- **review** — the three attack lenses are fixed members of the lens fan-out (see `review.md`).
- **implement part-check (017 R5)** — not a grill checkpoint: `implement.md`'s part completion
  check reuses the fresh-context dispatch *form* (attack a part's diff, 1–2 agents); its
  receipts land in the `notes/part-check-*.md` artifact with 修/log dispositions instead of
  grill-log lines, and nothing stops for a human.
