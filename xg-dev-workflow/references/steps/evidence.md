# Step: evidence discipline (M1)

Forked from **source-driven-development**. Adjusted: generalized from "framework docs"
to **any** load-bearing claim — code behavior, API signatures, config, runtime facts —
cited from an authoritative source. The rule applies across all phases.

## The rule
No guessing. No 望文生义 (don't infer behavior from a name). Every non-trivial claim is
either cited or flagged unverified.

**Fork ≠ upstream.** In a patched fork (e.g. Cloudberry/Greenplum on PostgreSQL), never
assume vanilla upstream behavior — lock modes, defaults, call paths may be changed. Verify
the actual in-repo code path before stating how it behaves.

## Negative results ("X doesn't exist / isn't implemented")
An absence claim is only as good as the search behind it. Before asserting "not found",
"not implemented", "no coordination", etc.:
- **Cover all relevant file types.** This codebase has C++ — search `.cc/.cpp/.cxx/.hpp/.hh`,
  not just `.c/.h`. Prefer **no `--include` filter** (or an explicit multi-ext set); a stub
  declaration in a `.h` does **not** mean the definition is absent — grep the symbol itself.
- **Search where wiring lives, not just code.** A feature may be present only in **build
  configs** (`Makefile`/`*.mk`/`configure.ac`/`CMakeLists.txt`/`meson.build` — guards, file
  lists, defines), **catalog definitions** (`pg_proc.dat`/`*.dat`/`*.bki`/catalog headers), or
  **registration sites** (function-pointer assignments, hook installs, `RegisterXact*`/AM-vtable
  setup). Grep these before concluding a feature is missing.
- **Search the symbol, not the file pattern.** A function declared in `*.h` is often defined
  in a sibling `.cc`. Grep `FuncName` across the whole tree before concluding it's a stub.
- **Distinguish same keyword across modules/layers.** The same name can exist in several
  modules (catalog-service vs QD; storage_am vs core). A hit in module A — or its absence
  there — says nothing about module B. Confirm **which module/layer owns** the behavior before
  any "missing"/"present" verdict; don't conflate look-alikes.
- Phrase a true negative as **"not found with query Q over scope S"**, not "absent."
- **Birth-certificate rule (a negative that justifies NEW code).** When an absence/existence
  claim is the *reason to build new plumbing* — a field / pipe / protocol layer to "carry X to
  Y", or a guard premised on "X is always N / X is dropped / X isn't reachable at Y" — it must
  reach **VERIFIED** by a hop-by-hop trace before it earns that code; a query-scoped negative
  isn't enough here. "The value isn't there" is the most expensive false claim: it births a whole
  layer where a few-line assert would do, and unlike an `(assumption)` it slips past review once
  "grounded". Can't verify → mark `(assumption)` and design as if X *might* already reach Y.

## Feasibility claims ("can't be done / infeasible") — design-time
Distinct from a fact about behavior: a feasibility verdict is a judgment about **mutable**
code, and during design the code is exactly what we'd change. Correctly-cited code is **not**
proof of infeasibility. Before writing "infeasible / 不可行 / can't":
- **Is the cited code even live in the target build?** Check `#ifdef` gating (`SERVERLESS`,
  `USE_INTERNAL_FTS`, …) and which branch this build compiles. An `Assert`/limit in a dead
  branch proves nothing.
- **Is it the relevant execution context?** A gate added via a hook runs where the *hook*
  runs (e.g. launcher main `AutoVacLauncherMain()`, with catalog/RPC), not in some unrelated
  dispatch-time helper. Cite the function that runs *at the seam you'll touch*.
- **Is it a swappable seam?** Function pointers (`cdbcomponent_getComponentInfo` is a
  `typedef`'d pointer), hook variables, registered callbacks, AM vtables — these are *meant*
  to vary; a current assignment is not a constraint. **Before any verdict resting on a seam,
  dispatch an agent to enumerate _every_ assignment/registration site** of that pointer/hook
  across `.c/.cc`, `.h`, build files, and catalog `.dat`/`.bki` — one current assignment is not
  the whole picture, and a seam re-pointed elsewhere flips the verdict.
- **Don't conflate look-alikes** — verify the entity is the one you think (e.g. catalog-service
  "coordinator" ≠ QD coordinator). Confirm identity before reasoning over it.
- **Verify the subagent's *inference*, not just its facts.** Re-checking that a cited line
  exists is not the same as re-checking the leap from it to "infeasible." Re-derive the
  conclusion yourself.
- **外部工具 / 运行时的行为断言 —— 跑一次,别推理。** 「这个 flag 去不掉」「这个参数加不上」
  「宿主没有 X」「这个语义在该文件系统上不可靠」这类断言的对象不是本仓代码,而是**可当场调用**的
  工具或运行时 ⟹ 唯一合格的依据是执行它并记下输出。从参数拼接位置、文档语义或工具惯例推出的结论
  标 `推断`,**不得标 VERIFIED** —— 这类断言恰恰是最便宜可测的一类,推断它没有任何时间收益。
- Phrase the honest result as **"no ready-made interface today (would need X)"**, reserve
  **"infeasible"** for a genuine fundamental barrier you can name.

## Where evidence comes from (by authority)
1. **The code itself** — `func()` in `file.c` (read it; no line numbers in prose).
2. **Project knowledge** — xg-knowledge-lite `[[wiki/<project>/<slug>]]`.
3. **Official docs / changelog** for a framework/library at the **detected version**
   (read the dependency file first); deep-link with anchors.
4. ❌ Not authoritative: Stack Overflow, blogs, AI summaries, your own training data.

## When you're unsure
Dispatch an **Explore** (or general-purpose) subagent to investigate and return the
evidence — then record the finding (in the relevant doc, and in the KB if reusable).
Surface conflicts (docs vs code, source vs source) to the human; don't silently pick.

**Model (cost):** follows SKILL.md「Subagent model assignment」(gather → cheaper `model: sonnet`;
inference/adjudication → session model, safe because the orchestrator re-derives). Evidence-specific
carve-out: keep the **session model** where recall itself is the deliverable with no cheap backstop —
the swappable-seam every-registration-site enumeration, and the hop-by-hop trace behind a
birth-certificate-grade negative.

When you dispatch, put the Negative-results rule **in the subagent's prompt**: tell it not
to restrict grep by file extension and to report negatives as query-scoped. A subagent's
narrow search (e.g. `.c/.h` only) is the single most common source of a false "not
implemented" conclusion — don't inherit it unverified. For any load-bearing negative the
subagent returns, re-check it yourself with a broader grep before stating it as fact.

## Confidence labeling — claims table before any conclusion
Before stating **any** feasibility or runtime/concurrency conclusion, lay out the load-bearing
claims as a table and label each:

| Claim | Evidence (`file:line`) | Confidence |
|---|---|---|
| … | `appserver.c:142` (or `—` if none) | VERIFIED / INFERRED / GUESS |

- **VERIFIED** — read the exact code/test that proves it. **INFERRED** — deduced from
  surrounding evidence but not directly read. **GUESS** — name/intuition, no evidence.
- **Never assert feasibility or runtime behavior on a claim marked INFERRED or GUESS** —
  investigate it up to VERIFIED first, or carry the conclusion as `UNVERIFIED:`.
- This audit table is the **one place** `file:line` is allowed (precision for the reader to
  re-check); prose elsewhere still cites `func()` in `file.c` without line numbers.

**Beyond investigation conclusions — provenance in every phase doc.** The same discipline applies
to **load-bearing claims** in any doc (requirement 需求条目, design Understanding/影响面, detail
rationale): mark each as evidence-cited / **推断 (inferred)** / **假设 (assumption)**. The full
claims table is reserved for feasibility/runtime verdicts; elsewhere the **inline marker** suffices
— a citation, or a trailing `(推断)` / `(assumption)`. Scope it to load-bearing claims; don't tax
every sentence. An unmarked non-trivial assertion reads as evidence-backed — if it isn't, it's a
`(assumption)` waiting to mislead.

**三种最容易漏标的载重断言** — 规则说「给载重断言标记」,难在**察觉自己正在下断言**。这三种形态
读起来像叙述,实为运行期行为断言,必须当场给依据或标 `推断`:

- **「这个机制能抓住 X」** — 你为一个机制编的使用场景,就是一条关于「X 发生时系统会怎样」的断言。
  写下它之前,把那个场景在代码里**推演一遍**;推不动就说明这个机制的理由还没成立。
- **「这个序列按 Y 顺序 / 已去重 / 是稳定的」** — 顺序、唯一性、幂等、稳定性**只能从产生它的代码
  读出来**,不能从它的用途推。断言指向用途(「它是用来 Z 的,所以应该有序」)即为无依据。
- **「这条 alt 做不到,所以否决」** — 否决一个候选方案的理由与选择它的理由**同等载重**:它把一整类
  方案从设计空间里移走。而它比被选中方案的前提**更危险** —— 被选中的会在实现里被检验,被否决的
  **没有任何下游动作会碰它**,错了可以一直错着,直到有人回头问「那条为什么不行来着」。写下否决理由
  前,按「要据以动手的前提」那个标准验它。

## Honesty
If something can't be verified, write `UNVERIFIED: …` explicitly rather than hedging.
A flagged gap is more useful than false confidence.

## Persistence

A verified load-bearing fact on a ledger card gets an `F<n>` block in the card's `facts.md`
(grill.md「载重事实入账」) so doc rewrites can't lose it; standalone docs keep a doc-local
事实清单 (`references/id-schemes.md` F-id scoping).

## Citation form in docs
- code: `` `TpFrozenShmemGetMin()` in `appserver.c` ``
- knowledge: `[[wiki/cbdb/appserver-epoch-shmem]]`
- external: full URL with anchor + a one-line quote for non-obvious decisions.
