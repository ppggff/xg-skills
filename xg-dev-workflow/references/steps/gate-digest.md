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
restates a pending (proposed) row — 陈述 + why + its `alt:` lines + provenance —
**never a bare pointer**; present in dependency order (`depends-on`), requirement-level rows
before design-level. A **doc-gate card** (017 D2 — `governance: doc-gate`, no ledger) uses the
**scaled digest** in「Doc-gate cards」below; a legacy card with no ledger (pre-010) uses the
same scaled form with doc-cited points in place of cards.

**Layout: every section renders as a list** (the conventions-core structure-over-paragraphs
rule applied to the chat digest); a card's 陈述 / why / alt / 锚点 each get **their own
sub-bullet line**, never compressed into the header line. Section 1's self-check lines and
section 5 (待你判) are a pair — without them the digest says *what* was decided but not
*what the human's judgment is needed on*; keep both, scaled down for small gates. In this order:

1. **Grill / 自检状态 (lead section — is this ask qualified to be judged?)**
   - The grill **convergence verdict** (grill.md auto-verdict): 继续/建议收敛 + this round's
     facts only.
   - The **mandatory self-check checklist**, strictly one line each — `verifier · receipt
     pointer · verdict`: adversarial panel (lenses + verdicts — adversarial-critic.md
     「Receipts」), the criterion-conformance judge (lens 4), any micro re-verify, M3 /
     `workflow-status.py --check`. What a round *found* is grill-notes content the receipt
     already reaches — never restated here; the whole section caps at ~10 lines. These lines
     carry the **已验证（勿复核）** role: an entry that names no
     dispatched verifier is a self-verification and doesn't belong; per-item correctness is
     backstopped by the verification flow and the close-out review, not by human re-reading —
     the gate approves **direction**, not line-by-line accuracy.
   - A one-line conclusion: 自检无欠账、gate 可判 — or what is still owed (owed → run it
     first; the ask is not presentable).
2. **Decision cards** (3–5 emphasized) — fixed card layout, written for comprehension
   (full sentences; plus a concrete example when the decision is abstract). **A card is
   ≤7 lines total**:
   - bold header: `[<id>] <一句话陈述标题>`;
   - sub-bullets, one per line — `陈述:` the full-sentence decision (1–2 lines) · `why:`
     ≤2 lines (the why
     must have a home in the doc: a card whose why can't point at a coherent section isn't
     presentable — write the section first) · `alt（拒）:` one line per rejected alternative,
     ≤2 shown (further alternatives live at the 锚点) ·
     `锚点:` the doc §section carrying the full argument.
   - **No other sub-bullets.** 注意/连带/已知情形-style caveats have a home — the ledger row
     or a doc § the 锚点 reaches; no home yet → write the home first, then cite it. Inlining
     them is how a card doubles.
   - The 3–5 ceiling caps **emphasis**, not disclosure: every remaining pending row still
     appears after the cards as a `其余 pending（一并批）` id list **grouped by level (1–2
     lines per level)** — a pending row missing from the ask would be approved by silence;
     rows needing individual attention (e.g. an Effect enumeration key changed since approval)
     are named out of the group, one line each.
3. **Phase attachments** — as lists: 设计 freeze inlines the `--trace` matrix summary
   (see Rules); the requirement confirm ask restates the **拆分审视 verdict line**
   (steps/requirement.md beat 8 — one line, 拆/不拆 + 理由); enumeration-criterion tables
   follow the paste-the-table rule below; other phases attach what their step prescribes.
4. **假设 closure sweep** — when the phase step requires it (e.g. design freeze): the doc's
   load-bearing 假设/推断 markers — plus any（落纸补充）transcription additions, listed one by
   one (grouped by section when numerous), cleared on approve (grill.md Discussion-first
   flow) — each discharged or carried-with-a-home.
5. **待你判** — the owner trade-offs an agent can't make, numbered, **≤3 lines each: the
   question + its stake** (what gets deleted / what tax is added / what bet is taken);
   background by reference to a card or doc §, not restated. Sources: pending rows' `alt:`
   trade-offs, downgrade-class decisions, risk bets — plus the **least-confident spots**
   (假设/推断-marked items, unverified comparisons, remote-trigger sizing calls): confidence
   comes from being told where to look, not from having read everything.
6. **Open questions** — what stays deliberately unresolved, with the default taken.
7. **The gate question + receipts** — the Stop-at-gate go ask, naming doc paths + the dev_root
   commit (SKILL.md「Ask with receipts」— unchanged, the digest sits on top of it); state that
   **partial approve is legal** (the human names rows — Approve transcription below; doc-gate
   cards: all-or-nothing per doc instead,「Doc-gate cards」).

## Rules

- **Panel-receipt precondition.** Before presenting any gate ask: every decision-level
  checkpoint this phase passed has a panel receipt, and the **criterion-conformance judge**
  (adversarial-critic.md lens 4) has run against this gate's criteria — its per-criterion
  verdicts feed section 1's self-check lines (satisfied rows) and 待你判 (key-mismatch /
  not-satisfied rows are exactly what the human must rule on). Missing receipts → run the
  panel first; a gate ask
  without them presents self-certified work as verified — the failure this rule exists to block.
