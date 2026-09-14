# xg-dev-workflow

A lite, design-centric development workflow skill. One card = one directory of docs, organized per
project under a config-driven root. The spine is one continuously updated working draft:

understand ⇄ investigate ⇄ compare ⇄ negotiate → **go** → continuous execution → close-out (simplify · review by size · observation note)

Requirement, design and detail are angles of thought in the draft, not gated phases. The human confirms
**commitments** (goals, constraints, acceptance conditions) and gives one **go**; after that Claude runs
autonomously and comes back only for a changed goal or boundary, work beyond the authorization, or an
operation that needs its own authorization. Everything lands in docs, so any session — including a
brand-new one — resumes from files alone.

## What it is / isn't

- It **is** a routing `SKILL.md` + one procedure (`references/steps/lite.md`, ≤150 lines) + its companions
  (`steps/discuss.md` for the pre-go conversation, `templates/design-lite.md`, `constraints.md` — the closed
  list of hard rules — and `lenses.md`, the fresh-context lens prompt shapes) + shared steps (investigate ·
  diagnose · review · improve · learn · split-isolate · retro) + a few Python tools. Everything the frozen
  five-phase flow needs lives under `references/legacy/` and `tools/legacy/` (deleted in phase 3).
- It **isn't** the knowledge base. Reusable module knowledge lives in `xg-knowledge-lite`
  (`~/knowledge`), referenced from here via `[[wiki/<project>/<slug>]]` wikilinks.
- **存量 cards** (frontmatter `governance` ≠ `lite`, 2026-09 and earlier) still run the old five-phase flow,
  frozen verbatim in `references/legacy/SKILL.md` and loaded only for them; new cards are always lite.

## Layout

```
<dev_root>/<project>/index.md (card board) · roadmap.md · investigations/ · reviews/ · notes/ · legacy/ · NNN-slug/design.md (+ facts.md · adr/ · plan.md · progress.md · log.md · notes/ as content appears)
```

`dev_root` and the `projects:` map come from `~/.config/xg-knowledge-wiki/config.yaml` — the same
config xg-knowledge-lite uses, so project names line up. Hard rules (layout, config, dev_root versioning,
ids, doc form, ADRs, go, operations, commits, config, KB boundary, usage logging, synced files, caps): `references/constraints.md`,
each row script- or reader-checkable.

## Key rules

- **One draft, explicit commitments, one go.** `design.md` carries the problem, the commitments as
  `### Req-n <状态词>` blocks, the candidates and chosen approach, contracts and invariants (`Inv-n`),
  open questions, tasks and the verification plan. A commitment is whatever the human asked for or
  confirmed and has not released — not copying it into the doc is no authorization to drop it.
- **Candidates first, evidence before go.** Two or more candidates on the hack ↔ 补丁 ↔ 推翻重来 spectrum
  with costs; key feasibility rests on code, a derivation or a spike; thin evidence is stated. Shape or
  environment clauses in the ask are constraint commitments; a redo imports the old card's verbatim human
  messages and the roadmap's rulings.
- **The go ask is one message with receipts**: commit first, then 摘要 · commitments · scope · impact forecast
  · risks · what the authorization includes and excludes · the 收敛行 · the split between what Claude
  verified and what only the human can decide. A reply that settles every open judgment and raises no new
  question is a go.
- **Execution is continuous.** Approach changes, added tests, reordering and review fixes are ordinary work
  (an A→B walk with one reason line); only three kinds of change come back to the human. Destructive or
  outward operations (live environments, push, range deletes) always need their own authorization.
- **Verification names object, method, outcome and environment** (concurrent load included); a test name
  is not a run. Close-out: simplify when the change is large, review by size (S self-review · M `review`
  standard tier · L deep), per-commitment result, and an observation note that records skipped steps.
- **Evidence only, with provenance.** No guessing, no 望文生义 — every load-bearing claim cites code or a doc,
  marked evidence / 推断 / 假设; doubts are investigated by a subagent (`investigate` is the front door).
- **By size.** XS/S stay light; size is re-judged whenever scope grows; M requires a grill to convergence, two
  fresh-context lenses (falsifier + commitment coverage), `plan.md`, `facts.md`, ADRs and diagrams as earned; L splits first
  (`references/steps/split-isolate.md`).
- **Docs + KB are git-managed.** `dev_root` and the KB are each their **own repo** with autonomous **local**
  commits at every doc boundary, scoped to the acting card (`--card <project>/<NNN>`); `push` stays
  manual. An optional session-end hook sweeps leftovers per project:

  ```json
  {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 <path-to-skill>/tools/commit-data-repos.py"}]}]}}
  ```
- **Check after every edit.** `tools/workflow-status.py --check <project>/<NNN>` runs the lite subset
  (links · status field · progress cap · governance carriers · board ↔ `status` sync — each naming its
  `constraints.md` row in `--manifest`); the board and the viewer show a lite card as one cell derived from
  `design.md`'s `status`; `--trace` / `--digest` print 不适用 for it.
- **Retro improves the skill itself.** Friction is folded back into `lite.md` / `discuss.md`, recorded in
  `CHANGELOG.md` with the 体量行 by dimension (`constraints.md` Cap-1) plus the lite-face and whole-skill totals.

## Usage

`xg-dev-workflow new <slug>` opens a lite card by hand (directory, `design.md` from
`templates/design-lite.md`, board row); then draft, ask for go, execute, close out — all per
`references/steps/lite.md`. `investigate <topic>` is the single front door for any code investigation;
`diagnose <symptom>` for defect localization (repro loop first, fix via Prove-It); `review <target>` for
judging new or changed code and for the lite close-out; `improve <project> [<region>…]` for a read-only
deepening scan whose picks graduate via the roadmap; `learn <card>…` distills redo-input from existing
cards. `resume <slug>` / `park <slug>` continue or hand off a card; `check` runs the lite checks; `status`
renders the card view (`python3 tools/viewer.py` serves the same data as a browsable localhost HTML
viewer — board, doc/KB browsing, wikilink nav, per-card diff, recent commits, plus an optional co-launched
**gitweb companion**; needs `lighttpd`, disable with `--no-gitweb`); `retro` improves the workflow. The
legacy phase verbs (`requirement` / `design` / `detail` / `plan` / `test` / `change`) exist only for 存量
cards and are defined in `references/legacy/SKILL.md`.

See `SKILL.md` for the routing contract; `references/steps/lite.md` for the procedure; `CHANGELOG.md` for
how the skill evolved.
