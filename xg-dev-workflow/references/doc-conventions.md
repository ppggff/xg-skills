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

## Reader-aware

Write each doc for its primary reader (each template states its Reader); the audience split is
SKILL.md「Two zones」.
