# Step: 设计 (design + grill)

Forked from **grill-with-docs**. Adjusted: the artifact is this requirement's `design.md`
+ `adr/` (not repo-root CONTEXT.md); reusable concepts/terminology route to
**xg-knowledge-lite**, not CONTEXT.md; the no-望文生义 evidence rule (M1) is enforced; ends
with the **freeze gate**.

Output: `design.md` (template: `references/templates/design.md`) + ADRs via `adr.md` step.

## Core values (read first — these outrank any single technique)

- **简单可靠 > 精致复杂 (overriding).** Prefer the simplest design that's *reliable* — simple =
  easy to implement, test, and verify-correct. Complexity must earn its place; don't chase
  elegant-but-complex. Within simplicity, still aim for a clean, **elegant** shape (美观优雅 —
  applies to both design and code). (反过度设计.)
- **找本质思路.** Find the one essential approach first, then apply it down the **层次 (layers)**
  and across the modules — the right layering dissolves whole classes of problem a flat module
  list leaves tangled.
- **方案优先.** Surface **multiple candidate approaches** and grill each one's **trade-offs**
  before settling structure (a primary goal of the grill). A design may be driven by the
  **normal flow OR by a dominant anomaly flow** — find which is the hard part first.
  **Comparison/evaluation tables carry a provenance column from the first draft**
  (VERIFIED / INFERRED / 推断 per cell-claim, M1) — a comparative claim about existing code
  ("X has no cache") is a code claim and needs the same evidence as any other; an unverified
  comparison table is how an overstated trade-off gets approved (2026-07-06: "零cache/零save
  hook" survived into a decision table unread, corrected only on human pushback).
- **抵御所有异常 (异常完整性).** Every anomaly gets an owning module or a fallback — a manual-intervention
  floor is acceptable — but a rare case does **not** earn its own structure. Alongside, weigh
  可测试性 (mock 周边、独立可测) · 可观测性 (坏了能定位到本模块) · 性能 + 规模放大后的性能.

## Altitude (design at the module level, not the code level)

A design describes **modules, responsibilities, boundaries, and contracts** — *what* talks to
*what* and *why* — not concrete code. Borrowed from **api-and-interface-design**:
- **Contract-first** — define each module's responsibility + the interface/semantics across a
  boundary before any implementation. The contract is the design; implementation follows.
- **Don't leak implementation details** into the design — specific functions, file paths,
  lock primitives, hook names, struct fields, SQL belong in **`plan.md`**, not here. Keep the
  design valid even if the implementation changes.
- **Build on existing modules** — frame the change in terms of the modules that already exist
  (what they own, where the seams are); the new piece is usually a thin module between them.
- **Layer the design, not just split modules** — place modules within **abstraction layers**;
  pick the layering that makes each layer simple to reason about (each assumes the layer below,
  serves the one above). Find the essential 思路 first, then realise it across the layers.
- Evidence (M1) still grounds load-bearing claims, but **cite it via KB `[[wiki/<project>/<slug>]]`**
  (or "deferred to plan") rather than inlining code into the design body.

If a reviewer needs a function name to understand the design, the design is too low; lift it.

## Diagrams (required)

`design.md` must include at least:
- a **module-interaction diagram** — the components/modules as boxes, the calls/seams between
  them as arrows (who invokes/depends on whom);
- a **data-relationship / data-flow view** — what data crosses each boundary and in which
  direction (a second diagram, or annotations on the first).

**Prefer Mermaid** — a ```` ```mermaid ```` fenced block (`flowchart`/`graph` for module
interaction, `sequenceDiagram`/`flowchart` for data flow). It renders in GitHub/Obsidian/VS Code
yet still diffs as text, and sidesteps the CJK-alignment pain below. Fall back to ASCII only for a
trivial diagram or one Mermaid can't express. Either way: label each box with its responsibility
and each arrow with what flows. A diagram that only restates the prose adds nothing — it must show
structure the prose can't.

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

## Procedure

1. **Understand before designing (M5).** Concept → layer. Query xg-knowledge-lite for what
   we already know — **Orient surfaces the project's `architecture` overview + `*-invariants`
   ledgers first** (the map + the rules); use Plan Mode / Explore subagent to investigate existing
   code (read-only). **Link this design to `[[wiki/<project>/architecture]]`** rather than
   re-describing the system. Capture genuinely reusable module knowledge to the KB
   (`[[wiki/<project>/<slug>]]`), don't bury it in `design.md`.
   **Card graduated with pre-design:** when the card was born from another card's M2/grill
   evaluation note that already reached design (even LLD) depth, this phase *consumes* that
   note — ADR-ize the decisions, build the trace/影响面, link the note as source — rather than
   re-deriving; the grill then targets what the note left open, not settled ground.
2. **Draft the chosen approach** in `design.md` **at module altitude** (see Altitude): modules
   + responsibilities, boundaries, contracts, invariants. **Required elements**: a
   **思路** up top — the single core strategy in **≤2 plain sentences** (name the one
   method + its punchline; **no** mechanism/perf/alternatives detail — see template's good/bad
   example); the **diagrams** (module-interaction + data-flow); and — when the design introduces a
   module — its **external interface as a contract** (operations: inputs/outputs/semantics +
   invariants, not signatures). Defer concrete code to `plan.md`;
   load-bearing claims cite evidence via KB links.
   - **Part decomposition (only if splitting — SKILL.md「拆分与隔离」A).** If the design splits
     into parts, fill the **「Decomposition / Parts」** table: name each part (a group of modules
     built & tested as one unit) + the **seam** to its neighbors. The seam's contract is the
     existing 「Interface/contract」entry and **freezes with the design** — that freeze is exactly
     what lets each part be built & unit-tested independently (mock the neighbor) before it exists.
     Grill the cut: are parts genuinely independent at the seam, or is the seam leaky (then it's
     one part, not two)? A seam disproved later at 联调 → M2 (`seam-contract-disproved`), never a
     silent plan edit. Omit the table for an un-split design.
3. **Grill it relentlessly** — the shared protocol + **grill-log** + **rollback** + **convergence
   auto-verdict** live in `grill.md` (a drafting-phase rollback re-walks superseded branches; once
   frozen, changes go through M2). Walk each branch of the design tree with the design-specific
   lenses below.
   - **Sharpen language → canonical term + `_Avoid_`** — for each domain term, pick **one**
     canonical name and name the synonyms to avoid (grill-with-docs' opinionated glossary).
     Define it by what it **IS, not what it does** (1–2 tight sentences). Record it as the
     **canonical term of the KB concept** (`[[wiki/<project>/<slug>]]`) / the project `CONTEXT-MAP.md`,
     not in `design.md`. **First infer the term's bounded context** (from CONTEXT-MAP); if it
     could belong to more than one, **ask**. Same word in two contexts = OK if scoped (note the
     homonym); same word twice **within** a context, or colliding with a canonical/`_Avoid_`
     there → flag and reconcile.
   - **Stress-test with concrete scenarios** — invent edge cases that force precision about
     boundaries between concepts.
   - **Cross-reference code (grep before accepting)** — when the human says how the code works
     today, verify (≥1 grep + 1 read) before taking it as fact; hallucinated agreement is worse
     than an honest "didn't check". Surface contradictions immediately.
   - **Correctness lens (systems work)** — grill the design on: is a "skip / ignore" actually
     *safe* or only *live* (prefer fail-safe — defer/refuse — over fail-unsafe); who is the
     **authority** for each value (consumers record it, don't re-judge across an XID/namespace
     boundary); **concurrency** (a snapshot taken before a lock can race with concurrent
     mutation). Code-level checks (upstream-replication completeness + sibling-site audit,
     no blocking I/O under a lock, dead/no-op hooks) are revisited in 实现's review lens
     and in the `review` verb's whole-change pass.
   - **Walk the design-quality lenses (per Core values)** — for each candidate approach grill
     简单可靠 (首要) · 可测试性 · 可观测性 · 异常完整性 (每异常有归属或兜底,兜底可人工;罕见不另立
     结构) · 性能 + 规模放大后的性能. For genuinely architectural designs also walk the
     **lifecycle** (bootstrap / 升级 / 回滚 / 长跑漂移 / 下线), each phase with an owner (opt-in —
     skip for structure-light changes).
   - **Module-depth lens (`codebase-design`)** — is the new module **deep** (small interface, lots
     hidden) rather than **shallow** (pass-through)? Apply the **deletion test**: delete it — if
     complexity vanishes it was a pass-through; if it reappears across N callers it earns its keep.
     **Don't introduce a seam/port for a single implementation** — one adapter is a *hypothetical*
     seam, two is a *real* one (反过度设计).
   - **方案优先 / explore solutions before structure** — surface multiple candidate approaches and
     grill their trade-offs before committing; pick on trade-off, not first idea. Identify whether
     the **normal flow or a dominant anomaly flow** is the hard part — either may drive the design.
     **Span the hack ↔ 补丁 ↔ 推翻重来 spectrum** and grill each one's **cost** (工期 / 技术债 /
     影响面 / 可维护性): the quick hack, the localized patch, the proper redo. The full redo is
     often the *correct* shape but isn't automatically right (it still must pass 简单可靠 /
     反过度设计); a hack/patch must be a **conscious, recorded debt decision**, not a default. Pick
     the spectrum point the trade-off justifies and say why. Any comparison/evaluation table
     produced here carries the provenance column from the first draft (Core values 方案优先).
     **Two axes of alternatives:** this **solution-class** axis (hack/补丁/重做) and — when the
     design introduces a **non-trivial module** — an **interface-shape** axis: optionally run
     `codebase-design`'s **Design-It-Twice** (parallel agents each design a radically different
     interface — minimal / flexible / common-case / ports&adapters — then compare on
     depth·locality·seam and recommend/hybrid). Optional, costs parallel agents — skip for
     structure-light work.
   - **Fresh-context adversarial panel (`adversarial-critic.md`)** — don't only grill from inside
     your own design. At each design-tree checkpoint run the three fresh-context lenses
     (causal-coverage · invariant-ledger replay · search-before-build) + the three standing rules
     (verify-the-assumption · re-apply-the-signature · class-to-constraint), so the agent
     reaches the decisive cuts itself instead of waiting for the human to land them. Dispatch per that step's stake tiers:
     **M+ decision-level checkpoints → parallel one-agent-per-lens; XS/S designs / edit-only
     rounds → the single-agent form**, with the **verified-facts pack** attached on every round
     after the first; rewrites of already-grilled decisions get only a lightweight
     text-consistency agent. The lenses also apply to
     **every newly proposed remediation/mechanism mid-grill** (run search-before-build on the fix
     itself before designing it), not just the design under test.
   - **Don't grill to death** — ~3 rounds on one point, then record an Open question and move on.
   - **Convergence — run the shared auto-verdict** (`grill.md`「Convergence」, the canonical
     rule): end every round with the one-line 继续/建议收敛 verdict — decision-level dry check
     against the doc's diff since the last grill checkpoint + ADR-weighted open points; the
     human still gates. (Calibration example — HatchDeck MS1: design round 3 yielded only
     detail-level items, a dry round; that was the stop signal.)
   - **Update `design.md` inline** — as each decision crystallises, write it into the doc
     right then; don't batch edits to the end. The doc tracks convergence in real time.
4. **Map to the requirement by R-id** — fill "How it meets the requirement": each
   `requirement.md`「需求条目」`R-id` → the module/contract that satisfies it (plus scope/
   constraints/effect/future). An R-id with no design home is a gap → back to 需求 or change-management.
   **Then fill the 验证策略 table (M+; XS/S may omit)** — per R-id/Effect item: the shortest E2E
   scenario that would prove it + the observation point the design provides. Grill each row: an
   item with no cheap E2E path becomes an **explicit decision** (unit-level proxy accepted with a
   why, or the design changes for observability) — never a blank silently deferred to 测试.
5. **Analyse the 影响面 (impact surface)** — fill the design's 影响面 section: changed/added
   modules, existing callers & downstream consumers, compat/ABI surface, cross-card/cross-project
   ripples (cf. `index.md` Deps), and behaviors to re-verify. Grep for callers rather than
   guessing; mark 推断/假设. This scopes risk and seeds `test.md` regression + the close-out review.
6. **Record ADRs** for decisions that are hard-to-reverse + surprising + a real trade-off
   (see `adr.md`).
7. **Freeze gate:** present via the gate digest (`gate-digest.md` — decision cards citing doc
   sections, least-confident spots, open questions, then the go ask with receipts); on human
   approval set `status: frozen`. From here, `design.md` changes
   only through change-management (M2). On freeze, **update the KB** (as-built): refresh the
   `[[wiki/<project>/architecture]]` overview to the shape this card establishes, and add any
   **durable invariant** it established to the subsystem's `*-invariants` ledger — so the next
   card's grill starts from a sharper map.

## Runtime override
`design use:grill-me` (pure grilling, no doc side-effects) or `use:<your-skill>`.

## Done when
- Approach is evidence-grounded, grilled to shared understanding, mapped to the
  requirement, ADRs recorded, `status: frozen`. Then run the omission check (M3).
