# Step: evidence discipline (M1)

Forked from **source-driven-development**. Adjusted: generalized from "framework docs"
to **any** load-bearing claim — code behavior, API signatures, config, runtime facts —
cited from an authoritative source. The rule applies across all phases.

## The rule
No guessing. No 望文生义 (don't infer behavior from a name). Every non-trivial claim is
either cited or flagged unverified.

**Fork ≠ upstream.** In a patched fork (e.g. Cloudberry/Greenplum on PostgreSQL), never
assume vanilla upstream behavior — lock modes, defaults, call paths may be changed. Verify
the actual in-repo code path before stating how it behaves.

## Negative results ("X doesn't exist / isn't implemented")
An absence claim is only as good as the search behind it. Before asserting "not found",
"not implemented", "no coordination", etc.:
- **Cover all relevant file types.** This codebase has C++ — search `.cc/.cpp/.cxx/.hpp/.hh`,
  not just `.c/.h`. Prefer **no `--include` filter** (or an explicit multi-ext set); a stub
  declaration in a `.h` does **not** mean the definition is absent — grep the symbol itself.
- **Search where wiring lives, not just code.** A feature may be present only in **build
  configs** (`Makefile`/`*.mk`/`configure.ac`/`CMakeLists.txt`/`meson.build` — guards, file
  lists, defines), **catalog definitions** (`pg_proc.dat`/`*.dat`/`*.bki`/catalog headers), or
  **registration sites** (function-pointer assignments, hook installs, `RegisterXact*`/AM-vtable
  setup). Grep these before concluding a feature is missing.
- **Search the symbol, not the file pattern.** A function declared in `*.h` is often defined
  in a sibling `.cc`. Grep `FuncName` across the whole tree before concluding it's a stub.
- **Distinguish same keyword across modules/layers.** The same name can exist in several
  modules (catalog-service vs QD; storage_am vs core). A hit in module A — or its absence
  there — says nothing about module B. Confirm **which module/layer owns** the behavior before
  any "missing"/"present" verdict; don't conflate look-alikes.
- Phrase a true negative as **"not found with query Q over scope S"**, not "absent."
- **Birth-certificate rule (a negative that justifies NEW code).** When an absence/existence
  claim is the *reason to build new plumbing* — a field / pipe / protocol layer to "carry X to
  Y", or a guard premised on "X is always N / X is dropped / X isn't reachable at Y" — it must
  reach **VERIFIED** by a hop-by-hop trace before it earns that code; a query-scoped negative
  isn't enough here. "The value isn't there" is the most expensive false claim: it births a whole
  layer where a few-line assert would do, and unlike an `(assumption)` it slips past review once
  "grounded". Can't verify → mark `(assumption)` and design as if X *might* already reach Y.

## Feasibility claims ("can't be done / infeasible") — design-time
Distinct from a fact about behavior: a feasibility verdict is a judgment about **mutable**
code, and during design the code is exactly what we'd change. Correctly-cited code is **not**
proof of infeasibility. Before writing "infeasible / 不可行 / can't":
- **Is the cited code even live in the target build?** Check `#ifdef` gating (`SERVERLESS`,
  `USE_INTERNAL_FTS`, …) and which branch this build compiles. An `Assert`/limit in a dead
  branch proves nothing.
- **Is it the relevant execution context?** A gate added via a hook runs where the *hook*
  runs (e.g. launcher main `AutoVacLauncherMain()`, with catalog/RPC), not in some unrelated
  dispatch-time helper. Cite the function that runs *at the seam you'll touch*.
- **Is it a swappable seam?** Function pointers (`cdbcomponent_getComponentInfo` is a
  `typedef`'d pointer), hook variables, registered callbacks, AM vtables — these are *meant*
  to vary; a current assignment is not a constraint. **Before any verdict resting on a seam,
  dispatch an agent to enumerate _every_ assignment/registration site** of that pointer/hook
  across `.c/.cc`, `.h`, build files, and catalog `.dat`/`.bki` — one current assignment is not
  the whole picture, and a seam re-pointed elsewhere flips the verdict.
- **Don't conflate look-alikes** — verify the entity is the one you think (e.g. catalog-service
  "coordinator" ≠ QD coordinator). Confirm identity before reasoning over it.
- **Verify the subagent's *inference*, not just its facts.** Re-checking that a cited line
  exists is not the same as re-checking the leap from it to "infeasible." Re-derive the
  conclusion yourself.
- Phrase the honest result as **"no ready-made interface today (would need X)"**, reserve
  **"infeasible"** for a genuine fundamental barrier you can name.

## Where evidence comes from (by authority)
1. **The code itself** — `func()` in `file.c` (read it; no line numbers in prose).
2. **Project knowledge** — xg-knowledge-lite `[[wiki/<project>/<slug>]]`.
3. **Official docs / changelog** for a framework/library at the **detected version**
   (read the dependency file first); deep-link with anchors.
4. ❌ Not authoritative: Stack Overflow, blogs, AI summaries, your own training data.

## When you're unsure
Dispatch an **Explore** (or general-purpose) subagent to investigate and return the
evidence — then record the finding (in the relevant doc, and in the KB if reusable).
Surface conflicts (docs vs code, source vs source) to the human; don't silently pick.

**Model (cost):** follows SKILL.md「Subagent model assignment」(gather → cheaper `model: sonnet`;
inference/adjudication → session model, safe because the orchestrator re-derives). Evidence-specific
carve-out: keep the **session model** where recall itself is the deliverable with no cheap backstop —
the swappable-seam every-registration-site enumeration, and the hop-by-hop trace behind a
birth-certificate-grade negative.

When you dispatch, put the Negative-results rule **in the subagent's prompt**: tell it not
to restrict grep by file extension and to report negatives as query-scoped. A subagent's
narrow search (e.g. `.c/.h` only) is the single most common source of a false "not
implemented" conclusion — don't inherit it unverified. For any load-bearing negative the
subagent returns, re-check it yourself with a broader grep before stating it as fact.

## Confidence labeling — claims table before any conclusion
Before stating **any** feasibility or runtime/concurrency conclusion, lay out the load-bearing
claims as a table and label each:

| Claim | Evidence (`file:line`) | Confidence |
|---|---|---|
| … | `appserver.c:142` (or `—` if none) | VERIFIED / INFERRED / GUESS |

- **VERIFIED** — read the exact code/test that proves it. **INFERRED** — deduced from
  surrounding evidence but not directly read. **GUESS** — name/intuition, no evidence.
- **Never assert feasibility or runtime behavior on a claim marked INFERRED or GUESS** —
  investigate it up to VERIFIED first, or carry the conclusion as `UNVERIFIED:`.
- This audit table is the **one place** `file:line` is allowed (precision for the reader to
  re-check); prose elsewhere still cites `func()` in `file.c` without line numbers.

**Beyond investigation conclusions — provenance in every phase doc.** The same discipline applies
to **load-bearing claims** in any doc (requirement 需求条目, design Understanding/影响面, detail
rationale): mark each as evidence-cited / **推断 (inferred)** / **假设 (assumption)**. The full
claims table is reserved for feasibility/runtime verdicts; elsewhere the **inline marker** suffices
— a citation, or a trailing `(推断)` / `(assumption)`. Scope it to load-bearing claims; don't tax
every sentence. An unmarked non-trivial assertion reads as evidence-backed — if it isn't, it's a
`(assumption)` waiting to mislead.

## Honesty
If something can't be verified, write `UNVERIFIED: …` explicitly rather than hedging.
A flagged gap is more useful than false confidence.

## Citation form in docs
- code: `` `TpFrozenShmemGetMin()` in `appserver.c` ``
- knowledge: `[[wiki/cbdb/appserver-epoch-shmem]]`
- external: full URL with anchor + a one-line quote for non-obvious decisions.
