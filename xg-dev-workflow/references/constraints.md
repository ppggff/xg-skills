# Constraints — the closed list of hard rules a lite card obeys

Every row is **script-checkable (S: which check / tool)** or **checkable by a reader without judgment
(H)**; anything that needs judgment is flow (`steps/lite.md` · `discuss.md`) or the model's call
(SKILL.md「自主区」). Rows are cited by id (`[Lay-2]`) and the lite checks' `--manifest` 依据 column
points at them. Shared writing rules stay in the synced `conventions-core.md` (style · first-use gloss ·
provenance three-class · negative statements · tables vs prose · diagrams · wikilinks) and
`diagram-gotchas.md`; 存量 cards follow `references/legacy/SKILL.md`「Layout / Conventions / Versioning」.

## Layout (Lay)

```
<dev_root>/<project>/            # == the xg-knowledge-lite project name; dev_root from config
  index.md                       # board: | Card | Phase | 整体状态 | Deps | Dir |
  roadmap.md · investigations/ · reviews/ · notes/ · legacy/ (pre-workflow archive, never canonical)
  NNN-slug/design.md             # the working draft; frontmatter `governance: lite`, `status:` is the truth
  NNN-slug/{facts.md, adr/, plan.md, progress.md, log.md, notes/}   # only when content appears
```
- Lay-1 (S: v, u) — the project root holds only the files above; every board row has a card dir and every card dir a row.
- Lay-2 (S: p, ai) — `design.md` frontmatter: `governance: lite` · `status` ∈ draft · executing · closing · done (no inline
  comment on the value); when `requirement.md` also carries `governance`, the two agree (requirement.md wins).
- Lay-3 (H) — other card files exist only once their content appears, never as empty containers; `notes/human-messages.md`
  holds the human's messages verbatim, one line each, appended as they arrive.
- Lay-4 (S: ah, w, u) — board row `| NNN | lite | todo·active·done·dropped | — | [NNN-slug](./NNN-slug/) |`; 整体状态 follows
  `status` (draft→todo · executing/closing→active · done→done; dropped is row-only) and never moves backwards.
- Lay-5 (S: s) — `progress.md` of an active card stays under the line cap.
- Lay-6 (S: o) — every markdown link and `[[wiki/<project>/<slug>]]` wikilink in the card and the project files resolves.

## Ids and citation (Id)

- Id-1 (H) — a lite card uses `NNN` (card) · `Req-n` · `Fact-n` · `Inv-n` · `ADR-NNNN` · `Task-n` (with plan.md), and nothing
  else; case-sensitive, no zero-padding except `NNN` / `NNNN`; a clause is the line-leading `- (x) ` marker, cited `[Req-12-a]`.
- Id-2 (H) — two forms: the definition site is bare (the structural position anchors it), a prose citation is bracketed `[Req-1]`;
  an id cited from another file links to its home (`[ADR-0001](./adr/0001-slug.md)`) at first mention, bare afterwards.
- Id-3 (H) — `Fact-n` lives in the card's `facts.md` (one container per card; docs cite `[Fact-n]`); a standalone note keeps a
  doc-local 事实清单 instead — never both.

## Doc form (Doc)

- Doc-1 (H) — `[x]` anywhere means 已验证 and nothing else; a Req 状态词 ∈ 待验证 · 已验证 · 验证失败 · 阻塞 · 仅方案 · 放弃.
- Doc-2 (H) — a load-bearing claim carries evidence-cited / 推断 / 假设; a `Fact-n` is `[VERIFIED]` only with a source line; a
  negative result names its query and scope; unverified never turns into a negative conclusion.
- Doc-3 (H) — a table cell or single-line field holds one plain self-contained sentence (ids as gloss); the full text lives at
  the content's home — a block field's indented continuation (two spaces) or prose in the same section, never the cell.
- Doc-4 (H) — a `### Req-n <状态词>` block has 陈述 (free-form) · 验证 · 来源 lines; 变更 whenever the commitment changes;
  确认 at go and every re-confirmation; the 验证 line names method · outcome · evidence pointer (commit SHAs included —
  product, or dev_root for a docs-only card).
- Doc-5 (H) — prose states the present; history is git plus the 变更 lines; full content has one home and a summary is
  self-contained; an enumeration cites its owner, never restates the count.
- Doc-6 (H) — diagrams are Mermaid (`diagram-gotchas.md`); KB references keep the wikilink form (load-bearing for recompile).
- Doc-7 (H) — a Task deleted / merged / deferred, or a `[x]` invalidated, leaves a one-line note (plan.md or a 变更 line) — never a silent edit.

## ADRs (Adr)

