---
id: NNN
title: <plan title>
project: <project>
design: ./design.md
status: draft | active | done | superseded
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# 实现 NNN: <plan title>

> **Reader: Claude-first** (execution zone — Claude executes this autonomously, no per-task gate;
> the human approved the *design*, not this breakdown). Write it terse & structured for execution +
> resume, not as a human read-through; it's the autonomy handoff. (SKILL.md「Two zones」.)
>
> This plan implements the FROZEN design (+ `detail.md` if present) and is **mutable** —
> refine it freely as reality bites. Tasks **reference** `detail.md` for structure/algorithm
> rather than redefining it. If you find the *design* is wrong, stop and run
> change-management (M2); do not silently diverge from `design.md`.
>
> **Refining a task is silent; deleting / merging / deferring a task — or invalidating an
> already-`[x]` acceptance — gets a one-line `log.md` `[实现]` entry (what + why)**, so a dropped
> task leaves a trail (was-it-done? why-gone?) instead of vanishing (M2 case B).

## Overview (optional — a one-paragraph orientation; skip when the design 思路 suffices)

One paragraph: what this plan builds, against which design.

## Task list (vertical slices, dependency-ordered)

<!-- If the design is split into parts (design.md「Decomposition/Parts」), tag each task with
     its `Part:`; cross-part tasks list the **seam** under Dependencies. Omit `Part:` when un-split. -->

### T1: <title>
- **Description:** what this slice accomplishes.
- **Implements:** [R1](./requirement.md), [R2](./requirement.md) — the「需求条目」this slice delivers (— if purely scaffolding). Cross-file ids link to their home (SKILL.md「Conventions」Links).
- **Part:** <part name> | —   (optional; only when the design is split into parts)
- **Acceptance:** (binary walk — `[x]` only when its verification test passes; `[!]` if it
  failed; `[ ]` unverified. No subjective `[x]`.)
  - [ ] <testable condition>
    e.g. ✅「`--check` 对含悬空 depends-on 的 fixture 卡 exit 1 且指名坏行」（可跑、可判）；
    ❌「账本检查工作正常」（主观形容，binary walk 无从打钩）。（示意）
- **Verification:** test / build / manual check (e.g. cbdb: describe, do not run, unless asked).
- **Dependencies:** None | T<n>
- **Files likely touched:** `path/...`
- **Scope:** XS | S | M | L  (L → break down further)

### Checkpoint: after T1–T<n>
- [ ] builds / tests green; system works end-to-end so far.

### Final: simplify sweep (after the last task — M+; XS/S may skip)
- [ ] one behavior-preserving pass over the whole change (`implement.md`「Simplify sweep」);
      suite re-run green; separate commit; run/skip recorded in `progress.md` `Close-out:`.

## Risks & mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| … | H/M/L | … |

## Open questions (optional — free list)

- …
