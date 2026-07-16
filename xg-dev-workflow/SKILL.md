---
name: xg-dev-workflow
description: "Design-centric dev workflow: gated phases 需求→设计→详设→实现→测试→评审, one requirement = one card dir under dev_root. Use when the user opens or works a requirement ('new requirement' / '开个需求' / 'design this' / 'resume <slug>' / 'change the design' / 'workflow retro'); investigates code behavior ('investigate X' / '调查 X'); diagnoses a defect ('diagnose' / '定位这个 bug'); or reviews new/changed code ('review X' / 'review 这些改动')."
---

# xg-dev-workflow

A thin **orchestrator** for code work, split into five phases. Each phase produces one doc; **everything lands in docs** so any fresh session resumes from files alone (no chat history needed). The emphasis is **design** — not jumping from a requirement straight to an implementation plan, nor from a frozen architecture straight to a task list.

```
需求 requirement.md → 设计 design.md (+adr/) → 详设 detail.md → 实现 plan.md / progress.md → 测试 test.md → 评审 review (M+)
   ■STOP confirm        ■STOP freeze on approve   ■STOP baseline    plan is mutable               results recorded   ■gate before done
```
(■STOP = halt for an explicit human go — the Stop-at-gate rule. 详设 is optional for XS/S. 评审 is a close-out gate producing `notes/review-*.md`, not a sixth doc-phase.)

Reusable module knowledge does **not** live here — it lands in **xg-knowledge-lite** (`~/knowledge` raw/wiki), referenced from these docs via `[[wiki/<project>/<slug>]]` wikilinks. This skill holds only per-requirement docs.

**Writing style (all phase docs): plain prose, technical terms intact** (不变量 / 契约 / 幂等 stay); short sentences.

