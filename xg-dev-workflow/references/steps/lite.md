# Step: lite — one draft, one go, continuous execution

The path for cards whose `design.md` frontmatter says `governance: lite` — followed **exclusively**;
SKILL.md「Files on the lite path」names what else is shared or never loaded.

## Model

One continuously updated working draft; explicitly confirmed goals and boundaries (**commitments**); one
execution authorization (**go**); verification evidence matching the current change. Requirement / design /
detail are angles of thought, not gated phases: understand ⇄ investigate ⇄ compare ⇄ negotiate runs before go
and continues after it inside the authorization — only three kinds of change come back to the human (「Executing」).
- **Commitment** = a goal, constraint or acceptance condition the human asked for or confirmed and still in
  force, plus the project's standing constraints; a confirmed Claude proposal is one and Claude cannot
  withdraw it alone. Not copied into the doc ≠ authorization to drop it — backfill and say so.
- **Impact forecast ≠ authorization boundary**: expected modules / files / tests move with investigation —
  no pause when they grow, but the size is re-judged (「By size」); hard boundaries exist only when the human
  set them, and are marked as the human's.

## Card files

Start from `design.md`; create the others when their content appears, never as empty containers:
`progress.md` (park / handoff) · `facts.md` (many load-bearing facts) · `adr/` (a trade-off worth its reason
— when, and the supersede form: `constraints.md` Adr-1/2; skeleton `templates/adr.md`) · `plan.md` (tasks crowd
the doc) · `log.md` (history outgrows the doc) · `notes/` (long output, spikes, lens and review notes;
`human-messages.md` — the human's messages verbatim, one line each, as they arrive). Full content has one
home; a summary is self-contained; prose states the present — history is git plus the 变更 lines.

## Open a card (SKILL.md's `new` verb — by hand, no script)

1. Next `NNN`: scan `<dev_root>/<project>/`, increment. 2. `mkdir NNN-slug/`; copy `templates/design-lite.md` to
`design.md`, fill id / title / project / created. 3. Board row in `index.md` (a new project first gets its dir +
`templates/index.md`): `| NNN | lite | todo | — | [NNN-slug](./NNN-slug/) |` — 整体状态 ∈ `todo` (drafting) ·
`active` (go → close-out) · `done` / `dropped`, nothing else.
Ids and citation form: `constraints.md`「Ids」; `[x]` = 已验证 and nothing else. **Diagrams**: two or more
interacting components, or a decision branch → at least one Mermaid diagram; more is your call.

## Drafting (before go)

Explore, investigate (`investigate.md`, evidence-cited), compare, negotiate — freely; the doc is a draft.
Shape or environment clauses in the ask (「是个 Linux 服务器」) are constraint commitments — quote them into
a Req block, never leave them as background. A redo card imports the old card's `notes/human-messages*.md`
and the roadmap's 裁定 lines even when its other docs stay unread. Spikes stay within standing permissions,
local and reversible. Enhancing an existing tool or script starts by running it **unchanged in its target
environment** (the host or container it actually runs in, not the dev box) — that baseline (command · output
· version) is the first fact in the doc, and the design and later verification are measured against it.
**Candidates first (方案优先)**: before drafting the approach, put ≥2 candidates side by side — one-line 思路
· position on the hack ↔ 补丁 ↔ 推翻重来 spectrum · cost (工期 / 技术债 / 影响面 / 可维护性) · provenance; a
hack or patch is a recorded debt decision, never a default (depth by size). "Enough basis" for go: key
feasibility rests on code, a derivation or a spike; thin evidence is stated; a question that could sink the
approach gets a bounded investigation or narrows the ask.

## The go ask (one message, receipts first)

Commit the card (`commit-data-repos.py --card <project>/<NNN>`), then ask with: 摘要 · the commitment list
(Req ids, one line each) · scope and not-in-scope · impact forecast (labelled) · risks and thin evidence ·
what the authorization includes and excludes · the **收敛行** `已定 n 项 · 待定 <…> · 未探索 <…> · grill: k 轮
/ 未做（原因）` · the judgment split: **已验证** (Claude checked — say how) vs **待你判** (only the human can
decide — each as 问题 · 选项与代价 · 推荐 · 不决的后果, plain language, ids only in brackets). A partial go
names the Req ids covered; the rest stay 讨论中. **What counts as go**: the word, or a reply that settles
every 待你判 item and raises no new question — name that reply in the 授权记录; an unanswered item gets asked
for by itself, never "please say go". On go: the 授权记录 line and each covered block's `确认:` line,
`status: executing`, `go:`, commit again (a tag is a pointer, not the approval).

## Executing (after go)

Stay in this session by default; switch when context is long, work is interrupted, or a handoff is being
tested. Usually just continue — change approach, add tests, reorder, fix review findings, update prose and
evidence — while the commitments hold and operations stay inside the authorization; a material approach
change gets one reason line. **A→B walk**: A's problem → does B still meet the commitments?
→ rewrite 当前方案 → one reason line → re-verify what B touches → sync facts / ADR / diagrams; B cannot meet
a commitment → propose and pause the dependent work. Product commits: `constraints.md` Git-1 (no card tail;
the Req 验证 line or plan.md row names the SHAs).
**Come back to the human only for** (1) changing a goal, weakening acceptance, dropping a deliverable, or
changing an explicit constraint or boundary; (2) work or a major trade-off beyond the authorization — "not
forbidden" is not authorization; (3) an operation needing its own authorization (`constraints.md` Ops).
Ask form: what was found · which commitment · proposed change; the doc carries a 待确认 proposal, the old
commitment stands, only dependent work pauses. Clarifications and blockers are not approvals: investigate
what code can answer, ask promptly for what only the human knows.

### Slice discipline

- **Recon first**: run the project's build / test baseline before slice 1 and record the exact entry
  (command · output · version) in the doc; read every build's warnings (an implicit declaration is a load-time undefined symbol).
- **Test mode follows the project's execution policy**: tests run by default → TDD (a failing test observed
  before the code; a bug fix reproduces first); "describe, don't run" → test-after (write or describe the
  test beside the code, defer the run, list the commands as suggested steps); unknown → ask before slice 1
  and record the answer as the project's standing policy. Both are vertical per slice — never all code, then
  all tests. `[x]` only on an observed pass; a criterion naming N sites is walked per site before ticking.
