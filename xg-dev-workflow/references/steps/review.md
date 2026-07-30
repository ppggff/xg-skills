# Step: review (the front door for reviewing new/changed code)

`investigate` answers "how does existing code behave"; `review` judges **new/changed
code** — a commit range, branch, PR, or working diff. It composes M1 (evidence) and
M5 (KB-first context) with two ideas merged from external review skills: parallel
lens fan-out (user `review` skill) and confidence-scored finding verification
(official code-review plugin, feature-dev code-reviewer). The five-axis lens menu
draws on agent-skills `code-review-and-quality`.

Read-only: never edits product code, never advances a phase. Fixes happen only on an
explicit human go afterwards — and when applied, **each fix is committed** (one concern per
commit, per implement's Commit cadence; `push` stays human-gated). **A fix that changes
behavior updates `test.md` (a coverage row + suggested-verification) like an implement slice,
then runs M3** — applying fixes as a quick commit batch bypasses the per-slice test-write
discipline, and M3's test-consistency check only fires if you actually run it after the edit.

**Two ways it runs:** (1) **ad-hoc** — invoked any time on any diff/PR (standalone); (2) **the
standard close-out gate** for an M-or-larger requirement — run after 测试, before the card goes
`done`, so every non-trivial change ends with both a test doc and a review doc. In the close-out
case a requirement is active, so it lands in `<requirement>/notes/review-*.md` (see step 6) and the
context pack should pull that requirement's `requirement.md`「需求条目」/ frozen `design.md`
「影响面」+「验证策略」— the close-out **checks the promised scenarios ran**: every 验证策略 row
maps to an executed test/check in `test.md` (or a recorded, reasoned downgrade); a silently
dropped scenario is a finding. The report carries the per-row verdict (the 核对结果 the
M3 close-out shape check looks for).
XS/S structure-light work may skip the close-out — then record `XS/S — review skipped` in
`progress.md`'s `Close-out:` line (the M3 gate is "review doc OR skip note"); see
SKILL.md「Requirement sizing」.

## Procedure

1. **Resolve target + eligibility + anchoring.** Accept a commit range / branch / PR /
   "current diff"; in a multi-repo workspace confirm which repo. Skip (and say so) if
   already reviewed and unchanged, or trivially mechanical. Note diff size: ~300 lines
   is one sitting; >1000 suggests reviewing in slices.
   **Pin the base ref (what "the change" is measured against) — state it in the report.**
   The human's explicit range/PR always wins. When none is given:
   - **Close-out gate for a card** → base = the card's **integration point**: `origin/<main>`
     (or the merge-base with it, `git merge-base origin/<main> HEAD`) — the whole set of commits
     this card adds on top of trunk, so the review sees the card as it will land, not just the
     latest session's slices. `progress.md` frontmatter (repo/branch) names the branch; a
     recorded design-freeze / branch-start SHA, if present, is the base when the card shares a
     branch with earlier merged work.
   - **Repeat review of the same card** → base = the **tip the last `notes/review-*.md` covered**
     (record the reviewed-through SHA in each report so the next round is incremental) — review
     only commits since, plus any file the prior round flagged and a fix touched.
   - **Ad-hoc / standalone** → base = whatever the human named; if only a branch is given, its
     merge-base with trunk.
   Cross-session cards are the trap: a multi-session card's "latest changes" is **not** the card's
   change — always base on the integration point, or a sweep/review silently misses the earlier
   sessions' commits.
   **Fail fast before any dispatch:** resolve the ref (`git rev-parse <target>`) and confirm
   the diff is non-empty — a bad ref or an empty diff dies here, not inside parallel lens
   agents.
   **Anchoring (where the report lands):** active card (human named it, or the session
   resumed into it) → the card's `notes/`. No active card but the target is plainly one
   card's work (its branch/commits implement that card — check the project `index.md`
   slugs) → **ask one question** ("这是 card NNN 的实现,报告挂它的 notes/ 还是走
   standalone?") instead of silently defaulting to standalone — otherwise the same
   card's review history scatters across `notes/` and `reviews/` depending on how the
   session happened to start. Neither → standalone (`<project>/reviews/`).
   (**Deliberately looser than `investigate`'s anchoring:** a review target objectively IS
   some card's implementation — checkable against the board — whereas an investigation topic
   is merely *about* something; that's why investigate defaults standalone and review asks.)

2. **Assemble the context pack (do this BEFORE dispatching any agent).** This is the
   step that distinguishes this verb from a generic review: lens agents without
   domain context report designed semantics as bugs.
   - KB: query xg-knowledge-lite for the touched subsystems' concepts (invariants,
     known semantics, prior decisions).
   - Requirement active → its `requirement.md` / frozen `design.md` / ADRs.
   - Repo conventions: relevant `CLAUDE.md` files; the human's recorded review
     lenses / feedback memories (e.g. safe-not-just-live, no blocking IO under
     locks, cross-XID-space rules — whatever the project's list is).
   - Distill into a short context pack and embed it in **every** lens-agent prompt.

3. **Split the work: own the riskiest slice.** The orchestrator personally deep-reads
   the highest-risk part (invariant/concurrency/lock/recovery code) with the context
   pack in hand — don't delegate the crown jewels. Delegate breadth to parallel lens
   agents.

4. **Pick the tier, then dispatch.** Tier by stakes — diff size (step 1), requirement sizing,
   invariant density of the touched code, and the human's explicit ask (「彻底审」→ deep). State
   the chosen tier in the report.
   - **light** (XS/S card, diff <~150 lines, not invariant-heavy) — **no subagents**: the
     orchestrator reviews inline with the context pack across the three axes below (spec trace ·
     standards/hygiene · invariants), applying the critic's standing rules (they are inline
     rules already). No sweep; step 5's adjudication discipline still applies to its own
     findings; 5b is skipped (single path).
   - **standard** (M, ~one-sitting diff) — **three axis agents** (axis shape from the external
     `code-review` skill's two-axis economy + our KB axis; each gets a complete self-contained
     brief — paste the checklist/context pack in full, assume no shared memory; ~400-word cap):
     **Spec axis** (session model) — does the change do what requirement/design say: R-id trace,
     missing/partial items, scope creep (test: every changed line traces to a requirement /
     design item; an untraceable line is creep or an unrecorded decision). **Standards axis**
     (`model: sonnet`) — conventions + comment/tests/docs hygiene (incl. the check-code-refs
     run) + **reuse/cohesion when the change adds helpers/abstractions** — apply the checks in
     `references/simplify-checks.md` (paste them into the axis brief; it assumes no shared memory).
     Where the repo documents no convention for a smell, fall back to the **smell catalog** baseline
     (`references/smell-catalog.md`); skip anything tooling already enforces. **Invariants axis** (session model) —
     context-pack invariants, concurrency, fail-safe, security. No model-diversity sweep at this
     tier; findings carry their axis into adjudication.
   - **deep** (L, invariant-heavy, an M+ close-out of such code, or the human asks) — the lens
     fan-out below + adversarial trio + the standing different-model sweep + saturation repeat
     passes (5b). **Start lean, expand on evidence:** pass 1 dispatches the sharp core
     (correctness-vs-invariants · adversarial trio · the sonnet sweep) plus only the menu lenses
     the diff plainly indicates; the remaining lenses join a later pass only if 5b judges the
     space under-sampled — max fan-out upfront buys redundancy, not recall.

   **Tier calibration (M6):** like model downgrades, tier choices sit under retro calibration —
   a target class repeatedly reviewed at light/standard whose misses surface later (a deep pass,
   a shipped bug, a retro) gets its default tier bumped. SKILL.md「Subagent model assignment」
   is the model-side analog.

   **Deep tier — you MUST read `references/steps/review-deep.md` before running:** it carries the
   lens fan-out menu (incl. per-lens model assignment) and the standing model-diversity sweep,
   plus the 5b saturation stop-rule. A deep review without it is incomplete.

5. **Adjudicate every finding (non-negotiable).** Before anything enters the report,
   verify it yourself (or via an independent verifier agent) against the actual
   code, scoring confidence 0–100; report only ≥80 as findings, carry 50–79 as
   explicitly-uncertain notes, drop the rest. Verify the TRIGGER CONDITION's
   distance, not just the mechanism — a real failure mechanism whose precondition
   is a remote tail case (e.g. "only after shared slop exhausts cluster-wide") is
   a sizing note, not a finding; re-derive how far away the trigger actually is. **Adjudicate the suggested FIX too,
   not just the finding** — check it against the context pack's invariants: a real
   finding can carry a fix that violates a design invariant (e.g. a fallback that
   reintroduces a forbidden cross-space comparison); correct or replace such fixes
   before they enter the report, and note the correction. Findings killed on review
   go to a 误报澄清 section — recording why a plausible finding is false is part of
   the deliverable; tag each killed finding with its source lens + model, so the
   per-model survive/die tally (with 5b's confirmed side) is computable at retro
   time — that tally is what SKILL.md「Subagent model assignment」's M6 calibration
   reads. False-positive exemplars (give to agents verbatim): pre-existing
   issues; linter/compiler-catchable; lines the change didn't modify; intentional
   behavior changes tied to the broader change; **designed semantics documented in
   the KB / design docs**.

5b. **Saturation verdict (deep tier) — the "another pass?" stop-rule (overlap-dominant vs
   singleton-heavy, the standard-tier caveat, dry-stop, and the one-line report verdict) now
   lives in `references/steps/review-deep.md`; consult it on any deep run.**

6. **Report — lands in dev_root, never the repo.**
   - Requirement active → `<requirement>/notes/review-YYYY-MM-DD-<target>.md` (the `review-`
     prefix is load-bearing — the M3 close-out gate globs `notes/review-*.md`; the date keeps
     multi-round reviews of the same target from colliding and sorts them chronologically;
     a same-day second round appends `-2`), plus a row in `progress.md` (Discovered issues /
     Design iterations as appropriate).
   - Standalone → `<dev_root>/<project>/reviews/YYYY-MM-DD-<slug>.md`.
   - Close-out review landing also sets `plan.md` frontmatter `status: done` (the plan's
     lifecycle closes with the card, plan step 7).
   Shape: 总体结论 (approval standard: approve when the change definitely improves
   overall code health — not when it's perfect; include the 5b saturation-verdict
   one-liner) → findings by severity with
   file:line + suggested fix → 误报澄清 → **确认正确的关键点** (what was checked
   and confirmed against the invariants — for invariant-heavy code this positive
   half carries as much value as the findings) → **修复决策表** → suggested
   verification steps, labeled NOT executed where the repo's execution policy
   forbids running them.
   The 修复决策表 (fix-decision table) closes the report so the human can act on it
   in one pass — one row per actionable item:
   `# | 项目 | 级别 | 预期修复 | 你需要定`. Mechanical single-way fixes get 否; an
   item with real alternatives gets **是** plus the concrete choice and your
   recommended option; flag rows whose files need explicit approval under the
   repo's scope rules (e.g. test dirs). Items judged not-worth-fixing go to a
   明确不修 line below the table, with the reason.
   **Future/deferred items obey M1 like any other claim**: a review-born Future item states
   its provenance (evidence-cited / 推断 / 假设) — an unverified "this wastes X" written as
   fact propagates into later requirements as one.
   Chat reply ≤10 lines pointing at the report — **with receipts**: the report path + the
   dev_root commit (write first, then reply; SKILL.md Stop-at-gate「Ask with receipts」). The
   table may be echoed in chat when the human asks to choose.

7. **Log usage** — `--action review` (both contexts; unlike `investigate`, a review
   inside a requirement is still a review, not a design step).
