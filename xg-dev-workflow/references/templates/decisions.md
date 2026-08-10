<!--
<card>/decisions.md — the card's decision ledger: the single source of approval status for
every human-judgment decision (requirement 条目 · design D/ADR decisions · 详设 S items ·
execution-zone escalations). Implementation-level decisions stay in log.md.
LEDGER CARDS ONLY (017 D1): a `governance: doc-gate` card has no decisions.md — its decisions
live in the phase docs (grill.md doc-gate branches); creating one there is an i4 finding.

Reader = human at gates (via the gate digest, generated FROM pending blocks) + tools
(workflow-status --check / card_status / --trace parse the headers and designated fields).

Contract (design 010, ADR-0001):
- One decision = one block. Header: `### <id> [<level>] <state>` — id reuses the existing
  scheme (R<n> / V<n> / D<n> / S<n> / ADR-NNNN [D<n>]; the ledger never mints ids); level ∈
  requirement | design | detail; state ∈ proposed | approved | superseded | retired (the ONLY
  state words — freeze/baseline force derives from level, never written as a state).
- Single active block per id: at most one block per id is not superseded/retired.
- New blocks append at the file end. Claude may write proposed freely (grill 逐条入账 and
  M2 proposal substance — before the confirm); superseded only after a confirmed M2 修改列表;
  approved is produced only by a human gate go (Claude transcribes).
- A **proposed** block may be rewritten in place while under discussion (git keeps history).
  Once **approved**, in-place edits are whitelisted to: the header state word · the
  `approved:`/`superseded:` annotation lines · a `- 澄清:` wording-clarification note
  (semantics unchanged; git keeps the old text). Everything else: supersede into a new block.
- why stays ≤1 paragraph; argumentation beyond that lives in the doc §/ADR the block cites
  (判断必需 → digest card · 论证 → doc §/ADR · 记录 → this ledger).
- `approved:` must carry the gate receipts-commit short hash (the ledger state the human saw);
  the approve transcription commits immediately after — adjacent in git, auditable.
- Docs are rewritable views over this ledger: synthesis prose cites the ledger id / `[F<n>]`
  fact and never contradicts an approved decision — `workflow-status.py --check` runs the
  deterministic subset, M3 judges semantics. The ADR `Status:` line is a display snapshot of
  the derived status (SKILL.md「Ledger」derived-status rule).
- `depends-on:` is the ONLY dependency source tools parse (comma-separated ids, **one
  line** — a wrapped continuation is silently ignored); prose mentions of ids inside
  陈述/why are not references. No dependencies → omit the line (a `—` placeholder is
  tolerated but pointless).

Decision-shaped 陈述, e.g.（示意）:
  ✅ 陈述: 心跳超时取 3×interval（9s）—— 一句话内有对象、有取值、可直接判对错;
     why: 2×在 GC 停顿下误判接管；alt: 固定 30s — 接管迟钝，违背 R3 的 5s 目标。
  ❌ 陈述: 「优化超时逻辑」——无对象无方向，gate 无从判，digest 卡片也无法复述。
-->

### R1 [requirement] proposed
- 陈述: <one-sentence decision>
- why: <one paragraph>
  - alt: <rejected option> — <one-line rejection reason>
- provenance: evidence <source> | 推断 | 假设
- depends-on: <comma-separated ids, or omit the line>

### ADR-0001 D1 [design] approved
- 陈述: <…>
- why: <…>
  - alt: <…> — <…>
- provenance: evidence <source>
- depends-on: R1
- approved: YYYY-MM-DD gate <receipts-commit short hash>
