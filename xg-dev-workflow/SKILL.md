---
name: xg-dev-workflow
description: "Design-centric dev workflow for code work: gated phases 需求→设计→详设→实现→测试→评审, one requirement = one docs directory (card) under dev_root. Use when the user opens or works a requirement ('new requirement' / '开个需求' / '走流程' / 'design this' / 'resume <slug>' / 'change the requirement/design' / 'workflow retro'); when the user asks to investigate code behavior ('investigate X' / '调查 X' — `investigate` is the front door for ANY code investigation); or when the user asks to review new/changed code ('review X' / 'review 这些提交/改动' — `review` is the front door for judging any commit range/branch/PR/diff)."
---

# xg-dev-workflow

A thin **orchestrator** for code work, split into five phases. Each phase produces one doc; **everything lands in docs** so any fresh session resumes from files alone (no chat history needed). The emphasis is **design**, not jumping from a requirement straight to an implementation plan — nor from a frozen architecture straight to a task list.

```
需求 requirement.md → 设计 design.md (+adr/) → 详设 detail.md → 实现 plan.md / progress.md → 测试 test.md → 评审 review (M+)
   ■STOP confirm        ■STOP freeze on approve   ■STOP baseline    plan is mutable               results recorded   ■gate before done
   (each ■STOP = produce the doc, then halt and wait for an explicit human go — see Stop-at-gate rule)
   (详设 is the concrete-structure layer between module contracts and task sequencing — optional for XS/S)
   (评审 is a close-out GATE not a sixth doc-phase: M+ runs `review` → notes/review-*.md before done; XS/S may skip)
```

Reusable module knowledge does **not** live here — it lands in **xg-knowledge-lite** (`~/knowledge` raw/wiki) and is referenced from these docs via `[[wiki/<project>/<slug>]]` wikilinks. This skill holds only per-requirement docs.

**Writing style (all phase docs): lean toward plain wording, but keep the technical term when it's the right word.** Prefer the everyday phrasing where it doesn't lose precision; don't force-replace established technical terms (不变量 / 契约 / 幂等 …) with folksy paraphrases. Err on the side of clear-but-professional, not dumbed-down. Short sentences; readable in one pass.

**Conventions (all docs):**
- **First-use gloss (coined terms & codenames).** A coined term, session-local codename, or
  non-standard abbreviation carries a one-line parenthetical definition at its first use in each
  doc — and on first use per chat session (方案 T（瘦身版 QD 驱动）; M+（sizing: multi-slice /
  new contract）). A term expected to be used fewer than ~3 times isn't coined at all — use the
  plain phrase. Established domain terms need no gloss. (M3 checks term *consistency*; this rule
  covers first-use *comprehensibility* — different failures.)
