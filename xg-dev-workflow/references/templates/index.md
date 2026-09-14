<!-- Two uses: <dev_root>/index.md (cross-project index — one row per project) and
<dev_root>/<project>/index.md (the per-project board — one row per card = one NNN-slug/ dir).
The human sets 整体状态 (the scheduling axis); Claude writes the row at `new` and updates it at go and
close-out (constraints.md Lay-4: lite rows use todo · active · done · dropped, following design.md `status`;
dropped is row-only). `resume` may read the board to locate a card, never as a state source.
存量 rows keep the five-phase Phase words and the wider 整体状态 set (references/legacy/SKILL.md「Layout」). -->

# Dev Workflow Index — <project or "all projects">

## Projects   <!-- cross-project index only -->

| Project | Index |
|---------|-------|
| <name> | [<name>/index.md](./<name>/index.md) |

## Cards (kanban)   <!-- per-project board -->

| Card | Phase | 整体状态 | Deps | Dir |
|------|-------|----------|------|-----|
| 001 | lite | todo | — | [001-slug](./001-slug/) |

<!-- Deps = same-project card NNN this card depends on (space / comma separated; "—" = none); the board
check keeps the graph acyclic. Optional section below the table:「参考对象注记」— one pointer line per card
group that became a reference object after a redo-triggered learn adoption (steps/learn.md backfill). List
lines only, never a `| NNN |`-shaped row: the board scans the whole file for such rows. -->