**Conventions (all docs):**
- **First-use gloss** — a coined term, codename, or non-standard abbreviation carries a one-line parenthetical at its first use per doc (and per chat session); **after that, use the term bare** — the gloss is paid once. A term used fewer than ~3 times isn't coined at all. Established domain terms need no gloss.
- **Diagrams — Mermaid preferred** (renders in GitHub/Obsidian/VS Code, diffs as text); ASCII only for the trivial or what Mermaid can't express (CJK-width rules in `design-grill.md`).
- **Links** — intra-requirement/project references use standard markdown links (`[design](./design.md)`); **KB cross-references keep the `[[wiki/<project>/<slug>]]` wikilink** — load-bearing for the KB's incremental recompile, don't swap it for a markdown link. **An ID cited from another file is a markdown link to its home** — `[R1](./requirement.md)`, `[ADR-0006 D5](./adr/0006-<slug>.md)`, `[T3](./plan.md)`; designated mapping fields and a doc's first mention always link, repeat prose mentions may stay bare (same-file citations stay bare).
- **Provenance** — load-bearing claims carry a marker: evidence-cited / 推断 (inferred) / 假设 (assumption). Only the claims a decision rests on (M1).
- **Reasoning shown (human-first docs)** — requirement/design/detail/ADR/review and investigation-notes prose carries the logical analysis, **evidence → mechanism → conclusion**, so the approver can check the inference, not just trust the citations — a fact table with a conclusion bolted on is a grep-hit list at doc level. Execution-zone docs stay terse: link the reasoning, don't restate it.
- **Reader-aware** — write each doc for its primary reader (each template states its Reader); the audience split is「Two zones」below.
- **Fixed ID prefixes (one letter, one meaning):** `NNN` card dir · `R<n>` requirement 条目 (R is reserved for requirements) · `ADR-NNNN` decision records · `T<n>` plan tasks · `G<n>` grill-log questions (**continuous across rounds**; round-scoped form `G<round>.<n>` — never a new letter per round) · `L<n>` abstraction layers (design) · `D<n>` design decisions/子决策 (scoped inside an ADR: `ADR-NNNN D<n>`) · `MS<n>` milestones/分期 (bare `M<n>` stays this skill's mechanisms `M1`–`M6`) · `P<n>` implement's principles (`implement.md` Principles). **Modules are named, like parts** (the name carries the meaning); `Mod<n>` only when a table/diagram needs a compact id — never bare `M<n>`/`D<n>` for a module. Review findings: `#<n>` within a report's 修复决策表, severity spelled out (High/Med/Low — no H/M/L shorthand). Parts are **named** (long form `Part <n> (<名>)` ok, no bare `P<n>`). Mermaid node ids are diagram-local — exempt. A new scheme picks an unused letter and lands here. **Cross-scheme mappings are recorded downstream→upstream only**, each in its doc's designated field (design「How it meets」R-id table · detail 可追溯 · plan `Implements:` · test Coverage rows · `ADR-NNNN D<n>`); the reverse map is derived (grep / M3), never hand-maintained — an upstream doc doesn't list who cites it (same one-way principle as workflow→KB links; M2 propagates along exactly these fields).

## Stop-at-gate rule (READ FIRST — overrides momentum)

The **hard stops** are the decision-zone gates — 需求 confirm · 设计 freeze · 详设 baseline — plus the **one-time execution authorization** after `plan.md`; each is a human decision. Past that authorization there are no per-phase stops (「Two zones」).

- **One phase per invocation.** After producing the phase's doc, STOP — even if you could roll on, even if the prompt mentions later phases. Report the doc + the gate question, then wait. Chaining requires the human to invoke each verb, or to explicitly say "run straight through".
- **A bare topic with no verb** means **`new` + `requirement` only**, then STOP. "调查 / investigate / explore" means stop at understanding — never auto-advance to a chosen design.
- **Gate = an explicit human go, this turn** — prior approval doesn't carry forward. Produce the doc, ask, and do not create or edit the next phase's doc until then. Unsure which phase is wanted → ask, don't assume the pipeline.
- **The advance word is `go` — uniformly.** Phrase every advance ask around it, naming what it authorizes (「确认后回 go,进入设计」/「go = 授权执行区」), and treat the human's `go` (or an equally explicit equivalent in their own words) as the authorization; comments or praise without a go are feedback, not a go. Applies to every advance: phase gates, the execution authorization, continuing after a grill convergence verdict.
- **Ask with receipts — write first, then ask.** An advance ask (and any reply that closes a verb run) is made only after this round's artifacts are on disk, and it **names them**: doc paths + the dev_root commit. No receipts, no ask. This closes M3's trigger blind spot — M3 fires on doc edits, so an *omitted* write produces no edit and no check; the receipts requirement makes a missing write impossible to ask past (a past grill ran rounds in chat without landing its grill-log).
- **Plan mode ≠ a gate substitute.** An ExitPlanMode approval only authorizes writing **this** phase's doc — not skipping it or jumping to implementation; the authoritative gate is the human approving that doc.

## Two zones: human-decision vs Claude-execution (one line, two meanings)

The phases split at the **设计/详设 freeze**, and that line is both the **decision** boundary and the **audience** boundary — they coincide on purpose:

- **Decision zone — 需求 · 设计 · 详设 (+ADRs).** Every binding gate lives here: the human makes the choices that are expensive to reverse. Docs are **human-first** — written to be read and approved: prose, rationale, alternatives, reviewable in one pass.
- **Execution zone — 实现 · 测试 · 评审.** Post-freeze choices are implementation-level — **Claude owns them** and runs the zone autonomously on the one "go" given after `plan.md` (the autonomy handoff): implement → test → close-out review report, **no per-task or per-phase gate**. Docs are **Claude-first** — terse, structured, link-don't-restate, optimized for execution + session resume, not for a human read-through.
- **The human re-enters at exactly two artifacts** — `log.md` (the audit trail; resume never reads it) and the 评审 review report (its 修复决策表 is a human decision) — plus any escalation Claude raises (design fork → M2, blocker, push request; commits are autonomous, push is gated).

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

**Project-global docs — split by nature.** **Planning → dev_root**: `<project>/roadmap.md` (next-up / themes / someday / rejected; items graduate to cards via `new`). **System knowledge → KB**, referenced one-way via `[[wiki/…]]`: the **architecture overview** (`[[wiki/<project>/architecture]]` — linked from each card's `design.md` and refreshed as-built when a design freezes) and per-subsystem **invariant ledgers** (loaded/replayed by the adversarial-critic). The KB never links back into dev_root.

## Config & project resolution (shared with xg-knowledge-lite)

Same config file: `~/.config/xg-knowledge-wiki/config.yaml`.

- `dev_root:` → workflow docs root. Resolution: (1) `--root <path>`; (2) config `dev_root:`; (3) default `~/dev-workflow`. Never auto-create the config.
- `projects:` → the **same** map xg-knowledge-lite uses. Resolve cwd→project with `tools/resolve-project.py [<cwd>]`; on miss, ask once and register via xg-knowledge-lite's `tools/register-project.py <name> <path>`. Never auto-pick `common`.

## Versioning the docs (dev_root git)

`dev_root` is its **own git repo** (all projects; separate from the product-code repo and the KB repo), lazily initialized on the first commit — `tools/commit-data-repos.py` does init-if-needed + commit-if-dirty.

- **Commit at each gate / doc boundary** (semantic, not per keystroke): when a verb finishes writing — `new`, `requirement` (confirmed), `design` (frozen), `detail` (baseline), `plan`, each implement task's `progress.md` update, `test`, `review`, a `change`/M2 entry, investigate/diagnose notes, each grill-round verdict (checkpoint). Run M3 first, then commit. Message: `<project>/NNN-slug: <verb> — <one line>`.
- **Autonomous local commit; `push` stays human-gated;** history append-only (no amend/rebase).
- An implement task yields **two** commits — product code → its own repo, docs → the dev_root repo. Don't cross them.
- Optional safety net: a session-end hook runs `tools/commit-data-repos.py` to sweep uncommitted docs (README).

## The five phases (contracts) + the close-out review gate

Each phase is a **contract** — input, output doc, gate — independent of which skill implements it (see Step binding). Templates in `references/templates/`, per-step procedures in `references/steps/`.

**Requirement sizing (XS/S vs M+).** A human judgment, reusing the task-scope vocabulary (XS · S · M · L) at requirement level: **XS/S** = structure-light, ~one vertical slice, no new module/contract → may skip **详设** and the **评审** close-out (record the skip). **M+** = multi-slice, or introduces/changes a module/contract → does 详设 when structural, and **must** pass 评审 before `done`. Judged at design time, not a board column; M3's done-time signal is "a review doc exists **or** an explicit `XS/S — review skipped` note does".

### 1. 需求 Requirement → `requirement.md`
Input: a raw ask. **Elicited interactively, not written in one shot** — the grill loop (`grill.md`) interleaved with code understanding (M5/M1): surface assumptions first and let the human correct them; understand the **essence** behind the ask (it may be layered, diverge from its wording, map to the design non-1:1) — solve the real problem, don't transcribe the words. Output sections: **Context** · **需求条目** (atomic items, each one statement with a stable **`R-id`** — the **traceability spine** every later doc references) · **Scope** (in/out + 初步影响面) · **Constraints** · **Effect** (testable success criteria, each citing its `R-id`) · **Future** · **Open questions**. GATE: STOP for explicit confirm. Step: `references/steps/requirement.md`.

### 2. 设计 Design → `design.md` + `adr/` (the emphasis)
Understand first (M5), then design **at module altitude in abstraction layers**: weigh **multiple approaches by trade-off** (方案优先, spanning hack / 补丁 / 推翻重来 — debt is a conscious, recorded choice), prefer the **simplest reliable** design (简单可靠 > 精致复杂); express modules / responsibilities / boundaries / contracts, with concrete code deferred to detail/plan, and **required diagrams** (module-interaction + data-flow). Output: the chosen approach grounded in evidence + alternatives considered + how it meets scope/constraints/effect **traced by `R-id`** + a **影响面 (impact surface)** analysis (changed modules, callers & downstream consumers, compat/ABI surface, cross-card ripples, behaviors to re-verify). **ADRs** for decisions that are hard-to-reverse, surprising, and a real trade-off. Stress-test via grilling. GATE: STOP; **on approval `design.md` is FROZEN** — thereafter it changes only through M2. Steps: `references/steps/design-grill.md`, `references/steps/adr.md`.

### 3. 详设 Detailed design → `detail.md` (LLD — optional for XS/S)
Lowers the frozen architecture to **concrete structures with rationale** — what `design.md` deferred and `plan.md` shouldn't have to invent. Sections: **数据结构** (each with a one-line why) · **关键机制/算法** (trigger → steps → locking/transaction → error & edge handling → idempotency point) · **代码级接口** (signatures, actual SQL) · **边界与错误矩阵** · **可追溯** (item ↔ design module/contract ↔ R-id). Division of labour with ADRs: the ADR records the hard-to-reverse decision + alternatives; `detail.md` holds the full concrete spec, referencing those ADRs and filling the small-but-load-bearing choices. GATE (**baseline, not freeze**): STOP for human review; afterwards it may change as implementation reality bites — each change adds a dated note; a change implicating the *architecture* routes through M2. Step: `references/steps/detail.md`.

### 4. 实现 Implement → `plan.md` (mutable) + `progress.md`
`plan.md` = vertical-slice task breakdown: each task tags the **`R-id`(s) it implements**; acceptance is a **binary** walk (`[x]`/`[!]`/`[ ]`, no subjective `[x]`). It implements the frozen design + `detail.md` and **may change freely** — but deleting / merging / deferring a task, or invalidating an `[x]`, is logged to `log.md` (only routine refinement is silent, M2 case B). The phase runs **autonomously** per「Two zones」; pause only on a design/requirement fork (→ M2), a real blocker, or a push request. Commit after each completed task and each review fix, one concern per commit (implement's Commit cadence). `progress.md` = the session-resume snapshot (M4). Per-slice testing runs in one of two modes, chosen by the project's test-execution policy and recorded in `progress.md`: **TDD** (test-first red-green) or **test-after** (write/describe the test, defer the run) — both vertical, never all-code-then-all-tests. The phase ends with one behavior-preserving **simplify sweep** over the whole change (implement.md; XS/S may skip). Steps: `references/steps/plan.md`, `references/steps/implement.md`.

### 5. 测试 Test → `test.md`
**Consolidation** — per-slice unit tests were written in 实现; here close coverage (**by `R-id`** + every module interface op/invariant), add the tests that span slices (integration / 跨 part 联调 / manual / E2E), balance the pyramid, run the full suite (or describe the commands for "describe, don't run"), record a binary acceptance walk. A bug found here → **Prove-It** (failing test first, fix in an 实现 slice). Step: `references/steps/test.md`.

### 6. 评审 Close-out review (M+, gate) → `notes/review-*.md`
After 测试, before `done`: run the `review` verb on the whole change. Sizing + skip rule:「Requirement sizing」. Step: `references/steps/review.md`.

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

- **M1 Evidence** — no guessing, no 望文生义. Every non-trivial claim cites code (`func()` in `file.c`, no line numbers) or a doc/source. Uncertainty → dispatch an Explore subagent to investigate; capture reusable findings to the KB. `references/steps/evidence.md`.
- **M2 Change management** — requirement changes are **gated at entry** (human-initiated, or Claude presents the fork and waits) → edit `requirement.md` with a dated note → **propagate along the R-id spine, mode-specifically (追加/变更/撤销) and scoped** — never a wholesale regenerate → re-approve scoped to what changed. Design-driven and detail-only changes enter the same route at their own gates; pure implementation reality → edit `plan.md` freely. Every change + why → `log.md`. Full flow: `references/steps/change.md`.
- **M3 Omission check** — after **any** doc edit: links resolve; `index.md` rows current; requirement↔design↔detail↔plan↔test consistent; terminology canonical (one term per concept, matching its KB concept); reusable knowledge captured to the KB via xg-knowledge-lite Write and compiled — or explicitly noted as deferred. `references/steps/omission-check.md`.
- **M4 Session continuity** — `progress.md` = pruned current-state snapshot, **self-sufficient for resume**; `log.md` = append-only why-history, **never on the resume path**. Never rebuild from chat history. Keep a decision-zone grill in one unbroken window (don't compact mid-grill); in the execution zone prefer `resume` in a fresh session over pushing a degraded one. `references/steps/resume.md`.
- **M5 Code understanding** — concept-first, layered: query xg-knowledge-lite first, then read-only exploration (Plan Mode / Explore subagent). The deliverable is the logical/causal analysis (Conventions「Reasoning shown」), not a grep-hit list. Existing-code questions enter through `investigate`; defect localization through `diagnose`; judging new/changed code → `review`. `references/steps/understand.md`.
- **M6 Retro** — review friction, land fixes into this skill, the project CLAUDE.md, or the KB; mine the usage log (`tools/log-usage.py report`). A behavior-changing retro records a dated entry in `CHANGELOG.md` + a commit. `references/steps/retro.md`.

## Subagent model assignment (cost)

Checklist / gather / verification-driven subagent work defaults to the cheaper model (Agent tool `model: sonnet`); inference-heavy analysis, adjudication, and decisions stay on the session model. Safe because the orchestrator re-derives / adjudicates (M1; review step 5) — a cheaper finder costs recall at worst. Corollaries: **deterministic checks are scripted, not delegated**; every downgrade sits under M6 calibration — a sonnet dispatch whose findings repeatedly die in adjudication gets its downgrade revoked. Per-lens application: `review.md` step 4.

## Verbs

Invoke as `xg-dev-workflow <verb> [args] [use:<skill>]`.

- `new <slug>` — resolve project + next `NNN` (zero-padded per project — scan the project dir for the highest, increment), scaffold from templates, register project if missing, add an `index.md` card row (初始整体状态 `todo`); a roadmap-sourced slug is marked graduated there; an ask born from a tracker issue records it in `requirement.md` frontmatter `issue:` (the card↔issue anchor; `progress.md` frontmatter carries the repo/branch/MR/merged anchors + an `issue:` mirror). **Create files lazily**: `requirement.md` now; each later doc when its phase starts; `progress.md` on first need (a mid-grill checkpoint may create it early); `adr/` on the first ADR.
- `requirement` | `design` | `detail` | `plan` | `test` — advance **exactly one** phase, then stop at its gate (Stop-at-gate). Past the `plan` gate the zone flows autonomously (「Two zones」) — you normally don't invoke `test` by hand.
- `investigate <topic>` — **the front door for any code-behavior question** (feasibility, runtime/concurrency, "调查 X"). KB-first, full M1 discipline; branches on context — active requirement → it is that requirement's design step; standalone → findings to the KB. Read-only on product code (an empirical question may run a throwaway **spike**). Step: `references/steps/investigate.md`.
- `diagnose <symptom>` — **the front door for defect localization** (bug, crash, perf regression): feedback-loop-first — a red-capable repro loop before any theory; the fix lands via Prove-It. Branches like investigate (active card → the fix is an 实现 slice; standalone → propose the fix and wait). Step: `references/steps/diagnose.md`.
- `review <target>` — **the front door for judging new/changed code** (commit range, branch, PR, or current diff): KB context pack + **stake-tiered dispatch** (light: orchestrator-only · standard: three axis agents · deep: full lens fan-out + different-model sweep), every finding adjudicated against actual code; report ends with a 修复决策表 and lands in dev_root (requirement `notes/review-*.md`, or standalone `<project>/reviews/`). Also the M+ close-out gate. Read-only. Step: `references/steps/review.md`.
- `change` — drive the M2 flow.
- `resume [<slug>]` — rebuild state from `progress.md` + the phase docs (M4).
- `check [<slug>]` — run the M3 check.
- `status [<project> …]` — the card view: every card's pipeline position, board 整体状态/Deps, progress Now/Next/Blockers, and the gate-derived next step; read-only, computed on demand by `tools/workflow-status.py` (`--json` for scripts). `tools/viewer.py` serves the same data as a browsable localhost HTML view, with an optional gitweb companion for the project repos' code — details in README.
- `retro` — review and enhance the skill/docs (M6).

Any phase verb accepts a `use:<skill>` suffix to override that step's implementation for this run.

## Usage logging (self-feedback)

Logging rule lives in `~/.claude/CLAUDE.md` (Skill Usage Logging). This skill's `--action` = the verb just run (`new`/`requirement`/`design`/`detail`/`plan`/`test`/`investigate`/`diagnose`/`review`/`change`/`resume`/`check`/`retro`/`status` — `status` only as a deliberate standalone view). Exceptions: an `investigate` inside an active requirement logs `design` (it is that requirement's design step); implement-phase task work logs `plan` (one record per task/checkpoint). **One event = one record:** a KB write inside an `investigate`/`diagnose`/`review` run is covered by that record — only standalone KB work logs under xg-knowledge-lite.

## Step binding (vendor + runtime override)

Each step resolves to one implementation, by priority: (1) **runtime override** — `use:<skill>` on the verb, or a persisted `workflow.bindings:` step→skill entry in config; (2) **vendored default** — `references/steps/<step>.md`, a forked copy of a source skill's procedure (ours, editable anytime); (3) **inline** — steps with no third-party source. Rebind or edit the vendored file to change behavior; the **contract never changes**, only the implementation behind it. Fork origins: `references/provenance.md`.

## References

- `references/templates/` — the ten doc templates (`requirement`, `design`, `adr`, `detail`, `plan`, `progress`, `log`, `test`, `index`, `roadmap`).
- `references/steps/` — the per-step procedures, plus shared mechanisms referenced by multiple steps.
- `references/steps/grill.md` — shared interactive elicitation (requirement + design-grill): one-question-at-a-time protocol + grill-log + rollback (supersede discipline) + convergence auto-verdict; resume can continue a grill mid-phase.
- `references/steps/adversarial-critic.md` — shared sharp-cut finder (fresh-context three-lens critic + invariant-ledger replay + standing rules); used by requirement, design-grill, and review.
- `references/split-isolate.md` — 拆分与隔离 field-level mechanics.
- `references/provenance.md` — what each vendored step was forked from.
- **`codebase-design`** (external skill, referenced not vendored) — deep-module vocabulary + Design-It-Twice (design-grill 方案优先) + dependency-categories→test-strategy (test) + the deletion test (design-grill, implement).
- `tools/resolve-project.py` — cwd→project and `--dev-root` resolution (reads the shared config).
