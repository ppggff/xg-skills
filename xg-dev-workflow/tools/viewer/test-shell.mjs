// Unit tests for the shell's pure helpers (SV), extracted from shell.html and run in node.
// Covers the tricky link-resolver / comment / diff logic; DOM wiring is verified in a browser.
// Run: node tools/viewer/test-shell.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import assert from "node:assert";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "shell.html"), "utf8");
// The SV module is the <script> block that defines `var SV = (function () {...})()`.
const m = html.match(/var SV = \(function[\s\S]*?\n\}\)\(\);/);
if (!m) { console.error("could not extract SV block"); process.exit(1); }
const sandbox = { module: { exports: {} } };
vm.createContext(sandbox);
vm.runInContext(m[0] + "\nmodule.exports = SV;", sandbox);
const SV = sandbox.module.exports;

let pass = 0;
function t(name, fn) { fn(); pass++; console.log("ok  -", name); }

// Every inline <script> block must at least parse — guards the DOM block (not otherwise
// eval'd here) against syntax slips like an unbalanced quote in a string concat.
t("all inline <script> blocks are syntactically valid", () => {
  const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  assert.ok(blocks.length >= 2, "expected the SV + DOM blocks");
  for (const b of blocks) new vm.Script(b);   // throws on a syntax error
});

