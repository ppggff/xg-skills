---
id: NNN
title: <design title>
project: <project>
requirement: ./requirement.md
status: drafting | frozen | superseded
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# 设计 NNN: <design title>

> Phase gate: once **approved**, this file is **FROZEN**. It changes only via the
> change-management flow (a requirement change, or the design proven infeasible) —
> never to accommodate implementation convenience.
> **Reader: human-first** (decision zone — you approve & freeze it; this is the last binding gate
> before autonomous execution). Write it to be reviewed at module altitude. (SKILL.md「Two zones」.)
> The body is **current-state only** (grill.md「Fold-in」): superseded alternatives compress to a
> verdict + git/grill-log pointer.
> **Three-class marking:** decisions cite their ledger id (`decisions.md`), facts cite `[F<n>]`
> (`facts.md`); unmarked prose is synthesis — freely rewritable, must not contradict approved
> decisions.

## 思路 (Approach in one paragraph)

**Required.** The **single core strategy in plain words** — the one idea a colleague could
restate after one read. **≤ 2 sentences.** Name the **one** method/metaphor and its punchline;
**exclude** mechanism detail (locks / hooks / modules / RPC / file names), performance &
motivation, alternatives, and constraints — each of those has its own section below.

- ✅ 「用选举解决：多个 coordinator 选举，只有成为 active 的运行 autovacuum/autocluster，其余 standby；active 失联则 standby 接力。」
- ❌ a dense paragraph naming the thin module, the coordination substrate, the kernel hook,
  "no enumeration", overhead-vs-correctness, anti-wraparound … — that's the *rest of the doc*,
  not the 思路.

Test: a reviewer who reads **only** this paragraph can correctly restate the approach.

## 速览 (Quick reference — fixed first stop)

The anchors a reader needs before the body (keep to one screenful; **regenerated** as the design
evolves, never appended):

- **术语表** — the doc's load-bearing coined terms, each defined fully enough to stand alone
  (later table cells may then use them bare — `references/doc-conventions.md`「Reasoning shown」
  table rule);
- **staging vocabularies** — when more than one scheme coexists (build order `MS<n>`,
  enablement tiers, …), one line stating how they map (`references/id-schemes.md`「Symbol budget」);
- **待拍 gates** — the open `G<n>` decisions blocking freeze, one-line asks each.

## Understanding (concept → layer)

What existing code/concepts this builds on, in layers (concept → module → file/func).
Ground each in evidence: `func()` in `file.c`, or KB `[[wiki/<project>/<slug>]]`. Capture any
reusable module knowledge to xg-knowledge-lite rather than restating it here.

**Write it as reasoning, not a fact list**: each point states *why* the cited code leads to the
design's premise (evidence → mechanism → implication), so the approver can check the logic, not
just the citations (`references/doc-conventions.md` Reasoning-shown). 示例（示意）：
- ✅ 「`launcher_main()` 只在 postmaster 直属进程里跑（evidence）→ serverless 模式无该进程，
  既有调度覆盖不到（mechanism）→ 需要外置触发 seam（implication，引出模块 X）。」
- ❌ 「`launcher_main()` 在 `autovacuum.c`；serverless 无 postmaster 子进程；存在一个 hook。」
  （三条事实并列，推理链断——approver 无从核逻辑）

## Chosen approach

