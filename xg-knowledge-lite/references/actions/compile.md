# Compile — synthesize concepts from raw (incremental)

The single routine that turns raw into concept articles — **one concept per
`wiki/<project>/<concept>.md`**. Called two ways, same procedure, only the work set differs:

- **Scoped** — from `write.md` §B: just the concept(s) the freshly written/updated raw touches.
- **Batch** — standalone: bootstrap concepts from an existing pile of raw (e.g. migrated raw
  articles), or repair drift after raw changed out-of-band.

Karpathy-style incremental: **no full rebuild, no hash stamp** — only the concepts in the work set
are (re)synthesized.

1. Resolve `$KB`; ensure `wiki/` + `wiki/index.md` exist.
2. **Determine the work set:**
   - *Scoped:* the concept(s) the triggering raw covers — same concept exists → update; new concept
     → create, named after the concept.
   - *Batch:* raw with **no** concept citing it yet → new concepts; raw whose `updated` is newer
     than the concepts citing it → re-synthesize; concepts whose **all** Sources raw no longer exist
     → stale, mark `[MISSING]` / remove; everything else → untouched.
3. **Synthesize each concept** in the work set into `wiki/<project>/<concept>.md` (per
   `references/concept-template.md`) from **all** raw that covers it (not just one write-up):
   overview + body + a **Sources** list linking that raw (`[[raw/<project>/<slug>]]`) + See Also.
   Synthesize, don't copy; contradictions across raw → annotate with attribution, never silently
   pick.
   - **Placement of a cross-cutting concept:** if a concept is relevant to several projects, put it
     under `common/` (or the single most relevant project) and `See Also` the project-specific
     concepts that touch it — don't duplicate it per project.
4. **Cascade Updates** (ripple to neighbors): after the work-set concepts, scan **same-project**
   concept articles (and `wiki/index.md`) for any whose content is **materially affected** by the
   changed raw — it cites the same raw, or states something the new raw supersedes. Re-synthesize
   those too and bump their `updated`. Keep it light: same-project + materially-affected only; no
   probe/graph, no multi-round chasing.
   - **Cross-article conflict:** when the contradiction is between two *separate* concept articles
     (not within one concept's raw), do not silently reconcile — annotate **both** with source
     attribution and cross-link them via `See Also`.
4b. **Glossary upkeep** — when a synthesized concept pins/changes a canonical term
(`_Avoid_`/`_Context_`), reflect it in the project/common `CONTEXT-MAP.md` (create lazily): add the
term under its context's Language section and the concept under that context's "Governs". A new
bounded context → a new section + its relationships. Flag any within-context term collision.
5. **Back-annotate & refresh** — set `compiled_to:` in each source raw's frontmatter to the
   concept(s) synthesized from it (format & semantics: `$KB/FORMAT.md`); then refresh the `wiki/index.md`
   row for every touched concept (and, when a project section is new or its scope shifted, its
   one-line project description); append one line to `wiki/log.md`:
   - scoped: `## [YYYY-MM-DD] write | raw <project>/<slug> → concept(s) <project>/<concept>[, …]`
   - batch: `## [YYYY-MM-DD] compile | +<new> ~<resynth> -<removed> concepts`
6. (Batch) suggest Lint afterward.
