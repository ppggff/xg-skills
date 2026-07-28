---
name: xg-dev-workflow
description: "Design-centric dev workflow for code work. Use when the user opens or works a requirement ('new requirement' / '开个需求' / 'design this' / 'resume <slug>' / 'change the design' / 'workflow retro'); investigates code behavior ('investigate X' / '调查 X'); diagnoses a defect ('diagnose' / '定位这个 bug'); or reviews new/changed code ('review X' / 'review 这些改动')."
---

# xg-dev-workflow

A thin **orchestrator** for code work, split into five phases. Each phase produces one doc;
**everything lands in docs** so any fresh session resumes from files alone (no chat history needed).
The emphasis is **design** — not jumping from a requirement straight to an implementation plan, nor
from a frozen architecture straight to a task list.

```
需求 requirement.md → 设计 design.md (+adr/) → 详设 detail.md → 实现 plan.md / progress.md → 测试 test.md → 评审 review (M+)
   ■STOP confirm        ■STOP freeze on approve   ■STOP baseline    plan is mutable               results recorded   ■gate before done
```
(■STOP = halt for an explicit human go — the Stop-at-gate rule. 详设 is optional for XS/S. 评审 is a
close-out gate producing `notes/review-*.md`, not a sixth doc-phase.)

Reusable module knowledge does **not** live here — it lands in **xg-knowledge-lite** (`~/knowledge`
raw/wiki), referenced from these docs via `[[wiki/<project>/<slug>]]` wikilinks. This skill holds
only per-requirement docs.

**Writing style (all docs): plain prose, technical terms intact** (不变量 / 契约 / 幂等 stay); short
sentences. Parallel/enumerable content goes in nested lists (one point per bullet); paragraphs
are for reasoning that genuinely chains — a paragraph packing ≥3 parallel points gets
restructured as a list.

**Conventions (all docs)** — full rules in `references/doc-conventions.md` (gloss, links,
provenance/`F<n>` containers, reasoning-shown, reader-aware, short lines): **read it before
writing any workflow doc** (phase docs, investigation/review notes, KB 注记). Resident essentials:
- **Provenance** — load-bearing claims carry a marker: evidence-cited / 推断 (inferred) / 假设
  (assumption); `F<n>` fact blocks centralize them per container (card → `facts.md`).
- **KB cross-references keep the `[[wiki/<project>/<slug>]]` wikilink** — load-bearing for the
  KB's incremental recompile; don't swap it for a markdown link.
- **Diagrams — Mermaid preferred**; ASCII only for the trivial (rules: `references/diagram-gotchas.md`).
- **Fixed ID prefixes** (one letter, one meaning). Core, resident: `NNN` card dir · `ADR-NNNN`
  decisions · `R<n>` requirement 条目 (R is **reserved**) · `T<n>` plan tasks · `M1`–`M6` this
  skill's mechanisms. Full registry — `G`/`L`/`D`/`MS`/`P`/`F`, review `#<n>`, the symbol budget,
  module/part naming, and the downstream→upstream mapping rule — in `references/id-schemes.md`; a
  new scheme picks an unused letter and lands there.

## Stop-at-gate rule (READ FIRST — overrides momentum)

The **hard stops** are the decision-zone gates — 需求 confirm · 设计 freeze · 详设 baseline — plus the
**one-time execution authorization** after `plan.md`; each is a human decision. Past that
authorization there are no per-phase stops (「Two zones」).

- **One phase per invocation.** After producing the phase's doc, STOP — even if you could roll on,
  even if the prompt mentions later phases. Report the doc + the gate question, then wait. Chaining
  requires the human to invoke each verb, or to explicitly say "run straight through". (Exception:
  the human-opted, sizing-scoped gate mergers —「Requirement sizing」Gate merging.)
- **A bare topic with no verb** means **`new` + `requirement` only**, then STOP. "调查 / investigate /
  explore" means stop at understanding — never auto-advance to a chosen design.
- **Gate = an explicit human go, this turn** — prior approval doesn't carry forward. Produce the
  doc, ask, and do not create or edit the next phase's doc until then. Unsure which phase is wanted
  → ask, don't assume the pipeline.
