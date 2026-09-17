# codemap standard — v0

The model a codemap conforms to. Version 0 freezes **seven elements plus the subject**; everything else is
framework and may change without invalidating an existing map. The test for admission: an element is in
the standard only if changing it would make existing maps, comments or checkers wrong.

## Frozen

### 1. Semantic abstraction belongs to the agent

The agent decides what a node is, what is folded into it, what is elided and which question each
diagram answers. Tools own facts, verification and mechanical views (call graphs, blast radius,
coverage graphs); a mechanical view never decides what is worth seeing now.
*Changing this* would make every hand-composed diagram non-conforming.

### 2. Observed / Intent / Presentation are separate layers

- **Observed**: assertions about the software at a pinned revision — nodes, edges, anchors, claims.
- **Intent**: what the human (or the agent on the human's behalf) wants — planned nodes or edges,
  requests on a selection of nodes, each with an acceptance predicate.
- **Presentation**: diagrams and overlays that reference nodes of the other two layers.
An intended thing and an existing thing never share a lifecycle. Presentation-only elements
(decision diamonds, notes) are not accounted (element 7).
*Changing this* would merge planned and real nodes and break every intent record.

### 3. Node identity is separate from anchors

A node's **id** is its stable logical identity inside the map (a slug the agent names). Its **anchors**
are zero or more evidence pointers into reality: `sym:<language-specific symbol path>` ·
`commit:<sha>` · `file:<path>` · `pkg:<path>` (set-valued; facts aggregate) · `hunk:<file>@<range>` ·
further types by plugin. Observed nodes carry at least one anchor; a planned node carries none until it
is satisfied; a semantic node may carry several. Comments and intents bind to the id, never to an anchor.
*Changing this* would orphan every comment on a renamed or split symbol.

### 4. Claims carry provenance and one of four states

A claim is one assertion in the Observed layer — a node exists, its size, an edge `(from, to, kind)`, the
tests touching it, coverage, a structural judgment. Edges are claims. States: **verified** (a resolver or
a reader checked it at the pinned revision) · **inferred** (asserted without checking) · **unresolved**
(wanted to check, could not) · **stale** (was verified, fails against the current head). Every claim
records where it came from (resolver and revision, or reader, or human).
*Changing this* would make verified and inferred indistinguishable, which is the trust problem the map
exists to solve.

### 5. Hierarchy with any node as a root

One diagram per level; a node may point at the diagram that expands it; the child diagram's universe is
the parent node's set. The **subject** of a map is the root node it starts from: a package, a file, a
function, a range of commits, or a change between two revisions. Subject = `(kind, scope, base?, head)`.
The universe's element type is defined per kind (package/file → top-level symbols · function → exits,
branches, callees · commits → commits · change → hunks or changed symbols); the accounting rule
(element 7) does not depend on the kind.
*Changing this* would break expansion links and make maps of different subjects non-comparable.

### 6. Selection + intent, three operations

The closed set of model operations a human performs on a map: **add** a planned node or edge ·
**expand** a node · **attach an intent** to a selection of nodes. A selection (click, box, predicate)
always reduces to a set of node ids; coordinates are never stored. The verb vocabulary of intents is
open.
*Changing this* would invalidate stored intent records.

### 7. Acceptance predicate

An intent = a target (which nodes, or what to add) + an **acceptance predicate** over Observed-layer facts
+ free text. States: **planned** → **satisfied** (a check finds the predicate true) · **abandoned** ·
**superseded** (replaced by another intent, link kept). "Build this module" (its anchor resolves),
"add tests here" (coverage ≥ x, or every exported function has a test), "cherry-pick these" (every
commit is on the target branch) and "cut this dependency" (an edge is gone) are one construct. A map
therefore states not only structure but when a change counts as done.
*Changing this* would break the only mechanism that closes the loop from Desired back to Current.

### Completeness accounting (the checker's half of the standard)

A `complete` map declares a `scope`; the universe is enumerated at the pinned revision; every element is
**drawn**, **folded** (into a set-anchored node; facts aggregate) or **elided** (an explicit record with
reason and count, rendered as an expandable bucket that still carries aggregated facts). Identity:
`universe − (drawn ∪ folded ∪ elided) = ∅`; double assignment is a conflict; an anchor outside the
universe is `unresolved`. Applies recursively per level. Edges are counted (shown / total), not required
complete. A map without a scope is a `sketch` and never claims completeness. Omission is a decision,
never an accident.

## Frontmatter fields inside the standard

`standard` (model version) · `repo` · `sha`, or `base` + `head` for a change map · `scope` (with kind) ·
`kind` (`complete` | `sketch`). Other fields belong to the framework.

## Framework — not frozen

The presentation text (Mermaid today, Graphviz DOT or a model-first format later) · comment and intent
file formats · any protocol between surface and agent · coverage and test schemas · resolver behavior
per language · mechanical views · surfaces (page, terminal list, canvas) · remaining frontmatter fields.
A conformance checker for the frozen elements does not exist in v0; conformance is a reader check.

## Versioning

v0 is a draft under trial. It freezes as v1 only after maps of at least three codebases in at least two
languages have needed no change to the seven elements, and after one round trip of draw → build →
satisfied has completed.
