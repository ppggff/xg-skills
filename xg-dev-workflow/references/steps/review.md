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
context pack should pull that requirement's `requirement.md`「需求条目」/ frozen `design.md`「影响面」.
XS/S structure-light work may skip the close-out — then record `XS/S — review skipped` in
`progress.md` (the M3 gate is "review doc OR skip note"); see SKILL.md「Requirement sizing」.

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
     run) + **reuse/cohesion when the change adds helpers/abstractions**: does a new helper
     duplicate one in the touched module (grep it), and is a new cross-cutting concern consistent
     with a sibling pattern the *same change* built (an interface hook vs a caller-side
     `if type == :foo` special-case)? Name these two checks explicitly — an embedded shared
     sub-expression evades a whole-function dup scan. (The same two checks mirror implement.md's
     simplify-sweep reuse/cohesion checklist — keep the two in sync.) **Invariants axis** (session model) —
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

   **Deep tier — lens fan-out (parallel agents; scale count to diff size, asked effort, and —
   on a repeat pass — the prior pass's saturation verdict, step 5b).**
   Menu — skip lenses that obviously don't apply and note the skips:
   - correctness vs documented invariants/design (the sharp lens);
   - **fresh-context adversarial trio (`adversarial-critic.md`)** — three lenses run from the
     problem, not the diff: *causal-coverage* (does each change map to a real cause; anything
     unnecessary or any gap?), *invariant-ledger replay* (does an established invariant make a
     flagged concern moot / a change redundant?), *search-before-build* (did the change reinvent
     an existing mechanism?);
   - project-convention conformance (incl. comment hygiene: comments the change added outside
     docstrings / step markers / why-notes — over-commenting is a finding, not a style nit; and
     workflow/KB doc references leaked into code — run `tools/check-code-refs.py --base <base>`
     on the target, a hit is a finding unless the file's domain is the docs);
   - tests (assertions match spec semantics; hygiene: no hardcoded dates/paths,
     generated-file conventions);
   - security / input validation / privilege checks;
   - **lifted fail-safe symmetry** — the diff *removes or relaxes a rejection path* (an error
     branch, a whitelist entry, a refusal)? then check (a) the **symmetric surface** picked up
     the load (a build-side lift needs its dump/serialize/reverse-path counterpart, and vice
     versa) and (b) **type-wrapper boundaries** (RelabelType/coercions: does the new positive
     path still fire when the value is wrapped, or does it silently fall back to a default?);
   - performance (hot paths, N+1 dispatch, lock scope);
   - git history (blame, prior fixes and review comments, in-code guidance comments);
   - **quality/simplify (one bundled sonnet agent, deep tier only)** — the review-side backstop
     to implement's simplify sweep, for the low-inference cleanup family that a diff-first read
     catches: **dead code / unused generality** (a static-fn parameter every caller passes
     constant/NULL, an unreachable mode), **duplication** (a copy-pasted call shape that wants
     one helper), **efficiency-hoist** (side-effect-free/expensive work sitting above the guard
     that skips it; per-row work that belongs in one-time setup), **altitude/over-abstraction**
     (a pass-through layer, or a flag/state-machine/ranking a simpler check replaces). These are
     one coherent family — bundle them in **one** agent, not one-per-check; recall loss is
     cheap here (a missed cleanup is a nice-to-have, not a bug), which is exactly why merging is
     safe for this family and not for correctness/concurrency/security. **Deep tier only** —
     standard's Standards axis already carries hygiene; don't add this lens at light/standard.
     Distinct from the adversarial trio (which reads problem-first): this reads the diff for
     local cleanups, so note the boundary and don't double-report a finding both surface;
   - docs accuracy (claims in docs/comments match the new behavior).
   Each agent prompt = context pack + its lens + the false-positive exemplars below
   + "verify each finding against actual file content before reporting; return
   structured findings (severity, file:line, issue, why, suggested fix); keep the
   report under ~400 words — if findings overflow, keep the highest-severity and state the
   count omitted; return empty if none — don't invent issues."
   **Model assignment (per-lens application):** checklist/verification-driven lenses default
   to the cheaper model (Agent tool, `model: sonnet`) — **conventions conformance** (comment
   hygiene, check-code-refs run, terminology), **tests hygiene**, **docs accuracy**,
   **git-history**, **quality/simplify**; the inference-heavy lenses stay on the session model —
   **correctness-vs-invariants**, the **adversarial trio**, **security** (perf: judge by the
   diff). Rationale + M6 calibration: SKILL.md「Subagent model assignment」(5b's overlap stats
   feed that calibration).
   **Standing model-diversity agent:** besides the lens agents, dispatch **one light-sweep
   agent on a different model** (Agent tool, `model: sonnet`) — same-model lenses share
   failure modes; a different model decorrelates them. Its framing is fresh-eyes,
   not a copied lens prompt: context pack + intentional-changes list + false-positive
   exemplars + "report only what you're confident is real — zero findings is a good
   outcome"; encourage it to *execute* the changed tools/flows where read-only-safe, not
   just read them. Deep tier only (light/standard run without it); within deep, skip only when
   the whole review is skipped (step 1 triviality).

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

5b. **Saturation verdict — decide "another pass?" from overlap, not gut feel.** During
   adjudication, record for each confirmed finding **how many independent paths hit it**
   (which lens agents + the orchestrator's own deep-read, each path tagged with its model —
   the confirmed side of step 5's per-model survive/die tally). "A re-review found something"
   is sampling variance — a review is a bounded search over a generative defect space,
   not an exhaustive proof — so the overlap statistics, not the existence of new
   findings, are the signal (capture-recapture intuition):
   - **Overlap-dominant** (most confirmed findings hit by ≥2 paths) → the current
     severity band is near-saturated; another pass yields tail only → recommend **stop**.
   - **Singleton-heavy** (most confirmed findings hit by exactly one path) → the space is
     under-sampled → one more pass is justified, **along axes not yet used**: a different
     slicing (by subsystem vs by concern), a different reading direction (diff-first ·
     problem-first adversarial · **spec-first** against requirement/design contracts ·
     **history-first** via blame/prior fixes), opposite polarity (verify-claims vs
     hunt-bugs), or a **different model** (a further model beyond step 4's standing sonnet
     agent). Re-running an existing lens prompt raises confidence (voting), **not**
     recall — don't count it as diversity.
   - **Standard-tier caveat:** the three axes are disjoint by design, so singleton-heavy is
     the *expected* shape there — at standard tier judge stop by the dry-stop rule, not overlap;
     overlap stats carry signal at deep tier.
   - **Dry-stop:** a pass whose confirmed findings all fall below the action bar (nothing
     that would add a 修复决策表 row) is **dry** → stop regardless of overlap. A new
     High on a later pass is a genuine earlier miss → send to retro (which lens/slice
     missed it, why).
   State the verdict in one line (in the report and chat), e.g.
   `Review 饱和判定: 建议停 — 8/9 confirmed 被 ≥2 路径命中, 无行动线上新发现` ·
   `Review 饱和判定: 可再补一轮 (spec-first / history-first) — 5/7 为 singleton`.
   Like the grill convergence auto-verdict (`grill.md`), it is a recommendation — the
   human decides. Cost cap: every extra lens's findings still pass step 5 adjudication,
   so diversity is bounded by adjudication bandwidth and the asked effort, not by how
   many agents can be spawned.

6. **Report — lands in dev_root, never the repo.**
   - Requirement active → `<requirement>/notes/review-YYYY-MM-DD-<target>.md` (the `review-`
     prefix is load-bearing — the M3 close-out gate globs `notes/review-*.md`; the date keeps
     multi-round reviews of the same target from colliding and sorts them chronologically;
     a same-day second round appends `-2`), plus a row in `progress.md` (Discovered issues /
     Design iterations as appropriate).
   - Standalone → `<dev_root>/<project>/reviews/YYYY-MM-DD-<slug>.md`.
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
