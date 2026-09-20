---
name: xg-codemap
description: "Shared intent map between a human and a coding agent: the agent draws what the software is (nodes with evidence anchors, verified vs inferred claims), the human marks what it should become (intents with acceptance predicates). Use when asked to map a change or a module as a diagram ('画变更图' / 'map this change' / '画结构图' / 'map this module' / 'codemap'), to explain a scattered set of commits visually, to drill a map down a level ('展开这个节点' / 'expand this node'), or to answer a comment anchored on a map node."
---

# xg-codemap

A **codemap** is a map the agent and the human share about one piece of software: the agent describes,
with evidence, what the software *is* (Current); the human uses the same map to say what it *should
become* (Desired). The model is `references/standard.md` (v0, seven frozen elements plus the subject).
This file is the drawing procedure. Version 0 is hand-drawn: Markdown plus Mermaid, no tooling.

## What you are drawing

Three layers, kept apart in the note:
- **Observed** — nodes and edges that exist in the code at the pinned revision, each with one or more
  anchors (symbol path, commit, file, package) and claims marked `verified` (you read it) or `inferred`.
- **Intent** — what the change is meant to achieve: the host's requirement items (the host supplies their
  ids and wording) or the human's own marks, each with an acceptance predicate when one is stated.
- **Presentation** — the diagrams: one diagram answers one question; the top level is intent, not the
  file tree; expansions go one level down per diagram.

Semantic abstraction is yours: you decide what a box is, what is folded into it and what is left out.
Facts are not yours to decide: every element in scope is accounted for, every edge you draw you read.

## Procedure — a change map (the v0 archetype)

1. **Pin the subject.** Frontmatter: `standard: v0` · `repo` · `base` and `head` SHAs (or one `sha` for a
   structure map) · `scope` with its kind (`change:BASE..HEAD` · `pkg:` · `file:` · `sym:` · `commits:`) ·
   `kind: complete` or `sketch`. A sketch never claims completeness.
2. **Enumerate before drawing.** List every element in scope with its size: for a change, every changed
   symbol per commit (`git log --stat`, `git diff -U0 BASE..HEAD`, then read the hunks to name the
   symbols); for a module, every top-level symbol. The list goes into the note's accounting section as
   written — it is the universe the map is measured against.
3. **Assign every element one of three fates**: **drawn** (a node), **folded** (inside a named node;
   say which), **elided** (an explicit "omitted: N items — reason" bucket). Zero elements unaccounted;
   an element both drawn and elided is a conflict. Edges are not required complete, but a drawn node
   states how many of its true in/out edges are shown when you know the count.
4. **Observed layer.** Node id = a stable logical slug you name (`judge`, `sampling-chain`), never an
   auto letter; anchors = the symbol paths / commits it stands for (a node may carry several). Each
   claim (exists · size · call or dependency edge · tests touching it · a structural judgment) is
   `verified` with its provenance (commit SHA, file read) or `inferred`. Draw no edge you have not read.
5. **Intent layer.** Top-level nodes are the requirement items the change serves, in the host's ids and
   words, with the acceptance wording attached. Every changed node hangs under one. Changed code that
   serves no item is listed as *unaccounted* — candidate creep or a missing item — never silently folded.
6. **Presentation.** One Mermaid diagram per question: the top diagram (items → changed nodes), then one
   expansion per item or subsystem. **Under each diagram's heading, one line names its kind, the question
   it answers and what an edge means** (`图类型 · 回答 · 边`); a change map's diagrams are structure /
   dependency diagrams, never control-flow, and the reader is told so up front. **Keep a diagram legible**:
   about 15 nodes at most, labels of one or two short lines (name · size · test count), `direction TB` inside
   subgraphs so groups stack instead of spreading; when a diagram would exceed that, split it by group and
   move the type names and details into a table beside it. Markers ride the label as text tags:
   `[+test]` a test changed with it · `[no-test]` code changed, no test changed · `[new]` · `[removed]` ·
   `[moved]`. After each diagram: a short prose block — traps, decisions, what is folded, what is elided.
   List the **blast radius** (callers of changed nodes at `head`, one level) as a table, not a diagram.
7. **Honesty lines.** Date the note, keep the SHAs in the frontmatter, mark anything measured (`实测`)
   apart from anything read. When the code moves, the note stays true to its SHAs and says so.

## Handling comments on the map

A reviewer's comment arrives anchored (`[<tree>:<path>#<heading>]` plus a quoted excerpt, or a node id).
Resolve heading → diagram → node → anchors; answer citing the node id and the code at `head`. A comment
that exposes a wrong or missing claim fixes the map first (a dated change line under the diagram), then
answers. A comment that expresses a wish ("this part needs tests") is an intent: record it under the
Intent layer with the acceptance wording the human gives, do not act on it inside the map.

## Boundaries

This skill knows nothing about where notes live or how work is governed: the host tells you the output
path and the requirement ids. It never writes into the repository it maps. It reads no shared
configuration. Rendering, checking and interactive surfaces are later stages; v0 is the note itself.

## Usage log

After a map is drawn or a comment round answered, append one record with the user-side script per the
global convention: `python3 ~/.claude/scripts/log-usage.py log --skill xg-codemap --action <map|answer>
--score <1-5> --note "<one sentence>"`.
