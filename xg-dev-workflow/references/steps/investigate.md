# Step: investigate — the front door for any code-behavior question

"调查 X", "how does Y behave", a concurrency / runtime / feasibility question, an open question on a
card: it all routes here. Read-only on product code, never advances a card; the deliverable is a
recorded evidence trail plus a **logical analysis** — grep and read gather evidence, they are not the
answer. Two disciplines compose: the evidence rule below and concept-first understanding.

## The evidence rule (non-negotiable)

No guessing, no 望文生义 (inferring behavior from a name). Every non-trivial claim is cited from the
code / tests / KB or written `UNVERIFIED: …` — a flagged gap beats false confidence. In a patched fork
(Cloudberry / Greenplum on PostgreSQL) never assume vanilla upstream behavior: lock modes, defaults and
call paths may differ — read the in-repo path. Minimum bar:
- runtime values / concurrency → read the code path that actually runs, not the name;
- function-pointer / hook / vtable targets → a current assignment is a **swappable seam**, not a constraint;
- `#ifdef` / build gating → confirm the cited code is live in the target build;
- external tool or runtime behavior ("this flag can't be dropped", "the host lacks X") → **run it once**,
  never reason from docs or habit; a deduced answer is 推断, never VERIFIED.

**Authority order**: (1) the code itself — `func()` in `file.c`; (2) the KB, `[[wiki/<project>/<slug>]]`
(rank 2 does not exempt a KB negative from the negative-results rule); (3) official docs / changelog at the
**detected** dependency version, deep-linked; (4) never Stack Overflow, blogs, AI summaries, training data.

## Analysis, not grep

- **Layers**: concept → module → file → function; start at the concept, descend only as far as the
  question needs, name the layer you are at.
- **Trace the path that runs** (control + data flow) end to end; **build the causal chain** — never
  "it deadlocks / is safe / can't happen because X" without tracing X to the effect.
- **Synthesis lens** for a cross-cutting verdict: stack the layers data flows through (property + one-line
  judgment each) · find the seams where one layer delegates to another (hooks, AM callbacks, RPC) ·
  ask **where responsibility actually lives** — often not the layer the question names. It surfaces
  responsibility inversion ("missing coordination here" = centralized elsewhere), the keystone /
  chokepoint (verify it first), cost / risk propagation across layers, and **collapses the question to a
  few decisive checks** — name them and stop chasing the rest.
- **Claims table before any feasibility / runtime / concurrency verdict** — `Claim | Evidence (file:line) |
  VERIFIED / INFERRED / GUESS`; never assert on an INFERRED or GUESS row (investigate it up or carry the
  conclusion as `UNVERIFIED:`); an INFERRED row is a reasoning step that itself needs re-deriving. The
  table is the one place `file:line` is allowed; prose cites `func()` in `file.c`.
- Load-bearing claims in any doc carry evidence / 推断 / 假设 inline (`constraints.md` Doc-2); only the
  claims a decision rests on — don't tax every sentence.

### Assertions that read like narration (mark or verify them on the spot)

- 「这个机制能抓住 X」— a usage scenario you wrote for a mechanism is a runtime claim: walk it in code.
- 「这个序列有序 / 已去重 / 稳定」— order, uniqueness, idempotence come only from the producing code.
- 「这条 alt 做不到，所以否决」— a rejection reason is as load-bearing as the choice and less checked:
  nothing downstream ever touches a rejected alternative, so an error stays wrong.
- 「这几个方案各有代价」— then verify the premise they **share** first; the usual collapse is "reuse X
  for Y" where X exists but its path is not wired: is the call site commented out, does the `switch`
  `default` panic, which manager / keyspace does it serve.
- Negative trigger phrases — evidence now or rewrite as an open question: 「只有一个调用方 / 放宽它无连带」
  (enumerate the callers) · 「这是 X 的私有路径 / 走不到那里」(ownership by registration site, not by
  name or file) · 「已覆盖 / 这条错误说明它到过 Y」(point at the throwing line and its gate) · 「这条分支也会
  命中」(reachable after the earlier gates?) · 「不能复用 / 不可行」(the feasibility guard below).

### Negative results and feasibility

- A written negative states **"not found with query Q over scope S"**, never a bare absence; grep the
  symbol across every file type, wiring (build configs, catalog `.dat`/`.bki`, registration sites) and
  module before "missing" (the checklist for an agent: `lenses.md`「Evidence-gathering agents」).
