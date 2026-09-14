# Doc conventions (xg-dev-workflow supplement)

The workflow-specific writing rules, layered on the shared core (`conventions-core.md`:
style/structure, first-use gloss, provenance marking, tables-vs-prose, diagrams, wikilink
form — **read the core first**). SKILL.md keeps the resident essentials and points here;
core + this supplement together are the single owner of the full rules. Read before writing
any workflow doc (phase docs, investigation/review notes, KB 注记).

## Links (clickable where cheap)

- Intra-requirement/project references: standard markdown links (`[design](./design.md)`).
- KB cross-references: wikilink form per core「KB cross-references」— load-bearing, don't
  swap for a markdown link.
- **An ID cited from another file is a markdown link to its home** — `[R1](./requirement.md)`,
  `[ADR-0006 D5](./adr/0006-<slug>.md)`, `[T3](./plan.md)`. Designated mapping fields and a
  doc's first mention always link; repeat prose mentions and same-file citations stay bare.
- **Enumeration counts cite their owner, never restate the number** (single-source counts):
  「R10 的闭列（见其陈述）」not 「R10 的十二项」— a restated count silently rots on the next
  M2 and needs a supersede sweep to catch.

## Provenance containers (F<n>)

Provenance markers (core「Provenance」) may **centralize** into `F<n>` fact blocks cited
inline as `[F<n>]`; `F<n>` is a **per-container scoped id** (like `R<n>`/`S<n>`): on a card,
the container is the card's `facts.md` — phase docs cite it and never keep a doc-local fact
list of their own; a **standalone** doc (investigation/review note, no card) uses a doc-local
「事实清单」section instead. One container per doc, never both; the inline marker form stays
for isolated load-bearing sentences.

## Reasoning shown (human-first docs)

requirement/design/detail/ADR/review and investigation-notes prose carries the logical
analysis, **evidence → mechanism → conclusion**, so the approver can check the inference, not
just trust the citations — a fact table with a conclusion bolted on is a grep-hit list at doc
level. Execution-zone docs stay terse: link the reasoning, don't restate it. (Tables-vs-prose
division: core「Tables carry facts, prose carries reasoning」.)

## Load-bearing prose and its home (载重散文的归宿 — doc-native)

Refines the core's「Tables carry facts, prose carries reasoning」(a cell phrase is a label,
not an argument) for doc-native carriers. **This section is the single owner of these rules**
— templates and steps carry one-line pointers plus exemplars, never restatements. (028)

- **Short form (短形)**: a slot (table cell, single-line field) holds one plain,
  self-contained sentence — ids/mechanism names as parenthetical gloss, never a bare label.
- **Home (归宿) mapping** — the full text lives at the content's home: block fields →
  indented continuation under the field (parsed into the anchored payload); table cells →
  prose in the same section outside the table; grill-log cells → the round's
  navigation-layer prose.
- **Short-enum exception**: slots holding short enumerable values (states, ids, checkboxes,
  dates) are exempt — a table is the right form for them.
- **Rich forms allowed in block fields** (陈述/why; facts.md 事实/来源): multi-paragraph
  (blank-line separated), nested lists, tables, code fences, mermaid — all indented.
- **Metadata fields stay single-line**: 类型 / provenance / depends-on.
- **Lead line (导语行)**: a 陈述's first physical line is one plain self-contained sentence
  ending with 。, ≤80 chars — the digest head-sentence extraction source; tables/code/lists
  never open a 陈述.
- **Indent is two spaces** (aligned to the field's content column); ≥4 spaces risks Markdown
  indented-code rendering.
- **Clause vs enumeration split**: lettered grammar clauses citable at `[Req-n-x]` level are
  written top-level (`- (x)`); purely enumerative or explanatory lists are written indented
  (they ride the anchored 陈述 payload).
- **Navigation-layer prose never carries a bare `resolved →`** — backtick it when quoting
  (the misplaced-decision-row scan matches raw text).
- **A shortened question cell keeps its id gloss** (parenthetical; the question-gloss hint
  flags bare ids).

## Reader-aware

Write each doc for its primary reader (each template states its Reader); the audience split is
legacy/SKILL.md「Two zones」(存量 cards; a lite card has no zone split).
