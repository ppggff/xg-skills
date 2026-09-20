# Changelog — xg-codemap

Behavior-level history of the skill (the curated view; `git log` is the full one). Prepend a dated
entry, newest first, whenever the skill's behavior changes.

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