- **Birth-certificate rule**: an absence that justifies new plumbing (a field / pipe / layer to carry X to
  Y, a guard premised on "X never reaches Y") reaches VERIFIED only by a hop-by-hop trace; can't →
  `(assumption)` and design as if X might already reach Y.
- **Consuming a KB negative or qualified conclusion**: land it first as a `Fact-n` (the verbatim sentence
  + its recorded scope) and cite that; read it in exactly its state — 语义边界 (a path / use limit) ·
  存在性否定 (doesn't exist / unreachable) · 规范处置 (a should / shouldn't) — never across states.
- **"Infeasible" is a judgment about mutable code**: before writing it — is the cited code live in the
  target build? is it the execution context you will touch (a hook runs where the hook runs)? is it a
  swappable seam (then enumerate **every** assignment / registration site before any verdict)? is the
  entity the one you think (catalog-service "coordinator" ≠ QD)? re-derive a subagent's leap yourself,
  not just its cited lines. Say "no ready-made interface today (would need X)"; reserve "infeasible"
  for a barrier you can name.

## Spike — a throwaway probe when reading cannot settle it

An empirical question (is this qual pushed down in a dispatched plan? what does the hook receive?)
gets a probe instead of a parked row: throwaway from day one, **outside the product tree**, one command,
prints the observed state; the run output upgrades the claims row to VERIFIED, lands via the normal
routing, and the probe is deleted. A probe that needs product-code changes is implementation — escalate.
A **defect** (observed-wrong behavior) is not a spike question — `diagnose.md`.

## Procedure

1. **KB first** — an xg-knowledge-lite Orient pass (project section of `wiki/index.md` · `CONTEXT-MAP.md`
   · uncompiled-raw count), then Query the relevant concepts and drill into their raw sources; don't
   re-investigate what is recorded. Orient is this run's warm-up, not a separate log record.
2. **Investigate read-only** — an Explore subagent for targeted grep / read, a broader layered survey for
   a sprawling question. A dispatched agent gets the negative-results checklist **in its prompt**
   (`lenses.md`); re-check every load-bearing negative it returns with a broader grep and re-derive any
   "infeasible". Model: gather → `model: sonnet`; inference → the session model (opus cap) — except
   where recall itself is the deliverable and nothing backstops it (seam enumeration, a birth-certificate
   trace): the full session model. Surface source conflicts (docs vs code) to the human; never pick silently.
3. **Record — branches on anchoring.** A card is **active only by explicit linkage** (the human named it
   in this ask, or the session entered via `resume`); relevance or recency never anchors — default
   standalone, and if torn ask one question **at recording time**, never before (the investigation itself
   is identical). Stricter than `review`'s anchoring on purpose: a review target objectively *is* some
   card's implementation; an investigation topic is merely *about* something a card also touches.
   - **Active card** → this is the card's own investigation: verdict + evidence into `design.md`
     「待解问题与证据」(facts into `facts.md` as `Fact-n`), reusable module truth to the KB via
     `[[wiki/<project>/<slug>]]` — design.md links it, never duplicates it. No separate usage record
     (the card's lite events cover it); 存量 cards record per `references/legacy/SKILL.md`.
   - **Standalone** → reusable findings to the KB (xg-knowledge-lite Write: raw, compile if it shifts a
     concept); scratch and phase notes to `<dev_root>/<project>/investigations/<topic>.md` (no prefix —
     the dir says it; a multi-phase campaign graduates to `investigations/<topic>/` with charter + phase
     notes), **never into the repo**. Log `--action investigate`.
4. **Large question → phases.** Name the phases up front (e.g. 1 registration sites · 2 execution context
   · 3 lock path); after each, append its claims table + verdict-so-far + open items to the notes file
   and **pause for the human** before the next; don't pre-conclude across the pause. A single question
   skips the phasing.
5. **Receipts — write first, then reply**: the closing reply (or a phase pause) names the notes / KB paths
   and the dev_root / KB commit; an answer with no named artifact means the recording step was skipped.

A finding in a notes file is a **field block** — stable labels 现象 · 规范 (or 机理) · 改法 (or 结论), each a label
line with free-form indented content; a further field only for an independent point (`conventions-core.md`「Form」).
Citation forms in docs: code `` `TpFrozenShmemGetMin()` in `appserver.c` `` · knowledge
`[[wiki/cbdb/appserver-epoch-shmem]]` · external: full URL with anchor + a one-line quote for a non-obvious
decision. A verified load-bearing fact persists as `Fact-n` (card) or in the note's 事实清单.
