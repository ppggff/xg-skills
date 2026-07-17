# Step: 需求 (requirement — elicit + grill)

Forked from **interview-me / grill-me** (one-question-at-a-time elicitation of the *real*
intent) + **grill-with-docs** (update the artifact inline as understanding crystallises) +
**spec-driven-development** (testable success criteria). Adjusted: the artifact is this
requirement's `requirement.md`; understanding the codebase (M5) is **interleaved** with the
questioning; the no-望文生义 evidence rule (M1) is enforced; ends with the **confirm gate**.

Output: `requirement.md` (template: `references/templates/requirement.md`).

## Principle

The requirement is **elicited interactively, not written in one shot.** A vague ask is the
input; the job is to converge — by questioning + reading code — on sharp boundaries and
testable criteria. Do **not** fill ambiguity silently: surface it, ask, and let the human
correct. You are extracting what the human actually wants, not what the ask literally says —
understand the **essence** behind it. The stated requirement may be **layered**, may **diverge
from its wording**, and **maps to the design non-1:1**; the goal is to solve the real problem,
not transcribe the words.

## Procedure (interleaved loop)

1. **Restate + surface assumptions.** Echo the raw ask in your words, then list the
   assumptions you'd otherwise bake in (性质/动机/语义/范围/约束). Ask the human to
   correct them **before** drafting. This is step 1, not an afterthought.
   Two checks before drafting anything (from `triage`): **(a) redundancy** — search the
   codebase for an existing implementation of the asked-for behavior **by domain concept,
   not the ask's wording**, and report where you looked (already implemented → no card;
   point at it instead); **(b) prior rejection** — scan the project `roadmap.md`
   「Rejected / won't do」ledger (and ADRs in the area) so a previously-rejected proposal
   doesn't return unnoticed; if the ask resembles an entry, surface it before continuing.
