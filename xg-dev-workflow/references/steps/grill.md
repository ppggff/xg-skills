# Step: grill (shared interactive elicitation — protocol + history + rollback)

A **shared mechanism** (like `adversarial-critic.md` / `evidence.md`), not a phase — it owns the
grill **protocol + grill-log + rollback + convergence** and is called by the **requirement** step
(elicit the real intent) and the **design-grill** step (stress-test the approach). The rollback
models the skill's append-only **supersede** discipline (`log.md` correction / ADR supersede). A
generic, non-doc grill can still be delegated via `use:grill-me` / `use:interview-me`.

Grilling is a **walk of a decision tree with dependencies** — each answer constrains the next. This
file owns the *protocol*, the *grill-log* (history), and *rollback*; each phase step adds its own
priorities and tactics (see "Phase-specific layers").

## Protocol (one question at a time)
- **One question at a time** (default). Walk the tree **resolving dependencies in order** —
  settle a prerequisite before the choices that hang off it; don't jump around.
- **Batching admission (one rule, two grounds):** (a) a **panorama** topic (per its
  topic-library attribute, `references/design-agenda.md`) or a fixed opening beat presents its full spread in one
  round — the round IS its decision cluster, item count follows the topic; (b) 2–3 mutually
  **independent sibling** questions — no `depends-on` between them, none gating another's
  framing. Under either ground each item still carries its own recommendation + trade-off and
  gets its own grill-log row; the human sets the pace and may drop back to single-question at
  any time; neither ground reorders the tree walk — anything dependent stays sequenced.
- **Round = one decision cluster resolved.** A round opens at a load-bearing branch point; its
  cluster is that unsettled decision plus the questions hanging off it (dependent follow-ups
  and their siblings — a batched round stays one round). It closes when the walk leaves
  the cluster (the next question hangs off a different branch point) or the cluster is exhausted
  (all resolved / explicitly Open); an adversarial pass is its own round. In a discussion-first
  run (below) a beat or agenda topic IS one round — the topic is the cluster, its sub-decisions
  cluster members even when mutually independent. Backstop for deep or fuzzy-edged branches:
  force-close after ~6-8 **human touchpoints** (answers and corrections both count) — a
  mid-topic force-close lands the flush + go ask with at most the mapping's lightweight
  mid-topic check; the full panel waits for topic end. This one boundary drives three mechanisms — the panel's branch checkpoints, the
  per-round doc sync (write cadence below), and the go-ask pace — and is the unit the
  ~3-round rule counts in.
- For **each** question give your **recommended answer + the trade-off**, then wait for the human.
- **A recommendation is not a decision — and transcription is never an ask.** Until the human
  answers, a recommendation lands in neither the phase doc nor the ledgers. A grill stops for
  exactly three ask shapes: the per-question answer ask, the round-end go ask, and the gate ask.
  "Written into the doc per my recommendation — please confirm" is forbidden on both counts:
  it decides before the answer, and it adds a per-item micro-gate for transcription correctness
  that the gate digest already covers (it approves ledger rows, not doc text).
- **Recommendation pre-check (self-proposals get the same rigor as external ones).** Before
  recommending an approach/idea of your own — inline in discussion, not only in dispatched
  panels — pass four checks; failing any, present it as an **open question with the check as
  pending work**, not as a recommendation:
  1. **载重前提 VERIFIED** — every premise the proposal rests on is checked **before** it is
     stated, not patched in afterwards. Two kinds: comparative claims about existing code
     ("X has no cache / no hook" requires having read X), and **feasibility premises**
     ("the existing flag can't express this", "the host has no psql") — those are settled by
     trying them, never by reasoning about them.
  2. **Magnitude × medium** — multiply by the requirement's stated design scale and the actual
     access medium's per-op cost (a per-row catalog lookup at 10^6 rows over RPC is a different
     proposal than the same lookup in-memory).
  3. **Cost symmetry** — list what the proposal **adds** (writers, schema, state, RPC shapes),
     not only what it saves; a read that becomes a write is a qualitative change.
  4. **价值归属 (who needs it)** — name **who needs it and what breaks without it**. A proposal
     whose strongest argument is that it makes the design more self-consistent fails this check.
     Corollary for option sets: when the options differ in **scale**, never lay them out as a
     minimal / medium / complete ladder — a ladder implies more-is-better and silently converts
     「要不要」into「要多少」. Options addressing **different kinds** of problem are listed by kind,
     each carrying its own value argument; only then is picking one a real choice.
