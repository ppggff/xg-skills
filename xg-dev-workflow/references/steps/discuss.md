# Step: discuss — the pre-go conversation on a lite card (with the human, with yourself, with fresh agents)

Companion to `lite.md`「Drafting」/「The go ask」/「By size」. Four parts: how to ask the human, how to state your
understanding, how to dispatch a fresh-context lens, and which design topics to walk. Distilled from the
frozen legacy step files (the 存量 flow keeps them).

## 1. One question at a time, to convergence

- **One question, one decision.** Walk the decision tree in dependency order — settle a prerequisite before the
  choices hanging off it. Each question carries its **recommended answer + the trade-off**, then wait. Three
  cases may share a round: a panorama topic laid out whole; 2–3 mutually independent items each answerable in
  a word; a 照案 table of independently accept-or-reject rows — every item still has its own recommendation,
  and the human sets the pace.
- **A recommendation is not a decision.** Until the human answers, nothing lands in the doc as decided. The
  only legal stops are the per-question ask, the round-end ask and the go ask; "written per my recommendation,
  please confirm" is forbidden. One answer lands on the one item it answered — a bundled reply is never
  transcribed as N approvals.
- **Self-proposals pass the same pre-check as external ones**: load-bearing premises verified before they are
  stated (a comparative claim about existing code means you read it; a feasibility premise is settled by
  trying, not reasoning) · magnitude × access medium · cost symmetry (what it adds vs removes) · does the
  system already ship a carrier for it.
- **Questions are self-contained**: an id's first use carries a one-clause gloss; phrase the judgment in
  operation/behavior language, never an internal shorthand.
- **A round is one decision cluster**; force-close after ~6–8 human touchpoints. **Every round ends with a
  one-line convergence verdict in the closing message** — judged by materiality (would another round change
  the decision?), not by "questions remain": a dry round (no decision-level change) → 建议收敛; an open point
  that is hard-to-reverse × surprising × a real trade-off → 继续, naming it. Report this round's facts only,
  never a forecast; the human decides. A later finding re-opens settled ground only if it would change a
  decision — otherwise it goes to 待解问题 / roadmap.
- **Rollback** re-opens an earlier answer by marking the answers that depended on it superseded (history is
  kept, not deleted) and re-walking from there; the doc holds the current state, git and the 变更 lines hold
  the path. Receipts before any ask: lite.md「The go ask」.

## 2. The understanding statement (before candidates)

- Understand before designing: **evidence → mechanism → implication**, concept → layer — not a fact list.
  Query the KB first (Orient: the project's `architecture` overview + `*-invariants` ledgers), then read-only
  code exploration; link `[[wiki/<project>/architecture]]` instead of re-describing the system; reusable
  findings go back to the KB.
- Present it **for judgment**: the understanding, the uncertainties, the information gaps. The human corrects
  it before any candidate is weighed. A prior note or card that already reached design depth is consumed, not
  re-derived; a `learn` report is non-binding input — claims to test, not settled ground.

## 3. Fresh-context lenses

- **Why fresh**: an agent that does not hold your frame hits the blind spots you cannot. Give it only {the
  problem + the claim or mechanism under test + a pack of verified facts}; mandate = attack from first
  principles: what here is unnecessary, what is missing, what already exists. Load-bearing premises come only
  from the pack (else marked `UNVERIFIED`); a negative result states its query and scope.
- **One lens, one agent** at M+ (a mixed mandate satisfices on its secondary lens; independent contexts
  decorrelate); XS/S may fold lenses into one agent. Model: SKILL.md「Subagents」. Report in Chinese with
  domain terms and ids in English, Mermaid only.
- **The two lite lenses** (dispatch once the approach forms, and again at any round that produces an
  expensive-to-redo artifact — an enumeration table, a layering decision): **falsifier** — attack the
  load-bearing facts and the chosen approach's assumptions; verdict per attack 站不住 / 需补证 / 站得住 with
  evidence; **commitment coverage** — the human's rulings ↔ the doc, upstream decisions and deferred items ↔
  a Req or an explicit 不做, Req ↔ Task ↔ V, scope creep, the roadmap's 裁定 lines, and on a redo the old
  card's commitments. Review's four lenses: `review.md`.
- **Adjudicate before reporting**: re-measure every numeric or enumerative claim; separate a finding's facts
  from its direction / attribution / generalization (those are your own inferences and need their own grounds);
  record each finding's 裁定 (采纳 · 修正采纳 · 不采纳 · 待人判) and 去向 in `notes/lens-<date>.md`.
- Two standing rules need no agent: before designing a new cross-boundary mechanism, grep for an existing
  carrier; test every open concern against the KB's `*-invariants` ledger for the subsystem.

## 4. Design topics to walk (M cards; lighter by size)

| Topic | attr | lite home in design.md |
|---|---|---|
| Module & layer split | panorama | 当前方案 (understanding statement · candidates · chosen path) |
| Happy path / data-flow walk | panorama | 当前方案 diagrams |
| Part decomposition (L) | panorama | 当前方案 seam contract; `split-isolate.md` A↔B |
| State & lifecycle | panorama | 契约与不变量 |
| Concurrency / ordering | detail | 契约与不变量 |
| Data model & storage footprint | panorama | 当前方案 impact forecast |
| Failure & recovery paths | panorama | 契约与不变量 · 测试与验证 |
| Compat & migration | detail | 当前方案 impact forecast · 目标与边界 不做 |
| Ops / observability | detail | 测试与验证 |
| Performance & scale | detail | 测试与验证 (判据) · 待解问题与证据 |
| Split review (card vs part) | detail | 目标与边界; `split-isolate.md` |
| Commitments closed? | detail | the go ask's 收敛行 |
