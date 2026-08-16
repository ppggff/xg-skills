# Step: learn (distill redo-input from existing cards)

Authored inline; **composes** the `investigate` skeleton (KB-first, read-only, dev_root
landing, Receipts — `investigate.md`) + `improve`'s report / chat-gate / roadmap-exit
contract (`improve.md`) + the M1 evidence discipline (`evidence.md`). This file carries
only the delta; it never restates those rules.

Contract (design 020): `learn <card>…` — **same-project 1..N existing cards** (any 整体状态);
**read-only on the input cards' docs and on product code** (the run's only write point is the
report file; backfill and KB writes happen strictly after the human's go); output = one
distilled **redo-input report** consumed by a future card's requirement step (beat 1). The
gate is a **chat stop**; the human's read + go there is the **only** way the report acquires
approved-note identity. learn never creates a card and never rewrites input-card bodies
(exceptions: board note / roadmap pointer / the consumption-side facts-marker flip — all
named below).

## Procedure

### 0. Card check & 口径 (before any mining)
1. Resolve the project (`tools/resolve-project.py`); every named card must exist in it —
   a miss stops the run with the actual card dirs listed (improve region-check 同款).
2. **The one mandatory 口径 question (R11), asked before mining**: 重做触发 (走偏/失败 ·
   换框架 · 新条件) + 新口径/stakes + 判定标准的变化. Record the answer **verbatim**, marked
   人拍 + date; no answer → the slot stays empty and the declaration is carried by the §1
   metadata line's 口径槽状态 field (`未问`/`空`) — never a fourth blockquote line.
   It precedes mining because the keep/drop criteria depend on it (被新口径否掉的一律 drop).
3. In-flight marking: input card 整体状态 ∉ {done, dropped} → the report carries the
   输入卡在途警示 section (§9).

### 1. Probe — the coverage skeleton is mechanical
`workflow-status.py --json` → the card's `governance` + `carriers` (应有载体 × 存在性) **is**
the coverage-table skeleton. Never hand-derive the carrier list — the closed-list mapping
lives only in the tool (it mirrors SKILL.md「Layout」). `governance: invalid` → full
enumeration + a warning row in §8; legacy cards arrive as existence-axis inferred set ∪ full
enumeration — mine what exists, zero "missing governance file" noise.

### 2. Mine & select (per carrier, read-only)
Read each existing carrier — including `log.md` (rework spots) and non-md artifact
directories via their pointer rows — and classify content **by nature** into the four axes
(来源不限阶段):

- **keep/drop (R12)**: keep only what is 与设计方案无关 · 花实测换来 · 便宜且真会踩;
  everything 被新口径否掉的一律 drop. The drop side of each axis renders as **one aggregate
  line** (count + reason, naming its sources) — never itemized. Compression is the actual
  work: a report that transcribes is a failed run.
  **Truncation order (超规模截断)**: decision/negotiation prose goes first; the requirement-item
  face (R tables) and F containers are the design-agnostic layer — never truncated.
