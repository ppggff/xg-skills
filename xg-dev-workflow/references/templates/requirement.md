---
id: NNN
title: <requirement title>
project: <project>
status: drafting | confirmed | superseded
governance: doc-native  <the card's governance mode. New cards are single-track doc-native
  (026 Req-32 — sizing scales volume, never the mechanism); `new` pre-fills it and the human
  ratifies at the 需求 confirm gate (mode stays the gate's FIRST judgment item), effective with
  `status: confirmed`. 存量 values stay valid on their own cards: ledger (010–017 M+),
  doc-gate (017 XS/S), doc-native-pilot (card 026); omitted = legacy (pre-017 only — new cards
  must declare, `--check` flags the omission). Upgrading is a one-time explicit M2
  (doc-gate→ledger, 017; `*→doc-native`, 026 HLD-13), past decisions never backfilled.>
issue: <optional — originating tracker issue(s)/ticket(s): id or URL, comma-separated. The
  card↔issue anchor; also the outward ref code comments may cite. Omit when there is none.>
created: YYYY-MM-DD
---

# 需求 NNN: <requirement title>

> Phase gate: this file must be **confirmed** by the human before design starts.
> **Reader: human-first** (decision zone — you read & confirm it). Write it to be reviewed: prose,
> rationale, sharp boundaries. Claude also implements against it. (See SKILL.md「Two zones」.)
> **Three-class marking:** decisions cite their ledger id (`decisions.md`), facts cite `[F<n>]`
> (`facts.md`); unmarked prose is synthesis — freely rewritable, must not contradict approved
> decisions. (Doc-gate cards carry the same three classes **in the doc**: decisions in their
> own sections, facts in a doc-local「事实清单」, pending proposals in「提议变更」— 017 D2.)
> **Doc-native cards (026): decisions ARE doc blocks.** Each 需求条目 is one block —
> `### Req-<n> <state> — <标题>` (states proposed/approved/superseded/retired) + the five
> load-bearing fields (`- 陈述:` `- 类型:` `- why:` `- provenance:` `- depends-on:`), lettered
> clauses `- (x) …` inside 陈述, and machine-read annotations appended per event:
> `- approved: <date> gate <hash> (single|batch Ask-<n>: 「原话」)` (date = the gate commit's
> author date; ask-id mandatory from the 2026-08-27 cutoff) · `- 变更/退役: <why> (M2 <hash>,
> <尾注>)` · `- 澄清: …(凭据)` · `- 来源: …` for transported blocks. No decisions.md; facts
> cite `[Fact-n]` (`facts.md` stays, Req-41); the 条目节首 index is a generated view
> (workflow-status render_index — never hand-edit); the approved-block compare face is guarded
> by the diff guard + git anchor checks ((ac)/(ad)). **陈述/why take indented rich forms**
> (multi-paragraph / nested lists / tables / code / mermaid; 2-space indent) opened by a
> one-sentence **lead line (导语行)** — rules: doc-conventions「载重散文的归宿」(028).

## Context (背景)

Why this is being done — the problem or need, what prompted it, the intended outcome.
State assumptions explicitly. Every non-trivial claim cites code (`func()` in `file.c`) or a
doc/`[[wiki/<project>/<slug>]]`; **mark each load-bearing claim's provenance** — evidence-cited /
推断 (inferred) / 假设 (assumption) — per M1. e.g.（示意）：
「serverless 池化后同集群可有多个 coordinator（`pool_register()` in `pool_mgr.c`——evidence）；
现网已出现双 launcher 并跑（工单 #123——evidence）；预计规模一年内 10×（假设——容量组口头，
待书面确认）。」——每个载重句子自带标注，读者一眼可分「查过的」与「赌的」。

## 需求条目 (Requirement items) — the canonical itemized list

The atomic, individually-trackable statements of what is required — **the traceability spine**.
One row = **one** requirement (a title with "and" is two). Each gets a **stable ID** (`R1`, `R2`,
…): never renumber; to drop one, mark it `retired (YYYY-MM-DD: why)` rather than reusing the
number — tool-recognized forms (workflow-status.py RETIRE_ID/RETIRE_MARK): strike the id
(`~~R9~~`) or put `retired` in the id cell, **or** begin the statement cell with the mark
(`~~旧陈述~~ retired (…)`); a mid-sentence "retired" elsewhere doesn't count.
Scope / Effect below **and** downstream docs (`design.md`「影响面」&「How it meets」, `detail.md`
可追溯, `plan.md` tasks, `test.md` coverage) **reference these IDs** instead of restating the text.

**需求条目 vs Effect — keep them distinct:** a 条目 states **what** is required (the need); an Effect
criterion states the **checkable condition that proves it** (the how-we-verify), and cites the R-id
it tests. E.g. 条目 `R1: 同一时刻至多一个 coordinator 运行 autovacuum` → Effect `观测 pg_stat_activity
中 launcher ≤ 1（verifies R1）`. Don't duplicate one as the other; they are need ↔ acceptance.

| ID | 需求条目 (one atomic statement) | 类型 (功能/约束/非功能) | provenance (evidence / 推断 / 假设) |
|----|--------------------------------|------------------------|-------------------------------------|
| R1 | … | … | `func()` in `file.c` / `[[wiki/…]]` / 假设 |

（存量表格形如上;doc-native block 的 陈述 写法——contrast pair（示意）:
✗ `- 陈述: 照案行沿既有义务(recommendation+trade-off,自含措辞引旧卡不重述),新增仅两点:evidence 锚必填、一行说不清→升真判。`——单行密句
✓ `- 陈述: 照案行新增两点义务。`——导语行(一句白话,句号收尾 ≤80 字)
✓ `  - evidence 锚必填;一行说不清 → 升真判(其余沿既有)。`——缩进续行,富格式随内容
rules: doc-conventions「载重散文的归宿」。）

## Scope (范围)

- **In scope:** … (by R-id where it sharpens the boundary)
- **Out of scope:** …
- **Affected (初步影响面):** modules / callers / consumers likely touched — full analysis in `design.md`「影响面」.
- **拆分审视:** 拆 / 不拆 — <一句理由>  (the split-review beat's verdict — steps/requirement.md
  beat 8; recorded even when 不拆, restated in the gate digest)

## Constraints (约束)

ABI / interface stability, project change rules, compatibility, performance, environment.
(e.g. cbdb: no ABI/extension/SQL-interface changes unless requested; changes minimal, module-local, reversible.)

## Effect (效果 — measurable success criteria)

Reframe the ask as testable conditions. "Done" means each of these is true. **Each criterion cites
the R-item(s) it verifies** (so a changed `R` localises to its criteria + tests).
**Byte/output-comparison criteria declare their compare face** (default-mode output vs the
verbose/itemized stream — 026's E6 paid one clarification round for leaving it implicit).
**Enumeration criteria declare their key.** A criterion of the form "every X …" names its
**枚举键** (what one row is) and **必填列** (at minimum: 可达性/适用性 + 依据) in the criterion
text; it flips to `[x]` only when the table exists with every declared row complete — never on
partial-completion prose, and never via a table keyed differently (探了 5 种 DDL ≠ 核了 7 个写点):

- [ ] … (verifies R1)
- [ ] 每个写点值来源正确 — 键=写点, 列=调用者/可达性/依据; 表全行齐才勾 (verifies R2)（示意）

## 人工澄清清单处置 (optional — doc-gate cards consuming an adopted learn report only)

<!-- Fill ONLY when this card is a doc-gate card whose beat 1 consumed an adopted learn
     report (steps/requirement.md Axis→section mapping, 024 R2): one row per §8b 清单行 —
     类别 (习惯/意图 vs 事实) · 处置 (续期 / retire / Open) · 去向. All rows complete before
     the confirm gate; the gate line cites this table. Ledger cards use a grill batch round
     instead — leave this section absent there. -->

| 清单行 | 类别 | 处置 | 去向 |
|---|---|---|---|

## Future (未来)

What is deliberately deferred; extensibility expected later; what we are NOT solving now and why.

## Open questions

- …

## Change log

<!-- Doc-native cards: DO NOT create this section (026 Req-31, 护栏 4 switch 2026-08-27) —
     gate events live in block approved annotations, content changes in 变更/退役 annotations,
     doc-level events in log.md. Ledger/doc-gate/legacy cards keep it as before. -->

- YYYY-MM-DD — created.
<!-- On any requirement change, add a dated entry here and trigger the change-management flow
     (M2). State each affected 条目's mode — 追加 (new R-id) / 变更 (supersede) / 撤销 (retire,
     keep the ID) — it drives the scoped downstream propagation. Doc-gate cards: gate passages
     also land here as `- <date> — <状态>（gate <receipts-commit short hash>）` — the audit
     anchor (017 S4). -->
