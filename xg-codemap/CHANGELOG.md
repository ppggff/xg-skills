# Changelog — xg-codemap

Behavior-level history of the skill (the curated view; `git log` is the full one). Prepend a dated
entry, newest first, whenever the skill's behavior changes.

## 2026-09-20 — the note is organised by function; glossary and function-name sentences required

Fourth reviewer round on the same map, five comments: undefined terms and mixed spellings (ledger,
视界 / horizon), bare function names, no flow for verification, no principles behind a package, and —
the structural one — a spine of "where the diff landed" where the reader wanted "what the software
does and how each function works, changed where, verified how". Step 5 now makes function the spine
and the code-area view an appendix; a new step 7 requires a glossary, one spelling per concept and a
subject-verb-object sentence after every function name; step 6 adds a verification flow diagram.
Model (standard v0) unchanged: this is all Presentation-layer procedure.

## 2026-09-20 — a change map also shows how the thing runs; every section opens with an intro

Third reviewer comment on the same real map: structure and dependency diagrams answered "what is
there" but not "how does it run". Step 6 now requires at least one control-flow diagram per entry
point that matters (the invocation path and the highest-risk run), read from the code at `head`,
plus a two-sentence intro per section. Model (standard v0) unchanged.

## 2026-09-20 — every diagram declares its kind; legibility rule for hand-drawn diagrams

From the first review of a real change map (158 commits): the reviewer could not tell what kind of
diagrams they were looking at, and the top diagram was too wide to read. Step 6 now requires a
`图类型 · 回答 · 边` line under each diagram and caps a diagram at about 15 nodes with short labels and
`direction TB` inside subgraphs, splitting by group beyond that. Model (standard v0) unchanged.

## 2026-09-17 — package opened as a value trial (v0)

`SKILL.md` drawing procedure for a hand-drawn change map (enumerate → assign drawn / folded / elided →
Observed and Intent layers → one diagram per question → comment handling) and `references/standard.md`
v0 (seven frozen elements plus the subject, completeness accounting, framework list). No tooling yet by
design: the trial first checks whether a map helps a reviewer more than the diff.
