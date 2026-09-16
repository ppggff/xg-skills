# Step: review — judging new or changed code

`investigate` answers "how does existing code behave"; `review` judges **new / changed code** — a
commit range, branch, PR or working diff — with a KB-first context pack, parallel lens fan-out and
adjudicated, confidence-scored findings. Read-only: never edits product code. On a lite card, fixes
are ordinary execution — apply and commit them (one concern each) without a further go unless a fix
touches a commitment (then lite.md「Executing」's ask); a fix that changes behavior updates the Req's
验证 line / a test like any slice.

**Context pack on a lite card** = `design.md`'s Req blocks + 当前方案 (its 契约与不变量 rows feed the
invariants axis); the test-adequacy lens's target list is the Req blocks' 验证 lines.

**Two ways it runs**: (1) **ad-hoc** — any time, any diff; (2) the **M+ close-out** (lite.md「Verification
and close-out」) — the review **checks the promised verification ran**: every V row / Req 验证 line maps to
an executed test or check, or to a recorded, reasoned downgrade; a silently dropped scenario is a finding,
and the report carries the per-row verdict. An S card may skip the close-out review — say so in the doc.

## Procedure

1. **Resolve target, eligibility, base, anchoring.** Accept a range / branch / PR / "current diff"; in a
   multi-repo workspace confirm which repo. Skip (and say so) if already reviewed and unchanged, or
   trivially mechanical. Diff size: ~300 lines is one sitting; >1000 suggests slices.
   **Pin the base ref and state it in the report.** The human's explicit range wins; otherwise —
   close-out of a card → the card's **integration point**, `git merge-base origin/<main> HEAD` (the
   whole set of commits the card adds on trunk, not the latest session's slices — a multi-session
   card is the trap); repeat review of a card → the tip the last `notes/review-*.md` covered (record the
   reviewed-through SHA in every report); ad-hoc with only a branch → its merge-base with trunk.
   **Fail fast before any dispatch**: `git rev-parse <target>` and a non-empty diff.
   **Anchoring**: active card (named, or resumed into) → the card's `notes/`; no active card but the
   target is plainly one card's work (its branch / commits implement a board slug) → **ask one question**
   (这是 card NNN 的实现，报告挂它的 notes/ 还是走 standalone?) rather than defaulting; neither →
   standalone, `<project>/reviews/`. Looser than `investigate`'s anchoring on purpose: a review target
   objectively *is* some card's implementation.

2. **Assemble the context pack before dispatching anything** — lens agents without domain context
   report designed semantics as bugs: KB concepts of the touched subsystems (invariants, known
   semantics, prior decisions) · the card's design.md / ADRs / part-check notes (their dispositions are
   not re-litigated) · repo conventions (`CLAUDE.md`s) · the human's recorded review lenses
   (safe-not-just-live, no blocking IO under locks, cross-XID-space rules …). Distill it and embed it in
   **every** agent prompt.

3. **Own the riskiest slice.** The orchestrator deep-reads the highest-risk part (invariant /
   concurrency / lock / recovery code) with the pack in hand; breadth goes to parallel lens agents.

4. **Pick the tier, then dispatch** (briefs, models, menu and stop-rule: `references/lenses.md`「Review
   lenses」). Tier by stakes — diff size, card size, invariant density, the human's ask (「彻底审」→ deep);
   state it in the report.
   - **light** (XS/S, diff <~150 lines, not invariant-heavy) — no subagents: the orchestrator reviews
     inline across the three axes (spec · standards · invariants) with the pack; step 5 still applies.
   - **standard** (M, one-sitting diff) — three axis agents, each a complete self-contained brief.
   - **deep** (L, invariant-heavy, an M+ close-out of such code, or asked) — the lens fan-out +
     adversarial trio + the model-diversity sweep + saturation passes. **Start lean, expand on
     evidence**: pass 1 = the sharp core (correctness-vs-invariants · trio · sweep) plus only the menu
     lenses the diff plainly indicates; the rest join a later pass if the saturation verdict says
     under-sampled — max fan-out upfront buys redundancy, not recall.
   **Zero-activation replay** (any tier, when the change adds a check / guard / handler): what was its
   activation count on the real baseline the change was validated against? A mechanism that never
   fired has an untested surface no green baseline vouches for — replay real inputs through it first.
   **Tier calibration**: a target class repeatedly reviewed light / standard whose misses surface later
   (a deep pass, a shipped bug, a retro) gets its default tier bumped at retro.

5. **Adjudicate every finding.** Verify it yourself (or via an independent verifier) against the actual
   code, confidence 0–100: ≥80 → finding, 50–79 → an explicitly-uncertain note, below → drop (scores
   stay off the human-facing surface). Verify the **trigger condition's distance**, not just the
   mechanism — a real failure whose precondition is a remote tail case is a sizing note, not a finding.
   **Adjudicate the suggested fix too** against the pack's invariants — a real finding can carry a fix
   that violates one (a fallback reintroducing a forbidden cross-space comparison); correct it before it
   enters the report. Killed findings go to 误报澄清 with their source lens + model — why a plausible
   finding is false is part of the deliverable, and the per-model survive / die tally is what retro's
   model calibration reads. Exemplars for agents: `lenses.md`「Review lenses」. Deep tier: the
   **saturation verdict** (`lenses.md`) decides "another pass?" from overlap, and goes in the report.

6. **Report — lands in dev_root, never the repo.** Card → `<card>/notes/review-YYYY-MM-DD-<target>.md`
   (the `review-` prefix and the date are load-bearing — multi-round reviews sort and don't collide; a
   same-day second round appends `-2`); standalone → `<dev_root>/<project>/reviews/YYYY-MM-DD-<slug>.md`.
   Shape: 总体结论 (approve when the change definitely improves overall code health, not when it is
   perfect; the saturation one-liner) → findings by severity, each a field block (现象 · 依据 with `file:line` ·
   改法 — label line + indented free-form content, never one long bullet) → 误报澄清
   → **确认正确的关键点** (what was checked and confirmed against the invariants — for invariant-heavy
   code this positive half carries as much value as the findings) → **修复决策表** → suggested
   verification steps, labeled NOT executed where the repo's execution policy forbids running them.
   The 修复决策表 closes the report so the human acts in one pass — one row per actionable item:
   `# | 项目 | 级别 | 预期修复 | 你需要定` — a mechanical single-way fix gets 否, an item with real
   alternatives gets **是** plus the choices and your recommendation; flag rows whose files need explicit
   approval under the repo's scope rules. Items judged not worth fixing → a 明确不修 line with the reason.
   A review-born Future / deferred item states its provenance (evidence-cited / 推断 / 假设) like any
   claim. Chat reply ≤10 lines pointing at the report, **with receipts** (path + dev_root commit — write
   first, then reply); echo the table only when the human asks to choose.

7. **Log usage** — `--action review` in both contexts (a review inside a card is still a review).
