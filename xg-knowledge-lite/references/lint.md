# Lint — the checklist (disclosed reference for SKILL.md「Lint」)

Seven checks, then the authority split and execution notes. Section numbers (§1–§7) are cited
from elsewhere in the skill — keep them stable.

1. **Coverage** — every `raw/<project>/*.md` is cited by at least one concept's Sources **or
   carries `compiled_to:` frontmatter** (semantics — incl. the `deferred` marker — in FORMAT.md;
   else it's uncompiled → suggest Compile). A Sources-cited raw missing its `compiled_to:`
   back-annotation → add it; a `compiled_to:` pointing at a non-existent concept → dangling.
   Every concept's Sources point to existing raw. Also flag
   **concept-promotion**: an idea recurring across several raw files (or repeatedly mentioned
   inside concepts) with no dedicated concept article → suggest extracting one.
2. **Index consistency** — every `wiki/<project>/*.md` **concept** has an index row; every row
   points to an existing concept. (Exclude the **curated docs** — `CONTEXT-MAP.md`,
   `architecture.md`, `*-invariants.md` — they're not concepts and carry no index row; they're
   checked in §7.) Report drift → suggest Compile.
3. **Dangling wikilinks** — every `[[<layer>/<project>/<slug>]]` resolves to an existing file
   `<layer>/<project>/<slug>.md`. Flag any non-fully-qualified form (bare / colon / relative — see
   FORMAT.md §3) → migrate to the full path form.
4. **Frontmatter** — raw + concept articles have `title` / `project` / `updated`; `project`
   matches parent dir; `aliases` don't collide across files (within a layer+project).
5. **Terminology / contexts** — verify concepts and each `CONTEXT-MAP.md` conform to
   `references/context-map-template.md` (canonical term + `_Avoid_` / definition style, within- vs
   cross-context term collision, CONTEXT-MAP purity). Plus the wiring checks not stated there:
   every concept's `_Context_` resolves to a context in the project/common CONTEXT-MAP, and every
   context "Governs" existing concepts. Drift → fix the term, record the scope, or move out
   non-glossary content.
6. **Size** — flag raw articles > 400 lines (FORMAT.md size guidance: split by sub-topic).
7. **Designated docs** — a project with several concepts but **no `architecture` overview** →
   suggest creating one (it's the entry map). Every line in a `*-invariants` ledger is
   **evidence-cited** (`func()` in `file.c` or a raw link); a subsystem with concepts but no
   invariant ledger is a **soft** flag (best-effort, don't force one where there are no
   invariants).

Authority (two levels): **deterministic findings are auto-fixed** —
§2 index rows, §3 link paths, §4 frontmatter fields, §1's mechanical `compiled_to:`
back-annotations; **judgment findings are report-only** — contradictions, concept-promotion
(§1), terminology/scope calls (§5), size splits (§6), designated-doc gaps (§7) go to the user
with a suggestion, never silently fixed.

Execution (cost): §2 / §3 / §4 / §6 are deterministic — script them when tooling exists; run
the rest (and any unscripted deterministic item) via one cheaper-model agent (Agent tool
`model: sonnet`) that returns only the violation list — the orchestrator re-verifies each
finding, then applies it per the authority split above. (Same principle as xg-dev-workflow's
「Subagent model assignment」; restated here so this skill stays self-contained.)
