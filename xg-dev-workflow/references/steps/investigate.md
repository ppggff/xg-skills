# Step: investigate — the front door for any code-behavior question

"调查 X", "how does Y behave", a concurrency / runtime / feasibility question, an open question on a
card: it all routes here. Read-only on product code, never advances a card; the deliverable is an
evidence trail — recorded unless answer-only (step 3) — plus a **logical analysis**: grep and read
gather evidence, they are not the answer. Two disciplines compose: the evidence rule below and
concept-first understanding.

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

## Independent run — an investigator who has not seen what we believe

Only on the human's 「独立调查」; you may suggest it once (a KB conclusion in doubt, candidates to compare), never
start it. It runs in an evolving dir (Procedure step 3; on an active card, in the card's `notes/`, conclusions into
「待解问题与证据」).
1. Write `problem.md` and self-check it — no candidate, no conclusion, no KB wording or slug, no card / Req id;
   show it with the ref, the code mode (item 2 below; the human may switch it) and the paths (default: the whole repo)
   and wait — the run's one stop. `problem.md` names the code locations the run will see.
2. `git archive <ref> [<paths>] | tar -x -C <new temp dir>` — no `.git`, outside the `projects:` map; delete every
   `CLAUDE.md`, `AGENTS.md` and `.claude/` in the snapshot (`find <dir> \( -name CLAUDE.md -o -name AGENTS.md -o
   -name .claude \) -prune -exec rm -rf {} +` — a nested `CLAUDE.md` loads once its dir is read; `.claude/` holds the
   hooks, skills and settings that `project,local` keeps) and the design docs. **Live repos** instead — the default
   when no repo's `git status` shows uncommitted work on the topic and its `CLAUDE.md` / `AGENTS.md` say nothing on
   it (a Grep still reads them):
   run in a new empty dir, each repo root its own `--add-dir` (a symlink resolves outside the dir and is denied;
   pass the paths one by one — zsh does not split a variable), and deny per repo by absolute path `CLAUDE.md` ·
   `**/CLAUDE.md` · `AGENTS.md` · `**/AGENTS.md` · `.claude/**` · `**/.claude/**` · `.git/**`, plus `Bash(git:*)` —
   a relative `**/` rule does not reach an added dir.
3. There: `claude -p --model <model> --effort <effort> --setting-sources project,local
   --strict-mcp-config --disallowedTools "ListAgents,SendMessage"
   --settings '{"autoMemoryEnabled":false,"permissions":{"deny":["Read(//<KB root>/**)","Read(//<dev_root>/**)"]}}'
   [--add-dir <repo root>…] -- "<task line> <the full text of problem.md>" < /dev/null` — the `--` keeps the variadic `--add-dir`
   from swallowing the prompt; the task line only asks to analyse against the code given, cite
   `func()` in `file` per claim, mark what could not be verified, report in Chinese. Never add
   `--dangerously-skip-permissions` or `--permission-mode bypassPermissions`, nor an `--add-dir` beyond the live
   repo roots: `-p`'s default permissions do the isolating. `--bare` needs an API key and a subagent carries the
   global CLAUDE.md — neither substitutes. `--setting-sources` also skips the user settings that hold the model
   and effort, so both are passed, and both are what the KB-informed run (item 5) gets — the session model capped
   at opus (SKILL.md「Subagents」) and the session effort: left to defaults the run drops to medium, and a fable
   session's run at fable against a subagent at opus confounds the comparison the same way.
4. Save the output as `analysis-independent-<date>.md`, headed by ref · paths · deleted files (live: each repo's
   HEAD and dirty state, the deny set) · the full command (task line included).
5. By default, run the KB-informed investigation on the same `problem.md` (`analysis-skill-<date>.md`). A subagent cannot
   write a report file: have it return the analysis as text and save it verbatim, headed by its model, effort and
   the paths it read — it stays off the independent output only on the prompt's word, so check those paths in its
   transcript. List the disagreements in `current.md` (on a card: 「待解问题与证据」) and settle each in the code —
   into `facts.md` or an open question; they are the run's output.
