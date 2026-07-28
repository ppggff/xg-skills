# Step: 测试 (test — consolidation)

Forked from **`tdd`** (behavior-through-public-interface, vertical slices) **+ test-driven-development**
(test pyramid / sizes). **The per-slice red-green loop now lives in `实现`**
(implement's Test mode — TDD or test-after by project); this 测试 phase is the **consolidation
layer**: prove coverage, add the tests that span slices (integration / 跨 part 联调 / manual / E2E),
balance the pyramid, run the full suite (or describe it for "describe, don't run"), and record
results. Adjusted: output is this requirement's `test.md`; every test maps back to an `R-id` /
success criterion; honors the project's test-execution policy — e.g. cbdb's "describe, don't run
by default" (write the plan + the commands; run only when asked).

Output: `test.md` (template: `references/templates/test.md`).

## Principles
- Test **behavior through public interfaces**, not implementation details — a good test
  reads like a spec and survives refactors.
- **No tautological tests** — an assertion must not recompute the expected value the way the
  implementation does (`expect(add(a,b)).toBe(a+b)`, a snapshot derived by the same logic, a
  constant asserted equal to itself): it passes by construction and can never disagree with the
  code. Expected values come from an **independent source of truth** — a known-good literal, a
  worked example, the spec (from `tdd`).
- **Per-slice unit tests come from `实现`** (one test ↔ one slice, per the chosen mode) — never
  "all code then all tests". This phase doesn't re-write them; it **consolidates** and adds what
  spans slices.
- **Mind the pyramid + test sizes** — most tests **small** (pure logic, ms), fewer **medium**
  (integration, localhost), fewest **large** (E2E). Prefer **real > fake > stub > mock**; mock only
  slow / non-deterministic boundaries (from `test-driven-development`).
- **Data-type diversity for type-generic code paths** — when the code under test is generic over
  key/value types (comparators, hashing, ordering, serialization), the fixtures must include at
  least one type with **non-trivial representation behavior** (e.g. varchar's binary-coercion
  RelabelType, a collatable type), not int-only tables — an all-int suite can silently keep a
  type-specific wrong-results path green.
- **Pick the strategy by dependency category** (`codebase-design` DEEPENING) — it decides how you
  cross the seam: **in-process** (pure/in-mem) → test directly through the interface, no double;
  **local-substitutable** (PGLite, in-mem fs) → run the stand-in in the suite; **remote-owned**
  (your service over a network) → a **port** + in-memory adapter in tests, HTTP/gRPC adapter in prod;
  **true-external** (Stripe/Twilio…) → injected port + mock adapter.
- **Exploit the design's testability** — if a module was designed to be mock-isolatable, test it
  **in isolation** with its dependencies mocked, instead of dragging the whole stack in to
  exercise one module.
- **Check setup/constructor errors in tests that spawn real resources** (pty, ports, files,
  processes). A `sess, _ := Create(...)` there turns a transient resource failure into a
  nil-deref panic that masquerades as a flaky race under `-count`/`-race` — fail loud with the
  error instead.
- **UI / mobile-facing slices** → see `references/frontend-testing.md` (browser + real-device testing).

## Procedure
1. **Inventory the per-slice tests** already written in `实现` (per the chosen mode) — don't rewrite them.
2. **Close coverage by `R-id`** — every `requirement.md` success criterion maps to ≥1 test; fill
   the "Coverage vs success criteria" table, **starting from the design's 验证策略 table when one
   exists** (each promised E2E scenario becomes a test/manual row; note any deviation from a
   promised scenario or observation point — silently substituting a weaker proof is a hole). An
   unmapped `R-id` is a hole → add the missing test.
3. **If the design introduced a module**, fill "Coverage vs module interface": every interface
   **operation** (inputs→outputs) + every contract **invariant** (uniqueness, idempotency,
   self-heal, degradation…) maps to ≥1 test, through the **public interface** (that is what
   "behavior, not implementation" means here).
4. **Add the tests that span slices** — integration, **跨 part 联调** (real neighbors, not mocks),
   manual / E2E, the anomaly/edge cases the per-slice loop didn't reach, and the **regression
   rows from `design.md`「影响面」「需回归的行为」** (fill the test plan's 回归 sub-section).
5. **Run & record** — TDD mode: run the full suite. test-after / describe-don't-run (e.g. cbdb): list the exact commands as
   **suggested steps**, don't execute. Record results as the **binary** check (`[x]/[!]/[ ]`, with
   date; per implement.md「Binary verify」— **no subjective `[x]`**).
   **After a full-suite run, sweep the server/process logs for silent failures** — green ≠ no
   error lines; a masked path (fallback, retry, manual-path shadowing) can pass every assertion
   while logging the real failure. For "describe, don't run", list the log-sweep command
   alongside the suite commands.
6. **Any bug found here → Prove-It** — write the failing reproduction test first, then fix it in an
   `实现` slice (don't patch silently from the 测试 phase).

## Runtime override
`test use:agent-skills:test` or `use:<your-skill>`.

## Done when
- `test.md` frontmatter `status` set from the Results walk (`passing` / `failing`).
- Every success criterion (every `R-id`) maps to ≥1 test; **if a module was introduced, every
  interface operation + contract invariant also maps to ≥1 test**; results recorded. Then run the
  omission check (M3).
- **Close-out review:** for an **M+** requirement (see SKILL.md「Requirement sizing」), run the
  `review` verb (`review.md`) on the whole change to produce the close-out review doc
  (`notes/review-*.md`) **before** the card goes `done` — code earns both a test doc and a review doc.
  **XS/S** structure-light work may skip it (mirror of `detail.md`'s optionality), but then record
  `XS/S — review skipped` in `progress.md`'s `Close-out:` line so M3 sees the decision (the gate is "review doc OR skip
  note"). Then mark the requirement resolved.