- **Interleave code understanding** (M5/M1): when a question is answerable from the codebase, go
  read it instead of asking/guessing; bring back evidence (`func()` in `file.c` / `[[wiki/…]]`).
  When it's answerable **only empirically** (runtime/planner behavior reading can't settle), run
  a **spike** — a throwaway probe (`investigate.md`「Spike」) — instead of parking it as 待验.
- Run the **fresh-context adversarial panel** (`adversarial-critic.md`) at branch checkpoints —
  the lenses, standing rules, and tiered dispatch are in「Shared elicitation tactics」below.
- **Mid-grill new mechanism → pin principles, defer axes.** When an answer *injects a new
  mechanism* into the doc (a new syntax surface, a new subsystem), the current phase pins only
  its **principles and boundaries** (what it guarantees, what it refuses, its consumers); the
  correctness envelope's **axis enumeration** (per-field/per-condition precision) belongs to the
  NEXT phase's grill.
- **Don't grill to death** — if one point won't converge in ~3 rounds, record it as an Open
  question and move on; an honest "still ambiguous" beats grinding.
- **Write cadence — the phase doc's write unit is the round, not the question.** Three levels:
  **per-question** → ledgers only (逐条入账 / 载重事实入账 below); **per-round** → phase doc
  fold-in + checkpoint commit (the Round-end order in「Convergence」is the SoT); **per-gate** →
  human confirmation (the gate digest approves ledger rows, never doc text). The phase doc
  (`requirement.md` / `design.md`) is the durable output; the grill-log below is the *path* to it.
- **逐条入账 (ledger as you converge).** When a `G<n>` resolves into a **human-judgment
  decision** (requirement 条目 / design D/ADR decision / 详设 `S<n>` item), append it to the
  card's `decisions.md` as a **proposed** block right then (`templates/decisions.md`; the file
  is created lazily on the first block, like `adr/`) — the gate digest is generated from these
  pending rows. Claude never writes `approved` (gate-digest.md「Approve transcription」). The
  round's checkpoint commit is what the eventual approve annotation will cite as receipts.
  **Doc-gate cards (017 D2)**: no ledger — the resolved decision is written into the phase
  doc's matching section right then (the doc's `drafting` status is what marks it pending);
  the gate confirms the doc, and the audit anchor is its Change log gate line.
- **Self-contained 陈述.** A ledger 陈述 whose decision object is a list/count follows
  gate-digest.md's self-containment rule at write time (same thresholds, same evidence-ref
  exemption) — a digest card *leads with* the row's 陈述 (why/alt compress to the card
  shape), so a 陈述 that isn't self-contained cannot be repaired at presentation time.
- **载重事实入账 (facts as you verify).** When a grill/investigate round **verifies a
  load-bearing fact** a decision rests on, append it to the card's `facts.md` as an `F<n>`
  block right then (`templates/facts.md`; created lazily like `decisions.md`) and cite it as
  `[F<n>]` from the phase doc. Boundary with the adversarial-critic **verified-facts pack**:
  the pack is session-state (avoids re-verifying within a grill); `facts.md` is the card's
  persistent layer — only facts that later phases/rewrites will lean on get an F block.
  User-stated environment facts (versions, scale, deployment shape) are not F-block material
  until verified — they land in the phase doc's Context with provenance marked (M1).
  **Doc-gate cards**: no `facts.md` — verified load-bearing facts go to the doc-local
  「事实清单」section instead (the standalone-doc container form, doc-conventions
  「Provenance containers」).
- **Skeleton docs (phase-start creation).** The phase doc is created at phase start as a
  skeleton — frontmatter `drafting` + the template's section headers, **no prose in a section
  before its consensus** (prose in an unconsensused section is a violation). "Discuss first"
  is carried by this emptiness constraint + the transcription invariant (below), never by the
  file's absence; per-round fold-in touches only consensus-reached sections (a section's
  *skeleton period* ends at its first consensus fold-in).

## Discussion-first flow (requirement / design phases)

Decision-zone phases run **discussion-first**: consensus forms in discussion rounds; the phase
doc only *transcribes* it. Generic grills keep the plain protocol; XS/S cards scale per
`references/design-agenda.md`'s **XS/S items table**.

