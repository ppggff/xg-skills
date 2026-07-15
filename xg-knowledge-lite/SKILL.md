---
name: xg-knowledge-lite
description: "Cross-project code-knowledge base: raw investigation write-ups compiled into concept articles (Karpathy two-layer), per project. Use when recording a finding ('capture this finding' / '记下来' / '沉淀知识'), updating a note ('update the <X> note'), compiling the wiki ('compile'), querying knowledge ('what do I know about <X>'), orienting on a project ('orient me on <project>' / '项目知识大纲'), or linting the KB."
---

# xg-knowledge-lite

A cross-project **code-knowledge base** with two layers, adapted from the Karpathy LLM-wiki (the LLM writes & maintains the wiki; the human reads & asks):

- **raw** (source of truth): `$KB/raw/<project>/*.md` + `$KB/raw/common/*.md` — Claude's investigation write-ups. One file = one investigation / topic, may span several concepts. Format per `$KB/FORMAT.md`. This is where Claude records what it learned.
- **wiki** (derived, Claude-maintained): **concepts synthesized from raw**.
  - `$KB/wiki/<project>/<concept>.md` — one **concept** article, distilled across the raw that covers it (format per `references/concept-template.md`). Concepts are extracted from raw, not written directly.
  - `$KB/wiki/index.md` — index of concept articles (one row each).
  - `$KB/wiki/log.md` — append-only operation log.

The split that matters: **raw = "what I learned in investigation X" (may mix concepts); a concept article = "everything we know about concept Y, synthesized across investigations."** Claude writes raw; Compile extracts/synthesizes concepts into wiki.

`$KB` resolution: (1) `--root <path>`; (2) `~/.config/xg-knowledge-wiki/config.yaml` `root:`; (3) default `~/knowledge`. Never auto-create the config.

## Actions

Write (record raw + refresh its concepts), Compile (synthesize concepts from raw, incrementally), Query (search), Orient (project knowledge outline / warm-up), Lint (check). No external-source ingestion. Compilation is **incremental, Karpathy-style** — no full rebuild, no hash stamp.

## Initialization (on first Write)

Create only what's missing; never overwrite: `$KB/raw/`, `$KB/raw/common/`, `$KB/wiki/`, `$KB/wiki/index.md` (`# Knowledge Index`), `$KB/wiki/log.md` (`# Knowledge Log`), and `$KB/FORMAT.md` (copy from `references/FORMAT.md`). On read (Query/Lint) with nothing there, tell the user to Write first; don't auto-create.

A **`$KB/wiki/<project>/CONTEXT-MAP.md`** (or `$KB/wiki/common/CONTEXT-MAP.md`) is created **lazily** — only when the first scoped/bounded-context term needs a home (format: `references/context-map-template.md`). It carves a project/common into **bounded contexts** that scope terminology, so a word can mean different things in different contexts without conflict.

## Designated docs (the map + the rules)

Two **curated project-global docs** — siblings of `CONTEXT-MAP.md`: **directly maintained**
(evidence-cited), **not** synthesized-from-raw concepts, so they sit **outside the recompute model**
(like CONTEXT-MAP). Created **lazily** when first needed, surfaced first by Orient, checked by Lint:

- **architecture** — `wiki/<project>/architecture.md`: the system's **overall design** (layers, modules, responsibilities, seams, key data flows) — the big-picture **map** that `See Also`s the detail concepts. xg-dev-workflow's design step links each card's `design.md` to it (`[[wiki/<project>/architecture]]`) and refreshes it **as-built** when a design freezes.
- **invariant ledgers** — `wiki/<project>/<subsystem>-invariants.md`: one line per established system invariant, **evidence-cited** — the ledger xg-dev-workflow's adversarial-critic **loads & replays**. Append to it whenever an investigation establishes a durable invariant; that is how the next design's starting point gets sharper.

They live in `wiki/<project>/` beside the concepts but are **hand-maintained docs, not concept index rows** — Query reaches them via Orient, not the concept index (Lint excludes them from the index check, see Lint §2).

## Project resolution

When a write needs a `project` and none is given: `--project <name>` → use it; else `tools/resolve-project.py [<cwd>]` (config `projects:` map, longest-prefix); on miss → ask once + `tools/register-project.py`. **Never auto-pick `common`.**

## Write — record raw, then refresh its concepts

The entry point for recording raw. Raw is Claude-authored: distill stable conclusions from investigation, never transcribe the play-by-play.

### A. Record raw

