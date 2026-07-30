# Step: improve (read-only deepening scan)

Authored inline; composes the `investigate` skeleton (KB-first, read-only, dev_root landing,
Receipts) + the M1 evidence discipline (`evidence.md`) + the adversarial-critic refutation
pattern. Probe methodology informed by the `improve-codebase-architecture` bare-run
observations — not a fork. Vocabulary: **deep module** = small interface hiding lots of
behaviour; **deletion test** = delete it mentally — complexity that vanishes marks a
pass-through, complexity reappearing across N callers earns its keep; **two-adapter rule** =
don't keep a seam/port with a single implementation (full vocabulary: the `codebase-design`
skill — link, don't restate).

Contract (design 013, ADR-0001): `improve <project> [<region>…]` — **read-only on product
code**; scan a bounded region for deepening candidates; every candidate carries evidence +
an independent refutation verdict; candidates conflicting with approved decisions are flagged
or suppressed; the report lands in dev_root; the gate is a **chat stop** (no ledger approval);
the **only exit is roadmap Next-up** — improve never creates a card.

## Procedure (five stages)

### 0. Region check
1. Resolve the project (`tools/resolve-project.py`); regions are repo-relative dirs (multiple OK).
2. A named region that doesn't exist → stop with the actual top-level dirs listed.
3. Count source files: `git ls-files -- <region…>` filtered to
   `.c .h .cc .cpp .go .py .ts .tsx .js .jsx .rs .java .sql .sh .pl`
   (non-git tree: `find` equivalent).
4. Count > **200** and no region given → **refuse** (print the count + top-level dirs, ask the
   human to bound the scan). Hard stop, never degrade to sampling — a sampled "whole-repo
   verdict" is false completeness.

### 1. Aggregate (all read-only)
- **KB orient** (xg-knowledge-lite Orient): project wiki section + `CONTEXT-MAP.md` +
  `architecture` + `*-invariants` + uncompiled-raw count → extract the domain vocabulary and
  scan priorities. Empty KB → continue, but the report header must note "no domain vocabulary —
  candidate naming may fall back to code identifiers".
- **Negative list** (read directly — no script dependency): every card's `adr/*.md` body
  (Status accepted/approved) + every `decisions.md` approved block (陈述 **and** `alt:` lines) +
  `roadmap.md`「Rejected / won't do」. Record per entry: card, id, one-line statement, source
  file. Cards without a ledger contribute via `adr/` only (two-regime history is accepted, never
  backfilled). No adr/ledger at all → empty list; the report header states the sources actually
  covered.
- **In-flight list**: `index.md` board rows with 整体状态 ∉ {done, dropped} + one Scope line from
  each card's `requirement.md`.

### 2. Scan (one agent, session model)
Dispatch one Explore-type agent over the bounded region. Its prompt must contain:
- the deep-module vocabulary gloss above + the KB domain vocabulary (name candidates in domain
  terms where they exist);
- the **five friction probes**: (1) understanding one concept requires bouncing across many
  small modules; (2) shallow modules — interface ≈ implementation (pass-throughs, thin
  wrappers); (3) pure functions extracted for testability while the real bugs live in their
  untested call orchestration; (4) tight coupling leaking across a seam; (5) parts untestable
  through their current interface;
- the **deletion test** as the filter (complexity concentrates → real candidate; reappears
  across callers → it earns its keep);
- M1: evidence must be file:func-level and actually read; negative results follow
  `evidence.md`「Negative-results」; candidates must not overlap; when in doubt, drop or mark
  Speculative — under-report beats padding;
- output: **≤8 candidates** in the candidate-card schema below (minus the 复核/核对 columns) +
  a **coverage statement** (what in the region was and wasn't read — no silent caps);
- report in Chinese, domain terms and code identifiers in English; no ASCII diagrams.
Agent failure or zero candidates → stop the run and say so in chat (no report file).
An over-large region blowing the agent's budget counts as failure — suggest a smaller region.

### 3. Refute (per candidate, `model: sonnet`)
One fresh-context agent per candidate, in parallel. Mandate: *read the actual call sites and
try to refute this candidate's shallow / pass-through / deletion-concentrates judgment.*
Verdict mapping (uncertain defaults to `weakened` — degrade, don't delete):
- `refuted` → drop to the report's 剔除候选 appendix (one line: title + refutation basis);
- `weakened` → recommendation strength drops one level (Strong → Worth exploring →
  Speculative), reason recorded in the 复核结论 column;
- `stands` → passes.
The orchestrator may overrule a verdict — the overrule reason lands in the 复核结论 column
(M6 calibration material for the sonnet assignment).

### 4. Conflict-match → report → gate → roadmap
1. **Conflict match**: for each candidate × negative-list entry, the orchestrator judges
   semantically (no deterministic text match). A **clear conflict** (candidate direction
   directly opposes an approved decision) → suppress into the appendix by default; keep it only
   when the friction justifies reopening, marked `contradicts <id> — <reopen reason>`.
   **Doubtful** → mark `possible-conflict <id>`, never suppress. Every mark links the decision
   id so the human can verify in one hop.
2. Render the report (template below, Markdown + Mermaid only) →
   `<project>/investigations/improve-<scope>-<YYYY-MM-DD>.md` (whole-repo scan: scope = project
   name; same-day rerun appends `-2`) → commit via `tools/commit-data-repos.py --project`.
3. **Chat gate** — receipts first (report path + commit + a candidate summary table), then STOP.
4. On the human's pick: one roadmap「Next up」line per chosen candidate —
   `- <title> — <one-line gain>(improve 候选,[报告](./investigations/<file>))` — then commit.
   No pick → the report stays archived, zero roadmap writes.
5. Log once per run: `log-usage.py log --skill xg-dev-workflow --action improve …`.
Write/commit/reply discipline: `investigate.md`「Receipts」. Report write failure → retry once,
then paste the content into chat (candidates must not be lost). Missing `roadmap.md` → create
it lazily from the template.

## Report template

Header: project · region(s) · file count · negative-list sources covered · KB vocabulary
present/absent. Then per candidate one card with the **fixed field order** (a missing column is
an M3 finding):

1. 标题 (verb-first) · 2. 涉及文件 · 3. friction 类型 (probe 1–5) · 4. file:func 证据 ·
5. deletion test 结论 · 6. 依赖分类 (in-process / local-substitutable / ports&adapters / mock) ·
7. 推荐强度 (Strong / Worth exploring / Speculative) · 8. 复核结论 (通过 / 降级+理由 / 见附录) ·
9. 负面清单核对 (无冲突 / possible-conflict+id / contradicts+id+reopen 理由)

Then: **在途卡提示节** (all active/drafting cards + one-line Scope each + judgment marks for
possibly-related ones — no automatic region matching) → **剔除候选附录** (refuted + suppressed,
one line each) → **Top recommendation** (one candidate, ≤3 sentences why). Mermaid for any
before/after structure worth drawing; prose stays in Chinese with English domain terms.

## Done when

- Region check enforced (refusal path exercised or region within bounds); negative list +
  in-flight list built with sources stated; ≤8 non-overlapping candidates each carrying all
  nine fields; refutation verdicts recorded; conflicts marked/suppressed with decision-id
  links; report committed; gate stopped with receipts; roadmap lines written only for the
  human's picks. Then run the omission check (M3).
