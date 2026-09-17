# xg-codemap

A **shared intent map** between a human and a coding agent. The agent draws, with evidence, what a piece
of software *is*; the human marks on the same map what it *should become*. It exists because code is
increasingly written by agents, and the mental map a programmer used to build by writing the code now has
to be handed over.

What makes it more than a diagram: every box in the Observed layer points at real code, commits or files
and says whether the claim was verified or inferred; every wish in the Intent layer carries an acceptance
predicate that says when it counts as done; and nothing in scope is left out by accident — omission is an
explicit, counted decision.

- `SKILL.md` — the drawing procedure (v0: hand-drawn Markdown plus Mermaid, no tooling).
- `references/standard.md` — the model, v0: seven frozen elements plus the subject; everything else is
  framework.

## Status

Version 0 is a value trial: one real set of scattered commits is mapped by hand and reviewed with the
map. If the map does not help a reviewer understand or locate faster than the diff, the standard stays a
record and nothing further is built. If it does, the next stages are a checker with per-language
resolvers, then an interactive surface (a terminal list or a rendered page), then human authoring of
intents on the map.

## Boundaries

This package knows nothing about workflow cards or knowledge bases, reads no shared configuration and
never writes into the repository it maps. The two sibling packages may call it; it never calls them.
