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

Lead the gate ask with decision cards, one line each, in this order:

1. **Load-bearing decisions this phase made** (3–5) — statement + a one-line why, each citing
   the doc section that carries the full argument. The why must have a home in the doc: a card
   whose why can't point at a coherent section isn't presentable — write the section first.
   The 3–5 ceiling caps **emphasis**, not disclosure: every remaining pending row still
   appears as a compact one-line list after the cards — a pending row missing from the ask
   would be approved by silence.
2. **Least-confident spots** (2–3) — where a human eye is most wanted: 假设/推断-marked items,
   unverified comparisons, remote-trigger sizing calls. Confidence comes from being told where
   to look, not from having read everything.
3. **Open questions** — what stays deliberately unresolved, with the default taken.
4. **The gate question + receipts** — the Stop-at-gate go ask, naming doc paths + the dev_root
   commit (SKILL.md「Ask with receipts」— unchanged, the digest sits on top of it).

## Rules

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
   (the phase doc's status field flips only when its level is fully approved — R12).
