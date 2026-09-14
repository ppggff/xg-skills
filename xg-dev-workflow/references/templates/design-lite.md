---
id: NNN
title: <slug>
project: <project>
governance: lite
status: draft      # draft | executing | closing | done — checks read `status`, not `state`
created: YYYY-MM-DD
go:                # at go: the dev_root commit (tag optional) of the authorization baseline
---
<!-- templates/design-lite.md — the design.md skeleton for a lite card (steps/lite.md「Card files」).
`new` copies it verbatim and fills id / title / project / created. Text after a heading is guidance; keep or delete. -->
# NNN <title>
## 当前摘要        problem · approach · key limits · unresolved risks (top; ≤200 字 when long)
## 目标与边界      deliver what · not what · the commitment blocks (index table optional, >5 blocks)
### Req-1 待验证 — <标题>        ← 状态词 ∈ 待验证 · 已验证 · 验证失败 · 阻塞 · 仅方案 · 放弃
- 陈述: free-form — paragraphs, nested lists, (a)(b) clauses, an `alt:` line; not a one-line cell
- 验证: <how> → <result + evidence pointer, product commit SHA(s) included>; the detail lives in 测试与验证
- why / 来源 · 变更 (mandatory when a commitment changes) · 确认 (go and every re-confirmation)
## 当前方案        candidates · chosen path · impact forecast · trade-offs · feasibility evidence
### 契约与不变量   | Inv-n | 不变量 | 归宿 | — M+ or any new contract; the close-out review walks each row
## 待解问题与证据  still to check · found so far (long material → facts.md / notes/)
## 任务            next steps · remaining work (→ plan.md when it crowds the doc)
## 测试与验证      已做 (layer · what · result) · 单次测不到的 · 计划表 (阶段 · 做什么 · 验证什么 · 判据 · 前置) · 结果与未验证项
## 授权记录        one line per go / re-confirmation: date · Req ids · scope & not-in-scope · quote · commit