- **The advance word is `go` — uniformly.** Phrase every advance ask around it, naming what it
  authorizes (「确认后回 go,进入设计」/「go = 授权执行区」), and treat the human's `go` (or an equally explicit
  equivalent in their own words) as the authorization; comments or praise without a go are feedback,
  not a go. Applies to every advance: phase gates, the execution authorization, continuing after a
  grill convergence verdict.
- **Ask with receipts — write first, then ask.** An advance ask (and any reply that closes a verb
  run) is made only after this round's artifacts are on disk, and it **names them**: doc paths + the
  dev_root commit — on a ledger card, also **the pending `decisions.md` rows being asked about**
  (the approve transcription cites this receipts commit). No receipts, no ask. This closes M3's trigger blind spot — M3 fires on doc edits,
  so an *omitted* write produces no edit and no check; the receipts requirement makes a missing
  write impossible to ask past.
- **Plan mode ≠ a gate substitute.** An ExitPlanMode approval only authorizes writing **this**
  phase's doc — not skipping it or jumping to implementation; the authoritative gate is the human
  approving that doc.

## Two zones: human-decision vs Claude-execution (one line, two meanings)

The phases split at the **设计/详设 freeze**, and that line is both the **decision** boundary and the
**audience** boundary — they coincide on purpose:

- **Decision zone — 需求 · 设计 · 详设 (+ADRs).** Every binding gate lives here: the human makes the
  choices that are expensive to reverse. Docs are **human-first** — written to be read and approved:
  prose, rationale, alternatives, reviewable in one pass.
- **Execution zone — 实现 · 测试 · 评审.** Post-freeze choices are implementation-level — **Claude owns
  them** and runs the zone autonomously on the one "go" given after `plan.md` (the autonomy
  handoff): implement → test → close-out review report, **no per-task or per-phase gate**. Docs are
  **Claude-first** — terse, structured, link-don't-restate, optimized for execution + session
  resume, not for a human read-through.
- **The human re-enters at exactly three artifacts** — `log.md` (the audit trail; resume never
  reads it), the 评审 review report (its 修复决策表 is a human decision), and a **proposed
  `decisions.md` row** Claude escalates from the execution zone (design fork → M2 — the row
  persists the fork + options; blocker and push requests stay chat-level; commits are
  autonomous, push is gated).

## Ledger (决策账本) — the gate currency

Gate approval's unit is the **decision, not the document**: each card's `decisions.md` is the
**single source of approval status** for every human-judgment decision (block format, rewritable-
views mechanics: `templates/decisions.md` 头注; digest & approve transcription: `gate-digest.md`).

- **States**: proposed / approved / superseded / retired — the only enumeration; freeze (需求/设计)
  and baseline (详设) are **binding forces** approved carries by level, never state words.
- **Gates approve rows**; Claude transcribes on go and **never self-approves**. Doc status is
  **derived**: `confirmed`/`frozen`/`baseline` ⇔ that level's rows all approved.
- **Changing an approved decision = M2 reopen** (`change.md`). Cards without a ledger (pre-010)
  keep the old document-gate semantics **end to end**.

## Layout (requirement-centric)

```
<dev_root>/                         # from config dev_root: (default ~/dev-workflow)
  index.md                         # cross-project index
  <project>/                        # == xg-knowledge-lite project name
    index.md                       # per-project kanban board (cards: Phase/整体状态/Deps)
    roadmap.md                     # project plan: next-up/themes/someday/rejected — M3 keeps it fed
    investigations/                # standalone investigations: <slug>.md (no investigation- prefix),
                                    #   or <topic>/ campaign dir for a large multi-file investigation
    reviews/                        # standalone review reports
    notes/                         # project-level scratch — event artifacts dated, living docs date-free
    legacy/                        # pre-workflow archive (read-only; never linked as canonical)
    NNN-requirement-slug/           # created lazily — each doc appears when first needed
      requirement.md               # 需求 (created by `new`)
      decisions.md                 # 决策账本 — approval-status single source (lazily, first
                                    #   proposed row; gates approve its rows: SKILL.md「Ledger」)
      facts.md                     # 卡级事实层 F<n> (lazily; cited as [F<n>] from phase docs)
      design.md                    # 设计 (概设/HLD) — FROZEN once approved
      adr/NNNN-slug.md             # decision records (adr/ created on first ADR)
      detail.md                    # 详设 (LLD) — BASELINE; optional, skip for XS/S
      plan.md                      # 实现 plan — MUTABLE
      progress.md                  # current-state snapshot (session resume); pruned, not a log
      log.md                       # append-only change log (what + why); never edited/pruned
      test.md                      # 测试
      notes/                       # requirement-specific scratch. Naming: event artifacts
                                    #   (review-/retro-) carry YYYY-MM-DD; living docs stay date-free
```

