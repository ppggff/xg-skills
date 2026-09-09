# Step: lite (trial governance mode — one draft, one go, continuous execution)

Trial path. A card whose `design.md` frontmatter says `governance: lite` follows this file
**exclusively** — SKILL.md's Stop-at-gate rule, Two zones, Ledger, five phases, M2/M3 and phase
verbs do not apply. SKILL.md「Lite route」lists the shared files, the sections cited by name and
the files never loaded for a lite card.

## Model

One continuously updated working draft; explicitly confirmed goals and boundaries
(**commitments**); one execution authorization (**go**); verification evidence matching the
current change. Requirement / design / detail are angles of thought, not gated phases; the
loop understand ⇄ investigate ⇄ compare ⇄ negotiate runs before go and continues after it
inside the authorization — only three kinds of change come back to the human (「Executing」).

- **Commitment** = a goal, constraint or acceptance condition the human explicitly asked for or
  confirmed and still in force, plus the project's standing constraints. Who said it first is
  irrelevant; a confirmed Claude proposal is one and Claude cannot withdraw it alone. Not copied
  into the doc ≠ authorization to drop it — backfill and say so, distinct from raising a new ask.
- **Impact forecast ≠ authorization boundary.** Expected modules/files/tests are a forecast that
  moves with investigation — no pause when it grows; hard boundaries exist only when the human
  set them, and are marked as the human's.

## Card files

Start from `design.md`; create the others when their content appears, never as empty containers:
`progress.md` (park / handoff) · `facts.md` (many load-bearing facts) · `adr/` (a trade-off worth
its reason; `templates/adr.md`) · `plan.md` (tasks crowd the doc) · `log.md` (history outgrows the
doc) · `notes/` (long output, spikes, reviews). Full content has one home; a summary is
self-contained; prose states the present — history is git plus the 变更 lines.

## Open a card (manual — do not run `new`; it scaffolds a doc-native requirement.md)

1. Next `NNN`: scan `<dev_root>/<project>/`, increment.
2. `mkdir <dev_root>/<project>/NNN-slug/`; write `design.md` from the skeleton below.
3. Board row in `index.md`: `| NNN | lite | todo | — | [NNN-slug](./NNN-slug/) |` — 整体状态 takes
   only the canonical words (`todo` drafting · `active` go → close-out · `done` / `dropped`).
Ids: `Req-n` · `Fact-n` · `ADR-NNNN` · `Task-n` (with plan.md); two-form citation per `id-schemes.md`.

## design.md skeleton

```markdown
---
id: NNN            title: <slug>        project: <project>      governance: lite
status: draft      # draft | executing | closing | done — checks read `status`, not `state`
created: YYYY-MM-DD
go:                # at go: the dev_root commit (tag optional) of the authorization baseline
---
# NNN <title>
## 当前摘要        problem · approach · key limits · unresolved risks (top; ≤200 字 when long)
## 目标与边界      deliver what · not what · the commitment blocks (index table optional, >5 blocks)
### Req-1 待验证 — <标题>        ← 状态词 ∈ 待验证 · 已验证 · 验证失败 · 阻塞 · 仅方案 · 放弃
- 陈述: free-form — paragraphs, nested lists, (a)(b) clauses, an `alt:` line; not a one-line cell
- 验证: <how> → <result + evidence pointer>; the detail lives in 测试与验证
- why / 来源 · 变更 (mandatory when a commitment changes) · 确认 (go and every re-confirmation)
## 当前方案        candidates · chosen path · impact forecast · contracts · trade-offs · feasibility evidence
## 待解问题与证据  still to check · found so far (long material → facts.md / notes/)
## 任务            next steps · remaining work (→ plan.md when it crowds the doc)
## 测试与验证      已做 (layer · what · result) · 单次测不到的 · 计划表 (阶段 · 做什么 · 验证什么 · 判据 · 前置) · 结果与未验证项
## 授权记录        one line per go / re-confirmation: date · Req ids · scope & not-in-scope · quote · commit
```

`[x]` anywhere means 已验证 and nothing else. **Diagrams**: two or more interacting components,
or a decision branch → at least one Mermaid diagram; M+ → two (module interaction + data flow).

## Drafting (before go)

Explore, investigate (`investigate.md`, M1), compare, negotiate — freely; the doc is a draft.
Spikes stay within standing permissions, local and reversible. **Candidates first (方案优先)**:
before drafting the approach, put ≥2 candidates side by side — one-line 思路 · position on the
hack ↔ 补丁 ↔ 推翻重来 spectrum · cost (工期 / 技术债 / 影响面 / 可维护性) · provenance; a hack or
patch is a recorded debt decision, never a default. S: 1+1 (pick + one-line rejected alt); XS
with an obvious single solution: one sentence. "Enough basis" for go: key feasibility rests on
code, a derivation or a spike; thin evidence is stated; a question that could sink the approach
gets a bounded investigation or narrows the ask. Claude compiles the commitment blocks.

## The go ask (one message, receipts first)

