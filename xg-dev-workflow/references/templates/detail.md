---
id: NNN
title: <detail title>
project: <project>
design: ./design.md
status: draft | baseline | superseded
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# 详设 NNN: <detail title>

> Phase gate: once **reviewed/approved** this file is the **BASELINE** for implementation.
> It stays **mutable** — refine as reality bites, but append a dated note (see Change notes)
> for each change. Only a change that implicates the *architecture* (`design.md`) routes back
> through change-management (M2). This is LLD: concrete structures + rationale, below the
> frozen module-altitude design and above the task-sequencing plan.
> **Reader: human-first** (decision zone — you baseline-review it). Concrete, but still written to
> be reviewed; it's the last human-facing spec before the Claude-first plan. (SKILL.md「Two zones」.)

## 数据结构 (data structures)

For each structure: definition + **why**. One row per field where it helps.

| 结构 / 字段 | 定义 (类型 / 键 / 索引 / 布局) | 为什么 |
|---|---|---|
| … | … | … |

## 关键机制 / 算法 (mechanisms / algorithms)

For each key operation:

### <operation name>
- **触发点 (trigger):** where/when it runs.
- **步骤 (steps):** a multi-step sequence goes as a numbered list, one step per line — never packed into one paragraph:
  1. first step.
  2. next step.
- **加锁 / 事务 (locking / transaction):** what lock, what transaction scope.
- **错误 & 边界 (error & edge):** failure handling, pointed at the safe direction.
- **幂等 (idempotency):** the idempotency point / re-entry behaviour.
- **决策来源:** references the ADR(s) this embodies; small load-bearing choices justified inline.

## 代码级接口 (code-level interfaces)

The concrete code `design.md` deferred — keep consistent with the design's contract table.

- Function / hook signatures.
- Actual SQL / DDL.

## 边界与错误矩阵 (boundary & error matrix)

| 情形 | 行为 (safe direction) |
|---|---|
| 缺失 (missing) | … |
| 并发 (concurrent) | … |
| 部分失败 (partial failure) | … |
| 取消 (cancel) | … |

## 可追溯 (traceability)

| 详设项 | design 模块/契约 | requirement 条目 (R-id) |
|---|---|---|
| … | … | [R1](./requirement.md) |

## Change notes (post-baseline)

Append a dated line per change after baseline; architecture-implicating changes → M2.

- YYYY-MM-DD: <what changed + why>

## Open questions

- …