2. **Grill one question at a time** — the shared protocol + **grill-log** + **rollback** + **convergence auto-verdict** live in
   `grill.md`; here, walk the decision tree toward the sections
   (Context/**需求条目**/Scope/Constraints/Effect/Future/Open questions).
   Priorities to nail early:
   - **Why now / motivation** — cost? a correctness bug? operability? (changes everything downstream)
   - **Semantics** — pin exact meaning of the ask's key words ("只在某个" = at-most-one? designated? auto-elected?).
   - **Boundaries** — what's in vs out; the no's are as load-bearing as the yes's.

   Grilling tactics (from grill-with-docs):
   - **Sharpen fuzzy language → canonical term + `_Avoid_`** — when the human uses a vague/
     overloaded term, pin **one** canonical name (define what it **IS, not what it does**, 1–2
     sentences) + note synonyms to avoid (grill-with-docs' opinionated glossary); fix the
     requirement's wording to it. **Canonical form follows the global Language rule**: an
     established EN technical term stays EN (`heap` not 堆, `segment` not 段) — a force-translated
     term is a pin trigger even when it isn't vague. State the pins as you make them (one line:
     `术语: heap (_Avoid_ 堆)`), so the human sees when a term gets decided and can veto on the spot. **Infer its bounded context** (project `CONTEXT-MAP.md`); if
     ambiguous, **ask**. If it **collides within that context** with an existing KB/CONTEXT-MAP
     term, flag immediately ("KB 用 'X' 指 A,你这里像是 B —— 哪个?"); same word in a
     *different* context is a legitimate scoped homonym. Durable domain terms get their
     canonical home in the KB concept / CONTEXT-MAP; the requirement just uses them consistently.
   - **Stress-test with concrete scenarios** — invent specific edge-case scenarios that force
     the human to be precise about a boundary ("两个 coordinator 同时崩溃时…?"), rather than
     accepting an abstract answer.
   - **Grep before accepting a current-behavior claim** — when the human asserts how the code
     works today, verify (≥1 grep + 1 read for the named term) before taking it as fact;
     hallucinated agreement is worse than an honest "didn't check". When the code disagrees,
     raise it on the spot, don't silently take either side.
   - **Disposable design sketch (前瞻草图)** — when a question can't settle without seeing a
     solution shape (feasibility, cost magnitude, scope size — is this R item cheap, or does it
     force a new mechanism?), draft a **throwaway sketch**: a solution outline at module
     altitude, explicitly marked 非约束 — in chat for small ones, `notes/sketch-design.md` when
     it needs to survive the session. It is the solution-shape sibling of the spike (spike =
     empirical questions; sketch = shape questions): its only job is to feed back into the
     requirement — surface R-item gaps/ambiguities and price tags **before** the confirm gate,
     instead of discovering them in the design phase as M2 churn. Rules: the sketch is **never
     presented at the confirm gate** and never becomes `design.md` by rename (the design phase
     authors `design.md` fresh, taking the sketch as input evidence); an R item whose content
     leans on the sketch is marked 推断/假设 until the design phase verifies it; the requirement
     must stand if the sketch is thrown away — it states the problem, the sketch only tests it.
   - **Fresh-context adversarial pass (`adversarial-critic.md`)** — don't grill the ask only
     from inside your own framing of it. At each branch checkpoint apply the *causal-coverage*
     lens (against the real intent/effect — is each requested thing tied to the actual goal;
     anything unnecessary or any gap?) + the standing rules (incl. **class-to-constraint** — a second same-shape finding pins a structural rule): **verify-the-assumption** (every
     load-bearing "X is available/true at Y" gets a grep+read before the requirement leans on it
     — this is what surfaces facts like "per-file info isn't returned to QD") and
     **re-apply-the-signature** (let the problem's specific structure shrink scope). Run the
     *invariant-ledger replay* + *search-before-build* lenses once the touched subsystem is known.
     **Tiered dispatch on repeat passes** (same as design-grill's): a full fresh-context pass at
     decision-level checkpoints; after a round that only *edited already-grilled text*, a
     **targeted re-verify of the new clauses + a lightweight whole-doc consistency sweep** —
     not another full pass. *Why (2026-07-11 retro):* card 002's rounds 5–8 each re-swept the
     whole requirement while every decision-level finding sat in the previous round's new text.
3. **Interleave code understanding (M5 + M1).** When a question is answerable from the
   codebase ("does X exist?", "how is Y gated?", "is Z enumerable?"), **go find out instead
   of asking or guessing**: query xg-knowledge-lite first, then a read-only Plan Mode /
   Explore subagent. Bring the evidence back (`func()` in `file.c` / `[[wiki/<project>/<slug>]]`).
   Capture genuinely reusable findings to the KB, not buried in `requirement.md`.
4. **Update the doc inline.** As each answer/finding lands, write it into the matching
   `requirement.md` section (grill-with-docs style). Keep `status: drafting`. The doc is the
   running record of convergence, not a final report dumped at the end.
5. **Itemize into 需求条目 (the traceability spine).** As intent converges, distil it into
   **atomic, individually-tracked requirement items** with **stable IDs** (`R1`, `R2`, …) — one
   statement each (a "X and Y" item is two). This is the canonical list; Scope/Effect and every
   downstream doc reference the IDs, so a later change localises to one `R`. Mark each item's
   **provenance** (evidence-cited / 推断 / 假设) per M1. Don't renumber; retire an item with a note.
6. **Reframe Effect as testable criteria.** Turn each requirement item into checkable conditions
   ("at most one coordinator runs the launcher; observable via …"), not vague goals; **cite the
   `R-id`** each criterion verifies.
7. **Boundaries & open questions explicit.** Anything still unresolved or needing human
   input → Open questions; anything deliberately deferred → Future. **Don't grill to death**:
   if one point won't converge after ~3 rounds, record it in Open questions and move on —
   an honest "still ambiguous" beats grinding the same branch forever.
8. **GATE — hard stop.** Present `requirement.md` for confirmation **via the gate digest**
   (`gate-digest.md`: load-bearing decisions + least-confident spots + open questions + the go
   ask with receipts), then **STOP this turn**.
   **XS gate merge** (SKILL.md「Requirement sizing」Gate merging): when the human opted into the
   combined 需求+设计 gate, continue into the design draft in this same invocation and present
   both docs at one combined gate — requirement-level decision cards first; if the work outgrows
   XS mid-run, stop at this confirm gate as usual.
   Do **not** create/scaffold/edit `design.md` (or any later-phase doc) until the human
   explicitly confirms in a later turn. Keep `status: drafting`; set `status: confirmed`
   only after the human signs off.

## Runtime override
`requirement use:interview-me` (pure intent-elicitation) · `requirement use:grill-me`
(relentless branch-resolving) · `use:<your-skill>`.

## Done when
- Redundancy + prior-rejection checks run (where-looked / ledger scan reported); assumptions
  confirmed; the sections filled; **需求条目 itemized with stable `R-id`s**; boundaries
  sharp; success criteria specific, testable, and each citing its `R-id`; load-bearing claims
  evidence-backed (provenance marked); `status: confirmed`. Then run the omission check (M3).
