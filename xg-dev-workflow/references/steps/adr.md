# Step: ADR

Forked from **documentation-and-adrs** + **grill-with-docs/ADR-FORMAT**. Adjusted: ADRs
live in this requirement's `adr/` (not a global `docs/decisions/`); numbering is per
requirement; a superseding ADR that reopens a frozen design must link the requirement
change that justified it (M2).

Output: `adr/NNNN-slug.md` (template: `references/templates/adr.md`).

## When to write one (all three required)
1. **Hard to reverse** — meaningful cost to change later.
2. **Surprising without context** — a future reader will ask "why this way?".
3. **A real trade-off** — genuine alternatives existed and one was chosen for reasons.

If any is missing, skip it. Keep it minimal — one paragraph is a valid ADR.

### Worthiness discipline (score it, don't hand-wave)
**Score the three gates explicitly** before deciding — no silent "2/3 is close". State each
✓/✗ + a one-line reason; on a fail, decline with what would have to be true to pass.

**Five categories presume gate 1 (hard-to-reverse) = true** — for these, default to writing the
ADR even if "surprising" feels weak in the moment; they are the expensive-to-reverse calls:
- 持久化 schema / 落盘或线格式 (persisted / wire format)
- 外部标识符格式 (对外可见的 ID / key / 命名)
- 用户可见面 (CLI / SQL / API 行为契约)
- 跨语言 / 跨进程 ABI
- 全新基础设施 (新依赖 / 新协调机制)

To **dismiss** a category-match, write down **≥2 named alternatives + why each is rejected** —
a one-line hand-wave doesn't clear it.

### What qualifies (recognisers, from grill-with-docs/ADR-FORMAT)
- **Architectural shape** — "系统表走 fdbobj AM 而非 heap";"frozenxid 走 per-appserver shmem 而非 FDB key".
- **Integration patterns between components** — "catalog_extension 经 proxy RPC 连 catalog_4x,不直连节点".
- **Technology / lock-in choices** — 存储后端、锁服务、重依赖,换掉要花一个季度的那种(不是每个库).
- **Boundary & scope decisions** — "X 由 A 组件拥有,其它只按 ID 引用";刻意的"不做"和"做"一样值钱.
- **Deliberate deviations from the obvious path** — "kernel 只加 hook、逻辑放 storage_am"这类反直觉选择,挡住下一个人"顺手改回去".
- **Constraints not visible in code** — 合规、SLA、外部契约、环境限制.
- **Non-obvious rejected alternatives** — 否掉某方案的理由很微妙时记下,否则半年后又有人提.

## Procedure
1. **Create `adr/` lazily** — only when this first ADR is needed (don't pre-scaffold an empty dir).
   Number: scan `adr/` for the highest `NNNN`, increment (zero-padded to 4).
2. Write Context / Decision / (optional Alternatives / Consequences). Status starts
   `accepted` (or `proposed` if still under discussion). A **superseding or
   semantics-changing** ADR also lists **被取代表述** — the phrases, module names, and terms
   this decision retires (one line each) — feeding `change.md`'s supersede sweep; without it
   the sweep has no word list and old restatements survive outside the traced items.
3. Link it from `design.md`'s ADRs list.
4. **Never delete** an ADR, and **never append a `## Amendment` block** — an ADR is the
   *current active decision*, not a changelog (amendment blocks let it grow into a 500-line
   compound doc). To change a recorded decision, pick one of three paths:
   - **small fix** (typo / clarification, no decision change) → edit in place;
   - **decision change** a single ADR can express → write a **new** ADR with
     `## Supersedes ADR-NNNN`; the old ADR's Status line gets only a **≤2-line** forward
     cross-ref (rationale lives in the new one);
   - **architecture-implicating** change (touches the frozen `design.md` / other ADRs) →
     route through change-management (M2).
5. **Keep the body lean** — one decision + why + consequences, aim for ≤ ~200 lines. Ballooning
   means either several decisions (split) or accreting history (supersede, don't amend).

## Done when
- ADR file exists, linked from `design.md`, status correct. Then run the omission check (M3).
