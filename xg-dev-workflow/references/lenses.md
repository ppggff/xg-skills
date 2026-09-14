# Lenses — fresh-context agent prompt shapes (the 视角 dimension)

An agent that does not hold your frame hits the blind spots you cannot; a designer grilling their own
proposal carries the blind spot through. Every lens below is dispatched as **one agent per lens** at M+
(a mixed mandate satisfices on its secondary lens; independent contexts decorrelate) — XS/S may fold
lenses into one agent. Model: SKILL.md「Subagents」. Companion: `smell-catalog.md` (the quality lens's
brief). Steps only say *when* to dispatch (`steps/discuss.md` §3 · `steps/review.md` step 4); the
prompt shapes live here and nowhere else.

## The frame every lens prompt shares

- **Pack** = {the problem · the claim or mechanism under test · verified facts (claim + `file:func`
  each) · dead findings (refuted claim + why)}. Load-bearing premises come **only** from the pack —
  anything else the dispatcher writes is marked `UNVERIFIED` or left out; "it appears in a doc"
  never launders a premise in. Agents treat packed facts as given (spot-check on contradiction).
- **Mandate**: attack from first principles — what here is unnecessary, what is missing, what
  already exists. Verify each finding against actual file content before reporting; structured
  findings (severity · `file:line` · issue · why · suggested fix); ≤400 words, keep the highest
  severity and state the count omitted on overflow; **return empty if none — never invent**.
- **Negative results** state query and scope ("not found with query Q over scope S"); a lens never
  restricts grep by extension; an inherited negative is re-checked before it becomes a fact.
- **Report** in Chinese, domain terms / file names / ids in English, diagrams Mermaid only.
- **Tiering**: a decision-level round (a new or changed mechanism, an enumeration table, a layering
  decision) gets the full lens; a rewrite implementing an already-grilled decision gets one `model: sonnet`
  consistency pass hunting old-semantics text and doc↔doc contradictions, fed the dispatcher's own
  **suspicion list** (what I touched that could contradict what — the agent cannot reconstruct it).

## Adjudicate before reporting (the orchestrator's half)

- Re-measure every numeric or enumerative claim (counts, "all N are X", corpus-wide absences) —
  panels sample; the direction is usually right, the number often isn't.
- Separate a finding's **facts** from its direction / attribution / generalization — those are
  your own inferences and need their own grounds. The **second** finding of the same shape is a
  candidate structural rule put through an ask, never the panel's generalization adopted as given.
- Record each finding's 裁定 (采纳 · 修正采纳 · 不采纳 · 待人判) and 去向 in `notes/lens-<date>.md`;
  a clean run states `no findings`. Refuted-with-why lines go to the pack's dead findings so the
  next dispatch does not re-find them; a later citation of a lens finding must be locatable.
- Several lenses or review axes in flight → collect them all before fixing anything.

## Pre-go lenses (lite.md「By size」M+; dispatch per discuss.md §3)

### Falsifier

Attack the load-bearing facts and the chosen approach's assumptions; verdict per attack **站不住 /
需补证 / 站得住** with evidence (`file:line`, or a command and its output). Three moves:
- **Causal coverage** — enumerate the minimal complete set of causal paths to the goal or failure;
  demand a bijection with what is built or logged: no-cause → unnecessary, no-coverage → gap.
- **Invariant-ledger replay** — load the KB ledger `[[wiki/<project>/<subsystem>-invariants]]`;
  test every open concern and proposed mechanism against each invariant ("does N make this moot
  or already handled?").
- **Search before build** — before a new cross-boundary mechanism (signal · flag · propagation
  path · structure), grep the codebase for an existing carrier.
Also attack caps and arithmetic, feasibility premises (settled by trying), what a check swallows silently.

### Commitment coverage

Traceability, not opinion. Matrices, each cell a Req id / 不做 item / 缺:
- **Rulings ↔ doc** — the human's messages **verbatim, complete, chronological** are in the pack
  (`notes/human-messages.md`); one answer transcribed as N approvals is the finding. Exemption: an
  enumerated 照案 table with per-row recommendations answered by a general reply naming the group
  approves exactly the listed rows — nothing outside them.
- **Upstream ↔ Req** — every content item of the direction note / roadmap 裁定 lines / predecessor
  card's deferred items / handed-over audit items → a Req or an explicit 不做; flag source conflicts.
- **Req ↔ Task ↔ V ↔ Inv** — orphans in any direction; numbering across design.md and plan.md.
- **Scope creep** — anything no source asked for (自主区 ok when SKILL.md「自主区」covers it).
- **Acceptance completeness** — every upstream acceptance condition has a V row; every inherited
  constraint an Inv; a redo card also covers the old card's commitments.
Verdict per criterion: `satisfied @<doc §>` / `not satisfied (<what's missing>)` /
`key-mismatch (<declared key> vs <delivered key>)`; the artifact's own "已核实 / done" is never
evidence — the author being the satisfier is the failure mode this lens exists to break.

## Review lenses (review.md step 4 picks the tier; briefs here)

- **Standard tier — three axes**, each a complete self-contained brief (paste pack + checklist):
  **Spec** (session model, opus cap) — does the change do what the commitments say: Req trace,
  missing / partial items, creep (every changed line traces to a Req or a recorded decision).
  **Standards** (`model: sonnet`) — conventions, comment / tests / docs hygiene, the
  `tools/check-code-refs.py` run, and `smell-catalog.md`「Reuse / cohesion」when the change adds
  helpers or abstractions; skip what tooling enforces. **Invariants** (session model) — the pack's
  Inv rows, concurrency, fail-safe symmetry, security.
- **Deep tier menu** (start lean: correctness · the trio · the sweep, plus what the diff plainly
  indicates; expand only on a singleton-heavy verdict): correctness vs invariants (opus cap) ·
  the **adversarial trio** = the falsifier's three moves run from the problem, not the diff (opus
  cap) · conventions conformance (sonnet) · tests — assertions match spec semantics, no hardcoded
  dates / paths (sonnet) · security / input validation / privilege (opus cap) · **lifted fail-safe
  symmetry** — a removed or relaxed rejection path: did the symmetric surface (build ↔ dump /
  reverse path) pick up the load, do type-wrapper boundaries (RelabelType, coercions) still fire? ·
  performance — hot paths, N+1 dispatch, lock scope · git history — blame, prior fixes (sonnet) ·
  **quality / simplify** — one bundled sonnet agent, deep only, `smell-catalog.md` pasted in
  (Speculative Generality · Duplicated Code · Middle Man · locality · single-adapter seams ·
  efficiency-hoist); it reads the diff for local cleanups and never double-reports the trio ·
  docs accuracy (sonnet).