**Project-global docs — split by nature.** **Planning → dev_root**: `<project>/roadmap.md` (next-up
/ themes / someday / rejected; items graduate to cards via `new`). **System knowledge → KB**,
referenced one-way via `[[wiki/…]]`: the **architecture overview**
(`[[wiki/<project>/architecture]]` — linked from each card's `design.md` and refreshed as-built when
a design freezes) and per-subsystem **invariant ledgers** (loaded/replayed by the
adversarial-critic). The KB never links back into dev_root.

## Config & project resolution (shared with xg-knowledge-lite)

Same config file: `~/.config/xg-knowledge-wiki/config.yaml`.

- `dev_root:` → workflow docs root. Resolution: (1) `--root <path>`; (2) config `dev_root:`; (3)
  default `~/dev-workflow`. Never auto-create the config.
- `projects:` → the **same** map xg-knowledge-lite uses. Resolve cwd→project with
  `tools/resolve-project.py [<cwd>]`; on miss, ask once and register via xg-knowledge-lite's
  `tools/register-project.py <name> <path>`. Never auto-pick `common`.

## Versioning the docs (dev_root git)

`dev_root` is its **own git repo** (all projects; separate from the product-code repo and the KB
repo), lazily initialized on the first commit — `tools/commit-data-repos.py` does init-if-needed +
commit-if-dirty.

- **Commit at each gate / doc boundary** (semantic, not per keystroke): when a verb finishes writing
  — `new`, `requirement` (confirmed), `design` (frozen), `detail` (baseline), `plan`, each implement
  task's `progress.md` update, `test`, `review`, a `change`/M2 entry, investigate/diagnose notes,
  each grill-round verdict (checkpoint). Run M3 first, then commit. Message: `<project>/NNN-slug:
  <verb> — <one line>`.
- **Gate commits are scoped to the acting project**: `tools/commit-data-repos.py --project
  <name>` (or, when running git directly, an equivalently scoped `add`/`commit` in both repos) —
  a parallel session's own uncommitted docs in another project must never ride along in this
  commit (the un-scoped `add -A` this replaced could pull them in).
- **Autonomous local commit; `push` stays human-gated;** history append-only (no amend/rebase).
- An implement task yields **two** commits — product code → its own repo, docs → the dev_root repo.
  Don't cross them.
- Optional safety net: a session-end hook runs `tools/commit-data-repos.py` to sweep uncommitted
  docs (README).

## The five phases (contracts) + the close-out review gate

Each phase is a **contract** — input, output doc, gate — independent of which skill implements it
(see Step binding). Templates in `references/templates/`, per-step procedures in
`references/steps/`.

**Requirement sizing (XS/S vs M+).** A human judgment, reusing the task-scope vocabulary (XS · S · M
· L) at requirement level: **XS/S** = structure-light, ~one vertical slice, no new module/contract →
may skip **详设** and the **评审** close-out (record the skip). **M+** = multi-slice, or
introduces/changes a module/contract → does 详设 when structural, and **must** pass 评审 before `done`.
Judged at design time, not a board column; M3's done-time signal is "a review doc exists **or** an
explicit `XS/S — review skipped` note does".

