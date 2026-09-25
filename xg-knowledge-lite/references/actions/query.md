# Query — search the knowledge

1. **Concepts first** (primary): read `wiki/index.md` → read the relevant
   `wiki/<project>/<concept>.md`. Synthesize an answer with `[[wiki/<project>/<concept>]]`
   citations; drill into a concept's **Sources** raw for detail. Prefer KB knowledge over training
   knowledge for repo facts.
2. **Grep fallback**: if concepts surface too little — or `wiki/` isn't built yet — grep the **raw**
   directly:
   ```bash
   rg -i "<query>" "$KB"/raw/*/*.md      # ripgrep; fallback: grep -ri ... --include='*.md'
   ```
   Report `<project>/<slug> @ line` + snippet. Catches raw recorded but not yet compiled into a
   concept.
   **Backlog visibility:** `tools/kb-backlog.py` lists per-project uncompiled raw (SessionStart-hook
   friendly; wiring example in README). Its reliability contract: `compile.md` step 5 owns the
   `compiled_to:` back-annotation; Lint §1 (`lint.md`) owns the check (incl. the
   deferred marker); the marker's semantics live in `$KB/FORMAT.md`.
3. Contradictory hits → flag to the user.
4. **Say what the KB doesn't cover**: an answer that leaves part of the question uncovered names that part and
   what was searched — the concepts read, the grep pattern and its scope ("not found with query Q over scope S",
   `conventions-core.md`「Negative statements」), so a caller never reads the silence as "the KB has nothing".

Don't write files during Query. Asked to save the answer → distill the **durable findings**
into raw via `write.md` (a synthesized answer is not itself raw — save what was learned, not the
Q&A); there is no separate archive-page layer (SKILL.md「Out of scope」).
