# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A monorepo of **two Claude Code Skill packages** — not application code. Each is Markdown-driven (a `SKILL.md` contract + on-demand `references/`) with a few Python helper scripts. There is **no build, compile, lint, or test pipeline**; "running" a skill means Claude Code loading its `SKILL.md` and following it.

- **`xg-knowledge-lite/`** — a cross-project code-knowledge base. Two layers: `raw/<project>/*.md` (Claude's investigation write-ups, the source of truth) → `wiki/<project>/<concept>.md` (concept articles *synthesized* from raw). Actions: Write, Compile, Query, Orient, Lint.
- **`xg-dev-workflow/`** — a design-centric dev workflow. Five phases (需求 requirement → 设计 design → 详设 detail → 实现 plan/implement → 测试 test) plus an M+ close-out **评审** review gate, one requirement = one directory of docs. Verbs: `new`, `requirement`, `design`, `detail`, `plan`, `test`, `investigate`, `review`, `change`, `resume`, `check`, `retro`.

The two are siblings: the workflow *orchestrates* code work and links out to the KB for reusable module knowledge; it never stores that knowledge itself.

## Skill package anatomy

```
<skill>/
  SKILL.md           # YAML frontmatter (name + description) + the procedure
  README.md          # human-facing overview
  references/        # steps/, templates/, format specs — loaded on demand, not all upfront
  tools/             # Python helpers (no deps beyond stdlib; PyYAML used if present, else a fallback parser)
                     #   xg-dev-workflow/tools/ also holds viewer.py + viewer/ (the status HTML
                     #   viewer's shell.html + vendored marked.min.js + LICENSE + its tests) —
                     #   the repo's only browser assets; marked is pinned, see viewer/VENDORED.md
```

- **`SKILL.md`'s `description` frontmatter is the activation/trigger surface.** Editing it changes *when* Claude Code invokes the skill — treat it as load-bearing, not a comment.
- `references/` files are pulled in by name as the procedure needs them, keeping the always-loaded surface small. When adding a step/template — or a **section within a template** — wire it into `SKILL.md` (and the relevant step file) or it is dead (invariant 6 below is the general rule).

## Cross-file invariants (not discoverable from a single file)

These are the things that break silently if you edit one file and forget the coupling:

1. **Tool scripts are byte-identical copies that must be kept in sync.** Each script's header lists its sync targets. Verified copies:
   - `tools/resolve-project.py` — identical in **both** `xg-dev-workflow/tools/` and `xg-knowledge-lite/tools/`.
   - `tools/log-usage.py` — identical across `xg-dev-workflow/tools/`, `xg-knowledge-lite/tools/`, **and** `~/.claude/scripts/`.
   - After editing one, `cp` it to the others (byte-identical). `register-project.py` and `kb-backlog.py` live only in `xg-knowledge-lite/tools/`; `commit-data-repos.py`, `check-code-refs.py`, `workflow-status.py` and `viewer.py` (+ its `viewer/` assets) live only in `xg-dev-workflow/tools/` (none of these is synced).
   - Quick check: `diff xg-dev-workflow/tools/resolve-project.py xg-knowledge-lite/tools/resolve-project.py`.

2. **Both skills share one config: `~/.config/xg-knowledge-wiki/config.yaml`** (outside this repo). It holds `root:` (KB root, default `~/knowledge`), `dev_root:` (workflow docs root, default `~/dev-workflow`), and one `projects:` map (name → paths). The shared `projects:` map is what makes project names line up, so `[[<layer>/<project>/<slug>]]` wikilinks resolve consistently between workflow docs and the KB. Scripts **never auto-create** this config.

3. **All user data lives outside the repo** — under `~/knowledge` (KB), `~/dev-workflow` (workflow docs), and `~/.config/xg-knowledge-wiki/` (config + `usage.jsonl`). Editing this repo changes skill *logic only*; it never touches that data. Don't add example KB/workflow content into the repo.

4. **Wikilink direction is a dependency rule, not a style choice** (xg-knowledge-lite): the load-bearing link is **concept → raw** (a concept's `Sources` list), which is what drives incremental recompile. `raw → raw` is navigation; a `raw → concept` link is navigation-only — **raw must never depend on a concept**, because the model's invariant is "wiki is recomputable from raw." Workflow docs → KB is one-way; the KB never links back into `dev_root`.

5. **`log-usage.py` enforces a canonical action vocabulary** (`KNOWN_ACTIONS` in the script). If you add or rename a verb/action in either `SKILL.md`, update that set in `log-usage.py` (and re-sync the copies) — off-vocabulary actions still log but emit a warning and fragment the retro report.

6. **Structural edits must backfill their cross-references in the same batch** (the general rule; the anatomy note above and invariant 5 are its file-level and verb-table instances). Concretely:
   - (a) When changing a term, ID scheme, deferral phrase, or mechanism wording that other files cite, grep `SKILL.md` + `references/` of **both** skills for stale references to the old wording and fix them in the same commit batch — two past evolutions (the 详设 phase introduction, the 010 ledger) skipped this and each left a crop of broken hand-offs (see the 2026-07-27 template-explicitness audit).
   - (b) When adding a template section, wire a filling instruction into the owning step file **or** mark the section optional in the template — a section nobody is instructed to write is dead weight.
   - `references/steps/retro.md` runs the same sweep as a retro backstop; this entry is the always-loaded trigger.

## xg-dev-workflow: the step-binding model

The five phases have **stable contracts** (input → output doc → gate) that are independent of *how* each step is implemented. Each step resolves to one implementation by priority: (1) runtime override via `use:<skill>` on the verb or a persisted `workflow.bindings:` config entry; (2) the **vendored default** in `references/steps/<step>.md` (a forked copy of a source skill — this is the default and is ours to edit); (3) inline for steps with no third-party source. When changing behavior, edit the vendored step file or rebind — **never change the contract** described in `SKILL.md` without intent. `references/steps/adversarial-critic.md` is shared by the requirement/design/review steps.

In the **decision zone** (需求/设计/详设, plus the one-time execution authorization after `plan.md`) the skill advances **one phase per invocation, then stops at a gate** — design freezes on approval (changes route through the `change`/M2 flow); the implementation plan is freely mutable. Once execution is authorized, the **execution zone** (实现 → 测试 → 评审 report) flows autonomously with **no per-phase stop** (see SKILL.md「Two zones」). This stop-at-gate discipline is core, not advisory.

## Editing conventions

- Skill files, code comments, and commit messages are **English** (per the global convention; the *content authored by* the skills — KB notes, workflow docs — is Chinese prose with English domain/technical terms preserved).
- When changing a `SKILL.md`, keep its `README.md` and the user-facing skill description registered with Claude Code consistent — they restate the same model and drift is confusing.
- When a change alters a skill's **behavior**, prepend a dated, behavior-level entry to that skill's `CHANGELOG.md` (the curated history — *what changed + why*, not a raw diff; `git log` is the full one). For `xg-dev-workflow` this is the M6 retro step's job; both skills carry a `CHANGELOG.md`.
- Python helpers target stdlib + an optional-PyYAML-with-text-fallback pattern; preserve that (don't introduce a hard PyYAML dependency).
- **Template examples: contrast-pair preferred over filled samples, ≤6 lines, marked 「示意」.** A good/bad pair teaches judgment; a filled sample whose fields are self-explanatory is dead weight — don't add one.
- **Trim/compression edits list semantic points first.** Before compressing or relocating any passage, write down the semantic points it carries and tick them off in the result — a diff walk alone misses dropped half-sentences (a contract clause can read like an explanation).
- **Comment sparsely; code self-explains.** Keep only: the file docstring (incl. the sync-target header), function docstrings, step/section markers, and why-notes for a constraint the code can't show. No comments narrating what the next line does, and don't restate the docstring inline. Match the existing files' density.
