# Changelog — xg-dev-workflow

Behavior-level history of the skill (the curated view; `git log` is the full one). Maintained by
the M6 retro step: when a retro changes skill behavior, prepend a dated entry here, newest first.
Each entry says *what changed* and *why*, not the raw diff.

## 2026-07-16 (retro batch — comparison against the ~/.agents/skills 2026-07-09 set)

- **New `diagnose` verb + vendored step** (`references/steps/diagnose.md`, forked from
  `diagnosing-bugs`): feedback-loop-first defect localization — a red-capable repro loop before
  any theory (trap rule: reading code to build a theory before the loop exists → stop), 3–5
  ranked falsifiable hypotheses shown to the human, tagged instrumentation (`[DBG-*]`, one-grep
  cleanup), minimise-until-load-bearing, fix routed through Prove-It as an 实现 slice. Context
  branching mirrors `investigate`. *Why:* the workflow had no step for "why is this behavior
  wrong" — bug localization sat ad-hoc between investigate (read-only) and implement. Wired:
  SKILL.md verb + M5 + logging vocabulary, `investigate.md` cross-ref (defect ≠ spike),
  `provenance.md`, `log-usage.py` KNOWN_ACTIONS (all three copies).
- **SKILL.md slimmed ~36%** (5020 → 3229 words; no contract change): stop-at-gate and
  execution-zone autonomy each converged to one authoritative section (previously restated
  5×/4×); `status` viewer/gitweb detail pushed down to README; retro-origin parentheticals
  stripped; phase contracts trimmed to contract level (procedure detail stays in steps).
  First-use gloss rule gains its other half: after the first gloss, use the term bare. *Why:*
  writing-great-skills audit — duplication and sediment inflate always-loaded context.
- **Descriptions pruned** (one trigger per branch, identity statements moved to the body;
  681 → 508 bytes) and the `diagnose` trigger added.
- **test.md: tautological-test anti-pattern** — expected values must come from an independent
  source of truth; an assertion that recomputes the expectation the implementation's way passes
  by construction (from `tdd`).
- **plan.md: expand–contract exception** for wide mechanical refactors whose blast radius can't
  land green as one vertical slice: expand → migrate in blast-radius-sized batches → contract
  (from `to-tickets`).
- **review.md: fail-fast + report cap** — resolve the ref (`git rev-parse`) and confirm a
  non-empty diff before dispatching lens agents; lens reports capped at ~400 words.
  ("Skip tooling-enforced findings" was already covered by the false-positive exemplars — not
  duplicated.)
- **requirement.md: redundancy + prior-rejection checks** before drafting — search for an
  existing implementation by domain concept (not the ask's wording), and scan the roadmap's new
  「Rejected / won't do」ledger so rejected proposals don't return unnoticed (from `triage`).
- **Templates:** roadmap gains the「Rejected / won't do」section (requirement-level rejections;
  design-level ones stay in ADRs); progress gains a no-secrets redact note; split-isolate gains
  the card-vs-fog test (can the question be stated precisely, not answered — from `wayfinder`).
- **Fixed ID-prefix registry** (SKILL.md Conventions): one letter, one meaning — `NNN` card ·
  `R<n>` requirement 条目 (reserved) · `ADR-NNNN` · `T<n>` plan tasks · `G<n>` grill questions ·
  `M1–M6` mechanisms · `P<n>` implement principles; review findings `#<n>` + severity spelled
  out; parts named, never numbered. Collisions fixed: implement.md's forked rule set
  R0/R0.5/R0.6/R1/R2/R5 renamed to P* (numbers kept — R1 "one concern per commit" read as
  requirement R1 in the same phase docs); grill.md's stray `Q4` → `G4`; plan template's
  "Task 1 / Task N" formalized as `T1` / `T<n>` (user rule, 2026-07-16).
  Second sweep over *real* design docs added the design-side schemes: `L<n>` abstraction
  layers, `MS<n>` milestones (a live design used bare M1/M2/M3 for milestones — ambiguous
  against mechanism M2 in the same doc), grill ids continuous across rounds (a past grill
  escalated G→H→I letters per round; H also reads as a High finding), parts named with
  long-form `Part <n> (<名>)` only, Mermaid node ids diagram-local/exempt. Third sweep:
  `D<n>` design decisions/子决策 registered (organic in two projects' designs, incl. the
  ADR-scoped form `ADR-NNNN D<n>`); modules confirmed **named** like parts (`Mod<n>` only
  for a compact table/diagram id). Mapping direction pinned: cross-scheme mappings are
  recorded **downstream→upstream only** in each doc's designated field (design How-it-meets ·
  detail 可追溯 · plan `Implements:` · test Coverage · `ADR-NNNN D<n>`); reverse maps are
  derived, never hand-maintained (hand-kept reverse lists drift on every plan edit).
  Cross-file id citations are **markdown links to the id's home** (`[R1](./requirement.md)`,
  `[ADR-0006 D5](./adr/0006-….md)`) — designated fields and first mention always link, repeat
  prose mentions may stay bare; same-file citations stay bare. Templates' mapping-field
  examples updated to the linked form (user rule, 2026-07-16).
- **Harness task list as display mirror** (implement.md + resume.md): at the execution "go",
  create one harness task per plan `T<n>` (+ Final sweep) and update them at the same beats as
  `progress.md` — display-only; `progress.md` stays the resume truth and a fresh session
  rebuilds the list from it. Long walks (investigate campaign, diagnose phases, large M2
  affected-set) may mirror the same way. Decision-zone grills, M3/Lint checklists, and review
  fan-out deliberately don't use it (human-paced / scripted / minutes-long) (user go, 2026-07-16).
- **Simplify sweep closes 实现** (implement.md; M+, XS/S may skip): after the last slice, one
  behavior-preserving pass over the whole change (reuse / dead code / altitude / final comment
  pass) with the green suite as the net, suite re-run, separate commit; bindable `use:simplify`.
  test-after projects restrict to non-structural cleanups (no runnable net → asymmetric risk),
  noting skipped candidates. Per-slice P0 + deletion test stay — the sweep is the whole-diff
  pass they can't do; refactoring stays out of the red-green loop (tdd's rule). Wired: plan
  template gains a Final checklist block; SKILL.md phase 4 names the sweep (user go, 2026-07-16).
- **The advance word is `go`, uniformly** (Stop-at-gate): every advance ask is phrased around
  `go` and names what it authorizes (「回 go 进入设计」); the human's `go` (or an equally
  explicit equivalent) is the authorization — comments/praise without a go are feedback, not
  a go. Covers phase gates, the execution authorization, and post-verdict grill continuation
  (user rule, 2026-07-16).
