<!--
<card>/decisions.md — the card's decision ledger: the single source of approval status for
every human-judgment decision (requirement 条目 · design D/ADR decisions · 详设 S items ·
execution-zone escalations). Implementation-level decisions stay in log.md.

Reader = human at gates (via the gate digest, generated FROM pending blocks) + tools
(workflow-status --check / card_status / --trace parse the headers and designated fields).

Contract (design 010, ADR-0001):
- One decision = one block. Header: `### <id> [<level>] <state>` — id reuses the existing
  scheme (R<n> / D<n> / S<n> / ADR-NNNN [D<n>]; the ledger never mints ids); level ∈
  requirement | design | detail; state ∈ proposed | approved | superseded | retired (the ONLY
  state words — freeze/baseline force derives from level, never written as a state).
- Single active block per id: at most one block per id is not superseded/retired.
- New blocks append at the file end. Claude may write proposed/superseded (via a confirmed
  M2 change list); approved is produced only by a human gate go (Claude transcribes).
- In-place edits are whitelisted to: the header state word · the `approved:`/`superseded:`
  annotation lines · a `- 澄清:` wording-clarification note (semantics unchanged; git keeps
  the old text). Everything else: supersede into a new block.
- `approved:` must carry the gate receipts-commit short hash (the ledger state the human saw);
  the approve transcription commits immediately after — adjacent in git, auditable.
- `depends-on:` is the ONLY dependency source tools parse (comma-separated ids); prose
  mentions of ids inside 陈述/why are not references.
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
