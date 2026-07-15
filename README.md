# xg-skills

Two [Claude Code](https://claude.com/claude-code) skill packages for grounding
substantive engineering work in durable, reusable knowledge. They are siblings:
the workflow *orchestrates* code work and links out to the knowledge base for
reusable module knowledge; the knowledge base never stores workflow state.

Each package is Markdown-driven — a `SKILL.md` contract plus on-demand
`references/` and a few dependency-free Python helpers. There is no build or
test pipeline; "running" a skill means Claude Code loading its `SKILL.md` and
following the procedure.

## Packages

### [`xg-dev-workflow/`](xg-dev-workflow/)

A design-centric development workflow. Gated phases —
requirement → design → detail → implement → test — plus a close-out review
gate, where **one requirement maps to one directory of docs** (a "card").

Verbs: `new`, `requirement`, `design`, `detail`, `plan`, `test`,
`investigate`, `review`, `change`, `resume`, `check`, `retro`.

Decision phases advance one gate per invocation and stop for human approval;
once execution is authorized, implementation and testing flow autonomously.

### [`xg-knowledge-lite/`](xg-knowledge-lite/)

A cross-project code-knowledge base with two layers (after Karpathy's
"two-layer" idea): `raw/<project>/*.md` investigation write-ups — the source of
truth — are compiled into `wiki/<project>/<concept>.md` concept articles.

Actions: Write, Compile, Query, Orient, Lint.

## Layout

```
<skill>/
  SKILL.md       # YAML frontmatter (name + description) + the procedure
  README.md      # per-package overview
  references/    # steps / templates / format specs — loaded on demand
  tools/         # Python helpers (stdlib; optional PyYAML with a text fallback)
```

## Install

Make each package discoverable to Claude Code as a skill — e.g. symlink the
directories into your personal skills location:

```sh
ln -s "$PWD/xg-dev-workflow"   ~/.claude/skills/xg-dev-workflow
ln -s "$PWD/xg-knowledge-lite" ~/.claude/skills/xg-knowledge-lite
```

Both skills share one config at `~/.config/xg-knowledge-wiki/config.yaml`
(knowledge-base root, workflow-docs root, and a project map); scripts never
auto-create it. All user data — notes, workflow docs, config — lives **outside**
this repo; the repo holds skill logic only.

## License

[MIT](LICENSE). Vendored third-party code (`marked`) retains its own license —
see [`xg-dev-workflow/tools/viewer/marked.LICENSE.md`](xg-dev-workflow/tools/viewer/marked.LICENSE.md).
