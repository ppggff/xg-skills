# Constraints — the hard rules every action obeys

Closed list, checkable without judgment; everything else is the model's call. Config / Initialization /
Project resolution / Versioning / Usage logging moved verbatim from SKILL.md (2026-09-14, when SKILL.md
became a router).

## `$KB` resolution (config shared with xg-dev-workflow)

`$KB` resolution: (1) `--root <path>`; (2) `~/.config/xg-knowledge-wiki/config.yaml` `root:`; (3)
default `~/knowledge`. Never auto-create the config.

## Initialization (on first Write)

Create only what's missing; never overwrite: `$KB/raw/`, `$KB/raw/common/`, `$KB/wiki/`,
`$KB/wiki/index.md` (`# Knowledge Index`), `$KB/wiki/log.md` (`# Knowledge Log`), and
`$KB/FORMAT.md` + `$KB/raw-archetypes.md` (copies from `references/` — the pair travels
together, FORMAT.md §2 points at the archetypes). On read (Query/Lint) with nothing there, tell
the user to Write first; don't auto-create.

## Project resolution

When an action needs a `project` and none is given: `--project <name>` → use it; else
`tools/resolve-project.py [<cwd>]` (config `projects:` map, longest-prefix); on miss → ask once +
`tools/register-project.py`. **Never auto-pick `common`.**

## Versioning the KB (git)

`$KB` is its **own git repo** (separate from `dev_root` and the product-code repo). **Lazily
initialized** on the first commit (`git init` + a minimal `.gitignore`, announced once).

- **Commit after each mutation** (semantic boundary, mirroring `wiki/log.md`): after a **Write**
  (raw + its scoped Compile), a **Compile** batch, or a **Lint** fix-pass. Message mirrors the log
  line — `<project>: write <slug> → concept(s) …` / `compile +N ~M -K` / `lint N issues, M fixed`.
- **Autonomous local commit**; **`push` stays human-gated**; history append-only (no amend/rebase).
- A KB write done **inside** an xg-dev-workflow `investigate`/`review` run commits there (one event
  → one KB-repo commit) — don't double-commit.
- Optional: a session-end hook (shipped with xg-dev-workflow's `tools/commit-data-repos.py`) commits
  both data repos as a safety net.

## Usage logging (self-feedback)

Logging rule lives in `~/.claude/CLAUDE.md` (Skill Usage Logging) — follow it. This skill's
`--action` values: `write|compile|query|orient|lint` (the logging tool warns on anything else).
**One event = one record:** a KB write — *or an Orient warm-up* — that happens inside an
xg-dev-workflow `investigate`/`diagnose`/`review`/`improve` run is covered by that run's record;
don't double-log here. Only standalone KB work logs under this skill (`orient` only when run as a
deliberate standalone warm-up).
