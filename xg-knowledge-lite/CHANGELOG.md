# Changelog — xg-knowledge-lite

Behavior-level history of the skill (the curated view; `git log` is the full one). Prepend a dated
entry, newest first, whenever the skill's behavior changes — including when an `xg-dev-workflow` M6
retro lands a fix in this skill. Each entry says *what changed* and *why*, not the raw diff.

## 2026-07-24 (comprehensive skill audit vs writing-great-skills — Sprawl + Duplication)

Part of the cross-skill audit driven from `xg-dev-workflow`'s M6 retro (its CHANGELOG has the
full framing). This skill carried **no** event-sourcing Sediment, but did carry Sprawl and
Duplication measured against `karpathy-llm-wiki` (the two-layer raw→wiki source) and the
`writing-great-skills` standard:

- **Sprawl** — `FORMAT.md`'s ~100 lines of optional raw-note archetypes (self-labeled "not
  mandatory") disclosed to `references/raw-archetypes.md` behind a pointer (216 → ~114 lines);
  FORMAT keeps frontmatter + conventions resident (karpathy's "template is the SSOT" shape).
- **Duplication → single source of truth**:
  - `compiled_to:` frontmatter semantics and wikilink **syntax** now live once in `FORMAT.md`;
    SKILL.md, lint.md, concept-template.md, README.md reference it (~5 + 3 sites converged). The
    SKILL link-direction (= dependency direction) recompile **invariant** stays in SKILL.md.
  - glossary collision rule (within-context conflict vs cross-context scoped homonym) + the
    "define what it IS, not what it does" style → `context-map-template.md`; concept-template.md
    and lint.md point to it.
  - cross-raw contradiction / cross-article conflict / cross-cutting placement → SKILL.md's
    Compile step; concept-template.md folds to a pointer.
  - `FORMAT.md` §5/§6 trimmed to items §3 doesn't already cover; the checklist references its
    sections rather than restating them.
- Removed scattered inline provenance asides (karpathy / grill-with-docs / CONTEXT-FORMAT); the
  karpathy attribution remains once, in README.md.

Open item (deferred): the CONTEXT-MAP / bounded-context glossary layer overlaps the sibling
`domain-modeling` skill — whether to pointer-reuse it or keep this layer self-contained is a
standing decision, not taken here.

## 2026-07-16 (retro batch — comparison against the ~/.agents/skills 2026-07-09 set)

- **Lint authority split** (from karpathy-llm-wiki): deterministic findings (index rows, link
  paths, frontmatter fields, mechanical `compiled_to:` back-annotations) are **auto-fixed**;
  judgment findings (contradictions, concept-promotion, terminology/scope calls, size splits,
  designated-doc gaps) are **report-only** — surfaced with a suggestion, never silently fixed.
  Previously the orchestrator fixed everything flagged, which let judgment calls land without a
  human decision.
- **Query save semantics closed**: "save the answer" now routes the durable findings into raw
  via Write (a synthesized answer is not itself raw — save what was learned, not the Q&A);
  karpathy-style `[Archived]` answer pages are explicitly Out of scope.
- **Description pruned** (one trigger per branch; 444 → 427 bytes).
- **Short-lines convention** (shared with xg-dev-workflow, same-day batch): KB articles and
  this skill's own files wrap prose around ~100 chars; a long list item splits into
  sub-bullets. Landed as a Conventions bullet in SKILL.md.
- **Second pass — fresh-context writing-great-skills audit** (same day): **Lint checklist
  disclosed to `references/lint.md`** (branch-only reference — Write/Query/Orient paths no
  longer wade past 26 lines of Lint detail; §1–§7 numbering preserved, cross-references now
  name the file). The incremental-no-hash design fact had four homes → one (the Compile
  section). Project resolution generalized to "when an *action* needs a project" so Orient
  points instead of restating. Orient's double-log sentence deduplicated to Usage logging
  (which now also names `diagnose`). Writing-style line collapsed. SKILL.md 2607 → 2209 words.

## 2026-07-08

- **Lint execution note (cost):** §2/§3/§4/§6 are deterministic — script when tooling
  exists; the remaining checks run via one cheaper-model agent (Agent tool `model: sonnet`)
  returning only the violation list, which the orchestrator re-verifies by fixing. Mirrors
  xg-dev-workflow's new「Subagent model assignment」rule (landed the same day); restated
  inline so this skill stays self-contained.

## 2026-07-07 (second batch — writing-great-skills audit)

- **raw authorship contradiction resolved deliberately (review F6, post-audit note).** The
  de-duplication deleted the conventions bullet "raw = source of truth (human + Claude author
  it)" — the only text allowing human-authored raw, which contradicted Write §A ("Raw is
  Claude-authored"). Resolution recorded here: **raw is Claude-authored** — matches practice and
  kb-backlog's treatment of hand-written raw (missing frontmatter) as format defects; humans
  contribute via chat/investigations, Claude records.

