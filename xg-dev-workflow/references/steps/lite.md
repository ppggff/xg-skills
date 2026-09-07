# Step: lite (trial governance mode — one draft, one go, continuous execution)

Trial path. A card whose `design.md` frontmatter says `governance: lite` follows this file
**exclusively** — SKILL.md's Stop-at-gate rule, Two zones, Ledger, five phases, M2/M3 and phase
verbs do not apply. Shared: project resolution, dev_root versioning (`commit-data-repos.py
--card`), usage logging, the read-only verbs (`investigate` / `diagnose` / `review` / `improve` /
`learn`), the M1 evidence discipline (`evidence.md`) and the KB boundary. Tooling is a stub:
`--check` on a lite card runs links · status-field · progress-cap and books one exemption; the
board reads `governance: lite` but its phase steps / Next line are five-phase artifacts —
design.md `status:` is the truth; `--trace` does not apply. Caps (anti-ratchet): this file ≤150
lines, SKILL.md「Lite route」≤40 lines; retro records both.

## Model

One continuously updated working draft; explicitly confirmed goals and boundaries
(**commitments**); one execution authorization (**go**); verification evidence matching the
current change. Requirement / design / detail are angles of thought, not gated phases. Understand
⇄ investigate ⇄ compare ⇄ negotiate is the normal loop before go and continues after it inside
the authorization; only three kinds of change come back to the human (see「Executing」).

- **Commitment** = a goal, constraint or acceptance condition the human explicitly asked for or
  confirmed and still in force, plus the project's standing constraints (CLAUDE.md, KB
  invariants). Who said it first is irrelevant: a musing is not a commitment until confirmed; a
  confirmed Claude proposal is one and Claude cannot withdraw it alone. Not copied into the doc ≠
  authorization to drop it — backfill, say so, and keep backfilling distinct from a new ask.
- **Impact forecast ≠ authorization boundary.** Expected modules/files/tests are a forecast that
  moves with investigation — no pause when it grows. Hard boundaries exist only when the human
  set them, and are marked as the human's.

## Card files

Start from `design.md`; create the others when their content appears, never as empty containers:
`progress.md` (park / handoff / long-task resume: now · next · blockers · build & verify entry) ·
`facts.md` (many load-bearing or re-cited facts: fact · evidence · scope · M1 confidence) · `adr/`
(a trade-off worth keeping the reason for; `templates/adr.md`) · `plan.md` (the task list crowds
the approach) · `log.md` (revision history outgrows the doc) · `notes/` (long output, spikes,
review reports). Full content has one home; a summary is self-contained; prose states the
present — history is git plus the 变更 lines, never stacked contradicting paragraphs.

## Open a card (manual — do not run `new`; it scaffolds a doc-native requirement.md)

1. Next `NNN`: scan `<dev_root>/<project>/`, increment.
2. `mkdir <dev_root>/<project>/NNN-slug/`, write `design.md` from the skeleton below.
3. Board row in `index.md`: `| NNN | lite | todo | — | [NNN-slug](./NNN-slug/) |`. The 整体状态
   column takes only the canonical words: `todo` while drafting, `active` from go to close-out,
   `done` / `dropped` at the end. Lite's own `status:` lives in design.md only.

## design.md skeleton

```markdown
---
id: NNN
title: <slug>
project: <project>
governance: lite
status: draft          # draft | executing | closing | done — checks read `status`, not `state`
created: YYYY-MM-DD
go:                    # at go: the dev_root commit (tag optional) of the authorization baseline
---
# NNN <title>

## 当前摘要        problem · intended approach · key limits · unresolved risks (top; ≤200 字 when long)
## 目标与边界      deliver what · not what · the commitment blocks (index table optional, >5 blocks)
### Req-1 待验证 — <标题>
- 陈述: <goal / constraint / acceptance; (a)(b) clauses and an `alt:` line allowed>
- 验证: <how> → <actual result + evidence: command / output excerpt / notes link; code version>
- why / 来源: only when it aids understanding or traceability
- 变更: <date> <what changed, why>          ← mandatory whenever a commitment changes
- 确认: <date> 「<human's words or paraphrase>」 <commit>   ← go and every re-confirmation
## 当前方案        path · impact forecast · contracts · trade-offs · feasibility evidence
## 待解问题与证据  still to check · found so far (long material → facts.md / notes/)
## 任务与验证      next steps · results · remaining work (→ plan.md when it crowds the doc)
## 授权记录        one line per go / re-confirmation: date · Req ids · scope & not-in-scope · quote · commit
```

Req status words: `待验证 · 已验证 · 验证失败 · 阻塞 · 仅方案 · 放弃`. `[x]` anywhere means 已验证
and nothing else. Auxiliary tests and regressions list under 任务与验证 without becoming
commitments; diagrams, code-level interfaces and candidate comparisons only when they help.

