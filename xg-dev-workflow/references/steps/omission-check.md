# Step: omission check (M3)

Authored inline. Run after **any** doc edit (and as the `check` verb). Cheap consistency
pass so nothing silently drifts. Inspired by xg-knowledge-lite Lint, scoped to a
requirement dir.

## How to run (cost)

Split the checklist by nature (SKILL.md「Subagent model assignment」):

- **Deterministic subset → script, zero tokens**: link/wikilink resolution, frontmatter
  status/updated presence, index-row existence, 项目根散件, board monotonic constraints,
  R-id trace *existence*, `[F<n>]` citations resolving to an active block in the card's
  `facts.md` (doc-local 事实清单 for standalone docs; not yet scripted — runs with the
  judgment subset until a checker exists). **The ledger checks ship as `workflow-status.py --check
  <project>/<card>`** (id-reference integrity · derived-status field mappings (SKILL.md「Ledger」) · depends-on
  acyclicity · approve-note format · single-active-block · **design.md unconditional-section
  existence** (思路/速览/How-it-meets/影响面; designs created before 2026-07-31 grandfathered;
  conditional sections stay in the judgment subset) · the **(i) governance checks**
  (`bad-governance-value` / `missing-governance-field` post-cutoff / `ledger-mode-no-ledger` /
  `doc-gate-has-ledger` — unconditional, ledger or not); exit 1 = findings) — run it on any
  card after a doc edit (the section check needs no ledger); semantic contradiction with
  approved decisions stays in the judgment subset. The remaining items still lack a checker and run with the judgment subset
  (roadmap item, not a prerequisite).
- **Judgment subset → one `model: sonnet` agent**: phase consistency, terminology,
  reasoning-shown, provenance marks, snapshot bloat, … — give it the requirement dir + this
  checklist, take back only the violation list; the orchestrator fixes what's flagged, which
  re-verifies each finding.
- **Right after an edit, inline is fine** — the docs are already in context, so a self-check
  costs little. Delegation pays off on a standalone `check`, after `resume`, or a full sweep
  of a large card.
- **Mode conditioning (017 S6)** — the checklist is per-card-mode (`card_mode` cascade,
  `--check` (i)): on a **doc-gate** card, ledger-id / derived-status / facts-marker checks
  naturally skip (no files); the Panel-receipts item verifies the scaled digest §1 lines
  instead; the three-class items read the doc-carried form (decisions in sections, facts in
  「事实清单」,「提议变更」cleared after confirm). Everything else — links, indexes, phase
  consistency, R-trace, enumeration criteria, terminology, sweeps, roadmap/KB/architecture,
  scope — runs unchanged. Legacy (no field) cards keep their original behavior end to end.

## Checklist
- [ ] **Links resolve** — every `[[wiki/<project>/<slug>]]` resolves (KB raw/concept); every
      relative link (`./design.md`, `./adr/NNNN-*.md`) points to an existing file.
- [ ] **ADRs wired + hygienic** — each `adr/NNNN-*.md` is linked from `design.md`; superseded
      ADRs carry the right status; **no `## Amendment` block** (decision changes are new
      superseding ADRs, not appended); a superseded ADR's forward cross-ref is **≤2 lines**;
      body stays lean (≤ ~200 lines).
- [ ] **Indexes current** — the requirement has a row in `<project>/index.md` with the
      right Phase + 整体状态; the project appears in `<dev_root>/index.md`.
- [ ] **项目根无散件** — the project root holds only `index.md` / `roadmap.md` and the spec'd
      dirs (`NNN-*/`, `investigations/`, `reviews/`, `notes/`, `legacy/`); a stray file at the
      project (or dev_root) root gets flagged with its suggested home (notes/ scratch ·
      investigations/ findings · legacy/ pre-workflow) — don't silently leave it.
- [ ] **Board (kanban) consistency** — **仅对已迁移到看板格式（含 `整体状态`/`Deps` 列）的 per-project
      `index.md` 生效**；旧格式（`NNN|Title|Phase|Status`）的项目索引**免检**，直到自愿迁移（迁移是 per-project
      opt-in，见 index 模板向后兼容注）。对已迁移的：card 依赖图（Deps 的 NNN）**无环**；`整体状态` 满足单调约束
      —— `done` ⇒ test 通过 且 `Phase=测试` 且各 gate 已过 且 close-out review doc 或 `XS/S — review
      skipped` 注已存在（即下方 Close-out review 项）; `backlog` ⇒ 没有超出 requirement 脚手架的阶段文档;
      `paused/blocked` ⇒ 至少一个阶段已起步. `整体状态` 是调度轴，**不**强映射内部阶段 status 值（那些不上看板）。
