---
id: NNN
title: <progress for NNN>
project: <project>
plan: ./plan.md
status: not-started | in-progress | blocked | done
current_task: <N>
branch: <optional product branch — the viewer's gitweb "code" link deep-links here>
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Progress NNN: <title>

> Single source of truth for **session resume**. A fresh session reconstructs state
> from this file alone (M4). Keep it current; it is the handoff, **not a diary**.
>
> **Reader = Claude-on-resume** (execution zone — a machine handoff): terse, structured,
> current-state. The human-audit narrative ("why we got here") lives in `log.md`, which resume
> never reads — that reader split is what lets this file stay small. (See SKILL.md「Two zones」.)
>
> **Keep it a current-state snapshot, roughly constant size:**
> - **Link, don't restate.** Reusable findings live in the KB (`[[wiki/…]]`/`[[raw/…]]`),
>   decisions in `design.md`/ADRs — reference them with one line, don't copy their content here.
> - **Prune superseded detail.** Once an open question is resolved, keep the one-line verdict +
>   a link; move the long evidence out (KB, or `notes/`). Delete rolled-back/obsolete notes.
> - Long scratch / blow-by-blow → `notes/` (resume reads it only if needed), not here.
> - What resume actually needs: **State at a glance + Task status**. Everything else stays terse.
> - **History / why-we-got-here → `log.md`** (append-only). This file is the *snapshot*; the log is the *story*.

## State at a glance

- **Phase:** 需求 / 设计 / 详设 / 实现 / 测试
- **Test mode:** TDD / test-after  (set at 实现 start, by project test-execution policy)
- **Now doing:** …  (mid-grill: name the open question, e.g. "grilling design @ G7" — see `grill.md`)
- **Next step:** …
- **Blockers:** …

## Task status

<!-- 设计被拆分时（design.md「Decomposition/Parts」），给本表**加一列 `Part`**，让多 part 半途 resume
     看得见每个 part 的进度 / 哪条 seam 已联调。**未拆分用下面的默认两列，不加 Part 列**（不给常见情形加税）。 -->

| Task | Status | Notes |
|------|--------|-------|
| 1 | todo / doing / done / blocked | … (a task is `done` only when its acceptance is all `[x]`; an `[!]` failing criterion keeps it `doing`) |

## Changed files

- `path/...` — what & why.

## Design iterations

Dated notes on how understanding/design evolved (and any change-management pivots).

## Discovered issues

Things found mid-execution (spawn new requirements or KB notes as appropriate).