6. Its conclusions are claims to test until checked in the code. Limits: comments still carry old conclusions;
   the isolation is missing pointers plus a read deny, not a sandbox; the run cannot execute scripts (no spikes).

## Procedure

1. **KB first** — an xg-knowledge-lite Orient pass (project section of `wiki/index.md` · `CONTEXT-MAP.md`
   · uncompiled-raw count), then Query the relevant concepts and drill into their raw sources; don't
   re-investigate what is recorded. Orient is this run's warm-up, not a separate log record. Skipped only
   on the human's word (「别查 KB」), never on your own — whether the KB covers the question is unknown until
   you look; the reply says 「调查未参考 KB（你要求）」, the conclusions cite only code, tests or runs, and any KB
   write from this run, now or later, first runs a Query on its topic and says so.
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
     concept); notes to `<dev_root>/<project>/investigations/<topic>.md` (no prefix — the dir says it),
     **never into the repo**. Log `--action investigate`.
   - **Evolving dir（演进目录）** — a doc set whose current conclusion can always be regenerated from the rest;
     ordinary and independent runs share it. A multi-phase campaign, a topic discussed past one round, or a
     second analysis graduates the note to `investigations/<topic>/`, one file per role: the problem
     (`problem.md` — state · goals · constraints, no solution or conclusion, readable without background) ·
     facts (`facts.md` — evidence-cited, each with its verification mark; a correction strikes and says why) · the
     human's messages (`human-messages.md`, verbatim and dated, as on a card) · analyses (`analysis-<source>-<date>.md`,
     `-2` on a same-day repeat — skill · independent · an external model — headed by source and evidence mode,
     appended while its run lasts, frozen once it ends; a phase is a run) · the current conclusion
     (`current.md`, present tense, rewritten freely; when messy, regenerate it from the other four — list the
     semantic points first, tick them off after). Commit dev_root at each round's end. A card holds the same
     roles (design.md summary and goals · `facts.md` · `notes/human-messages.md` · `notes/` · 当前方案);
     opening one from this dir: `discuss.md` §2.
   - **Answer-only** (standalone only) — on the human's word (「不用记」), or your call on a single unphased
     question whose answer is a one-off lookup (where X is defined, a default) or already in the KB with
     nothing to add (not open when the KB was skipped); a conclusion that needed a claims table or a causal
     chain is never a lookup — unsure → record. No notes, no KB write; still log `--action investigate`
     with `answer-only` in the note; a later 「记下来」 records through the Standalone branch, no second record.
4. **Large question → phases.** Name the phases up front (e.g. 1 registration sites · 2 execution context
   · 3 lock path); after each, append its claims table + verdict-so-far + open items to the notes file (in an
   evolving dir, the phase's analysis file), say so in the message that starts the next phase, and go on. **Pause
   for the human** only when a verdict adds, drops or rescopes a named phase, the next phase needs what only the
   human knows, or the first recording is torn on anchoring (step 3); never pre-conclude a later phase. A single
   question skips the phasing. On the human's 「不用记」 the phase notes are still written — they carry progress
   across a context summary; only the KB write is skipped, and the closing reply says so.
5. **Receipts — write first, then reply**: the closing reply (or a phase pause) names the notes / KB paths
   and the dev_root / KB commit; an answer with no named artifact means the recording step was skipped —
   unless it ends with 「未落盘（原因）；要记就说『记下来』」 (answer-only, step 3).

A finding in a notes file is a **field block** — stable labels 现象 · 规范 (or 机理) · 改法 (or 结论), each a label
line with free-form indented content; a further field only for an independent point (`conventions-core.md`「Form」).
Citation forms in docs: code `` `TpFrozenShmemGetMin()` in `appserver.c` `` · knowledge
`[[wiki/cbdb/appserver-epoch-shmem]]` · external: full URL with anchor + a one-line quote for a non-obvious
decision. A verified load-bearing fact persists as `Fact-n` (card) or in the note's 事实清单.
