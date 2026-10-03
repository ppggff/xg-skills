// Source and behaviour rules for the refined frontend (/v2): shell-v2.html, v2.css and the v2-*.js area
// files. The pure helpers they share with the classic shell are tested in test-shell.mjs (sv.js); what
// needs a browser is in shots-v2.mjs.  Run: node tools/viewer/test-shell-v2.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import assert from "node:assert";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const read = (f) => readFileSync(join(here, f), "utf8");
const AREAS = ["core", "tree", "board", "reader", "search", "find"];
const page = read("shell-v2.html"), css = read("v2.css");
const js = Object.fromEntries(AREAS.map((a) => [a, read(`v2-${a}.js`)]));
const allJs = Object.values(js).join("\n");
const viewerPy = read("../viewer.py");

let pass = 0;
function t(name, fn) { fn(); pass++; console.log("ok  -", name); }

t("every area file parses", () => { for (const a of AREAS) new vm.Script(js[a], { filename: `v2-${a}.js` }); });

t("Q-4: each file stays under ~800 lines", () => {
  for (const [f, src] of [["shell-v2.html", page], ["v2.css", css], ...AREAS.map((a) => [`v2-${a}.js`, js[a]])])
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

console.log(`${pass} v2 shell tests passed`);
