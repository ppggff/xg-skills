# CONTEXT-MAP format (bounded contexts + scoped glossary)

A **CONTEXT-MAP** carves a project (or `common`) into **bounded contexts** — boundaries inside
which a term has **one** consistent meaning. Same word, different context = legitimately
different meaning (a *scoped homonym*, not a conflict); same word, two meanings *within* one
context = a conflict to fix.

## Where it lives

- `$KB/wiki/<project>/CONTEXT-MAP.md` — bounded contexts within a project.
- `$KB/wiki/common/CONTEXT-MAP.md` — cross-project / shared contexts.

Created **lazily** — only when the first scoped term needs a home. A project with no
terminology pressure doesn't need one.

## Structure

```md
# Context Map — <project or common>

## Contexts

- **<Context Name>** — <one line: what this context is about>. Governs: [[wiki/<project>/concept-a]], [[wiki/<project>/concept-b]].
- **<Context Name 2>** — … Governs: [[wiki/<project>/concept-c]].

## Language  (canonical terms, scoped per context)

### <Context Name>
**<canonical term>**: <1–2 sentence definition — what it IS, not what it does>.
_Avoid_: <synonyms / near-misses banned in this context>
_Scope_: <this context only> (note if it deliberately collides with a term elsewhere)

### <Context Name 2>
**<canonical term>**: …
_Avoid_: …

## Relationships

- **<Context A> → <Context B>**: <how they relate — shared term, emitted event, dependency>.
- **<Context A> ↔ <Context C>**: <shared types / vocabulary>.
```

## Rules

- **Opinionated, per context.** Within a context: one canonical term per concept, the rest
  under `_Avoid_`. Across contexts: a word may recur with a different meaning **iff** each
  occurrence is scoped to its context (record both, note the deliberate homonym).
- **Domain terms only** — general programming words don't get entries.
- **Concepts declare their context** (concept frontmatter/`scope`); a context "Governs" the
  concepts whose terms it owns.
- **Relationships are load-bearing** — they say how vocabularies meet at a seam (shared id,
  event, dependency), the way module-interaction diagrams say how modules meet.
- **Definition style** — define each term by what it **IS, not what it does**, in 1–2 tight
  sentences. A definition that describes behavior is too long/wrong.
- **Glossary purity** — a CONTEXT-MAP is **a glossary and a context map, nothing else**: terms,
  scopes, relationships. No implementation details, no design decisions (those live in
  design.md / ADRs), no scratch notes. If it reads like a spec, move that content out.
- **Keep it incremental** (Karpathy-style): start with the contexts that actually have
  terminology pressure; add rows as scoped terms arise. Don't force-classify every concept.