**At module altitude** (no concrete code — defer functions/locks/hooks/files to `detail.md`
「代码级接口」; XS/S cards that skip detail.md: the plan task's Files/Description):
modules + responsibilities, boundaries, contracts, key invariants. Build on existing modules;
contract-first. Cite load-bearing claims via KB `[[wiki/<project>/<slug>]]`.

**Each module carries a 归属 tag** — one of **复用已有** (an existing module used as-is) ·
**已有扩展** (a new responsibility grafted onto an existing module) · **全新** (a new module).
The tag feeds 影响面「改动/新增模块」and the 详设-necessity call (new/extended structural
modules are what makes a card M+/structural).
Refer to modules **by name**; number in-design decisions/子决策 `D<n>` when other sections or
ADRs need to reference them (`ADR-NNNN D<n>` for a decision inside an ADR — SKILL.md
「Fixed ID prefixes」).

State the **essential 思路** and the **abstraction layers** it realises (each layer's job + which
modules live in it) before listing flat modules — the right layering simplifies the problem.
Number layers `L1..Ln` (bottom-up) when other sections need to reference them; milestones/分期
use `MS<n>` (SKILL.md「Fixed ID prefixes」— bare `M<n>` means the skill mechanisms).

示例（示意，非唯一写法）：
- ✅ 「coordination 模块（全新）：负责跨 coordinator 互斥——谁是 active；对外只暴露
  acquire/release 语义，建于既有 lease 机制之上，不新增存储。」（模块 + 职责 + 边界 + 依托）
- ❌ 「在 `do_start_worker()` 里加 `LWLockAcquire(AutovacScheduleLock)`，超时 5s 后……」
  （函数/锁/参数——这是 `detail.md` 的 altitude，设计层写它就漂了）

### Diagrams (required)

- **Module interaction** — modules as boxes (labelled with responsibility), calls/seams as
  arrows (who depends on / invokes whom).
- **Data flow / relationships** — what data crosses each boundary and in which direction
  (separate diagram or annotations on the first).

**Prefer Mermaid** (a ```` ```mermaid ```` fenced block — `flowchart`/`graph` for module
interaction, `sequenceDiagram`/`flowchart` for data flow): it renders in GitHub/Obsidian/VS Code
and still diffs as text. Fall back to ASCII only for a trivial diagram or one Mermaid can't
express (then follow the CJK-width rules in `references/diagram-gotchas.md`).

### Interface / contract (required when the design introduces a module)

The new module's **external interface as a contract, not signatures** (concrete functions/types
→ `detail.md`「代码级接口」; XS/S without detail.md: the plan task fields): each operation's
inputs / outputs / semantics, plus the contract invariants
(uniqueness, idempotency, self-heal, degradation). Fixed columns:

| 操作 | 输入 | 输出 | 语义 | 不变量 |
|---|---|---|---|---|
| … | … | … | … | … |

e.g.（示意）`acquire | node-id | granted/denied | 请求成为 active；幂等重入 | 至多一个
granted；holder 崩溃后 lease 过期自愈`——语义列写**含义与顺序约束**，不变量列写**跨操作
恒成立的性质**，两列都不是签名。

Vocabulary follows the `codebase-design` skill: an **interface** = everything a caller must know
(the signature **plus** invariants, ordering, error modes, perf); aim for a **deep** module (small
interface, lots hidden) at a clean **seam** (Feathers — _Avoid_ "boundary" **for the joint
itself**; "boundary" stays the word for a module's own perimeter, as in "modules /
responsibilities / boundaries"). Depth = leverage per unit of interface a caller must learn.

### 存储足迹 (Storage footprint — 按模块; required when the design touches any storage)

Every store the design adds or touches, **organized by module** (one module's 责任/操作/存储 all
hang off its name): what exists, who owns it, how durable. Design altitude only — concrete
schema / keys / indexes stay in `detail.md`「数据结构」. This table feeds 影响面's 兼容/ABI 面
(on-disk / catalog changes surface here first). Omit the section when the design touches no
storage (same convention as Parts).

| 模块 | 存储 (file / shmem / catalog / DB / 内存态 / GUC) | 持久性 (persistent / ephemeral) | 归属 / 生命周期 |
|------|--------------------------------------------------|--------------------------------|----------------|
| … | … | … | … |

### Decomposition / Parts (optional — only when this design is split into independently-built parts)

When the design splits into **parts** (each part = ≥1 module built & tested as one independent
unit — see SKILL.md「拆分与隔离」A), list the parts + the **seam** between adjacent ones. The
seam's contract IS the relevant 「Interface / contract」entry above; it **freezes with this
design**, and that freeze is what lets each part be built & unit-tested against it (mocking the
neighbor) before the neighbor exists.

| Part | 含哪些 module | 对外 seam (邻居 part) | seam 契约 (指向上面 Interface/contract 条目) |
|------|--------------|----------------------|---------------------------------------------|
| … | … | … | … |

**Omit this section entirely for an un-split design — nothing else changes** (M3 does not require
it). If 联调 later disproves a frozen seam contract, that's an architecture change → route through
M2 (`change.md` `seam-contract-disproved`), never a silent `plan.md` edit.

### Design qualities (state how each holds)

简单可靠 (首要) · 可测试性 (能 mock 周边、独立测) · 可观测性 (坏了能定位到本模块) · 异常完整性
(每个异常有归属或兜底,兜底可人工;罕见不另立结构) · 性能 + 规模放大后的性能. One line each;
"N/A — <why>" is a valid answer.

## How it meets the requirement

Trace by **R-id** (link each id — `[R1](./requirement.md)`; `references/doc-conventions.md` Links)
so every requirement has a design home:

- **需求条目** — each `R-id` → which module/contract satisfies it (a small table works well).
- **Scope** — stays within / why each out-of-scope item is excluded.
- **Constraints** — how each constraint is honored.
- **Effect** — how each success criterion will be satisfied.
- **Future** — what this leaves open for the deferred work.

## 验证策略 (Verification strategy — 主体 E2E; required for M+, XS/S may omit)

How we will know it works, fixed **at design time** — testability is a design property: the
design must provide the observation points, and discovering "R3 can't be verified end-to-end"
during 测试 is too late. **Strategy/mapping altitude only** — scenarios + observation points;
concrete test cases, commands, and fixtures stay in `test.md` (`detail.md` carries only
mechanism-level boundary behavior — its 边界与错误矩阵, not test cases).

| R-id / Effect 项 | E2E 场景 (最短的端到端证明路径) | 观测点 (设计提供的) | 备注 / gap 决策 |
|---|---|---|---|
| [R1](./requirement.md) | … | … | … |

e.g.（示意）一行填法：`[R1] | 起双 coordinator，kill active，观察接管 | pg_stat_activity 中
launcher 计数 ≤1 | 5s 内接管；复用既有视图，无新观测点`——场景是**动作序列**，观测点是**设计
已提供的可读位置**；写成「跑测试套件」就退化成 test.md 的事了。

An item with **no cheap E2E path is an explicit design decision** — either accept a unit-level
proxy (state why it suffices) or change the design for observability; never leave the row blank.
`test.md` consumes this table as its coverage skeleton, and the close-out review checks the
promised scenarios ran.

## 影响面 (Impact surface — blast radius)

What this change reaches beyond the new code — the surface a reviewer/operator must watch.
Ground each entry in evidence (`func()` in `file.c` / `[[wiki/…]]`); mark 推断/假设 where unverified.

- **改动/新增模块** — modules & files this design adds or edits.
- **调用方 / 下游消费者** — existing callers, consumers, or jobs that depend on the touched
  behavior (who breaks if the contract shifts).
  e.g.（示意）「`vacuum_worker()` in `autovacuum.c` 轮询本模块状态（evidence）；运维脚本
  `nightly-vacuum.sh` 解析其日志行格式（推断——未验 crontab，验证归 test 回归行）。」
  ❌ 「nightly-vacuum.sh 也依赖本模块」——没标注查过还是猜的，reviewer 无从核。
- **兼容 / ABI 面** — on-disk format, catalog, SQL/extension interface, ABI — and whether each
  stays compatible.
- **跨 card / 跨项目波及** — other requirements (same-project `NNN`, see `index.md` Deps) or
  projects affected.
- **需回归的行为** — existing behaviors to re-verify (feeds `test.md` + the close-out `review`).

## Alternatives considered

**方案优先** — alternatives + their trade-offs are a primary grill target, not an afterthought;
the chosen approach wins on trade-off. Say whether the design is driven by the **normal flow or
by a dominant anomaly flow**.

**Span the solution-class spectrum + name each cost.** Don't compare only same-class variants —
weigh the three classes explicitly and choose deliberately:
- **hack** (quick workaround) — fastest now; cost = tech debt, fragility, often-hidden 影响面.
- **补丁 / patch** (localized fix, doesn't touch the root) — moderate; cost = root cause persists,
  may re-surface, partial coverage.
- **推翻重来 / proper redo** (fix the root correctly) — often the *right* shape; cost = time + a
  bigger 影响面/risk now, and it must still pass 简单可靠 / 反过度设计 (a full rewrite isn't
  automatically right — over-engineering is its own debt).

State the cost of **each**, then pick the point on the spectrum the trade-off actually justifies. A
hack/patch is a **conscious debt decision** — record it + the intended follow-up (a `Future` item or
a new card), never a silent default.

### Alternative A — <name>
- Class (hack / 补丁 / 重做) · Pros / Cons / **Cost** / Why rejected.
  e.g.（示意）「Alternative B — 指定单 coordinator 硬编码 · Class: hack · Pros: 零协调开销 ·
  Cons: 指定节点故障即全停 · **Cost**: 单点 + 运维手工切换 · Why rejected: 与 R2（高可用）
  直接冲突，且迁移到选举方案时该硬编码要整体拆除。」
- Comparative claims about existing code carry provenance **from the first draft** (VERIFIED /
  INFERRED / 推断 per claim) — an unread-code claim doesn't go in the comparison (M1;
  design-grill 方案优先).

(Decisions that are hard-to-reverse + surprising + a real trade-off → record an ADR in `adr/`.)

## ADRs

- [ADR-0001 <slug>](./adr/0001-<slug>.md) — <one line>

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| … | H/M/L | … |

## Open questions

- …
