---
id: NNN
title: <test plan & results for NNN>
project: <project>
plan: ./plan.md
status: planned | passing | failing
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# 测试 NNN: <title>

> **Reader: Claude-first** (execution zone — the test plan is Claude's; the **pass/fail results**
> surface to the human at the close-out review). Terse & structured. (SKILL.md「Two zones」.)

Tests verify behavior through public interfaces, not implementation details —
they read like a specification and survive refactors. Each maps back to a
success criterion in `requirement.md`.

> **Consolidation doc.** Per-slice unit tests were written during 实现 (TDD or test-after
> mode); here you close coverage + add the tests that span slices (integration / 联调 / manual)
> + record results. Note the project's test mode below.

## Test plan

<!-- Split design (design.md has「Decomposition/Parts」)? Group the Unit / Coverage rows by part
     (one sub-section or a Part column per part) and fill the 跨 part 联调 sub-section below;
     un-split designs leave both as-is. -->

### Unit (from 实现 — inventory the per-slice tests)
- [ ] <behavior> — which slice's test covers it (written in 实现 per the chosen mode).

### Integration
- [ ] <behavior> — where / how.

#### 跨 part 联调 (cross-part integration — only when the design is split into parts)
- [ ] <seam 行为> — 把独立建好的 part 接起来，用**真邻居**（非 mock）验 seam 契约一致性 + 涌现的跨 part 行为。

### Manual verification
- [ ] <step> — expected result.

## Coverage vs success criteria

Every `requirement.md` success criterion (and its `R-id`) maps to ≥1 test — an unmapped R-id is a hole.

| R-id | Requirement success criterion | Covered by |
|---|---|---|
| [R1](./requirement.md) | … | … |

## Coverage vs module interface (when the design introduced a module)

Every interface operation and every contract invariant from `design.md` gets a test. When the
design is **split into parts**, each **seam** contract needs **two levels**: part级 (mock 邻居,
单测) + 联调级 (真邻居, 见上「跨 part 联调」) — a flat single test can't tell "each matches its mock"
from "they actually compose."

| Interface op / invariant (from design) | 层级 part级(mock)/联调级(real) | Covered by |
|---|---|---|
| op: … (inputs→outputs) | … | … |
| invariant: … | … | … |

## Results

| Test | Result | Date | Notes |
|------|--------|------|-------|
| … | `[x]` / `[!]` / `[ ]` | YYYY-MM-DD | … |

**Log sweep**（套件全绿后扫服务端/进程日志找 silent failure — green ≠ no error lines, step 5）:
`<sweep command>` → `[x]` / `[!]` / `[ ]`

<!-- describe-don't-run execution policy (e.g. cbdb): describe commands as suggested
     verification steps; do not run builds/tests by default unless the user asks — the
     log-sweep command above is listed, not run, under this policy. -->
