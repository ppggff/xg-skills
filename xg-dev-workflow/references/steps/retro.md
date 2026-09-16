# Step: retro — improve this skill

Run at the end of a work session or periodically across cards: find friction, fold fixes back into
the workflow so the skill compounds — and prune, so it does not sediment.

## Inputs

- Lite cards' close-out **observation notes** (`notes/observations.md`: places synced per change · needless
  interruptions · doc time and lines read at go · missed commitments / unauthorized changes / verification
  gaps · quality steps skipped and why · handoff gaps) — the flow's friction record.
- **The session transcripts** where available: tally AskUserQuestion calls and turns ending in 「继续？」or a
  confirmation ask — the interruption count the model's own observation note misses.
- **The usage log** — `tools/log-usage.py report`: low scores and friction notes point at what to fix.
- Any place evidence was guessed, a pointer drifted, or a commitment was changed without its 变更 line.

## Procedure

1. **Collect friction** — concrete moments where the workflow under- or over-served; cite the doc / step
   (evidence, not vibes).
2. **Classify each** → the fix belongs in a step file (the procedure was wrong or unclear) · `constraints.md`
   (a checkable rule is missing or wrong) · `lenses.md` (a lens prompt shape) · a template (a skeleton gap) ·
   `SKILL.md` (routing, the 自主区 list) · the project's CLAUDE.md (a project rule should be explicit) ·
   xg-knowledge-lite (recurring module knowledge).
3. **Propose, smallest diff first**; confirm with the human before changing `SKILL.md`, `constraints.md` or
   a template (they touch every future card) — each proposal one 照案 row (recommendation + trade-off +
   evidence anchor) or one 真判 ask; never a blanket confirm over an untiered list.
4. **Apply, then sweep**: when a term, id, pointer or mechanism wording that other files cite changed, grep
   `SKILL.md` + `references/` of **both** skills for the old wording and fix it in the same batch (repo
   CLAUDE.md invariant 6); `references/legacy/**` and `tools/legacy/` are excluded — frozen on purpose.
   Run `tools/check-sync.py`; re-measure `constraints.md` Cap-1 (the 体量行 below).
5. **Record — the skill is git.** A behavior change gets a dated, behavior-level `CHANGELOG.md` entry (what
   changed + why — the motivating incident lives **there**: date, card, calibration data, quote — never
   inlined in a step body), ending with the **体量行**: the six dimension numbers (SKILL.md · 流程 files/lines
   · 约束 · 模版 · 视角 · 元) and the two totals (lite face / whole skill incl. `references/legacy/` +
   `tools/legacy/`). Commit the skill repo (English message; new commits, never rewritten history). Re-score
   the usage log where user feedback contradicted a provisional score.

## Pruning pass — every retro

Retros add rules; without a deletion discipline the skill sediments. Prune the docs this retro touched
(periodically the whole lite face), **your own additions first** — the newest layer is the likeliest to
sediment and the cheapest to cut:
- **Rule in the body, evidence in the CHANGELOG**: an inline dated justification (`Learned YYYY-MM-DD …`)
  moves to the CHANGELOG now; if a rule is opaque without an example, keep a bare undated one.
- **No-op test**, sentence by sentence — does the line change behavior versus the model's default? A
  failing sentence is deleted whole, not trimmed.
- **Duplication hunt** — one meaning, one owner; other sites become pointers or go.
- **Sediment check** — a rule whose failure mode no longer shows up (usage log, recent cards' observation
  notes) is a 退役候选: mark it in the CHANGELOG's rule → failure table; retire only with the human's
  confirm, noting why.
- **自主区 check** — a step sentence that fixes something SKILL.md「自主区」leaves to the model (section
  depth · drawing beyond the trigger · candidate count beyond the minimum · file / card split · test
  strategy · commit granularity · reading scope · lens dispatch by risk · ADR count) is out of bounds: delete it.
- **Gate-cost budget** — a new per-go action names the existing action it replaces or how it scales down by
  size; one that can answer neither is rejected.

## Where the outputs land

Fixes + `CHANGELOG.md` + commits → the skill repo. A deferred fix → the relevant `<project>/roadmap.md` (for
skill-repo fixes, the skill repo's own project). A retro analysis worth keeping as a doc → the card's
`notes/retro-YYYY-MM-DD-<scope>.md` (an event artifact, immutable once written); cross-card retros normally
need no doc of their own.

## Periodic extras

- Scan the boards for stuck or abandoned cards; scan `roadmap.md`s for stale items — graduate the ripe
  ones (`new`), prune the dropped ones with a reason.
- **Triage the KB compile backlog** (`kb-backlog.py`): each uncompiled raw gets compiled or an explicit
  deliberately-deferred note; a raw missing frontmatter gets it repaired. Check the KB `architecture`
  overview and `*-invariants` ledgers against what recent cards actually built.
- **KB usage-frequency scan** — every use of a KB note lands as a wikilink in a workflow doc, so the citation
  tally across dev_root is the usage record:
  `grep -rhoE '\[\[(wiki|raw)/[^]]*\]\]' <dev_root> --include='*.md' | sort | uniq -c | sort -rn`.
  A heavily cited concept earns its keep; a heavily cited raw with no concept is a promotion candidate; a
  concept with zero citations across recent cards is a dead-weight candidate — verify, then retire or merge.
- The same investigation re-done across cards → promote a KB concept; a lens or review axis whose findings
  repeatedly die in adjudication → revoke its cheaper-model assignment (SKILL.md「Subagents」calibration).