## Drafting (before go)

Explore, investigate (`investigate.md`, M1), compare, negotiate — freely; the doc is a draft.
Spikes are allowed within the host's and project's standing permissions, local and reversible; a
spike result is not a deliverable. "Enough basis" for go: key feasibility rests on code, a
derivation or a spike; thin evidence is stated as such; an open question that could sink the
approach gets a bounded investigation or narrows the ask — never "risk noted, start anyway".
Claude compiles the commitment blocks for confirmation.

## The go ask (one message, receipts first)

Commit the card (`commit-data-repos.py --card <project>/<NNN>`), then ask with: 摘要 · the
commitment list (Req ids, one line each) · scope and not-in-scope · impact forecast (labelled as
forecast) · risks and where evidence is thin · what the authorization includes and excludes · the
已验证 / 待你判 split (`gate-digest.md`「判断分工」). A partial go is legal: name the Req ids
covered; the rest stay below as「讨论中」. On the human's `go` (or an equally explicit equivalent):
write the 授权记录 line and each covered block's `确认:` line, set `status: executing` and `go:`,
commit again (tag `<project>/<NNN>/go` optional — a snapshot pointer, not the approval itself).

## Executing (after go)

Stay in this session by default; switch when context is long, work is interrupted, or a handoff
is being tested. Usually just continue — change approach, add tests, reorder tasks, trace call
chains, fix review findings, correct the forecast, update prose and evidence — while the
commitments hold and operations stay inside the authorization. A material approach change gets
one line of reason; not every edit. **A→B walk**: find A's problem → does B still meet the
commitments? → rewrite 当前方案 → one reason line → re-verify what B touches → sync facts / ADR /
diagrams if present. If B cannot meet a commitment → propose and pause the dependent work.

**Come back to the human only for** (1) changing a goal, weakening acceptance, dropping a
deliverable, or changing an explicit constraint or boundary; (2) work or a major trade-off beyond
the authorization (e.g. a new long-running service) — "not forbidden" is not authorization;
(3) an operation needing its own authorization not yet given. Ask form: what was found · which
commitment is affected · proposed change; the doc carries it as a 待确认 proposal, the old
commitment stands until approved, only dependent work pauses. Clarifications and blockers are not
approvals: investigate what code can answer, ask promptly for what only the human knows.

**Operation carve-outs**: destructive operations on shared/live environments, publish, push,
range deletes / truncate / schema / cluster-level writes — verify actual scope, target-version
behavior and restore conditions first; without authorization present reviewable information and
wait. A go on tasks never covers these; an authorization already given is not re-asked.
File-scope checks are not operation permission.

**Park / resume**: park = `progress.md` to the resume floor (now · next · blockers · build/verify
entry) + commit; resume = `progress.md` (if present) → design.md 摘要 → 承诺 → 当前方案 → evidence
and code as needed; reading scope is unrestricted — the summary is the entry, not the contract.

## Verification and close-out

A result names the object, method, actual outcome and code version / environment. A test name is
not a run; a link is not support. When code, approach or environment changes, re-judge old
evidence; stale → 待重验 with reason. Refuted (counter-example) and unverified (thin evidence)
stay distinct — the latter is never written as a negative conclusion (M1). Review depth follows
impact, reversibility, invariants and verifiability, not task size; a fresh-context agent that
attacks load-bearing facts or checks code against commitments is optional and never replaces a run.

Close-out: per commitment — met / scope of the result / unverified / residual risk. A task that
promised only a plan or static analysis may close on that, never claiming runtime verification; a
promised run that cannot happen is a blocker or a negotiated cut, never a self-declared done. Then
`status: done`, board row `done`, KB triage (correct reusable wrong conclusions; not every card
yields KB), the usage log (`log-usage.py log --skill xg-dev-workflow --action lite …`; a second
record when the human's verdict lands) and the **observation note** (five lines under 授权记录 or
in `notes/`): places synced per ordinary change · needless interruptions and why ·
doc-maintenance time and lines read at go · missed commitments / unauthorized changes /
verification gaps · handoff gaps and correction rounds. Asking about a real doc gap is not a failure.

## Replay probes (once per trial card; a replay is labelled as one)

- **P1 ordinary approach change** — a finding invalidates a step → A→B walk, one reason line, no ask, affected 已验证 → 待重验.
- **P2 commitment change** — B cannot meet Req-n → 待确认 proposal, three-part ask, dependent work paused, the rest continues.
- **P3 missing information** — only the human knows X → prompt question, no silent narrowing of acceptance, gap recorded.
