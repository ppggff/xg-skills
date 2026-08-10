# Step: change management (M2)

Authored inline (no third-party source). Governs how a confirmed requirement and a frozen
design are allowed to change, so the design stays stable while the plan flexes.

## Three kinds of change — route correctly

### A. Requirement/design change (scope/constraints/effect shifted)

0. **Gate at entry.** A requirement/design change is a decision-zone act: it comes from the
   human, or — when Claude escalates a fork from **any post-freeze point** (详设 / 实现 /
   测试 — the detail phase and the execution zone alike; the detail/implement steps' split
   probes route their 升 B verdicts here) — Claude **presents
   the fork + options and waits for the human's call** before touching `requirement.md` or
   unfreezing any decision (both entry points below are gated the same way). The escalation
   itself persists as a **proposed `decisions.md` row** (fork + options folded into why/alt —
   the row IS the presented fork, resumable if the session breaks); appending that row is
   **not** "touching" the docs — phase docs and approved rows stay untouched until the call.
0a-bis. **Doc-gate cards (017 D2)**: no ledger — proposal substance lands in the target doc's
   「提议变更」section (+ a `progress.md` pointer, resume-reachable); on the human's confirm,
   apply the edits, clear the section, append the doc's Change log gate line, and re-confirm
   the doc. **Upgrading doc-gate→ledger is itself an M2 action** (one-time; past decisions stay
   anchored to their gate lines, not backfilled — D2 既往不追溯).

0b. **Proposal substance first, then the 修改列表 (ledger cards).** On a card with a ledger,
   the reopen target is one or more **approved rows**. Before operating:
   - **Compute the affected closure** — reverse `depends-on` (who depends on the target) ∪
     the trace ripple (design sections citing the id → detail S rows → plan tasks → test
     rows). (--check (c) guarantees the closure walk terminates.)
   - **Land the proposal substance as proposed blocks** in `decisions.md` — the new 陈述 +
     why + alt live there, the generalization of step 0's escalation row (appending proposed
     blocks is not "touching" the docs; approved rows and phase docs stay untouched). A
     proposed block may be rewritten in place while under discussion (git keeps history —
     the supersede-into-new-block rule binds approved blocks only, templates/decisions.md).
     残留/open questions fold into the relevant block's why/alt or a `log.md` line — they
     must survive a session break, not ride the chat.
   - **Present the 修改列表 in chat as a touch-list**: one line per **write op** —
     `id · doc · action (supersede/追加/撤销) · 一句话 what` — each pointing at its proposed
     block; **re-verify items** (read-only re-checks, not write authorizations) collapse into
     one grouped line (count + ids). The human judges substance in the proposed blocks; the
     touch-list is **never persisted as a file** (an analysis note that *precedes* an M2 —
     a reboundary proposal, a design probe — stays a legal note; the list itself is not one).
   The human confirms the list; **no approved row flips and no phase doc is touched before
   that confirm**. Rejected proposals: proposed → retired with a one-line reason. Targeted
   re-grill scope = the closure's decisions.
1. **Two entry points, same discipline:**
   - **Requirement-driven** — the requirement itself shifted: edit `requirement.md`; add a
     dated **Change log** entry stating, per affected 条目, the **change mode**: **追加**
     (add — a new `R-id`) · **变更** (supersede — an existing `R-id`'s statement changes) ·
     **撤销** (retire — keep the ID, mark retired with a note, never renumber). Bump
     `updated`. Affected set = the changed R-ids' traces.
   - **Design-driven (方案变更, requirement unchanged)** — the design is proven infeasible,
     or a better approach replaces it, while every 条目 still stands: **`requirement.md` is
     not touched** (the change record is the superseding ADR + the `log.md` line). Affected
     set = the changed **modules/contracts'** traces, walked downward; and the rewritten
     「How it meets」must **re-verify the same R-ids** against the new approach — that
     re-verification is the substance of the re-approval. `seam-contract-disproved` below is
     the split-design instance of this entry.
2. **Propagate along the spine, mode-specific** — walk the affected set (requirement-driven:
   from the changed 条目; design-driven: from the changed modules/contracts) through
   `design.md` (「How it meets」+ 影响面) → `detail.md` 可追溯 (where present) → `plan.md`
   (`Implements:`) → `test.md` (R-id coverage rows), touching **only** the traced items — not
   a wholesale re-evaluate/regenerate:
   The three modes anchor on **ledger blocks** where a ledger exists (追加 = new proposed
   block; 变更 = old block header → superseded + new proposed block appended; 撤销 = header →
   retired; the proposed blocks already landed at 0b — what executes here, on confirm, is the
   header flips) — re-approval is the 评审会 over the new proposed rows, not a doc re-read:
   - **追加** — append: a new design entry (影响面 updated), detail item if structural, new
     plan task(s), new test rows. Existing content stays valid — **no acceptance resets**;
     design re-approval scopes to the addition.
   - **变更** — supersede: a **new ADR carrying `## Supersedes ADR-NNNN`** (link the
     requirement change; the old ADR gets only a ≤2-line forward cross-ref — **never an
     `## Amendment` block**, see `adr.md`); update the traced design/detail entries; reset the
     traced plan tasks' acceptance **`[x] → [ ]`** with a dated note and the traced test rows
     to unverified. **Proportional re-grill** before re-freeze: design-grill the changed
     modules/contracts only, not the whole design; the re-freeze ask's criterion-conformance
     judge (adversarial-critic.md lens 4) is scoped the same way — the changed criteria/rows
     only, not a whole-doc re-adjudication.
   - **撤销** — retire downstream too: the traced plan tasks / test rows are marked retired
     (with the log line below), not deleted-silently.
2b. **Supersede sweep（mode 变更/撤销 必跑）.** Trace-driven propagation only touches traced
   items; natural-language docs also carry **restatements** of the old semantics *outside* the
   trace — a tail sentence in an untouched bullet, a module name, a term (e.g. a superseded
   claim surviving in an untraced Scope bullet; a renamed module surviving a full rewrite AND
   a consistency agent, because a *name* asserts nothing false). After propagating:
   - Build the retired-phrasing list from the superseding ADR's **被取代表述** section
     (`adr.md`), extending with old names/terms noticed while editing.
   - Run `tools/check-superseded-phrases.py <card-dir> --terms …` (or equivalent grep) across
     requirement/design/detail/plan/test + adr; **every hit resolves one of three ways**:
     rewrite · annotate as 历史表述 (change-log entries and grill/notes history qualify) ·
     record why it stays. No silent hits.
   - **Rename check**: for each changed contract, ask of its module/term names "does the name
     still describe the responsibility?" — rename (dated note) or annotate.
   - **Rewrite checklist**: before editing, collect every scattered "改写时澄清" note
     (evaluation notes, grill log, review) into one checklist and tick each — a self-note not
     carried into the edit list gets lost.
3. **Cross-card ripple.** Check the board's `Deps` (and the design's 影响面 cross-card line):
   a dependent card whose assumptions this change touches gets flagged (its 整体状态 may move
   to `blocked`) and its human told.
