---
name: xg-dev-workflow
description: "Design-centric dev workflow for code work. Use when the user opens or works a requirement ('new requirement' / '开个需求' / 'design this' / 'resume <slug>' / 'change the design' / 'workflow retro'); parks a session before leaving ('park <slug>' / '交接给新 session' / '收工离场'); investigates code behavior ('investigate X' / '调查 X'); diagnoses a defect ('diagnose' / '定位这个 bug'); reviews new/changed code ('review X' / 'review 这些改动'); or scans a region for deepening opportunities ('improve X' / '架构巡检' / '找 deepening 候选')."
---

# xg-dev-workflow

A thin **orchestrator** for code work, split into five phases. Each phase produces one doc;
**everything lands in docs** so any fresh session resumes from files alone (no chat history
needed). The emphasis is **design** — never straight from requirement to plan.

```
需求 requirement.md → 设计 design.md (+adr/) → 详设 detail.md → 实现 plan.md / progress.md → 测试 test.md → 评审 review (M+)
   ■STOP confirm        ■STOP freeze on approve   ■STOP baseline    plan is mutable               results recorded   ■gate before done
```
(■STOP = human gate — the Stop-at-gate rule; 详设 optional for XS/S; 评审 = close-out gate
producing `notes/review-*.md`, not a sixth doc-phase.)

Reusable module knowledge does **not** live here — it lands in **xg-knowledge-lite** (`~/knowledge`
raw/wiki), referenced via `[[wiki/<project>/<slug>]]` wikilinks; this skill holds only
per-requirement docs.

**Writing style (all docs): plain prose, technical terms intact** (不变量 / 契约 / 幂等 stay); short
sentences. Parallel/enumerable content goes in nested lists (one point per bullet); paragraphs
are for reasoning that genuinely chains — a paragraph packing ≥3 parallel points gets
restructured as a list.

**Conventions (all docs)** — full rules split core + supplement: `references/conventions-core.md`
(shared with xg-knowledge-lite, byte-identical: style/structure, gloss, provenance marking,
diagrams, wikilink form) + `references/doc-conventions.md` (workflow supplement: links, `F<n>`
containers, reasoning-shown, reader-aware). **Read both before writing any workflow doc**
(phase docs, investigation/review notes, KB 注记). Resident essentials:
- **Provenance** — load-bearing claims carry a marker: evidence-cited / 推断 (inferred) / 假设
  (assumption); `F<n>` fact blocks centralize them per container (card → `facts.md`).
- **KB cross-references keep the `[[wiki/<project>/<slug>]]` wikilink** — load-bearing for the
  KB's incremental recompile; don't swap it for a markdown link.
- **Diagrams — Mermaid preferred**; ASCII only for the trivial or what Mermaid can't express
  (rules: `references/diagram-gotchas.md`).
- **Fixed ID prefixes** (one letter, one meaning). Core, resident: `NNN` card dir · `ADR-NNNN`
  decisions · `R<n>` requirement 条目 (R is **reserved**) · `T<n>` plan tasks · `M1`–`M6` this
  skill's mechanisms. Full registry — `G`/`L`/`D`/`MS`/`P`/`F`, review `#<n>`, the symbol budget,
  module/part naming, and the downstream→upstream mapping rule — in `references/id-schemes.md`; a
  new scheme picks an unused letter and lands there.

## Stop-at-gate rule (READ FIRST — overrides momentum)

The **hard stops** are the decision-zone gates — 需求 confirm · 设计 freeze · 详设 baseline — plus the
**one-time execution authorization** after `plan.md`; each is a human decision. Past that
authorization there are no per-phase stops (「Two zones」).

- **One phase per invocation.** After producing the phase's doc, STOP — even if the prompt mentions
  later phases. Report the doc + the gate question, then wait. Chaining requires the human to invoke
  each verb or explicitly say "run straight through". (Exception: the human-opted, sizing-scoped
  gate mergers —「Requirement sizing」Gate merging.)
- **A bare topic with no verb** = `new` + `requirement` only, then STOP; 调查/investigate/explore
  stops at understanding — never auto-advance to a chosen design.
