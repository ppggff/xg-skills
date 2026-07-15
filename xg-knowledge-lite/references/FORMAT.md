# Raw Article Format

This governs how a single **raw** article is written (`$KB/raw/<project>/<slug>.md`) — Claude's investigation write-ups, the source of truth. Architecture and workflow are in this skill's `SKILL.md`; concept articles (the wiki layer) follow `concept-template.md`.

On init this file is copied to `$KB/FORMAT.md` (default `~/knowledge/FORMAT.md`; root configurable via `~/.config/xg-knowledge-wiki/config.yaml` `root:`). Article prose may be written in any language; this spec is about structure, not wording.

## 1. Required structure

Minimal skeleton shared by every raw article:

```markdown
---
title: concise title
project: cbdb           # or common; must equal the parent directory name
updated: 2026-05-25     # date the content actually changed
aliases: [short-alias-1, short-alias-2]   # optional; also matched on wikilink resolution
---

# {Title}

A one-sentence-to-one-paragraph overview: what this covers, why it matters, what
the reader walks away with. **At most 3 sentences** — used for search / overview.

## {body sections} ...
```

Fields:

- `title` — required; used for the `wiki/index.md` row of the concept(s) synthesized from this raw.
- `project` — required; the parent directory name (e.g. `cbdb`, `common`); Lint checks it matches the directory.
- `updated` — required; the date the content actually changed, **not** the file mtime. Compile diffs this against concepts to decide what to re-synthesize.
- `aliases` — optional; alternative slugs matched on link resolution (e.g. an alias `vacuum` lets `[[raw/cbdb/vacuum]]` resolve to `raw/cbdb/vacuum_autovacuum_fdbobj.md`); Lint checks aliases don't collide across files.
- `compiled_to` — optional, **Compile-maintained** (don't hand-write on first save): the concept(s) synthesized from this raw, e.g. `compiled_to: [[wiki/cbdb/fdbobj-vacuum]]` (comma-separated if several). Compile back-annotates it (SKILL.md Compile step 5); `kb-backlog.py` and Lint treat a raw without it (and without a concept Sources citation) as uncompiled backlog. To defer compiling on purpose, write `compiled_to: deferred — <why>` — that marks an explicit deferral instead of a gap.

The overview sits after `# Title` and before the first `##`.

## 2. Article archetypes

Pick an archetype by knowledge type — **not mandatory**; the structure is there to help you think and to make synthesis into concepts easier.

### A. Module overview

For: how a module works, its components, the big picture.

```markdown
# {Module}

One-sentence positioning (what this is).

## Problem it solves
Why it exists, the core need it addresses.

## Key concepts
Term-style or short-sentence definitions; bold a term on first mention.

## Components / data structures
Constituent parts, key types.

## Main flow (high level)
The normal path, no deep detail (leave detail to a Flow article).

## Boundaries & limits
What's out of scope, known constraints.

## Relationship to related modules
Cross-module collaboration, comparison with similar modules.
```

### B. Flow / trace

For: the full execution path of one operation, call-chain analysis.

```markdown
# Execution path of {Operation}

## One-line summary
The key observation — the single most informative sentence.

## Trigger
What SQL / API / event starts this path.

## Call chain
In order: each step's `func()` + `file` + what that step does.

## Key data structures
Structs / state objects passed along the path.

## Differences from related flows
A table: this flow vs similar flows.

## Known pitfalls / edge cases
Traps hit, behavior under special conditions.
```

### C. Pattern catalog

For: a set of same-shaped patterns, failure modes, or variants.

```markdown
# Common {patterns / failure modes} in {area}

## Prerequisites
Background shared by all the patterns.

## Pattern 1: {name}
**Symptom**: what's observed
**Root cause**: the underlying reason
**Fix**: how to resolve it

## Pattern 2: ...
(same shape — keeps scanning and synthesis regular)

## Diagnosis flow
How to classify a problem into one of the patterns.

## Anti-patterns
Things that look like a pattern here but shouldn't be applied.
```

Same shape per pattern is the point of this archetype — it makes scanning and retrieval regular.

### D. Invariant / constraint

For: a single invariant, constraint, or contract. Short; often a subsection of a Module overview, standalone only when referenced by several articles.

```markdown
## {Invariant name}

**Statement**: the invariant, stated precisely.

**Why**: why it must hold.

**Violation consequence**: what breaks if it's violated.

**Enforcement**: where in the code it's checked / guaranteed.

**Known bypasses**: paths that legitimately bypass it, and why they don't break it.
```

## 3. Micro-conventions

### Prose style

- Prefer lists; use bold sparingly.
- Blank line between paragraphs.
- Bold a core term `**term**` on first mention — aids scanning and retrieval.
- No exclamation marks, first-person narration, or debug-session emotion.
- No admonitions / callouts or other renderer-dependent constructs.

### Code, file, and SQL references

- Functions / types / SQL identifiers: backtick + call parens (functions) or type prefix (structs).
  - Good: `heap_prepare_freeze_tuple()`, `struct LVRelState`, `pg_class.relfrozenxid`
- File paths: backtick + repo-root-relative path.
  - Good: `cbcloud/src/backend/commands/vacuum.c`
  - Bad: `/Users/.../cbcloud/...` (absolute) / `vacuum.c` (no directory)
- Fenced code gets a language: ` ```c ` / ` ```sql ` / ` ```go ` / ` ```yaml `.
- SQL / test references: test file name + test name/number, not a line number.
  - Good: `vacuum_appserver.sql/Test 6`
  - Bad: `vacuum_appserver.sql:142`
- Avoid line numbers throughout; if a hub file or pure enumeration must keep one, write it as a `:LXXX` comment, not a path fragment.

### Links

- Wikilinks are **fully-qualified, layer-explicit paths**: `[[<layer>/<project>/<slug>]]`, where
  `<layer>` is `wiki` (a concept) or `raw` (a write-up). E.g. `[[wiki/cbdb/fdbobj-vacuum]]` (concept),
  `[[raw/common/pg_vacuum_internals]]` (raw). Mirrors the on-disk path `<layer>/<project>/<slug>.md` —
  unambiguous (no raw-vs-wiki search) and followable by path-style wikilink tools (Obsidian/Foam).
- **No** bare `[[slug]]` and **no** colon `[[wiki/<project>/<slug>]]` form — always full `layer/project/slug`.
- Display text: `see [[raw/cbdb/vacuum_internals|VACUUM internals]]`.
- Section anchors: plain markdown `[text](file.md#section)` (wikilinks don't support `#`).
- Source-code URLs and other external links: plain markdown.
- Never use relative paths like `../<other>.md`.

### Tables

- Only when the content is genuinely 2-D (attribute × item).
- Header row needs `|---|---|`; alignment markers `:---:` optional.
- Three-plus dimensions → split into sections; don't force nested tables.

## 4. Size guidance

| Lines | Guidance |
|-------|----------|
| < 50 | Probably folds into another article rather than standing alone. |
| 50–300 | Sweet spot. |
| 300–400 | Add a top-of-file anchor list; review whether it should split. |
| > 400 | Lint warns; split by sub-topic into multiple articles. |

Splitting principle: single responsibility. Module overview + Flow + Pattern catalog crammed into one file = split.

## 5. Anti-patterns

- **Pasting large source blocks** — keep the key 3–5 lines, link the rest back to `func()` in `file.c`.
- **Play-by-play narration** — "then I found… then I tried…" belongs in problem/progress; a raw article keeps stable conclusions only.
- **Transient references** — PR numbers, issue numbers, git branches — they rot.
- **Line-number references** — drift with every patch; use function names.
- **Reverse coupling** — an article linking to workflow docs (dev_root requirement dirs, or legacy `plan/` / `problem/` / `progress/`); references are one-way (workflow → KB), Lint flags the reverse.
- **Copying plan/problem content** — an article cites only "stable facts"; investigation-scene observations stay in problem.
- **Fancy markdown** — embedded HTML, emoji decoration, admonitions — they hurt portability.
- **Placeholder empty sections** — a heading with no body / `TODO` — delete it; add when needed.
- **Conflating same-named concepts** — terms that share a name across projects but mean different things get their own files (distinguished by `<project>/<slug>`), not crammed into one.

## 6. Quick checklist

Scan once after writing:

- [ ] frontmatter complete (title / project / updated; `compiled_to` is Compile's job — set it only for a deliberate `deferred — <why>`)
- [ ] overview ≤ 3 sentences
- [ ] a fitting archetype chosen (or deliberately skipped)
- [ ] core terms bolded on first mention
- [ ] source refs use function + file name, no `file:line`
- [ ] cross-references use wikilinks, not relative paths
- [ ] no links to workflow docs (dev_root requirement dirs / legacy plan/problem/progress)
- [ ] line count in 50–300, or a good reason to exceed
- [ ] no TODO empty sections, transient references, or emotive wording