4. **Re-approve → re-freeze** (the approval scope = what changed); note the pivot in
   `progress.md`; run the omission check (M3) across all touched docs.

### B. Implementation reality (design is fine, plan was naive)
- Edit `plan.md` freely. **Do not touch `design.md`.** Record the new state in `progress.md`.
- **Implementation-level decisions stay in `log.md`, never the ledger** — the promotion test
  is exactly this A/B boundary: a fork that touches a requirement/design/detail decision
  escalates as a proposed ledger row (case A, gate at entry); everything else logs.
- **Routine refinement is silent; deleting / merging / deferring a task — or invalidating an
  already-`[x]` acceptance — gets a `log.md` `[实现]` line** (what + why), per *Always* below. A
  freely-mutable plan still owes a trail for drops, or resume/close-out review can't tell "done"
  from "forgotten".
- If you're tempted to change `design.md` "just a little" to make the plan easier — that's
  the signal to STOP and treat it as case A (or prove the design infeasible first).

### C. Detail-only change (structures shift, architecture doesn't)
`detail.md` sits at a **baseline** gate, not a freeze: when implementation reality changes a
concrete structure without implicating any `design.md` module/contract, edit `detail.md` in
place **with a dated note (why)** — no ADR, no re-freeze, no full M2. An approved `S<n>` row's
**baseline force** means exactly this: the dated-note refinement never reopens it; only
overturning the decision itself routes through case A. The moment the change
implicates the architecture, it is case A. (See SKILL.md M2 + `detail.md`.)

### Trigger `seam-contract-disproved` (split designs — a frozen seam contract proven wrong at 联调)
This is **case A, mode 变更** (architecture), NOT B: a part's frozen **seam** contract (the `design.md`
「Interface/contract」entry) is disproved when independently-built parts are integrated. Because
parts are tags inside the **single** `plan.md`/`test.md`, "regenerate the affected part" means an
**in-file, scoped** roll-back:
1. **Scope** = the seam's two parts + parts transitively depending on them (via plan Dependencies).
2. **Unfreeze** `design.md`; write a **superseding ADR** for that 「Interface/contract」entry; fix
   the contract (**proportional re-grill** of the fixed contract, per mode 变更); re-approve →
   re-freeze.
3. In the shared `plan.md`, reset the in-scope parts' acceptance **`[x] → [ ]`** with a dated note
   (an "invalidate" move in the binary walk); leave out-of-scope parts' `[x]` intact.
4. Set those parts' `test.md` section / 跨 part 联调 results back to unverified.
5. Move the card's **整体状态** `done`/`active` → `active` (or `blocked` if it now waits on a Dep).
**Never** absorb a disproved contract by quietly editing `plan.md` — that's case B, the opposite.

## Always
Append every change (either case) to `log.md` — one line, **tagged with its 类型**
(`[需求]`/`[设计]`/`[范围]`/`[纠错]`/… per the template's tag enumeration): **what changed + why**
(the trigger: requirement shift / infeasibility / reality). `progress.md` holds the new *state*; `log.md` holds
the *history*.

## Guardrail
The frozen design is the contract. It changes only because the requirement changed, the design
was proven infeasible, or a demonstrably better approach replaces it (recorded via a superseding
ADR — the design-driven entry above) — **never for implementation convenience**.
