# xg-dev-workflow

A design-centric development workflow skill. One requirement = one directory holding all of its
docs, organized per project under a config-driven root. The spine is five phases plus a close-out
gate:

需求 (requirement) → 设计 (design, HLD) → 详设 (detail, LLD — optional) → 实现 (plan + implement) → 测试
(test) → 评审 (close-out review, M+)

The point of the skill is to **emphasize design** (not jump from a need straight to an
implementation plan, nor from a frozen architecture straight to a task list) and to keep
**everything in docs** so any session — including a brand-new one — can resume from files alone.

## What it is / isn't

- It **is** an orchestrator + a set of doc templates + per-step procedures. The five phases have
  stable *contracts*; each step's *implementation* is a vendored copy of a well-known skill that you
  can override at runtime or edit anytime.
- It **isn't** the knowledge base. Reusable module knowledge lives in `xg-knowledge-lite`
  (`~/knowledge`), referenced from here via `[[wiki/<project>/<slug>]]` wikilinks.

## Layout

```
<dev_root>/<project>/index.md (card kanban) · roadmap.md · investigations/ · reviews/ · notes/ · legacy/ · NNN-slug/{requirement,design,detail,plan,progress,log,test}.md + adr/ + notes/
```

`dev_root` and the `projects:` map come from `~/.config/xg-knowledge-wiki/config.yaml` — the same
config xg-knowledge-lite uses, so project names line up.

## Key rules

- **Design freezes on approval.** Changing it requires the change-management flow; the
  implementation plan, by contrast, is freely mutable (but dropping a task is logged). An M+
  design also fixes its **验证策略** (per-R E2E scenario + observation point) — verifiability is
  decided at design time, and the test phase inherits it as the coverage skeleton.
- **Two zones, one boundary.** The 设计/详设 freeze is *both* the last binding human gate *and* the
  audience line: requirement/design/detail are **human-first** (you read & approve them);
  plan/progress/test are **Claude-first** (run autonomously, written terse for execution + resume).
  The human re-enters the execution zone only at `log.md` (audit) and the close-out review
  (decision). Every gate asks via a **decision digest** (load-bearing decisions + least-confident
  spots + open questions) so approving doesn't require re-reading the whole doc; small work can
  opt into **merged gates** (XS: 需求+设计 · M: 详设+执行授权 — sizing rules).
- **需求条目 are the traceability spine.** The requirement is an itemized list with stable `R-id`s;
  design / detail / plan / test reference the IDs, so a change localises and coverage holes surface;
  `tools/workflow-status.py --trace <project>/<card>` renders the derived
  R→design→task→test→commit matrix.
- **Evidence only, with provenance.** No guessing, no 望文生义 — every load-bearing claim cites code or
  a doc, marked evidence / 推断 / 假设; doubts are investigated by a subagent. Investigation means
  **logical/causal analysis** (trace the running path, build the mechanism), not a grep-hit list.
- **Commit cadence.** In the execution zone, commit locally after each completed task (runnable
  checks green) and each review fix (one concern per commit); `push` stays human-gated.
- **Split & isolate when work grows.** A design can name **parts** joined at **seams** whose
  contracts freeze with the design (a seam contract disproved in 联调 is an architecture change →
  change-management, never a silent plan edit); a requirement that outgrows one card splits into
  several — the per-project `index.md` is a **kanban** of cards (Phase + 整体状态 + Deps) and
  `roadmap.md` holds not-yet-card work (next-up / themes / someday; items graduate via `new`).
- **Docs + KB are git-managed.** `dev_root` and the KB are each their **own repo** — lazily init'd,
  with autonomous **local** commits at every gate / doc boundary (KB: per Write/Compile/Lint),
  scoped to the acting project (`--project <name>`) so a parallel session's own uncommitted work
  in another project never rides along. `push` stays manual. An optional session-end hook sweeps
  any leftovers — without `--project` it groups dirty paths by project and commits one group at a
  time (message suffixed ` [<group>]`), so the safety net can't mix projects either. Wire it in
  `settings.json`:

  ```json
  {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 <path-to-skill>/tools/commit-data-repos.py"}]}]}}
  ```
- **Per-slice tests, two modes by project.** Implementation tests each vertical slice — **TDD**
  (test-first red-green) where tests run, **test-after** (write/describe, defer the run) for
  "describe, don't run" projects like cbdb. 测试 is then the **consolidation** phase (coverage +
  integration / 联调 / manual + results), not where unit tests are first written.
- **Code earns a test doc and a review doc.** M+ requirements run the `review` close-out gate before
  `done`.
- **Check after every edit.** Cross-references, indexes, and downstream docs are reconciled before
  moving on.
- **Retro improves the skill itself.** Friction found in a session is folded back into the
  templates/steps and recorded in `CHANGELOG.md`.

## Usage

`xg-dev-workflow new <slug>` to scaffold, then `requirement` / `design` / `detail` / `plan` / `test`
to advance (`detail` is the optional LLD step — skip for structure-light XS/S work). `investigate
<topic>` is the single front door for any code investigation (feasibility/runtime/concurrency) — it
enforces the evidence discipline and branches on whether a requirement is active. `diagnose
<symptom>` is the front door for defect localization (bug / crash / perf regression) —
feedback-loop-first: a tight red-capable repro loop before any theory, ranked falsifiable
hypotheses, the fix landing via Prove-It. `resume <slug>` to pick up in a new session, `change` to
revise a requirement/design, `check` to lint, `status` for the card view (every card's pipeline
position + next step, computed from the docs by `tools/workflow-status.py`; `python3
tools/viewer.py` serves the same data as a browsable localhost HTML viewer — board, doc/KB browsing,
wikilink nav, per-card diff, recent commits, plus an optional co-launched **gitweb companion** for
browsing the project repos' code, deep-linked from each card's `code` link; needs `lighttpd`,
disable with `--no-gitweb`), `retro` to improve the workflow. Append `use:<skill>` to any phase verb
to swap that step's implementation for the run.

See `SKILL.md` for the full contract; `references/steps/` for each step's procedure and what it was
forked from.
