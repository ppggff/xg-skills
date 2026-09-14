# Step: code understanding (M5)

Composed from **xg-knowledge-lite** (query) + **Plan Mode / Explore subagent** (read-only
investigation). Concept-first and layered: understand *existing* code before designing, and
review your *own* code after writing it — two different activities.

## Layers
concept → module → file → function. Always start at the concept, then descend only as far
as the task needs. Name the layer you're at.

## Synthesis lens: layer × module × hook × relationship
When the task is a **cross-cutting result** (a concurrency/safety/perf verdict, a "where does
behavior X actually live" question, a sprawling investigation with many findings), don't stop
at a list of findings — re-read them through this lens. It routinely turns scattered facts
into one structural judgment.

1. **Layers** — stack the components data/control flows through (e.g. scheduler → command →
   hook/plugin → access layer → backing service). For each, state its *property* and a
   one-line *judgment*.
2. **Hooks/seams** — find where one layer delegates to another (registered hooks, AM
   callbacks, RPC boundaries). Behavior — and responsibility — often *moves* at these seams.
3. **Module relationships** — who calls whom, who serializes/guards what. Ask explicitly:
   **where does responsibility actually live?** It is frequently *not* the layer the question
   names (e.g. "launchers don't coordinate" → safety was delegated downward to a lock layer).

Conclusions this lens reliably surfaces:
- **Responsibility inversion / delegation** — a concern absent at the obvious layer because
  it was pushed up or down; "missing coordination here" may be "centralized elsewhere."
- **Keystone / chokepoint** — the single point everything funnels through; its correctness
  is the whole system's correctness (verify it first).
- **Cost/risk propagation** — how redundancy, contention, or failure amplifies across layers
  (e.g. N replicated schedulers all funnel to one service → that service is the bottleneck).
- **Collapse to decisive checks** — the lens usually compresses a broad question into a small
  set of must-verify items; name them and stop chasing the rest.

## Understanding existing code
1. **Query the KB first** — start with an `xg-knowledge-lite` **Orient** pass (project-scoped
   warm-up: `wiki/index.md` section + `CONTEXT-MAP.md` + uncompiled-raw count) to see what's
   already knowable, then Query the relevant concept → drill into its Sources raw. Prefer KB
   facts over training-data guesses.
2. **If the KB is thin**, investigate in **Plan Mode** (read-only, no edits until approved):
   use an Explore subagent for targeted grep/read, or enter Plan Mode directly for a
   broader layered survey. grep the raw KB sources as a quick fallback.
3. **Capture what you learned** back to the KB (xg-knowledge-lite Write) so the next
   requirement starts ahead. Reference it from `design.md` via `[[wiki/<project>/<slug>]]` — don't
   duplicate module knowledge into the requirement dir.

## Reviewing your own (new) code
- Route it through the **`review` verb** (`review.md`): KB/requirement context pack, lens
  fan-out, adjudicated findings — distinct from comprehension of existing code. Findings
  feed `progress.md` / discovered issues, not the KB (unless they reveal reusable module
  truth).

## Investigating while a requirement is active
Any investigation — resolving an Open question, probing feasibility, "调查 X" — routes through the
**`investigate` verb** (`investigate.md`), the single front door for code investigation. It owns the
mechanics: anchoring to the requirement, recording (scratch in `notes/` → verdict + evidence in
`progress.md` *Design iterations*), KB routing, the `--action` log, and Stop-at-gate. When a
requirement is active it *is* this M5/design step; don't run a parallel loop here.

## Evidence (M1)
Every claim about how code behaves follows the **canonical M1 discipline in `evidence.md`** —
citations (`func()` in `file.c`, no line numbers) or a KB link, the Feasibility-claims guard for any
"infeasible" verdict, never 望文生义 from a name. Apply it here; don't restate it.
