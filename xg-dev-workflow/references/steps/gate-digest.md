# Step: gate digest (shared — the decision-card ask at every decision-zone gate)

A **shared mechanism** (like `grill.md` / `adversarial-critic.md`), not a phase. Applies to every
decision-zone gate ask — 需求 confirm · 设计 freeze · 详设 baseline · the execution authorization
after `plan.md`.

Why: a gate is only real if the human can exercise judgment there. Phase docs serve completeness
and audit, and their volume exceeds gate-time reading bandwidth — in practice gates get
approved on grill-trust rather than reading. The digest inverts the burden:
the model surfaces what deserves human attention; the doc is the reference to drill into, not the
reading assignment.

## The digest (in the gate-ask chat message)

**Cards are generated from the ledger** (`decisions.md`, templates/decisions.md): each card
restates a pending (proposed) row — 陈述 + a why excerpt + its `alt:` lines + provenance —
**never a bare pointer**; present in dependency order (`depends-on`), requirement-level rows
before design-level. A card with no ledger (pre-010) falls back to the doc-cited form below.

Lead the gate ask with decision cards — **written for comprehension**: full sentences
restating 陈述 + why + the rejected alt (plus a concrete example when the decision is
abstract), never compressed to labels. Items 2–3 are a pair — without them the digest says
*what* was decided but not *what the human's judgment is needed on*; keep both, scaled down
for small gates. In this order:

1. **Load-bearing decisions this phase made** (3–5) — statement + a one-line why, each citing
   the doc section that carries the full argument. The why must have a home in the doc: a card
   whose why can't point at a coherent section isn't presentable — write the section first.
   The 3–5 ceiling caps **emphasis**, not disclosure: every remaining pending row still
   appears as a compact one-line list after the cards — a pending row missing from the ask
   would be approved by silence.
2. **已验证（勿复核）** — what this round's machine/adversarial verification already covered:
   one line per verification + its method/receipt pointer. Per-item correctness is
   backstopped by the verification flow and the close-out review, not by human re-reading —
   the gate approves **direction**, not line-by-line accuracy.
3. **待你判** — the owner trade-offs an agent can't make, numbered, each naming its **stake**
   (what gets deleted / what tax is added / what bet is taken). Sources: pending rows' `alt:`
   trade-offs, downgrade-class decisions, risk bets — plus the **least-confident spots**
   (假设/推断-marked items, unverified comparisons, remote-trigger sizing calls): confidence
   comes from being told where to look, not from having read everything.
4. **Open questions** — what stays deliberately unresolved, with the default taken.
5. **The gate question + receipts** — the Stop-at-gate go ask, naming doc paths + the dev_root
   commit (SKILL.md「Ask with receipts」— unchanged, the digest sits on top of it).

## Rules

- **Decision-object references are self-contained.** A card whose decision object is a
  list/count ("the 16 bad edges", "the Top-10 sections") inlines the items one line each, or
  links their home doc; >5 items → link plus inline the judgment-heaviest subset. **Evidence
  references** (file:line provenance anchors) are exempt — they are spot-check anchors, not
  required reading. A digest readable only with the current session's context fails a fresh
  reader (resume, or a different approver).

- **Presentation over the ledger, not a new doc.** The digest cards themselves never land on
  disk; what lands is the **ledger row** (`decisions.md`) and the phase doc. A decision that
  exists only in the digest is an omission — enter it as a proposed row (and its home section)
  first; M3/--check catch the reverse (a doc-cited id with no ledger row).
- **Scale down, never pad.** An XS phase with two decisions sends two cards. The 3–5 / 2–3 counts
  are ceilings for a typical M card, not quotas.
- **Approving the digest approves the phase doc.** The doc stays the durable, authoritative
  artifact; the human may always drill in — each card names the section to jump to.
- **Execution-zone surfaces already exist — point, don't duplicate.** The test phase's human
  surface is the coverage matrix + its gap rows (`test.md`); the close-out's is the review
  报告's 修复决策表. Cite those, don't restate them as cards.

## Approve transcription (on the human's go)

The go is the approval; Claude transcribes it into the ledger — never ahead of it:

1. The gate ask's receipts commit already carries the ledger state the human saw.
2. On go, for each approved row: header `proposed` → `approved` + append
   `- approved: <date> gate <receipts-commit short hash>`.
3. Commit immediately (the gate commit) — approve transcription sits adjacent to its
   receipts commit in git, auditable via `git log -S`.
4. **Partial approve is legal**: only the rows the human named flip; the rest stay proposed
   (the phase doc's status field flips only when its level is fully approved — the
   derived-status rule, SKILL.md「Ledger」).
