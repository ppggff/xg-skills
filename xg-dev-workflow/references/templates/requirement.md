---
id: NNN
title: <requirement title>
project: <project>
status: drafting | confirmed | superseded
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# 需求 NNN: <requirement title>

> Phase gate: this file must be **confirmed** by the human before design starts.
> **Reader: human-first** (decision zone — you read & confirm it). Write it to be reviewed: prose,
> rationale, sharp boundaries. Claude also implements against it. (See SKILL.md「Two zones」.)

## Context (背景)

Why this is being done — the problem or need, what prompted it, the intended outcome.
State assumptions explicitly. Every non-trivial claim cites code (`func()` in `file.c`) or a
doc/`[[wiki/<project>/<slug>]]`; **mark each load-bearing claim's provenance** — evidence-cited /
推断 (inferred) / 假设 (assumption) — per M1.

## 需求条目 (Requirement items) — the canonical itemized list

The atomic, individually-trackable statements of what is required — **the traceability spine**.
One row = **one** requirement (a title with "and" is two). Each gets a **stable ID** (`R1`, `R2`,
…): never renumber; to drop one, mark it `retired (YYYY-MM-DD: why)` rather than reusing the number.
Scope / Effect below **and** downstream docs (`design.md`「影响面」&「How it meets」, `detail.md`
可追溯, `plan.md` tasks, `test.md` coverage) **reference these IDs** instead of restating the text.

**需求条目 vs Effect — keep them distinct:** a 条目 states **what** is required (the need); an Effect
criterion states the **checkable condition that proves it** (the how-we-verify), and cites the R-id
it tests. E.g. 条目 `R1: 同一时刻至多一个 coordinator 运行 autovacuum` → Effect `观测 pg_stat_activity
中 launcher ≤ 1（verifies R1）`. Don't duplicate one as the other; they are need ↔ acceptance.

| ID | 需求条目 (one atomic statement) | 类型 (功能/约束/非功能) | provenance (evidence / 推断 / 假设) |
|----|--------------------------------|------------------------|-------------------------------------|
| R1 | … | … | `func()` in `file.c` / `[[wiki/…]]` / 假设 |

## Scope (范围)

- **In scope:** … (by R-id where it sharpens the boundary)
- **Out of scope:** …
- **Affected (初步影响面):** modules / callers / consumers likely touched — full analysis in `design.md`「影响面」.

## Constraints (约束)

ABI / interface stability, project change rules, compatibility, performance, environment.
(e.g. cbdb: no ABI/extension/SQL-interface changes unless requested; changes minimal, module-local, reversible.)

## Effect (效果 — measurable success criteria)

Reframe the ask as testable conditions. "Done" means each of these is true. **Each criterion cites
the R-item(s) it verifies** (so a changed `R` localises to its criteria + tests):

- [ ] … (verifies R1)
- [ ] … (verifies R2)

## Future (未来)

What is deliberately deferred; extensibility expected later; what we are NOT solving now and why.

## Open questions

- …

## Change log

- YYYY-MM-DD — created.
<!-- On any requirement change, add a dated entry here and trigger the change-management flow
     (M2). State each affected 条目's mode — 追加 (new R-id) / 变更 (supersede) / 撤销 (retire,
     keep the ID) — it drives the scoped downstream propagation. -->
