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

Lead the gate ask with decision cards, one line each, in this order:

1. **Load-bearing decisions this phase made** (3–5) — statement + a one-line why, each citing
   the doc section that carries the full argument. The why must have a home in the doc: a card
   whose why can't point at a coherent section isn't presentable — write the section first.
2. **Least-confident spots** (2–3) — where a human eye is most wanted: 假设/推断-marked items,
   unverified comparisons, remote-trigger sizing calls. Confidence comes from being told where
   to look, not from having read everything.
3. **Open questions** — what stays deliberately unresolved, with the default taken.
4. **The gate question + receipts** — the Stop-at-gate go ask, naming doc paths + the dev_root
   commit (SKILL.md「Ask with receipts」— unchanged, the digest sits on top of it).

## Rules

- **Presentation, not a new doc.** Nothing lands on disk beyond the phase doc; the cards restate
  the doc's decisions and never introduce new ones — a decision that exists only in the digest is
  an omission (write it into the doc first; M3).
- **Scale down, never pad.** An XS phase with two decisions sends two cards. The 3–5 / 2–3 counts
  are ceilings for a typical M card, not quotas.
- **Approving the digest approves the phase doc.** The doc stays the durable, authoritative
  artifact; the human may always drill in — each card names the section to jump to.
- **Execution-zone surfaces already exist — point, don't duplicate.** The test phase's human
  surface is the coverage matrix + its gap rows (`test.md`); the close-out's is the review
  报告's 修复决策表. Cite those, don't restate them as cards.
