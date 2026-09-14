# Write — record raw, then refresh its concepts

The entry point for recording raw. Raw is Claude-authored: distill stable conclusions from
investigation, never transcribe the play-by-play.

### A. Record raw

1. Resolve project. Pick a slug for the write-up (kebab-case, ≤ 60 chars — named after the
   investigation / topic). If that slug already exists in the project and this is genuinely new
   content, append a numeric suffix (`-2`) or pick a distinct name — never silently overwrite an
   existing raw file (to revise it, use Update mode instead).
2. Write `$KB/raw/<project>/<slug>.md` per `$KB/FORMAT.md` (frontmatter `title`/`project`/`updated`;
   archetype body; `func()` in `file.c` not `file.c:NNN`; `[[..]]` wikilinks; no links to workflow
   docs — dev_root requirement dirs or legacy `plan/`/`problem/`/`progress/`; references are
   one-way: workflow → KB). A raw file may legitimately cover several concepts.
3. **Update mode**: to revise existing raw, locate the raw file (slug / context / grep), edit in
   place, bump `updated`. Contradictions → don't silently overwrite; quote both / ask.

### B. Refresh affected concepts

4. Identify the distinct concept(s) this raw touches (a raw file may cover several).
5. **Run Compile scoped to those concepts** (`compile.md`). It synthesizes/updates each concept
   article, cascades to materially-affected neighbors, back-annotates `compiled_to:` in the raw, and
   refreshes index + log.

(One investigation may legitimately produce/refresh several concept articles — split by concept.)