**Gate merging (sizing-scoped, human opt-in).** **XS**: 需求+设计 may run in one invocation with
**one combined gate** — Claude offers it when the ask is plainly XS; the human's yes is the
standing go for the combined run; the docs stay separate files and the digest presents
requirement-level decisions before design-level ones. **M**: the 详设 baseline gate may merge with
the execution authorization (detail.md + plan.md presented together, one go covers both). The
default stays one gate per phase; a merged run that outgrows its sizing (the XS turns out M+)
splits back — stop at the earlier gate as usual.

### 1. 需求 Requirement → `requirement.md`
Input: a raw ask. **Elicited interactively, not written in one shot** — the grill loop (`grill.md`)
interleaved with code understanding (M5/M1): surface assumptions first and let the human correct
them; understand the **essence** behind the ask (it may be layered, diverge from its wording, map to
the design non-1:1) — solve the real problem, don't transcribe the words. Output sections:
**Context** · **需求条目** (atomic items, each one statement with a stable **`R-id`** — the
**traceability spine** every later doc references) · **Scope** (in/out + 初步影响面) · **Constraints** ·
**Effect** (testable success criteria, each citing its `R-id`) · **Future** · **Open questions**.
GATE: STOP for explicit confirm — the confirm approves the requirement-level ledger rows
(「Ledger」). Step: `references/steps/requirement.md`.

### 2. 设计 Design → `design.md` + `adr/` (the emphasis)
Understand first (M5), then design **at module altitude in abstraction layers**: weigh **multiple
approaches by trade-off** (方案优先, spanning hack / 补丁 / 推翻重来 — debt is a conscious, recorded choice),
prefer the **simplest reliable** design (简单可靠 > 精致复杂); express modules / responsibilities /
boundaries / contracts, with concrete code deferred to detail/plan, and **required diagrams**
(module-interaction + data-flow). Output: the chosen approach grounded in evidence + alternatives
considered + how it meets scope/constraints/effect **traced by `R-id`** + a **影响面 (impact surface)**
analysis (changed modules, callers & downstream consumers, compat/ABI surface, cross-card ripples,
behaviors to re-verify). **ADRs** for decisions that are hard-to-reverse, surprising, and a real
trade-off. Stress-test via grilling. GATE: STOP; **on approval `design.md` is FROZEN** — meaning
its referenced ledger rows are all approved (「Ledger」); thereafter those decisions change only
through M2 (the synthesis prose stays rewritable). Steps: `references/steps/design-grill.md`, `references/steps/adr.md`.

### 3. 详设 Detailed design → `detail.md` (LLD — optional for XS/S)
Lowers the frozen architecture to **concrete structures with rationale** — what `design.md` deferred
and `plan.md` shouldn't have to invent. Sections: **数据结构** (each with a one-line why) · **关键机制/算法**
(trigger → steps → locking/transaction → error & edge handling → idempotency point) · **代码级接口**
(signatures, actual SQL) · **边界与错误矩阵** · **可追溯** (item ↔ design module/contract ↔ R-id). Division of
labour with ADRs: the ADR records the hard-to-reverse decision + alternatives; `detail.md` holds the
full concrete spec, referencing those ADRs and filling the small-but-load-bearing choices.
Ledger-worthy choices get `S<n>` ids (「Ledger」). GATE
(**baseline, not freeze**): STOP for human review — approving the detail-level rows gives them
baseline force; afterwards it may change as implementation
reality bites — each change adds a dated note; a change implicating the *architecture* routes
through M2. Step: `references/steps/detail.md`.

### 4. 实现 Implement → `plan.md` (mutable) + `progress.md`
`plan.md` = vertical-slice task breakdown: each task tags the **`R-id`(s) it implements**;
acceptance is a **binary** walk (`[x]`/`[!]`/`[ ]`, no subjective `[x]`). It implements the frozen
design + `detail.md` and **may change freely** — but deleting / merging / deferring a task, or
invalidating an `[x]`, is logged to `log.md` (only routine refinement is silent, M2 case B). The
phase runs **autonomously** per「Two zones」; pause only on a design/requirement fork (→ M2), a real
blocker, or a push request. Commit after each completed task and each review fix, one concern per
commit (implement's Commit cadence). `progress.md` = the session-resume snapshot (M4); each
finished slice also appends its one-line entry to `test.md`'s Unit registry (seeded at plan
time — see 测试). Per-slice
testing runs in one of two modes, chosen by the project's test-execution policy and recorded in
`progress.md`: **TDD** (test-first red-green) or **test-after** (write/describe the test, defer the
run) — both vertical, never all-code-then-all-tests. The phase ends with one behavior-preserving
**simplify sweep** over the whole change (implement.md; XS/S may skip). Steps:
`references/steps/plan.md`, `references/steps/implement.md`.

