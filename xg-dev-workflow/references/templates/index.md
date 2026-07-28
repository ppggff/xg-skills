<!--
Two uses of this template:

1. <dev_root>/index.md — cross-project index. One row per project pointing at its
   own index.md. (Unchanged; no per-card status here — a project rollup view is Future.)

2. <dev_root>/<project>/index.md — per-project KANBAN board. One row per **card**
   (a card = one full requirement lifecycle = one NNN-slug/ directory). Kept current by
   the omission check (M3).

Reader = both: the human sets 整体状态 (the scheduling axis); Claude updates Phase/Deps on
`new`/M3 transitions. `resume` doesn't use the board as a state source (it may read it to locate the card;
state rebuilds from the card's own docs).
-->

# Dev Workflow Index — <project or "all projects">

<!-- ============ Use 1: cross-project board (dev_root/index.md) ============ -->
## Projects   <!-- cross-project index only -->

| Project | Index |
|---------|-------|
| <name> | [<name>/index.md](./<name>/index.md) |

<!-- ============ Use 2: per-project kanban (dev_root/<project>/index.md) ============ -->
## Cards (kanban)

| Card | Phase | 整体状态 | Deps | Dir |
|------|-------|----------|------|-----|
| 001 | 需求/设计/实现/测试 | todo | — | [001-slug](./001-slug/) |

<!--
Card = one full lifecycle unit (需求→…→测试) living in one NNN-slug/ dir. It is the kanban
ALIAS of the "requirement directory"; the rest of the skill still says "requirement" for this
unit (scoped homonym — not drift). "Split a requirement" = spawn multiple cards (run `new`
again) — see SKILL.md「拆分与隔离」.

Columns:
- Phase    = furthest phase reached, a CARD-LEVEL summary: 需求/设计/实现/测试.
- 整体状态 = the card's OVERALL scheduling state — a human-set axis, SEPARATE from the internal
   per-phase status VALUES (design:frozen / plan:active / progress:blocked …), which stay in the
   phase docs and do NOT appear on the board:
     backlog  尚未启动 · todo 已排期待办(new 默认) · active 正在做 ·
     blocked  被某未 done 的 Dep card 被动挡住 · paused 人主动降优挂起 ·
     done     完成 · dropped 放弃/废弃
- Deps     = same-project card NNN this card depends on (space/comma separated; "—" = none).
   M3 checks the card graph is acyclic. Cross-project deps are out of scope.
- Dir      = link to the card directory.

整体状态 vs internal progress is LOOSELY coupled (not fully orthogonal): free EXCEPT the monotonic
constraints M3 enforces (done / backlog / paused-blocked preconditions) — the authoritative list
is in omission-check.md「Board (kanban) consistency」.

Backward compat: existing rows stay valid. Migrating an old per-phase `Status` column to 整体状态
is a ONE-TIME, HUMAN-REVIEWED pass (the axes differ): suggested drafting→todo, active→active,
done→done, superseded→dropped — confirmed row by row, not auto-mapped.

Add a row on `new` (初始 整体状态 = todo); update Phase / 整体状态 / Deps on every transition.
-->
