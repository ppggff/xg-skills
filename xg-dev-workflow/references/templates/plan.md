---
id: NNN
title: plan for NNN <slug>
project: <project>
status: executing   # follows design.md `status`; the status-field check reads it
---
<!-- templates/plan.md — a lite card's task file, created when tasks crowd design.md (steps/lite.md「Card files」).
Task-n ↔ Req-n where it fits (constraints.md Id-1); one block per task with a binary 判据; the index table at the top holds
one sentence per cell and nothing the blocks do not say. A task deleted / merged / deferred leaves a one-line note here
(Doc-7). Product commit SHAs land in a block's 验证 line — the Req 验证 line in design.md cites this file, never repeats it. -->
# plan — NNN <slug>

<execution order · per-slice notes (test mode, recon entry) — a few lines, present tense>

## 状态索引

| Task | Req | 状态 | 一句话 |
|---|---|---|---|
| Task-0 | — | 已验证 | <the recon baseline in one sentence> |
| Task-1 | Req-1 | 待做 | <what it delivers, one sentence> |

### Task-0 已验证 — recon 基线        ← 状态词 ∈ 待做 · 进行中 · 已验证 · 阻塞 · 放弃
- 做什么: <the build / test baseline, run unchanged in the target environment>
- 判据: <binary>
- 状态: 已验证（YYYY-MM-DD）
- 验证: <command · output · version>

### Task-1 待做 — <标题>
- 做什么: <the change, free-form; sub-steps as `- ` lines>
- 判据: <the binary pass condition>
- 状态: 待做
- 验证: <commit SHA(s) · check output · test count — filled when done>
