# Todo file format

The contract for `<dev_root>/todo/*.md`. Two implementations read it — the viewer page (`viewer/sv.js`, for display and
the editor) and `todo.py` (for scripts and mods) — and `todo.py` is the only writer: the viewer server performs every
write through it. `todo-cases.json` pins this document: both implementations run its `parse` cases, `todo.py` runs its
`write` cases. Change a rule here, in the cases, and in both implementations together.

## Files

- A todo file is any `*.md` directly under `todo/` whose name is not hidden; other lines than items are kept as they are.
- Text is normalized before parsing: a leading byte order mark is dropped and CRLF / lone CR become LF. Writes store LF.
- A file created by a write is titled after its name: `# <name without .md>`, then a blank line.

## Items

- An item is a line `<indent><marker><space>[<mark>]<space><text>` where indent is spaces or tabs, marker is `-`, `*`,
  `+`, `1.` or `1)` (ASCII digits), each space is one or more spaces or tabs, and mark is a space (open) or `x` / `X`
  (done). A task inside a block quote (`> - [ ] …`) is not an item.
- Lines inside a fenced code block (three or more backticks or tildes, indented at most three spaces) are never items;
  a fence closes on the same character, at least as long, with nothing after it.
- `depth` is the number of indent characters (a tab counts one). The items right after an item that sit deeper are its
  sub-items; an item with sub-items has `progress` = [done sub-items, all sub-items].
- Continuation lines (written by `todo.py` for multi-line text): lines indented four spaces under an item; a line whose
  content starts with a backslash or looks like an item gets one more leading backslash. They are not items; only
  `todo.py` reads them back as part of the item's text.

## Marks, tags and the key

- Marks: `➕ YYYY-MM-DD[ HH:MM[:SS]]` created, `📅 YYYY-MM-DD` due, `✅ YYYY-MM-DD` done, `⏫` / `🔼` / `🔽` priority
  1 / 2 / 3. Digits are ASCII; the gap after a mark sign is spaces or tabs.
- Tags: `@name` or `#name` after the line start or a space / tab, `name` of ASCII letters, digits, `_`, `.`, `-`; a tag
  inside a `[[wikilink]]` or a `[text](target)` link does not count. An item's project is its first tag.
- The key is the item's text with every mark taken out, runs of two or more spaces / tabs folded to one, and spaces /
  tabs trimmed at both ends. File, created stamp and key together find an item again.

## Writes (todo.py)

- Tick: the mark becomes `x`, a trailing `✅ …` is replaced by `✅ <today>`. Untick: the mark becomes a space and the
  trailing `✅ …` goes. Indent, marker and spacing are kept.
- Append: `- [ ] <text>[ @<project>][ [[<link>]]] ➕ <YYYY-MM-DD HH:MM:SS>` at the end of the file (a newline is added
  first when the file lacks one); the project tag is left out when the text already has exactly that tag. Further
  lines of a multi-line text follow as continuation lines.
- Every write holds one lock per todo directory and replaces the file atomically; a write that names a version
  (`<inode>-<mtime ns>-<size>`) is refused when the file is no longer at that version.
