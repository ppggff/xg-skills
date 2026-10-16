// Source and behaviour rules for the refined frontend (/v2): shell-v2.html, v2.css + v2-widths.css and the v2-*.js area
// files. The pure helpers they share with the classic shell are tested in test-shell.mjs (sv.js); what
// needs a browser is in shots-v2.mjs.  Run: node tools/viewer/test-shell-v2.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import assert from "node:assert";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const read = (f) => readFileSync(join(here, f), "utf8");
const AREAS = ["core", "tree", "board", "time", "reader", "search", "find", "todo", "edit"];
const page = read("shell-v2.html"), css = read("v2-themes.css") + "\n" + read("v2.css") + "\n" + read("v2-widths.css") + "\n" + read("v2-time.css");
const js = Object.fromEntries(AREAS.map((a) => [a, read(`v2-${a}.js`)]));
const allJs = Object.values(js).join("\n");
const viewerPy = read("../viewer.py");

let pass = 0;
function t(name, fn) { fn(); pass++; console.log("ok  -", name); }

t("the table's column-hiding classes name nothing else: no other CSS rule styles them", () => {
  const hide = /V\.hideCls = h => \(h \? " ([\w-]+)" \+ h : ""\)/.exec(js.board);
  assert.ok(hide, "V.hideCls keeps its one-prefix form");
  for (const k of ["n", "p"]) {
    const cls = hide[1] + k, uses = css.split("\n").filter((l) => new RegExp(`\\.${cls}(?![\\w-])`).test(l));
    assert.ok(uses.length >= 1 && uses.every((l) => l.includes("columns marked to hide")), `.${cls} is styled outside the hide rule: ${uses.join(" | ")}`);
    assert.doesNotMatch(allJs, new RegExp(`<t[dh] class="[^"]*\\bh${k}\\b`), `a table cell still names the old h${k} class`);
  }
});

