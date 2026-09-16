---
id: NNN
title: <slug>
project: <project>
governance: lite
status: draft      # draft | executing | closing | done — checks read `status`, not `state`
created: YYYY-MM-DD
go:                # at go: the dev_root commit (tag optional) of the authorization baseline
skill:             # the skill repo HEAD the card was drafted against; re-read the rules when it moves
---
<!-- templates/design-lite.md — the design.md skeleton for a lite card (steps/lite.md「Card files」).
`new` copies it verbatim and fills id / title / project / created. Text after a heading is guidance; keep or delete.
Form: conventions-core.md「Form is judged per item」— a field label owns a block whose content sits on the indented
lines below; clauses are line-leading `- (a)` (constraints.md Id-1); a table cell holds one sentence (Doc-3). -->
# NNN <title>
## 当前摘要        problem · approach · key limits · unresolved risks (top; ≤200 字 when long); present tense — a dated update is a 变更 line, not a paragraph here
## 目标与边界      deliver what · not what · the commitment blocks (index table optional, >5 blocks)
### Req-1 待验证 — <标题>        ← 状态词 ∈ 待验证 · 已验证 · 验证失败 · 阻塞 · 仅方案 · 放弃
- 陈述:
  <lead sentence, then each clause on its own line>
  - (a) <clause — cited as [Req-1-a]>
  - (b) <clause>
  - alt: <the alternative weighed and why it lost — when there was one>
- 验证: <method> → <outcome + evidence pointer, product commit SHA(s) included>; the detail lives in 测试与验证
- 来源: <who asked · which note or message>
- 变更: YYYY-MM-DD <what changed, quoting the human's confirming words> ← newest-first; mandatory whenever the commitment changes
- 确认: YYYY-MM-DD <go or re-confirmation, quoting the human>
## 当前方案        candidates (≥2, side by side) · chosen path · impact forecast (labelled) · trade-offs · feasibility evidence
### 契约与不变量   one block per contract — **mandatory** once any Req mentions a lock · signal · exit code · disk format · output shape · external environment · irreversible operation (steps/lite.md「Triggers」), else one line `- Inv: 无（原因）`; the close-out review walks each block
### Inv-1 <标题>
- 不变量: <one falsifiable sentence>
- 归宿: <the Req ids it protects>
- 检验: <command · test · reader check>
## 待解问题与证据  open questions as a list (`- Q-n …`; an answered one is struck through with its answer); facts are `Fact-n` in facts.md, never inline
## 任务            next steps · remaining work (→ plan.md from `templates/plan.md` when tasks crowd the doc)
## 测试与验证      plan as blocks (`### V-n` · 验证什么 · 判据) or a layered list — never long cells; results table: one word + one sentence per row · 单次测不到的 · 未验证项
## 授权记录        one line per event, newest-first: date · **go / go（续）/ 答复** · Req ids · scope & not-in-scope · 人原话：「…」(verbatim from notes/human-messages.md) · lens: 已做 n / 未做（原因）· review: <tier>（原因）· commit; a correction is a new line — the old line stays
