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
- **Sibling batch (opt-in):** 2–3 questions may go out in one round **only when mutually
  independent** — no `depends-on` between them, none gating another's framing; each still
  carries its own recommendation + trade-off and gets its own grill-log row. Offer it when a
  round surfaces several independent siblings; the human sets the pace and can drop back to
  single-question any time. Anything dependent stays sequenced — batching never reorders the
  tree walk.
- For **each** question give your **recommended answer + the trade-off**, then wait for the human.
- **Recommendation pre-check (self-proposals get the same rigor as external ones).** Before
  recommending an approach/idea of your own — inline in discussion, not only in dispatched
  panels — pass three checks; failing any, present it as an **open question with the check as
  pending work**, not as a recommendation:
  1. **Comparative claims VERIFIED** — never put an unread-code claim in a comparison table
     ("X has no cache / no hook" requires having read X).
  2. **Magnitude × medium** — multiply by the requirement's stated design scale and the actual
     access medium's per-op cost (a per-row catalog lookup at 10^6 rows over RPC is a different
     proposal than the same lookup in-memory).
  3. **Cost symmetry** — list what the proposal **adds** (writers, schema, state, RPC shapes),
     not only what it saves; a read that becomes a write is a qualitative change.
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
- Convergence lands **inline in the phase doc** (`requirement.md` / `design.md`) as you go — the
  doc is the durable output; the grill-log below is the *path* to it.

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
   your own framing. At each branch checkpoint run the three fresh-context lenses (causal-coverage
   · invariant-ledger replay · search-before-build) + the three standing rules
   (verify-the-assumption · re-apply-the-signature · class-to-constraint — a second same-shape
   finding pins a structural rule), so the agent reaches the decisive cuts itself instead of
   waiting for the human to land them. **Tiered dispatch:** M+ decision-level checkpoints →
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
  persist a file.
- **Large / branchy / multi-session** → append-only `notes/grill-<phase>.md` (phase = `requirement`
  / `design`) so it survives resume and records rollbacks.

**Codename legend.** When a grill coins session-local codenames (方案 T/S, N1/N2 …), a persisted
grill-log carries a one-line legend at the top (`T = 瘦身版 QD 驱动 · S = floor 方案现状`) and
keeps it current; in chat, re-expand each codename on first use per session ("方案 T（瘦身版 QD
驱动）"). A codename without a nearby definition is unreadable after resume.

Entry format — **append-only**: never edit/delete a past row; a correction is a *new* row.
**Ids run continuous across rounds** (`G<n>` keeps counting in round 3; round-scoped form
`G<round>.<n>` if wanted) — never mint a new letter per round (a past grill's G→H→I escalation
collided with other prefixes; see SKILL.md「Fixed ID prefixes」).

| id | question | recommended | chosen | why | depends-on | status |
|----|----------|-------------|--------|-----|------------|--------|
| G1 | …        | …           | …      | …   | —          | resolved |
| G2 | …        | …           | …      | …   | G1         | open / superseded |

**Lifecycle:** the grill-log is `notes/` **scratch — the *path*, not the durable output**. Once the
phase doc converges (requirement `confirmed` / design `frozen`), it may be pruned or archived (like
investigation notes); the phase doc + ADRs are what persist.

## Convergence — auto-verdict at the end of every round

"New questions exist" is **not** a continue signal: the question space is generative — a fresh
pass can always ask more — so question-exhaustion is an unreachable stop state. Convergence is
judged by **materiality**: would another round still change the decision this phase gates?

At the end of each round (a batch of resolved questions, or one adversarial pass), **Claude runs
this check and states a one-line verdict**. The verdict is a *recommendation* — the human still
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
   **continue**, naming those slots. (Structurally bounded: slots are finite.)
2. **Decision-level dry check** (repeat / adversarial passes): did **this** round change the doc
   at decision level — a 需求条目 added/changed, a 方案 choice flipped, a seam/contract edited, an
   ADR(-worthy) decision made? Zero such changes = a **dry** round (wording/format fixes don't
   count) → recommend **stop**. Verify against the doc's actual `git diff` **since the last grill
   checkpoint** — after stating each verdict, commit a checkpoint to dev_root
   (`<project>/NNN-slug: grill <phase> round N — <verdict>`), which is what gives the next
   round's dry check its baseline (phase-gate commits alone are too coarse: all rounds of one
   phase would share one baseline). XS/S: one adversarial pass suffices; M+: run passes until
   one comes up dry.
3. **ADR-weighted open points**: an open point that is hard-to-reverse × surprising × a real
   trade-off (the ADR test) justifies another targeted round — recommend **continue** naming
   exactly those points. An open point failing the ADR test gets the recommended default + an
   Open-question row instead of another round.

Verdict format (one line in chat, after the doc is updated):
`Grill 收敛判定: 继续 — 2 个 ADR 级 open 点 (G7 seam 契约, G9 兼容边界)` ·
`Grill 收敛判定: 建议收敛 — 本轮 0 决定级变更; 槽位全三态; Open 已记录 (G4, G11)`.
**Round-end order (write first, then ask):** verdict row appended to the grill-log — when one
is persisted; a small grill's conversation-is-the-log case has no file to append (Grill-log
proportionality above), its receipts are the phase doc + the commit → phase doc synced with the
round's answers → checkpoint commit → **then** the go ask, **with receipts** — the ask names
the doc paths (grill-log included when persisted) + the commit (SKILL.md Stop-at-gate「Ask with
receipts」).
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

When a round's verdict lands in the phase doc, **fold the correction into the live text**:
rewrite the affected sentences/sections so the body reads as if written today. Process history
goes to the grill-log and the doc's Change log — never the body. A superseded alternative
leaves the body (a one-line final verdict + git/grill-log pointer replaces its full text).
The body never stacks two generations of corrections — dated inline notes piling on each other
(「2026-XX-XX 更正…」on top of an earlier 更正) are the smell. The supersede discipline below
is for the **grill-log** (append-only history); the phase doc is the opposite: always
current-state.

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
- **Small, un-persisted grill** — the conversation *is* the log; just **re-ask the question in
  place** and re-walk anything downstream. No rows to mark (nothing was persisted).
- **Persisted log without `depends-on` tracked** — be **conservative**: mark `Gk` **and all later
  rows** `superseded` and re-walk from `Gk`. Over-invalidate rather than miss a hidden dependency
  (precise subtree invalidation needs the `depends-on` column).

The superseded rows are the audit trail of *why* the requirement/design went the way it did.
**Caveat (design phase):** rollback applies while `design.md` is still `drafting`; once **frozen**,
a change goes through change-management (M2), not a grill rollback.

## Resume mid-grill (M4)
If a grill is interrupted, `progress.md`「Now doing」names the open question (e.g. "grilling design,
at G7"); resume reads `notes/grill-<phase>.md` (if persisted) and continues from the `open` row — no
chat history needed. A small, un-persisted in-conversation grill just restarts the open question
from the phase doc's current state.

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