- **Fixed opening beats** (each = one round). Design: an **understanding statement** (evidence
  → mechanism → implication + uncertainties + **information gaps**), judged by the human; then
  a **candidate spread** (≥2 side by side — the 方案优先 table, mandatory, pre-draft).
  Requirement: **problem understanding** + **boundary spread** (step 1; XS may merge the two).
- **Agenda negotiation** — its own mini-round right after the candidate spread, own round-end
  go ask (XS/S skip it, default order applies): Claude proposes topics + order + rationale from
  the **topic library**, ordered by the **driving axis** (initial call at understanding close,
  rechecked here). The human reorders/adds freely; **contract-fixed** entries (拆分审视,
  freeze-checklist review, part-topic A↔B/seam duties) cannot be dropped. Live agenda = the
  ordered open `G<n>` rows (the design 速览 renders it; reordering appends an annotation row).
- **Convergence loop, per beat/topic**: statement → human judgment → gap-filling (「Interleave
  code understanding」/ spike; facts per 载重事实入账) → **incremental restatement** (only what
  changed) → human confirmation; close per Round-end order, verdict per「Convergence」.
  Information gaps are listed up front; each ends **resolved or `deferred`**.
- **Granularity guardrail — discussion material ≠ draft**: understanding ≤ ~one screen, no
  section structure, diagrams, or contract text; a candidate = one-line 思路 + 3–5 responsibility blocks + most-different
  point (**no diagrams/contracts/interfaces**); a topic item ≤3 lines. Over-limit is a violation
  a fresh-context pass may flag.
- **Transcription invariant.** Sections fill **only from consensus**. A gap found while
  writing: decision-level → open a regular round (a mini-round IS a round); below that → write
  it marked **（落纸补充）** (transcription addition — a discussion-flow marker owned by this
  section, NOT a provenance class). The gate ask's 假设 closure sweep enumerates markers one by
  one (never folded into the digest's emphasis cap); approve transcription clears them — git
  keeps the record. Decision-level items carrying the marker = 0 at any gate.

## Shared elicitation tactics (lenses)

Both grill users — **requirement** (elicit the real intent) and **design-grill** (stress-test the
approach) — apply these four tactics. They are canonical **here**; each phase step adds only its
own slant (see "Phase-specific layers"). Change a tactic once, in this file.

1. **Sharpen fuzzy language → canonical term + `_Avoid_`.** When a term is vague/overloaded — or
   a force-translated EN technical term (a pin trigger even when it isn't vague, per the global
   Language rule: `heap` not 堆, `segment` not 段) — pin **one** canonical name, defined by what
   it **IS, not what it does** (1–2 tight sentences), plus the synonyms to avoid (grill-with-docs'
   opinionated glossary); fix the doc's wording to it. State each pin as you make it (one line:
   `术语: heap (_Avoid_ 堆)`) so the human sees the decision and can veto on the spot. **Infer the
   term's bounded context** (project `CONTEXT-MAP.md`); if it could belong to more than one,
   **ask**. Same word in two contexts = a legitimate scoped homonym (note it); same word twice
   **within** a context, or colliding with a canonical/`_Avoid_` there → flag and reconcile
   immediately. Durable domain terms get their canonical home in the **KB concept / CONTEXT-MAP**;
   the phase doc just uses them consistently, never stores the glossary itself.
2. **Stress-test with concrete scenarios.** Invent specific edge-case scenarios that force the
   human to be precise about a boundary ("两个 coordinator 同时崩溃时…?"), rather than accepting an
   abstract answer.
3. **Cross-reference code (grep before accepting).** When the human asserts how the code works
   today, verify (≥1 grep + 1 read for the named term) before taking it as fact; hallucinated
   agreement is worse than an honest "didn't check". When the code disagrees, raise it on the spot
   — don't silently take either side. (This is the assertion-checking companion to the Protocol's
  「Interleave code understanding」, which covers proactively reading when a question is answerable
   from code.)