- [ ] **Phase consistency** — requirement↔design↔detail↔plan↔test don't contradict each
      other (e.g. a success criterion with no test; a plan task with no design basis; a
      `detail.md` structure/mechanism with no design home or no upward trace to a requirement
      条目 (R-id); a frozen design edited without a change-management entry; **a design interface
      op / contract invariant with no test** once `test.md` exists; an acceptance criterion or test result recorded as a subjective
      `done`/`pass` instead of the binary `[x]/[!]/[ ]` walk).
- [ ] **需求条目 (R-id) traceability** — every `requirement.md`「需求条目」`R-id` has a design home
      (`design.md`「How it meets」), ≥1 `plan.md` task (`Implements:`), and ≥1 `test.md` row, once
      those docs exist; each Effect criterion cites its `R-id`; IDs are stable (no renumber — retired
      items carry a note). A requirement still on the old prose-only template (no「需求条目」) is exempt
      until it's voluntarily migrated — don't flag its absence.
- [ ] **Enumeration criteria well-formed** — every "every X …" Effect criterion declares its
      枚举键 + 必填列 (template Effect note); a `[x]` one has its table with **key matching the
      declaration and all rows complete**; partial-completion phrasing ("已完成 N 条") or a
      full table under a **different key** fails even when the prose sounds covered — check the
      criterion's words against the table's key, not the doc's claim. Criteria on the
      pre-declaration template (created before 2026-07-30) are exempt until touched.
- [ ] **Panel receipts present** — each gate this card passed traces to its adversarial-panel
      receipts (grill-log / round-closing messages cited from the digest, per
      adversarial-critic.md「Receipts」): decision-level checkpoints have attack-lens receipts
      (or an explicit XS/S tier-down note), and the gate has a criterion-conformance verdict
      list. A gate with zero receipts was approved on self-certified work — flag it. Gates
      passed before 2026-07-30 are exempt (grandfathered). Doc-gate cards: the receipt lives
      in the round-closing chat message and is cited from the scaled digest §1
      (gate-digest.md「Doc-gate cards」) — verify those lines, not a grill-log file.
- [ ] **Transcription additions bounded** — （落纸补充）markers (grill.md Discussion-first
      flow) appear only below decision level, and none survives a passed gate (approve clears
      them; a decision-level item carrying one is a finding).
- [ ] **Provenance marked** — load-bearing claims in requirement/design/detail carry a provenance
      marker (evidence-cited / 推断 / 假设); an uncited non-trivial assertion is flagged `UNVERIFIED:`
      or `(assumption)`, not left bare (M1).
- [ ] **Comparison tables carry provenance** — any 方案/alternatives comparison or evaluation
      table in a decision-zone doc (design/detail/ADR/proposal note) marks each comparative
      claim about existing code (VERIFIED / INFERRED / 推断); a bare Pros/Cons table with
      unverified code claims fails (design-grill 方案优先 — verify-before-table).
- [ ] **Grill-log codename legend** — a persisted `notes/grill-*.md` that uses session-local
      codenames (方案 T/S, N1 …) carries a legend line up top defining each (grill.md
      「Codename legend」).
- [ ] **Reasoning shown (human-first docs)** — in requirement/design/detail/ADR/review and
      investigation-notes prose, each
      load-bearing conclusion is *derived in the text* (evidence → mechanism → conclusion), not
      bolted onto a fact table; a section that is only citations + a verdict is flagged — the
      approver must be able to check the inference, not just the sources
      (`references/doc-conventions.md` Reasoning-shown).
- [ ] **Part traceability (split designs only)** — each part in `design.md`「Decomposition/Parts」
      traces to its `plan.md` tasks (`Part:` 字段) and `test.md` 分节; each **seam** contract has a
      **联调级 (real-neighbor)** test (扩自上一条 "每个 interface op/invariant 都要有测试"). An
      **un-split** design is **not required** to have a Parts section — do **not** flag its absence.
      The deterministic half is `--check` (h): `Part:` values ⊆ the new-format table's canonical
      names (legacy tables without an `R` column are skipped) — this item keeps only the judgment
      half (test 分节 coverage, seam 联调级 tests).
