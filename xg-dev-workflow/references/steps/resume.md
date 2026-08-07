# Step: session resume (M4)

Authored inline. Reconstruct full working state from **docs only** — never from chat
history. This is what lets a brand-new session start fast (docs are the core).
The write side is the `park` verb (`park.md`): run before leaving a session, it lands
un-persisted state into its containers and prints the `resume` line this step answers.

## Procedure
1. Resolve project + `dev_root` (`tools/resolve-project.py`, `--dev-root`).
2. Read `<dev_root>/<project>/index.md` → find the requirement (by slug/NNN, or the one
   the user named).
3. Read, in order: `requirement.md` (what & why, success criteria) → **`decisions.md`** (the
   ledger — approval authority: what is approved / still pending; absent on pre-ledger cards)
   → `design.md` + `adr/` (the contract **view** — its `frozen` means the referenced decisions
   are all approved) → `plan.md` (intended tasks) → **`progress.md`** (the live state:
   phase, now-doing, next-step, blockers, **Build/test:** — the exact build/test invocation to
   rebuild and re-verify with — **Close-out:** status, task table, changed files).
   **Mid-grill?** If `progress.md`「Now doing」names an open `G<n>`, also read
   `notes/grill-<phase>.md` (if persisted) and continue from the `open` row (`grill.md` Resume
   mid-grill).
   **Do NOT read `log.md`** — it's append-only audit/history (can be large), never needed to
   resume. `progress.md` is built to be self-sufficient; if you find you *need* the log to
   resume, that's a sign `progress.md` is too thin — fix the snapshot, don't lean on the log.
4. Re-establish evidence on demand: first run a light `xg-knowledge-lite` **Orient** (project-
   scoped, `wiki/index.md` section only) to catch concepts the project gained *after* this
   design froze; then re-open the requirement's own `[[wiki/…]]` links / cited `func()`/files
   on demand — don't trust prose; verify anything you're about to act on (M1). (This Orient is
   part of the resume run — covered by its log record, not logged separately.)
5. State back a 3-line situation report (phase / next step / blockers), then **STOP and wait
   for go** — resume is the human's re-entry point and they may redirect; auto-continuing
   burns work in a direction they came back to change. Exception: the resume invocation
   itself carries a directive ("resume 016 继续 T5") — follow it directly. On go, continue
   from `progress.md`'s "Next step"; execution-zone autonomy resumes as usual from there.
   Resuming into an in-flight 实现 → rebuild the harness task
   list from `progress.md`'s Task status (display mirror, `implement.md`「Harness task list」);
   never treat a stale harness list as state.

## If docs are stale or contradictory
Run the omission check (M3) first and reconcile before doing new work — a wrong resume
compounds. If `progress.md` disagrees with the code, trust the code and fix the doc.
