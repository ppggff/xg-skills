# Step: learn — distill redo-input from existing cards

Composes the `investigate` skeleton (KB-first, read-only, dev_root landing, receipts) + `improve`'s
report / chat-gate / roadmap-exit contract + the evidence rule; this file carries only the delta.

**Contract**: `learn <card>…` — same-project 1..N existing cards, any 整体状态; **read-only** on the input
cards and on product code (the run's only write is the report; backfill and KB writes happen strictly
after the human's go); output = one **redo-input report** a future card consumes while drafting. The gate
is a **chat stop**; the human's go is the only way the report acquires adopted status. learn never
creates a card and never rewrites an input card's body (exceptions: the board note · roadmap pointer ·
the narrow facts-marker flip — all named in step 5). In Chinese prose the operation is **学习**, never 蒸馏.

## Procedure

### 0. Card check and 口径
1. Resolve the project; every named card must exist — a miss stops the run with the actual dirs listed.
2. **The one mandatory 口径 question, before mining**: 重做触发 (走偏 / 失败 · 换框架 · 新条件) + 新口径 /
   stakes + 判定标准的变化. Record the answer verbatim, marked 人拍 + date; no answer → the slot stays empty
   and the §1 metadata line's 口径槽状态 says `未问` / `空`. It precedes mining because keep / drop depends on
   it (被新口径否掉的一律 drop).
3. An input card with 整体状态 ∉ {done, dropped} → the report carries §9 输入卡在途警示.

### 1. Probe — the coverage skeleton is mechanical
`workflow-status.py --json` gives each card's `governance` + `carriers` (应有载体 × 存在性) = the §8a
skeleton; never hand-derive the carrier list. A **lite card's carrier table is empty by design** — not an
error: its skeleton is `design.md` + whichever of `facts.md` · `adr/` · `plan.md` · `progress.md` · `log.md`
· `notes/` exist. 存量 cards: their five-phase carriers (`references/legacy/SKILL.md`「Layout」); invalid
governance → full enumeration + a warning row in §8a.

### 2. Mine and select (per carrier, read-only)
Read every existing carrier — `log.md` rework spots and non-md artifact dirs via their pointer rows
included — and classify content **by nature** into the axes:
- **keep / drop**: keep only what is 与设计方案无关 · 花实测换来 · 便宜且真会踩; drop everything the new
  口径 rules out. Each axis's drop side renders as **one aggregate line** (count + reason + sources), never
  itemized — compression is the work; a transcribing report is a failed run. Truncation order when over
  size: decision / negotiation prose first; the Req face and Fact containers are never truncated.
- **Facts axis**: source pointer (cross-card form `NNN 的 [Fact-n]` + link) + one-sentence restatement +
  **时效标注** (原实测 / 验证日期 + 失效风险 / 依赖面) — report-local fields.
- **Non-fact axis** (设计判断 · 机制 · 死路 · 教训 / 起手规则): every item non-binding, with 证伪依据 +
  失效条件 / 适用边界; dead ends are **pointers** to the source card's ADR / rejected candidate row.
- **Execution-zone exposures**: canonical-name pointers — the Req 验证 lines, review reports' 修复决策表 /
  误报澄清, `log.md` rework spots, part-check / lens notes. Test code is pointer-only, never copied.
- **人工澄清轴 — mandatory, never skipped silently**: mine the human's own words — a lite card's
  `notes/human-messages.md` + 确认 lines + 授权记录; a 存量 card's approved ledger rows + grill-log 人工
  chosen rows + sections whose title says 人工 / 澄清 / 前提 (one row per bullet). Output = §8b, **指针分层**:
  every item carries a re-checkable 出处坐标 (卡 / 文件 / 节); a qualitative point carries the verbatim
  quote, never a passage.
- **Qualitative claims: pointer or verbatim, never a restatement** — a pointer where one is reachable
  (ADR / rejected row / 确认 line), otherwise an exact quote + 出处 whose match is mechanically checkable;
  a one-sentence restatement is compression only. 「示意」contrast pair:
  - 可: 「001 Req-37 的定性见 001/design.md Req-37 确认行」（指针）; 或逐字引「执行 SQL 客户端无关」+ 出处
  - 不可: 转述括注「Req-37 = 信封+三类退出码」——转述承载定性, 其错误在消费端不可见
- **KB triage — judgment only, no writes yet**: a lesson that holds in another project → a retro pointer
  (§4); one that dies outside this card group stays in the report; durable environment facts are marked
  for post-go graduation; known-refuted facts are never marked.