- **Gate = an explicit human go, this turn** — prior approval doesn't carry forward. Produce the
  doc, ask, and do not create or edit the next phase's doc until then. Unsure which phase is wanted
  → ask, don't assume the pipeline.
- **The advance word is `go` — uniformly.** Phrase every advance ask around it, naming what it
  authorizes (「确认后回 go,进入设计」/「go = 授权执行区」); the human's `go` — or an equally
  explicit equivalent in their own words — is the authorization; comments or praise without one
  are feedback, not a go. Applies to every advance: phase gates, the execution authorization,
  continuing after a grill convergence verdict.
- **Ask with receipts — write first, then ask.** An advance ask (and any reply that closes a verb
  run) is made only after this round's artifacts are on disk, and it **names them**: doc paths + the
  dev_root commit — on a ledger card, also **the pending `decisions.md` rows being asked about**
  (the approve transcription cites this receipts commit); on a doc-gate card, the doc itself is
  the receipt and the go lands as its Change log gate line (`gate-digest.md`「Doc-gate cards」).
  No receipts, no ask (closes M3's trigger
  blind spot: an omitted write produces no doc edit for M3 to catch).
- **Plan mode ≠ a gate substitute.** An ExitPlanMode approval only authorizes writing **this**
  phase's doc; the authoritative gate is the human approving that doc.

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
  `decisions.md` row** Claude escalates from any post-freeze phase (design fork or split
  proposal → M2; on a doc-gate card the escalation carrier is the target doc's「提议变更」
  section + a `progress.md` pointer instead; blockers and
  push requests stay chat-level; commits autonomous, push gated).

## Ledger (决策账本) — the gate currency

Gate approval's unit is the **decision, not the document**: each card's `decisions.md` is the
**single source of approval status** for every human-judgment decision (mechanics:
`templates/decisions.md` 头注; digest & approve transcription: `gate-digest.md`).

- **States**: proposed / approved / superseded / retired — the only enumeration; freeze (需求/设计)
  and baseline (详设) are **binding forces** approved carries by level, never state words.
- **Gates approve rows**; Claude transcribes on go and **never self-approves**. Doc status is
  **derived** — `confirmed`/`frozen`/`baseline` ⇔ that level's rows all approved (the
  **derived-status rule**).
- **Changing an approved decision = M2 reopen** (`change.md`).
- **Governance mode (017)**: the ledger machinery above is the **`governance: ledger`** (M+)
  mode. **`doc-gate`** (XS/S) cards run document-level gates instead — no ledger/facts files
  and no transcription loop (the digest itself **scales down**, it doesn't vanish —
  gate-digest.md「Doc-gate cards」); gate = doc + confirm + commit, audit anchor = the doc's
  Change log gate line
  (`gate-digest.md`「Doc-gate cards」). Mode judged by the two-level cascade: frontmatter field
  first (pre-filled at `new`, human-ratified at the 需求 gate); **no field = legacy** — pre-017
  cards keep their original semantics (pre-010 document-gate, 010–016 ledger) end to end.
  Upgrading doc-gate→ledger is a one-time explicit M2 action, past decisions not backfilled.

## Layout (requirement-centric)

```
<dev_root>/                         # from config dev_root: (default ~/dev-workflow)
  index.md                         # cross-project index
  <project>/                        # == xg-knowledge-lite project name
    index.md                       # per-project kanban board (cards: Phase/整体状态/Deps)
    roadmap.md                     # project plan: next-up/themes/someday/rejected — M3 keeps it fed
    investigations/                # standalone investigations: <slug>.md (no investigation- prefix)
                                    #   or <topic>/ campaign dir
    reviews/                        # standalone review reports
    notes/                         # project-level scratch — event artifacts dated, living docs date-free
    legacy/                        # pre-workflow archive (read-only; never linked as canonical)
    NNN-requirement-slug/           # created lazily — each doc appears when first needed
      requirement.md               # 需求 (created by `new`)
      decisions.md                 # 决策账本 — approval-status single source (SKILL.md「Ledger」)
      facts.md                     # 卡级事实层 F<n> (lazily; cited as [F<n>] from phase docs)
      design.md                    # 设计 (概设/HLD) — FROZEN once approved
      adr/NNNN-slug.md             # decision records (adr/ created on first ADR)
      detail.md                    # 详设 (LLD) — BASELINE; optional, skip for XS/S
      plan.md                      # 实现 plan — MUTABLE
      progress.md                  # current-state snapshot (session resume); pruned, not a log
      log.md                       # append-only change log (what + why); never edited/pruned
      test.md                      # 测试
      notes/                       # requirement-specific scratch — same naming rule as project notes/
```

