# Doc conventions (all workflow docs)

The writing rules for every doc this skill produces — phase docs, investigation/review notes,
and KB 注记 alike. SKILL.md keeps the resident essentials (the writing-style block, provenance
markers, the wikilink form rule, Mermaid preference, core ID prefixes) and points here; this file
is the single owner of the full rules. Read it before writing any workflow doc.

## Writing style & structure

- Plain prose, technical terms intact (不变量 / 契约 / 幂等 stay); short sentences.
- **Structure over paragraphs**: parallel or enumerable content (conditions, steps, per-module
  points) goes in nested lists — one point per bullet; paragraphs are reserved for reasoning
  that genuinely chains (evidence → mechanism → conclusion). A paragraph packing ≥3 parallel
  points is the smell — restructure it as a list.
- **Short lines** — wrap prose around ~100 chars; a list item that runs long **splits into
  sub-bullets** (one clause per line) instead of one long line. Applies to phase docs and this
  skill's own files (rewrap existing long lines opportunistically when editing them).

## First-use gloss

A coined term, codename, or non-standard abbreviation carries a one-line parenthetical at its
first use per doc (and per chat session); **after that, use the term bare** — the gloss is paid
once. A term used fewer than ~3 times isn't coined at all. Established domain terms need no
gloss.

## Links (clickable where cheap)

- Intra-requirement/project references: standard markdown links (`[design](./design.md)`).
- KB cross-references keep the `[[wiki/<project>/<slug>]]` wikilink — load-bearing for the
  KB's incremental recompile; don't swap it for a markdown link.
- **An ID cited from another file is a markdown link to its home** — `[R1](./requirement.md)`,
  `[ADR-0006 D5](./adr/0006-<slug>.md)`, `[T3](./plan.md)`. Designated mapping fields and a
  doc's first mention always link; repeat prose mentions and same-file citations stay bare.

## Provenance

Load-bearing claims carry a marker: evidence-cited / 推断 (inferred) / 假设 (assumption). Only
the claims a decision rests on (M1). Provenance may **centralize** into `F<n>` fact blocks cited
inline as `[F<n>]`; `F<n>` is a **per-container scoped id** (like `R<n>`/`S<n>`): on a card, the
container is the card's `facts.md` — phase docs cite it and never keep a doc-local fact list of
their own; a **standalone** doc (investigation/review note, no card) uses a doc-local
「事实清单」section instead. One container per doc, never both; the inline marker form stays for
isolated load-bearing sentences.

## Reasoning shown (human-first docs)

requirement/design/detail/ADR/review and investigation-notes prose carries the logical analysis,
**evidence → mechanism → conclusion**, so the approver can check the inference, not just trust
the citations — a fact table with a conclusion bolted on is a grep-hit list at doc level.
Execution-zone docs stay terse: link the reasoning, don't restate it. **Tables carry facts,
prose carries reasoning**: tables hold contracts / enumerable facts / comparisons; a compressed
phrase in a table cell is a label, not an argument — its rationale lives as prose in the same
section.

## Reader-aware

Write each doc for its primary reader (each template states its Reader); the audience split is
SKILL.md「Two zones」.
