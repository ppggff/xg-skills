# xg-knowledge-lite

A lean, project-organized code-knowledge base skill for Claude Code, with two layers (Karpathy-style): **raw** investigation write-ups that Claude authors, and **wiki concept articles** synthesized from them. Claude writes raw and compiles concepts; the human queries — answers cite concepts and fall back to grep over raw.

Adapted from [karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki) (MIT). Kept: *the LLM writes and maintains the wiki; the human reads and asks*, and the **raw → (compile) → concept** two-layer model. Changed: organized by **project** (not topic), raw is **Claude-generated from investigation** (not ingested from the web), search adds a **grep fallback**.

## Layout

```
$KB/                          # default ~/knowledge (config: ~/.config/xg-knowledge-wiki/config.yaml)
  raw/
    <project>/*.md            # raw: Claude's investigation write-ups (source of truth), format per FORMAT.md
    common/*.md
  wiki/                       # derived: concepts synthesized from raw
    <project>/<concept>.md    # one concept article (format per references/concept-template.md)
    index.md                  # index of concept articles (one row each)
    log.md                    # append-only operation log
  FORMAT.md                   # raw article format spec
```

The key distinction: **raw = "what I learned in investigation X" (may mix concepts); a concept = "everything we know about concept Y, synthesized across investigations."** Concepts are extracted from raw, never hand-authored.

**Git-managed:** `$KB` is its **own git repo** — lazily `git init`'d on first commit, then an autonomous **local** commit after each Write / Compile / Lint (push stays manual). `architecture` + `*-invariants` ledgers are first-class **curated** docs (sibling to `CONTEXT-MAP.md`), surfaced first by Orient.

**Compile-backlog push:** `tools/kb-backlog.py` lists, per project, raw not yet compiled to a concept (quiet when clean, always exits 0). Wire it as a Claude Code **SessionStart hook** so the backlog is surfaced every session — in `settings.json`:

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python3 <path-to-skill>/tools/kb-backlog.py"}]}]}}
```

A deliberately deferred raw is marked as such in its frontmatter (`compiled_to: deferred`; semantics in FORMAT.md), and the script then stops flagging it.

## Actions

- **Write** — record raw from investigation (or update it), then run Compile scoped to the concept(s) that raw touches.
- **Compile** — the single routine that synthesizes concepts from raw, incrementally (re-synthesize only the in-scope concepts + cascade to materially-affected same-project neighbors). Called scoped by Write, or batch (standalone) to bootstrap from a pile of raw / repair drift. No full rebuild, no hash stamp.
- **Query** — read concept articles → cite + drill into their Sources raw; grep raw as fallback.
- **Lint** — raw↔concept coverage, index consistency, dangling wikilinks, frontmatter (deterministic findings auto-fixed; judgment findings report-only).

See `SKILL.md` for the full workflow, `references/FORMAT.md` (raw) and `references/concept-template.md` (concept) for formats.

## Deliberately out of scope

Glossary, link graph, changes timeline, compile-stamp / hash-based drift tracking, similarity probe, heavy cascade, external-source ingestion, slash commands. If you need those, use the full `xg-knowledge-wiki`.

## License

[MIT](LICENSE) — inherits karpathy-llm-wiki's license.