**Project-global docs — split by nature.** **Planning → dev_root**: `<project>/roadmap.md`
(next-up / themes / someday / rejected; items graduate to cards via `new`). **System knowledge →
KB**, one-way via `[[wiki/…]]`: the **architecture overview** (`[[wiki/<project>/architecture]]`,
refreshed as-built when a design freezes) and per-subsystem **invariant ledgers** (replayed by the
adversarial-critic). The KB never links back into dev_root.

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
- **Gate commits are scoped to the acting project**: `tools/commit-data-repos.py --project <name>`
  (or an equivalently scoped `add`/`commit`) — a parallel session's uncommitted docs in another
  project must never ride along.
- **Autonomous local commit; `push` stays human-gated;** history append-only (no amend/rebase).
- An implement task yields **two** commits — product code → its own repo, docs → the dev_root repo.
  Don't cross them.
- Optional safety net: a session-end hook sweeps uncommitted docs via `commit-data-repos.py` (README).

## The five phases (contracts) + the close-out review gate

Each phase is a **contract** — input, output doc, gate — independent of which skill implements it
(see Step binding). Templates in `references/templates/`, per-step procedures in
`references/steps/`.

**Requirement sizing (XS/S vs M+).** A human judgment, reusing the task-scope vocabulary (XS · S · M
· L) at requirement level: **XS/S** = structure-light, ~one vertical slice, no new module/contract →
may skip **详设** and the **评审** close-out (record the skip). **M+** = multi-slice, or
introduces/changes a module/contract → does 详设 when structural, and **must** pass 评审 before `done`.
The 详设/评审 skips stay judged at design time, not a board column; M3's done-time signal: a review
doc **or** an explicit `XS/S — review skipped` note. **The governance mode (017) moves one sizing
consequence earlier**: `new` pre-fills `governance:` from the apparent sizing and the 需求 gate
ratifies it — a card that outgrows its mode later upgrades via M2 (「Ledger」Governance mode).

**Gate merging (sizing-scoped, human opt-in).** **XS**: 需求+设计 may run in one invocation with
**one combined gate** (offered when the ask is plainly XS; docs stay separate files;
requirement-level cards first). **M**: the 详设 baseline gate may merge with the execution
authorization (one go covers both). Default = one gate per phase; a merged run that outgrows its
sizing splits back — stop at the earlier gate as usual.

### 1. 需求 Requirement → `requirement.md`
Input: a raw ask. **Elicited interactively, not written in one shot** — the grill loop (`grill.md`)
interleaved with code understanding (M5/M1): surface assumptions, let the human correct them,
solve the real problem behind the wording. Core output: **需求条目** — atomic items with stable
**`R-id`**s, the **traceability spine** every later doc references — plus Scope / Constraints /
**Effect** (testable criteria citing their `R-id`) per the template.
GATE: STOP for explicit confirm — the confirm approves the requirement-level ledger rows
(「Ledger」). Step: `references/steps/requirement.md`.