- Adr-1 (H) — an ADR only when all three hold: hard to reverse · surprising without context · a real trade-off; a paragraph is a
  valid ADR (`templates/adr.md`); `adr/NNNN-slug.md` numbered per card, the dir created at the first ADR.
- Adr-2 (H) — Status ∈ proposed · accepted · superseded by ADR-NNNN · deprecated, kept by hand on a lite card; a changed decision
  is a **new** ADR with `## Supersedes ADR-NNNN`, the old one gets a ≤2-line forward pointer — never an amendment block.

## Go (Go)

- Go-1 (H) — go is the word, or a reply that settles every 待你判 item and raises no new question; the 授权记录 line names that
  reply, `status: executing`, `go: <dev_root commit>` and each covered block's 确认 line are written, then committed.
- Go-2 (H) — a partial go names the Req ids it covers; a commitment changes only through a 待确认 proposal the human confirms,
  written as a 变更 line — the old commitment stands meanwhile.
- Go-3 (H) — cross-card supersede: the superseding card writes one `- 退役:` line under the superseded item, `(<its go commit>, date)`;
  on a 存量 card through `commit-data-repos.py --allow-approved-edit`.

## Operations (Ops) — never covered by a go on tasks

- Ops-1 (H) — destructive operations on shared or live environments · publish · push · range deletes / truncate / schema /
  cluster-level writes: verify scope, target-version behavior and restore conditions first; without authorization, present
  reviewable information and wait. A file-scope check is not operation permission.
- Ops-2 (H) — commit pending work before anything that rewrites the worktree (`reset --hard` · `checkout --` · `clean`; probe a
  non-fast-forward with `reset --soft`); while a background job runs, edit only files it never reads.
- Ops-3 (H) — spikes stay within standing permissions, local and reversible.

## Product commits (Git)

- Git-1 (H) — `<scope>: <what>`, one concern each, English, **no card or Req tail**; the mapping runs the other way — a Req 验证
  line or a plan.md row names the SHAs. Product code and dev_root docs are two commits, never one.
- Git-2 (S: check-code-refs.py) — code and comments never point into dev_root or the KB: no `dev_root` / `~/knowledge` paths,
  `[[wiki]]` links, `ADR-NNNN`, private `*.md` names or `file:line`; run the checker on the diff before finishing.

## Versioning the docs (Ver) — dev_root is its own git repo

- Ver-1 (S: commit-data-repos.py) — lazily initialized on the first commit; never a submodule of the product repo.
- Ver-2 (H) — commit at each doc boundary (a verb finishing its writes · go · a task landing · a note), `check` first; message
  `<project>/NNN-slug: <verb> — <one line>`.
- Ver-3 (S: commit-data-repos.py --card) — a card commit is scoped `--card <project>/<NNN>` (its dir + the project's index /
  roadmap); `--project <name>` for project-level writes; a parallel session's uncommitted docs never ride along.
- Ver-4 (H) — autonomous local commit; `push` stays human-gated; history is append-only (no amend / rebase / squash).

## Config and project resolution (Cfg) — shared with xg-knowledge-lite

- Cfg-1 (S: resolve-project.py) — one config, `~/.config/xg-knowledge-wiki/config.yaml`: `dev_root:` (order `--root` · config ·
  `~/dev-workflow`) and the `projects:` map both skills read; never auto-created.
- Cfg-2 (H) — cwd → project via `tools/resolve-project.py`; on a miss ask once and register with xg-knowledge-lite's
  `register-project.py`; never auto-pick `common`.

## KB boundary (KB)

- KB-1 (H) — reusable module knowledge lands in xg-knowledge-lite (`~/knowledge` raw/wiki), cited via `[[wiki/<project>/<slug>]]`;
  workflow docs → KB is one-way, the KB never links back into dev_root.

## Usage logging (Log)

- Log-1 (S: log-usage.py) — per `~/.claude/CLAUDE.md`「Skill Usage Logging」: `--action` is the verb just run (vocabulary
  `KNOWN_ACTIONS`); a lite card logs `--action lite` once per event (open · go · close-out); one event = one record.

## Synced files (Sync)

- Sync-1 (S: check-sync.py) — `tools/sync-manifest.txt` declares the byte-identical sets (conventions-core · diagram-gotchas ·
  ask-routing-core · resolve-project · log-usage); edit one copy, `cp` to the others, exit 1 on drift.

## Caps (Cap) — anti-ratchet, re-measured by `retro`

- Cap-1 (S: wc -l) — SKILL.md ≤120 · `steps/lite.md` ≤150 · `steps/discuss.md` ≤100 · this file ≤120 · 流程 = `steps/` minus
  `retro.md`: ≤8 files, ≤900 lines in all · `templates/` 6 files ≤250 · lenses ≤200 (one or two files) · `steps/retro.md` (元) ≤100.
