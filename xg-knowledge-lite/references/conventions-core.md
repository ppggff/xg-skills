# Writing conventions — shared core

<!-- KEEP IN SYNC (byte-identical pair):
       xg-dev-workflow/references/conventions-core.md
       xg-knowledge-lite/references/conventions-core.md
     Edit one, `cp` to the other. Checked by xg-dev-workflow/tools/check-sync.py
     (declared in tools/sync-manifest.txt). Skill-agnostic rules ONLY — anything that
     references one skill's own artifacts belongs in that skill's supplement
     (xg-dev-workflow: references/doc-conventions.md; xg-knowledge-lite: SKILL.md
     writing block / FORMAT.md). `diagram-gotchas.md` ships alongside as part of the
     same synced set. -->

## Writing style & structure

- Plain prose, technical terms intact (不变量 / 契约 / 幂等 stay); short sentences.
- **Structure over paragraphs**: parallel or enumerable content (conditions, steps, per-module
  points) goes in nested lists — one point per bullet; paragraphs are reserved for reasoning
  that genuinely chains (evidence → mechanism → conclusion). A paragraph packing ≥3 parallel
  points is the smell — restructure it as a list.
- **Short lines** — wrap prose around ~100 chars; a list item that runs long **splits into
  sub-bullets** (one clause per line) instead of one long line; rewrap existing long lines
  opportunistically when editing.

## First-use gloss

A coined term, codename, or non-standard abbreviation carries a one-line parenthetical at its
first use per doc (and per chat session); **after that, use the term bare** — the gloss is paid
once. A term used fewer than ~3 times isn't coined at all. Established domain terms need no
gloss.

## Provenance (three-class marking)

Load-bearing claims carry a marker: evidence-cited / 推断 (inferred) / 假设 (assumption) —
only the claims a decision rests on. An uncited non-trivial assertion is flagged
(`UNVERIFIED:` / `(assumption)`), never left bare.

## Tables carry facts, prose carries reasoning

Tables hold contracts / enumerable facts / comparisons; a compressed phrase in a table cell is
a label, not an argument — its rationale lives as prose in the same section. A load-bearing
conclusion is derived in the text (evidence → mechanism → conclusion), not bolted onto a fact
table.

## Diagrams

**Mermaid preferred**; ASCII only for the trivial or what Mermaid can't express. Pitfalls and
the CJK display-width rules for a forced ASCII diagram: `diagram-gotchas.md` (shipped alongside
this file).

## KB cross-references

Keep the `[[<layer>/<project>/<slug>]]` wikilink form — it is load-bearing for the KB's
incremental recompile; don't swap it for a markdown link.