Commit the card (`commit-data-repos.py --card <project>/<NNN>`), then ask with: 摘要 · the
commitment list (Req ids, one line each) · scope and not-in-scope · impact forecast (labelled) ·
risks and thin evidence · what the authorization includes and excludes · the **收敛行**
`已定 n 项 · 待定 <…> · 未探索 <…> · grill: k 轮 / 未做（原因）` · the judgment split: **已验证**
(Claude checked — say how) vs **待你判** (only the human can decide — each as 问题 · 选项与代价 ·
推荐 · 不决的后果, plain language, ids only in brackets). A partial go names the Req ids covered;
the rest stay as「讨论中」. On `go` (or an equally explicit equivalent): the 授权记录 line and each
covered block's `确认:` line, `status: executing`, `go:`, commit again (a tag is a pointer, not the approval).

## Executing (after go)

Stay in this session by default; switch when context is long, work is interrupted, or a handoff
is being tested. Usually just continue — change approach, add tests, reorder, trace call chains,
fix review findings, update prose and evidence — while the commitments hold and operations stay
inside the authorization; a material approach change gets one reason line. **A→B walk**: A's
problem → does B still meet the commitments? → rewrite 当前方案 → one reason line → re-verify
what B touches → sync facts / ADR / diagrams if present; B cannot meet a commitment → propose and
pause the dependent work. Product commits: `<scope>: <what> (NNN Req-n[,m])`, one concern each.

**Come back to the human only for** (1) changing a goal, weakening acceptance, dropping a
deliverable, or changing an explicit constraint or boundary; (2) work or a major trade-off beyond
the authorization — "not forbidden" is not authorization; (3) an operation needing its own
authorization. Ask form: what was found · which commitment · proposed change; the doc carries a
待确认 proposal, the old commitment stands, only dependent work pauses. Clarifications and
blockers are not approvals: investigate what code can answer, ask promptly for what only the human knows.

**Operation carve-outs**: destructive operations on shared/live environments, publish, push,
range deletes / truncate / schema / cluster-level writes — verify scope, target-version behavior
and restore conditions first; without authorization present reviewable information and wait. A
go on tasks never covers these. File-scope checks are not operation permission.

**Park / resume**: park = `progress.md` to the resume floor (now · next · blockers · build/verify
entry) + commit; resume = progress (if any) → design.md 摘要 → 承诺 → 当前方案 → evidence and code
as needed; reading scope is unrestricted — the summary is the entry, not the contract.

## Verification and close-out

A result names object, method, actual outcome and code version / environment. A test name is not
a run; a link is not support. When code, approach or environment changes, re-judge old evidence;
stale → 待重验 with reason. Refuted (counter-example) and unverified (thin evidence) stay distinct
— the latter is never a negative conclusion (M1). Review depth follows impact, reversibility,
invariants and verifiability, not task size.

Close-out, in order: (1) **simplify** once when the change exceeds ~150 lines or adds files
(`simplify-checks.md`, behavior-preserving), result noted; (2) **review by size** — S: light
self-review (diff walk · each commitment against the code · each test against its claim) written
into the doc; M: `review` verb standard tier (test-adequacy lens over the Req 验证 lines); L: deep
— **skipping any step is written down with its reason**; (3) per commitment: met / scope of the
result / unverified / residual risk — a task that promised only a plan closes on that, never
claiming a run; a promised run that cannot happen is a blocker or a negotiated cut; (4) `status:
done`, board `done`, KB triage, usage log `--action lite`, and the **observation note** (five
lines): places synced per ordinary change · needless interruptions · doc time and lines read at
go · missed commitments / unauthorized changes / verification gaps · handoff gaps. Asking about a
real doc gap is not a failure.

## By size

| | XS | S | M | L |
|---|---|---|---|---|
| grill | one round, may share the go ask | as needed — say so in the 收敛行 | **required**: understanding statement · candidates · one question at a time to convergence (grill.md「Protocol」「Convergence」, design-grill.md「方案优先」) | as M, per card |
| candidates / diagrams | one sentence / when triggered | 1+1 / when triggered | full spectrum + rejection reasons, ADRs 0–3 / two diagrams | as M |
| lenses | — | by risk | once the approach forms: falsifier (attack load-bearing facts) + commitment coverage (code ↔ commitments) — fresh-context, one agent each, adjudicate before reporting | as M + deep review |
| files / execution | design only | + progress at park; light self-review | + plan.md (Req-tagged, binary tasks) · facts.md · adr/; one commit per slice; standard review; **one documents-only handoff check** | split first: split-isolate.md A↔B + five steps; seam contract in 当前方案, 联调 rows in 测试与验证 |

## Replay probes (once per trial card; a replay is labelled as one)

P1 ordinary approach change → A→B walk, one reason line, no ask, affected 已验证 → 待重验. P2 B cannot
meet Req-n → 待确认 proposal, three-part ask, dependent work paused. P3 only the human knows X → a
prompt question, no silent narrowing of the acceptance, the gap recorded.

Caps (anti-ratchet): this file ≤150 lines, SKILL.md「Lite route」≤40 lines; retro records both.
