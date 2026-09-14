# Orient — warm up on a project's knowledge (read-only outline)

Query is **pull** (you already have a question); Orient is **push** — it surfaces *what is even
knowable* about a project up front, so investigation starts knowing which concepts exist and reuses
them instead of re-deriving. The outline already exists as `wiki/index.md` + the project's
`CONTEXT-MAP.md`; Orient **reads and presents** them scoped to one project — it never regenerates or
caches an outline file (that would drift from the index — SKILL.md「Out of scope」).

**When:** on demand (`orient me on <project>`, `项目知识大纲`, `warm up the KB`); and as the
project-scoped front of an investigation / review / new card (xg-dev-workflow calls it as its
"KB first" step; logging for that case: `references/constraints.md`「Usage logging」).

1. **Resolve project** (per `references/constraints.md`「Project resolution」). Always pull `common` alongside the resolved
   project.
2. **Read the outline** — `wiki/index.md`, the resolved project's section + `common`: the one-line
   project description + every concept row (title + summary). This *is* the outline — don't open
   concept bodies here (that's Query, once a topic is picked).
3. **Read the project-global docs** (`wiki/<project>/`, and `common`'s, if present): the
   **`CONTEXT-MAP.md`** glossary (bounded contexts + canonical terms — names to use, `_Avoid_`
   terms), the **`architecture`** overview (the map), and any **`*-invariants`** ledgers (the
   rules). **Lead with the map + the rules** — the concepts hang off them.
4. **Flag uncompiled raw** — list count + slugs so the reader knows there's detail below the outline
   (`tools/kb-backlog.py` computes exactly this).
5. **Present compactly** — project one-liner → concepts (title + summary) → bounded contexts + key
   terms → "N uncompiled raw" note. Nothing for the project → say so, suggest a first Write. Don't
   write files.