4. **Fresh-context adversarial panel (`adversarial-critic.md`).** Don't grill only from inside
   your own framing. At each branch checkpoint run the three fresh-context attack lenses
   (causal-coverage · invariant-ledger replay · search-before-build) + the three standing rules
   (verify-the-assumption · re-apply-the-signature · class-to-constraint — a second same-shape
   finding pins a structural rule), so the agent reaches the decisive cuts itself instead of
   waiting for the human to land them. Before the gate ask, add the **criterion-conformance
   judge** (lens 4 there) against this gate's criteria. **Each run leaves a receipt**
   (adversarial-critic.md「Receipts」) — the gate digest requires them; a grill with zero
   dispatches cannot present a gate ask. **Tiered dispatch:** M+ decision-level checkpoints →
   parallel one-agent-per-lens; XS/S work / edit-only rounds → the single-agent form; attach the
   **verified-facts pack** on every round after the first; a round that only *rewrote
   already-grilled text* gets just a lightweight text-consistency agent + a targeted re-verify of
   the new clauses, not another full pass. The lenses also apply to **every newly proposed
   remediation/mechanism mid-grill** (run search-before-build on the fix itself before designing
   it), not just the artifact under test.

**Don't grill to death** (the ~3-round rule) is the Protocol's, above — the SoT; phase steps
reference it rather than restating the round count.

## Grill-log (history) — proportional
The record of the decision-tree walk: what was asked, recommended, chosen, and why. **Size it to
the grill**, don't tax simple cases:
- **Small** (a handful of questions, single session) → the conversation **is** the log; don't
  persist a file. **Generic grills only** — a discussion-first run persists the grill-log **from
  round 1**, the skeleton period's doc-side consensus carrier (017 R1: logging/receipts never
  scale away with sizing).
- **Large / branchy / multi-session** → append-only `notes/grill-<phase>.md` (phase = `requirement`
  / `design`) so it survives resume and records rollbacks.

**Codename legend.** When a grill coins session-local codenames (方案 T/S, N1/N2 …), a persisted
grill-log carries a one-line legend at the top (`T = 瘦身版 QD 驱动 · S = floor 方案现状`) and
keeps it current; in chat, re-expand each codename on first use per session ("方案 T（瘦身版 QD
驱动）"). A codename without a nearby definition is unreadable after resume.

Entry format — **append-only**: never edit/delete a past row; a correction is a *new* row.
Status values: `resolved` / `open` / `superseded` / `deferred` (an information gap left
consciously unclosed). An alignment-correction row maps: question = the understanding point,
recommended = the original statement, chosen = the human's correction.
**Ids run continuous across rounds** (`G<n>` keeps counting in round 3; round-scoped form
`G<round>.<n>` if wanted) — never mint a new letter per round (a past grill's G→H→I escalation
collided with other prefixes; see SKILL.md「Fixed ID prefixes」). A resolved row whose status
carries `→ <decision id>` (`→ <doc §>` on doc-gate cards) is a **decision row** — the
reverse-fidelity enumeration key; plain alignment rows don't count. A bare human `go` lands in
`chosen` as 「照案」+ the recommended option's reference, never a bare ack.

| id | question | recommended | chosen | why | depends-on | status |
|----|----------|-------------|--------|-----|------------|--------|
| G1 | …        | …           | …      | …   | —          | resolved |
| G2 | …        | …           | …      | …   | G1         | open / superseded |

**Lifecycle:** the grill-log is `notes/` **scratch — the *path*, not the durable output**. Once the
phase doc converges (requirement `confirmed` / design `frozen`), it may be pruned or archived (like
investigation notes); the phase doc + ADRs are what persist. Traceability anchors are **ledger
rows + receipts commits — never grill-log lines**; a disagreement's durable anchor is the
checkpoint-commit history (git), so pruning breaks nothing.

## Convergence — auto-verdict at the end of every round

"New questions exist" is **not** a continue signal: the question space is generative — a fresh
pass can always ask more — so question-exhaustion is an unreachable stop state. Convergence is
judged by **materiality**: would another round still change the decision this phase gates?

At the end of each round (one decision cluster resolved — Protocol「Round」— or one adversarial
pass), **Claude runs this check and states a one-line verdict**. The verdict is a *recommendation* — the human still
decides at the gate; it replaces neither the gate nor the human's "keep going".

**MANDATORY — surface it, don't just file it.** The verdict must appear in the **user-facing
message that closes the round** (not only in the grill log / phase doc). "继续/建议收敛" is the
one thing the human needs to decide what happens next, so it is a *conclusion*, not a process
note — omitting it and waiting for the human to ask "还要继续吗?" is a defect. Never end a grill
round reporting only *what was found/fixed*; always end with the 继续/建议收敛 recommendation.
This applies to **both** grill users — `requirement` (elicitation) and `design-grill` — since
both run this shared step.

1. **Slot state** (elicitation grill): every template slot / 需求条目 sits in one of three states
   — **evidence-backed · human-confirmed · explicitly Open**. Any slot in none → recommend
   **continue**, naming those slots. (Structurally bounded: slots are finite. Skeleton period:
   the slots are the beat objects — understanding confirmed / candidates chosen / agenda set;
   template slots apply from the first fold-in.)
2. **Decision-level dry check** (repeat / adversarial passes): did **this** round change the doc
   at decision level — a 需求条目 added/changed, a 方案 choice flipped, a seam/contract edited, an
   ADR(-worthy) decision made? Zero such changes = a **dry** round (wording/format fixes don't
   count) → recommend **stop**. Verify against the **card's** git diff (phase docs +
   `decisions.md` + grill-log — one checkpoint commit covers them) **since the last grill
   checkpoint**; process rows never count as decision-level (verdict lines, panel receipts,
   agenda-order annotations, prunes) — after stating each verdict, commit a checkpoint to dev_root
   (`<project>/NNN-slug: grill <phase> round N — <verdict>`), which is what gives the next
   round's dry check its baseline (phase-gate commits alone are too coarse: all rounds of one
   phase would share one baseline). A mid-grill checkpoint may create `progress.md` early
   (ahead of the implement phase) so a fresh session can resume the grill; an *interrupted*
   round is landed by the `park` verb (`park.md`), which pulls this round-end order forward
   to the interruption point. XS/S: one adversarial pass suffices; M+: run passes until
   one comes up dry.