### 3. Render — the fixed ten-section shape
Landing: `<project>/investigations/learn-<slug>-<YYYY-MM-DD>.md` (slug names the group; same-day rerun
`-2`); Chinese prose, English domain terms, Mermaid only. § numbers are load-bearing (downstream docs
cite them); a missing section fails Done-when.
- **§1 Header** — (a) metadata line: 输入卡组 · per-card governance / 整体状态 · date · `Supersedes:` (rerun) ·
  `adopted:` (absent until backfill) · 口径槽状态 · cards cited from outside the set; (b) blockquote of
  three declarations: 非真相源 (the cards' authority stays in their own Req / ADR / fact carriers) ·
  非状态源、非承载容器 (never on a resume path) · 无 `adopted:` 行时仅为输入证据; (c) one Reader line: a
  future card's drafting session; §5–§7 are its input evidence, nothing pre-approved.
- **§2 人侧口径** — verbatim + 人拍 date, or 空 + the declaration (人拍原话 / 未问, never self-filled).
- **§3 重做起手规则** — candidate constraints, each with 证伪依据 + 失效条件 (the new card confirms them
  one by one). **§4 过程教训** — group-specific; generalizable ones only as a retro pointer line.
- **§5 事实类资产表** — columns 源 id · 一句复述 · 时效标注 · keep 理由; drop = the aggregate line.
- **§6 非事实类参考** — non-binding banner, then 判断 / 机制 / 死路. **§7 执行区暴露点** — pointers only.
- **§8a 覆盖表** — one row per card: `n 载体 / 已读 a / 跳过 b(理由码)` with **a + b = n**; 理由码 closed
  list: 不存在 · 空文件 · 无本轴内容 · 超规模截断(须点名). **§8b 人工澄清清单** — 源卡 · 项名 / 一句 · 出处坐标 ·
  逐字引句 (定性处) · 时效标注; zero hits → the single 「无」 row.
- **§9 输入卡在途警示** — per in-flight card: its facts may still move; none → one 「无」 line.
- **§10 规模自检行** — line count vs the caps.
**Size**: soft cap **50 lines × N cards**, hard cap **200**; N > 3 → suggest batching at the chat stop
(never refuse). Overflow is a selection failure — re-cut the keep side, never raise the cap.

### 4. Chat stop — the 采纳门
Commit the report (`commit-data-repos.py --project`) → **receipts first** (path + commit + the 规模 line),
then STOP. No go → the report stays archived as input evidence (declaration (c)). Write failure → retry
once, then paste the content into chat.

### 5. Backfill — strictly post-go, the closed list
1. Metadata gains **`adopted: <date>`** on every go, even when the items below are skipped.
2. **Roadmap one-line pointer — unconditional**; plus one candidate line per generalizable lesson.
3. **Board「参考对象注记」** when the trigger is a redo (the report becomes the canonical carrier; index /
   roadmap shrink to pointers); a pure 经验归纳 run skips only this item.
4. **KB Write** (raw + scoped compile) for durable environment facts: the raw body carries a「来源与时效」
   section (源卡 Fact id + 原实测日期 + 方法 + 未重核) and **no dev_root pointer**; compiled → `[[wiki/…]]`,
   not yet → `[[raw/…]]` + `compiled_to: deferred`; known-refuted facts never graduate; write failure →
   a deferred line in the report + receipts.
5. Rerun: the superseded report's header gains `superseded by <新文件名>` (≤2 lines); never deleted.
6. **Shrinking human-written duplicates** (index 暂停说明, rich roadmap entries) to pointers needs the
   human's per-item approval — render the 处置表 (已缩指针 / 人批保留 + 理由) before touching anything.
7. `check` + scoped commit; closing receipts name the backfill commit + the KB commit.
The consuming side (the new card's drafting: 点名合法以 `adopted:` 行为判 · 死路 prior-rejection 比对 ·
重核纪律) lives in lite.md「Drafting」's redo-import sentence and `templates/facts.md`'s header note.

Exceptions bind to existing disciplines: card missing → stop + list · 口径 empty → slot + declaration ·
project unregistered → resolve-project's on-miss path · input size uncapped (the skeleton bounds the face).

Done when: 口径 asked before mining and its source state recorded; skeleton from the tool; all ten
sections in order; §8a a + b = n per card; §8b present (zero-hit = 「无」); every fact item has source id +
时效; every non-fact item non-binding with 证伪依据 + 失效条件; dead ends are pointers; qualitative claims
pointer-or-verbatim; test code pointer-only; size within caps; report committed and the chat stop made with
receipts; backfill only post-go, `adopted:` first. Log once: `--action learn`.
