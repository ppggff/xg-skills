# Model tiering (cost)

The full rationale behind SKILL.md「Subagent model assignment」— read when assigning a model to
a subagent dispatch or suggesting a session-model switch.

## Subagent assignment (the rule, with rationale)

Checklist / gather / verification subagent work defaults to the cheaper model (Agent tool
`model: sonnet`); inference-heavy analysis stays on the session model, **capped at opus** —
subagents never run fable: a fable session dispatches its inference-heavy agents (panel lenses,
review axes) at `model: opus` and keeps fable for the orchestrator itself (adjudication,
synthesis). Safe for the same reason as the sonnet default — a lens mandate is a scoped attack
and the orchestrator re-derives / adjudicates (M1; review step 5) — at half the per-token cost.
**Deterministic checks are scripted, not delegated**; every downgrade sits under M6 calibration
(findings that repeatedly die in adjudication revoke it). Per-lens application: `steps/review.md`
step 4 and `steps/review-deep.md`.

## Session-model tiering follows the two zones

Decision-zone gates deserve the strong session model; the execution zone runs well on a cheaper
one — the plan gate digest reminds the human of the optional `/model sonnet` + `/advisor opus`
switch after go (a fresh session via `resume` makes it free). The cheap-model 评审 adjudication
tradeoff sits under M6 calibration like every downgrade.