3. **ADR-weighted open points**: an open point that is hard-to-reverse × surprising × a real
   trade-off (the ADR test) justifies another targeted round — recommend **continue** naming
   exactly those points. An open point failing the ADR test gets the recommended default + an
   Open-question row instead of another round.

Verdict format (one line in chat, after the doc is updated):
`Grill 收敛判定: 继续 — 2 个 ADR 级 open 点 (G7 seam 契约, G9 兼容边界)` ·
`Grill 收敛判定: 建议收敛 — 本轮 0 决定级变更; 槽位全三态; Open 已记录 (G4, G11)`.
**Round-end order (write first, then ask):** verdict row **and any panel receipts**
(adversarial-critic.md「Receipts」) appended to the grill-log — when one
is persisted; only a **generic** grill's conversation-is-the-log case has no file to append
(decision-zone runs always persist), its panel receipts land in the round's closing message
and its ask receipts are the phase doc + the commit → phase doc synced with the
round's answers → checkpoint commit → **then** the go ask, **with receipts** — the ask names
the doc paths (grill-log included when persisted) + the commit (SKILL.md Stop-at-gate「Ask with
receipts」— those doc/commit receipts are distinct from panel receipts).
The ask uses the advance word **go** (「继续下一轮请回 go」/「收敛,回 go 进入下一阶段」). A round
whose artifacts aren't on disk isn't finished — chat-only rounds are how a past grill lost its log.

**The verdict reports this round's facts only — never forecast the next round.** "预期下轮
dry / severity 在衰减" is not information the dry check produces, and it anchors the human's
continue/stop call on optimism. Say what this round changed; let the mechanical
criteria carry the recommendation.

**Re-open bar for a later grill:** a subsequent pass's finding re-opens settled ground **only if
decision-changing** (it would alter a 条目 / choice / contract → rollback below, or M2 once
frozen); anything else lands in Open questions / `roadmap.md` without re-opening.

**Calibration (offline, M6):** post-freeze M2 changes tracing back to points a grill defaulted →
stopping too early; rounds repeatedly ending dry → stopping too late. The retro tunes the bar
from this signal (usage log + `log.md`).

## Fold-in (压实) — the phase doc stays current-state

**Key fidelity on fold-in.** When folding a round's results back into the doc, an
**enumeration criterion's declared key must not change**. Results gathered under a different
key (e.g. probing by DDL statement when the criterion enumerates by write point) land as
**partial evidence**: record what they do cover and **name the key rows still unverified** —
they never close the criterion or relabel its coverage ("收敛到只有 X"). A criterion closes
only through its declared table, every row filled. (The archetype: a writer-axis criterion
closed by a 5-DDL probe in the requirement grill itself — the confirmed doc then carried both
the instruction and the false "done", and design faithfully inherited it.)

