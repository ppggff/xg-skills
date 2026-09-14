# Split and isolate (拆分与隔离) — an L card's two granularities

Both optional and independent; a card small enough is not split. lite.md「By size」L: run the A↔B call first.

## A — parts inside one design.md (part 化)

A design splits into **parts** — named blocks of ≥1 module, each implemented and tested as a unit — with
**seams** between them. Each seam's contract is a row in `design.md`「当前方案」(the seam contract, cited from
「契约与不变量」); at go it becomes a commitment, which is what lets the parts be built and unit-tested
independently against mocked neighbors. The part axis runs through `plan.md` (a `Part` column or grouping)
and 「测试与验证」(one 联调 row per seam). A seam contract **disproved by 联调** is an approach change: an
A→B walk (lite.md「Executing」) when the commitments still hold, otherwise the three-case ask — never a
silent plan edit. Each part's completion gets one fresh-context attack on its diff (lite.md).

## B — several cards + the board

Too big → several cards (`new` again). `index.md` is the board: one row per **card** (one `NNN-slug/` dir,
one lifecycle); it shows Phase (`lite` for a lite card) + 整体状态 (the human's scheduling axis, separate from
the card's internal `status`) + Deps (same-project NNN, acyclic — the board check). `resume` stays
single-card; the board locates, it is never a status source.

**Card or fog?** A split-out item that can be **stated precisely** (not necessarily answered) → a card or a
roadmap Next-up line; still vague → roadmap Themes / Someday (fog), made concrete as earlier cards advance —
never pre-cut fog into cards. In prose refer to a card by name (NNN in the link), not a bare number.

## Split-out — the five steps after a B verdict

The human confirms the B verdict (a 待确认 proposal in the doc); then, each step pointing at its owner:
1. **Child card**: the `new` verb (number · dir + design.md skeleton · board row; a roadmap-born slug is
   marked graduated in the roadmap).
2. **Commitment hand-over**: the parent Req gets 状态词 放弃 + a 变更 line naming the child (`移交 → NNN`);
   the child's Req cites the parent (`承接 <NNN> Req-n`). Ids are never renumbered.
3. **Board Deps**: parent and child record each other in `index.md` Deps.
4. **Seam as a named contract**: home = the **provider** card's `design.md`「契约与不变量」row; before the
   provider's go, both cards carry the contract's key points as Req constraints, formalized at its go.
5. **The remainder**: what is left goes through the card-or-fog call — a card, or a roadmap fog line — never
   left hanging.

Terms, one canonical form each: **part** · **seam** · **联调** (the seam-level integration row) · **card** ·
**整体状态**. Colloquial "part / 部分" and a repo's own "Integration" test bucket are context-disambiguated.
