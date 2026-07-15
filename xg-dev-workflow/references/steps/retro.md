# Step: retro (M6)

Authored inline; may use **write-a-skill** when editing this skill. Run session-level
(end of a work session) or periodically (across requirements) to find friction and fold
fixes back into the workflow itself — so the skill compounds.

## Inputs
- This session's `progress.md` "Design iterations" + "Discovered issues".
- **The usage log** — `tools/log-usage.py report`: low scores and friction notes point at
  what to fix (this is the mining SKILL.md M6 refers to).
- Where the five phases felt slow, ambiguous, or got skipped.
- Any place evidence was guessed, an index drifted, or a frozen design got edited
  improperly (signals the mechanisms need sharpening).

## Procedure
1. **Collect friction** — list concrete moments where the workflow under- or over-served.
   Cite the doc/step involved (evidence, not vibes).
2. **Classify each** → fix belongs in:
   - a **step file** (`references/steps/*`) — the procedure was wrong/unclear;
   - a **template** (`references/templates/*`) — a doc was missing a section;
   - **SKILL.md** — a contract/mechanism/gate needs changing;
   - **cbdb/CLAUDE.md** — a project rule should be explicit;
   - **xg-knowledge-lite** — recurring module knowledge to capture/promote.
3. **Propose the edits**, smallest-diff first; confirm with the human before changing
   SKILL.md or templates (they affect every future requirement).
4. **Apply**, then run the omission check on any workflow docs touched. When a SKILL.md
   mechanism/verb changed, also grep `references/steps/*` and `references/templates/*` for
   stale references to the old wording — cross-file drift is the most common retro
   regression (the omission check alone only covers the doc being edited).
5. **Record the change history (the skill is git).** When this retro changed skill behavior,
   append a dated, **behavior-level** entry to the skill's `CHANGELOG.md` (what changed + why —
   the curated view, not a raw git diff), and commit the skill repo (English commit message, per
   repo convention; new changes as new commits — don't rewrite history). `CHANGELOG.md` is the
   human-readable evolution log; `git log` remains the full one.
   Also **re-score the usage log** where warranted: a provisional score that later user feedback
   contradicted gets a corrective record appended (per the global Skill Usage Logging rule) —
   don't leave optimistic first impressions standing.

## Pruning pass (anti-sediment — every retro)

Retros naturally *add* rules; without a deletion discipline the skill sediments (stale layers
settle because adding feels safe and removing feels risky — `writing-great-skills` vocabulary).
So every retro also prunes the docs it touches (periodically: the whole skill):

- **No-op test, sentence by sentence** — does this line change behavior versus what the model
  does by default? A failing sentence is deleted whole, not trimmed.
- **Duplication hunt** — the same meaning stated in more than one place collapses to a single
  source of truth (one authoritative statement; other sites become pointers or go).
- **Sediment check** — a rule whose justifying friction no longer shows up (usage log / recent
  cards show the failure mode gone) gets retired, with a CHANGELOG note saying why.

Deletions in SKILL.md/templates need the same human confirm as additions (step 3).

## Where the outputs land
- **The fixes + `CHANGELOG.md` + commits → the skill repo.** M6 consumes dev_root docs
  (progress, usage log) but produces none of its own by default.
- **A deferred fix is not lost** — record it in the relevant `<project>/roadmap.md`
  (M3 "Roadmap fed"; for skill-repo fixes that project is the skill repo's own).
- **A retro analysis worth persisting as a doc** (card-scoped, e.g. an end-of-milestone
  retrospective): the card's `notes/retro-YYYY-MM-DD-<scope>.md` (dated like review reports —
  an event artifact, immutable once written; a repeat retro of the same scope then can't
  collide). Cross-card retros normally need no doc of their own — fixes land in the repo,
  deferrals in the roadmap.

## Periodic (cross-requirement) extras
- Scan `index.md`s for stuck/abandoned requirements.
- **Triage the KB compile backlog** (`kb-backlog.py` output): each uncompiled raw gets compiled
  or an explicit deliberately-deferred note; a raw missing frontmatter gets it repaired (it was
  written outside the Write discipline). The session-start hook only *surfaces* the backlog —
  the retro is where it gets resolved.
- Scan `<project>/roadmap.md` for forgotten/stale items — graduate ripe ones to cards (`new`),
  prune dropped ones (note why). Check the KB `architecture` overview + `*-invariants` ledgers
  aren't drifting behind what recent cards actually built.
- Look for steps repeatedly overridden via `use:<skill>` → maybe rebind the default or
  author your own vendored version.
- Look for the same investigation re-done across requirements → promote a KB concept.