### 2. 设计 Design → `design.md` + `adr/` (the emphasis)
Understand first (M5), then design **at module altitude in abstraction layers**: weigh **multiple
approaches by trade-off** (方案优先, spanning hack / 补丁 / 推翻重来 — debt is a conscious, recorded
choice), prefer the **simplest reliable** design (简单可靠 > 精致复杂); modules / responsibilities /
boundaries / contracts, concrete code deferred to detail/plan, **required diagrams**
(module-interaction + data-flow). Output: chosen approach + alternatives + how-it-meets **traced by
`R-id`** + the **影响面 (impact surface)** analysis. **ADRs** for decisions that are
hard-to-reverse, surprising, and a real trade-off. Stress-test via grilling. GATE: STOP; **on
approval `design.md` is FROZEN** (its referenced ledger rows all approved,「Ledger」); those
decisions change only through M2. Steps: `references/steps/design-grill.md`, `references/steps/adr.md`.

### 3. 详设 Detailed design → `detail.md` (LLD — optional for XS/S)
Lowers the frozen architecture to **concrete structures with rationale** — what `design.md`
deferred and `plan.md` shouldn't have to invent: 数据结构 · 关键机制/算法 · 代码级接口 ·
边界与错误矩阵 · 可追溯 (per the template). The ADR records the hard-to-reverse decision;
`detail.md` holds the full concrete spec referencing it. Ledger-worthy choices get `S<n>` ids
(「Ledger」). GATE (**baseline, not freeze**): STOP for human review — approved detail-level rows
carry baseline force; afterwards each change adds a dated note, and a change implicating the
*architecture* routes through M2. Step: `references/steps/detail.md`.

### 4. 实现 Implement → `plan.md` (mutable) + `progress.md`
`plan.md` = vertical-slice task breakdown: each task tags the **`R-id`(s) it implements**;
acceptance is a **binary** walk (`[x]`/`[!]`/`[ ]`, no subjective `[x]`). It implements the frozen
design + `detail.md` and **may change freely** — but deleting / merging / deferring a task, or
invalidating an `[x]`, is logged to `log.md` (routine refinement is silent, M2 case B). The phase
runs **autonomously** per「Two zones」; pause only on a design/requirement fork (→ M2), a real
blocker, or a push request. Commit after each task and each review fix, one concern per commit.
`progress.md` = the session-resume snapshot (M4); each finished slice appends one line to
`test.md`'s Unit registry. Per-slice testing runs in the project's recorded mode — **TDD** or
**test-after** — both vertical, never all-code-then-all-tests. The phase ends with one
behavior-preserving **simplify sweep** over the whole change (implement.md; XS/S may skip).
Steps: `references/steps/plan.md`, `references/steps/implement.md`.