- **Model-diversity sweep** (deep only, `model: sonnet`): fresh-eyes framing — pack + intentional-changes
  list + exemplars + "report only what you are confident is real; zero findings is a good outcome".
- **Test adequacy** (M+ close-out fixed member): target list = the Req blocks' 验证 lines; per
  block four questions — **落地了吗** (the artifact exists at the named home doing what the 陈述
  says) · **可证伪吗** (a test or negative sample can trigger its failure) · **与他行矛盾吗** (other
  Req / Inv rows, the KB ledger) · **测试覆盖了吗** (a test or check cites it). Rows touched since
  the last pass get all four, the rest are sampled.
- **False-positive exemplars** (paste verbatim): pre-existing issues · linter / compiler-catchable ·
  lines the change did not modify · intentional behavior changes tied to the broader change ·
  designed semantics documented in the KB or the design.

### Saturation verdict (deep tier, after adjudication)

Record how many independent paths (lens agents · the orchestrator's own deep read, each tagged
with its model) hit each confirmed finding. **Overlap-dominant** (most hit by ≥2) → near-saturated,
recommend stop. **Singleton-heavy** → under-sampled: one more pass along an axis not yet used — a
different slicing (subsystem vs concern), reading direction (diff-first · problem-first · spec-first
· history-first), polarity (verify claims vs hunt bugs), or model; re-running the same lens is voting,
not recall. **Dry stop**: a pass whose confirmed findings all fall below the action bar ends the
review regardless of overlap; a new High on a later pass is a genuine miss → retro. State it in one
line (`Review 饱和判定: 建议停 — 8/9 confirmed 被 ≥2 路径命中`); the human decides.

## Evidence-gathering agents (investigate · diagnose · falsifier support)

- **Negative-results checklist — put it in the prompt**: cover every file type (no `--include`;
  C++ `.cc/.cpp/.cxx/.hpp/.hh` beside `.c/.h`) · search where wiring lives — build configs
  (`Makefile` · `*.mk` · `configure.ac` · `CMakeLists.txt` · `meson.build`), catalog definitions
  (`pg_proc.dat` · `*.dat` · `*.bki`), registration sites (function-pointer assignments, hook
  installs, AM vtables) · grep the **symbol**, not the file pattern (a `.h` stub does not mean the
  definition is absent) · a hit or miss in module A says nothing about module B — name the owning
  module / layer · report as "not found with query Q over scope S".
- **Swappable-seam enumeration** — before any verdict resting on a function pointer, hook, callback
  or AM vtable: enumerate **every** assignment / registration site across code, build files and
  catalog data; recall is the deliverable, so the full session model, no cheaper backstop.
- **Birth-certificate negative** — an absence that justifies new plumbing reaches VERIFIED only by a
  hop-by-hop trace; the agent returns the trace, the orchestrator re-derives the leap to "infeasible".
- Facts and inference come back as separate lists; the orchestrator re-greps every load-bearing negative.

## Standing rules the orchestrator applies inline (no agent)

- **Verify the assumption** — every load-bearing "X is available / true at Y" gets a grep + read (or
  the KB) before the design leans on it.
- **Re-apply the signature** — keep the problem's signature and constraints first-class and re-apply
  them to every scope / granularity / completeness decision; the specific structure often makes the
  general-optimal answer unnecessary.
- **Class to constraint** — the second finding of one shape is an uninstantiated structural
  constraint: name the class, pin it as a rule or Inv row, let later rounds check the rule.
- **Grep for an existing carrier** before designing a cross-boundary mechanism; **test every open
  concern against the KB invariants ledger**, and land a newly confirmed invariant there in the same
  session (one evidence-cited line) — deferral is what forces the next round to re-verify from zero.

Honest limit: domain intuition is not automatable; these moves trigger the search that approximates it.