1. Resolve project. Pick a slug for the write-up (kebab-case, ≤ 60 chars — named after the investigation / topic). If that slug already exists in the project and this is genuinely new content, append a numeric suffix (`-2`) or pick a distinct name — never silently overwrite an existing raw file (to revise it, use Update mode instead).
2. Write `$KB/raw/<project>/<slug>.md` per `$KB/FORMAT.md` (frontmatter `title`/`project`/`updated`; archetype body; `func()` in `file.c` not `file.c:NNN`; `[[..]]` wikilinks; no links to workflow docs — dev_root requirement dirs or legacy `plan/`/`problem/`/`progress/`; references are one-way: workflow → KB). A raw file may legitimately cover several concepts.
3. **Update mode**: to revise existing raw, locate the raw file (slug / context / grep), edit in place, bump `updated`. Contradictions → don't silently overwrite; quote both / ask.

### B. Refresh affected concepts

4. Identify the distinct concept(s) this raw touches (a raw file may cover several).
5. **Run Compile scoped to those concepts** (see Compile below). It synthesizes/updates each concept article, cascades to materially-affected neighbors, back-annotates `compiled_to:` in the raw, and refreshes index + log.

(One investigation may legitimately produce/refresh several concept articles — split by concept.)

## Compile — synthesize concepts from raw (incremental)

The single routine that turns raw into concept articles — **one concept per `wiki/<project>/<concept>.md`**. Called two ways, same procedure, only the work set differs:

- **Scoped** — from Write §B: just the concept(s) the freshly written/updated raw touches.
- **Batch** — standalone: bootstrap concepts from an existing pile of raw (e.g. migrated raw articles), or repair drift after raw changed out-of-band.

Karpathy-style incremental: **no full rebuild, no hash stamp** — only the concepts in the work set are (re)synthesized.

1. Resolve `$KB`; ensure `wiki/` + `wiki/index.md` exist.
2. **Determine the work set:**
   - *Scoped:* the concept(s) the triggering raw covers — same concept exists → update; new concept → create, named after the concept.
   - *Batch:* raw with **no** concept citing it yet → new concepts; raw whose `updated` is newer than the concepts citing it → re-synthesize; concepts whose **all** Sources raw no longer exist → stale, mark `[MISSING]` / remove; everything else → untouched.
3. **Synthesize each concept** in the work set into `wiki/<project>/<concept>.md` (per `references/concept-template.md`) from **all** raw that covers it (not just one write-up): overview + body + a **Sources** list linking that raw (`[[raw/<project>/<slug>]]`) + See Also. Synthesize, don't copy; contradictions across raw → annotate with attribution, never silently pick.
   - **Placement of a cross-cutting concept:** if a concept is relevant to several projects, put it under `common/` (or the single most relevant project) and `See Also` the project-specific concepts that touch it — don't duplicate it per project.