- [ ] **progress.md is a snapshot, not a log** — current-state only; reusable findings/decisions are **linked** (KB / `design.md`), not restated; superseded detail pruned or moved to `notes/`. If it has bloated with copied KB/design content, slim it. Deterministic half: the template's **≈150-line cap** — an over-cap file is flagged for pruning, not grandfathered.
- [ ] **Design completeness** — `design.md` has its required elements: a **思路** one-paragraph
      TL;DR, a current **速览** (regenerated, not appended), the **diagrams** (module-interaction
      + data-flow **walking one named flow end-to-end** — a static relationship map no flow
      traverses fails; **Mermaid preferred**, ASCII fallback), the **影响面 (impact surface)** section,
      the **验证策略** table (M+ cards), the **存储足迹** table (when the design touches storage),
      and — if it introduces a module — that module's **interface contract** (operations +
      invariants, not signatures); and — for structural cards whose `design.md` is not yet
      frozen and whose `created` date is on/after 2026-07-30 — the「Design qualities」section
      carries a per-new/extended-module **module-depth record** (deletion-test conclusion +
      seam adapter count); frozen or pre-cutoff designs are exempt.
- [ ] **Close-out review** — a requirement at `done` / Phase=测试 complete has **either** a close-out
      review doc under `notes/review-*.md` **or** an explicit skip/grandfather note in `progress.md`
      (`XS/S — review skipped`, or `pre-gate done` for cards finished before the gate existed —
      both satisfy the gate and are honored by `workflow-status.py`). Size (XS/S vs M+) is a human judgment (see SKILL.md「Requirement sizing」); M3
      checks only that **one of the two is present** — an existence check that needs no size
      signal of its own (the governance mode is a separate axis, judged by the mode-field
      cascade — 017 ADR-0001), and an
      M+ card that silently lacks both is the violation. (Mirrors the board `done` monotonic constraint.)
      **Shape check** (existence-level only): when a review doc exists and the design has a 验证策略
      table, the doc contains the per-row promised-scenarios 核对结果 (content verification itself
      is review.md's job).
- [ ] **Status/dates** — frontmatter `status` and `updated` reflect reality; design is
      `frozen` only if approved.
- [ ] **Terminology consistent** — each domain term in the doc has a **single canonical
      form** within its bounded context (no same-concept-many-names; no same-word-two-meanings
      *inside one context*). Terms match the canonical term of their KB concept
      (`[[wiki/<project>/<slug>]]`) / the project-or-common `CONTEXT-MAP.md`. A word reused across
      **different contexts** is fine if each is scoped (note the homonym) — don't false-flag it.
      **Form follows the global Language rule** — an established EN technical term stays EN
      (`heap`, not 堆): a force-translated term is drift **even when used consistently**.
      Drift → pin canonical term + `_Avoid_` (+ `_Context_` for scoped terms), record the
      durable ones in the KB concept / CONTEXT-MAP, rewrite the doc. Makes "sharpen language" a
      verified gate, not hoped-for behavior.
      **术语纠正 (human-initiated):** the human flagging a term while reading any doc ("这里该写
      heap") is this check firing out-of-band. Order matters — **pin in the project/common
      `CONTEXT-MAP.md` first** (`heap` + `_Avoid_ 堆`; create the map lazily): that is the anchor
      every later M3 run reads, so one correction propagates to all future docs. Then update the
      owning KB concept if one exists, rewrite the current card's docs now (other cards heal
      lazily at their next M3), and append a `log.md` entry when inside a card.
- [ ] **Superseded phrasing swept（换语义类 change 后）** — if the round included an M2
      mode-变更/撤销（or an ADR that retires phrasings）, the supersede sweep ran
      (`tools/check-superseded-phrases.py`, terms from the ADR's 被取代表述 section) and every
      hit was rewritten / annotated as 历史表述 / justified; module & term names re-checked
      against their new responsibilities (a name asserts nothing false, so plain consistency
      reads miss its drift). Change-log entries quoting old semantics are exempt (history).
- [ ] **Knowledge captured & compiled** — any reusable module insight discovered this round was
      written to xg-knowledge-lite **via its Write flow (compliant frontmatter — not a bare file
      write), and either compiled to a concept or explicitly marked deferred** (`compiled_to:
      deferred — <why>` in the raw's frontmatter); not left only in the requirement dir, and not
      left as an uncompiled raw (which `kb-backlog.py` will flag each
      session). Compile back-annotates `compiled_to:` and updates `wiki/index.md`.
      **XS cards: satisfied by default** — no per-round capture/defer statement required;
      still write to the KB when a find is plainly reusable.
- [ ] **Roadmap fed** — deferred work this card surfaced (Future / Discovered issues) is captured
      in `<project>/roadmap.md`, not only buried in the card; a graduated roadmap item links its NNN.
- [ ] **Architecture / invariants current (KB)** — a frozen design that changed the system's shape
      updated `[[wiki/<project>/architecture]]`, and any durable invariant it established reached the
      subsystem `*-invariants` ledger (the as-built KB didn't silently drift).
- [ ] **Scope** — no out-of-scope changes crept in (cf. requirement Scope + the project's
      change rules, e.g. cbdb's).

Report what's missing and fix it (or list it) before considering the edit done.
