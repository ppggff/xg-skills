# ID schemes (the full registry)

The workflow's fixed ID prefixes — **one letter, one meaning**. legacy/SKILL.md「Conventions」(存量; a lite card uses `Req-n` · `Fact-n` · `Inv-n` · `ADR-NNNN` · `Task-n`, lite.md「Open a card」) keeps the
core five resident (`NNN` / `ADR-NNNN` / `R<n>` / `T<n>` / `M1`–`M6`); this file holds the full
scheme, consulted when naming. A new scheme picks an **unused** letter and lands here.

## Prefixes

**Doc-native three-letter set (026 HLD-1 — the current form on doc-native cards; the single-
letter forms below stay the 存量 notation, dual-recognized by the tools):**
`Req-<n>` 需求条目 · `HLD-<n>` design decisions · `LLD-<n>` 详设 items · `Task-<n>` plan tasks
(tools still parse `T<n>` heads) · `Ask-<n>` grill rows (`G<n>` = transitional 存量 form in
approved-note ask-id slots) · `Fact-<n>` fact entries (`[F<n>]` stays legal as the transitional
alias on transported text) · `Eff-<n>` Effect criteria · `Crit-<n>` verification-criteria
definitions (V 存量) · `Layer-<n>` abstraction layers (L 存量) · `Inv-<n>` 契约与不变量 rows (lite
`design.md`「当前方案」, walked by the close-out review; `I<n>` = 存量 form). Case-sensitive strict, no
zero-padding. **Unchanged set**: `MS` · `ADR-NNNN` · `#<n>` (report-local) · `NNN` · `M1`–`M6` ·
P-rules · lens 1–4 · Tier 0–2. Two-form rule (Req-30): definition site bare (the structural
position is the anchor), prose citations bracketed `[Req-1]`; **clause exception (W-10)**: a
clause's definition site is the in-block local marker `- (x) `, cited as `[Req-12-a]`
(hyphen-to-the-end single token); **clause-marker disambiguation**: only the line-leading
`- (x) ` form is a clause address — `(a)`/`(b)` inside clause prose (batching grounds, source
§ numbers) is content, not an address. **Range notation** `Req-1..Req-23` is a legal id-set
form; consuming parsers expand it (block_parse.expand_ranges / the trace layer). Check-id
families ((a)–(ae) / ABC 族 / (c1)–(c8)) stay their own scheme — the `- (a)` clause marker is
the same glyph in a different scheme, context disambiguates (declared ambiguity, W-10).

- `NNN` — card dir · `ADR-NNNN` — decision records · `T<n>` — plan tasks.
- `R<n>` — requirement 条目; **R is reserved** for requirements.
- `G<n>` — grill-log questions, **continuous across rounds**; round-scoped form `G<round>.<n>`,
  never a new letter per round.
- `L<n>` — abstraction layers (design) · `D<n>` — design decisions/子决策 (ADR-scoped:
  `ADR-NNNN D<n>`).
- `MS<n>` — milestones/分期 — bare `M<n>` stays this skill's mechanisms `M1`–`M6`.
- `S<n>` — 详设 (detail/structure) 级决策条目 (numbered in `detail.md`, ledger level `detail`;
  approved carries baseline force — see `templates/decisions.md`). Number only items that enter
  the ledger, not every spec line.
- `P<n>` — implement's principles (`implement.md` Principles).
- `V<n>` — **verification-criteria definitions** shared by several Effect items (`SNAP`-class: what
  a judgement compares, over which scope, with which cardinality assertions). Requirement-level
  ledger rows, so changing one definition supersedes **one** row instead of cascading through every
  `R<n>` whose Effect cites it. Effect items cite them as `[V<n>]`.
- `F<n>` — fact entries, **per-container scoped** (`references/doc-conventions.md`「Provenance containers」): card →
  the card's `facts.md` (phase docs cite `[F<n>]`, no doc-local list); standalone doc → its
  doc-local「事实清单」section. Never both containers for one doc.
- Review findings: `#<n>` within a report's 修复决策表, severity spelled out
  (High/Med/Low — no H/M/L shorthand).
- Discussion-first stages are **word-named** (understanding statement / candidate spread /
  agenda negotiation …, `references/design-agenda.md`) — stages are not ledger rows, no letter
  prefix exists or should be minted for them.
- `governance:` — not an id scheme but a **registered frontmatter field** (requirement.md only,
  017 D1): literals `ledger`/`doc-gate`/`doc-native-pilot`/`doc-native` (pilot = card 026's
  self-hosted trial; `doc-native` = the post-collapse single track for new cards, 026 Req-32 —
  ledger/doc-gate stay as 存量 values; upgrade direction `*→doc-native` is a one-time explicit
  M2, HLD-13(7)), key word-only (the flat frontmatter parser drops hyphenated keys), no inline comments
  (values are taken verbatim); omitted = legacy cascade.

## Rules

- **Symbol budget** — a prime evolution (`X'`→`X''`) survives **one** generation; the next
  supersession renames/consolidates instead of adding another prime. Introducing a second
  staging/tier scheme alongside an existing one requires a one-line statement of their relation
  at first use, and its letter must not collide with the list above.
- **New ledger-entering prefix wiring checklist** — a prefix whose ids enter `decisions.md`
  must land ALL of these in one batch (each is a closed enumeration that fails silently when
  skipped): (1) this registry; (2) `workflow-status.py` `LEDGER_HEAD` + `LEDGER_ID` regexes;
  (3) `_id_level()` (an unmapped prefix falls through to design — reference checks then skip
  it on requirement-stage cards); (4) `templates/decisions.md` header id enum; (5) a
  regression-test group shaped like the existing per-prefix ones; (6) the `check` verb (legacy M3)
  deterministic-subset sentence when the prefix adds a check.
- **Modules and parts are named** (the name carries the meaning); `Mod<n>` / `Part <n> (<名>)`
  only when a table/diagram needs a compact id — never bare `M<n>`/`D<n>`/`P<n>` for them.
  Mermaid node ids are diagram-local — exempt.
- **Cross-scheme mappings are recorded downstream→upstream only**, each in its doc's designated
  field (design「How it meets」· design「Decomposition/Parts」`R` column (R→part 归属; doubles
  as the new-format marker — tools treat a Parts table without it as un-split) ·
  detail 可追溯 · plan `Implements:` · test Coverage rows ·
  `ADR-NNNN D<n>`); the reverse map is derived (grep / M3), never hand-maintained — an upstream
  doc doesn't list who cites it (same one-way principle as workflow→KB links; M2 propagates
  along exactly these fields).