- **Commit when a slice's runnable checks pass** (`constraints.md` Git · Ver; granularity is your call, one
  concern each); verify the staged blob, not the worktree (`git show :<file>` — after a `reset --soft` the old content is what's staged); a
  project no-commit policy → checkpoint and ask.
- **Self-review before a slice is done**, against code not memory: a skip / ignore / optimize-away decision
  is classified safety vs liveness and fails safe · mirrored upstream logic replicates **all** branches at
  **every** copying site · a fix for a repeated pattern sweeps every instance · a value owned by one authority
  is validated there, never re-derived in another space · check-then-act is atomic only inside one transaction
  (a pool cap serializes statements, not sequences) · no blocking IO under a lock · deletion test + caller
  audit on every new function (a parameter every caller passes constant is unused generality) · no causal claim
  without the traced mechanism.
- **Scope**: the simplest *reliable* thing, no abstraction before the third use; touch only what the task
  needs — clean up what your own change orphans, leave pre-existing dead code (note it); don't re-handle
  anomalies the design already eliminated; compilable after every slice; additive and revertable.
- **Comments**: docstrings · step markers · why-notes for what the code can't show (a load-bearing guard's
  why at its definition; a patched-upstream divergence with the upstream commit SHA); density = the
  surrounding file's; a comment pass per slice deletes the rest and `tools/check-code-refs.py` runs on the
  diff (`constraints.md` Git-2). Generated test artifacts (`.source`-driven `sql/` + `expected/`) are gitignored.
- **L cards**: each part's completion gets one fresh-context attack on its diff (`lenses.md` frame; a guard /
  audit-class mechanism gets the injection mandate — try to bypass it); findings fixed or noted in one line,
  never a stop. A Task deleted / merged / deferred or a `[x]` invalidated leaves a one-line note (`constraints.md` Doc-7).

### Park / resume

Park = `progress.md` to the resume floor (now · next · blockers · build / verify entry) + commit; resume =
progress (if any) → design.md 摘要 → 承诺 → 当前方案 → evidence and code as needed — the summary is the entry,
not the contract; reading scope is unrestricted.

## Verification and close-out

A result names object, method, actual outcome and code version / environment — concurrent load included; a
test name is not a run, a link is not support. When code, approach or environment changes, re-judge old
evidence (stale → 待重验 with reason). Refuted (counter-example) and unverified (thin evidence) stay distinct
— the latter is never a negative conclusion (`investigate.md`). Review depth follows impact, reversibility,
invariants and verifiability, not task size. A "follow the text literally" criterion is run by an agent that
does not know the answer — the author's run does not count. A check run outside the card (scratch dir,
temporary dev_root) lands its result line in plan.md at once; progress.md may cite it, never assert it.
Close-out, in order: (1) **simplify** once when the change exceeds ~150 lines or adds files — behavior-
preserving, over the **whole diff vs the integration point** (`git merge-base origin/<main> HEAD`, not the
last session's slices), reuse / dead code / altitude per `smell-catalog.md`「Reuse / cohesion」, a final comment
pass; "describe, don't run" projects: non-structural cleanups only, structural candidates noted; result
recorded; (2) **review by size** — S: light self-review (diff walk · each commitment and Inv row against
the code · each test against its claim) written into the doc; M: `review` verb standard tier; L: deep —
**skipping any step is written down with its reason**; (3) per commitment: met / scope of the result /
unverified / residual risk — a task that promised only a plan closes on that, never claiming a run; a
promised run that cannot happen is a blocker or a negotiated cut; (4) `status: done`, board `done`, KB
triage, usage log `--action lite`, and the **observation note**: places synced per ordinary change ·
needless interruptions · doc time and lines read at go · missed commitments / unauthorized changes /
verification gaps · **quality steps skipped and why** · handoff gaps. Asking about a real doc gap is not a failure.

## By size

Size is judged at open and **re-judged whenever the scope or impact forecast grows** — the opening call is not
sticky; moving to a larger row switches on that row's requirements from that point, with one reason line.

| | XS | S | M | L |
|---|---|---|---|---|
| grill | one round, may share the go ask | as needed — say so in the 收敛行 | **required**: understanding statement · candidates · one question at a time to convergence (`discuss.md` §1–§2, §4 topics) | as M, per card |
| candidates / diagrams | one sentence / when triggered | 1+1 / when triggered | full spectrum + rejection reasons, ADRs as earned / when triggered | as M |
| lenses | — | by risk | once the approach forms: falsifier + commitment coverage (`lenses.md`; dispatch per `discuss.md` §3) — fresh-context, one agent each, adjudicate before reporting | as M |
| files / execution | design only | + progress at park | + plan.md (Req-tagged, binary tasks) · facts.md · adr/; **one documents-only handoff check** | split first: `split-isolate.md` A↔B + five steps; seam contract in 当前方案, 联调 rows in 测试与验证 |

Caps (anti-ratchet): `constraints.md`「Caps」(Cap-1); retro re-measures them.
