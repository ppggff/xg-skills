# Constraints — the hard rules every card obeys (lite and 存量 alike)

Closed list, script-checkable or checkable without judgment; everything else is the model's call (SKILL.md
「自主区」). Config / Versioning / Usage logging were moved verbatim from SKILL.md (2026-09-10, 030).

## Layout (lite)

```
<dev_root>/<project>/            # == xg-knowledge-lite project name; dev_root from config
  index.md                       # card board: | Card | Phase | 整体状态 | Deps | Dir | — lite rows write `lite` · todo/active/done/dropped
  roadmap.md · investigations/ · reviews/ · notes/ · legacy/ (pre-workflow archive, never canonical)
  NNN-slug/design.md             # the working draft; frontmatter `governance: lite`, `status:` is the truth
  NNN-slug/{facts.md, adr/, plan.md, progress.md, log.md, notes/}   # created when content appears (lite.md「Card files」)
```
存量 cards keep the five-phase layout described in `references/legacy/SKILL.md`「Layout」.

## KB boundary

Reusable module knowledge does **not** live in dev_root — it lands in xg-knowledge-lite (`~/knowledge`
raw/wiki), referenced via `[[wiki/<project>/<slug>]]` wikilinks (load-bearing for the KB's incremental
recompile — never swap for a markdown link). Workflow docs → KB is one-way; the KB never links back.

## Config & project resolution (shared with xg-knowledge-lite)

Same config file: `~/.config/xg-knowledge-wiki/config.yaml`.

- `dev_root:` → workflow docs root ((1) `--root <path>`; (2) config `dev_root:`; (3) default
  `~/dev-workflow`). Never auto-create the config.
- `projects:` → the **same** map xg-knowledge-lite uses. Resolve cwd→project with
  `tools/resolve-project.py [<cwd>]`; on miss, ask once and register via xg-knowledge-lite's
  `tools/register-project.py <name> <path>`. Never auto-pick `common`.


## Versioning the docs (dev_root git)

`dev_root` is its **own git repo** (separate from the product-code and KB repos), lazily
initialized on the first commit (`tools/commit-data-repos.py`).

- **Commit at each gate / doc boundary** (semantic, not per keystroke): whenever a verb finishes
  writing — gates, implement tasks, notes, grill-round checkpoints. Run M3 first, then commit.
  Message: `<project>/NNN-slug: <verb> — <one line>`.
- **Gate commits are scoped to the acting card**: `tools/commit-data-repos.py --card
  <project>/<NNN>` (docs = the card dir + the project's index/roadmap; KB stays
  project-level) — a parallel session's uncommitted docs,同项目他卡 included, must never
  ride along (027). `--project <name>` stays for project-level writes (learn/improve).
- **Autonomous local commit; `push` stays human-gated;** history append-only (no amend/rebase).
- An implement task yields **two** commits — product code → its own repo, docs → the dev_root repo.
  Don't cross them.
- Optional safety net: a session-end hook sweeps uncommitted docs via `commit-data-repos.py` (README).


## Usage logging (self-feedback)

Rule: `~/.claude/CLAUDE.md` (Skill Usage Logging); `--action` = the verb just run (vocabulary:
`KNOWN_ACTIONS` in `tools/log-usage.py`; `status` only as a deliberate standalone view). Mappings:
an in-card `investigate` logs `design`; implement-phase task work logs `plan` (one record per
task/checkpoint). **One event = one record** — a KB write inside a verb run is covered by that
record; only standalone KB work logs under xg-knowledge-lite.

Lite cards log `--action lite`, one record per event (open · go · close-out); the other verbs keep their names.
