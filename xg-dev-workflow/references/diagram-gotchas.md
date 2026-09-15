# Diagram gotchas (quick reference)

<!-- KEEP IN SYNC (byte-identical pair):
       xg-dev-workflow/references/diagram-gotchas.md
       xg-knowledge-lite/references/diagram-gotchas.md
     Edit one, `cp` to the other. Checked by xg-dev-workflow/tools/check-sync.py
     (declared in tools/sync-manifest.txt); part of the conventions-core synced set. -->

Consulted only while drawing/debugging a diagram in any doc — the Mermaid traps that make a block
silently mis-render or error, plus the display-width alignment rules for the fallback case where a
diagram **must** be ASCII **and** contains CJK. The recommended path is **prefer Mermaid**
(`conventions-core.md`「Diagrams」); this is the rarely-walked detail behind it.

**Mermaid gotcha — ASCII `;`:** a bare ASCII semicolon is a statement separator even inside
sequenceDiagram message text and unquoted flowchart labels — the tail parses as a new statement
and the diagram errors. Use fullwidth punctuation in CJK diagram text; after writing, grep the
mermaid blocks for `\x3b`.

**Mermaid gotcha — `[` `]` in an unquoted flowchart label:** same shape as the `;` trap, one level
worse because our own ID conventions produce it — an **unquoted** edge/node label containing `[`
makes the parser start a *node shape* mid-label (`Expecting 'SQE' … got 'SQS'`) and the whole block
fails to render. So any label carrying an `[F<n>]` / `[R<n>]` / `[D<n>]` citation **must be quoted**:
`A -->|"事件流（非 JSONL [F38]）"| B`, `N["… [F12]"]`. Node labels written `N["…"]` are already safe;
**edge labels are the exposed form** because `|…|` looks like it quotes and doesn't. After writing,
grep the mermaid blocks for an unquoted `|`-label containing `[`.

**Mermaid gotcha — a call chain drawn as a straight line reads as N separate steps:** `A → B → C`
for outer function → inner function → the system call it makes is read as *three things that happen
one after another* (measured: "so that is three remote executions?"). What contains what goes in a
`subgraph`, whose title says what that layer *is* ("one table = one execution"). The sections a
single function prints in order are a **chain**, not a fan-out — a fan-out reads as alternatives.
Nest **two levels at most**: all clusters share one `clusterBkg`, so depth is carried only by the
border and the title, and a third level means the diagram wants splitting. When two levels really
do need separating, one `style <id> fill:#f6f6f6` on the inner one — a neutral light fill, never a
colour, because the value is hardcoded and has to stay readable in a dark theme.

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
