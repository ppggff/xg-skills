# Concept article format (wiki layer)

A concept article lives at `$KB/wiki/<project>/<concept>.md`. It is **synthesized from raw** — distilled, deduplicated knowledge about one concept, drawn across the raw write-ups that touch it. Claude maintains it; humans read it. Do not hand-author concepts; record raw and compile.

## Structure

```markdown
---
title: <concept name>
project: <project or common>   # = parent dir under wiki/
updated: <YYYY-MM-DD>          # when the concept's synthesized content last changed
---

# {Concept}

**规范术语 (canonical term)**: {the one preferred name for this concept}
_Avoid_: {synonyms / near-misses that should NOT be used for it}
_Context_: {the bounded context this concept's terms belong to — a heading in the project/common
`CONTEXT-MAP.md`; omit if the project has no CONTEXT-MAP yet}

One-paragraph (≤ 3 sentence) synthesis: what this concept is, why it matters.

## {Body sections}

Synthesized, reorganized knowledge — not a copy of any single raw file. Distill
and dedupe across sources. Use the same prose / code-reference conventions as
raw articles (`func()` in `file.c`, no `file.c:NNN`; `[[..]]` wikilinks).

## Sources

The raw write-ups this concept is synthesized from (drives incremental Compile —
when one of these raw files changes, this concept is re-synthesized):

- [[raw/<project>/<slug>]]
- [[raw/<project>/<slug-2>]]

## See Also

Related concept articles (cross-links maintained by Compile / Lint):

- [[wiki/<project>/<other-concept>]]
```

## Rules

- **One concept per file.** A concept is the unit; name the file after the concept.
- **Canonical term + `_Avoid_` + `_Context_` (the project glossary).** Each concept declares **one**
  preferred name, the synonyms/near-misses to avoid, and (if the project has a CONTEXT-MAP) the
  bounded **context** its terms live in (borrowed from grill-with-docs' opinionated glossary). The
  concept index + CONTEXT-MAP together are the project's **ubiquitous-language glossary**: pick the
  best term, ban the rest. Collision rule: two terms colliding **within the same context** = a
  conflict, flag + reconcile; the **same word across different contexts** is a legitimate scoped
  homonym (record both, note it) — see `references/context-map-template.md`. Keep it to
  **domain-specific** terms; general programming words don't need an entry.
  **Definition style:** define what the term **IS, not what it does**, in 1–2 tight sentences.
- **Sources is load-bearing** — it records which raw the concept draws from, so Compile knows which concepts to re-synthesize when a raw file changes. Keep it accurate.
- **Synthesize, don't copy** — a concept article is the cross-investigation view, not a paste of one raw file. If it would just duplicate a single raw file verbatim, the raw probably already is the concept — still give it a concept article so it's queryable, but keep it a distilled summary that points to the raw.
- **Contradictions across raw** (within this concept) → annotate both with attribution; never silently pick one.
- **Cross-article conflict** → when this concept contradicts another concept article, annotate both with attribution and cross-link them under `See Also`; don't silently reconcile.
- **Cross-cutting concept** → if it spans several projects, place it under `common/` (or the single most relevant project) and `See Also` the project-specific concepts, rather than duplicating per project.
- Concept `updated` reflects when the synthesized content changed, not raw mtimes.
