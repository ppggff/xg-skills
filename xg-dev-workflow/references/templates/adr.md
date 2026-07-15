# ADR-NNNN: <short title of the decision>

Status: proposed | accepted | superseded by ADR-NNNN | deprecated
Date: YYYY-MM-DD

<!--
Reader = human (decision zone): the approver now, the future maintainer later — prose
rationale over terseness; Claude reads it back as the recorded contract.

An ADR can be a single paragraph: what's the context, what we decided, and why.
The value is recording THAT a decision was made and WHY. Only add the optional
sections below when they earn their place. Record an ADR only when the decision is
hard-to-reverse AND surprising-without-context AND the result of a real trade-off.

Hygiene: an ADR ≡ the CURRENT active decision, not a changelog. Keep the body lean
(≤ ~200 lines). Never add a `## Amendment` block — to change the decision, write a NEW
ADR with `## Supersedes ADR-NNNN` and leave only a ≤2-line forward pointer on this one.
-->

## Context

The requirement/constraint that forces a decision.

## Decision

What we decided.

## Alternatives considered (optional)

- **<option>** — why rejected.

## Supersedes (optional)

`ADR-NNNN` — one line on what this changes. The superseded ADR's Status line gets only a
≤2-line forward pointer — never an `## Amendment` block there.

## Consequences (optional)

Non-obvious downstream effects. (Superseding a frozen design? link the requirement change.)
