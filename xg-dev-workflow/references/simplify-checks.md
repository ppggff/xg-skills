# Simplify checks (reuse / cohesion)

The single source for the reuse/cohesion checks a change that adds helpers/abstractions must
pass. Shared by `implement.md`'s simplify sweep and `review.md`'s Standards axis — when a review
axis agent needs them, paste this file into its brief (it assumes no shared memory).

- **New helper/constant → grep the touched module for the same logic first.** A new `arch→prefix`
  helper beside an existing one that already computes it is a *merge*, not a new method.
- **New cross-cutting concern → match the shape of its just-built sibling.** If this change made
  concern X a backend/interface hook, concern Y of the same shape is a hook too — not an
  `if type == :foo` special-case in the caller.
- **New wrapper/layer → deletion test + locality.** Mentally delete the new layer: complexity
  that merely moves (pass-through) is a Middle Man — collapse it. When a change extracts pure
  functions for testability, ask where the real bugs will live — the extracted function or the
  untested orchestration calling it; tested helpers around untested orchestration is a locality
  smell.

An embedded shared sub-expression evades a whole-function dup scan — name both checks explicitly;
a generic "look for duplication" doesn't cover them.
