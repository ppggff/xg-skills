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
   correct them **before** drafting.
   Two checks before drafting anything (from `triage`): **(a) redundancy** — search the
   codebase for an existing implementation of the asked-for behavior **by domain concept,
   not the ask's wording**, and report where you looked (already implemented → no card;
   point at it instead); **(b) prior rejection** — scan the project `roadmap.md`
   「Rejected / won't do」ledger (and ADRs in the area) so a previously-rejected proposal
   doesn't return unnoticed; if the ask resembles an entry, surface it before continuing.
   **Write side:** when an ask is rejected at requirement level (triage or the confirm gate),
   append it to that ledger (`roadmap.md`「Rejected / won't do」, one line: what + why + date)
   — the anti-resurrection scan only works if rejections actually land there.
   **Ask born from an approved analysis note** (an audit/proposal the human already reviewed —
   the requirement-side sibling of design-grill's "card graduated with pre-design"): consume the
   note — seed the sections from it and grill only what it left open; when the note's scope got
   an explicit go this session, assumption-surfacing may fold into the confirm-gate digest
   instead of a standalone grill round.
2. **Grill one question at a time** — the shared protocol + **grill-log** + **rollback** + **convergence auto-verdict** live in
   `grill.md`; here, walk the decision tree toward the sections
   (Context/**需求条目**/Scope/Constraints/Effect/Future/Open questions).
   Priorities to nail early:
   - **Why now / motivation** — cost? a correctness bug? operability? (changes everything downstream)
   - **Semantics** — pin exact meaning of the ask's key words ("只在某个" = at-most-one? designated? auto-elected?).
   - **Boundaries** — what's in vs out; the no's are as load-bearing as the yes's.

   Grilling tactics — the four shared tactics (sharpen-language, stress-test scenarios,
   grep-before-accepting, fresh-context adversarial panel + tiered dispatch) live in
   `grill.md`「Shared elicitation tactics」. Apply them with the **requirement slant**:
   - **Sharpen language** — the pinned term captures **requirement semantics**: the exact meaning
     of the ask's key words (the 语义 priority above).
   - **Stress-test scenarios** target **requirement boundaries** — force precision on what's in
     vs out (the no's are as load-bearing as the yes's).
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
   - **Fresh-context adversarial panel** — targets **需求条目 completeness**: the *causal-coverage*
     lens leads (is each requested thing tied to the real goal; anything unnecessary or any gap?),
     with *verify-the-assumption* surfacing requirement facts (a load-bearing "X is available at Y"
     gets grep+read before the requirement leans on it — e.g. "per-file info isn't returned to QD").
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
   **Each R item also enters the ledger** as a proposed `decisions.md` block (grill.md
   「逐条入账」) — the confirm gate approves those rows, not the doc text.
6. **Reframe Effect as testable criteria.** Turn each requirement item into checkable conditions
   ("at most one coordinator runs the launcher; observable via …"), not vague goals; **cite the
   `R-id`** each criterion verifies. An **enumeration criterion** ("every X passes …") declares
   its **枚举键 + 必填列** in the criterion text and closes only via the full table — see the
   template's Effect note; no partial-completion phrasing ("已完成 N 条").
7. **Boundaries & open questions explicit.** Anything still unresolved or needing human
   input → Open questions; anything deliberately deferred → Future. **Don't grill to death**
   (`grill.md` Protocol): a point that won't converge → record it in Open questions and move on.
8. **GATE — hard stop.** Run the **criterion-conformance judge** (adversarial-critic.md lens 4,
   against this requirement's own claimed-closed criteria) and confirm panel receipts are in
   place (gate-digest.md precondition), then present `requirement.md` for confirmation **via the
   gate digest** (`gate-digest.md`: cards from the pending ledger rows + least-confident spots +
   open questions + the go ask with receipts), then **STOP this turn**. On confirm: approve
   transcription (gate-digest.md) — `confirmed` means the requirement-level rows are all
   approved (the derived-status rule, SKILL.md「Ledger」), then set `status: confirmed`.
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
  sharp; success criteria specific, testable, each citing its `R-id`, and enumeration criteria
  declaring their 枚举键 + 必填列 (#6); load-bearing claims
  evidence-backed (provenance marked); `status: confirmed`. Then run the omission check (M3).
