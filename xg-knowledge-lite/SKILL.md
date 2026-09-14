---
name: xg-knowledge-lite
description: "Cross-project code-knowledge base: raw investigation write-ups compiled into concept articles, per project. Use when recording a finding ('记下来' / 'capture this finding'), updating a note ('update the <X> note'), compiling the wiki ('compile'), querying knowledge ('what do I know about <X>'), orienting on a project ('orient me on <project>' / '项目知识大纲'), or linting the KB."
---

# xg-knowledge-lite

A cross-project **code-knowledge base** with two layers (the LLM writes & maintains the wiki; the
human reads & asks):

- **raw** (source of truth): `$KB/raw/<project>/*.md` + `$KB/raw/common/*.md` — Claude's
  investigation write-ups. One file = one investigation / topic, may span several concepts. Format
  per `$KB/FORMAT.md`. This is where Claude records what it learned.
- **wiki** (derived, Claude-maintained): **concepts synthesized from raw**.
  - `$KB/wiki/<project>/<concept>.md` — one **concept** article, distilled across the raw that
    covers it (format per `references/concept-template.md`). Concepts are extracted from raw, not
    written directly.
  - `$KB/wiki/index.md` — index of concept articles (one row each).
  - `$KB/wiki/log.md` — append-only operation log.

The split that matters: **raw = "what I learned in investigation X" (may mix concepts); a concept
article = "everything we know about concept Y, synthesized across investigations."** Claude writes
raw; Compile extracts/synthesizes concepts into wiki. No external-source ingestion.

This file routes. Each action's procedure is one file under `references/actions/`; the hard rules —
`$KB` / config resolution, initialization, project resolution, KB git versioning, usage logging — are
`references/constraints.md`; formats are `$KB/FORMAT.md` (raw) and `references/concept-template.md` (concept).

## Actions

Resolve `$KB` and the project first (`references/constraints.md`), then read only the action's file.

| Action | Does | Procedure |
|---|---|---|
| **Write** | record a raw write-up (or update one), then Compile scoped to the concepts it touches | `references/actions/write.md` |
| **Compile** | synthesize concept articles from raw, incrementally — scoped (from Write) or batch (bootstrap / repair drift) | `references/actions/compile.md` |
| **Query** | answer from concepts first, grep raw as fallback; read-only | `references/actions/query.md` |
| **Orient** | a project's knowledge outline for warm-up — index section · designated docs · uncompiled-raw count; read-only | `references/actions/orient.md` |
| **Lint** | eight health checks; deterministic findings auto-fixed, judgment findings report-only | `references/actions/lint.md` |

Every mutating action (Write · Compile · a Lint fix-pass) ends with a KB commit and one usage record
(`references/constraints.md`「Versioning」·「Usage logging」).

## Designated docs (the map, the rules, the glossary)

Three **curated project-global docs** in `wiki/<project>/` (or `wiki/common/`), created **lazily** and
**directly maintained** — not synthesized from raw, so they sit outside the recompute model and carry no
concept index row (Lint §5 / §7 check them; §2 excludes them from the index check). Orient surfaces them
first; Query reaches them through Orient, not the concept index.

- **`architecture.md`** — the system's **overall design** (layers, modules, responsibilities, seams, key
  data flows): the big-picture **map** that `See Also`s the detail concepts; evidence-cited. xg-dev-workflow's
  understanding statement (`steps/discuss.md`) links each card's `design.md` to `[[wiki/<project>/architecture]]`
  and refreshes it **as-built** at the card's close-out (存量 five-phase cards: when a design freezes).
- **`<subsystem>-invariants.md`** — one **evidence-cited** line per established system invariant: the
  ledger xg-dev-workflow's lenses (`references/lenses.md`; 存量 cards: the legacy adversarial-critic) **load & replay**.
  Append to it whenever an investigation establishes a durable invariant — that is how the next design's
  starting point gets sharper.
- **`CONTEXT-MAP.md`** — carves the project (or `common`) into **bounded contexts** that scope
  terminology, so a word can mean different things in different contexts without conflict (format:
  `references/context-map-template.md`); created when the first scoped term needs a home, kept current by
  Compile (`compile.md` step 4b).

## Conventions

- raw article format: `$KB/FORMAT.md`. concept article format: `references/concept-template.md`.
- Cross-references: **fully-qualified** `[[<layer>/<project>/<slug>]]` wikilinks — full syntax
  (forbidden bare / colon / relative forms, display text, section anchors) in `$KB/FORMAT.md` §3.
- **Link direction = dependency direction.** The load-bearing link is **concept→raw** (Sources) — it
  drives recompile. `raw→raw` and `concept↔concept` (See Also) are navigation. A `raw→concept` link
  is allowed but **navigation only — raw must never *depend on* a concept** (the model's invariant
  is "wiki is recomputable from raw"; if a concept vanished, raw must still stand). Keep
  dependencies pointing source→… never derived→source.
- Today's date for `updated` and log entries.
- **Writing conventions: `references/conventions-core.md`** (shared core, byte-identical with
  xg-dev-workflow's copy — style/structure, short lines, first-use gloss, provenance marking,
  Mermaid preference; `references/diagram-gotchas.md` ships alongside). Applies to KB articles
  and this skill's own files alike; KB-specific rules (fully-qualified wikilinks etc.) stay in
  `$KB/FORMAT.md`.

## Out of scope (deliberately)

graph, changes-timeline, compile-stamp / hash-based drift tracking, similarity-probe,
probe/graph-driven or multi-round cascade (Compile does a light same-project ripple only,
Karpathy-style), external-source (web/Notion) ingestion, slash commands, archive pages
(karpathy-style `[Archived]` snapshots of Query answers — durable content routes into raw via Write
instead; see Query). If you outgrow this, that's the full `xg-knowledge-wiki`.

## References

- `references/actions/{write,compile,query,orient,lint}.md` — one file per action (`lint.md` carries the §1–§8
  checklist, authority split and execution notes; its section numbers are cited from elsewhere — keep them stable).
- `references/constraints.md` — `$KB` / config resolution · initialization set · project resolution · KB git
  versioning · usage logging.
- `references/FORMAT.md` — raw article format (copied to `$KB/FORMAT.md` on init, **together with
  `references/raw-archetypes.md` → `$KB/raw-archetypes.md`** — FORMAT.md §2 points at it, so the pair travels
  together; both `$KB` copies are drift-checked by xg-dev-workflow's `tools/check-sync.py`, report-only).
- `references/concept-template.md` — wiki concept article format (canonical term / `_Avoid_` / `_Context_` /
  Sources / See Also).
- `references/context-map-template.md` — `wiki/<project|common>/CONTEXT-MAP.md`: bounded contexts + scoped glossary.
- `references/index-template.md` — `wiki/index.md` layout.
- `references/conventions-core.md` · `diagram-gotchas.md` · `ask-routing-core.md` — synced pairs with
  xg-dev-workflow (byte-identical; `tools/sync-manifest.txt` there).
- `tools/resolve-project.py`, `tools/register-project.py` — cwd → project mapping.
- `tools/kb-backlog.py` — per-project uncompiled-raw backlog (SessionStart-hook friendly; quiet when clean,
  always exit 0).
