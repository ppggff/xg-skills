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

console.log("\n" + pass + " shell-helper tests passed");