### 5. 测试 Test → `test.md`
**Skeleton-first, filled incrementally** — `test.md` is **seeded at plan time** (coverage table
from the design's 验证策略, 回归 rows from 影响面), grows one Unit-registry line per implement
slice, and this phase **closes it out** rather than reconstructing it: coverage **by `R-id`** +
every module interface op/invariant, cross-slice tests (integration / 联调 / manual / E2E), full
suite run (or "describe, don't run"), a binary acceptance walk. A bug found here → **Prove-It**
(failing test first, fix in an 实现 slice). Step: `references/steps/test.md`.

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
drafting。质量判据（单向必要）：seam 写不出一份**具名契约** → 不具备拆卡条件，先
investigation 把契约摸出来再判；写得出是必要非充分。字段级机制（part 轴各文档字段、看板
两轴与单调约束、canonical 术语表、card-还是-雾判定）与 **split-out procedure**（升 B 后的
拆出五步）：`references/split-isolate.md`。

## Six cross-cutting mechanisms

- **M1 Evidence** — no guessing, no 望文生义. Every non-trivial claim cites code (`func()` in `file.c`,
  no line numbers) or a doc/source. Uncertainty → dispatch an Explore subagent to investigate;
  capture reusable findings to the KB. `references/steps/evidence.md`.
- **M2 Change management** — reopening an approved decision is **gated at entry** (human-initiated,
  or Claude escalates the fork as a proposed ledger row and waits) → **proposal substance lands as
  proposed blocks, then a 修改列表 touch-list** (human confirms; no approved row flips and no phase
  doc is touched before) → **scoped, mode-specific propagation (追加/变更/撤销)** — never a
  wholesale regenerate → re-approve over the new proposed rows. Detail-only changes ride baseline
  force; pure implementation reality → edit `plan.md` freely. Every change + why → `log.md`.
  Full flow: `references/steps/change.md`.
- **M3 Omission check** — after **any** doc edit: links resolve; `index.md` rows current;
  requirement↔design↔detail↔plan↔test consistent; terminology canonical (one term per concept,
  matching its KB concept); run `workflow-status.py --check` (the deterministic subset — ledger
  id integrity, derived-status mappings, cycles, **facts.md marker integrity**, **part
  consistency** (plan `Part:` ⊆ the new-format Parts table's names); exit 1 =
  findings); reusable
  knowledge captured to the KB (xg-knowledge-lite Write + compile) or explicitly noted as
  deferred. `references/steps/omission-check.md`.
- **M4 Session continuity** — `progress.md` = pruned current-state snapshot, **self-sufficient for
  resume**; `log.md` = append-only why-history, **never on the resume path**. Never rebuild from
  chat history. Keep a decision-zone grill in one unbroken window (don't compact mid-grill); in the
  execution zone prefer `resume` in a fresh session over pushing a degraded one — `park` is the
  write side that lands state before leaving (human-initiated; Claude only suggests).
  `references/steps/resume.md` · `references/steps/park.md`.
- **M5 Code understanding** — concept-first, layered: query xg-knowledge-lite first, then read-only
  exploration (Plan Mode / Explore subagent). The deliverable is the logical/causal analysis
  (`doc-conventions.md`「Reasoning shown」), not a grep-hit list. Existing-code questions enter through
  `investigate`; defect localization through `diagnose`; judging new/changed code → `review`.
  `references/steps/understand.md`.
- **M6 Retro** — review friction, land fixes into this skill, the project CLAUDE.md, or the KB; mine
  the usage log (`tools/log-usage.py report`). A behavior-changing retro records a dated entry in
  `CHANGELOG.md` + a commit. `references/steps/retro.md`.

## Subagent model assignment (cost)

Checklist / gather / verification subagent work → cheaper model (Agent tool `model: sonnet`);
inference-heavy analysis → session model **capped at opus** (subagents never run fable; a fable
session dispatches them at `model: opus`). **Deterministic checks are scripted, not delegated**;
every downgrade sits under M6 calibration. Rationale, per-lens application, and the session-model
tiering (optional post-go `/model sonnet` + `/advisor opus` switch): `references/model-tiering.md`.

## Verbs

Invoke as `xg-dev-workflow <verb> [args] [use:<skill>]`.

- `new <slug>` — resolve project + next `NNN` (zero-padded; scan the project dir, increment),
  scaffold from templates, add the `index.md` card row (初始整体状态 `todo`); a roadmap-sourced slug
  is marked graduated there; a tracker-born ask records `issue:` in `requirement.md` frontmatter
  (the card↔issue anchor; `progress.md` carries the repo/branch/MR anchors). **Pre-fill the
  `governance:` field by sizing** (M+ → ledger, XS/S → doc-gate; the 需求 gate ratifies it —
  templates/requirement.md 头注). **Create files
  lazily**: `requirement.md` now, each later doc when its phase starts, `adr/` on the first ADR.
- `requirement` | `design` | `detail` | `plan` | `test` — advance **exactly one** phase, then stop
  at its gate (Stop-at-gate). Past the `plan` gate the zone flows autonomously (「Two zones」) — you
  normally don't invoke `test` by hand.
- `investigate <topic>` — **the front door for any code-behavior question** (feasibility,
  runtime/concurrency, "调查 X"); KB-first, M1, read-only. Step: `references/steps/investigate.md`.
- `diagnose <symptom>` — **the front door for defect localization** (bug, crash, perf regression);
  repro loop before any theory, fix lands via Prove-It. Step: `references/steps/diagnose.md`.
- `review <target>` — **the front door for judging new/changed code**; also the M+ close-out gate;
  read-only, report lands in dev_root. Step: `references/steps/review.md`.
- `improve <project> [<region>…]` — read-only deepening scan over a bounded region: friction
  probes + deletion test, negative-list-checked candidates land in a dev_root report; gate stops
  for the human pick → roadmap Next-up. Step: `references/steps/improve.md`.
- `change` — drive the M2 flow.
- `resume [<slug>]` — rebuild state from `progress.md` + the phase docs (M4).
- `park [<slug>]` — the write side of `resume` (M4): land un-persisted session content into its
  containers, top `progress.md` up to the resume floor, M3 + scoped commit, close with receipts
  + a one-line start instruction. Human-initiated — Claude only suggests.
  Step: `references/steps/park.md`.
- `check [<slug>]` — run the M3 check.
- `status [<project> …]` — the card view (pipeline position, board 整体状态/Deps, gate-derived next
  step); read-only, computed by `tools/workflow-status.py` (`--json`; `--trace` renders the
  R→design→task→test→commit matrix); `tools/viewer.py` serves the browsable HTML view — README.
- `retro` — review and enhance the skill/docs (M6).

Any phase verb accepts a `use:<skill>` suffix to override that step's implementation for this run.

## Usage logging (self-feedback)

Rule: `~/.claude/CLAUDE.md` (Skill Usage Logging); `--action` = the verb just run (vocabulary:
`KNOWN_ACTIONS` in `tools/log-usage.py`; `status` only as a deliberate standalone view). Mappings:
an in-card `investigate` logs `design`; implement-phase task work logs `plan` (one record per
task/checkpoint). **One event = one record** — a KB write inside a verb run is covered by that
record; only standalone KB work logs under xg-knowledge-lite.

## Step binding (vendor + runtime override)

Each step resolves to one implementation, by priority: (1) **runtime override** — `use:<skill>` on
the verb, or a persisted `workflow.bindings:` entry in config; (2) **vendored default** —
`references/steps/<step>.md`, a forked copy of a source skill's procedure (ours, editable; origins:
`references/provenance.md`); (3) **inline** — steps with no third-party source. Rebind or edit the
vendored file to change behavior; the **contract never changes**, only the implementation.

## References

- `references/templates/` — the twelve doc templates.
- `references/steps/` — per-step procedures + shared mechanisms referenced by multiple steps.
- `references/conventions-core.md` — shared writing core (byte-identical copy in both skills;
  synced, see `tools/sync-manifest.txt` once T2 lands).
- `references/doc-conventions.md` — the workflow-supplement writing rules (layered on core;
  read both before writing any workflow doc).
- `references/steps/grill.md` — shared interactive elicitation: one-question-at-a-time + grill-log
  + rollback + convergence auto-verdict.
- `references/steps/adversarial-critic.md` — fresh-context critic panel (three attack lenses +
  gate-adjacent criterion-conformance judge) + receipts; used by requirement, design-grill,
  review, and (lens 4 only) the 详设 baseline + execution-authorization gates.
- `references/steps/gate-digest.md` — the decision-card gate ask (判断分工: 已验证(勿复核) /
  待你判 + stakes; one chat message ≤~70 lines, never a file); read before every
  decision-zone gate ask.
- `references/steps/review-deep.md` — the `review` verb's deep-tier continuation.
- `references/model-tiering.md` — subagent model assignment rationale + session-model tiering.
- `references/split-isolate.md` — 拆分与隔离 field-level mechanics.
- `references/provenance.md` — what each vendored step was forked from.
- `references/id-schemes.md` — the full ID-prefix registry (SKILL.md keeps only the core five).
- `references/diagram-gotchas.md` — Mermaid pitfalls + ASCII CJK-width alignment.
- `references/frontend-testing.md` — browser + mobile real-device testing (UI-facing slices only).
- `references/simplify-checks.md` — reuse/cohesion checks (implement's sweep + review Standards).
- `references/smell-catalog.md` — Fowler code-smell names for the review quality lens.
- **`codebase-design`** (external skill) — deep-module vocabulary, Design-It-Twice, the deletion test.
- `tools/resolve-project.py` — cwd→project and `--dev-root` resolution (reads the shared config).
