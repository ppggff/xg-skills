# Ask routing — shared core (two-lane)

<!-- KEEP IN SYNC (byte-identical pair):
       xg-dev-workflow/references/ask-routing-core.md
       xg-knowledge-lite/references/ask-routing-core.md
     Edit one, `cp` to the other. Checked by xg-dev-workflow/tools/check-sync.py
     (declared in tools/sync-manifest.txt). This file is the single source of the
     routing CORE — carrier-agnostic wording only (「交人判条目」,「该面的 open 项
     载体」); how each surface maps its own carriers onto these rules lives with
     that surface's hook sentence (xg-dev-workflow: grill/gate-digest/review/retro
     steps; xg-knowledge-lite: the lint report-only buckets), never here. -->

**Load-bearing precondition (named, 024 R6): every ask is self-contained** — the solo
channel only works when a single question carries everything needed to answer it (context,
recommendation, trade-off; no undefined shorthand, no numbering back-references as the
main clause). The routing below assumes it.

## The three tiers (incorporation framing — no new autonomous authority)

交人判条目 route through three tiers. Tier 0 is the **naming of existing channels**
(evidence-settled labeling, below-decision-level transcription additions, mechanical
fixes under existing authorization) — zero new self-serve authority; adversarial-verdict
routing stays with the gate's 待你判 section. The human-judgment remainder splits:

- **Tier 1 照案 (batch)** — rows a reader can accept/reject from the row alone: each row
  carries recommendation + trade-off + **evidence anchor (mandatory)**; a row that can't
  say it in one line escalates to Tier 2.
- **Tier 2 真判 (solo)** — one question, one decision, asked alone.
- **拿不准 (unsure) group** — presented as its own group, never mixed into the 照案 table;
  every row names its uncertainty point. Numeric confidence scores are banned **on the ask
  surface only** (internal adjudication filters may use them).

## Tier 2 escalation criteria (closed list)

A candidate is Tier 2 when any of these holds:

1. 真实权衡 / 风险接受 (a real trade-off, or accepting a risk)
2. 定方向或边界归属 (sets direction, or assigns a boundary/ownership)
3. 触及已批行 (touches an approved decision)
4. 不可逆 (hard to reverse)
5. 高扇出 (high fan-out — many downstream items hang on it)
6. 意图不明 (the human's intent is unclear)
7. 悬于 UNVERIFIED 前提 (rests on an unverified premise)
8. 挑战应答 (the reply to a human's challenge)
9. 同形被否 (the same-shaped recommendation was previously rejected)

## Decision order

1. **Closed list first** — any hit above → Tier 2.
2. **Test 1** — would the human's answer merely restate the recommendation? (yes → the ask
   is not a judgment; keep it Tier 0/1.)
3. **Test 2** — is the missing information something **only the human holds**? (narrowed
   wording: information, not preference.)
4. Still undecided → the 拿不准 group.

**Tier 1 admission precondition:** the Recommendation pre-check passes all four gates
(载重前提 VERIFIED · magnitude × medium · cost symmetry · 价值归属); a proposal failing
any is presented as an open question, never as a 照案 row.

## Value-rewrite direction

Tier changes are one-way toward caution by default: 拿不准/照案 → 真判 on any human touch;
拿不准 → 照案 only by the human's whole-group release. A general reply (「其他按推荐」)
covers only the listed 照案 rows — the 拿不准 group needs its own per-row answer or an
explicit named-group release.
