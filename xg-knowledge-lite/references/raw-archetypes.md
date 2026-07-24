# Raw-note archetypes (optional)

Optional structural archetypes for a **raw** article (`$KB/raw/<project>/<slug>.md`), referenced from `FORMAT.md` §2. These are writing scaffolds, **not mandatory**: a raw note follows FORMAT.md §1's frontmatter/structure and §3's conventions regardless of which (if any) archetype it uses.

Pick an archetype by knowledge type — the structure is there to help you think and to make synthesis into concepts easier.

## A. Module overview

For: how a module works, its components, the big picture.

```markdown
# {Module}

One-sentence positioning (what this is).

## Problem it solves
Why it exists, the core need it addresses.

## Key concepts
Term-style or short-sentence definitions; bold a term on first mention.

## Components / data structures
Constituent parts, key types.

## Main flow (high level)
The normal path, no deep detail (leave detail to a Flow article).

## Boundaries & limits
What's out of scope, known constraints.

## Relationship to related modules
Cross-module collaboration, comparison with similar modules.
```

## B. Flow / trace

For: the full execution path of one operation, call-chain analysis.

```markdown
# Execution path of {Operation}

## One-line summary
The key observation — the single most informative sentence.

## Trigger
What SQL / API / event starts this path.

## Call chain
In order: each step's `func()` + `file` + what that step does.

## Key data structures
Structs / state objects passed along the path.

## Differences from related flows
A table: this flow vs similar flows.

## Known pitfalls / edge cases
Traps hit, behavior under special conditions.
```

## C. Pattern catalog

For: a set of same-shaped patterns, failure modes, or variants.

```markdown
# Common {patterns / failure modes} in {area}

## Prerequisites
Background shared by all the patterns.

## Pattern 1: {name}
**Symptom**: what's observed
**Root cause**: the underlying reason
**Fix**: how to resolve it

## Pattern 2: ...
(same shape — keeps scanning and synthesis regular)

## Diagnosis flow
How to classify a problem into one of the patterns.

## Anti-patterns
Things that look like a pattern here but shouldn't be applied.
```

Same shape per pattern is the point of this archetype — it makes scanning and retrieval regular.

## D. Invariant / constraint

For: a single invariant, constraint, or contract. Short; often a subsection of a Module overview, standalone only when referenced by several articles.

```markdown
## {Invariant name}

**Statement**: the invariant, stated precisely.

**Why**: why it must hold.

**Violation consequence**: what breaks if it's violated.

**Enforcement**: where in the code it's checked / guaranteed.

**Known bypasses**: paths that legitimately bypass it, and why they don't break it.
```