- **设计 freeze asks attach the trace gap summary, not the matrix.** Run `workflow-status.py
  --trace <project>/<card>`; inline the **gap rows only** — an R-id with no design home is a
  gap the ask must name, not paper over — plus a one-line 统计 (`N/N 有落点，缺口 0`) and the
  command for the full matrix. Never inline the full output. At freeze time the task/test/
  commit columns are legitimately empty. Later gates may re-attach the same summary as the
  columns fill (optional there).
- **Enumeration criteria: paste the table, not the conclusion.** A criterion of the form
  "every X …" claimed satisfied is presented as its table (declared key × rows × evidence
  columns, blanks visible) or its missing-row list — never as a prose conclusion
  ("已核过 / covered"). Blank cells and key mismatches are what the gate exists to show.
  These tables are **exempt from the >5-items link-out threshold below** (like evidence
  references): the table is the judgment surface. A genuinely large one (>~10 rows) inlines
  every incomplete/key-mismatch row + links the full table — complete rows are spot-checkable
  there; the criterion still never closes on a row count alone.
- **Decision-object references are self-contained.** A card whose decision object is a
  list/count ("the 16 bad edges", "the Top-10 sections") inlines the items one line each, or
  links their home doc; >5 items → link plus inline the judgment-heaviest subset. **Evidence
  references** (file:line provenance anchors) are exempt — they are spot-check anchors, not
  required reading. A digest readable only with the current session's context fails a fresh
  reader (resume, or a different approver).

- **Presentation over the ledger, not a new doc.** The digest cards themselves never land on
  disk; what lands is the **ledger row** (`decisions.md`) and the phase doc. A decision that
  exists only in the digest is an omission — enter it as a proposed row (and its home section)
  first; M3/--check catch the reverse (a doc-cited id with no ledger row). (Doc-gate cards:
  the same rule with the doc as the carrier — enter it in the doc's matching section /
  「提议变更」, never a decisions.md.)
- **One chat message, never a file.** The digest exists to be read at the gate: target
  **≤~70 lines** (an L card; a typical M card lands ~50). Over the ceiling is a **routing
  signal, not a reason to land a file** — the overflow belongs in its home (ledger row ·
  doc §/ADR · grill notes) and the digest cites it; no home yet → write the home first, the
  same discipline as a card's why. Persisting the digest under `notes/` (a `freeze-ask.md`
  and the like) is forbidden: the ledger + receipts commit are already the audit surface, the
  digest is regenerable from the pending rows, and a digest on disk is a second source of
  truth that degrades back into the reading assignment this mechanism exists to kill. (This
  is the sanctioned exception to the global "long content → files" convention — which is
  exactly why it must stay small.)
- **Scale down, never pad.** An XS phase with two decisions sends two cards. The 3–5 / 2–3 counts
  are ceilings for a typical M card, not quotas.
- **Approving the digest approves the phase doc.** The doc stays the durable, authoritative
  artifact; the human may always drill in — each card names the section to jump to.
- **Execution-zone surfaces already exist — point, don't duplicate.** The test phase's human
  surface is the coverage matrix + its gap rows (`test.md`); the close-out's is the review
  报告's 修复决策表. Cite those, don't restate them as cards.

## Doc-gate cards (017 D2/S4 — the scaled digest, and status written directly)

The full digest skeleton **scales down; only §2 (ledger cards) and the approve-transcription
loop are exempt** — never the judgment surfaces:

- **§1 self-check stays** (the receipts presentation: grill convergence verdict · the
  single-agent panel receipt — in the persisted grill-log on a discussion-first run, else the
  round-closing message · M3/`--check` line — ≤5 lines).
- **§3/§4/§6 follow their own rules** (a small gate's rows are naturally empty or one line;
  an empty section is omitted, which is scaling, not exemption).
- **§5 待你判 stays** when there is anything to judge; **§7 go ask** names the doc path(s) +
  the receipts commit. **Mode is the 需求 gate's first judgment item** (ratifying the
  pre-filled `governance:` field).
- **On go**: write the doc's frontmatter `status` directly and append a
  `- <date> — <状态>（gate <receipts-commit short hash>）` line to the doc's「Change log」
  section (detail.md: its「Change notes (post-baseline)」section doubles as this container;
  the audit anchor — same semantics as a ledger `approved:` note), then commit.
  **No partial approve** (all-or-nothing per doc); repeated go is idempotent.
- Decisions/facts/proposals live in the doc itself (grill.md's doc-gate branches): decisions in
  the matching section, verified facts in a doc-local「事实清单」, pending proposals in a
  「提议变更」section + a `progress.md` pointer (resume-reachable; cleared on confirm).

## Approve transcription (on the human's go — ledger cards)

The go is the approval; Claude transcribes it into the ledger — never ahead of it:

1. The gate ask's receipts commit already carries the ledger state the human saw.
2. On go, for each approved row: header `proposed` → `approved` + append
   `- approved: <date> gate <receipts-commit short hash>`.
3. Commit immediately (the gate commit) — approve transcription sits adjacent to its
   receipts commit in git, auditable via `git log -S`.
4. **Partial approve is legal**: only the rows the human named flip; the rest stay proposed
   (the phase doc's status field flips only when its level is fully approved — the
   derived-status rule, SKILL.md「Ledger」).
