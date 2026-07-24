# Smell catalog (Fowler code smells — the no-standard baseline)

A named vocabulary of code smells for the review quality lens. The names are **leading words**:
each recruits the model's pretrained sense of the smell and its refactoring, so a review agent
hooks into that knowledge instead of re-deriving from a custom description. Usable even when the
repo documents **no** coding standard of its own.

## Binding rules

- **Documented repo standard wins.** Where the repo documents a convention, it overrides this
  baseline; the catalog is the fallback for what the repo leaves unspecified.
- **Skip what tooling enforces.** Don't hand-flag anything a linter / formatter / compiler already
  catches — review time is for what tools can't see.

## The smells (name — what it IS → the fix)

- **Mysterious Name** — a name that doesn't say what the thing is or does → rename to intent.
- **Duplicated Code** — the same structure in more than one place → extract, call one copy.
- **Feature Envy** — a function using another module's data more than its own → move it to the data.
- **Data Clumps** — the same group of fields/args travelling together → bundle into one object.
- **Primitive Obsession** — a primitive standing in for a concept (a string for money/phone/path)
  → introduce the type.
- **Repeated Switches** — the same switch/if-chain on a type in many places → polymorphism or a
  dispatch table.
- **Shotgun Surgery** — one logical change forces edits across many modules → gather what changes
  together into one place.
- **Divergent Change** — one module edited for many unrelated reasons → split it by reason.
- **Speculative Generality** — abstraction / params / hooks added for a future that never came →
  delete until a second caller needs it. (Our **dead code / unused generality** family.)
- **Message Chains** — `a.b().c().d()` reaching through layers → ask the first object for the end
  result; hide the navigation.
- **Middle Man** — a class/layer that only delegates → inline it. (Our **altitude / pass-through**
  family; the deletion test in `codebase-design` is the check.)
- **Refused Bequest** — a subclass/impl that ignores most of what it inherits → prefer composition
  or re-shape the base.

## Not a smell — kept separate

**efficiency-hoist** (side-effect-free/expensive work above the guard that skips it; per-row work
that belongs in one-time setup) is a *performance* observation, not a Fowler maintainability smell
— the review quality lens carries it alongside this catalog, not inside it.