- **Facts axis (R3)**: per item = source pointer (existing cross-card form `NNN 的 [F<n>]`
  + link; a doc-gate input card's doc-scoped containers use the doc axis `NNN/<doc> 的
  [F<n>]`) + one-sentence restatement + **时效标注** (原实测/验证日期 + 失效风险/依赖面) —
  report-local fields, not part of the provenance/facts marker vocabulary.
- **Non-fact axis (R4)**: every item (设计判断 · 机制 · 死路 · 教训/起手规则) is marked
  non-binding and carries **证伪依据 + 失效条件/适用边界**; dead ends are **pointers** to the
  source card's ADR / design.md Alternatives table (anti-resurrection hooks), never restated.
- **Execution-zone exposures (R6)**: point by canonical name — test.md Coverage/回归/Results ·
  评审报告 修复决策表/误报澄清 · log.md rework spots · part-check artifacts. **Test code is
  pointer-only** (file/case names), never copied.
- **KB triage (D7) — judgment only, no writes yet**: 换个项目还成立的 lesson → M6 side
  (pointer in §4); 换组卡就不成立的 → stays in the report. durable environment facts →
  marked for post-go graduation; known-refuted facts are never marked.

### 3. Render — the fixed report shape
Landing: `<project>/investigations/learn-<slug>-<YYYY-MM-DD>.md` (slug names the input-card
group; same-day rerun appends `-2`, `-3`, …). Chinese prose, English domain terms; Mermaid
only. In Chinese prose the operation is called **学习** (matching the verb name `learn`) —
never 蒸馏 (user convention, 2026-08-13). Fixed order of the **ten sections** (§ numbers are
load-bearing — downstream docs cite
them); a missing section fails Done-when (and the omission-check judgment item):

- **§1 Header block** — three fixed pieces:
  (a) **metadata dotted line** (improve form): 输入卡组 · per-card governance/整体状态 ·
  date · `Supersedes: <旧文件名>` (rerun only) · `adopted:` (absent until backfill) ·
  口径槽状态 (人拍/未问) · 输入集外被引用卡 id;
  (b) **blockquote — three declarations**: 非真相源 (the cards' authority stays in their own
  decisions.md/facts.md — state it in those terms; no template carries a canonical
  wording) · 非状态源、非承载容器 (never on any card's resume path) · 无 `adopted:` 行时仅
  input evidence (conditional sentence; the `adopted: <date>` line is written only by the
  post-go backfill step);
  (c) **single Reader line** (test.md form): reader = a future card's requirement/design
  session; §5–§7 are its input evidence, nothing here is pre-approved.
- **§2 人侧口径** — the R11 slot: verbatim + 人拍 date, or 空 + 首部声明 (source 二态:
  人拍原话 / 未问 — never self-filled).
- **§3 重做起手规则** — candidate constraints, each with 证伪依据 + 失效条件 (non-binding;
  the new card's confirm gate adopts/rejects them one by one).
- **§4 过程教训** — group-specific lessons; generalizable ones appear only as an M6
  pointer line.
- **§5 事实类资产表** — external key = the source cards' actual F containers, tiered per
  doc-conventions「Provenance containers」(cite the owner, don't restate); columns: 源 id ·
  一句复述 · 时效标注 · keep 理由; drop = the one aggregate line.
- **§6 非事实类参考** — non-binding banner first; 判断 / 机制 / 死路 subsections (rules
  in §2 Mine).
- **§7 执行区暴露点** — canonical-name pointers + one pointer line per non-md probe dir.
- **§8 挖掘面覆盖表** — one row per input card: `n 载体 / 已读 a / 跳过 b(理由码)` with
  **a+b=n** (mechanical self-consistency; 「存在」and「已覆盖」stay separate columns).
  理由码闭列: 不存在 · 空文件 · 无本轴内容 · 超规模截断(须点名). No expected set (invalid) →
  its warning row; legacy → the two markers shown as probed.
- **§9 输入卡在途警示** (distinct name from improve's 在途卡提示节 — different semantics) —
  per in-flight input card: its facts may still move; consumers re-verify. No in-flight
  input card → the section carries a single 「无」 line (the ten-section shape is invariant).
- **§10 规模自检行** — line count vs the caps.

**Size discipline (D4)**: soft cap **50 lines × N input cards**, hard cap **200**; N>3 →
suggest batching at the chat stop (never refuse). Overflow is a selection failure — re-cut
the keep side; never treat it as a reason to raise the cap.

### 4. Chat stop — the 采纳门
Commit the report (`tools/commit-data-repos.py --project`) → **receipts first** (report path
+ commit + the 规模 line), then STOP. No go → the report stays archived as input evidence
(declaration (c)); it does **not** unlock the requirement step's grill-relief clause.
Report write failure → retry once, then paste the content into chat (improve 同款).

### 5. Backfill (strictly post-go) — the closed list
1. Report metadata gains **`adopted: <date>`** — written on every go, even when items below
   are skipped (the adoption gate's persistent, cross-session mark).
2. **roadmap one-line pointer — unconditional** (orphan-proofing; improve step 4.4 line
   form). Plus one roadmap candidate line per generalizable lesson (none → record zero).
3. **Board「参考对象注记」** — required when the trigger is a redo (搬移语义: the report
   becomes the canonical carrier; index/roadmap shrink to one-line pointers); a pure
   经验归纳 run skips this item only. Section form: the registered optional section in
   templates/index.md.
4. **KB Write A+B** (xg-knowledge-lite Write raw + scoped compile) for durable environment
   facts: raw body carries a「来源与时效」section (源卡 F-id + 原实测日期 + 方法 + 未重核) and
   **no dev_root pointer** (KB one-way); topic-cluster granularity (1..k notes); known-refuted
   facts never graduate; pointer rule — compiled → `[[wiki/…]]`, not yet → `[[raw/…]]` +
   frontmatter `compiled_to: deferred`; write failure → a deferred line in the report + chat
   receipts. The report keeps pointers only.
5. Rerun case: the superseded report's header gains `superseded by <新文件名>` (≤2 lines);
   the old report is never deleted; "current" = whatever the roadmap/board pointers name.
6. **存量副本缩指针** — shrinking human-written rich duplicates (index 暂停说明, roadmap
   rich entries) to one-line pointers **requires the human's per-item approval**; render the
   处置表 (已缩指针 / 人批保留 + 理由) before touching anything.
7. M3 + scoped commit. Closing receipts name the backfill commit + the KB commit.

Consumption-side disciplines live at their owners — steps/requirement.md beat 1 (点名合法以
`adopted:` 行为判 · 轴→节区映射 · 采纳门 · 重核纪律 · 死路 prior-rejection 比对 · 重做冷起
触发半句) and templates/facts.md 头注 (the cross-card narrow marker-flip); this step only
points there.

### Exceptions (all bind to existing disciplines)
Card missing / project mismatch → stop + list (0.1) · 口径 empty → slot + declaration (0.2) ·
KB project unregistered → resolve-project on-miss path · report write failure → retry once,
paste chat · KB write failure → deferred line + receipts · input size — no cap (the coverage
skeleton bounds the mining face; R12 governs output size only).

## Done when
- 口径 asked **before** mining, source 二态 recorded; coverage skeleton taken from the tool
  (zero hand-derived carrier lists); all **ten** sections present in order; §8 numbers
  self-consistent (a+b=n per card, no silent caps); every fact item carries source id +
  时效标注; every non-fact item carries the non-binding mark + 证伪依据 + 失效条件; dead ends
  are ADR/Alternatives pointers; test code pointer-only; size within caps (or the keep side
  re-cut); report committed and the chat stop made with receipts; backfill ran only post-go
  and walked its closed list (`adopted:` line first); M3 run. Log once per run:
  `log-usage.py log --skill xg-dev-workflow --action learn …`.
