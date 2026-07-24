# Diagram gotchas (quick reference)

Consulted only while drawing/debugging a `design.md` diagram — the Mermaid traps that make a block
silently mis-render or error, plus the display-width alignment rules for the fallback case where a
diagram **must** be ASCII **and** contains CJK. The recommended path is **prefer Mermaid**
(`design-grill.md`「Diagrams」); this is the rarely-walked detail behind it.

**Mermaid gotcha — ASCII `;`:** a bare ASCII semicolon is a statement separator even inside
sequenceDiagram message text and unquoted flowchart labels — the tail parses as a new statement
and the diagram errors. Use fullwidth punctuation in CJK diagram text; after writing, grep the
mermaid blocks for `\x3b`.

**Mermaid gotcha — subgraph `direction` is ignored when the subgraph has external links**
(documented limitation): any edge crossing the subgraph boundary makes the subgraph inherit the
parent graph's direction, so a "two vertical columns" layout built from `direction TB` subgraphs
+ cross edges silently renders flat. Don't fight the layouter with invisible `~~~` chains either
— if a diagram is too dense, **reduce its semantic node/edge count** (merge same-role nodes,
move detail to a caption) instead of forcing geometry.

**ASCII fallback — CJK width:** every Chinese character and Chinese punctuation occupies **2 columns**; ASCII,
box-drawing (`┌ ─ ┐ │ └ ┘`), and arrows (`▼ ▲ ▶`) are **1 column** in standard monospace.
Use the box-drawing/arrow glyphs (nicer than `+ - | v`). The alignment bug is CJK *content* —
pad each content line by *display width* (CJK=2, glyphs=1). **Pick the layout that shows the
structure**, not whichever is easiest: a fan-in/fan-out (e.g. two callers → one module) needs
**side-by-side** boxes; a pure pipeline reads well **vertical**. Side-by-side CJK boxes are the
hardest to align by hand, so **generate with a tiny width-aware script** (compute box centers,
place the join `┬`/arrows by column) rather than counting — that makes horizontal fan-in cheap.
Gotcha: an **inline CJK label on a connector row** (e.g. `│ 经 hook   │`) shifts every glyph
after it if you place by character index — compose connector rows by **display column** (pad to
each target column accounting for CJK=2), or a later `│` won't line up with the `┘` below it.
