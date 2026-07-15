# Vendored third-party assets

Per the 002-status-viewer requirement's vendored-JS constraint (name the library, pin the
version, ship its LICENSE, do not auto-update — upgrade by hand only on a security advisory).

Both are served from a hardcoded filename allowlist via `GET /assets/<name>` (viewer.py),
never a user-supplied path — the R6 read boundary still holds.

## mermaid.min.js

- **Library**: [mermaid](https://github.com/mermaid-js/mermaid) — renders ```mermaid diagrams.
- **Version**: pinned **10.9.1** (a UMD `dist/mermaid.min.js` exposing `window.mermaid`; v11 ships
  an esbuild-IIFE that doesn't expose the global as cleanly).
- **Source**: `https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js`.
- **License**: MIT — see `mermaid.LICENSE` (same pinned version).
- **Size note**: ~3.3 MB — served via `/assets/` (not inlined) so the shell page stays small;
  it is browser-only (needs DOM APIs), so its rendering is verified in the browser walk, not headlessly.
- **Update policy**: do NOT auto-update; re-vendor by hand only for a security advisory.

## marked.min.js

- **Library**: [marked](https://github.com/markedjs/marked) — Markdown → HTML renderer.
- **Version**: pinned **15.0.12** (the last release shipping a standalone browser
  `marked.min.js` UMD build; 16+ dropped it). Exposes `window.marked.parse()`.
- **Source**: `https://cdn.jsdelivr.net/npm/marked@15.0.12/marked.min.js`.
- **License**: MIT — see `marked.LICENSE.md` (same pinned version).
- **Update policy**: do NOT auto-update. Re-vendor by hand only for a security advisory,
  re-pinning this file and the version above together.
