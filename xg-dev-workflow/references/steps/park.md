# Step: park (session handoff — M4 write side)

Authored inline (no third-party fork; orchestrates M3 + `commit-data-repos.py` + grill.md's
round-end order + the ledger/facts/KB write disciplines. Examined-not-forked: the installed
`handoff` / `remember` skills — their carriers, an OS-temp document and a project-root
`.remember/`, are incompatible with the progress.md entry model).

The write-side counterpart of `resume`: before leaving a session — context degradation, end of
day, a model switch after the plan gate, a mid-grill interruption — make the card's state solid
on disk so a fresh session resumes from files alone. `progress.md` is the handoff's **single
entry point** (resume's first read), not its only container: content lands where its discipline
already puts it. When every write discipline was followed as you went, park degrades to a cheap
confirmation — its value is the degraded session where they weren't.

**Invocation: human-initiated.** Claude may *suggest* park on degradation/leave signals, but
never auto-runs it — especially mid-grill (M4's unbroken-window advice stands; park serves the
unavoidable interruption, it doesn't license casual ones).

## Procedure

**Precondition — resolve the card** (input parsing, not a beat): `park [<slug>]` — slug
omitted → the session's active card; ambiguous → list candidates and ask once (never guess).
No card at all (standalone investigate/review context) → refuse and point at that work's own
doc discipline (investigation/review notes); standalone handoff is out of scope.

The four beats (numbering matches the frozen design's 四拍契约):

1. **Container-routing sweep.** Walk this session for content not yet on disk and land
   each piece in its **existing** container — the scan list is "every write obligation the
   steps declare":
   - human-judgment decisions → `decisions.md` proposed blocks (grill.md「逐条入账」; park never
     writes `approved`);
   - verified load-bearing facts → `facts.md` (grill.md「载重事实入账」);
   - reusable module findings → the KB (xg-knowledge-lite Write, or note as deferred);
   - grill path → `notes/grill-<phase>.md` — a small grill's conversation-is-the-log exemption
     **expires at leave time**: persist the log (open + resolved rows) before the conversation
     is lost;
   - pending log-worthy events → `log.md` — implement-discipline audit lines (a task
     delete/merge/defer, an invalidated `[x]`) whose event happened but whose line wasn't
     written yet;
   - finished-but-unregistered slices → their `test.md` Unit-registry line;
   - live working state → `progress.md` (beat 2).
2. **Verify + top up `progress.md` to the resume floor** — the template's "State at a glance +
   Task status". By leave-state form:
   - **mid-grill (decision zone):**「Now doing」names the open `G<n>`; grill-log persisted
     (beat 1). This is grill.md's round-end order (verdict/receipts → doc sync → checkpoint
     commit) pulled forward to an arbitrary interruption point — follow that order, don't
     restate it here.
   - **mid-task (execution zone):** Task status current; **dirty product files recorded, not
     touched** — list + where-you-are + next step in「Changed files」/「Now doing」; no WIP
     commit, no stash, no interactive ask (the product working tree must leave park
     byte-identical);「Build/test:」line present.
   - At a gate stop (between phases) the state is already gate-committed — park degrades to
     confirmation + the closing reply.
3. **M3, then a scoped dev_root commit** — run the omission check first, then
   `commit-data-repos.py --project <name>` (SKILL.md「Versioning」discipline, parallel
   sessions' docs never ride along); nothing to land → skip the empty commit.
4. **Closing reply = receipts + start line** (Stop-at-gate「Ask with receipts」applies to a
   verb-run-closing reply): name the touched docs + the commit, and end with one paste-ready
   line — `xg-dev-workflow resume <slug>` — plus, when the card sits in the execution zone, an
   optional model-switch suggestion (`/model sonnet` + `/advisor opus`, SKILL.md「Subagent model
   assignment」).

## Contract invariants

- Product working tree **byte-identical** before/after park (park writes dev_root docs only).
- Board `整体状态` and every ledger-derived doc `status:` (confirmed/frozen/baseline) untouched
  — progress.md's own live frontmatter fields are normal beat-2 updates.
- **Idempotent**: a re-run with nothing new to land degrades to confirmation + closing reply,
  never an empty commit.
- On exit `progress.md` ≥ the resume floor.
- No new handoff file types — `progress.md` stays the single entry point; containers are
  created lazily by their own disciplines only.

## Usage logging

One record per run: `--action park` (vocabulary: `KNOWN_ACTIONS`). KB writes inside the sweep
are covered by this record (one event = one record).