4. **Cascade Updates** (ripple to neighbors): after the work-set concepts, scan **same-project** concept articles (and `wiki/index.md`) for any whose content is **materially affected** by the changed raw — it cites the same raw, or states something the new raw supersedes. Re-synthesize those too and bump their `updated`. Keep it light: same-project + materially-affected only; no probe/graph, no multi-round chasing.
   - **Cross-article conflict:** when the contradiction is between two *separate* concept articles (not within one concept's raw), do not silently reconcile — annotate **both** with source attribution and cross-link them via `See Also`.
4b. **Glossary upkeep** — when a synthesized concept pins/changes a canonical term (`_Avoid_`/`_Context_`), reflect it in the project/common `CONTEXT-MAP.md` (create lazily): add the term under its context's Language section and the concept under that context's "Governs". A new bounded context → a new section + its relationships. Flag any within-context term collision.
5. **Back-annotate & refresh** — set `compiled_to:` in each source raw's frontmatter to the concept(s) synthesized from it (`compiled_to: [[wiki/<project>/<concept>]]`, comma-separated if several) — this is what keeps `kb-backlog.py`'s signal reliable; then refresh the `wiki/index.md` row for every touched concept (and, when a project section is new or its scope shifted, its one-line project description); append one line to `wiki/log.md`:
   - scoped: `## [YYYY-MM-DD] write | raw <project>/<slug> → concept(s) <project>/<concept>[, …]`
   - batch: `## [YYYY-MM-DD] compile | +<new> ~<resynth> -<removed> concepts`
6. (Batch) suggest Lint afterward.

"What changed" is computed by comparing raw `updated` to the concepts that cite them — no stamp file, only the delta is rebuilt.

## Query — search the knowledge

1. **Concepts first** (primary): read `wiki/index.md` → read the relevant `wiki/<project>/<concept>.md`. Synthesize an answer with `[[wiki/<project>/<concept>]]` citations; drill into a concept's **Sources** raw for detail. Prefer KB knowledge over training knowledge for repo facts.
2. **Grep fallback**: if concepts surface too little — or `wiki/` isn't built yet — grep the **raw** directly:
   ```bash
   rg -i "<query>" "$KB"/raw/*/*.md      # ripgrep; fallback: grep -ri ... --include='*.md'
   ```
   Report `<project>/<slug> @ line` + snippet. Catches raw recorded but not yet compiled into a concept.
   **Backlog visibility:** `tools/kb-backlog.py` lists per-project uncompiled raw (SessionStart-hook
   friendly; wiring example in README). Its reliability contract: Compile step 5 owns the
   `compiled_to:` back-annotation; Lint §1 owns the check (incl. the `deferred — <why>` marker).
3. Contradictory hits → flag to the user.

Don't write files during Query unless asked to save the answer (then Write).

## Orient — warm up on a project's knowledge (read-only outline)

Query is **pull** (you already have a question); Orient is **push** — it surfaces *what is even knowable* about a project up front, so investigation starts knowing which concepts exist and reuses them instead of re-deriving. The outline already exists as `wiki/index.md` + the project's `CONTEXT-MAP.md`; Orient **reads and presents** them scoped to one project — it never regenerates or caches an outline file (that would drift from the index — see Out of scope).

**When:** on demand (`orient me on <project>`, `项目知识大纲`, `warm up the KB`); and as the project-scoped front of an investigation / review / new requirement (xg-dev-workflow calls it as its "KB first" step). Auto-warm-up inside a dev-workflow run is covered by that run — don't double-log.

1. **Resolve project** — `--project <name>` → use it; else `tools/resolve-project.py [<cwd>]`. On miss, say so and offer to register; never default to `common`. Always pull `common` alongside the resolved project.
2. **Read the outline** — `wiki/index.md`, the resolved project's section + `common`: the one-line project description + every concept row (title + summary). This *is* the outline — don't open concept bodies here (that's Query, once a topic is picked).
3. **Read the project-global docs** (`wiki/<project>/`, and `common`'s, if present): the **`CONTEXT-MAP.md`** glossary (bounded contexts + canonical terms — names to use, `_Avoid_` terms), the **`architecture`** overview (the map), and any **`*-invariants`** ledgers (the rules). **Lead with the map + the rules** — the concepts hang off them.
4. **Flag uncompiled raw** — list count + slugs so the reader knows there's detail below the outline (`tools/kb-backlog.py` computes exactly this).
5. **Present compactly** — project one-liner → concepts (title + summary) → bounded contexts + key terms → "N uncompiled raw" note. Nothing for the project → say so, suggest a first Write. Don't write files.

## Lint — minimal health check

1. **Coverage** — every `raw/<project>/*.md` is cited by at least one concept's Sources **or carries `compiled_to:` frontmatter** (else it's uncompiled → suggest Compile; `compiled_to: deferred — <why>` is an explicit deferral, not a gap). A Sources-cited raw missing its `compiled_to:` back-annotation → add it; a `compiled_to:` pointing at a non-existent concept → dangling. Every concept's Sources point to existing raw. Also flag **concept-promotion**: an idea recurring across several raw files (or repeatedly mentioned inside concepts) with no dedicated concept article → suggest extracting one.
2. **Index consistency** — every `wiki/<project>/*.md` **concept** has an index row; every row points to an existing concept. (Exclude the **curated docs** — `CONTEXT-MAP.md`, `architecture.md`, `*-invariants.md` — they're not concepts and carry no index row; they're checked in §7.) Report drift → suggest Compile.
3. **Dangling wikilinks** — every `[[<layer>/<project>/<slug>]]` resolves to an existing file `<layer>/<project>/<slug>.md` (`<layer>`∈`wiki`/`raw`). Flag any legacy `[[project:slug]]` / bare `[[slug]]` → migrate to the full path form.
4. **Frontmatter** — raw + concept articles have `title` / `project` / `updated`; `project` matches parent dir; `aliases` don't collide across files (within a layer+project).
5. **Terminology / contexts** — each concept with a glossary entry has **one** canonical term + `_Avoid_`, defined by what it IS (not what it does); within a bounded context (a `CONTEXT-MAP.md` heading) no two concepts claim the same term and no word carries two meanings; the **same word across different contexts is fine** (scoped homonym) — verify each is scoped. Every concept's `_Context_` resolves to a context in the project/common CONTEXT-MAP; every context "Governs" existing concepts. **CONTEXT-MAP purity** — it holds only terms / scopes / relationships, no implementation details or design decisions (those belong in workflow `design.md`/ADRs). Drift → fix the term, record the scope, or move out non-glossary content.
6. **Size** — flag raw articles > 400 lines (FORMAT.md size guidance: split by sub-topic).
7. **Designated docs** — a project with several concepts but **no `architecture` overview** →
   suggest creating one (it's the entry map). Every line in a `*-invariants` ledger is
   **evidence-cited** (`func()` in `file.c` or a raw link); a subsystem with concepts but no
   invariant ledger is a **soft** flag (best-effort, don't force one where there are no invariants).

Execution (cost): §2 / §3 / §4 / §6 are deterministic — script them when tooling exists; run
the rest (and any unscripted deterministic item) via one cheaper-model agent (Agent tool
`model: sonnet`) that returns only the violation list — the orchestrator fixes what's flagged,
re-verifying each finding. (Same principle as xg-dev-workflow's「Subagent model assignment」;
restated here so this skill stays self-contained.)

Append `## [YYYY-MM-DD] lint | <N> issues, <M> fixed` to `wiki/log.md`.

## Versioning the KB (git)

`$KB` is its **own git repo** (separate from `dev_root` and the product-code repo). **Lazily initialized** on the first commit (`git init` + a minimal `.gitignore`, announced once).

- **Commit after each mutation** (semantic boundary, mirroring `wiki/log.md`): after a **Write** (raw + its scoped Compile), a **Compile** batch, or a **Lint** fix-pass. Message mirrors the log line — `<project>: write <slug> → concept(s) …` / `compile +N ~M -K` / `lint N issues, M fixed`.
- **Autonomous local commit**; **`push` stays human-gated**; history append-only (no amend/rebase).
- A KB write done **inside** an xg-dev-workflow `investigate`/`review` run commits there (one event → one KB-repo commit) — don't double-commit.
- Optional: a session-end hook (shipped with xg-dev-workflow's `tools/commit-data-repos.py`) commits both data repos as a safety net.

## Conventions

- raw article format: `$KB/FORMAT.md`. concept article format: `references/concept-template.md`.
- Cross-references: **fully-qualified** `[[<layer>/<project>/<slug>]]` wikilinks (`<layer>`∈`wiki`/`raw`) — e.g. `[[wiki/cbdb/fdbobj-vacuum]]`, `[[raw/cbdb/vacuum_internals]]`. (No legacy `[[project:slug]]` / bare `[[slug]]`.)
- **Link direction = dependency direction.** The load-bearing link is **concept→raw** (Sources) — it drives recompile. `raw→raw` and `concept↔concept` (See Also) are navigation. A `raw→concept` link is allowed but **navigation only — raw must never *depend on* a concept** (the model's invariant is "wiki is recomputable from raw"; if a concept vanished, raw must still stand). Keep dependencies pointing source→… never derived→source.
- Today's date for `updated` and log entries.
- **Writing style: lean plain, keep technical terms** — prefer everyday phrasing where it doesn't lose precision, but don't force-replace established technical terms (不变量/契约/幂等…) with folksy paraphrases. Clear-but-professional, not dumbed-down. Short sentences.

## Usage logging (self-feedback)

Logging rule lives in `~/.claude/CLAUDE.md` (Skill Usage Logging) — follow it. This skill's `--action` values: `write|compile|query|orient|lint` (the logging tool warns on anything else). **One event = one record:** a KB write — *or an Orient warm-up* — that happens inside an xg-dev-workflow `investigate`/`review` run is covered by that run's record; don't double-log here. Only standalone KB work logs under this skill (`orient` only when run as a deliberate standalone warm-up).

## Out of scope (deliberately)

graph, changes-timeline, compile-stamp / hash-based drift tracking (Compile diffs raw `updated` vs concepts — no hashing), similarity-probe, probe/graph-driven or multi-round cascade (Compile does a light same-project ripple only, Karpathy-style), external-source (web/Notion) ingestion, slash commands. If you outgrow this, that's the full `xg-knowledge-wiki`.

## References

- `references/FORMAT.md` — raw article format (copied to `$KB/FORMAT.md` on init).
- `references/concept-template.md` — wiki concept article format (canonical term / `_Avoid_` / `_Context_` / Sources / See Also).
- `references/context-map-template.md` — `wiki/<project|common>/CONTEXT-MAP.md`: bounded contexts + scoped glossary.
- `references/index-template.md` — `wiki/index.md` layout.
- `tools/resolve-project.py`, `tools/register-project.py` — cwd → project mapping.
- `tools/kb-backlog.py` — per-project uncompiled-raw backlog (SessionStart-hook friendly; quiet when clean, always exit 0).
