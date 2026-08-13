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

**Optional archetypes** (module-overview / flow / … structures for a raw note) → see `references/raw-archetypes.md`. Not mandatory; a raw note follows §1's frontmatter + §3's conventions regardless.

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

Only the ones §3's conventions don't already cover — line numbers, code/file refs, relative-path
links, and renderer-dependent markdown are all handled in §3:

- **Pasting large source blocks** — keep the key 3–5 lines, link the rest back to `func()` in `file.c`.
- **Play-by-play narration** — "then I found… then I tried…" belongs in problem/progress; a raw article keeps stable conclusions only.
- **Transient references** — PR numbers, issue numbers, git branches — they rot.
- **Reverse coupling** — an article linking to workflow docs (dev_root requirement dirs, or legacy `plan/` / `problem/` / `progress/`); references are one-way (workflow → KB), Lint flags the reverse.
  **Named exception — a project whose documented subject *is* the workflow itself** (currently `xg-skills`): its cards are that project's own development record, not an external private store, so card-scoped provenance tags (`(017 D2)`, `(013 ADR-0001、R3)`) may stay inline. The exception covers **provenance tags only** — still no dev_root file paths, and `dev_root` appearing as a domain term (or a skill-repo source path like `xg-dev-workflow/tools/viewer.py`) was never a violation to begin with. Any other project claiming this exception has to be added here first.
- **Copying plan/problem content** — an article cites only "stable facts"; investigation-scene observations stay in problem.
- **Placeholder empty sections** — a heading with no body / `TODO` — delete it; add when needed.
- **Conflating same-named concepts** — terms that share a name across projects but mean different things get their own files (distinguished by `<project>/<slug>`), not crammed into one.

## 6. Quick checklist

Scan once after writing — no new rules, just the earlier sections applied in order:

- [ ] frontmatter + overview per §1 (`compiled_to` is Compile's job; hand-set only for a deliberate `deferred — <why>`)
- [ ] an archetype chosen, or deliberately skipped (§2)
- [ ] prose / code-ref / link conventions per §3
- [ ] size within §4 guidance
- [ ] none of the §5 anti-patterns present