When a round's verdict lands in the phase doc, **fold the correction into the live text**:
rewrite the affected sentences/sections so the body reads as if written today. Process history
goes to the grill-log (plus, for requirement.md, its Change log; design.md keeps no Change log —
its process history lives in grill-log + git) — never the body. A superseded alternative
leaves the body (a one-line final verdict + git/grill-log pointer replaces its full text).
The body never stacks two generations of corrections — dated inline notes piling on each other
(「2026-XX-XX 更正…」on top of an earlier 更正) are the smell. The supersede discipline below
is for the **grill-log** (append-only history); the phase doc is the opposite: always
current-state.

**Whole-doc rewrite at convergence.** Per-round fold-in keeps sentences current but not the
doc's *shape*: after several rounds the section structure drifts (patch-ordered content,
duplicated emphasis, sections that no longer carve the design at its joints). When the verdict
is 建议收敛 — before the gate ask — judge the doc's structure as if writing it fresh today; if
patched shape shows, do one content-preserving whole-doc rewrite (first collect every scattered
"改写时澄清" self-note into a checklist and tick each — same discipline as `change.md`'s
Rewrite checklist), then re-verify the rewritten text against the round's decisions.

## Rollback (回退 — return to a previous question)
"回退" / "go back" re-opens an earlier decision. Reuse the append-only **supersede** discipline —
don't delete history:
1. **Pick the target** `Gk` (default: the last resolved question).
2. **Invalidate the dependent subtree** — mark `Gk` and every later entry that (transitively)
   `depends-on` it as `superseded` (a status change on those rows, **not** a deletion); independent
   siblings stay `resolved`.
3. **Re-open `Gk`** and re-walk forward; the new answers are **new** `G` rows (they may differ from
   the superseded ones).
4. **Reconcile the phase doc** — edit `requirement.md` / `design.md` to drop content that came from
   the superseded answers and reflect the new ones (the doc holds current state; the log holds the
   path, dead branches included).

**Fallbacks (the common cases):**
- **Small, un-persisted grill** (generic only — discussion-first runs always persist) — the
  conversation *is* the log; **re-ask in place** and re-walk downstream. No rows to mark.
- **Persisted log without `depends-on` tracked** — be **conservative**: mark `Gk` **and all later
  rows** `superseded` and re-walk from `Gk`. Over-invalidate rather than miss a hidden dependency
  (precise subtree invalidation needs the `depends-on` column).

The superseded rows are the audit trail of *why* the requirement/design went the way it did.
**Caveat (design phase):** rollback applies while `design.md` is still `drafting`; once **frozen**,
a change goes through change-management (M2), not a grill rollback.

## Resume mid-grill (M4)
If a grill is interrupted, `progress.md`「Now doing」names the open question (e.g. "grilling design,
at G7"); resume reads `notes/grill-<phase>.md` (if persisted) and continues from the `open` row — no
chat history needed. A small, un-persisted in-conversation grill (generic only) restarts from
the phase doc's current state; a discussion-first run resumes from the persisted grill-log —
skeleton-period doc sections are legitimately empty. A mid-grill **leave** is landed by the `park` verb (`park.md`):
the conversation-is-the-log exemption expires at leave time — park persists the grill-log and
names the open row before the session ends.

## Phase-specific layers (defined in the phase steps, not here)
Both phases apply the four **Shared elicitation tactics** above; each phase step carries only its
slant on them plus its own unique items:
- **requirement** (`requirement.md`) — semantics-first priorities (why-now / 语义 / boundaries) +
  the **disposable design sketch** (shape questions get a throwaway 非约束 sketch, not a parked
  待验). Shared-tactic slant: term = requirement semantics · scenarios = 需求 boundaries ·
  adversarial = 需求条目 completeness.
- **design** (`design-grill.md`) — module altitude, 方案优先 + the hack/补丁/重做 spectrum,
  design-quality + module-depth lenses, required diagrams. Shared-tactic slant: term → KB
  concept/CONTEXT-MAP · scenarios = module boundaries · adversarial = design decisions +
  invariant-ledger replay.

## Runtime override
`use:grill-me` (relentless branch-resolving) · `use:interview-me` (intent elicitation) ·
`use:<your-skill>` — these replace the *protocol*; the grill-log + rollback discipline still apply.