// --- R1: code blocks use a dedicated --code face (Sarasa Fixed SC first); chrome untouched ---
t("R1: --code leads with Sarasa Fixed SC and pre/code adopt it, chrome stays --mono", () => {
  assert.match(html, /--code:\s*"Sarasa Fixed SC"/, "--code should lead with Sarasa Fixed SC");
  assert.match(html, /pre \{[^}]*font-family: var\(--code\)/, "pre uses var(--code)");
  assert.match(html, /code \{ font-family: var\(--code\)/, "code uses var(--code)");
  assert.match(html, /--chrome: var\(--mono\)/, "chrome must stay on --mono, not --code");
});

// --- R7: renderMermaid removes mermaid's orphaned body temp node (the bottom "Syntax error") ---
t("R7: renderMermaid drops mermaid's orphaned body temp node in both settle paths", () => {
  assert.match(html, /\["d" \+ gid, "i" \+ gid\]\.forEach/, "cleanup targets #d<gid>/#i<gid>");
  assert.match(html, /parentNode === document\.body\) el\.remove\(\)/, "only body-level orphans removed");
  assert.match(html, /\.then\(function \(res\) \{ holder\.innerHTML = res\.svg; dropTemp\(\);/, "cleanup on success too");
});

// --- R6: pane widths (side/left/toc) persist to sv-layout; #right width is not stored ---
t("R6: saveLayout persists side/left/toc to sv-layout, never #right", () => {
  assert.match(html, /function saveLayout\(\) \{ lsSet\("sv-layout", JSON\.stringify/, "saveLayout writes sv-layout");
  assert.match(html, /JSON\.parse\(lsGet\("sv-layout"\)/, "init reads sv-layout");
  assert.match(html, /leftW: layoutState\.leftW, tocW: layoutState\.tocW, leftCustom: layoutState\.leftCustom, sideW: layoutState\.sideW/, "persists left/toc/leftCustom/side");
  assert.doesNotMatch(html, /rightW/, "#right width is never persisted");
  assert.match(html, /saveLayout\(\);\s+\/\/ R6: persist the new pane widths/, "drag-end persists");
});

// --- R8: #toc is never the flex filler; the doc pane absorbs width changes ---
t("R8: #toc never becomes the filler (applyLayout keeps it fixed)", () => {
  assert.doesNotMatch(html, /tocPane\.style\.flex = "1 1 0"/, "#toc must never flex-fill");
  assert.match(html, /tocPane\.style\.flex = "none"; tocPane\.style\.width = tw \+ "px";\s+\/\/ R8: #toc never fills/, "toc fixed unconditionally");
  assert.doesNotMatch(html, /singleAutoToc/, "the old single-pane toc-filler freeze is gone");
});

// --- R4: sectionForLine maps a full-file line to its covering heading section ---
t("R4: sectionForLine finds the covering section, adjusting for frontmatter", () => {
  const H = [{ line: 0, text: "A" }, { line: 5, text: "B" }, { line: 12, text: "C" }];
  assert.equal(SV.sectionForLine(H, 10, 4), 1);   // file 10 → body 5 → heading B
  assert.equal(SV.sectionForLine(H, 17, 4), 2);   // file 17 → body 12 → heading C
  assert.equal(SV.sectionForLine(H, 5, 4), 0);    // file 5 → body 0 → heading A
  assert.equal(SV.sectionForLine(H, 4, 4), -1);   // still inside the frontmatter → before first heading
  assert.equal(SV.sectionForLine(H, 0, 4), -1);   // filename match (line 0) → none
  assert.equal(SV.sectionForLine([], 10, 0), -1); // no headings → none
});
t("R4: search hit rows navigate and content hits carry their line", () => {
  assert.match(html, /class="hit" data-nav="doc" data-tree="' \+ g\.tree/, "hit row is a doc nav target");
  assert.match(html, /\(h\.line \? ' data-line="' \+ h\.line/, "content hit carries data-line");
  assert.match(html, /line: \+t\.dataset\.line \|\| 0/, "click handler forwards the line");
  assert.match(html, /function scrollToLine\(side, fileLine\)/, "scrollToLine wrapper exists");
  assert.match(html, /function scrollToSection\(side, idx\)/, "shared scroll helper extracted (review #3)");
  assert.match(html, /scrollToSection\(focus, \+t\.dataset\.toc\)/, "TOC jump reuses the shared helper");
});

// --- R3: usage/shortcuts overlay (?) ---
t("R3: help overlay markup + ?/esc bindings, suppressed while typing", () => {
  assert.match(html, /id="help"[^>]*role="dialog"/, "help dialog markup present");
  assert.match(html, /function openHelp\(\)/, "openHelp exists");
  assert.match(html, /e\.key === "\?"[^\n]*!typing[^\n]*openHelp\(\)/, "? opens help, not while typing");
  assert.match(html, /e\.key === "Escape" && helpEl\.classList\.contains\("show"\)/, "esc closes help");
  assert.match(html, /class="hint">shift-click[^<]*<kbd>\?<\/kbd> 帮助/, "the sidebar hint line mentions the ? help shortcut");
});

// --- R2: internal-link hover preview (hovercard) ---
t("R2: hover preview targets resolved internal doc links, read-only, with a grace period", () => {
  assert.match(html, /'\.docbody a\[data-nav="doc"\]'/, "preview only on resolved internal doc links");
  assert.match(html, /function lpOpen\(a\)/, "lpOpen fetches + renders the target");
  assert.match(html, /el\.querySelectorAll\("a\[href\]"\)\.forEach/, "preview links are made read-only");
  assert.match(html, /lpHideT = setTimeout\(lpHide, 450\)/, "grace period to move into the preview");
  assert.match(html, /if \(lp && lp\.contains\(e\.target\)\) return; lpHide\(\)/, "scrolling the preview itself does not dismiss it");
});

// --- R5 (T8): change-history dropdown ---
t("R5: change-history dropdown — button, per-file log fetch, selection", () => {
  assert.match(html, /data-changelog="' \+ side \+ '"/, "doc header carries a changelog button");
  assert.match(html, /\/api\/filelog\?path=/, "chOpen fetches the per-file commit log");
  assert.match(html, /function chChoose\(side, sha, rowEl\)/, "commit selection handler exists");
  assert.match(html, /data-chclose/, "history panel has an explicit close control (closes only on demand)");
  assert.doesNotMatch(html, /!chPanel\.contains\(e\.target\)\) chClose/, "no outside-click auto-close for the history panel");
});

// --- R5 (T9): diffSegments (pure) + diff-overlay wiring ---
t("R5: diffSegments merges contiguous same-state blocks and places del groups", () => {
  const spans = [{ start: 0, end: 2 }, { start: 2, end: 4 }, { start: 4, end: 6 }, { start: 6, end: 8 }];
  assert.deepEqual(SV.diffSegments(spans, [2, 3], [{ at: 4, lines: ["x", "y"] }]),
    [{ plain: true, from: 0, to: 0 }, { add: true, from: 1, to: 1 }, { del: ["x", "y"] }, { plain: true, from: 2, to: 3 }]);
  const s2 = [{ start: 0, end: 1 }, { start: 1, end: 2 }, { start: 2, end: 3 }];
  assert.deepEqual(SV.diffSegments(s2, [1, 2], []), [{ plain: true, from: 0, to: 0 }, { add: true, from: 1, to: 2 }]);
  assert.deepEqual(SV.diffSegments([], [], [{ at: 0, lines: ["gone"] }]), [{ del: ["gone"] }]);
});
t("R5: diff-overlay wiring — filediff fetch, lexer spans, non-intrusive render, exit", () => {
  assert.match(html, /\/api\/filediff\?path=/, "renderDiffOverlay fetches filediff");
  assert.match(html, /window\.marked\.lexer\(body\)/, "top-level spans via lexer");
  assert.match(html, /tk\.type !== "space"/, "space tokens skipped when aligning to DOM blocks");
  assert.match(html, /wrap\.className = "diffrun add"/, "add runs wrapped in one merged region");
  assert.match(html, /data-diffexit/, "exit-diff control present");
});

// --- resolveLink -----------------------------------------------------------
const mk = arr => new Map(arr.map(s => [s.toLowerCase(), s]));
const trees = {
  dev: mk(["xg-skills/002-status-viewer/design.md", "xg-skills/002-status-viewer/requirement.md",
           "cbdb/001-x/design.md"]),
  kb: mk(["wiki/cbdb/fdbobj-vacuum.md", "raw/cbdb/vacuum.md"]),
};
const D = "xg-skills/002-status-viewer/design.md", DIR = "xg-skills/002-status-viewer";

t("inline relative link resolves", () =>
  assert.equal(SV.resolveLink("./requirement.md", "dev", D, trees),
               "dev:xg-skills/002-status-viewer/requirement.md"));
t("inline with anchor drops anchor", () =>
  assert.equal(SV.resolveLink("./requirement.md#scope", "dev", D, trees),
               "dev:xg-skills/002-status-viewer/requirement.md"));
t("relative .. climbs correctly", () =>
  assert.equal(SV.resolveLink("../001-x/design.md", "dev", "cbdb/002-y/plan.md", trees),
               "dev:cbdb/001-x/design.md"));
t("relative .. above root → broken (null)", () =>
  assert.equal(SV.resolveLink("../../../../etc/passwd.md", "dev", D, trees), null));
t("KB wikilink path-form resolves, .md appended", () =>
  assert.equal(SV.resolveLink("[[wiki/cbdb/fdbobj-vacuum]]", "dev", D, trees),
               "kb:wiki/cbdb/fdbobj-vacuum.md"));
t("KB wikilink with |alias and #anchor", () =>
  assert.equal(SV.resolveLink("[[wiki/cbdb/fdbobj-vacuum|VACUUM#sec]]", "dev", D, trees),
               "kb:wiki/cbdb/fdbobj-vacuum.md"));
t("legacy bare wikilink → broken (no dev fallthrough)", () =>
  assert.equal(SV.resolveLink("[[fdbobj-vacuum]]", "dev", D, trees), null));
t("legacy colon wikilink → broken", () =>
  assert.equal(SV.resolveLink("[[cbdb:vacuum]]", "dev", D, trees), null));
t("case-insensitive match (APFS)", () =>
  assert.equal(SV.resolveLink("./Design.md", "dev", D, trees),
               "dev:xg-skills/002-status-viewer/design.md"));
t("external link → null", () =>
  assert.equal(SV.resolveLink("https://x.com", "dev", D, trees), null));
t("non-md target → null", () =>
  assert.equal(SV.resolveLink("./pic.png", "dev", D, trees), null));
t("missing file → broken", () =>
  assert.equal(SV.resolveLink("./nope.md", "dev", D, trees), null));

// --- buildTree (R13 directory nesting) -------------------------------------
t("buildTree folds flat paths into nested dirs/files", () => {
  const tree = SV.buildTree(["a/b/x.md", "a/b/y.md", "a/z.md", "top.md"]);
  assert.deepEqual(tree.files.map(f => f.name), ["top.md"]);           // root file
  assert.ok(tree.dirs.a);                                              // dir a
  assert.deepEqual(tree.dirs.a.files.map(f => f.name), ["z.md"]);      // a/z.md
  assert.ok(tree.dirs.a.dirs.b);                                       // a/b
  assert.deepEqual(tree.dirs.a.dirs.b.files.map(f => f.path), ["a/b/x.md", "a/b/y.md"]);
});

// --- sortCmp (R1 per-section sort: name/mtime, asc/desc, folders-first is the caller's job) ---
t("sortCmp orders by name and mtime in both directions, name breaks mtime ties", () => {
  const nodes = () => [{ name: "b.md", mtime: 100 }, { name: "a.md", mtime: 300 }, { name: "c.md", mtime: 100 }];
  assert.deepEqual(nodes().sort(SV.sortCmp("name", 1)).map(n => n.name), ["a.md", "b.md", "c.md"]);
  assert.deepEqual(nodes().sort(SV.sortCmp("name", -1)).map(n => n.name), ["c.md", "b.md", "a.md"]);
  assert.deepEqual(nodes().sort(SV.sortCmp("mtime", -1)).map(n => n.name), ["a.md", "b.md", "c.md"]);  // newest first; b,c tie → name
  assert.deepEqual(nodes().sort(SV.sortCmp("mtime", 1)).map(n => n.name), ["b.md", "c.md", "a.md"]);   // oldest first; b,c tie → name
});
t("buildTree aggregates node.mtime as the newest descendant", () => {
  const tree = SV.buildTree([{ path: "a/x.md", mtime: 100 }, { path: "a/b/y.md", mtime: 500 }, { path: "a/z.md", mtime: 200 }]);
  assert.equal(tree.dirs.a.mtime, 500);       // deepest descendant floats up
  assert.equal(tree.dirs.a.dirs.b.mtime, 500);
});

// --- matchScore (R5 quick-open: fuzzy subsequence match + quality ranking) ---
t("matchScore: subsequence match, misses when a char is absent", () => {
  assert.equal(SV.matchScore("victim", "catalog-cache-victim-checker.md").hit, true);
  assert.equal(SV.matchScore("xyz", "catalog-cache-victim-checker.md").hit, false);
  assert.deepEqual(SV.matchScore("", "anything").idx, []);        // empty query = trivial hit
});
t("matchScore ranks contiguous/exact above scattered subsequence", () => {
  const contiguous = SV.matchScore("victim", "dev/acme-db/002-cache-victim/progress.md").score;   // "victim" appears intact
  const scattered = SV.matchScore("victim", "dev/xg-skills/004-ui-polish/adr/0003-visual-direction-terminal.md").score;  // v..i..t..i..m spread out
  assert.ok(contiguous > scattered, `contiguous ${contiguous} should beat scattered ${scattered}`);
});
t("matchScore rewards word-boundary starts (prefix / after separator)", () => {
  const boundary = SV.matchScore("card", "proj/002-card-notes.md").score;    // 'card' starts after '-'
  const mid = SV.matchScore("card", "xcardy.md").score;                          // 'card' mid-word
  assert.ok(boundary > mid, `boundary ${boundary} should beat mid-word ${mid}`);
});

// --- matchScore multi-term AND + `=` exact (R9/R10, ADR-0003) ---
const nameStart = (full) => full.length - full.split("/").pop().length;
t("matchScore: space-separated terms are AND, order-independent (R9)", () => {
  const full = "dev/cbdb/005-tree-sort-filter/plan.md", b = nameStart(full);
  assert.equal(SV.matchScore("plan 005 cbdb", full, b).hit, true);    // typed order ≠ path order
  assert.equal(SV.matchScore("cbdb plan 005", full, b).hit, true);    // any order still hits
  assert.equal(SV.matchScore("plan 999", full, b).hit, false);        // one term absent ⇒ whole miss
});
t("matchScore: `=term` is exact contiguous substring, not fuzzy (R10)", () => {
  const a = "dev/cbdb/005/plan.md", c = "dev/pl-a-n/notes.md";
  assert.equal(SV.matchScore("=plan", a, nameStart(a)).hit, true);    // contiguous "plan" present
  assert.equal(SV.matchScore("=plan", c, nameStart(c)).hit, false);   // p-l-a-n split by '-' ⇒ exact miss
  assert.equal(SV.matchScore("plan", c, nameStart(c)).hit, true);     // fuzzy still hits the scattered form
});
t("matchScore: `=` mixes with fuzzy terms under AND (R10)", () => {
  const full = "dev/cbdb/005/plan.md", b = nameStart(full);
  assert.equal(SV.matchScore("=plan.md cbdb", full, b).hit, true);    // exact name + fuzzy path term
  assert.equal(SV.matchScore("=plan.md zzz", full, b).hit, false);
});
t("matchScore: filename hit outranks path-only hit (名>路径, P1)", () => {
  const named = "dev/x/report.md", path = "dev/report-x/notes.md";
  const sNamed = SV.matchScore("report", named, nameStart(named)).score;
  const sPath = SV.matchScore("report", path, nameStart(path)).score;
  assert.ok(sNamed > sPath, `name-hit ${sNamed} should beat path-only ${sPath}`);
});
t("matchScore: smart-case — an uppercase term is case-sensitive (P3)", () => {
  const upper = "dev/x/README.md", lower = "dev/x/readme.md";
  assert.equal(SV.matchScore("readme", upper, nameStart(upper)).hit, true);   // lowercase query ⇒ case-insensitive
  assert.equal(SV.matchScore("README", upper, nameStart(upper)).hit, true);
  assert.equal(SV.matchScore("README", lower, nameStart(lower)).hit, false);  // uppercase query won't match lowercase
});

// --- recentPush (R6/R7/R8 recent-use history: dedup move-to-front, cap, recency) ---
t("recentPush dedups to front, caps, keeps recency order", () => {
  assert.deepEqual(SV.recentPush(["b", "c"], "a", 8), ["a", "b", "c"]);          // new item to front
  assert.deepEqual(SV.recentPush(["a", "b", "c"], "c", 8), ["c", "a", "b"]);     // existing moves to front (no dup)
  assert.deepEqual(SV.recentPush(["a", "b", "c"], "d", 3), ["d", "a", "b"]);     // cap drops the oldest
  assert.deepEqual(SV.recentPush(undefined, "x", 8), ["x"]);                     // empty/undefined list
});

// --- projectsFromTree (R14 selector, excludes top-level files) -------------
t("projectsFromTree lists project dirs, excludes top-level files", () => {
  const projs = SV.projectsFromTree(
    ["cbdb/001-x/design.md", "xg-skills/002-y/plan.md", "index.md", "log.md"],
    ["raw/cbdb/note.md", "wiki/common/arch.md", "wiki/index.md", "wiki/log.md"]);
  assert.deepEqual(projs, ["cbdb", "common", "xg-skills"]);   // no index.md / log.md from either tree
});

// --- groupHits (R31 search grouped by file) --------------------------------
t("groupHits groups by file, preserves first-seen order", () => {
  const g = SV.groupHits([
    { tree: "dev", path: "a.md", line: 1, snippet: "x" },
    { tree: "dev", path: "b.md", line: 2, snippet: "y" },
    { tree: "dev", path: "a.md", line: 9, snippet: "z" }]);
  assert.equal(g.length, 2);
  assert.deepEqual(g.map(x => x.path), ["a.md", "b.md"]);   // order preserved
  assert.equal(g[0].hits.length, 2);                         // a.md's two hits grouped
});

// --- parseFrontmatter ------------------------------------------------------
t("frontmatter extracted, body follows", () => {
  const r = SV.parseFrontmatter("---\nid: 002\nstatus: frozen\n---\n# Title\nbody");
  assert.equal(r.fields.id, "002"); assert.equal(r.fields.status, "frozen");
  assert.ok(r.body.startsWith("# Title"));
});
t("no frontmatter → empty fields, full body", () => {
  const r = SV.parseFrontmatter("# just a doc\ntext");
  assert.deepEqual(r.fields, {}); assert.ok(r.body.startsWith("# just"));
});

// --- colorizeDiff ----------------------------------------------------------
t("diff coloring by leading char, +++/--- not marked, html-escaped", () => {
  const h = SV.colorizeDiff("@@ -1 +1 @@\n+added\n-removed\n+++ b/f\n--- a/f\n+<script>x</script>");
  assert.ok(h.includes('class="hunk"')); assert.ok(h.includes('class="add"'));
  assert.ok(h.includes('class="del"'));
  assert.ok(!/class="add"[^>]*>\+\+\+/.test(h));           // +++ header not an add line
  assert.ok(h.includes("&lt;script&gt;") && !h.includes("<script>")); // content html-escaped
});

// --- commentBlock ----------------------------------------------------------
t("comment block: nearest heading above selection + every line quoted", () => {
  const headings = [{ depth: 1, text: "Title", line: 0 }, { depth: 2, text: "Scope", line: 5 }];
  const b = SV.commentBlock("dev", "p/001-x/requirement.md", headings, 7, "line one\nline two");
  assert.ok(b.startsWith("[dev:p/001-x/requirement.md#Scope]"));
  assert.ok(b.includes("\n> line one\n> line two")); // multiline: each line quoted
});
t("comment block: selection before any heading → no anchor", () => {
  const b = SV.commentBlock("dev", "p/001-x/r.md", [{ depth: 1, text: "H", line: 5 }], 1, "pre");
  assert.ok(b.startsWith("[dev:p/001-x/r.md]\n> pre"));
});

// --- F1 end-to-end: the wikilink marked extension actually emits <a> --------
// (the isolated resolveLink test above passed while the whole path was dead because marked
//  never produced an <a>; this loads the REAL vendored marked + the shell's real extension
//  registration and asserts a wikilink renders as an anchor markLinks can then resolve.)
t("marked + shell wikilink extension renders [[..]] as <a href=[[..]]>", () => {
  const markedSrc = readFileSync(join(here, "marked.min.js"), "utf8");
  const box = {};
  box.globalThis = box; box.self = box; box.window = box;
  vm.createContext(box);
  vm.runInContext(markedSrc, box);
  assert.equal(typeof box.marked.use, "function");        // marked@15 supports extensions
  const reg = html.match(/window\.marked\.use\(\{[\s\S]*?\}\] \}\);/);
  assert.ok(reg, "could not extract the marked.use registration from shell.html");
  const escSrc = html.match(/function esc\(s\) \{[\s\S]*?\}/);   // use the shell's REAL esc
  assert.ok(escSrc, "could not extract esc() from shell.html");
  vm.runInContext(escSrc[0] + "\nthis.esc = esc;", box);
  vm.runInContext(reg[0], box);
  const out = box.marked.parse("see [[wiki/cbdb/x]] here");
  assert.ok(/<a href="\[\[wiki\/cbdb\/x\]\]">/.test(out), "wikilink not rendered as anchor: " + out);
  // must NOT fire inside a code fence
  const fenced = box.marked.parse("```\n[[wiki/cbdb/x]]\n```");
  assert.ok(!/<a href/.test(fenced), "wikilink wrongly transformed inside code fence");
  // attribute injection: a quote in the wikilink text must not break out of href="..."
  const inj = box.marked.parse('[[a" onmouseover="alert(1)" x="]]');
  assert.ok(!/onmouseover=/.test(inj) || /&quot;|&#39;/.test(inj),
    "quote in wikilink escaped so no live handler injected: " + inj);
  assert.ok(!/ onmouseover="alert/.test(inj), "attribute injection not neutralized: " + inj);
});

// 004 T3/T7: pure state→presentation mappings
t("stName: canonical pass-through · ?/empty → unknown · non-canonical → backlog", () => {
  assert.equal(SV.stName("active"), "active");
  assert.equal(SV.stName("Done"), "done");
  assert.equal(SV.stName("?"), "unknown");
  assert.equal(SV.stName(""), "unknown");
  assert.equal(SV.stName("doing"), "backlog");
});
t("stepFill: unstarted/planned → pending · in-progress/testing/blocked/failing → doing · settled → done", () => {
  assert.equal(SV.stepFill("—"), "pending");
  assert.equal(SV.stepFill(""), "pending");
  assert.equal(SV.stepFill("?"), "pending");
  assert.equal(SV.stepFill("planned"), "pending");         // test.md not-yet-run
  assert.equal(SV.stepFill("not-started"), "pending");     // progress.md
  assert.equal(SV.stepFill("drafting"), "doing");
  assert.equal(SV.stepFill("in-progress"), "doing");
  assert.equal(SV.stepFill("testing"), "doing");           // implement 进行中
  assert.equal(SV.stepFill("blocked"), "doing");
  assert.equal(SV.stepFill("failing"), "doing");           // not "done"
  assert.equal(SV.stepFill("frozen"), "done");
  assert.equal(SV.stepFill("passing"), "done");
  assert.equal(SV.stepFill("confirmed"), "done");
});
t("statusTone: doc statuses → pill tone · unknown → backlog", () => {
  assert.equal(SV.statusTone("frozen"), "done");
  assert.equal(SV.statusTone("confirmed"), "done");
  assert.equal(SV.statusTone("drafting"), "paused");
  assert.equal(SV.statusTone("whatever"), "backlog");
});

// --- pickLineRect (006: current-line band unit) ------------------------------
const rr = (top, bottom) => ({ top, bottom, height: bottom - top });
t("pickLineRect: smallest containing rect wins over enclosing container box", () => {
  const rects = [rr(0, 100), rr(0, 20), rr(20, 40), rr(40, 100)];   // container first, content order
  assert.equal(SV.pickLineRect(rects, 25), rects[2]);
  assert.equal(SV.pickLineRect(rects, 5), rects[1]);
});
t("pickLineRect: y outside all rects → first rect (default fallback)", () => {
  const rects = [rr(10, 30), rr(30, 50)];
  assert.equal(SV.pickLineRect(rects, 500), rects[0]);
});
t("pickLineRect: null/undefined y → first rect", () => {
  const rects = [rr(10, 30), rr(30, 50)];
  assert.equal(SV.pickLineRect(rects, null), rects[0]);
  assert.equal(SV.pickLineRect(rects, undefined), rects[0]);
});
t("pickLineRect: equal-height candidates → first in content order", () => {
  const rects = [rr(0, 40), rr(10, 30), rr(10, 30)];
  assert.equal(SV.pickLineRect(rects, 15), rects[1]);
});
t("pickLineRect: ±2px tolerance at rect edges", () => {
  const rects = [rr(0, 100), rr(10, 30)];
  assert.equal(SV.pickLineRect(rects, 8), rects[1]);    // top-2
  assert.equal(SV.pickLineRect(rects, 32), rects[1]);   // bottom+2
});
t("pickLineRect: empty rects → null", () => {
  assert.equal(SV.pickLineRect([], 10), null);
});

// --- mergeTreeOpen (006: scope-safe persist merge) ---------------------------
t("mergeTreeOpen: out-of-scope saved keys survive a scoped persist", () => {
  // project A rendered; B's saved keys are NOT present in the DOM and must survive
  const saved = ["dev", "dev/projA", "dev/projB", "dev/projB/sub"];
  const present = ["dev", "dev/projA", "dev/projA/sub"];
  const open = ["dev", "dev/projA/sub"];
  assert.deepEqual(SV.mergeTreeOpen(saved, present, open).sort(),
    ["dev", "dev/projA/sub", "dev/projB", "dev/projB/sub"].sort());
});
t("mergeTreeOpen: closing a present folder removes it from saved", () => {
  assert.deepEqual(SV.mergeTreeOpen(["dev", "dev/a"], ["dev", "dev/a"], ["dev"]), ["dev"]);
});
t("mergeTreeOpen: empty saved → just the open set", () => {
  assert.deepEqual(SV.mergeTreeOpen([], ["dev", "dev/a"], ["dev/a"]), ["dev/a"]);
});
t("mergeTreeOpen: no duplicates when an open key was already saved", () => {
  const out = SV.mergeTreeOpen(["dev/a"], ["dev/a"], ["dev/a"]);
  assert.deepEqual(out, ["dev/a"]);
});
t("mergeTreeOpen: everything closed in a full render → empty", () => {
  assert.deepEqual(SV.mergeTreeOpen(["dev", "dev/a"], ["dev", "dev/a"], []), []);
});

// --- decisionRows (010: card-drawer ledger section) ---------------------------
t("decisionRows: empty/missing ledger renders nothing", () => {
  assert.equal(SV.decisionRows([]), "");
  assert.equal(SV.decisionRows(undefined), "");
});
t("decisionRows: header counts pending; rows escape text and tone by state", () => {
  const html = SV.decisionRows([
    { id: "R1", level: "requirement", state: "approved", text: "keep <it>" },
    { id: "ADR-0001 D2", level: "design", state: "proposed", text: "b" },
  ]);
  assert.match(html, /Decisions<\/span><span class="cd-v">2 · <span class="trcell q">待评审 1<\/span>/);
  assert.match(html, /trcell ok">✓ approved<\/span> <span class="cd-src">requirement<\/span> keep &lt;it&gt;/);
  assert.match(html, /ADR-0001 D2<\/span>/);
  assert.match(html, /trcell q">● proposed/);
});
t("decisionRows: conflict state renders neutral ⚠ without a winner state", () => {
  const html = SV.decisionRows([{ id: "R1", level: "requirement", state: "conflict", text: "" }]);
  assert.match(html, /trcell miss">⚠ 冲突\(dup-active\)/);
  assert.ok(!/approved|proposed/.test(html), "conflict row must not name a state");
});
t("decisionRows: all approved shows 全批", () => {
  assert.match(SV.decisionRows([{ id: "R1", level: "requirement", state: "approved", text: "x" }]),
               /trcell ok">全批/);
});

// --- taskCounts / taskTone (007: drawer task summary) -------------------------
t("taskCounts: done/total over parsed rows; empty and missing degrade to 0/0", () => {
  assert.deepEqual(SV.taskCounts([{ done: true }, { done: false }, { done: true }]),
    { done: 2, total: 3 });
  assert.deepEqual(SV.taskCounts([]), { done: 0, total: 0 });
  assert.deepEqual(SV.taskCounts(undefined), { done: 0, total: 0 });
});
t("taskTone: done wins; blocked/doing recognized; unknown → backlog", () => {
  assert.equal(SV.taskTone({ done: true, status: "blocked" }), "done");
  assert.equal(SV.taskTone({ done: false, status: "blocked" }), "blocked");
  assert.equal(SV.taskTone({ done: false, status: "[!]" }), "blocked");
  assert.equal(SV.taskTone({ done: false, status: "doing" }), "active");
  assert.equal(SV.taskTone({ done: false, status: "???" }), "backlog");
  assert.equal(SV.taskTone({ done: false }), "backlog");
});

// --- traceCells (007: per-R five-cell presence display) ------------------------
t("traceCells: booleans map ok/miss; commit four values map ok/q/miss/na", () => {
  const cells = SV.traceCells({ present: { design: true, verify: false, task: true, test: false, commit: "strict" } });
  assert.deepEqual(cells.map(c => c.k), ["design", "verify", "task", "test", "commit"]);
  assert.deepEqual(cells.map(c => c.state), ["ok", "miss", "ok", "miss", "ok"]);
  assert.equal(SV.traceCells({ present: { commit: "loose" } })[4].state, "q");
  assert.equal(SV.traceCells({ present: { commit: "none" } })[4].state, "miss");
  assert.equal(SV.traceCells({ present: { commit: "unchecked" } })[4].state, "na");
});
t("traceCells: missing present degrades to all-miss + na commit", () => {
  const cells = SV.traceCells({});
  assert.deepEqual(cells.map(c => c.state), ["miss", "miss", "miss", "miss", "na"]);
});

t("traceGaps: counts rows with a miss or the no-cell flag; loose/unchecked are hints", () => {
  const full = { present: { design: true, verify: true, task: true, test: true, commit: "strict" }, flags: [] };
  const missTest = { present: { design: true, verify: true, task: true, test: false, commit: "strict" }, flags: [] };
  const loose = { present: { design: true, verify: true, task: true, test: true, commit: "loose" }, flags: [] };
  const unchecked = { present: { design: true, verify: true, task: true, test: true, commit: "unchecked" }, flags: [] };
  const flagOnly = { present: { design: true, verify: true, task: true, test: true, commit: "strict" }, flags: ["not-in-需求条目"] };
  assert.equal(SV.traceGaps([full, missTest, loose, unchecked, flagOnly]), 2);
  assert.equal(SV.traceGaps([]), 0);
  assert.equal(SV.traceGaps(undefined), 0);
});

// --- groupTraceRows (015 part axis) -----------------------------------------
t("groupTraceRows: null for un-split; design order; multi-part row in each group", () => {
  const a = { rid: "R1", parts: ["观测"] };
  const b = { rid: "R3", parts: ["观测", "推进"] };
  const c = { rid: "R9", parts: [] };
  assert.equal(SV.groupTraceRows([a, b], []), null);
  assert.equal(SV.groupTraceRows([a, b], undefined), null);
  const g = SV.groupTraceRows([a, b, c], ["观测", "推进"]);
  assert.deepEqual(g.map(x => x.part), ["观测", "推进", "—"]);
  assert.deepEqual(g[0].rows.map(r => r.rid), ["R1", "R3"]);
  assert.deepEqual(g[1].rows.map(r => r.rid), ["R3"]);   // multi-part appears in each
  assert.deepEqual(g[2].rows.map(r => r.rid), ["R9"]);   // ungrouped → trailing "—"
});

t("groupTraceRows: no trailing group when every row has a part", () => {
  const g = SV.groupTraceRows([{ rid: "R1", parts: ["alpha"] }], ["alpha"]);
  assert.equal(g.length, 1);
  assert.equal(SV.groupTraceRows([], ["alpha"])[0].rows.length, 0);
});

// --- clampMeasure (016 T1: reading-measure drag keeps the box inside the pane) ---
t("clampMeasure: crossing / narrow-window / already-in-bounds", () => {
  // 左右交叉: dragging the left edge past the right edge collapses to min width at the drag point
  assert.deepEqual(SV.clampMeasure(700, -150, 1000, 200), { left: 700, width: 200 });
  // 窄窗口: pane itself is narrower than min → fill the whole pane, no overflow
  assert.deepEqual(SV.clampMeasure(20, 100, 150, 300), { left: 0, width: 150 });
  // 边界相等: right edge already exactly at paneW → passes through unchanged (idempotent)
  assert.deepEqual(SV.clampMeasure(300, 500, 800, 200), { left: 300, width: 500 });
});

// --- invalidateGeometry (016 T2: rAF-coalesced, five hookpoints wired this slice) ---
t("T2: invalidateGeometry rAF-coalesces and skips a detached current block", () => {
  assert.match(html, /function invalidateGeometry\(side\)/, "invalidateGeometry defined");
  assert.match(html, /requestAnimationFrame\(function \(\) \{/, "coalesces via rAF");
  assert.match(html, /if \(p\._curEl && p\._curEl\.isConnected\) \{   \/\/ the marked block is gone — skip that part, don't throw/, "curline reposition skipped for a detached block, no throw");
  assert.match(html, /rail\(side\);   \/\/ T7\/S9: marker rail geometry depends on the same pane\/docbody layout/, "T7: rail redraws too, regardless of curline's own guard");
});
t("T2: setCurLine stores a block-relative y offset, not the raw viewport clientY", () => {
  assert.match(html, /p\._curYOff = clientY == null \? null : clientY - blk\.getBoundingClientRect\(\)\.top;/, "offset stored relative to blk");
});
t("T2: all five hookpoints call invalidateGeometry", () => {
  assert.match(html, /positionMrules\(side, pane, db\);\s+invalidateGeometry\(side\);.*hookpoint 1/, "hookpoint 1: measure drag");
  assert.match(html, /saveLayout\(\); applyMeasure\(ws\); invalidateGeometry\(ws\);.*hookpoint 2/, "hookpoint 2: width-tier button (per-pane since the M2 change)");
  assert.match(html, /invalidateGeometry\("left"\); invalidateGeometry\("right"\);.*hookpoint 5/, "hookpoint 5: applyLayout end");
  assert.match(html, /padForDrawer\(pane\);\s+invalidateGeometry\(side\);.*hookpoint 6/, "hookpoint 6: updateDetail end");
  assert.match(html, /window\.addEventListener\("resize", function \(\) \{.*hookpoint 7/, "hookpoint 7: window resize");
});

// --- blockSpans / blockLineNumbers (016 T3: F8's top-level-HTML-comment off-by-one) ---
t("blockSpans: skips a top-level HTML-comment token so spans.length == block count [F8]", () => {
  // marked.lexer("<!-- c -->\n\n# Title\n\npara one\n\npara two") shape, per facts.md F8:
  // non-space tokens = 4 (html, heading, paragraph, paragraph); marked.parse() renders 3 elements
  // (the comment becomes a Comment node, not an Element child).
  const tokens = [
    { type: "html", raw: "<!-- c -->\n\n" },
    { type: "heading", raw: "# Title\n\n" },
    { type: "paragraph", raw: "para one\n\n" },
    { type: "paragraph", raw: "para two" },
  ];
  const spans = SV.blockSpans(tokens);
  assert.equal(spans.length, 3, "comment token excluded — matches the 3 rendered elements");
  assert.deepEqual(spans[0], { start: 2, end: 4 });   // heading starts after the comment's 2 lines
  assert.deepEqual(spans[1], { start: 4, end: 6 });
  assert.deepEqual(spans[2], { start: 6, end: 6 });   // last token, no trailing \n to count
});
t("blockSpans: skips space tokens; a non-comment html token still counts (raw block HTML)", () => {
  const tokens = [
    { type: "space", raw: "\n" },
    { type: "html", raw: "<div>raw</div>\n\n" },   // not a bare comment — still renders an Element
    { type: "paragraph", raw: "text" },
  ];
  const spans = SV.blockSpans(tokens);
  assert.equal(spans.length, 2);
  assert.deepEqual(spans[0], { start: 1, end: 3 });   // the leading space token's 1 line still counts toward ln
});
t("blockLineNumbers: 1-based file line = span.start + fmLines + 1", () => {
  const spans = [{ start: 0, end: 1 }, { start: 2, end: 3 }];
  assert.deepEqual(SV.blockLineNumbers(spans, 4), [5, 7]);
  assert.deepEqual(SV.blockLineNumbers([], 4), []);
  assert.deepEqual(SV.blockLineNumbers(spans, 0), [1, 3]);
});
t("T3: lineGutter tags blocks via dataset (not textContent) and warns once on mismatch", () => {
  assert.match(html, /function lineGutter\(blocks, tokens, fmLines\)/, "lineGutter defined");
  assert.match(html, /b\.dataset\.srcline = nums\[i\];/, "tags via dataset, never a text node");
  assert.match(html, /console\.warn\("line-gutter: block\/span mismatch/, "warns on mismatch instead of showing a wrong number");
  assert.match(html, /lineGutter\(\[\]\.slice\.call\(pane\.querySelectorAll\("\.docbody > \*"\)\), window\.marked\.lexer\(fm\.body\), pane\._doc\.fmLines\);/, "renderDoc wires it in");
});
t("T3: renderMermaid takes side and invalidates from its inner .then (hookpoint 4)", () => {
  assert.match(html, /function renderMermaid\(side, body\)/, "renderMermaid takes side");
  // T10 widened this from invalidateGeometry to invalidateContent (which calls it) — the diagram
  // swap changes the indexed text too, not only the layout. The hookpoint is unchanged.
  assert.match(html, /holder\.innerHTML = res\.svg; dropTemp\(\);\s+invalidateContent\(side\); \}\).*hookpoint 4/, "inner .then invalidates, not the outer ensureMermaid().then");
});
t("T3: renderDiffOverlay reuses SV.blockSpans and labels plain/add blocks with their source line", () => {
  assert.match(html, /var tokens = window\.marked\.lexer\(body\), spans = SV\.blockSpans\(tokens\);/, "diff overlay no longer duplicates the span-building loop");
  assert.match(html, /wrap\.dataset\.srcline = SV\.blockLineNumbers\(\[useSpans\[s\.from\]\], fmLines\)\[0\];/, "add segment labels its first block");
  assert.match(html, /blocks\[i\]\.dataset\.srcline = SV\.blockLineNumbers\(\[useSpans\[i\]\], fmLines\)\[0\];/, "plain segment labels each block");
});

// --- buildIndexText / scanHits / offsetToNode (016 T4: content coordinate layer, S1/S2) ---
t("buildIndexText: folds whitespace to one space + lowercases; a source-line-break phrase becomes searchable", () => {
  const shells = [
    { node: "N1", off: 0, len: 5, isSpace: false, text: "Hello" },
    { node: "N1", off: 5, len: 1, isSpace: true },   // a single "\n" between two text nodes
    { node: "N2", off: 0, len: 5, isSpace: false, text: "World" },
  ];
  const { text, runs } = SV.buildIndexText(shells);
  assert.equal(text, "hello world");
  assert.deepEqual(runs.map(r => r.at), [0, 5, 6]);
  assert.equal(SV.scanHits(text, "hello world").length, 1, "phrase spanning the folded line-break is searchable");
});
t("scanHits: empty needle / overlapping candidates / CJK / case-sensitive (caller lowercases first)", () => {
  assert.deepEqual(SV.scanHits("hello world", ""), []);
  assert.deepEqual(SV.scanHits("aaaa", "aa"), [[0, 2], [2, 4]]);   // non-overlapping, greedy left-to-right
  assert.deepEqual(SV.scanHits("设计文档 说明", "设计"), [[0, 2]]);
  assert.deepEqual(SV.scanHits("hello world", "World"), []);       // scanHits itself is case-sensitive
  assert.deepEqual(SV.scanHits("hello world", "world"), [[6, 11]]);
});
t("offsetToNode: run boundary / inside a folded whitespace run / out of bounds", () => {
  const runs = [
    { at: 0, node: "A", off: 0, len: 5, isSpace: false },
    { at: 5, node: "A", off: 5, len: 3, isSpace: true },   // 3 original spaces, folded to 1 char at idx.text[5]
    { at: 6, node: "B", off: 0, len: 5, isSpace: false },
  ];
  assert.deepEqual(SV.offsetToNode(runs, 6), { node: "B", nodeOff: 0 });   // boundary → the next run, no spillover
  assert.deepEqual(SV.offsetToNode(runs, 5), { node: "A", nodeOff: 5 });   // folded run → its own original start, not off+len
  assert.equal(SV.offsetToNode(runs, -1), null);
  assert.equal(SV.offsetToNode(runs, 11), null);
});
t("T4: buildIndex excludes chrome (S1's exclusion table) and walks Text nodes only", () => {
  // T12 added `style`: mermaid injects a <style> into each rendered SVG, and CSS text is never
  // visible content — searching it yields hits with no rect.
  assert.match(html, /var IDX_EXCLUDE = "\.doc-head, \.frontmatter, \.diffbar, \.tr-asof, \.cd-bar, \.board-filters, \.findbar, \.rail, section\.grp\[hidden\], style";/, "static exclusion list matches S1's table (+ the findbar/rail overlays and injected <style>)");
  assert.match(html, /function blockText\(el\) \{[\s\S]*?idxTextExcluded\(n\)/, "anchors read the same content rule as the index, so a diagram's generated style id can't poison the prefix");
  assert.match(html, /var cd = el\.closest\("\.cd-body"\);\s+return !!\(cd && cd\.offsetParent === null\);/, "cd-body excluded only while hidden (R15)");
  assert.match(html, /document\.createTreeWalker\(pane, NodeFilter\.SHOW_TEXT,/, "walks idx.root's Text nodes");
  assert.match(html, /root: pane,/, "idx.root is always the pane itself (D19)");
});
t("T4: rangeOf skips a stale hit instead of throwing, never caches the Range", () => {
  assert.match(html, /function rangeOf\(idx, start, end\)/, "rangeOf defined");
  assert.match(html, /if \(!a \|\| !b\) return null;/, "either endpoint out of bounds → skip, don't throw");
  assert.match(html, /range\.setStart\(a\.node, a\.nodeOff\); range\.setEnd\(b\.node, b\.nodeOff\);/, "builds a fresh Range from both endpoints");
});

// --- find box + paint + f/Esc wiring (016 T5) ---
t("T5: Escape closes an open find box before help/change-history (position matters)", () => {
  const m = html.match(/if \(e\.key === "Escape" && PANES\[focus\]\._findOpen\) \{ findClose\(focus\); return; \}[\s\S]{0,80}?if \(e\.key === "Escape" && helpEl/);
  assert.ok(m, "find's Escape branch comes before the existing help/Escape branch");
});
t("T5: bare f opens/focuses find (not while typing); cmd/ctrl+F stays native", () => {
  assert.match(html, /if \(e\.key === "f" && !\(e\.metaKey \|\| e\.ctrlKey \|\| e\.altKey\) && !typing\) \{ e\.preventDefault\(\); findOpen\(focus\); \}/, "bare f only, guarded by !typing");
});
t("T5/T6: paint unregisters all seven highlight names for this pane, then splits hit vs current", () => {
  assert.match(html, /if \(!window\.CSS \|\| !CSS\.highlights\) return;/, "no Custom Highlight API → skip (ADR-0001 corollary 2)");
  assert.match(html, /"sv-hit-" \+ side, "sv-cur-" \+ side, "sv-sel-" \+ side,/, "unregisters hit/cur/sel names even though sel/pin aren't populated yet");
  assert.match(html, /"sv-pin-" \+ side \+ "-0", "sv-pin-" \+ side \+ "-1", "sv-pin-" \+ side \+ "-2", "sv-pin-" \+ side \+ "-3"/, "and all four pin slots");
  assert.match(html, /allHl\.priority = 100; curHl\.priority = 200;/, "current hit outranks the rest (S11)");
});
t("T5: reindex skips empty models and clamps cur via Math.min; find reuses the cached idx", () => {
  assert.match(html, /if \(!h\.q && !h\.pins\.length\) \{ h\.idx = null; return; \}/, "nothing to search → skip rebuilding the index, but drop the one pointing at the replaced DOM");
  assert.match(html, /h\.cur = Math\.min\(h\.cur, h\.hits\.length - 1\);/, "clamp doubles as the empty-hits → -1 case");
  assert.match(html, /if \(!h\.idx\) h\.idx = buildIndex\(p\);\s+\/\/ find box opened before any render's reindex ran/, "find lazily builds the index if reindex hasn't run yet");
});
t("T5: findClose clears this pane's model (R13) and unpaints; findOpen anchors off .doc-head", () => {
  assert.match(html, /p\._hits\.q = ""; p\._hits\.hits = \[\]; p\._hits\.cur = -1;\s+writeField\(side, "q", ""\);.*\s+paint\(side\);/, "closing clears q/hits/cur, drops the remembered query (T12), then repaints");
  assert.match(html, /head\.insertAdjacentHTML\("afterend", findBarHtml\(side\)\);/, "find bar is inserted right after .doc-head, every view kind");
});
t("T5: two non-full-render visibility toggles reindex too (found live — neither goes through afterRender)", () => {
  assert.match(html, /cd\.classList\.toggle\("open", detailOpen\);\s+reindex\(t\.closest\("#left"\) \? "left" : "right"\); return; \}/, "board drawer open/close reindexes (else its text stays searchable while hidden, or vice versa)");
  assert.match(html, /grp\.hidden = !chk\.checked;\s+reindex\(focus\); return; \}/, "TOC-filtered group hide/show reindexes (else a filtered-out group stays searchable)");
});

// --- stepHitIndex (016 T6: hit navigation, wraps at both endpoints) ---
t("stepHitIndex: total=0 / cur=-1 (no current yet) / wraps at both endpoints", () => {
  assert.equal(SV.stepHitIndex(0, 0, 1), -1);
  assert.equal(SV.stepHitIndex(-1, 0, -1), -1);
  assert.equal(SV.stepHitIndex(-1, 5, 1), 0);     // next from nothing → the first hit
  assert.equal(SV.stepHitIndex(-1, 5, -1), 4);    // previous from nothing → the last hit
  assert.equal(SV.stepHitIndex(4, 5, 1), 0);      // last → next wraps to first
  assert.equal(SV.stepHitIndex(0, 5, -1), 4);     // first → previous wraps to last
  assert.equal(SV.stepHitIndex(2, 5, 1), 3);      // ordinary advance, no wrap
});
t("T6/S14: scrolling is hand-computed (HEAD_PAD), and only when the target isn't already visible", () => {
  assert.match(html, /var HEAD_PAD = 56;/, "matches the existing scroll-margin-top: 56px");
  const m = html.match(/function scrollToInterval\(side, iv, force\) \{[\s\S]*?\n  \}/);
  assert.ok(m, "scrollToInterval defined");
  assert.match(m[0], /p\.scrollTop = p\.scrollTop \+ \(rects\[0\]\.top - pr\.top\) - HEAD_PAD;/, "manual scrollTop math");
  assert.match(m[0], /var lo = pr\.top \+ HEAD_PAD, hi = pr\.bottom - \(bar \? bar\.getBoundingClientRect\(\)\.height : 0\);/, "the visible band excludes both sticky strips");
  assert.match(m[0], /if \(!force && rects\[0\]\.top >= lo && rects\[0\]\.bottom <= hi\) return;/, "S14: already on screen → don't move the page");
  assert.doesNotMatch(m[0], /scrollIntoView/, "never falls back to scrollIntoView — scroll-margin-top can't cover paragraphs/tables");
});
t("T14/S6: rail marks carry their interval and act as jump targets", () => {
  assert.match(html, /el\.dataset\.s = hit\[0\]; el\.dataset\.e = hit\[1\];/, "the interval is the mark's identity, not a Range");
  assert.match(html, /if \(t\.dataset\.hit != null\) \{ rh\.cur = \+t\.dataset\.hit; paint\(rs\); updateFindCount\(rs\); \}/, "clicking a hit mark also makes it current");
  assert.match(html, /scrollToInterval\(rs, \[\+t\.dataset\.s, \+t\.dataset\.e\], true\); return; \}/, "a click always scrolls, unlike stepping");
  assert.match(html, /\.rail i \{[^}]*height: 8px;[^}]*background-clip: content-box;/, "8px hit area, 2px of visible bar");
});
t("T14/S7: the measure is per pane, with the old flat fields migrating to both sides", () => {
  assert.match(html, /m: \{ left: \{ mode: "default", l: null, w: null \}, right: \{ mode: "default", l: null, w: null \} \}/, "two sets, not one");
  assert.match(html, /var flat = \{ mode: s\.mMode, l: s\.mLeft, w: s\.mWidth \};\s+takeSide\(d\.m\.left, flat\); takeSide\(d\.m\.right, flat\);/, "D7: an old preference was about reading, not about a pane");
  assert.match(html, /function applyMeasure\(side\) \{[\s\S]*?var m = layoutState\.m\[side\];/, "applyMeasure reads its own side");
  // Review #2: --m-l/--m-w are content-box quantities. Every producer must say so, or a drag
  // shifts the body by one padding-left per grab.
  const measureProducers = html.match(/SV\.clampMeasure\([^)]*\)/g) || [];
  assert.ok(measureProducers.length >= 2, "both the drag and applyMeasure clamp");
  measureProducers.forEach(call => assert.match(call, /measureSpace\(pane\)|space/, "clamped against the content-box width, never a border-box rect: " + call));
  assert.match(html, /var left0 = measureLeftOf\(pane, db\)/, "the drag's starting left is content-box relative too");
  assert.match(html, /function measureLeftOf\(pane, db\) \{[\s\S]*?- parseFloat\(getComputedStyle\(pane\)\.paddingLeft\)/, "…which is what subtracting padding-left buys");
});
t("T14/S8: the source-line gutter hangs outside the measure, folding back inline when cramped", () => {
  assert.match(html, /left: calc\(-44px - var\(--gx, 0px\)\);/, "hangs left of the rule, cancelling each block's own indent");
  assert.match(html, /b\.style\.setProperty\("--gx", geo\[i\]\.x \+ "px"\);/, "so a blockquote's padding doesn't carry its number right with it");
  assert.match(html, /line-height: var\(--gl, inherit\);/, "shares the block's first line box, so a heading's number doesn't float above its text");
  assert.match(html, /var w = document\.createTreeWalker\(b, NodeFilter\.SHOW_TEXT\), n, line = null;/, "measures the first character's line — a range over a list returns one rect per child block, not per line");
  assert.match(html, /b\.style\.setProperty\("--gt", geo\[i\]\.top \+ "px"\);/, "so both the offset and the line height are measured, not inferred");
  assert.match(html, /\.mrule:hover::before, \.mrule\.on::before \{ opacity: 1; \}/, "R1: the boundary line surfaces on approach or during a drag, not always");
  assert.match(html, /db\.classList\.toggle\("gutter-in", db\.getBoundingClientRect\(\)\.left - pane\.getBoundingClientRect\(\)\.left < 44\);/, "T3's clipping finding kept as the fallback trigger");
  assert.match(html, /var GUTTER_PAD = 46;/, "the default/full tiers reserve the strip, or every default view falls back to the inline gutter");
  assert.match(html, /\} else \{ db\.style\.setProperty\("--m-l", GUTTER_PAD \+ "px"\); db\.style\.removeProperty\("--m-w"\); \}/, "default tier offsets the measure instead of sitting on the pane edge");
  assert.match(html, /db\.style\.setProperty\("--m-w", \(measureSpace\(pane\) - FULL_PAD - Math\.max\(0, FULL_PAD - sbw\)\) \+ "px"\);/, "full tier's gaps look equal — the scrollbar already ate into the right one");
  assert.match(html, /var FULL_PAD = 16;/, "full leaves only what the gutter needs to stay inside the scrollport");
  assert.match(html, /var top = db\.offsetTop \+ "px", h = db\.offsetHeight \+ "px";/, "the lines start at the body and run its whole height, not one screenful");
});
t("T14/S10+S11: the find bar sits at the pane's bottom edge; the current hit is a reversed chip", () => {
  assert.match(html, /\.findbar \{[^}]*order: 99;\s*position: sticky; bottom: 0;/, "last in the flex column, stuck to the bottom");
  assert.match(html, /padding: 6px 0 8px; bottom: -20px;/, "rests 20px lower — the pane's own bottom padding — so it sits flush with the pane edge");
  assert.match(html, /\.rail i\.cur \{ right: -7px; background-color: var\(--fg\); z-index: 1; \}/, "reaches right, off the text; background-color never the shorthand — that resets background-clip and paints the whole 8px hit area");
  assert.match(html, /h\.hits\.forEach\(function \(hit, i\) \{ mark\(hit, i === h\.cur \? "cur" : "", i\); \}\);/, "the current index drives that class");
  assert.match(html, /::highlight\(sv-cur-left\), ::highlight\(sv-cur-right\) \{ background-color: var\(--s-todo\); color: var\(--bg\);/, "reversed, not a second shade of the same wash");
});
t("T6: Enter/⇧Enter in the find input steps without the global !typing guard blocking it", () => {
  assert.match(html, /var fi = t\.closest && t\.closest\("\[data-find-input\]"\);/, "checked independently of the shared `typing` flag");
  assert.match(html, /var es = fi\.closest\("#left"\) \? "left" : "right"; findHistPush\(PANES\[es\]\._hits\.q\); step\(es, e\.shiftKey \? -1 : 1\); \}/, "shift reverses direction, and stepping records the query");
  assert.match(html, /if \(h\.hits\[h\.cur\]\) scrollToInterval\(side, h\.hits\[h\.cur\]\);/, "step scrolls through the one scroll helper — no separate jump wrapper");
});

// --- railTop (016 T7: marker rail vertical position, pixel-derived per design) ---
t("railTop: contentH=0 / out-of-bounds clamp / midpoint", () => {
  assert.equal(SV.railTop(100, 0, 0, 500), 0);          // contentH===0 → 0, not NaN/Infinity
  assert.equal(SV.railTop(-50, 0, 1000, 500), 0);        // above content start clamps to the track's top
  assert.equal(SV.railTop(2000, 0, 1000, 500), 498);     // beyond content end clamps to trackH-2
  assert.equal(SV.railTop(500, 0, 1000, 500), 250);      // midpoint: 500/1000 * 500
});
t("T7: .rail is the pane's first child (every view kind, via paneHead) and paint redraws it", () => {
  assert.match(html, /return '<div class="rail"><\/div>' \+   \/\/ S6: pane's first child/, "rail comes before .doc-head in paneHead's own string");
  assert.match(html, /rail\(side\);   \/\/ S6: marker rail redraws alongside the highlights/, "paint always redraws the rail too");
});
t("T7: rail takes the first rect only (one mark per hit) and falls back to the containing block when hidden", () => {
  assert.match(html, /var rect = r\.getClientRects\(\)\[0\];/, "first rect only — a bold/code-boundary hit still gets one mark");
  // T11 fix: a client rect is viewport-relative, so marks drawn while scrolled down clamped to the
  // track top. The track maps the whole document, hence + scrollTop.
  assert.match(html, /SV\.railTop\(rect\.top \+ p\.scrollTop, pr\.top, contentH, trackH\)/, "mark position is document-absolute");
  assert.match(html, /var blk = a && a\.node\.parentElement && a\.node\.parentElement\.closest\(p\._blockSel\);/, "falls back to the hit's containing block (only remaining zero-rect cause: a collapsed trace row)");
});
t("T7: ensureHitVisible expands a collapsed trace row holding the current hit and marks its summary row .x", () => {
  assert.match(html, /var el = a\.node\.parentElement, dr = el && el\.closest\("tr\.trm-drow\[hidden\]"\); if \(!dr\) return;/, "finds the collapsed detail row via the hit's own node");
  assert.match(html, /dr\.hidden = false;\s+var tr = dr\.previousElementSibling; if \(tr && tr\.matches\("tr\[data-trx\]"\)\) tr\.classList\.add\("x"\);/, "sets .x too — renderTraceView() reads it from the old DOM to decide what reopens after a rebuild");
});

// --- selectionEcho (016 T8): no second selection listener, piggybacks the existing #cmt mouseup ---
t("T8: selectionEcho piggybacks the existing mouseup handler, not a second selection listener", () => {
  const m = html.match(/document\.addEventListener\("mouseup", function \(\) \{ {28}\/\/ show 💬 by the selection[\s\S]*?\n {2}\}\);/);
  assert.ok(m, "the #cmt mouseup handler block");
  assert.match(m[0], /updateSelectionEcho\(focus, own \? sel : null\);   \/\/ R6: T8/, "one echo call, driven by pane ownership alone");
  assert.match(m[0], /if \(own && doc\) \{/, "T14: the 💬 button still needs a doc, but the echo is pane-level — it must work on board/trace/search/recent too");
});
t("T8: updateSelectionEcho rejects short/multiline selections and never touches _hits", () => {
  assert.match(html, /if \(!text \|\| text\.length < 2 \|\| \/\\n\/\.test\(text\)\) \{ CSS\.highlights\.delete\(name\); return; \}/, "length<2 or a newline in the selection → no echo");
  assert.match(html, /hl\.priority = 150;/, "S5: between hit (100) and current (200)");
  assert.doesNotMatch(html.match(/function updateSelectionEcho[\s\S]*?\n  \}/)[0], /_hits\.hits|_hits\.q|_hits\.cur/, "reads only h.idx — never writes into the search model (S2's deliberate independence)");
});


// --- pinSlot (016 T9: color-slot allocation from the occupancy table) ---
t("pinSlot: empty table / reuses a released middle slot / full table cycles by pin count", () => {
  assert.equal(SV.pinSlot([false, false, false, false], 0), 0);
  assert.equal(SV.pinSlot([true, false, true, false], 2), 1);    // first free slot, not the next index
  assert.equal(SV.pinSlot([true, true, false, true], 3), 2);     // a released middle slot comes back
  assert.equal(SV.pinSlot([true, true, true, true], 4), 0);      // full → count % 4 (5th pin shares the 1st color)
  assert.equal(SV.pinSlot([true, true, true, true], 6), 2);
  assert.equal(SV.pinSlot(undefined, 0), 0);                     // no table yet
});
t("T9: h pins the selection, ⇧h clears this pane's pins, and the find box has its own pin button", () => {
  assert.match(html, /if \(e\.key === "h" && !\(e\.metaKey \|\| e\.ctrlKey \|\| e\.altKey\) && !typing\) \{ pinCurrent\(focus\); \}/, "h pins/unpins, never while typing");
  assert.match(html, /if \(e\.key === "H" && e\.shiftKey && !\(e\.metaKey \|\| e\.ctrlKey \|\| e\.altKey\) && !typing\) \{ clearPins\(focus\); \}/, "⇧h clears");
  assert.match(html, /data-find-pin title="pin this term"/, "inside the input h is typing, so the find term needs a button");
  assert.match(html, /var pinSide = t\.closest\("#left"\) \? "left" : "right"; pin\(pinSide, PANES\[pinSide\]\._hits\.q\);/, "the button pins the current query");
});
t("T9: pin toggles on the same term and only frees a slot nobody else holds", () => {
  const fn = html.match(/function pin\(side, term\) \{[\s\S]*?\n  \}/)[0];
  assert.match(fn, /if \(at >= 0\) \{ unpin\(side, at\); return; \}/, "same word again → unpin (h is a toggle)");
  assert.match(fn, /var slot = SV\.pinSlot\(h\.slotUsed, h\.pins\.length\);/, "slot comes from the occupancy table, not the array index");
  assert.match(html, /var shared = h\.pins\.some\(function \(pn\) \{ return pn\.slot === gone\.slot; \}\);\s+if \(!shared\) h\.slotUsed\[gone\.slot\] = false;/, "past 4 pins two entries share a slot — don't free it under the other one");
});
t("T9: paint merges pins by slot under hit priority, and the rail stays outside the Highlight-API guard", () => {
  const fn = html.match(/function paint\(side\) \{[\s\S]*?\n  \}/)[0];
  assert.match(fn, /var hl = bySlot\[pn\.slot\] \|\| \(bySlot\[pn\.slot\] = new Highlight\(\)\);/, "one highlight per color, not per pin");
  assert.match(fn, /hl\.priority = i;/, "S11: pin order stacks pins; still below hit's 100");
  assert.match(fn, /\}\s+\}\s+rail\(side\);   \/\/ S6: marker rail redraws alongside the highlights\s+\}$/, "rail is drawn even where CSS.highlights is unsupported");
});
t("T9: rail marks pins with their slot class so the track color matches the highlight", () => {
  assert.match(html, /h\.pins\.forEach\(function \(pn\) \{ pn\.hits\.forEach\(function \(hit\) \{ mark\(hit, "p" \+ pn\.slot\); \}\); \}\);/, "R8: pinned items get marks too");
  assert.match(html, /\.rail i\.p0 \{ background-color: color-mix\(in srgb, var\(--s-active\) 55%, transparent\); \}/, "slot 0 rail colour matches its ::highlight rule, muted, and set without the shorthand");
});

// --- reset (016 T10): the render tails that bypass afterRender ---
t("T10: all seven bypass paths call reset", () => {
  const hooks = html.match(/\/\/ D18 hookpoint \d/g) || [];
  assert.equal(hooks.length, 7, "five render .catch branches + the trace placeholder + the board drawer");
  // 9 = the function itself + the labelled seven + restoreView's empty-memory path. A bare extra
  // call means someone added a hookpoint without labelling it.
  assert.equal((html.match(/reset\(side\)/g) || []).length, 9, "no unlabelled reset call sites");
  [1, 2, 3, 4, 5, 6, 7].forEach(n => assert.match(html, new RegExp("D18 hookpoint " + n + "\\b"), "hookpoint " + n + " is labelled"));
  assert.match(html, /'<p class="tr-loading">计算中…<\/p>';\s+reset\(side\); return; \}/, "the trace early return resets before returning");
});
t("T10: reset drops everything derived from the dead DOM and blanks the readout", () => {
  const fn = html.match(/function reset\(side\) \{[\s\S]*?\n  \}/)[0];
  assert.match(fn, /h\.idx = null; h\.hits = \[\]; h\.cur = -1;/, "the index and its hits are gone");
  assert.match(fn, /h\.pins\.forEach\(function \(pn\) \{ pn\.hits = \[\]; \}\);/, "pin hits are derived too — empty the array, don't leave stale ranges or undefined");
  assert.match(fn, /hlNames\(side\)\.forEach/, "unregisters every highlight this pane owns");
  assert.match(fn, /var track = p\.querySelector\("\.rail"\); if \(track\) track\.innerHTML = "";/, "clears the marker rail");
  assert.match(fn, /el\.textContent = ""; el\.classList\.remove\("zero"\);/, "R14: blank readout, not a 0/0 that reads as a real zero-hit result");
  assert.doesNotMatch(fn, /h\.q = |h\.pins = \[\]/, "the terms survive — the view is often right back");
});
t("T10: a settled mermaid diagram invalidates content, not just geometry", () => {
  assert.match(html, /invalidateContent\(side\); \}\)   \/\/ S9 hookpoint 4/, "the inner .then swaps the source <pre> for the SVG");
  assert.match(html, /function invalidateContent\(side\) \{\s+PANES\[side\]\._idxDirty = true; invalidateGeometry\(side\);/, "rides the geometry frame so N diagrams cost one rescan");
  assert.match(html, /if \(p\._idxDirty\) \{ p\._idxDirty = false; reindex\(side\); \}/, "the rAF callback rescans before relocating the band");
});

// --- view memory (016 T11): view identity, MRU store, content anchor ---
t("viewKey: one key shape per view kind, pane-prefixed, unknown kind degrades", () => {
  assert.equal(SV.viewKey("left", { kind: "doc", tree: "dev", rel: "a/b.md" }), "left|doc:dev/a/b.md");
  assert.equal(SV.viewKey("right", { kind: "doc", tree: "dev", rel: "a/b.md" }), "right|doc:dev/a/b.md");
  assert.equal(SV.viewKey("left", { kind: "diff", card: "xg-skills/016" }), "left|diff:xg-skills/016");
  assert.equal(SV.viewKey("left", { kind: "trace", card: "xg-skills/016" }), "left|trace:xg-skills/016");
  assert.equal(SV.viewKey("left", { kind: "search", q: "pane" }), "left|search:pane");
  assert.equal(SV.viewKey("left", { kind: "recent" }), "left|recent");
  assert.equal(SV.viewKey("left", { kind: "board" }, "cbdb"), "left|board:cbdb");
  assert.equal(SV.viewKey("left", { kind: "board" }, ""), "left|board:");   // all-projects board is its own view
  assert.equal(SV.viewKey("left", { kind: "future" }), "left|future");      // degrades, never throws
});
t("recallPut: MRU order, re-put moves to front, cap evicts from the map too", () => {
  let s = SV.recallPut(null, "k1", { y: 1 }, 2);
  s = SV.recallPut(s, "k2", { y: 2 }, 2);
  assert.deepEqual(s.order, ["k2", "k1"]);
  s = SV.recallPut(s, "k1", { y: 9 }, 2);
  assert.deepEqual(s.order, ["k1", "k2"], "re-put moves the key to the front, no duplicate");
  assert.equal(s.map.k1.y, 9, "and overwrites its entry");
  s = SV.recallPut(s, "k3", { y: 3 }, 2);
  assert.deepEqual(s.order, ["k3", "k1"]);
  assert.equal(s.map.k2, undefined, "the evicted key's entry is dropped, not orphaned in the map");
});
t("anchorOf / anchorFind: index hit, index moved (prefix rescue), both miss", () => {
  const blocks = ["alpha block text", "beta block text", "gamma block text"];
  assert.deepEqual(SV.anchorOf(blocks, 1), { b: 1, p: "beta block text" });
  assert.equal(SV.anchorOf(blocks, 5), null);
  assert.equal(SV.anchorFind(blocks, { b: 1, p: "beta block text" }), 1);
  // two blocks inserted above → the recorded index now points elsewhere, the prefix still finds it
  assert.equal(SV.anchorFind(["new", "also new", ...blocks], { b: 1, p: "beta block text" }), 3);
  assert.equal(SV.anchorFind(blocks, { b: 1, p: "deleted block" }), -1);
  assert.equal(SV.anchorFind(blocks, null), -1);
});

t("T11: the entering flag is set on every entry path and burned on read", () => {
  assert.match(html, /p\._entering = true;   \/\/ S12/, "navigate sets it before render");
  assert.match(html, /if \(p\._hi > 0\) \{ leaveView\(side\); p\._hi--; p\._entering = true;/, "back sets it");
  assert.match(html, /PANES\[side\]\._entering = true; setFocus\(side\); render\(side\);   \/\/ S12: a history jump is an entry/, "the history dropdown sets it");
  assert.match(html, /L\._entering = R\._entering = true;   \/\/ S12/, "swapPanes sets it for both panes");
  assert.match(html, /var entering = p\._entering; p\._entering = false;/, "afterRender reads once and clears");
  const rv = html.match(/function refreshView\(side\) \{[\s\S]*?\n  \}/)[0];
  assert.doesNotMatch(rv, /_entering/, "D12 priority 3: the re-render path must never set it");
});
t("T11: restore yields to an explicit target and never writes an empty anchor", () => {
  assert.match(html, /if \(entering\) restoreView\(side, !\(p\._view && p\._view\.line\)\);/, "D12 priority 1 beats 2: a search hit's line suppresses the anchor scroll");
  assert.match(html, /if \(!v \|\| !p\._blockSel \|\| !blockEls\(p\)\.length\) return;/, "an error panel has no blocks — don't overwrite good memory");
  assert.match(html, /if \(!e\) return;   \/\/ nothing remembered for this view yet/, "a field write can't conjure an entry out of nothing");
  assert.match(html, /else if \(typeof e\.y === "number"\) p\.scrollTop = e\.y;/, "D5: pixel fallback when the anchor is gone");
});

t("T12: the query and pin terms are remembered, and cleared field by field", () => {
  assert.match(html, /q: h\.q, p: pinTerms\(h\) \};   \/\/ R11/, "leaveView stores the terms, never the slots");
  assert.match(html, /writeField\(side, "q", ""\);   \/\/ R13: the query is gone for good/, "Esc drops only the query");
  assert.match(html, /writeField\(side, "p", \[\]\);/, "⇧h drops only the pins");
  assert.match(html, /function pinTerms\(h\) \{ return h\.pins\.map/, "one name for the remembered shape of the pin list");
  assert.match(html, /writeField\(side, "p", pinTerms\(h\)\);   \/\/ R13, single pin/, "unpin rewrites the remaining list");
  const wf = html.match(/function writeField\(side, field, value\) \{[\s\S]*?\n  \}/)[0];
  assert.match(wf, /e\[field\] = value;/, "one field at a time — Esc must not take the pins with it");
});
t("T12: entering a view adopts exactly what that view remembers", () => {
  const rv = html.match(/function restoreView\(side, scroll\) \{[\s\S]*?\n  \}/)[0];
  assert.match(rv, /h\.q = e\.q \|\| ""; h\.hits = \[\]; h\.cur = e\.q \? 0 : -1;/, "no memory → empty, so the previous doc's query doesn't follow along (R11); a restored query lands on its first hit, not a 0/n readout");
  assert.match(rv, /h\.pins = \[\]; h\.slotUsed = \[false, false, false, false\];/, "pins likewise start from this view's memory");
  assert.match(rv, /var slot = SV\.pinSlot\(h\.slotUsed, h\.pins\.length\);/, "slots are reassigned on reflow — color was never identity");
  assert.match(rv, /if \(h\.q && !p\._findOpen\) findOpen\(side, true\);/, "a remembered query reopens the bar quietly, without stealing the caret");
  assert.match(rv, /if \(h\.q \|\| h\.pins\.length\) reindex\(side\); else reset\(side\);/, "entering a view that remembers nothing must unregister the last view's highlights — reindex returns early there");
  assert.match(html, /if \(entering\) restoreView\(side, !\(p\._view && p\._view\.line\)\);/, "the explicit target suppresses only the scroll, not the term reflow");
});

t("T13: every exit from a view writes through the one named hook", () => {
  const calls = (html.match(/(?<!function )leaveView\((side|"left"|"right")\)/g) || []);
  assert.equal(calls.length, 7, "navigate + back + history + closeright + swapPanes' two + pagehide");
  [1, 2, 3, 4, 5].forEach(n => assert.match(html, new RegExp("write point " + n + " of 5"), "write point " + n + " is labelled"));
  assert.match(html, /window\.addEventListener\("pagehide", function \(\) \{ visiblePanes\(\)\.forEach\(function \(side\) \{ leaveView\(side\); \}\); \}\);/, "closing the tab never reaches the five entries");
  assert.match(html, /leaveView\("left"\); leaveView\("right"\);   \/\/ write point 5 of 5\s+var tmp = \{ h: L\._hist/, "swapPanes writes BEFORE the histories move — the key carries the pane");
});

t("R17: the find box seeds from the selection, remembers past queries, and waits before scanning", () => {
  assert.match(html, /var seed = quiet \? "" : selectedIn\(side\);/, "opening with something selected means you want to find that");
  assert.match(html, /return \(t\.length >= 2 && t\.length <= 80 && !\/\\n\/\.test\(t\)\) \? t : "";/, "a paragraph-sized or multiline selection isn't a query");
  assert.match(html, /var FIND_DEBOUNCE = 160;/, "a one-letter query matches half the document — don't pay for that on the way to a word");
  assert.match(html, /clearTimeout\(p\._findT\);\s+p\._findT = setTimeout\(function \(\) \{ find\(side, inp\.value\); \}, FIND_DEBOUNCE\);/, "each keystroke restarts the wait");
  assert.match(html, /lsSet\("sv-findhist", JSON\.stringify\(SV\.recentPush\(findHist\(\), q, 20\)\)\);/, "the recall list reuses the existing MRU primitive");
  assert.match(html, /findHistStep\(fi\.closest\("#left"\) \? "left" : "right", e\.key === "ArrowUp" \? 1 : -1\); \}/, "↑/↓ walks it, shell-style");
  assert.match(html, /findHistPush\(p\._hits\.q\); p\._histAt = null;/, "closing the box records what was searched");
});

console.log("\n" + pass + " shell-helper tests passed");