- **implement.md: test-mode uncertainty asks** — when the project's test-execution policy isn't
  recorded anywhere (project CLAUDE.md / KB / a prior card's progress.md), ask the human
  TDD vs test-after before slice 1 instead of silently inferring; record the answer as the
  project's standing policy so the next card doesn't re-ask (user rule, 2026-07-16).
- **retro.md: KB usage-frequency scan** (periodic extra): tally `[[wiki/…]]`/`[[raw/…]]`
  citations across dev_root (one grep) to see which knowledge pays off — heavily-cited raw
  with no concept → promotion candidate; zero-citation concepts → dead-weight candidates.
  *Why:* KB reads leave no trace (`wiki/log.md` records mutations only, by design); the
  citations workflow docs already carry are the usage record — the retro just has to count
  them. Chosen over per-read logging (user decision, 2026-07-16).
- **Second pass — fresh-context writing-great-skills audit** (same day; 15 findings, 13 fully +
  2 partially applied): the batch's slimming had *compressed instead of disclosed* in places —
  M2/phase-6/verb entries still carried step-level procedure inline; converged them to
  contract-level pointers (change.md owns the M2 mechanics; Requirement sizing owns the
  close-out gate; Usage logging owns the `--action` mappings; Two zones owns the autonomy
  handoff — Stop-at-gate and Verbs now point). review.md's model-assignment rationale
  deduplicated to SKILL.md「Subagent model assignment」. Two completion-criterion fixes: the
  ~400-word lens cap gains an overflow rule (keep highest-severity + state count omitted —
  silent truncation was an unmeasured recall loss); requirement's Done-when now includes the
  redundancy/prior-rejection checks (they were ungated). Writing-style line collapsed to
  "plain prose, technical terms intact". SKILL.md 3229 → 3126 words.

## 2026-07-11 (card-002 retro batch — grill economy + fail-safe discipline)

- **Mid-grill new mechanism → pin principles, defer axes** (`grill.md` Protocol): when an answer
  injects a new mechanism into the phase doc, the current phase pins only its principles and
  boundaries; axis enumeration belongs to the next phase's grill. *Why:* card 002's requirement
  grill spent 3+ of 8 rounds enumerating LLD-grade axes for a mechanism injected mid-grill.
- **Verdict reports facts, never forecasts** (`grill.md` Convergence): "预期下轮 dry" is not
  dry-check output and anchors the human on optimism (a round-4 "衰减" forecast was refuted by
  round 5's wrong-results findings).
- **Third standing rule「class-to-constraint」** (`adversarial-critic.md`): the second same-shape
  finding pins a structural rule instead of continuing instance-hunting (symmetric closure took
  three rounds to be promoted; the trigger should be round two). References updated in
  `requirement.md`/`design-grill.md`.
- **Tiered dispatch on requirement repeat passes** (`requirement.md`): after a round that only
  edited already-grilled text, targeted re-verify of new clauses + lightweight consistency sweep
  — not another full pass (rounds 5–8 re-swept the whole doc while every finding sat in the
  previous round's new text).
- **Review lens「lifted fail-safe symmetry」** (`review.md`): a diff removing/relaxing a rejection
  path triggers a walk of the symmetric surface and type-wrapper (RelabelType) boundaries — the
  two silent-wrong-results bugs in card 002's close-out were both born from lifting v1 refusals
  without this walk.
- **Future items obey M1** (`review.md`): review-born Future/deferred items carry provenance —
  an unverified premise ("this wastes X") survived two phases before being empirically refuted
  mid-implementation (card 002 R12).
- **Data-type diversity for type-generic paths** (`test.md`): fixtures must include a type with
  non-trivial representation behavior (varchar/RelabelType, collatable) — an all-int suite kept
  a varchar-only wrong-results path green through 14 TDD slices.
- **Environment recon before slice 1** (`implement.md`): record the exact build/test invocation
  + baseline suite status in `progress.md`; run the baseline first; never filter build output to
  errors only (an implicit-declaration warning is a load-time undefined symbol).

## 2026-07-11 (status viewer — UI polish)

- **Visual direction ("terminal"):** the `status` HTML viewer (`tools/viewer/shell.html`) gets a
  coherent identity — mono-chrome (labels/ids/phases/tree/meta), squared corners, an amber accent,
  and a high-contrast dark palette — replacing the default-dashboard look. The card phase row is
  redesigned into a **gate-track** signature: one line of node + label per phase (fill = done /
  in-progress / pending), a marker at the decision→execution boundary, doc deep-links preserved.
- **Fullscreen ergonomics:** the list board is a responsive grid within each project section
  (equal-height cards, phase tracks bottom-aligned) instead of one stretched banner; a single
  document reads at a comfortable **measure** (left-aligned) with a **measure ⇄ full-width** toggle
  (persisted). Two-doc split and kanban are unchanged.
- **Manual theme toggle:** a 3-state control (follow OS / light / dark) whose choice overrides
  `prefers-color-scheme` and persists; mermaid re-themes on toggle. Cards use a compact eyebrow
  (state pill + project·id) → title → aligned Now/Next skeleton; doc frontmatter renders as a
  compact meta line, not a table; unknown/`?` status reads as a dashed outline; badge text adapts
  per theme. Plus an a11y floor (visible focus, reduced-motion) and a top-level "browse code"
  (gitweb) entry. Why: the viewer is used fullscreen for long reading + at-a-glance triage; the old
  layout wasted width, ran prose edge-to-edge, and had no distinct identity.

## 2026-07-08 (subagent model assignment — cost)

- **New SKILL.md rule「Subagent model assignment (cost)」**, generalizing review step 4's
  per-lens model table (from a 2026-07-08 standalone investigation, landed via M6 on human
  approval): checklist/gather/verification-driven subagent work defaults to Agent-tool
  `model: sonnet`; inference-heavy analysis, adjudication, and decisions stay on the session
  model; deterministic checks are scripted rather than delegated; every downgrade sits under
  M6 calibration (revoked when its findings repeatedly die in adjudication or it repeatedly
  misses what the orchestrator catches). Why: Sonnet runs ~3.3× cheaper per token than the
  session model and delegated reads leave the main context entirely; the orchestrator's
  existing re-derive/adjudicate duties already backstop precision, so the downgrade costs
  recall at worst — applied only where recall doesn't lean on inference depth.
- **Dispatch points wired to the rule:** M1 gather dispatches pin `model: sonnet`
  (`evidence.md`; exceptions stay on the session model — swappable-seam full enumeration and
  birth-certificate-negative traces, where recall is the deliverable with no cheap backstop);
  M3 gains a「How to run (cost)」section (`omission-check.md` — deterministic subset
  script-eligible, judgment subset to one sonnet agent, inline stays fine right after an
  edit); the critic's lightweight consistency pass pins its "cheaper model" wording to
  `model: sonnet` (`adversarial-critic.md`); `review.md` step 4 now names itself the origin
  of the generalized rule. `change.md` needed no edit — its "consistency agent" mention is a
  historical note, not a dispatch instruction (corrects the investigation's initial reading).

## 2026-07-07 (fourth batch — review rounds 1+2 fixes)

- **Two new M3 items** (review F8, human opted for both): decision-zone comparison/evaluation
  tables carry a provenance marker per comparative claim; a persisted grill log using
  session-local codenames carries a legend line. Templates caught up with the round-1 rules
  (design Alternative scaffold states the provenance requirement; test template carries the
  post-suite log-sweep line); `detail.md` regained its explicit read-only-on-product-code
  contract.
- **log-usage.py normalization extended to report time** (supersedes the second batch's
  "at write time" description): `canonical_action()` is applied to stored rows *and* to the
  `--action` filter argument (per-row, under each row's skill) in `cmd_report`, so pre-fix
  records aggregate under canonical verbs and filtering by an alias spelling still matches.
  The append-only log is never rewritten. Synced to all three copies.

## 2026-07-07 (third batch — writing-great-skills audit, Tier 1+2)

- **SKILL.md de-duplicated and disclosed** (5630 → 4763 words; no behavior change — every cut
  either collapsed a duplicate to its single source or moved branch-specific reference down the
  ladder): the `detail` verb bullet (near-wholesale duplicate of phase §3) deleted; `investigate`/
  `review` verb bullets compressed to front-door + gate + step pointer (details live in their step
  files); M5's restatement of the investigate front-door replaced with a pointer; Stop-at-gate's
  duplicate "one phase" bullet merged and its execution-zone tail (a preview of the Two-zones
  section that immediately follows) cut to one pointer line; the fork-provenance table moved to
  `references/provenance.md` and 拆分与隔离 field mechanics to `references/split-isolate.md`
  (SKILL.md keeps the essence + A↔B 判定 stub — existing 「拆分与隔离」 references still resolve);
  Step binding compressed; two meta/no-op sentences removed ("balance still being tuned",
  first-use-gloss transcript-evidence tail). Tier 3 (phase-paragraph section enumerations) left
  for future pruning passes. Audit: dev_root xg-skills notes/retro-2026-07-07-wgs-audit.md.

## 2026-07-07 (second batch — from the ~/.agents/skills comparison study)

- **retro.md: pruning pass (anti-sediment), every retro.** No-op test sentence-by-sentence,
  duplication collapse to a single source of truth, sediment check (a rule whose justifying
  friction no longer shows up gets retired). *Why:* retros only ever added rules — the
  `writing-great-skills` failure-mode vocabulary names where that ends (sediment/sprawl);
  deletions now have a standing home, with the same human confirm as additions.

- **Description pruned to branches + leading words** (~160 → ~95 words, `wc -w`). Mechanism details
  (M1/M5 discipline, lens fan-out, report locations, frozen-design list) moved back to the body
  they restated; one trigger form per branch kept (CN+EN). Same treatment applied to
  xg-knowledge-lite's description. *Why:* the description is always-loaded context — per
  `writing-great-skills`, it earns harder pruning than the body.

- **Spike — a throwaway probe when reading can't settle it** (investigate.md new section;
  grill.md interleave bullet routes empirical questions to it; SKILL.md investigate verb notes
  it). Probe lives outside the product tree, never committed; the answer upgrades the claims
  table to VERIFIED and lands via normal routing; the code is deleted. A probe needing product
  changes isn't a spike — escalate. *Why:* grills kept parking empirical open questions as
  待验/落地前验 (cbdb 002 left two); adapted from the `prototype` skill ("throwaway code that
  answers a question").

- **M4 session hygiene** (one sentence in SKILL.md): decision-zone grills stay in one unbroken
  window (no mid-grill compact); execution-zone tasks cold-start from `progress.md` — prefer
  `resume` in a fresh session over pushing a long degraded one. *Why:* M4 mechanically supported
  fresh-session-per-task but never recommended it; borrowed from ask-matt's context-hygiene flow.

## 2026-07-07

- **grill.md: recommendation pre-check — self-proposals get the same rigor as external ones.**
  Before recommending an own idea inline (not only in dispatched panels), three checks must pass,
  else it's presented as an open question: comparative claims VERIFIED (no unread-code claims in
  comparison tables), magnitude × medium cost (multiply by the requirement's design scale and the
  access medium's per-op cost), cost symmetry (list what the proposal *adds* — writers/schema/
  state/RPC shapes — not only what it saves). *Why:* 2026-07-06/07 proposal-T grill — three
  consecutive design recommendations overturned by the human on exactly these grounds (overstated
  "零cache/零save hook" table; per-row catalog lookup at 10^6 over RPC; a read turned into a
  write to save a join); the rigor applied to user proposals wasn't applied to own ones, and the
  07-05 dispatch fix only covered agent panels, not inline recommendations.

- **First-use gloss rule (SKILL.md conventions) + grill codename legend.** Coined terms,
  session-local codenames, and non-standard abbreviations carry a one-line parenthetical
  definition at first use per doc and per chat session; a term used fewer than ~3 times isn't
  coined at all. Persisted grill logs that coin scheme codenames (方案 T/S, N1…) keep a one-line
  legend up top. *Why:* transcript scan found 14 "xxx 是什么意思?" questions in two weeks — all
  coined-term/codename/idiom category (M+, 不变量台账, R1, T/S, tp-bearing…); M3 checks term
  *consistency* but nothing covered first-use *comprehensibility*.

- **design-grill.md: comparison/evaluation tables carry a provenance column from the first
  draft** (VERIFIED/INFERRED per cell-claim) — a comparative claim about existing code is a code
  claim (M1). *Why:* same proposal-T retro; the unverified comparison table was the round-1 defect.

- **test.md: post-suite log sweep.** After a full-suite run, sweep server/process logs for silent
  failures (green ≠ no error lines; masked paths pass assertions while logging the real failure);
  "describe, don't run" lists the sweep command alongside. *Why:* cbdb 002 — suite green while
  the log carried a silent sync failure masked by the manual path; the ad-hoc sweep caught it.

- **design-grill.md: card graduated with pre-design.** When a card is born from another card's
  M2/grill evaluation note that already reached design/LLD depth, the design phase *consumes*
  that note (ADR-ize + trace + link) rather than re-deriving; the grill targets what the note
  left open. *Why:* cbdb 003 graduated from 002's proposal-T evaluation at LLD precision — the
  shape worked but wasn't blessed.

- **retro.md periodic extras: KB compile-backlog triage** — each uncompiled raw gets compiled or
  an explicit `compiled_to: deferred — <why>`; missing frontmatter gets repaired. The
  session-start hook only surfaces the backlog; the retro resolves it. *Why:* 6 uncompiled raws
  (2 without frontmatter) had accumulated across acme-db/postgresql/vagrant-qemu with no owner.

- **log-usage.py: recurring mis-logged actions normalized at write time** (implement→plan,
  implement/test→plan, design-note→design, change/adr→change; synced to all three copies).
  *Why:* off-vocabulary spellings kept fragmenting the report aggregation the retro mines
  (4× "implement" alone) despite the warning.

## 2026-07-05

- **grill.md: convergence verdict must surface in the round-closing user message** (not only in
  the grill log / phase doc). The verdict format line already said "one line in chat" but weakly;
  in practice the ADR-0006 grill filed each round's 继续/建议收敛 into the log while closing the
  user-facing message with only *what was found/fixed*, forcing the human to ask "还要继续吗?".
  Strengthened to MANDATORY: the 继续/建议收敛 recommendation is a *conclusion* the human needs
  to decide next-step, so omitting it is a defect. Covers **both** grill users (`requirement`
  elicitation + `design-grill`) since both run this shared step. *Why:* user 2026-07-05 — "为啥
  grill 完没有直接给出是否需要继续 grill".

- **Anti-residual mechanism for semantics-changing changes** (retro of ADR-0006 propagation:
  three old-semantics restatements survived a full rewrite + a consistency agent — an untraced
  Scope tail sentence, the `FloorMerge` module name, a self-noted-then-dropped clarification).
  Root cause: trace-driven M2 propagation touches traced items only; docs also carry
  *restatements* outside the trace, and *names* assert nothing false so consistency reads miss
  their drift. Three additions: (1) `change.md` step 2b **supersede sweep** (mode 变更/撤销
  必跑): retired-phrasing grep across all phase docs, every hit rewritten / annotated-历史表述 /
  justified, plus a rename check per changed contract and a rewrite checklist collecting
  scattered "改写时澄清" notes; (2) `adr.md`: superseding/semantics-changing ADRs list
  **被取代表述** (the sweep's word list); (3) `omission-check.md`: new M3 item verifying the
  sweep ran. New tool `tools/check-superseded-phrases.py` (deterministic grep, exit-code
  gated, `--exclude` for history dirs).

- **adversarial-critic: grill dispatch made faster without lowering the M1 floor** (retro of the
  2026-07-04/05 ADR-0006 grill — 6 rounds, 2 heavyweight agents ≈15 min / ≈140k tokens each;
  user asked how to accelerate). Four dispatch-level changes; verification discipline untouched
  (blockers still orchestrator-verified, every CONFIRMED still cites `file:func`):
  1. **Parallel one-agent-per-lens is now the default panel form** (the merged three-mandate
     agent demoted to trivial checkpoints). *Why:* mixed mandates satisfice on secondary lenses —
     search-before-build skipped the remediation design and cost two extra rounds; single-lens
     agents in parallel cut wall-clock to ~the slowest lens and decorrelate blind spots.
  2. **Verified-facts pack (new third artifact).** CONFIRMED findings + positive verifications
     accumulate in the grill log and are attached to every subsequent dispatch, scoping mandates
     to the delta + integration seams. *Why:* rounds 1 and 5 each re-proved the same kernel
     chains (suppress-only semantics, aggressive read-point) from zero.
  3. **Invariant ledger is maintained in-session, not deferred to as-built.** A grill-confirmed
     invariant lands as an evidence-cited ledger line immediately; only concept articles may
     wait. *Why:* the deferred ledger was the root cause of (2)'s re-verification.
  4. **Tiered passes in design-grill.** Full three-lens panel only at decision-level
     checkpoints; a rewrite implementing an already-grilled decision gets a lightweight
     text-consistency agent (cheaper model, no kernel re-verification; escalate only findings
     that implicate code truth). *Why:* 7 of 8 post-rewrite findings were text-consistency —
     the heavyweight pass mostly re-proved settled facts.
  design-grill.md's panel bullet now points at this dispatch guidance and extends the lenses to
  newly proposed remediations mid-grill (search-before-build the fix before designing it).

## 2026-07-03

- **review.md: checklist lenses default to the cheaper model.** Conventions / tests-hygiene /
  docs-accuracy / git-history lenses dispatch on `model: sonnet` by default; correctness,
  the adversarial trio and security stay on the session model, and step-5 adjudication is never
  downgraded (the precision backstop that makes cheap finders low-risk — recall on checklist
  lenses doesn't lean on inference depth). M6 revokes a downgrade whose findings repeatedly die
  in adjudication or whose axis stops contributing (5b overlap stats). *Why:* user 2026-07-03 —
  token cost; the same-day sonnet pass had just demonstrated verification-driven work holds up.

- **review.md: standing model-diversity agent in the fan-out.** Every review now dispatches,
  besides the lens agents, one light-sweep agent on a different model (Agent `model: sonnet`)
  with fresh-eyes framing (intentional-changes list + "zero findings is a good outcome" +
  execute-don't-just-read where safe); 5b's unused-axes list gains the model axis. *Why:*
  same-model lenses share failure modes — the 2026-07-03 sonnet pass caught a false-positive
  class (check-code-refs flagging the skill's own directory name) that three same-model lenses
  had all missed, at the cost of one extra agent.

- **Review-driven fixes (reviews/2026-07-03, 4M/15L, all applied).** Tools: `--root` value no
  longer leaks into workflow-status's project list (quoted-tilde emptied output) and `--root=`
  accepted; template placeholders no longer mask the gate-derived next step; check-code-refs
  same-line allowlist swallow + `++`-line header misparse fixed; commit-data-repos argparse
  errors exit 0; parse_key strips inline comments. Wiring: investigate.md adopts the blessed
  investigations naming (`<topic>.md`, campaign dir for large ones); design-grill's old
  convergence bullet now defers to grill.md's canonical auto-verdict, and every "protocol +
  grill-log + rollback" enumeration gained the fourth shared piece; **grill checkpoint commits**
  (one per round verdict) give the dry check its diff baseline; review-vs-investigate anchoring
  difference documented as deliberate in both steps; `pre-gate done` grandfather note recognized
  by the M3 close-out item; change.md Guardrail admits the better-approach reason, seam flow
  gains its proportional re-grill, entry gate covers the design-driven entry.

- **New `status` verb + `tools/workflow-status.py`: the card view.** Workflow visibility was
  split across the kanban (coarse: Phase + 整体状态) and each card's `progress.md` (the detail,
  one file at a time). The new read-only tool aggregates, per card: the pipeline position
  (每阶段 doc 的 frontmatter status), board 整体状态/Deps, progress's Now/Next/Blockers, and a
  **gate-derived next step** when progress has no Next bullet (which gate the card waits at).
  Computed from the docs on demand — no cached view to drift — and doubles as a light data check
  (its first run surfaced three real gaps: two cards' progress frontmatter missing `status:`,
  and webapp 003's frontmatter still saying in-progress after done). `status` added to the
  logging vocabulary (log-usage.py copies re-synced). *Why:* user 2026-07-02 — "workflow 可见性:
  card 视图、每卡具体状态、步骤展示、下一步是什么".

## 2026-07-02

- **Layout naming: underscore prefixes dropped.** `_index.md` → `index.md`, `_roadmap.md` →
  `roadmap.md`, `_investigations/` → `investigations/` across the layout tree, steps, and
  templates. The `_` was an inconsistently-applied "project-level meta" marker (`reviews/` never
  had it); the human chose full removal over extending it. dev_root data renamed in lockstep
  (git mv + in-doc reference fixes; `log.md` and `legacy/` untouched as append-only/archive), and
  all remaining old-format per-project index files were upgraded to the card-kanban format in the
  same pass. Historical CHANGELOG entries keep the old names — curated history stays as written.

- **Terminology: form rule + visible pins + human-initiated 术语纠正.** The sharpen-language
  tactic only fired on vague/overloaded terms and pinned them silently, and M3 only checked
  *consistency* — so a force-translated term used consistently everywhere (堆 for `heap`) passed
  both. Now: (1) canonical **form** follows the global Language rule (established EN technical
  terms stay EN) — a force-translated term is a pin trigger / M3 drift even when consistent;
  (2) pins are **stated as they happen** (`术语: heap (_Avoid_ 堆)`) so the human sees when a term
  got decided and can veto; (3) a human flagging a term while reading any doc is a defined
  **术语纠正** flow — pin in CONTEXT-MAP **first** (the anchor M3 reads, so one correction
  propagates), then the owning KB concept, then rewrite the current card's docs (other cards heal
  at their next M3), `log.md` entry inside a card. *Why:* user question 2026-07-02 — term
  decisions were invisible and the wrong-form class had no trigger.

- **`tools/check-code-refs.py`: the no-doc-refs-in-code ban is now a script, not an improvised
  grep.** The ban (no workflow/KB doc references, `.md` mentions, wikilinks, **bare `ADR-NNNN`
  references** (added same day), or line numbers in code comments — repo-public README/CHANGELOG
  etc. allowlisted, also same day) existed in implement.md but its check was "grep the changed
  files" — improvised
  each time, so it kept getting skipped and the refs leaked anyway. New stdlib script scans the
  working diff's added lines (or given files) for the banned patterns, quiet when clean, exit 1 on
  hits; issue/ticket refs stay unflagged. implement.md's hygiene pass now invokes it verbatim, and
  the review conventions lens runs it on the target range (a hit is a finding unless the file's
  domain is the docs — advisory, judged, not auto-stripped). *Why:* same lesson as the comment
  pass — a rule without a deterministic check point doesn't hold.

- **implement.md: mandatory per-slice comment pass; review conventions lens flags over-commenting.**
  The 代码即文档 bullet already said "few but necessary" but was descriptive prose with no check
  point, and projects built through the workflow kept accumulating narrative comments. Now the
  allowed set is explicit (file/function docstrings · step markers · why-notes for constraints the
  code can't show; density = the surrounding file's), a **comment pass** joins the per-slice
  hygiene sweep (re-read added comments, delete narration), and the review verb's conventions lens
  treats over-commenting as a finding. Same rule landed in global CLAUDE.md「Code Comments」so it
  also governs ad-hoc edits outside the workflow. *Why:* user feedback 2026-07-02 — guidance
  without a gate didn't change behavior; the delta is the checkable pass.

- **M2/change.md: R-id-scoped, mode-classified propagation (rewrite of Route A) + detail-only
  route.** Route A was wholesale ("re-evaluate design.md", "regenerate plan.md") even though the
  same enhancement batch had built the R-id traceability spine — and it skipped `detail.md` and
  `test.md` entirely while the seam trigger already did precise scoped rollback. Now: entry is
  **gated** (human decides, incl. escalated design-forks); each affected 条目 declares a **mode**
  — **追加** (new R-id: append downstream, nothing invalidated, approval scoped to the addition) ·
  **变更** (supersede: superseding ADR + traced `[x]→[ ]` resets + test-row resets + proportional
  re-grill of just the changed contracts) · **撤销** (retire, keep the ID, retire downstream) —
  and propagation walks the full spine (design → detail → plan → **test**) touching only traced
  items; **cross-card Deps** are checked for ripples; a new **case C** codifies the detail-only
  baseline change; seam-contract-disproved is labeled as case-A mode-变更. *Why:* 2026-07-02
  discussion — the mode split (直接改变 vs 追加) is the human's insight; scoped propagation
  brings Route A to the precision the seam flow already had. Same-day follow-up: Route A gained
  an explicit **design-driven entry** (方案变更 with the requirement unchanged — `requirement.md`
  untouched, record = superseding ADR + `log.md`, affected set = the changed modules/contracts'
  traces, the rewritten「How it meets」re-verifies the same R-ids); previously the steps forced a
  no-op requirement edit and mis-anchored the propagation on R-ids.

- **retro.md: outputs section + usage-log input/re-scoring.** Three gaps closed: (1) Inputs now
  include mining the usage log (SKILL.md M6 said it, the step file didn't); (2) step 5 adds the
  corrective re-scoring of optimistic provisional records (was only in the global logging rule);
  (3) a new "Where the outputs land" section states what M6 produces and where — fixes/CHANGELOG/
  commits in the skill repo, deferred fixes in `<project>/_roadmap.md`, card-scoped retro analyses
  in the card's `notes/retro-<scope>.md` (blessing the existing webapp practice), cross-card
  retros need no doc of their own. *Why:* user asked "M6 产生什么文档、在哪" 2026-07-02 and the
  answers existed only as convention.

- **Human-first docs must show the reasoning, not only cited facts.** The "logical/causal
  analysis, not a grep-hit list" discipline lived only on the `investigate` verb (M5) — it
  governed the investigation, not what lands in the docs, so a design's Understanding /
  How-it-meets could legally degenerate into an evidence-cited fact table with conclusions
  bolted on (uncheckable inference). New doc convention: in requirement/design/detail/ADR/review
  **and investigation-notes** prose (extended same day — standalone `investigations/` files and KB
  raw, where the rule originated) every load-bearing chain reads **evidence → mechanism →
  conclusion** so the approver can check the inference; design template's Understanding section
  says it explicitly. Execution-zone
  docs stay terse (link, don't restate). *Why:* user 2026-07-02 — 人读文档要有逻辑分析,
  不只是代码事实.

- **Layout: three project-level locations blessed + M3 no-strays check.** `investigations/`
  gains the `<topic>/` **campaign dir** form (charter + phase notes + progress — the shape large
  investigations already took) and new single files drop the redundant `investigation-` prefix;
  `<project>/notes/` (project-level scratch: proposals, triage, project retros — event artifacts
  dated) and `<project>/legacy/` (pre-workflow archive, read-only) are now spec'd. M3 gains a
  「项目根无散件」item. dev_root strays migrated accordingly (skill-notes + the detail-step
  proposal → xg-skills/notes/, 042-data-loss → acme-db/investigations/, webapp mvp0
  strays → notes//legacy/, vagrant-qemu triage → notes/, the mis-slotted xg-skills audit →
  xg-skills/reviews/) and existing card review/retro files renamed to the dated convention.

- **notes/ naming principle: event artifacts dated, living docs not.** Review reports and retro
  analyses are immutable event artifacts → `review-YYYY-MM-DD-<target>.md` /
  `retro-YYYY-MM-DD-<scope>.md`; the grill-log (one append-only file per phase, re-grills append)
  and topic scratch (edited in place, history in git) stay date-free. Stated once in the SKILL.md
  layout comment.

- **review.md: card-level report filenames carry the date.** `notes/review-<target>.md` →
  `notes/review-YYYY-MM-DD-<target>.md` — multi-round reviews of one target (saturation verdict,
  close-out + fix-verification) collided or dated themselves ad-hoc (acme-db appended dates,
  cbdb didn't); now mirrors the standalone `reviews/YYYY-MM-DD-<slug>.md` convention while
  keeping the `review-` prefix the M3 gate globs. Existing files stay (glob still matches);
  unifying them can ride the deferred layout migration.

- **review.md: anchoring question in step 1.** The report's two homes are by design (active
  card → `notes/review-*.md`, standalone → `<project>/reviews/`), but "active" was purely
  session-dependent, so one card's review history could scatter across both (cbdb appserver
  reviews: three in `reviews/`, one in `002/notes/`). Now, when no card is active but the target
  is plainly one card's work, review **asks** whether to anchor instead of silently defaulting to
  standalone. *Why:* user spotted the scatter 2026-07-02; explicit-linkage stays the rule — the
  fix adds a question at the boundary, not topical auto-anchoring.

- **review.md: saturation verdict + adaptive diversity (step 5b).** The review sibling of the
  grill convergence auto-verdict: "a re-review found something" is sampling variance (a review is
  a bounded search over a generative defect space), so whether another pass is worth it is read
  from **adjudication overlap statistics**, not from the existence of new findings — during step 5
  record how many independent paths (lens agents + orchestrator deep-read) hit each confirmed
  finding; **overlap-dominant → near-saturated, recommend stop; singleton-heavy → under-sampled,
  recommend one more pass along axes not yet used** (slicing / reading direction: diff-first ·
  problem-first · spec-first · history-first / polarity: verify-claims vs hunt-bugs — re-running
  the same lens is voting, not diversity); a pass with nothing above the action bar is **dry →
  stop** regardless (a new High on a later pass = genuine miss → retro). One-line verdict goes in
  the report 总体结论 + chat; human still decides. *Why:* same 2026-07-02 discussion as the grill
  rule — the 2026-07-02 xg-skills review itself showed the pattern (the High hit by 3/3 lenses =
  saturated top; several single-lens Mediums = unsaturated middle).

- **grill.md: explicit convergence rule + per-round auto-verdict.** "New questions exist" was an
  unreachable stop criterion (the question space is generative — a fresh pass can always ask
  more), so grills had no principled end. Convergence is now judged by **materiality** — would
  another round still change the decision this phase gates? — via three checks Claude runs at the
  end of every round, emitting a one-line `Grill 收敛判定: 继续/建议收敛` recommendation (the human
  still gates): (1) slot three-state (evidence-backed · human-confirmed · explicitly Open — finite,
  bounds the elicitation grill), (2) decision-level dry check for repeat/adversarial passes (zero
  条目/方案/contract/ADR-level doc changes this round = dry → stop; XS/S one pass, M+ until dry;
  verified against the git diff, not memory), (3) ADR-weighted open points (hard-to-reverse ×
  surprising × real trade-off earns a targeted round; the rest get the recommended default + an
  Open row). A later pass re-opens settled ground only with a decision-changing finding (else →
  Open questions / `_roadmap.md`); M6 calibrates the bar from post-freeze M2 rates vs dry-round
  rates. *Why:* discussion 2026-07-02 — "第二次 grill 总能问出新问题" is perspective diversity,
  not incompleteness; depth must be stop-rule-driven, not count-driven.

- **`commit-data-repos.py`: a data dir only counts as a repo if it is its own work-tree toplevel.**
  Previously `rev-parse --is-inside-work-tree` also matched a not-yet-initialized `~/knowledge` /
  `~/dev-workflow` sitting inside an ancestor's work tree — `git add -A` would then have staged and
  committed the whole ancestor repo. Now such a dir gets its own nested `git init` (the intended
  lazy-init), and a top-level guard makes "Exit 0 always" hold even on unexpected errors (matching
  `kb-backlog.py`). *Why:* found by the 2026-07-02 review (reviews/2026-07-02, M2/L9).
- **Alignment fixes from the same review.** Commit-cadence summaries now say "after each
  **completed** task (runnable checks green)" — the old "verified task" wording read as zero
  autonomous commits in test-after mode, where acceptance stays `[ ]` pending-run. `progress.md`
  is created on **first need** (a mid-grill checkpoint or in-requirement `investigate` may create
  it before 实现) — "lazy" means don't pre-create, not implement-phase-only. The board `done`
  constraint now includes the close-out clause (review doc or `XS/S — review skipped` note)
  everywhere it's stated. Plus template/README alignment: 跨 part 联调 nested under Integration
  with a when-split grouping note, Reader tags on adr/index/roadmap, seam-vs-boundary scoped,
  READMEs cover 拆分与隔离 + `_roadmap.md` + hook-wiring examples, skill description mentions the
  评审 gate.

## 2026-06-30

- **M3 omission-check tightened: "knowledge captured" → "captured & compiled".** A reusable insight
  must reach the KB **through xg-knowledge-lite's Write flow (compliant frontmatter — not a bare
  hand-written file)** and be **compiled to a concept or explicitly deferred**, not left as an
  uncompiled raw. *Why:* this session routed an investigation through `investigate` but recorded it
  with a direct `Write` — producing a raw with no frontmatter that the compile-tracking couldn't see,
  and never compiled. Sibling fix in xg-knowledge-lite: `kb-backlog.py` surfaces uncompiled raw at
  every SessionStart (push, not the old pull-only Lint/Orient), and Compile now must back-annotate
  `compiled_to:` + update `wiki/index.md`.

## 2026-06-28

- **Docs (dev_root) + KB are now git-managed, with a commit cadence.** Each is its **own repo**
  (separate from the product-code repo and from each other), **lazily `git init`'d** on the first
  commit (announced once). dev_root commits at each **gate / doc boundary** (one per verb:
  new/requirement/design/detail/plan/per-task progress/test/review/change/investigate-notes, after
  M3); the KB commits after each **Write/Compile/Lint** (mirroring `wiki/log.md`). **Autonomous local
  commit, push human-gated, history append-only** — the same discipline as the product-code Commit
  cadence (an implement task → two commits: code to its repo, `progress.md` to dev_root). New
  helper `tools/commit-data-repos.py` (init-if-needed + commit-if-dirty + never-push, reads the
  shared config) backs an **optional session-end hook** that sweeps any uncommitted docs/KB. *Why:*
  "文档和 KB 也要被 git 管理,有提交时机,自动提交" — extends the commit discipline to the two data repos.
- **Project-global, card-transcending docs — placed by nature.** Added a project **roadmap**
  (dev_root `<project>/_roadmap.md`, new template): next-up / themes / someday / graduated — a
  savable plan lighter than the kanban so deferred work (cards' Future / Discovered-issues) isn't
  forgotten; items graduate to cards via `new`. **System knowledge stays in the KB**: the design
  step now links each card to the KB **architecture** overview (`[[wiki/<project>/architecture]]`)
  and refreshes it (as-built) on freeze, and adds durable invariants to the subsystem **invariant
  ledger** — both made first-class in xg-knowledge-lite (Orient surfaces them, Lint checks them).
  M3 now checks the roadmap is fed + the architecture/invariants didn't drift; retro scans the
  roadmap. *Why:* "每个 project 要有超脱各 card 的全局文档(架构 / 路线图 / 不变量台账)" — split by
  the repo invariant (planning → dev_root, system knowledge → KB); the invariant ledger already
  existed per-subsystem in the adversarial-critic, just not discoverable.

## 2026-06-27

- **需求条目 (Requirement items) as the traceability spine.** `requirement.md` now carries a
  canonical itemized list — atomic requirements with stable `R-id`s — that Scope/Effect and every
  downstream doc (`design.md`, `detail.md`, `plan.md`, `test.md`) reference by ID instead of
  restating. *Why:* a flat prose requirement couldn't be traced or changed item-by-item; IDs
  localise change and close coverage holes (an `R-id` with no test/task is now a flagged gap).
- **影响面 (Impact surface) section in `design.md`.** Design now states the blast radius —
  changed/added modules, callers & downstream consumers, compat/ABI surface, cross-card/cross-project
  ripples, behaviors to re-verify. *Why:* scope/risk and review focus were implicit; the Risk table
  alone didn't capture who-breaks-if-this-changes.
- **评审 (review) wired as the M+ close-out gate.** After 测试, an M-or-larger requirement runs the
  `review` verb to produce `notes/review-*.md` before the card can go `done`; XS/S may skip. *Why:*
  code earned a test doc but a formal review was ad-hoc; non-trivial changes now end with both.
- **Implementation phase autonomy made explicit.** The implement phase rolls through plan slices
  without per-task gates; Claude owns implementation-level decisions (makes + logs them), escalating
  only on a design/requirement fork (→ M2), a blocker, or a commit request. *Why:* Stop-at-gate was
  being misread as a per-slice halt.
- **Plan-task drops are logged.** Deleting / merging / deferring a task — or invalidating an `[x]`
  — now gets a `log.md` `[实现]` entry (what + why); routine refinement stays silent. *Why:* a
  freely-mutable plan left dropped tasks untraceable — resume/review couldn't tell "done" from "forgotten".
- **Provenance markers generalized.** Load-bearing claims in any phase doc carry an evidence-cited /
  推断 / 假设 marker (not only `investigate` conclusions). *Why:* unmarked assertions read as
  evidence-backed even when they're assumptions.
- **Mermaid preferred for diagrams; link policy clarified.** Diagrams default to Mermaid (ASCII
  fallback); intra-tree references use standard markdown links while KB cross-refs keep the
  load-bearing `[[wiki/…]]` wikilink. *Why:* `[[ ]]` and ASCII don't render/click in common viewers,
  but the wikilink drives KB recompile so it stays.
- **Issue/ticket references allowed in code comments.** The comment-hygiene rule still strips
  uncommitted-doc references and line numbers, but explicitly permits a stable issue/tracker ID/URL.
- **Two-zone model (decision vs execution) made a first-class concept.** The 设计/详设 freeze is
  framed as a single line that is *both* the binding-decision boundary *and* the reader/audience
  boundary: requirement/design/detail are **human-first** (reviewable, gated); plan/progress/test
  are **Claude-first** (autonomous execution + resume) — with `log.md` (audit) and the close-out
  review report as the two deliberate human-facing artifacts in the execution zone. Every template
  now carries a one-line **Reader** tag, and the implement-phase autonomy is tied to this boundary
  (plan = the one-time autonomy handoff; next human touch = the close-out review). *Why:* unifies
  the earlier "split docs by reader" and "implementation needn't wait for the user" points — they
  are the same boundary seen from two angles.
- **Stop-at-gate carve-out for the execution zone.** The hard stops are now scoped to the
  decision-zone gates (需求 confirm · 设计 freeze · 详设 baseline) **plus** the one-time execution
  authorization after `plan.md`. Within the execution zone there is **no per-phase stop** — on one
  "go", implement → test → the M+ close-out review report run autonomously, stopping only to
  escalate (design-fork/blocker/commit) and finally at the review report's fix decision. *Why:*
  "实现阶段不用等待用户决策" means the per-phase checkpoints between implement/test/review aren't
  human *decisions*, so they shouldn't gate; the binding decisions all live before plan.
- **CHANGELOG introduced** (this file) — the M6 retro step now records behavior changes here.
- **Refined after self-review (same day):** (F1) **requirement sizing** (XS/S vs M+) is now defined
  once in SKILL.md「Requirement sizing」, and the close-out gate is verifiable as "a review doc
  **or** an explicit `XS/S — review skipped` note (in `progress.md`)" — so M3 needs no size field,
  it just checks one-of-two is present. *Why:* the gate hinged on a requirement-size axis that was
  never defined and that M3 had no signal to evaluate. (F3) clarified **需求条目 vs Effect** as
  need ↔ acceptance-test (a 条目 = what's required; an Effect = the checkable condition proving it).
- **Investigation = logical analysis, not grep.** `investigate.md` gains an
  「Analysis, not just grep」rule (+ M5 pointer): grep/read only *gather*; the deliverable is a
  traced control/data path + a causal mechanism + the Synthesis lens — a grep-hit list is not a
  conclusion. *Why:* investigations were at risk of degrading to "found N matches, here's a list".
- **Commit cadence.** Implement now commits **autonomously and locally after each verified task**
  (and after each review fix), one concern per commit; **`push` stays human-gated** and history is
  append-only (no amend/squash). Respects an explicit project no-commit policy. *Why:* "每个 task /
  每次 review 修复后提交" — local commits are reversible (so they fit the autonomous execution zone),
  while the irreversible outward act (push) stays gated, reconciling with the global commit rule.
- **Design weighs the hack / 补丁 / 推翻重来 spectrum + each cost.** `design.md`「Alternatives」and
  design-grill「方案优先」now require spanning the solution-class spectrum (quick hack · localized
  patch · proper redo) and naming each one's cost (工期/技术债/影响面/可维护性); a hack/patch is a
  conscious, recorded debt decision, and the "correct" full redo still must pass 简单可靠/反过度设计.
  *Why:* 方案优先 surfaced variants but not this debt-vs-correctness axis explicitly.

- **实现 carries two test modes (TDD vs test-after), picked per project.** Comparing the vendored
  sources surfaced a lossy fork: our `implement.md` cycle had dropped incremental-implementation's
  **Test** step (it read "Implement → Verify"), and the rich `test-driven-development` red-green +
  Prove-It content only half-existed in `test.md` — so the flow looked test-after while claiming
  TDD. Fix: `实现` now carries **both** cycles explicitly — **Cycle A (TDD: RED→GREEN→REFACTOR +
  Prove-It)** where tests run, **Cycle B (test-after: Implement→Test→Verify, defer the run)** for
  cbdb's "describe, don't run". Mode is chosen by the project's test-execution policy and recorded
  in `progress.md` (State at a glance). Both are vertical/per-slice — never all-code-then-all-tests.
  `测试` is reframed as the **consolidation** phase (close coverage by R-id + module interface, add
  integration / 跨 part 联调 / manual / E2E, balance the pyramid, run-or-describe, record results);
  the per-slice red-green loop now lives in `实现`, not here. Commit cadence reconciled with
  test-after (commit when runnable checks pass even if acceptance is `[ ]` pending the human's run).
  Provenance table updated (implement ← incremental-implementation + test-driven-development).
  *Why:* "实现按项目分:能跑测试走 TDD,cbdb 走 test-after" — and a faithful prep of both needed the
  vendor sources, which also revealed the dropped-Test-step bug.

- **Provenance corrected + refactor depth.** A comparison against the real standalone `tdd` skill
  showed our TDD-mode loop ≈ its loop (the difference is structural — planning is frozen upstream in
  需求/设计/详设, so our Cycle A is the loop without the `tdd` skill's Planning step). It also surfaced
  a mis-attribution from the prior entry: the red-green loop's primary source is **`tdd`** (the
  standalone skill), not `test-driven-development` — the latter contributed only **Prove-It / pyramid
  / sizes**. Fixed the provenance table + step headers (implement ← incremental-implementation + `tdd`
  + test-driven-development; test ← `tdd` + test-driven-development). Cycle A's REFACTOR step now
  names deepen-modules / SOLID and points at `codebase-design`; added a note that `use:tdd` overrides
  with its **loop only** (skip its Planning — the design phases own it).

- **Reference the `codebase-design` skill (deep modules) at four points.** design-grill: optional
  **Design-It-Twice** (parallel agents try radically different interfaces — the *interface-shape*
  axis, complementing the hack/补丁/重做 *solution-class* axis) + a **module-depth / deletion-test /
  two-adapter-seam** quality lens. test: pick the test strategy by **dependency category**
  (in-process / local-substitutable / remote-owned port+adapter / true-external mock). implement
  review lens: the **deletion test** (sharper than "remove no-ops"). `design.md`「Interface/contract」
  sources its seam/depth vocabulary (interface = all a caller must know; deep module; seam = Feathers)
  from it. **Referenced (link, don't restate), not vendored** — so it's listed under References, not
  the fork-provenance table. *Why:* `codebase-design` is complementary (module/interface-depth layer)
  and supplies concrete mechanisms our 方案优先 / testability guidance only gestured at.

- **Grilling factored into a shared `grill.md` with history + rollback.** The one-question
  elicitation protocol (duplicated in `requirement` + `design-grill`) is now a shared mechanism
  (`references/steps/grill.md`), adding a **grill-log** (append-only Q / recommended / chosen / why /
  depends-on / status — inline for small grills, `notes/grill-<phase>.md` for large or multi-session)
  and **rollback** (回退 to a previous question = mark it + its dependent subtree `superseded`,
  re-walk, reconcile the phase doc — reusing the `log.md` / ADR supersede discipline, not deleting
  history). `resume` can continue a grill mid-phase from the open `G<n>`. **No new verb / state
  machine**; sized to the grill; a drafting-phase rollback re-walks branches, but once `design.md` is
  frozen a change goes through M2, not a rollback. *Why:* grilling is a dependency-ordered
  decision-tree walk — a structured history + clean rollback matches that and survives resume, where
  before only the in-session chat held it. (Generic non-doc grilling can still `use:grill-me`.)

## Earlier

See `git log` (init + the split-and-isolate part-axis / kanban additions) — this curated changelog
starts at the 2026-06-27 enhancement batch.
