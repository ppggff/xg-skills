# Step: review — deep tier (continuation of `review.md`)

Read this **together with** `references/steps/review.md`, and only when the chosen tier is
**deep** (step 4). It holds the deep-only machinery lifted out of `review.md` so the
light/standard path stays resident-lean: the **lens fan-out menu** + per-lens **model
assignment**, the **standing model-diversity sweep**, and the **5b saturation stop-rule**.
This file is a continuation, not a standalone procedure — cross-references below to
"step 1/4/5/6", "the false-positive exemplars below", and the report shape all point back into
`review.md` (the exemplars are step 5's; 5b's overlap tally is the confirmed side of step 5's
per-model survive/die tally).

## Deep-tier lens fan-out + model assignment + standing diversity sweep

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
  to implement's simplify sweep, for the low-inference cleanup family a diff-first read catches.
  Assess the diff against the **Fowler smell catalog** (`references/smell-catalog.md` — paste it
  into the agent's brief); the families that recur here are **Speculative Generality** (a static-fn
  parameter every caller passes constant/NULL, an unreachable mode — dead code / unused generality),
  **Duplicated Code** (a copy-pasted call shape that wants one helper), **Middle Man** (a
  pass-through layer, or a flag/state-machine/ranking a simpler check replaces — apply the deletion
  test), **locality** (pure functions extracted for testability while the failure modes live in
  their untested call orchestration; state leaking across a seam), and **single-adapter seams** (a
  port with exactly one implementation and no test-double consumer — one adapter is a hypothetical
  seam, two is a real one), plus non-smell
  **efficiency-hoist** (side-effect-free/expensive work above the guard that
  skips it; per-row work that belongs in one-time setup). These are one coherent family — bundle
  them in **one** agent, not one-per-check; recall loss is cheap here (a missed cleanup is a
  nice-to-have, not a bug), which is exactly why merging is safe for this family and not for
  correctness/concurrency/security. **Deep tier only** — standard's Standards axis already carries
  hygiene; don't add this lens at light/standard. Distinct from the adversarial trio (which reads
  problem-first): this reads the diff for local cleanups, so note the boundary and don't
  double-report a finding both surface;
- docs accuracy (claims in docs/comments match the new behavior).
Each agent prompt = context pack + its lens + the false-positive exemplars below
+ "verify each finding against actual file content before reporting; return
structured findings (severity, file:line, issue, why, suggested fix); keep the
report under ~400 words — if findings overflow, keep the highest-severity and state the
count omitted; return empty if none — don't invent issues."
**Model assignment (per-lens application):** checklist/verification-driven lenses default
to the cheaper model (Agent tool, `model: sonnet`) — **conventions conformance** (comment
hygiene, check-code-refs run, terminology), **tests hygiene**, **docs accuracy**,
**git-history**, **quality/simplify**; the inference-heavy lenses stay on the session model,
capped at opus (a fable session dispatches them at `model: opus`) —
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

## 5b — saturation verdict (deep tier)

**Saturation verdict — decide "another pass?" from overlap, not gut feel.** During
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
