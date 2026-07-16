<!--
<dev_root>/<project>/roadmap.md — the project's persisted, card-transcending plan: a savable
todo / someday list that outlives any single card, so deferred work isn't forgotten. Lighter than
the index.md kanban (which tracks in-flight cards); a roadmap item graduates into a card via
`new <slug>` (then link it). Kept fed by: cards' Future / Discovered-issues append here; M3 checks
deferred work landed here; retro scans it. This is a dev_root planning doc — system *knowledge*
(architecture, invariants) lives in the KB, not here.

Reader = human (planning): scanned when deciding what's next — one line per item, prunable.
-->

# Roadmap — <project>

## Next up (ordered)

Intended next cards, roughly ordered. An item graduates to a card with `new <slug>` — then move it
to "Graduated" with the NNN.

- [ ] <one-line intent> — why / source (card NNN Future · a discovered issue). → card: —

## Themes / direction

Bigger arcs the project is moving toward (each spawns several cards over time).

- <theme> — one line.

## Someday / maybe

Uncommitted ideas; no card yet. Prune when dropped (note why).

- <idea> — one line.

## Rejected / won't do

Proposals consciously rejected at requirement level, so they don't return unnoticed — the
requirement step checks here before drafting (design-level rejections live in ADRs instead).

- <proposal> — why rejected (YYYY-MM-DD).

## Graduated / shipped (recent tail)

Items that became cards or shipped — keep a short tail for memory, prune the old.

- <item> → card NNN (YYYY-MM-DD).
