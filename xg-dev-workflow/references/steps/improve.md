# Step: improve — read-only deepening scan

Composes the `investigate` skeleton (KB-first, read-only, dev_root landing, receipts) + the evidence
rule + the fresh-context refutation pattern (`references/lenses.md`); probe methodology informed by
`improve-codebase-architecture` bare-run observations, not forked. Vocabulary: **deep module** = small
interface hiding lots of behavior · **deletion test** = delete it mentally — complexity that vanishes
marks a pass-through, complexity reappearing across N callers earns its keep · **two-adapter rule** =
don't keep a seam / port with a single implementation (full vocabulary: the `codebase-design` skill).

**Contract**: `improve <project> [<region>…]` — read-only on product code; scan a bounded region for
deepening candidates; every candidate carries evidence + an independent refutation verdict; candidates
conflicting with approved decisions are flagged or suppressed; the report lands in dev_root; the gate is
a **chat stop**; the **only exit is a roadmap Next-up line** — improve never creates a card.

## Procedure

### 0. Region check
Resolve the project (`tools/resolve-project.py`); regions are repo-relative dirs (several allowed); a
named region that doesn't exist → stop with the actual top-level dirs listed. Count source files
(`git ls-files -- <region…>` filtered to `.c .h .cc .cpp .go .py .ts .tsx .js .jsx .rs .java .sql .sh .pl`;
non-git: `find`). Count > **200** with no region given → **refuse** (print count + top-level dirs, ask for
a bound) — never degrade to sampling; a sampled whole-repo verdict is false completeness.

### 1. Aggregate (read-only)
- **KB orient**: the project's wiki section + `CONTEXT-MAP.md` + `architecture` + `*-invariants` +
  uncompiled-raw count → domain vocabulary and scan priorities; empty KB → continue, header notes "no
  domain vocabulary — candidate naming may fall back to code identifiers".
- **Negative list** (read directly): every card's accepted `adr/*.md` + each lite `design.md`'s 不做 list
  and rejected candidate rows + `roadmap.md`「Rejected / won't do」(存量 cards contribute their own
  decision carriers per `references/legacy/SKILL.md`). Record per entry: card · id · one-line statement ·
  source file; the header states the sources actually covered.
- **In-flight list**: board rows with 整体状态 ∉ {done, dropped} + one scope line from each card's summary.

### 2. Scan — one agent, session model (opus cap)
One Explore-type agent over the bounded region; its prompt carries: the vocabulary gloss + the KB
domain terms (name candidates in domain terms where they exist) · the **five friction probes** — (1)
understanding one concept bounces across many small modules; (2) shallow modules, interface ≈
implementation (pass-throughs, thin wrappers); (3) pure functions extracted for testability while the
real bugs live in their untested orchestration; (4) coupling leaking across a seam; (5) parts untestable
through their current interface · the deletion test as the filter · evidence at `file:func` level,
actually read; negatives query-scoped; candidates non-overlapping; when in doubt drop or mark
Speculative — under-report beats padding · output ≤8 candidates in the schema below (minus the 复核 /
核对 columns) + a **coverage statement** (what was and wasn't read — no silent caps); 依赖分类 uses four
categories glossed in the brief — **in-process** (pure compute, no I/O) · **local-substitutable** (a
local stand-in exists) · **ports&adapters** (own service across a network seam) · **mock** (true third
party) · report in Chinese, identifiers English, Mermaid only. Agent failure, zero candidates, or a
region blowing its budget → stop and say so in chat (no report file; suggest a smaller region).

### 3. Refute — one `model: sonnet` agent per candidate, in parallel
Mandate: read the actual call sites and try to refute this candidate's shallow / pass-through /
deletion-concentrates judgment; every verdict reports the call sites checked (`stands` included — the
adjudication and retro calibration need the basis). Mapping, uncertain → `weakened` (degrade, don't
delete): `refuted` → the 剔除候选 appendix (title + basis) · `weakened` → recommendation drops one level
(Strong → Worth exploring → Speculative), reason in 复核结论 · `stands` → passes. The orchestrator may
overrule — the reason lands in 复核结论. A refuter that dies leaves 复核未完成 and a forced Speculative,
never a drop and never a block.

### 4. Conflict-match → report → gate → roadmap
1. For each candidate × negative-list entry judge **semantically** (no text match): a clear conflict
   (direction opposes an approved decision) → suppress into the appendix unless the friction justifies
   reopening, marked `contradicts <id> — <reopen reason>`; doubtful → `possible-conflict <id>`, never
   suppressed. Every mark links the decision id.
2. Render the report (template below) → `<project>/investigations/improve-<scope>-<YYYY-MM-DD>.md`
   (whole-repo: scope = project; same-day rerun `-2`) → `tools/commit-data-repos.py --project`.
3. **Chat gate** — receipts first (path + commit + a candidate summary table), then STOP.
4. On the human's pick: one roadmap「Next up」line per chosen candidate —
   `- [ ] <title> — <one-line gain>(improve 候选,[报告](./investigations/<file>)) → card: —` — then
   commit; no pick → zero roadmap writes. Missing `roadmap.md` → create from the template.
5. Log once: `--action improve`. Write failure → retry once, then paste the content into chat.

## Report template

Header: project · region(s) · file count · negative-list sources covered · KB vocabulary present /
absent. Per candidate one card, **fixed field order**: 1 标题 (verb-first) · 2 涉及文件 · 3 friction 类型
(probe 1–5) · 4 file:func 证据 · 5 deletion test 结论 · 6 依赖分类 · 7 推荐强度 (Strong / Worth exploring /
Speculative) · 8 复核结论 (通过 / 降级+理由 / 见附录) · 9 负面清单核对 (无冲突 / possible-conflict+id /
contradicts+id+reopen 理由). Then **在途卡提示节** (active cards + one-line scope + judgment marks for
possibly related ones — no automatic region matching) → **剔除候选附录** (refuted + suppressed, one line
each) → **Top recommendation** (one candidate, ≤3 sentences). Mermaid for any before / after structure.

Done when: region check enforced; negative and in-flight lists built with sources stated; ≤8
non-overlapping candidates each with all nine fields; refutation verdicts recorded; conflicts marked or
suppressed with decision-id links; report committed; gate stopped with receipts; roadmap lines written
only for the human's picks.