- **SKILL.md de-duplicated** (no behavior change): the `compiled_to`/backlog reliability story,
  previously stated in four places, now has one owner each — Compile step 5 owns the
  back-annotation obligation, Lint §1 owns the check; Query's Backlog-visibility block and
  Orient §4 point instead of restating. "raw = source of truth" conventions bullet removed
  (stated in the architecture intro); link-direction Directions enumeration merged into the
  Link-direction bullet; "balance still being tuned" meta-sentence dropped.

## 2026-07-07

- **Description pruned to branches** (from the ~/.agents/skills comparison study, via the
  xg-dev-workflow retro): dropped the root/config paths and "lean sibling" identity (body
  facts), collapsed the 'warm up the KB' synonym into the orient branch — the description is
  always-loaded context and pays for every word. One trigger form per branch kept (some
  synonym spellings collapsed).

## 2026-06-30

- **`tools/kb-backlog.py` + SessionStart push for uncompiled raw.** New script lists, per project,
  raw articles not yet synthesized into a concept (signal: no concept `Sources` cites them via
  `[[raw/<project>/<slug>]]` and no `compiled_to:` frontmatter) plus raw missing frontmatter; wired
  to a SessionStart hook so the compile backlog is **surfaced every session** instead of only when
  someone runs Lint/Orient. Quiet when clean, always exits 0. *Why:* an `xg-dev-workflow` M6 retro
  found raw kept accumulating uncompiled (e.g. acme-db 6 raw / 1 wiki) because Compile is a
  deferred manual judgment with no push — "remember to compile" had just failed in practice. The
  fix is **visibility (pull→push)**, not more discipline. A deliberate deferral is marked in the
  raw itself — `compiled_to: deferred — <why>` (any non-empty `compiled_to:` suppresses the flag) —
  so intentional backlog doesn't nag every session.
- **Compile must back-annotate `compiled_to:` and update `wiki/index.md`.** The same retro found
  compiled raw (all of cbdb) lacked `compiled_to`, and a created concept (acme-db
  `ao-rewrite-invariants`) was never added to `index.md`. These make the backlog signal reliable and
  the concept discoverable; treat both as required Compile outputs, checked by Lint.

## 2026-06-28

- **The KB is now git-managed, with a commit cadence.** `$KB` is its **own repo**, **lazily
  `git init`'d** on the first commit (announced once), committed after each **Write/Compile/Lint**
  with a message mirroring `wiki/log.md`. **Autonomous local commit, push human-gated, history
  append-only.** A KB write done inside an xg-dev-workflow `investigate`/`review` commits once
  there. An optional session-end hook (xg-dev-workflow's `tools/commit-data-repos.py`) sweeps both
  data repos as a safety net. *Why:* "文档和 KB 也要被 git 管理,有提交时机,自动提交."
- **First-class designated docs: `architecture` + `*-invariants` ledgers.** Recognized two
  curated project-global docs surfaced first by Orient and checked by Lint: an **architecture**
  overview (`wiki/<project>/architecture` — the system map, linked & refreshed as-built by
  xg-dev-workflow's design step) and per-subsystem **invariant ledgers**
  (`wiki/<project>/<subsystem>-invariants` — evidence-cited, loaded/replayed by the dev-workflow
  adversarial-critic). Both are **hand-maintained, CONTEXT-MAP-class docs outside the
  recompute model** — not synthesized-from-raw concepts, and they carry no index row
  (SKILL.md「Designated docs」; corrected 2026-07-02 — this entry originally mis-stated them as
  ordinary recomputable concepts). *Why:* these
  card-transcending docs are durable system knowledge → KB (per the two-skill split); the invariant
  ledger already existed by design but wasn't discoverable (no Orient/Lint surfacing).

## 2026-06-27

- **CHANGELOG introduced** (this file) — both sibling skills now keep a curated, behavior-level
  change history alongside `git log`. *Why:* `git log` alone isn't a readable "what changed in the
  skill's behavior" view.

## Earlier

See `git log` for the init and subsequent commits — this curated changelog starts 2026-06-27.