t("todo rows have no in-place edit; a double-click and the new button open the source editor", () => {
  assert.doesNotMatch(js.todo, /data-ted=|class="tedit"/);
  assert.match(js.reader, /b\("tedit", "doc", "编辑这个 todo 文件"\)/);
  assert.match(js.edit, /V\.editTodoAt = /);
  assert.match(js.todo, /"dblclick"[\s\S]*V\.editTodoAt\(/);
  assert.match(js.todo, /data-tnew[\s\S]*V\.editTodoAt\("inbox\.md"/);
});

t("a checked box keeps its place: the tick is out of flow; the editor's line height stays modest for WebKit's caret", () => {
  assert.match(css, /\.md input\[type=checkbox\]:checked::before \{[^}]*position: absolute/);
  assert.match(css, /\.ted \.thl, \.ted \.tta \{[^}]*\/1\.45 var\(--code\)/);
});

t("a table group heading keeps its distance whether or not a dots row sits above it", () => {
  assert.match(css, /\.tbl tbody tr:not\(\.gh\):not\(\.tfold\) \+ tr\.gh td \{ padding-top: 37px; \}/);
});

t("a multi-line todo: the todo view counts the further lines; the reader renders a todo file as any doc", () => {
  assert.doesNotMatch(js.reader, /breaks: true|todoReadable/);
  assert.match(js.todo, /it\.more\.length \? `<span class="tmore"/);
  assert.equal((js.todo.match(/\$\{moreHTML\(it\)\}/g) || []).length, 2);   // the list form and the table
  assert.match(css, /#tip \.tfull \{ white-space: pre-wrap;/);
});

t("a loose list reads as tight: an item's last paragraph has no bottom margin", () => {
  assert.match(css, /\.md li > p:last-child \{ margin-bottom: 0; \}/);
});

t("046 Req-52/53: an amber card answers the pointer; closing the detail keeps the card selected", () => {
  assert.match(css, /:root\[data-theme\^="amber"\] \.card:hover \{ border-color: var\(--mu\); \}/);
  const close = /function closeDetail\(\) \{([\s\S]*?)\n  \}/.exec(js.board)[1];
  assert.doesNotMatch(close, /sel = null|classList\.remove\("sel"\)/);
  assert.match(js.board, /V\.layer\(10, \(\) => V\.view === "board" && !!sel && !V\.W\.dc, closeDetail\)/);
});

t("the tree renders before the first data: no ext list is an empty one", () => {
  assert.match(js.tree, /const ext = D\.tree\.ext \|\| \[\];/);
  assert.doesNotMatch(js.tree, /D\.tree\.ext\.length/);
});

t("054 round 2: the progress bar is one bar; done requirements list last; the detail's columns keep their own rows; the indicator starts at now", () => {
  assert.match(js.board, /<i style="--p:\$\{\(c\.ok \/ c\.req\)\.toFixed\(3\)\}"><\/i>/);
  assert.doesNotMatch(js.board, /--k:\$\{i\}/);
  assert.match(js.board, /rq\.slice\(\)\.sort\(\(a, b\) => \(a\.st === "已验证"\) - \(b\.st === "已验证"\)\)/);
  assert.match(js.board, /<div class="bdg" data-st="\$\{c\.st\}"><div class="bdl">/);
  assert.match(css, /\.bdl \{ display: grid; gap: 6px; align-content: start;/);
  assert.doesNotMatch(css, /grid-row: 1 \/ span 5/);
  assert.match(css, /:is\(#bscroll, #tscroll\) \{[^}]*scrollbar-gutter: stable;/);
  assert.match(js.time, /if \(V\.timeCur === null\) V\.timeCur = now;/);
  assert.match(js.time, /V\.click\("\[data-tmnow\]"/);
});

t("054 round 3: a small screen keeps the detail low and shows its progress as a number beside the governance", () => {
  assert.match(css, /:is\(\.app\.narrow, \.app\.short\):not\(\.hdset\) #bdet \{ max-height: 40%; \}/);
  assert.match(css, /:is\(\.app\.narrow, \.app\.short\) #bdet \.rhead \{ display: none; \} :is\(\.app\.narrow, \.app\.short\) \.bdr \{ margin-top: 0; \}/);
  assert.doesNotMatch(css, /#bdet \{ max-height: 62%; \}/);
  assert.match(js.board, /<span class="hfr">　\$\{done\}<\/span>/);
});

t("the table and the time form span a tray's outer width", () => {
  assert.match(css, /:is\(#bscroll, #tscroll\)\.tbl-form \{ padding: 14px var\(--bG\) 40px; \}/);
  assert.match(css, /#bscroll\.tm-form \{ padding: 0 var\(--bG\) 40px; \}/);
});

t("054: a time row names the card only, no done count", () => {
  assert.doesNotMatch(js.time, /<span class="s">\$\{esc\(c\.slug\)\}<\/span>\$\{c\.lite/);
});

t("every area file parses", () => { for (const a of AREAS) new vm.Script(js[a], { filename: `v2-${a}.js` }); });

t("Q-4: each file stays under ~800 lines", () => {
  for (const [f, src] of [["shell-v2.html", page], ["v2.css", read("v2.css")], ["v2-widths.css", read("v2-widths.css")], ["v2-themes.css", read("v2-themes.css")], ["v2-time.css", read("v2-time.css")], ...AREAS.map((a) => [`v2-${a}.js`, js[a]])])
    assert.ok(src.split("\n").length <= 820, `${f} has ${src.split("\n").length} lines`);
});

t("the page loads the area files in order: marked, sv, core first, then the areas", () => {
  const srcs = [...page.matchAll(/<script src="\/assets\/([^"]+)"><\/script>/g)].map((m) => m[1]);
  assert.deepStrictEqual(srcs, ["marked.min.js", "sv.js", ...AREAS.map((a) => `v2-${a}.js`)]);
});

// --- Inv-2: the security baseline does not loosen ---
t("Inv-2: no inline script and no inline event handlers in the page", () => {
  assert.doesNotMatch(page, /<script(?![^>]*\bsrc=)[^>]*>/);
  assert.doesNotMatch(page, /<[^>]+\son[a-z]+\s*=/i);
});
t("Inv-2: every /assets/ file the page or the stylesheet names is in viewer.py's allowlist", () => {
  const names = new Set([...page.matchAll(/\/assets\/([\w.-]+)/g), ...css.matchAll(/\/assets\/([\w.-]+)/g), ...allJs.matchAll(/\/assets\/([\w.-]+)/g)].map((m) => m[1]));
  const allow = viewerPy.match(/ASSETS = \{[\s\S]*?\n(?=\S)/)[0];
  for (const n of names) {
    const m = /^v2-(\w+)\.js$/.exec(n);
    assert.ok(allow.includes(`"${n}"`) || (m && allow.includes(`"${m[1]}"`)), `${n} not allowlisted`);
  }
});
t("Inv-2: the area files fetch only same-origin paths", () => {
  for (const m of allJs.matchAll(/\b(?:fetch|V\.api|V\.json)\(\s*(["'`])([^"'`]*)/g)) assert.match(m[2], /^\/(api|raw|assets)\//, "fetch target " + m[2]);
  assert.doesNotMatch(allJs, /https?:\/\/(?!www\.w3\.org)/, "no absolute URL in the area files");
});

// --- Inv-3: the two frontends' local memory never mixes ---
t("Inv-3: no classic sv-* key literal anywhere in v2", () => {
  assert.doesNotMatch(allJs, /["'`]sv-/);
});
t("Inv-3: localStorage is touched only inside V.store", () => {
  for (const a of AREAS) {
    const uses = (js[a].match(/localStorage/g) || []).length;
    if (a !== "core") assert.strictEqual(uses, 0, `v2-${a}.js uses localStorage directly`);
  }
  const store = js.core.match(/V\.store = \{[\s\S]*?\n {2}\};/)[0];
  assert.strictEqual((js.core.match(/localStorage/g) || []).length, (store.match(/localStorage/g) || []).length);
  assert.match(store, /"svd2-" \+ k/);
});

// --- Inv-5: layout judges width, never the device ---
t("Inv-5: no device sniffing", () => {
  assert.doesNotMatch(allJs + css, /userAgent|navigator\.platform|maxTouchPoints|\(pointer:|\(hover:/);
});

// --- Inv-6-c: single-key hotkeys never fire with a modifier, nor inside a text field ---
t("Inv-6-c: the key dispatcher lets modified keys and typing through", () => {
  const kd = js.core.match(/document\.addEventListener\("keydown"[\s\S]*?\n {2}\}\);/)[0];
  assert.match(kd, /if \(e\.metaKey \|\| e\.ctrlKey \|\| e\.altKey\) return;/);
  assert.match(kd, /closest\("input,textarea,select,\[contenteditable\]"\)\) return;/);
  assert.ok(kd.indexOf("e.altKey) return") < kd.indexOf("keys[e.key]"), "modifier check precedes the hotkey lookup");
  assert.doesNotMatch(allJs.replace(kd, ""), /addEventListener\("keydown", e => \{\s*if \(e\.key === "[a-z]"/, "no second single-key listener outside the dispatcher");
});

t("046 Req-2: a letter chord is ⌘ or ctrl+shift; plain ctrl stays with the text field", () => {
  assert.match(js.core, /V\.isChord = e => e\.metaKey \|\| \(e\.ctrlKey && e\.shiftKey\);/);
  assert.doesNotMatch(allJs, /\(e\.metaKey \|\| e\.ctrlKey\) && (!e\.altKey && )?V\.chord/, "every chord check goes through V.isChord");
  assert.match(js.edit, /const cmd = V\.isChord\(e\)/);
});
t("046 Req-3: no native dialog — confirm, prompt and alert go through V.ask", () => {
  assert.doesNotMatch(allJs, /(^|[^.\w])(confirm|prompt|alert)\(/m);
  assert.match(page, /<div class="qo" id="ask" hidden>/);
});

// --- Inv-6: the event and render rules the classic shell learned (KB viewer-architecture) ---
t("Inv-6-a: one Esc closes one layer, the topmost open one", () => {
  const kd = js.core.match(/document\.addEventListener\("keydown"[\s\S]*?\n {2}\}\);/)[0];
  assert.match(kd, /if \(e\.key === "Escape"\) \{ const l = layers\.find\(x => x\.isOpen\(\)\); if \(l\) \{ e\.preventDefault\(\); l\.close\(\); \} return; \}/);
  assert.match(js.core, /layers\.sort\(\(a, b\) => b\.pri - a\.pri\)/, "layers are kept highest priority first");
});
t("Inv-6-a: input-level Esc consumers stop the event before the layer chain sees it", () => {
  assert.match(js.find, /inp\.addEventListener\("keydown", e => \{\s*if \(V\.isChord\(e\) && V\.chord\[e\.key\.toLowerCase\(\)\]\) return;[^\n]*\n\s*e\.stopPropagation\(\);/, "find box: only the ⌘ chords pass, Esc is stopped");
  assert.match(js.search, /\$\("#qIn"\)\.addEventListener\("keydown", e => \{\s*e\.stopPropagation\(\);/, "quick open box");
  assert.match(js.search, /else if \(e\.key === "Escape"\) \{ e\.stopPropagation\(\); e\.target\.blur\(\); \}/, "search box");
});
t("Inv-6-a: closing a text-field layer gives the focus back, so later keys are not swallowed", () => {
  assert.match(js.search, /\$\("#qIn"\)\.blur\(\)/);
  assert.match(js.find, /if \(f\.contains\(document\.activeElement\)\) document\.activeElement\.blur\(\);/);
});
t("Inv-6-b: the find debounce is cancelled on close and on leaving, flushed on Enter", () => {
  const close = js.find.match(/function close\(k\) \{[\s\S]*?\n {2}\}/)[0];
  assert.match(close, /clearTimeout\(h\.t\)/);
  assert.match(js.find, /V\.on\("leave", k => \{ clearTimeout\(H\[k\]\.t\);/);
  assert.match(js.find, /e\.preventDefault\(\); clearTimeout\(h\.t\);[^\n]*\n\s*if \(h\.q !== inp\.value\.toLowerCase\(\)\) find\(k, inp\.value\);/);
});
t("Inv-6-d: highlight names carry the pane; old registrations are dropped before painting; no Range is kept", () => {
  assert.match(js.find, /const names = k => \["hit-" \+ k, "hitc-" \+ k, "echo-" \+ k, "p0-" \+ k, "p1-" \+ k, "p2-" \+ k, "p3-" \+ k\];/);
  const paint = js.find.match(/function paint\(k\) \{[\s\S]*?\n {2}\}/)[0];
  assert.ok(paint.indexOf("CSS.highlights.delete") < paint.indexOf("CSS.highlights.set"), "delete precedes set");
  assert.match(js.find, /function fresh\(\) \{ return \{ q: "", hits: \[\], cur: -1, idx: null, pins: \[\], slots:/);
  assert.doesNotMatch(js.find, /\.(range|ranges|rng)\s*=/i, "no Range stored on state");
  for (const p of ["A", "B"]) for (const n of ["hit", "hitc", "echo", "p0", "p1", "p2", "p3"]) assert.ok(css.includes(`::highlight(${n}-${p})`), `css for ${n}-${p}`);
});
t("Inv-6-e: a failed render drops what hung off the last good one", () => {
  const rendered = js.find.match(/V\.on\("rendered", \(k, entering\) => \{[\s\S]*?\n {2}\}\);/)[0];
  assert.match(rendered, /if \(!root\(k\)\) \{ h\.hits = \[\]; h\.cur = -1; if \(HL\) names\(k\)\.forEach\(n => CSS\.highlights\.delete\(n\)\); rail\(k\); count\(k\); return; \}/);
  const fail = js.reader.match(/function fail\(k, loc, e\) \{[\s\S]*?\n {2}\}/)[0];
  assert.match(fail, /V\.emit\("rendered", k, true\)/, "the error branch announces its (empty) content");
  assert.match(js.reader, /if \(opt\.entering\) \{ p\.cur = null; \$\$\("\.curline,\.lastmark", p\.body\)\.forEach\(x => x\.remove\(\)\); \}/);
});
t("Inv-6-f: scroll writers in priority order — explicit target, then (entering) the remembered place, else stay", () => {
  const place = js.reader.match(/function place\(k, loc, opt, keepTop\) \{[\s\S]*?\n {2}\}/)[0];
  const i0 = place.indexOf("if (!opt.entering) { b.scrollTop = keepTop; return; }"), i1 = place.indexOf("loc.xid"), i2 = place.indexOf("restorePlace(k)");
  assert.ok(i0 > 0 && i0 < i1 && i1 < i2, "keep → target → anchor");
  assert.match(js.board, /const b = \$\("#bscroll"\), top = b\.scrollTop, kc = \$\("\.kcols", b\), left = kc \? kc\.scrollLeft : 0;/, "board re-render keeps both scroll axes");
});
t("Inv-6-g: nothing sticks to a bottom edge — the sticky elements are heads at the top: the table's and the time form's", () => {
  const sticky = [...css.matchAll(/([^{}]+)\{[^}]*position:\s*sticky[^}]*\}/g)];
  assert.strictEqual(sticky.length, 2);
  assert.match(sticky[0][0], /\.tbl th[^{]*\{[^}]*top: 0/); assert.match(sticky[1][0], /\.tm-head \{[^}]*top: 0/);
});

t("round 5: iOS keeps the text size on turning to landscape", () => {
  assert.match(css, /html \{ -webkit-text-size-adjust: 100%; text-size-adjust: 100%; \}/);
});

t("043 Req-4: the history labels uncommitted changes, not a sha", () => {
  assert.match(js.reader, /const shaLabel = sha => \(sha === "worktree" \? "未提交" : sha\.slice\(0, 7\)\);/);
});

console.log(`${pass} v2 shell tests passed`);