- **Diagrams — prefer Mermaid** (a ```` ```mermaid ```` fenced block; renders in GitHub/Obsidian/VS Code, still diffs as text). ASCII only for a trivial diagram or what Mermaid can't express (then the CJK-width rules in `design-grill.md`).
- **Links — clickable where cheap.** Intra-requirement / intra-project references use **standard markdown links** (`[design](./design.md)`, `[ADR-0001](./adr/0001-x.md)`) so they resolve in any viewer. **KB cross-references keep the `[[wiki/<project>/<slug>]]` wikilink** — it is load-bearing for the KB's incremental recompile; don't swap it for a markdown link. (KB and `dev_root` are separate roots, so a companion markdown link to a KB file would be a fragile cross-root path — not required.)
- **Provenance** — load-bearing claims carry a marker: evidence-cited / 推断 (inferred) / 假设 (assumption). Don't tax every sentence — just the claims a decision rests on (M1, `evidence.md`).
- **Reasoning shown, not just facts (human-first docs).** Requirement/design/detail/ADR/review **and investigation-notes** prose (standalone `investigations/` files, KB raw write-ups — where the rule originated, M5) must carry the **logical analysis**, not only cited code facts: **evidence → mechanism → conclusion**, so the approver can *check the inference*, not just trust the citations — a section that is a fact table with a conclusion bolted on is the doc-level version of a grep-hit list. M5's "the deliverable is a logical/causal analysis" governs what lands in these docs, not only the investigation that produced it. (Execution-zone docs stay terse — link the reasoning, don't restate it.)
- **Reader-aware detail** — write each doc for its primary reader: **decision-zone** docs (requirement/design/detail) are **human-first** (reviewable prose), **execution-zone** docs (plan/progress/test) are **Claude-first** (terse, machine-resumable); `log.md` is the human audit trail and the review report is the human decision point. See 「Two zones」below; each template states its Reader.

## Stop-at-gate rule (READ FIRST — overrides momentum)

In the **decision zone** (需求/设计/详设) this skill advances **one phase per invocation, then STOPS** and hands control back to the human; gates there are **hard stops**, not signposts you note while continuing. (The **execution zone** — 实现→测试→评审 — is the deliberate exception: it flows autonomously on one authorization — see the last bullet and「Two zones」.) The bullets below describe the decision-zone discipline unless noted.

- **One phase per invocation.** After producing the phase's doc, STOP. Do not roll on to the next phase in the same turn, even if you have enough to do so, even if the prompt mentions later phases. Report what you wrote and the gate question, then wait. Chaining phases requires the human to invoke each verb, or to explicitly say "run straight through."
- **A bare topic with no verb** (e.g. `/xg-dev-workflow <some ask>`) means **`new` + `requirement` only**, then STOP. It does **not** authorize design/detail/plan/test. "调查 / investigate / explore" means stop at understanding — never auto-advance to a chosen design.
- **Gate = wait for an explicit human go.** "human confirms before design" / "approved → frozen" mean: produce the doc, ask, and **do not edit or create the next-phase doc until the human says go** (in their own words this turn — prior approval doesn't carry forward). When unsure which phase the human wants, ask; don't assume the whole pipeline.
- **Plan mode ≠ a gate substitute.** If Claude Code's plan mode is entered during a phase, an ExitPlanMode approval only authorizes writing **this** phase's doc — not skipping it or jumping to implementation. Its "plan" should read "I'll write `<doc>`"; the authoritative gate is the human approving that doc.
- **The hard stops are the decision-zone gates** (需求 confirm · 设计 freeze · 详设 baseline) **plus the one-time execution authorization** after `plan.md` — binding because each is a human *decision*. Within the **execution zone** there is no per-phase stop: it flows autonomously on that one "go" — semantics, escalations, and the human's re-entry points in「Two zones」below.

## Two zones: human-decision vs Claude-execution (one line, two meanings)

The phases split into two halves at the **设计/详设 freeze**, and that one line is **both** the
decision boundary **and** the audience boundary — they coincide on purpose:

- **Decision zone — 需求 · 设计 · 详设 (+ADRs).** Every **binding gate** lives here (confirm /
  freeze / baseline): this is where the human makes the choices that are expensive to reverse.
  So these docs are **human-first** — written to be *read and approved*: prose, rationale,
  alternatives, reviewable in one pass. Claude reads them too (as the contract), but the approver
  is the primary reader.
- **Execution zone — 实现 · 测试 · 评审 (plan / progress / test / review report).** Once the design
  is frozen the remaining choices are **implementation-level — Claude owns them** and runs the zone
  **autonomously, no per-task *or* per-phase gate**: one "go" flows implement → test → close-out
  review report (see implement's Autonomy). `plan.md` is the zone's first doc and the autonomy
  handoff — the human authorizes execution **once**, not a stream of decisions. So these docs are
  **Claude-first** — terse, structured, link-don't-restate, optimized for execution + session-resume,
  *not* for a human read-through (the human approved the design, not the task list).
- **The human re-enters the execution zone at exactly two deliberate artifacts** — `log.md` (the
  human-only audit trail; resume never reads it) and the **评审 close-out review** report (its
  修复决策表 is a human decision). Plus any escalation Claude raises (design-fork → M2, blocker,
  push request — commits are autonomous, push is gated). Otherwise the zone is hands-off.

Net: gates cluster in the first half, autonomy lives in the second, and you write each doc for
whoever actually reads it — because the decision axis and the audience axis are the same line.

## Layout (requirement-centric)

```
<dev_root>/                         # from config dev_root: (default ~/dev-workflow)
  index.md                         # cross-project index
  <project>/                        # == xg-knowledge-lite project name
    index.md                       # per-project kanban board (cards: Phase/整体状态/Deps)
    roadmap.md                     # project-global plan: next-up/themes/someday (lighter than cards) — M3 keeps it fed
    investigations/                # standalone (requirement-less) investigations: <slug>.md
                                    #   single-file (new files: no investigation- prefix — the dir
                                    #   already says it), or <topic>/ campaign dir for a large
                                    #   multi-file investigation (charter + phase notes + progress)
    reviews/                        # standalone (requirement-less) review reports
    notes/                          # project-level scratch (proposals, triage, project retro) —
                                    #   same naming rule as card notes/ (event artifacts dated)
    legacy/                         # pre-workflow archive (read-only; never linked as canonical)
    NNN-requirement-slug/           # created lazily — each doc appears when first needed (usually its phase start)
      requirement.md                # 需求 (created by `new`)
      design.md                     # 设计 (概设/HLD) — FROZEN once approved
      adr/NNNN-slug.md              # decision records (adr/ created on first ADR)
      detail.md                     # 详设 (LLD) — BASELINE (review-gated, mutable w/ dated note); optional, skip for XS/S
      plan.md                       # 实现 plan — MUTABLE
      progress.md                   # current-state snapshot (session resume); pruned, not a log
      log.md                        # append-only change log (what changed + why); never edited/pruned
      test.md                       # 测试
      notes/                        # requirement-specific raw scratch (optional). Naming: event
                                    #   artifacts (review-/retro-) carry YYYY-MM-DD; living docs
                                    #   (grill-<phase> log, topic scratch) stay date-free
```

**Project-global docs (card-transcending) — split by nature.** **Planning → dev_root**: `<project>/roadmap.md` (next-up / themes / someday — so deferred work isn't forgotten; items graduate to cards via `new`). **System knowledge → KB** (xg-knowledge-lite), referenced one-way via `[[wiki/…]]`: the **architecture overview** (`[[wiki/<project>/architecture]]` — the big-picture map each card's `design.md` links and updates as designs freeze) and per-subsystem **invariant ledgers** (`[[wiki/<project>/<subsystem>-invariants]]` — loaded/replayed by the adversarial-critic). The KB never links back into dev_root.

## Config & project resolution (shared with xg-knowledge-lite)

Same config file: `~/.config/xg-knowledge-wiki/config.yaml`.

- `dev_root:` → workflow docs root. Resolution: (1) `--root <path>`; (2) config `dev_root:`; (3) default `~/dev-workflow`. Never auto-create the config.
- `projects:` → the **same** map xg-knowledge-lite uses. Resolve cwd→project with `tools/resolve-project.py [<cwd>]`; on miss, ask once and register via xg-knowledge-lite's `tools/register-project.py <name> <path>` (positional args). The project name here equals the KB project name, so `[[wiki/<project>/<slug>]]` links stay consistent. Never auto-pick `common`.
- `NNN` is a zero-padded sequence **per project** (scan the project dir for the highest, increment).

## Versioning the docs (dev_root git)

`dev_root` is its **own git repo** (one repo covering all projects — separate from the product-code repo *and* the KB repo). **Lazily initialized** on the first commit (`git init` + a minimal `.gitignore`, announced once) — `tools/commit-data-repos.py` does init-if-needed + commit-if-dirty.

- **Commit at each gate / doc boundary** (semantic, *not* per keystroke): one commit when a verb finishes writing — `new` (scaffold + card), `requirement` (confirmed), `design` (frozen), `detail` (baseline), `plan`, **each implement task's `progress.md` update**, `test`, `review`, a `change`/M2 entry, investigate notes, **each grill-round verdict (checkpoint — the dry check's diff baseline, `grill.md` Convergence)**. Run M3 first, then commit. Message: `<project>/NNN-slug: <verb> — <one line>` (e.g. `cbdb/001-foo: design frozen`).
- **Autonomous local commit** (the human's standing authorization, like the product-code Commit cadence); **`push` stays human-gated**; history append-only (no amend/rebase).
- **Separate from product code:** an implement task yields **two** commits — product code → its own repo, `progress.md`/docs → the dev_root repo. Don't cross them.
- **Safety net (optional):** a session-end hook can run `tools/commit-data-repos.py` to sweep any uncommitted docs (see README).

## The five phases (contracts) + the close-out review gate

Each phase is defined by a **contract** — input, output doc, gate — independent of which skill implements it (see Step binding). Templates in `references/templates/`, per-step procedures in `references/steps/`. The five doc-producing phases are followed by **评审**, a close-out *gate* (not a sixth doc-phase) for M+ requirements.

**Requirement sizing (XS/S vs M+).** A human judgment, reusing the task-scope vocabulary (XS · S · M · L) at the requirement level: **XS/S** = structure-light, ~one vertical slice, introduces no new module/contract → may skip **详设** *and* the **评审** close-out (record the skip). **M+** = multi-slice, or introduces/changes a module/contract → does 详设 when structural, and **must** pass the 评审 gate before `done`. Size is judged at design time and is **not** a board column; the done-time signal M3 keys off is "a review doc exists **or** an explicit `XS/S — review skipped` note does" (so the check needs no size field of its own).

### 1. 需求 Requirement → `requirement.md`
Input: a raw ask. **Elicited interactively, not written in one shot** — a grill/interview loop (one question at a time, each with a recommended answer; shared protocol + grill-log + rollback + convergence auto-verdict in `grill.md`) **interleaved with code understanding** (M5/M1: read the code to answer a question instead of guessing), converging on sharp boundaries and testable criteria. Output sections: **Context** (why / what prompted) · **需求条目** (the canonical itemized list — atomic requirements, each a single statement with a **stable `R-id`**; this is the **traceability spine** every later doc references, not prose to restate) · **Scope** (in / out + 初步影响面) · **Constraints** (ABI, change rules, compat, perf) · **Effect** (measurable success criteria — *how* each 条目 is verified, each citing its `R-id`; 条目 = what's required, Effect = the acceptance test for it) · **Future** (deliberately deferred / extensibility) · **Open questions**. Surface assumptions explicitly first and let the human correct them (mark provenance — evidence / 推断 / 假设, M1); reframe vague asks as testable criteria. Understand the **essence** behind the ask (it may be layered, diverge from its wording, and map to the design non-1:1) — solve the real problem, don't transcribe the words. **GATE (hard stop): after writing `requirement.md`, STOP. Do not create or touch `design.md` until the human explicitly confirms the requirement this turn.** Step: `references/steps/requirement.md`.

### 2. 设计 Design → `design.md` + `adr/` (the emphasis)
Understand first, concept→layer (see M5), then design **at module altitude in abstraction layers** — find the essential 思路, weigh **multiple approaches by trade-off** (方案优先), prefer the **simplest reliable** design (简单可靠 > 精致复杂); express it as modules / responsibilities / boundaries / contracts within layers, with **concrete code (functions, locks, hooks, files) deferred to `plan.md`** — and **required diagrams** (module-interaction + data-flow; **Mermaid preferred**, ASCII fallback). Output: the **chosen feasible approach** grounded in evidence + alternatives considered (spanning the **hack / 补丁 / 推翻重来** spectrum, each with its cost — debt is a conscious, recorded choice) + how it meets scope/constraints/effect/future **traced by `R-id`** + a **影响面 (impact surface)** analysis (changed/added modules, existing callers & downstream consumers, compat/ABI surface, cross-card/cross-project ripples, behaviors to re-verify). Emit **ADRs** for decisions that are hard-to-reverse, surprising, and a real trade-off. Stress-test the design (grilling). **GATE (hard stop): present the design and STOP. Do not write `detail.md`/`plan.md` or any code until the human approves. On approval `design.md` is FROZEN** — thereafter it changes only through the change-management flow (M2). Steps: `references/steps/design-grill.md`, `references/steps/adr.md`.

### 3. 详设 Detailed design → `detail.md` (LLD — optional for XS/S)
Lowers the frozen architecture to **concrete structures with rationale** — the layer between module contracts and task sequencing (what `design.md` deferred and `plan.md` shouldn't have to invent). Output sections: **数据结构** (schema / types / keys / indexes / in-memory structures, **each with a one-line why**) · **关键机制/算法** (trigger → step sequence → locking/transaction → error & edge handling → idempotency point, citing relevant ADRs) · **代码级接口** (function/hook signatures, actual SQL — the concrete code `design.md` deferred) · **边界与错误矩阵** (missing / concurrent / partial-failure / cancel → behavior in the safe direction) · **可追溯** (each item ↔ a design module/contract ↔ a requirement 条目 R-id). **Division of labour with ADRs:** an ADR records the hard-to-reverse decision + alternatives; `detail.md` holds the *full concrete spec*, **referencing** those ADRs and filling the small-but-load-bearing choices that don't each merit one (column types, PK, hash-load vs point-query, error paths). **GATE (baseline, not freeze): present `detail.md` and STOP for human review. On approval it is the BASELINE** — it may still change as implementation reality bites, but each change adds a dated note explaining why; only when a change implicates the *architecture* (`design.md`) does it route back through M2. **Skip for XS/S requirements** (a structure-light change goes straight to plan). Step: `references/steps/detail.md`.

### 4. 实现 Implement → `plan.md` (mutable) + `progress.md`
`plan.md` = vertical-slice task breakdown (each task tags the **`R-id`(s) it implements**; acceptance criteria, verification, dependencies, files, scope); acceptance is a **binary** walk (`[x]`/`[!]`/`[ ]`, no subjective `[x]`). It implements the frozen design + `detail.md` (when present) and **may change freely** as reality bites; tasks **reference** `detail.md` for structure/algorithm rather than redefining it. **Deleting / merging / deferring a task — or invalidating an `[x]` — is logged to `log.md`** (`[实现]`, what + why); only routine refinement is silent (M2 case B). **This phase runs autonomously** — once the human says go, roll through the slices without per-task gates: own the implementation-level decisions (make + record them), pause/escalate only on a design- or requirement-level fork (→ M2), a real blocker, or a push request (Stop-at-gate stops after the *phase*, not each slice). **Commit cadence:** an autonomous local commit after each completed task (runnable checks green — acceptance `[x]` in TDD mode, `[ ]` pending-run in test-after mode) and each review fix, one concern per commit; **push stays human-gated** (see implement's Commit cadence). `progress.md` = step table, changed files, design iterations, discovered issues — the session-resume doc (M4). Code in thin increments; cite sources for framework/API calls (M1). **Per-slice testing runs in one of two modes, chosen by the project's test-execution policy and recorded in `progress.md`:** **TDD** (test-first red-green, where tests run) or **test-after** (write/describe the test then defer the run — for cbdb's "describe, don't run") — both **vertical / per-slice**, never all-code-then-all-tests. Steps: `references/steps/plan.md`, `references/steps/implement.md`.

### 5. 测试 Test → `test.md`
**Consolidation phase** — the per-slice unit tests were already written in 实现 (per the chosen mode); here you close coverage (**by `R-id`** + every module interface op/invariant), add the tests that **span slices** (integration / 跨 part 联调 with real neighbors / manual / E2E), balance the test pyramid, run the full suite (or describe the commands for "describe, don't run"), and record a **binary** acceptance walk (`[x]` observed pass / `[!]` failed / `[ ]` unverified — no subjective `[x]`). Behavior-level tests via public interfaces; a bug found here uses **Prove-It** (failing test first, fix in an 实现 slice). Step: `references/steps/test.md`.

### 6. 评审 Close-out review (M+, gate) → `notes/review-*.md`
Not a sixth doc-producing phase — a **gate**: after 测试, an **M+** requirement (see「Requirement sizing」above) runs the `review` verb on the whole change to produce a close-out review doc under `notes/` **before the card goes `done`**, so non-trivial code earns *both* a test doc and a review doc. **XS/S** structure-light work may skip it — then record `XS/S — review skipped` in `progress.md` (the gate is "review doc OR skip note"). `review` stays usable standalone on any diff/PR too. Step: `references/steps/review.md`.

## 拆分与隔离 (split & isolate) — 可选叠加层

把工作拆成独立部分、各自推进、最后收口。两种粒度，互相独立，都可选（够小就不拆）：
**A — 设计内 part 化**（**part** = 作为独立单元实现+测试的命名 module 块，**seam** = part 间
边界，其契约随设计冻结；part 是贯穿 design→plan→test→progress 的可选分组轴；seam 契约被联调
证伪 = 架构级变更走 M2）；**B — 需求级拆分** = 多 **card** + 每项目 `index.md` 看板
（Phase + **整体状态** + Deps）。**A↔B 判定**——满足任一即升 B：(a) 独立上线/发布时间线；
(b) 能单独交付并产生价值；(c) 不同 reviewer/负责人；(d) 一部分设计能独立冻结而另一部分还在
drafting。字段级机制（part 轴各文档字段、看板两轴与单调约束、canonical 术语表）：
`references/split-isolate.md`。

## Six cross-cutting mechanisms

- **M1 Evidence** — no guessing, no 望文生义. Every non-trivial claim cites code (`func()` in `file.c`, no line numbers) or a doc/source. Uncertainty → dispatch an Explore/general-purpose subagent to investigate; record the finding (and capture reusable parts to the KB). `references/steps/evidence.md`.
- **M2 Change management** — requirement changes are **gated at entry** (human-initiated, or Claude presents the fork and waits) → edit `requirement.md` (dated change note stating each affected 条目's **mode**: **追加** add-new-R-id / **变更** supersede / **撤销** retire) → **propagate along the R-id spine, mode-specifically and scoped** (design「How it meets」/影响面 → `detail.md` 可追溯 → `plan.md` `Implements:` → `test.md` R-id rows — not a wholesale regenerate): 追加 appends without invalidating existing acceptance; 变更 = superseding ADR + traced `[x]→[ ]` resets + **proportional re-grill** of just the changed contracts; 撤销 retires downstream items too. Check **cross-card Deps** for ripples, then re-approve/re-freeze scoped to what changed. A **design-driven 方案变更 with the requirement unchanged** enters the same route without touching `requirement.md` (record = superseding ADR + `log.md`; affected set = the changed contracts' traces; the rewritten「How it meets」re-verifies the same R-ids). A `detail.md`-only change that doesn't touch the architecture stays at the baseline gate — edit it with a dated note, no full M2. Pure implementation reality → edit `plan.md` freely, **no design churn**. **Append every change + its reason to `log.md`** (the append-only history). `references/steps/change.md`.
- **M3 Omission check** — after **any** doc edit, run `references/steps/omission-check.md`: wikilinks/ADR links resolve; `index.md` rows updated; requirement↔design↔detail↔plan↔test stay consistent (each `detail.md` item traces to a design module/contract); **terminology consistent (one canonical term per concept, matching its KB concept)**; status/dates current; reusable knowledge captured to KB **via xg-knowledge-lite Write (frontmatter discipline — not a bare hand-written file), and either compiled to a concept or explicitly noted as deferred** (an uncompiled raw is backlog, surfaced per-session by `kb-backlog.py`).
- **M4 Session continuity** — two complementary docs: **`progress.md`** = current-state snapshot (pruned, link-don't-restate); **`log.md`** = append-only change log (every notable change + **why**; never edited/pruned — full history/audit). **`resume` rebuilds from `progress.md` + the phase docs and must NOT read `log.md`** (it's human/audit-only and can grow large — reading it on every resume would defeat the snapshot's token savings). So **`progress.md` must be self-sufficient for resume**; the log is never on the resume path. Never rebuild from chat history. **Session hygiene:** keep a decision-zone grill (requirement/design) in one unbroken window — don't compact mid-grill; in the execution zone each task/checkpoint can cold-start from `progress.md`, so when a session grows long/degraded, prefer `resume` in a fresh session over pushing on — which also keeps proving the snapshot's self-sufficiency. `references/steps/resume.md`.
- **M5 Code understanding** — concept-first, layered. Query xg-knowledge-lite first; for existing code use Plan Mode investigation or an Explore subagent (grep + read, no edits). **grep/read only *gather*; the deliverable is a logical/causal analysis** — trace the path that actually runs, build the mechanism, apply the Synthesis lens — not a grep-hit list (see `investigate.md`「Analysis, not just grep」). Understanding existing code enters through the **`investigate` verb** (front door + context branching there); judging new/changed code → `review`. `references/steps/understand.md` is the underlying comprehension mechanism.
- **M6 Retro** — session-level or periodic: review friction, then land fixes into this skill (SKILL.md / templates / steps), `cbdb/CLAUDE.md`, or the KB. Closes the improvement loop. Mine the usage log (`tools/log-usage.py report`) for what to fix. **A retro that changes skill behavior records it** — a dated, behavior-level entry in the skill's `CHANGELOG.md` (the curated history; `git log` is the full one) + a commit. `references/steps/retro.md`.

## Subagent model assignment (cost)

**Checklist / gather / verification-driven subagent work defaults to the cheaper model** (Agent
tool `model: sonnet`); **inference-heavy analysis, adjudication, and decisions stay on the
session model.** Safe because the orchestrator's re-derive / adjudicate duties (M1; `review.md`
step 5) are the precision backstop — a cheaper finder costs recall at worst, and checklist
recall doesn't lean on inference depth. Two corollaries: **deterministic checks are scripted,
not delegated** (zero tokens — a model gets only the judgment-heavy remainder), and **every
downgrade sits under M6 calibration** — a sonnet dispatch whose findings repeatedly die in
adjudication, or that repeatedly misses what the orchestrator then catches, gets its downgrade
revoked. Origin + the per-lens application: `review.md` step 4. Other dispatch points citing
this rule: M1 gather (`evidence.md`), M3 check (`omission-check.md`), the critic's lightweight
consistency pass (`adversarial-critic.md`); xg-knowledge-lite's Lint states the same principle
self-contained.

## Verbs

Invoke as `xg-dev-workflow <verb> [args] [use:<skill>]`.

- `new <slug>` — resolve project + next `NNN`, scaffold the requirement dir from `references/templates/`, register project if missing, add an `index.md` **card** row (初始 **整体状态** = `todo`; see 「拆分与隔离」). If the slug came from a `roadmap.md` item, mark it graduated there (→ NNN). **Create files lazily** (grill-with-docs convention): scaffold `requirement.md` now; create `design.md` / `detail.md` / `plan.md` / `test.md` only when their phase starts (`detail.md` only if the requirement does the optional 详设 phase), `progress.md` on **first need** (a mid-grill checkpoint or an in-requirement `investigate` record may create it before 实现 — lazy means don't pre-create, not implement-phase-only), and `adr/` only when the first ADR is written — don't pre-create empty next-phase docs or dirs.
- `requirement` | `design` | `detail` | `plan` | `test` — advance **exactly one** phase (resolves the step binding), then STOP at that phase's gate (see Stop-at-gate rule). **Decision-zone verbs** (`requirement`/`design`/`detail`) each stop at a binding gate; `plan` stops at the one-time **execution authorization**. After that "go", the **execution zone flows autonomously** — implement → `test` → 评审 report run without separate per-phase invocations (the Stop-at-gate carve-out), so you normally don't invoke `test` by hand. Decision-zone phases still need explicit invocation each, unless the human says "run straight through".
- `investigate <topic>` — **the single front door for any code investigation** (feasibility, runtime/concurrency, "调查 X", probing an Open question). KB-first, full M1 discipline (claims table before any feasibility/runtime conclusion); **branches on context** — requirement active → its M5/design step (logs `design`); standalone → findings to the KB (logs `investigate`); anchoring rule in the step. Read-only on product code (an **empirical** question may run a throwaway **spike** probe — see the step's Spike section). Step: `references/steps/investigate.md`.
- `review <target>` — **the front door for reviewing new/changed code** (commit range, branch, PR, or current diff): KB context pack + parallel lens agents (+ one different-model sweep), every finding **adjudicated** against actual code before reporting; report ends with a 修复决策表 and lands in dev_root (requirement `notes/review-*.md`, or standalone `<project>/reviews/`). Also the **M+ close-out gate** before a card goes `done` (XS/S may skip). Read-only. Step: `references/steps/review.md`.
- `change` — drive the M2 change-management flow.
- `resume [<slug>]` — reconstruct state from docs (M4).
- `check [<slug>]` — run the omission/consistency check (M3).
- `status [<project> …]` — **the card view** (workflow visibility): every card's pipeline position (需求→设计→详设→实现→测试→评审, each phase's doc status from frontmatter), board 整体状态/Deps, progress.md's Now/Next/Blockers, and — when progress carries no Next-step bullet — the **gate-derived next step** (which gate the card is waiting at). Read-only, computed from the docs on demand (`tools/workflow-status.py` — no cached view to drift); doubles as a light data check (`requirement.md`/`progress.md` missing frontmatter status shows as `?` — progress with a pointer; other phase docs without frontmatter render as their default). A **browsable HTML view** of the same data (board + doc/KB browsing + wikilink nav + per-card diff + recent commits, cross-project, agent-independent) is served by `tools/viewer.py` — a transient localhost read-only server; `workflow-status.py --json` is its machine-readable feed and a scriptable board on its own. For **browsing the project code itself**, the viewer co-launches an optional **gitweb companion** (`tools/gitweb-companion.py`; needs `lighttpd`; disable with `--no-gitweb`, port via `--gitweb-port`) — a read-only, localhost-only gitweb over every project repo + the dev_root and KB repos (a symlink forest, Host-allowlisted, snapshot off); each board card's **`code`** link deep-links into it, at the card's `branch:` (a card may set an optional `branch:` in `progress.md` frontmatter) when set.
- `retro` — review and enhance the skill/docs (M6).

Any phase verb accepts a `use:<skill>` suffix to override that step's implementation for this run.

## Usage logging (self-feedback)

Logging rule lives in `~/.claude/CLAUDE.md` (Skill Usage Logging) — follow it so the retro loop (M6) has data. This skill's `--action` = the verb just run (`new`/`requirement`/`design`/`detail`/`plan`/`test`/`investigate`/`review`/`change`/`resume`/`check`/`retro`/`status` — `status` only when run as a deliberate standalone view, not as a glance inside another verb). Exception: an `investigate` run inside an active requirement logs `--action design` (it is that requirement's design step); `review` logs `--action review` in both contexts. **Implementation-phase task work (writing code against `plan.md`) has no verb of its own — log it as `plan`** (so `plan` covers both authoring the plan and executing its tasks; one record per task/checkpoint). **One event = one record:** a KB write performed as part of an `investigate`/`review` run is covered by that single record — do **not** also log `xg-knowledge-lite/write`; only standalone KB work logs under xg-knowledge-lite. The logging tool warns on non-canonical actions — use the verb names above verbatim.

## Step binding (vendor + runtime override)

Each step resolves to one implementation, by priority: (1) **runtime override** — `use:<skill>` on the verb, or a persisted `workflow.bindings:` step→skill entry in config; (2) **vendored default** — `references/steps/<step>.md`, a forked copy of a source skill's procedure (ours, editable anytime); (3) **inline** — steps with no third-party source. Rebind or edit the vendored file to change behavior; the **contract never changes**, only the implementation behind it. What each vendored step was forked from: `references/provenance.md`.

## References

- `references/templates/` — the ten doc templates (`requirement`, `design`, `adr`, `detail`, `plan`, `progress`, `log`, `test`, `index`, `roadmap`).
- `references/steps/` — the per-step procedures, plus shared mechanisms (`evidence`, `understand`, `adversarial-critic`) referenced by multiple steps.
- `references/split-isolate.md` — 拆分与隔离 field-level mechanics (part axis fields per doc, board axes + monotonic constraints, canonical terms).
- `references/provenance.md` — what each vendored step was forked from (rebind/retro reference).
- `references/steps/adversarial-critic.md` — shared "sharp-cut finder" (fresh-context three-lens critic + invariant-ledger replay + causal-coverage/assumption rules); used by **requirement** grill, **design-grill**, and **review** so the agent reaches the decisive cuts itself.
- `references/steps/grill.md` — shared interactive elicitation used by **requirement** + **design-grill**: the one-question-at-a-time protocol + a **grill-log** (append-only history, proportional — inline for small grills, `notes/grill-<phase>.md` for large/multi-session) + **rollback** (回退 to a previous question = mark it + its dependent subtree `superseded`, re-walk, reconcile the doc — the same supersede discipline as `log.md`/ADRs) + a **convergence auto-verdict** ending every round (materiality-based: slot three-state / decision-level dry check / ADR-weighted open points → a one-line 继续/建议收敛 recommendation; the human still gates). Resume can continue a grill mid-phase.
- **`codebase-design`** (external skill, **referenced not vendored**) — deep-module vocabulary (module/interface/seam/depth/leverage) + two procedures: **Design-It-Twice** (parallel interface alternatives) used by **design-grill** 方案优先, and **dependency categories → test strategy** (DEEPENING) used by **test**; the **deletion test** is used by **design-grill** + **implement** review lens.
- `tools/resolve-project.py` — cwd→project and `--dev-root` resolution (reads the shared config).