### 5. 测试 Test → `test.md`
**Skeleton-first, filled incrementally** — `test.md` is **seeded at plan time** (coverage table
from the design's 验证策略, 回归 rows from 影响面) and the Unit registry grows one line per
implement slice; this phase closes it out rather than reconstructing it. Close coverage (**by `R-id`** +
every module interface op/invariant), add the tests that span slices (integration / 跨 part 联调 /
manual / E2E), balance the pyramid, run the full suite (or describe the commands for "describe,
don't run"), record a binary acceptance walk. A bug found here → **Prove-It** (failing test first,
fix in an 实现 slice). Step: `references/steps/test.md`.

### 6. 评审 Close-out review (M+, gate) → `notes/review-*.md`
After 测试, before `done`: run the `review` verb on the whole change. Sizing + skip rule:「Requirement
sizing」. Step: `references/steps/review.md`.

## 拆分与隔离 (split & isolate) — 可选叠加层

把工作拆成独立部分、各自推进、最后收口。两种粒度，互相独立，都可选（够小就不拆）：
**A — 设计内 part 化**（**part** = 作为独立单元实现+测试的命名 module 块，**seam** = part 间
边界，其契约随设计冻结；part 是贯穿 design→plan→test→progress 的可选分组轴；seam 契约被联调
证伪 = 架构级变更走 M2）；**B — 需求级拆分** = 多 **card** + 每项目 `index.md` 看板
（Phase + **整体状态** + Deps）。**A↔B 判定**——满足任一即升 B：(a) 独立上线/发布时间线；
(b) 能单独交付并产生价值；(c) 不同 reviewer/负责人；(d) 一部分设计能独立冻结而另一部分还在
drafting。字段级机制（part 轴各文档字段、看板两轴与单调约束、canonical 术语表、card-还是-雾判定）：
`references/split-isolate.md`。

## Six cross-cutting mechanisms

- **M1 Evidence** — no guessing, no 望文生义. Every non-trivial claim cites code (`func()` in `file.c`,
  no line numbers) or a doc/source. Uncertainty → dispatch an Explore subagent to investigate;
  capture reusable findings to the KB. `references/steps/evidence.md`.
- **M2 Change management** — reopening an approved decision is **gated at entry** (human-initiated,
  or Claude escalates the fork as a proposed ledger row and waits) → **修改列表 first** (affected
  closure: reverse depends-on + trace ripple; human confirms, zero writes before) → **propagate
  along the spine, mode-specifically (追加/变更/撤销) and scoped** — never a wholesale regenerate →
  re-approve = the 评审会 over the new proposed rows. Detail-only changes ride baseline force
  (dated note); pure implementation reality → edit `plan.md` freely. Every change + why →
  `log.md`. Full flow: `references/steps/change.md`.
- **M3 Omission check** — after **any** doc edit: links resolve; `index.md` rows current;
  requirement↔design↔detail↔plan↔test consistent; terminology canonical (one term per concept,
  matching its KB concept); on a ledger card run `workflow-status.py --check` (the deterministic
  ledger subset — id integrity, derived-status mappings, cycles; exit 1 = findings); reusable
  knowledge captured to the KB via xg-knowledge-lite Write and
  compiled — or explicitly noted as deferred. `references/steps/omission-check.md`.
- **M4 Session continuity** — `progress.md` = pruned current-state snapshot, **self-sufficient for
  resume**; `log.md` = append-only why-history, **never on the resume path**. Never rebuild from
  chat history. Keep a decision-zone grill in one unbroken window (don't compact mid-grill); in the
  execution zone prefer `resume` in a fresh session over pushing a degraded one.
  `references/steps/resume.md`.
- **M5 Code understanding** — concept-first, layered: query xg-knowledge-lite first, then read-only
  exploration (Plan Mode / Explore subagent). The deliverable is the logical/causal analysis
  (`doc-conventions.md`「Reasoning shown」), not a grep-hit list. Existing-code questions enter through
  `investigate`; defect localization through `diagnose`; judging new/changed code → `review`.
  `references/steps/understand.md`.
- **M6 Retro** — review friction, land fixes into this skill, the project CLAUDE.md, or the KB; mine
  the usage log (`tools/log-usage.py report`). A behavior-changing retro records a dated entry in
  `CHANGELOG.md` + a commit. `references/steps/retro.md`.

## Subagent model assignment (cost)

Checklist / gather / verification-driven subagent work defaults to the cheaper model (Agent tool
`model: sonnet`); inference-heavy analysis, adjudication, and decisions stay on the session model.
Safe because the orchestrator re-derives / adjudicates (M1; review step 5) — a cheaper finder costs
recall at worst. Corollaries: **deterministic checks are scripted, not delegated**; every downgrade
sits under M6 calibration — a sonnet dispatch whose findings repeatedly die in adjudication gets its
downgrade revoked. Per-lens application: `review.md` step 4.

**Session-model tiering follows the two zones.** Decision-zone gates deserve the strong session
model; the execution zone runs well on a cheaper one — the plan gate digest reminds the human to
optionally switch `/model sonnet` + `/advisor opus` after go (the skill cannot switch models
itself; a fresh session via `resume` makes the switch free — prompt caches are per-model). The
tradeoff is explicit: with a cheap session model the 评审 adjudication also runs on it
(advisor-assisted); like every downgrade this sits under M6 calibration — weak adjudication
verdicts revoke it.

## Verbs

Invoke as `xg-dev-workflow <verb> [args] [use:<skill>]`.

- `new <slug>` — resolve project + next `NNN` (zero-padded per project — scan the project dir for
  the highest, increment), scaffold from templates, register project if missing, add an `index.md`
  card row (初始整体状态 `todo`); a roadmap-sourced slug is marked graduated there; an ask born from a
  tracker issue records it in `requirement.md` frontmatter `issue:` (the card↔issue anchor;
  `progress.md` frontmatter carries the repo/branch/MR/merged anchors + an `issue:` mirror).
  **Create files lazily**: `requirement.md` now; each later doc when its phase starts; `progress.md`
  on first need (a mid-grill checkpoint may create it early); `adr/` on the first ADR.
- `requirement` | `design` | `detail` | `plan` | `test` — advance **exactly one** phase, then stop
  at its gate (Stop-at-gate). Past the `plan` gate the zone flows autonomously (「Two zones」) — you
  normally don't invoke `test` by hand.
- `investigate <topic>` — **the front door for any code-behavior question** (feasibility,
  runtime/concurrency, "调查 X"). KB-first, full M1 discipline; branches on context — active
  requirement → it is that requirement's design step; standalone → findings to the KB. Read-only on
  product code (an empirical question may run a throwaway **spike**). Step:
  `references/steps/investigate.md`.
- `diagnose <symptom>` — **the front door for defect localization** (bug, crash, perf regression):
  feedback-loop-first — a red-capable repro loop before any theory; the fix lands via Prove-It.
  Branches like investigate (active card → the fix is an 实现 slice; standalone → propose the fix and
  wait). Step: `references/steps/diagnose.md`.
- `review <target>` — **the front door for judging new/changed code** (commit range, branch, PR, or
  current diff): KB context pack + **stake-tiered dispatch** (light: orchestrator-only · standard:
  three axis agents · deep: staged lens fan-out + different-model sweep), every finding adjudicated
  against actual code; report ends with a 修复决策表 and lands in dev_root (requirement
  `notes/review-*.md`, or standalone `<project>/reviews/`). Also the M+ close-out gate. Read-only.
  Step: `references/steps/review.md`.
- `change` — drive the M2 flow.
- `resume [<slug>]` — rebuild state from `progress.md` + the phase docs (M4).
- `check [<slug>]` — run the M3 check.
- `status [<project> …]` — the card view: every card's pipeline position, board 整体状态/Deps, progress
  Now/Next/Blockers, and the gate-derived next step; read-only, computed on demand by
  `tools/workflow-status.py` (`--json` for scripts; `--trace <project>/<card>` renders the derived
  R→design→task→test→commit trace matrix from the designated mapping fields, flagging unimplemented
  / uncovered R-ids). `tools/viewer.py` serves the same data as a browsable localhost HTML view,
  with an optional gitweb companion for the project repos' code — details in README.
- `retro` — review and enhance the skill/docs (M6).

Any phase verb accepts a `use:<skill>` suffix to override that step's implementation for this run.

## Usage logging (self-feedback)

Logging rule lives in `~/.claude/CLAUDE.md` (Skill Usage Logging). This skill's `--action` = the
verb just run
(`new`/`requirement`/`design`/`detail`/`plan`/`test`/`investigate`/`diagnose`/`review`/`change`/`resume`/`check`/`retro`/`status`
— `status` only as a deliberate standalone view). Exceptions: an `investigate` inside an active
requirement logs `design` (it is that requirement's design step); implement-phase task work logs
`plan` (one record per task/checkpoint). **One event = one record:** a KB write inside an
`investigate`/`diagnose`/`review` run is covered by that record — only standalone KB work logs under
xg-knowledge-lite.

## Step binding (vendor + runtime override)

Each step resolves to one implementation, by priority: (1) **runtime override** — `use:<skill>` on
the verb, or a persisted `workflow.bindings:` step→skill entry in config; (2) **vendored default** —
`references/steps/<step>.md`, a forked copy of a source skill's procedure (ours, editable anytime);
(3) **inline** — steps with no third-party source. Rebind or edit the vendored file to change
behavior; the **contract never changes**, only the implementation behind it. Fork origins:
`references/provenance.md`.

## References

- `references/templates/` — the twelve doc templates (`requirement`, `design`, `adr`, `detail`,
  `plan`, `progress`, `log`, `test`, `index`, `roadmap`, `decisions`, `facts`).
- `references/steps/` — the per-step procedures, plus shared mechanisms referenced by multiple
  steps.
- `references/steps/grill.md` — shared interactive elicitation (requirement + design-grill):
  one-question-at-a-time protocol + grill-log + rollback (supersede discipline) + convergence
  auto-verdict; resume can continue a grill mid-phase.
- `references/steps/adversarial-critic.md` — shared sharp-cut finder (fresh-context three-lens
  critic + invariant-ledger replay + standing rules); used by requirement, design-grill, and review.
- `references/steps/gate-digest.md` — shared decision-card presentation for every decision-zone
  gate ask (comprehension-first cards + the 判断分工 split — 已验证(勿复核) / 待你判 with
  stakes — + open questions before the go ask; decision-object references self-contained).
- `references/split-isolate.md` — 拆分与隔离 field-level mechanics.
- `references/provenance.md` — what each vendored step was forked from.
- `references/id-schemes.md` — the full ID-prefix registry (SKILL.md keeps only the core five).
- `references/diagram-gotchas.md` — Mermaid pitfalls + ASCII CJK-width alignment (design diagrams).
- `references/frontend-testing.md` — browser + mobile real-device testing (UI-facing slices only).
- `references/steps/review-deep.md` — the `review` verb's deep-tier continuation (lens fan-out
  menu, model-diversity sweep, saturation stop-rule); read when running a deep review.
- `references/simplify-checks.md` — the two reuse/cohesion checks shared by implement's simplify
  sweep and review's Standards axis (single source).
- `references/smell-catalog.md` — Fowler code-smell names (leading words) for the review quality
  lens; the no-repo-standard baseline.
- **`codebase-design`** (external skill, referenced not vendored) — deep-module vocabulary +
  Design-It-Twice (design-grill 方案优先) + dependency-categories→test-strategy (test) + the deletion
  test (design-grill, implement).
- `tools/resolve-project.py` — cwd→project and `--dev-root` resolution (reads the shared config).
