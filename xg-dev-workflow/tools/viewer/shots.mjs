#!/usr/bin/env node
// shots.mjs — viewport screenshot harness for the status viewer (zero dependencies).
//
// Drives the system Chrome (headless) over the DevTools protocol with Node's built-in
// WebSocket, opens each view kind at each viewport, and writes one PNG per pair plus a
// manifest with the browser / node versions, the viewer's /api/rev token and per-shot
// layout measurements (pane rects, page overflow). `--compare A B` diffs two runs byte
// by byte and by measurement, so a before/after pair can be judged without eyeballing.
//
// Run (viewer already up, or it is started on the url's port and stopped on exit):
//   node tools/viewer/shots.mjs --out /tmp/shots/before
//   node tools/viewer/shots.mjs --compare /tmp/shots/before /tmp/shots/after
//   node tools/viewer/shots.mjs --scenario crossing,overlay     (behavioural checks, no files)
//   node tools/viewer/shots.mjs --viewports 390x844 --views doc --eval "<js>"   (print an expression per viewport/view)
// Options: --url http://127.0.0.1:8790/  --viewports 390x844,768x1024,1024x768,1920x1080
//   --views board,doc,search,diff,recent  --doc dev/<rel> (default: the newest card's design.md)
//   --card <project>/<NNN> (default: derived from --doc)  --q <term>
//   --chrome <path>  --keep-storage (default clears localStorage per viewport for a cold start)
//   --mask-head (hide the pane header before each shot: the one region allowed to differ across a change)
//   --no-freeze (by default Date.now is pinned per run so relative times render the same in a re-run)
//   --touch <file> (the refresh scenario bumps this file's mtime to trigger the live refresh)
// A --url ending in /v2 drives the refined frontend instead: its views, measurements and scenarios
// live in shots-v2.mjs; everything else (Chrome, CDP, the viewer lifecycle, --compare) is shared.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, readFileSync, existsSync, utimesSync, readdirSync, rmSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DEF = {
  url: "http://127.0.0.1:8790/",
  viewports: "390x844,768x1024,1024x768,1920x1080",
  views: "board,doc,search,diff,recent",
  doc: null,     // default: the newest card's design.md in the dev tree (resolved at run time)
  card: null,    // default: derived from --doc as <project>/<NNN>
  q: "viewer",
  chrome: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
};

function parseArgs(argv) {
  const o = { ...DEF, compare: null, out: null, scenario: null, eval: null, keepStorage: false, maskHead: false, freeze: true, touch: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--compare") { o.compare = [argv[++i], argv[++i]]; continue; }
    if (a === "--keep-storage") { o.keepStorage = true; continue; }
    if (a === "--mask-head") { o.maskHead = true; continue; }
    if (a === "--no-freeze") { o.freeze = false; continue; }
    if (a.startsWith("--")) { o[a.slice(2)] = argv[++i]; continue; }
    throw new Error("unexpected argument: " + a);
  }
  return o;
}

// --- CDP client -------------------------------------------------------------
class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.listeners = []; }
  static async connect(url) {
    const ws = new WebSocket(url);
    await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(new Error("ws connect failed: " + url)); });
    const c = new CDP(ws);
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && c.pending.has(m.id)) {
        const { ok, no } = c.pending.get(m.id); c.pending.delete(m.id);
        m.error ? no(new Error(m.error.message)) : ok(m.result);
      } else if (m.method) c.listeners.forEach((f) => f(m));
    };
    return c;
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params, sessionId }));
    return new Promise((ok, no) => this.pending.set(id, { ok, no }));
  }
  waitEvent(method, sessionId, timeout = 15000) {
    return new Promise((ok, no) => {
      const t = setTimeout(() => { off(); no(new Error("timeout waiting " + method)); }, timeout);
      const f = (m) => { if (m.method === method && (!sessionId || m.sessionId === sessionId)) { clearTimeout(t); off(); ok(m.params); } };
      const off = () => { this.listeners = this.listeners.filter((x) => x !== f); };
      this.listeners.push(f);
    });
  }
  close() { this.ws.close(); }
}

const TMP = process.env.TMPDIR || "/tmp";

// Leftovers of runs that died before stopChrome (kill -9, crash). Their Chrome may still be
// up as an orphan, so close it over its DevToolsActivePort first. A live pid is a concurrent run.
async function sweepStaleProfiles() {
  for (const name of readdirSync(TMP)) {
    const m = name.match(/^sv-shots-(\d+)$/);
    if (!m || +m[1] === process.pid) continue;
    try { process.kill(+m[1], 0); continue; } catch (e) { if (e.code !== "ESRCH") continue; }
    const dir = join(TMP, name);
    try {
      const [port, path] = readFileSync(join(dir, "DevToolsActivePort"), "utf8").split("\n");
      const cdp = await CDP.connect(`ws://127.0.0.1:${port}${path}`);
      const closed = new Promise((ok) => cdp.ws.addEventListener("close", ok));
      cdp.send("Browser.close").catch(() => {});
      await Promise.race([closed, sleep(5000)]);
    } catch {}
    try { rmSync(dir, { recursive: true, force: true, maxRetries: 10 }); } catch {}   // Chrome may still be exiting
  }
}

async function launchChrome(chromePath) {
  await sweepStaleProfiles();
  const userDir = join(TMP, "sv-shots-" + process.pid);
  const child = spawn(chromePath, ["--headless=new", "--remote-debugging-port=0", "--user-data-dir=" + userDir,
    "--no-first-run", "--no-default-browser-check", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1"],
    { stdio: ["ignore", "ignore", "pipe"] });
  const wsUrl = await new Promise((ok, no) => {
    let buf = "";
    child.stderr.on("data", (d) => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) ok(m[1]); });
    child.on("exit", (code) => no(new Error("chrome exited " + code + "\n" + buf)));
    setTimeout(() => no(new Error("chrome did not announce DevTools\n" + buf)), 15000);
  });
  return { child, wsUrl, userDir, cdp: null };
}

// A signalled Chrome skips its shutdown and leaves its code-sign clone under
// $TMPDIR/../X/com.google.Chrome.code_sign_clone; Browser.close lets it clean up.
async function stopChrome({ child, cdp, userDir }) {
  const exited = child.exitCode !== null || child.signalCode !== null
    ? Promise.resolve() : new Promise((ok) => child.once("exit", ok));
  if (cdp) cdp.send("Browser.close").catch(() => {}); else child.kill();
  if (!(await Promise.race([exited.then(() => true), sleep(5000).then(() => false)]))) { child.kill("SIGKILL"); await exited; }
  cdp?.close();
  rmSync(userDir, { recursive: true, force: true });
}

// --- viewer lifecycle ---------------------------------------------------------
async function viewerUp(url) {
  try { const r = await fetch(new URL("/api/rev", url), { signal: AbortSignal.timeout(1500) }); return r.ok ? await r.json() : null; }
  catch { return null; }
}
async function ensureViewer(url) {
  const rev = await viewerUp(url);
  if (rev) return { rev, stop: () => {} };
  const port = new URL(url).port || "80";
  const child = spawn("python3", [join(HERE, "..", "viewer.py"), "--no-browser", "--port", port], { stdio: "ignore" });
  for (let i = 0; i < 40; i++) { await sleep(250); const r = await viewerUp(url); if (r) return { rev: r, stop: () => child.kill() }; }
  child.kill(); throw new Error("viewer did not come up on " + url);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- views ---------------------------------------------------------------------
// The app script is an IIFE, so views are driven the way a user drives them: nav buttons,
// a synthetic anchor through the document-level `[data-nav]` click handler, Enter in the
// search box. `ready` is the predicate that says the view has rendered.
const VIEW = {
  board:  (o) => ({ drive: `document.querySelector('[data-go="board"]').click()`, ready: "!!document.querySelector('#left .card, #left .btable, #left .board, #left .sdots')" }),
  recent: (o) => ({ drive: `document.querySelector('[data-go="recent"]').click()`, ready: "!!document.querySelector('#left h2.commit')" }),
  doc:    (o) => { const [tree, ...rest] = o.doc.split("/"); return { drive: navAnchor({ nav: "doc", tree, rel: rest.join("/") }), ready: "!!document.querySelector('#left .docbody')" }; },
  search: (o) => ({ drive: `(() => { const s = document.getElementById("search"); s.value = ${JSON.stringify(o.q)};
      s.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })); })()`, ready: "!!document.querySelector('#left .hit, #left .none, #left h2.sec')" }),
  diff:   (o) => ({ drive: navAnchor({ nav: "diff", card: o.card }), ready: "!!document.querySelector('#left pre.diff, #left .muted, #left .broken')" }),
};
function navAnchor(data) {
  return `(() => { const a = document.createElement("a"); ${Object.entries(data).map(([k, v]) => `a.dataset.${k} = ${JSON.stringify(v)};`).join(" ")}
    document.body.appendChild(a); a.click(); a.remove(); })()`;
}
let UI = null;   // the frontend under test: classic (below) or shots-v2.mjs, picked from --url at the bottom
const MEASURE = `(() => { const r = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect();
  const cs = getComputedStyle(e); return cs.display === "none" ? { display: "none" } : { x: Math.round(b.x), w: Math.round(b.width), h: Math.round(b.height) }; };
  return { side: r("#side"), left: r("#left"), right: r("#right"), toc: r("#toc"), head: r("#left .doc-head"),
    headOverflow: (() => { const h = document.querySelector("#left .doc-head"); return h ? h.scrollWidth - h.clientWidth : null; })(),
    pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    inner: [innerWidth, innerHeight] }; })()`;

async function evalIn(cdp, sid, expression, awaitPromise = false) {
  const r = await cdp.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise }, sid);
  if (r.exceptionDetails) throw new Error("page threw: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
  return r.result.value;
}
async function waitFor(cdp, sid, predicate, timeout = 10000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) { if (await evalIn(cdp, sid, predicate)) return; await sleep(100); }
  throw new Error("timeout: " + predicate);
}

async function resolveDoc(o) {
  if (!o.doc) {
    const tree = await (await fetch(new URL("/api/tree", o.url))).json();
    const designs = tree.dev.map((e) => e.path).filter((p) => /\/\d{3}-[^/]+\/design\.md$/.test(p)).sort();
    if (!designs.length) throw new Error("no <project>/<NNN>-<slug>/design.md in the dev tree; pass --doc");
    o.doc = "dev/" + designs[designs.length - 1];
  }
  if (!o.card) { const m = o.doc.match(/^dev\/([^/]+)\/(\d{3})-/); if (!m) throw new Error("cannot derive --card from " + o.doc); o.card = m[1] + "/" + m[2]; }
}

// --- browser session -----------------------------------------------------------
async function session(o, fn) {
  const cleanups = [];
  const cleanup = async () => { while (cleanups.length) { try { await cleanups.pop()(); } catch {} } };
  const onSignal = () => { cleanup().finally(() => process.exit(130)); };
  process.once("SIGINT", onSignal); process.once("SIGTERM", onSignal);
  try {
    const viewer = await ensureViewer(o.url); cleanups.push(viewer.stop);
    await resolveDoc(o);
    const chrome = await launchChrome(o.chrome); cleanups.push(() => stopChrome(chrome));
    const cdp = chrome.cdp = await CDP.connect(chrome.wsUrl);
    const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
    const { sessionId: sid } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
    await cdp.send("Page.enable", {}, sid); await cdp.send("Runtime.enable", {}, sid);
    const frozenNow = Date.now();
    if (o.freeze) await cdp.send("Page.addScriptToEvaluateOnNewDocument", { source: `Date.now = () => ${frozenNow};` }, sid);
    const centerOf = async (sel) => {   // viewport centre of an element, scrolled into view first
      const c = await evalIn(cdp, sid, `(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return null; e.scrollIntoView({ block: "center" });
        const r = e.getClientRects()[0] || e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);   // first line box: a link wrapped over two lines has empty space at its bounding-box centre
      if (!c) throw new Error("no element " + sel);
      return c;
    };
    const ctx = {
      viewer, chrome: (await cdp.send("Browser.getVersion")).product,
      eval: (expr, awaitPromise) => evalIn(cdp, sid, expr, awaitPromise),
      wait: (pred, timeout) => waitFor(cdp, sid, pred, timeout),
      viewport: (w, h) => cdp.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false }, sid),
      load: async () => {
        await cdp.send("Page.navigate", { url: o.url }, sid); await cdp.waitEvent("Page.loadEventFired", sid);
        if (!o.keepStorage) { await evalIn(cdp, sid, "localStorage.clear(); true"); await cdp.send("Page.reload", {}, sid); await cdp.waitEvent("Page.loadEventFired", sid); }
        await waitFor(cdp, sid, UI.ready);
      },
      go: async (name) => { const { drive, ready } = UI.VIEW[name](o); await evalIn(cdp, sid, drive + "; true"); await waitFor(cdp, sid, ready); await sleep(400); },
      click: (sel) => evalIn(cdp, sid, `(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return false; e.click(); return true; })()`),
      shot: async () => {
        if (o.maskHead) await evalIn(cdp, sid, `document.querySelectorAll(${JSON.stringify(UI.mask)}).forEach(h => h.style.visibility = 'hidden'); true`);
        const png = Buffer.from((await cdp.send("Page.captureScreenshot", { format: "png" }, sid)).data, "base64");
        if (o.maskHead) await evalIn(cdp, sid, `document.querySelectorAll(${JSON.stringify(UI.mask)}).forEach(h => h.style.visibility = ''); true`);
        return png;
      },
      measure: () => evalIn(cdp, sid, UI.MEASURE),
      sleep, touchFile: (f) => { const now = new Date(); utimesSync(f, now, now); },
      key: async (key, mods = 0) => {   // a real key press (mods: 1 alt, 2 ctrl, 4 meta, 8 shift)
        const code = key.length === 1 ? "Key" + key.toUpperCase() : key, text = key.length === 1 && !(mods & 6) ? key : undefined;
        await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key, code, text, modifiers: mods, windowsVirtualKeyCode: key === "Escape" ? 27 : key === "Enter" ? 13 : key.length === 1 ? key.toUpperCase().charCodeAt(0) : 0 }, sid);
        await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key, code, modifiers: mods }, sid);
      },
      type: (text) => cdp.send("Input.insertText", { text }, sid),
      touch: (on) => cdp.send("Emulation.setTouchEmulationEnabled", { enabled: on, maxTouchPoints: 1 }, sid),
      tap: async (sel) => {   // a finger tap at the element's centre (touchStart + touchEnd)
        const c = await centerOf(sel);
        await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: c[0], y: c[1] }] }, sid);
        await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }, sid);
      },
      wheel: (x, y, dy) => cdp.send("Input.dispatchMouseEvent", { type: "mouseWheel", x, y, deltaX: 0, deltaY: dy }, sid),   // a real wheel at a point
      media: (features) => cdp.send("Emulation.setEmulatedMedia", { features }, sid),   // e.g. [{ name: "prefers-color-scheme", value: "dark" }]
      mouseAt: (x, y) => cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y }, sid),   // no scrolling first
      mouseMove: async (sel) => { const c = await centerOf(sel); await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: c[0], y: c[1] }, sid); },
    };
    return await fn(ctx);
  } finally { await cleanup(); process.off("SIGINT", onSignal); process.off("SIGTERM", onSignal); }
}

async function shoot(o) {
  mkdirSync(o.out, { recursive: true });
  const manifest = await session(o, async (ctx) => {
    const manifest = { taken: new Date().toISOString(), url: o.url, viewerRev: ctx.viewer.rev, node: process.version, chrome: ctx.chrome,
      viewports: o.viewports, views: o.views, doc: o.doc, card: o.card, q: o.q, maskHead: o.maskHead, frozenClock: o.freeze, shots: {} };
    for (const vp of o.viewports.split(",")) {
      const [w, h] = vp.split("x").map(Number);
      await ctx.viewport(w, h); await ctx.load();
      for (const name of o.views.split(",")) {
        await ctx.go(name);
        const file = `${vp}-${name}.png`;
        writeFileSync(join(o.out, file), await ctx.shot());
        manifest.shots[file] = await ctx.measure();
        process.stdout.write(`${file}  overflow=${manifest.shots[file].pageOverflow} head=${manifest.shots[file].headOverflow}\n`);
      }
    }
    return manifest;
  });
  writeFileSync(join(o.out, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
  console.log("wrote " + join(o.out, "manifest.json"));
}

const J = JSON.stringify;
// --- scenarios: behaviour that a cold screenshot cannot show -----------------------
const SCENARIO = {
  // A tablet rotating crosses the breakpoint without a reload: the right pane closes on the way
  // down and comes back on the way up; inline column widths never survive below the breakpoint.
  async crossing(ctx, check) {
    await ctx.viewport(1024, 768); await ctx.load(); await ctx.go("doc");
    await ctx.click("[data-mirror]"); await ctx.wait("document.querySelector('#right').classList.contains('show')");
    const rects = "JSON.stringify(['#side','#left','#right','#toc'].map(s => { const r = document.querySelector(s).getBoundingClientRect(); return [Math.round(r.x), Math.round(r.width)]; }))";
    const before = await ctx.eval(rects);
    check("1024: mirror opened the right pane", await ctx.eval("document.querySelector('#right').classList.contains('show')"));
    check("1024: #left carries an inline width while the right pane is open", await ctx.eval("document.querySelector('#left').style.width !== ''"));
    await ctx.viewport(768, 1024); await ctx.wait("document.documentElement.classList.contains('narrow')");
    check("768: html.narrow set by the change listener", await ctx.eval("document.documentElement.classList.contains('narrow')"));
    check("768: right pane hidden", await ctx.eval("getComputedStyle(document.querySelector('#right')).display === 'none'"));
    check("768: sidebar hidden (overlay closed)", await ctx.eval("getComputedStyle(document.querySelector('#side')).display === 'none'"));
    check("768: inline widths cleared", await ctx.eval("['#left','#toc','#side'].every(s => document.querySelector(s).style.width === '')"));
    check("768: content pane spans the viewport", await ctx.eval("Math.abs(document.querySelector('#left').getBoundingClientRect().width - 768) < 2"));
    await ctx.viewport(1024, 768); await ctx.wait("!document.documentElement.classList.contains('narrow')");
    check("1024 again: right pane restored", await ctx.eval("document.querySelector('#right').classList.contains('show')"));
    check("1024 again: sidebar back as a column", await ctx.eval("getComputedStyle(document.querySelector('#side')).position !== 'fixed' && getComputedStyle(document.querySelector('#side')).display !== 'none'"));
    await sleep(300);
    const after = await ctx.eval(rects);
    check(`1024 again: pane rects as before the round trip (${before} → ${after})`, before === after);
  },
  // Below the breakpoint the sidebar and the TOC open as overlays from their buttons and close on a pick.
  async overlay(ctx, check) {
    await ctx.viewport(390, 844); await ctx.load(); await ctx.go("doc");
    check("390: sidebar starts hidden", await ctx.eval("getComputedStyle(document.querySelector('#side')).display === 'none'"));
    await ctx.click("[data-side]");
    check("☰ opens the sidebar overlay with a scrim", await ctx.eval("document.querySelector('#side').classList.contains('open') && document.querySelector('#scrim').classList.contains('show') && getComputedStyle(document.querySelector('#side')).position === 'fixed'"));
    check("390: the desktop collapse button is out of reach inside the overlay", await ctx.eval("getComputedStyle(document.querySelector('[data-collapse=\"side\"]')).display === 'none'"));
    await ctx.click('#side [data-go="recent"]'); await ctx.wait("!!document.querySelector('#left h2.commit')");
    check("picking Recent inside it navigates and closes the overlay", await ctx.eval("!document.querySelector('#side').classList.contains('open') && !document.querySelector('#scrim').classList.contains('show')"));
    await ctx.click("[data-side]"); await ctx.eval("const s = document.getElementById('search'); s.value = 'viewer'; s.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); true");
    await ctx.wait("!!document.querySelector('#left .hit, #left h2.sec')");
    check("searching from inside the overlay closes it too", await ctx.eval("!document.querySelector('#side').classList.contains('open')"));
    await ctx.click('[data-find="left"]'); await ctx.wait("!!document.querySelector('#left [data-find-input]')"); await ctx.click("[data-side]");   // find first: a tap outside an open drawer only closes it (041 Req-9)
    await ctx.eval("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); true");
    check("Escape closes the overlay before the find bar under it", await ctx.eval("!document.querySelector('#side').classList.contains('open') && !!document.querySelector('#left [data-find-input]')"));
    await ctx.go("doc");
    await ctx.click("[data-tocbtn]");
    check("☷ opens the TOC overlay", await ctx.eval("document.querySelector('#toc').classList.contains('open') && getComputedStyle(document.querySelector('#toc')).position === 'fixed'"));
    check("TOC overlay has entries", await ctx.eval("document.querySelectorAll('#toc a[data-toc]').length > 3"));
    await ctx.click("#toc a[data-toc]");
    check("picking an entry closes the TOC overlay", await ctx.eval("!document.querySelector('#toc').classList.contains('open')"));
    await ctx.click("[data-tocbtn]"); await ctx.click("#scrim");
    check("tapping the scrim closes it", await ctx.eval("!document.querySelector('#toc').classList.contains('open') && !document.querySelector('#scrim').classList.contains('show')"));
    check("390: head does not overflow", (await ctx.measure()).headOverflow === 0);
  },
  // The pane head's buttons work at every width (no ? button: the ? key opens help), and the head never overflows.
  async buttons(ctx, check) {
    for (const [w, h] of [[390, 844], [1024, 768]]) {
      await ctx.viewport(w, h); await ctx.load(); await ctx.go("doc");
      check(`${w}: doc head does not overflow`, (await ctx.measure()).headOverflow === 0);
      await ctx.click('[data-find="left"]'); await ctx.wait("!!document.querySelector('#left [data-find-input]')");
      check(`${w}: ⌕ opens the find bar`, await ctx.eval("!!document.querySelector('#left [data-find-input]')"));
      check(`${w}: no ? button in the head`, await ctx.eval("!document.querySelector('#left [data-help]')"));
      await ctx.click("[data-quick]"); check(`${w}: ⌘K button opens quick open`, await ctx.eval("document.querySelector('#qo').classList.contains('show')"));
      await ctx.eval("const i = document.getElementById('qoInput'); i.value = 'viewer'; i.dispatchEvent(new Event('input', { bubbles: true })); true");
      await ctx.wait("!!document.querySelector('#qo .qrow.qfall')");
      await ctx.click("#qo .qrow.qfall"); await ctx.wait("!!document.querySelector('#left .hit, #left h2.sec')");
      check(`${w}: the last quick-open row runs a content search`, await ctx.eval("!!document.querySelector('#left .hit, #left h2.sec')"));
    }
    await ctx.go("doc"); await ctx.click("[data-mirror]"); await ctx.wait("document.querySelector('#right').classList.contains('show')"); await sleep(300);
    check("1024 split panes: neither head overflows", await ctx.eval("['#left','#right'].every(s => { const h = document.querySelector(s + ' .doc-head'); return h && h.scrollWidth <= h.clientWidth; })"));
    await ctx.click("[data-closeright]"); await ctx.wait("!document.querySelector('#right').classList.contains('show')");
    await ctx.click("[data-tocbtn]"); check("1024: ☷ hides the TOC column", await ctx.eval("!document.querySelector('#toc').classList.contains('show')"));
    await ctx.go("board"); await ctx.go("doc");
    check("1024: the hidden TOC stays hidden across views", await ctx.eval("!document.querySelector('#toc').classList.contains('show')"));
    await ctx.click("[data-tocbtn]"); check("1024: ☷ shows it again", await ctx.eval("document.querySelector('#toc').classList.contains('show')"));
  },
  // The board's forms: the table below the breakpoint, grid above, one button cycling grid → kanban → table → dots (041),
  // the pick remembered; a stored pick of the retired rows form reads as the table.
  async forms(ctx, check) {
    await ctx.viewport(390, 844); await ctx.load(); await ctx.go("board");
    check("390: the table form by default", await ctx.eval("!!document.querySelector('#left .btable') && !document.querySelector('#left .card') && !document.querySelector('#left .row')"));
    check("390: a table row shows id (with the state dot), card, progress, next and time", await ctx.eval("[...document.querySelectorAll('#left .btable .trow')].every(r => r.cells.length === 5 && r.cells[0].querySelector('.dot'))"));
    check("390: the table has row hairlines only and no header row", await ctx.eval("(() => { const td = getComputedStyle(document.querySelector('#left .btable td')); return td.borderLeftWidth === '0px' && td.borderRightWidth === '0px' && !document.querySelector('#left .btable th'); })()"));
    check("390: row lines are inset — none under the id cell, one under the title", await ctx.eval("(() => { const r = [...document.querySelectorAll('#left .btable .trow')].find(x => x.nextElementSibling); if (!r) return false; const a = getComputedStyle(r.cells[0]), b = getComputedStyle(r.cells[1]); return a.borderBottomColor === 'rgba(0, 0, 0, 0)' && b.borderBottomColor !== 'rgba(0, 0, 0, 0)'; })()"));
    check("390: the table fits the pane", await ctx.eval("[...document.querySelectorAll('#left .btable')].every(t => t.scrollWidth <= t.clientWidth + 1) && document.querySelector('#left').scrollWidth <= document.querySelector('#left').clientWidth"));
    const aligned = `(() => { const ts = [...document.querySelectorAll("#left .btable")], pane = document.querySelector("#left .btable").parentElement.getBoundingClientRect().width;
      const lefts = t => [...t.rows[0].cells].map(c => Math.round(c.getBoundingClientRect().left));
      const one = t => [...t.rows].every(r => [0, 2, 4].every(i => { const g = document.createRange(); g.selectNodeContents(r.cells[i]); return g.getBoundingClientRect().height < 20; }));
      return ts.length > 1 && ts.every(t => lefts(t).join() === lefts(ts[0]).join() && Math.abs(t.getBoundingClientRect().width - pane) < 2 && one(t)); })()`;
    check("390: columns line up across the project groups, each table spans the pane, id, progress and time on one line", await ctx.eval(aligned));
    check("390: board head and chips sit on single lines", await ctx.eval("(() => { const h = document.querySelector('#left .doc-head'), f = document.querySelector('#left .board-filters'); return h.getBoundingClientRect().height < 48 && f.getBoundingClientRect().height < 40 && f.scrollWidth >= f.clientWidth; })()"));
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .sdots')"); await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board:not(.kanban) .card')");   // table → dots → grid (041: the signal form follows the table)
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board.kanban')");                // grid → kanban
    check("the one button cycles the forms and the pick is remembered under sv-board-mode", await ctx.eval("localStorage.getItem('sv-board-mode') === 'kanban' && localStorage.getItem('sv-board-kanban') === null"));
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .btable')");                     // kanban → table
    check("the kanban leads on to the table", await ctx.eval("document.querySelector('[data-bmode]').textContent.trim() === 'table'"));
    await ctx.click("#left .btable .trow .tid"); check("tapping a table row opens the detail drawer and marks the row", await ctx.eval("!!document.querySelector('#left .card-detail') && !!document.querySelector('#left .trow.selected')"));
    await ctx.eval("localStorage.setItem('sv-board-mode', 'rows'); location.reload(); true"); await ctx.wait("!!document.querySelector('#tree a.file')"); await ctx.go("board");
    check("a stored rows pick (retired) reads as the table", await ctx.eval("!!document.querySelector('#left .btable') && !document.querySelector('#left .row')"));
    await ctx.viewport(768, 1024); await ctx.load(); await ctx.go("board");
    check("768: columns line up across the project groups, each table spans the pane, id, progress and time on one line", await ctx.eval(aligned));
    await ctx.viewport(1920, 1080); await ctx.load(); await ctx.go("board");
    check("1920: grid by default", await ctx.eval("!!document.querySelector('#left .board:not(.kanban) .card')"));
    await ctx.eval("localStorage.setItem('sv-board-kanban', '1'); true"); await ctx.eval("location.reload(); true"); await ctx.wait("!!document.querySelector('#left .board.kanban')");
    check("1920: the old kanban boolean still selects kanban", true);
  },
  // Below the breakpoint a tap on a doc link navigates without the hover preview; above it the
  // preview still opens on a real mouse hover.
  async touch(ctx, check) {
    const link = '#left .docbody a[data-nav="doc"]';
    await ctx.viewport(390, 844); await ctx.load(); await ctx.touch(true); await ctx.go("doc");
    const before = await ctx.eval("document.querySelector('#left .crumb .base').textContent");
    await ctx.tap(link); await sleep(700);
    check("390 + touch: tapping a doc link navigates", await ctx.eval("document.querySelector('#left .crumb .base').textContent") !== before);
    check("390 + touch: no hover preview pops up", await ctx.eval("!document.getElementById('lp') || getComputedStyle(document.getElementById('lp')).display === 'none'"));
    await ctx.click("[data-quick]"); await ctx.eval("const i = document.getElementById('qoInput'); i.value = 'viewer'; i.dispatchEvent(new Event('input', { bubbles: true })); true");
    await ctx.wait("!!document.querySelector('#qo .qrow.qfall')"); await ctx.tap("#qo .qrow.qfall"); await ctx.wait("!!document.querySelector('#left .hit, #left h2.sec')");
    check("390 + touch: tapping quick open's last row runs a content search", await ctx.eval("!!document.querySelector('#left .hit, #left h2.sec')"));
    await ctx.touch(false); await ctx.viewport(1024, 768); await ctx.load(); await ctx.go("doc");
    await ctx.mouseMove(link); await sleep(600);
    check("1024 + mouse: the hover preview still opens", await ctx.eval("getComputedStyle(document.getElementById('lp')).display !== 'none'"));
  },
  // Hit areas below the breakpoint: head buttons at desktop size, tree rows ≥ 30px, board table rows ≥ 30px.
  async targets(ctx, check) {
    await ctx.viewport(390, 844); await ctx.load(); await ctx.go("doc");
    const h = async (sel) => {   // [count, min height] over the visible matches — an empty set must not pass
      const r = await ctx.eval(`(() => { const hs = [...document.querySelectorAll(${JSON.stringify(sel)})].filter(e => e.offsetParent).map(e => e.getBoundingClientRect().height); return [hs.length, Math.min(...hs)]; })()`);
      return r[0] ? r[1] : -1;
    };
    const fs = (sel) => ctx.eval(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); return e ? parseFloat(getComputedStyle(e).fontSize) : -1; })()`);
    check("390: head buttons keep their desktop size and the head stays on one line", (await h("#left .doc-head .iconbtn")) < 30 && (await ctx.eval("document.querySelector('#left .doc-head').getBoundingClientRect().height")) < 48);
    await ctx.click('[data-find="left"]'); await ctx.wait("!!document.querySelector('#left [data-find-input]')");
    check("390: the find bar fits the pane", await ctx.eval("(() => { const f = document.querySelector('#left .findbar'); return f.scrollWidth <= f.clientWidth && document.querySelector('#left').scrollWidth <= document.querySelector('#left').clientWidth; })()"));
    check("390: the find input is 16px (no zoom on focus)", (await fs("#left [data-find-input]")) >= 16);
    await ctx.click("[data-quick]"); await ctx.eval("const i = document.getElementById('qoInput'); i.value = 'problem-statement'; i.dispatchEvent(new Event('input', { bubbles: true })); true");
    await ctx.wait("document.querySelectorAll('#qo .qrow').length > 1");
    check("390: quick open's list never scrolls sideways", await ctx.eval("(() => { const l = document.querySelector('#qo .qlist'); return l.scrollWidth <= l.clientWidth && document.querySelector('#qo').getBoundingClientRect().right <= innerWidth; })()"));
    check("390: the quick-open input is 16px (no zoom on focus)", (await fs("#qoInput")) >= 16);
    await ctx.eval("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); true");
    await ctx.click("[data-side]");
    check("390: tree rows ≥ 30px", (await h("#tree summary")) >= 30);
    check("390: tree text ≥ 13px", (await fs("#tree summary")) >= 13);
    await ctx.click("#scrim"); await ctx.go("board");
    check("390: board table rows ≥ 30px", (await h("#left .btable .trow")) >= 30);
    check("390: table-row meta text ≥ 12px", (await fs("#left .btable .tprog")) >= 12);
  },
  // Below the breakpoint wide content scrolls inside its own box and the pane never scrolls sideways;
  // the inline source-line gutter (it would skew pre, table and hr) is not drawn. 375 = the narrowest phone.
  async wide(ctx, check) {
    await ctx.viewport(375, 667); await ctx.load(); await ctx.go("doc");
    await ctx.eval(`(() => { const w = "wide_identifier_without_breaks_".repeat(4);
      document.querySelector("#left .docbody").insertAdjacentHTML("afterbegin",
        '<table data-srcline="1" id="wt"><tr><td>' + w + '</td><td>' + w + '</td></tr></table>' +
        '<pre data-srcline="2" id="wp"><code>' + w + w + '</code></pre><hr data-srcline="3" id="wh">' +
        '<p data-srcline="4" id="wl">see <code>' + w + '</code> and <a href="#">' + w + '</a></p>' +
        '<div class="mermaid" id="wm"><svg viewBox="0 0 900 300" width="100%" style="max-width: 900px;"></svg></div>');
      return true; })()`);
    await sleep(200);
    const pane = "document.querySelector('#left')";
    check("375: the pane never scrolls sideways", await ctx.eval(`${pane}.scrollWidth <= ${pane}.clientWidth`));
    const fits = (id) => `(() => { const e = document.getElementById("${id}"); return e.scrollWidth <= e.clientWidth + 1 && e.getBoundingClientRect().right <= ${pane}.getBoundingClientRect().right + 1; })()`;
    check("375: a wide table and code block wrap to the pane — no nested scrollers", (await ctx.eval(fits("wt"))) && (await ctx.eval(fits("wp"))));
    check("375: a diagram fits the pane", await ctx.eval(`(() => { const m = document.getElementById("wm"); return m.querySelector("svg").getBoundingClientRect().width <= m.clientWidth + 1; })()`));
    check("375: source line numbers hang in the left margin, off the text", await ctx.eval(`["wt", "wp", "wh", "wl"].every(id => { const e = document.getElementById(id), b = getComputedStyle(e, "::before");
      return b.position === "absolute" && b.display !== "none" && parseFloat(b.left) + e.getBoundingClientRect().left >= ${pane}.getBoundingClientRect().left && parseFloat(b.left) + parseFloat(b.width) <= 0; })`));
    if (await ctx.eval("document.querySelectorAll('#left .docbody pre > code.language-mermaid, #left .docbody .mermaid:not(#wm)').length")) {
      await ctx.wait("[...document.querySelectorAll('#left .docbody .mermaid:not(#wm)')].every(m => m.querySelector('svg, .broken'))");
      check("375: a rendered diagram fits the pane", await ctx.eval(`[...document.querySelectorAll("#left .docbody .mermaid:not(#wm)")].every(m => m.querySelector("svg, .broken").getBoundingClientRect().width <= m.clientWidth + 1)`));
    } else console.log("note - wide: the doc has no mermaid block; only the synthetic diagram was checked");
    await ctx.go("board");
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .sdots')"); await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board:not(.kanban) .card')");   // table → dots → grid (041: the signal form follows the table)
    check("375: grid cards stay inside the pane", await ctx.eval(`[...document.querySelectorAll("#left .card")].every(c => c.getBoundingClientRect().right <= ${pane}.getBoundingClientRect().right) && ${pane}.scrollWidth <= ${pane}.clientWidth`));
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board.kanban')");                // grid → kanban
    check("375: a kanban column is no wider than the board", await ctx.eval(`(() => { const b = document.querySelector("#left .board.kanban"); return [...b.querySelectorAll(".col")].every(c => c.getBoundingClientRect().width <= b.clientWidth); })()`));
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .btable')");                     // kanban → table
  },
  // The second phone pass: the sidebar top folds, the card detail stays in the pane, the visit history is a
  // ▾ button, the board has a table form, and chrome text is back near desktop sizes (375 = the narrowest phone).
  async phone(ctx, check, o) {
    await ctx.viewport(375, 667); await ctx.load(); await ctx.go("board");
    const pane = "document.querySelector('#left')", noSideways = `${pane}.scrollWidth <= ${pane}.clientWidth`;
    const fs = (sel) => ctx.eval(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); return e ? parseFloat(getComputedStyle(e).fontSize) : -1; })()`);
    await ctx.click("[data-side]");
    check("375: scope and search start folded and the tree starts near the top", await ctx.eval("(() => { const t = document.querySelector('.side-top'); return !!t && getComputedStyle(t).display === 'none' && document.querySelector('#tree').getBoundingClientRect().top < 120; })()"));
    check("375: the fold toggle shows the scope", await ctx.eval("document.querySelector('[data-sidetop] .scope').textContent === (document.getElementById('proj').value || 'all')"));
    check("375: Board · Recent · code sit on one line", await ctx.eval("new Set([...document.querySelectorAll('#side .navbtn')].map(b => Math.round(b.getBoundingClientRect().top))).size === 1"));
    check("375: the desktop collapse button stays out of the phone's brand row", await ctx.eval("getComputedStyle(document.querySelector('#side [data-collapse]')).display === 'none'"));
    check("375: the nav entries are as tall as the scope button", await ctx.eval("(() => { const a = document.querySelector('[data-sidetop]').getBoundingClientRect().height; return [...document.querySelectorAll('#side .navbtn')].filter(b => b.offsetParent).every(b => Math.abs(b.getBoundingClientRect().height - a) < .5); })()"));
    check("375: … as equal segments", await ctx.eval("(() => { const w = [...document.querySelectorAll('#side .navbtn')].filter(b => b.offsetParent).map(b => b.getBoundingClientRect().width); return w.length === 3 && Math.max(...w) - Math.min(...w) <= 1; })()"));
    check("375: the nav row sits a little below the brand row", await ctx.eval("document.querySelector('#side .navbtns').getBoundingClientRect().top - document.querySelector('#side .brand').getBoundingClientRect().bottom >= 10"));
    await ctx.eval("(() => { const g = document.getElementById('gitwebEntry'); g.addEventListener('click', (e) => e.preventDefault(), { once: true }); g.click(); return true; })()");
    check("375: tapping 浏览代码 closes the sidebar overlay", await ctx.eval("!document.getElementById('side').classList.contains('open') && !document.getElementById('scrim').classList.contains('show')"));
    await ctx.click("[data-side]");
    check("375: the file-filter ⌕ sits right after the scope toggle", await ctx.eval("(() => { const a = document.querySelector('[data-sidetop]'), f = document.querySelector('[data-treefilter]'); return a.nextElementSibling === f && Math.abs(a.getBoundingClientRect().top - f.getBoundingClientRect().top) < 1; })()"));
    await ctx.click("[data-sidetop]");
    check("375: the toggle unfolds scope and search", await ctx.eval("!!document.getElementById('proj').offsetParent && !!document.getElementById('search').offsetParent"));
    check("375: tree text 13px, inputs stay 16px", (await fs("#tree a.file")) === 13 && (await fs("#search")) === 16);
    await ctx.click("[data-sidetop]");
    check("375: tree rows 30px, the help hint and the file filter are out of the way", await ctx.eval("(() => { const r = document.querySelector('#tree summary').getBoundingClientRect().height; return r <= 31 && getComputedStyle(document.querySelector('#side .hint')).display === 'none' && getComputedStyle(document.getElementById('filterbox')).display === 'none'; })()"));
    await ctx.eval("document.querySelectorAll('#tree details').forEach(d => d.open = true); true"); await sleep(300);
    check("375: a long file name drags sideways on its own row, the tree does not", await ctx.eval("(() => { const f = [...document.querySelectorAll('#tree a.file')].sort((a, b) => b.scrollWidth - a.scrollWidth)[0], t = document.getElementById('tree'); return f.scrollWidth > f.clientWidth && getComputedStyle(f).overflowX === 'auto' && t.scrollWidth <= t.clientWidth; })()"));
    await ctx.eval("document.querySelectorAll('#tree details').forEach(d => d.open = false); true");
    await ctx.click("[data-treefilter]");
    check("375: ⌕ opens the file filter", await ctx.eval("!!document.getElementById('treeFilter').offsetParent"));
    await ctx.eval("(() => { const i = document.getElementById('treeFilter'); i.value = 'design'; i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()");
    await ctx.click("[data-treefilter]");
    check("375: an active filter stays in view after ⌕ folds it", await ctx.eval("!!document.getElementById('treeFilter').offsetParent"));
    await ctx.eval("(() => { const i = document.getElementById('treeFilter'); i.value = ''; i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()");
    await ctx.click("#scrim");
    check("375: crumb and table-row meta 12px", (await fs("#left .crumb")) === 12 && (await fs("#left .btable .tprog")) === 12);
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .sdots')"); await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board:not(.kanban) .card')");   // table → dots → grid (041: the signal form follows the table)
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board.kanban')");                // grid → kanban
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .btable')");                     // kanban → table
    check("375: the table form has id (with the state dot), card, progress, next and time per row", await ctx.eval("[...document.querySelectorAll('#left .btable .trow')].every(r => r.cells.length === 5 && r.cells[0].querySelector('.dot')) && !!document.querySelector('#left .btable .trow .ttitle a')"));
    check("375: the table fits the pane without scrolling sideways", await ctx.eval(`${noSideways} && [...document.querySelectorAll("#left .btable")].every(t => t.scrollWidth <= t.clientWidth + 1)`));
    await ctx.click("#left .btable .trow .tid");
    check("375: tapping a table row opens the detail drawer and marks the row", await ctx.eval("!!document.querySelector('#left .card-detail') && !!document.querySelector('#left .trow.selected')"));
    check("the table pick is remembered", await ctx.eval("localStorage.getItem('sv-board-mode') === 'table'"));
    const keys = await ctx.eval("[...document.querySelectorAll('#left .trow')].map(r => r.dataset.key)");
    let matrix = false;
    for (const key of keys.slice(0, 8)) {
      await ctx.eval(navAnchor({ nav: "trace", card: key }) + "; true");
      await ctx.wait("!!document.querySelector('#left .doc-head') && !document.querySelector('#left .btable')");
      await sleep(1500);
      if (await ctx.eval("!!document.querySelector('#left table.trm')")) { matrix = true; break; }
    }
    check("375: a card detail with its trace tables stays inside the pane", matrix && await ctx.eval(`${noSideways} && [...document.querySelectorAll('#left table.trm')].every(t => t.getBoundingClientRect().right <= ${pane}.getBoundingClientRect().right + 1)`));
    await ctx.go("doc");
    await ctx.click("[data-tocbtn]"); await ctx.wait("document.querySelector('#toc').classList.contains('open')");
    check("375: a one-line TOC entry is as tall as a tree row", await ctx.eval("(() => { const hs = [...document.querySelectorAll('#toc a[data-toc]')].map(a => a.getBoundingClientRect().height); return hs.length > 0 && Math.abs(Math.min(...hs) - 30) <= 1; })()"));
    await ctx.click("#scrim");
    const totopShown = "getComputedStyle(document.getElementById('totop')).display !== 'none'";
    check("375: no back-to-top button at the top of a doc", !(await ctx.eval(totopShown)));
    await ctx.eval("(() => { const l = document.querySelector('#left'); l.scrollTop = l.clientHeight * 2; return true; })()"); await sleep(300);
    check("375: a screen down, the back-to-top button shows", await ctx.eval(totopShown));
    await ctx.tap("#totop"); await sleep(300);
    check("375: tapping it jumps to the top and hides it", await ctx.eval(`document.querySelector('#left').scrollTop === 0 && !(${totopShown})`));
    check("375: head in desktop order — navigation left, crumb between, the rest flush right", await ctx.eval(`(() => { const h = document.querySelector("#left .doc-head"), c = h.querySelector(".crumb").getBoundingClientRect();
      const nav = h.querySelector(".hg").getBoundingClientRect(), find = h.querySelector("[data-find]").getBoundingClientRect(), g = [...h.querySelectorAll(".hg")].filter(x => x.getBoundingClientRect().width > 0).pop().getBoundingClientRect();
      const inner = h.getBoundingClientRect().right - parseFloat(getComputedStyle(h).paddingRight);
      return c.left >= nav.right && c.right <= find.left && Math.abs(g.right - inner) <= 2 && c.width >= 40 && h.getBoundingClientRect().height < 48; })()`));
    check("375: the history ▼ box is the size of its neighbours", await ctx.eval("(() => { const w = document.querySelector('#left .histwrap').getBoundingClientRect(), f = document.querySelector('#left [data-find]').getBoundingClientRect(); return Math.abs(w.height - f.height) < .5 && Math.abs(w.width - f.width) < .5; })()"));
    check("375: after two views the history ▾ shows and the head stays one line", await ctx.eval("(() => { const w = document.querySelector('#left .histwrap'); return !!w && w.getBoundingClientRect().width > 0 && document.querySelector('#left .doc-head').getBoundingClientRect().height < 48; })()"));
    await ctx.eval("(() => { const s = document.querySelector('#left select[data-hist]'); const i = [...s.options].findIndex(x => /board/i.test(x.textContent)); s.value = String(i); s.dispatchEvent(new Event('change', { bubbles: true })); return true; })()");
    await ctx.wait("!!document.querySelector('#left .btable, #left .card')", 5000).catch(() => {});
    check("375: picking an entry from the history navigates to it", await ctx.eval("!!document.querySelector('#left .btable') && !document.querySelector('#left .docbody')"));
  },
  // Tree F rebuilds the section closed (fresh <details>: WebKit painted a folder switched while hidden as a blank);
  // only the very next F restores what was open — a folder clicked in between voids that.
  async treefold(ctx, check) {
    await ctx.viewport(375, 667); await ctx.load(); await ctx.go("board"); await ctx.click("[data-side]");
    const SEC = `document.querySelector('#tree > details[data-name="dev"]')`, OUTER = `${SEC}.querySelector(":scope > details.kids")`, INNER = `${OUTER}.querySelector(":scope > details.kids")`;
    const F = `${SEC}.querySelector('.sx[data-act="collapse"]')`;
    const tap = async (expr) => { await ctx.eval(`${expr}.click(); true`); await sleep(250); };
    await tap(`${OUTER}.querySelector("summary")`); await tap(`${INNER}.querySelector("summary")`);
    await ctx.eval(`window.__old = ${OUTER}; true`);
    await tap(F);
    check("375: F rebuilds the section with every folder closed", await ctx.eval(`${OUTER} !== window.__old && [...${SEC}.querySelectorAll("details")].every(d => !d.open)`));
    await tap(F);
    check("375: an immediate second F restores what was open", await ctx.eval(`${OUTER}.open && ${INNER}.open`));
    await tap(F); await tap(`${OUTER}.querySelector("summary")`);
    check("375: re-opening the outer folder shows the inner one closed, rows packed", await ctx.eval(`(() => { const k = [...${OUTER}.children]; let g = 0;
      for (let i = 1; i < k.length; i++) g = Math.max(g, k[i].getBoundingClientRect().top - k[i - 1].getBoundingClientRect().bottom); return !${INNER}.open && g <= 1; })()`));
    await tap(`${OUTER}.querySelector("summary")`); await tap(F);
    check("375: after a folder was clicked, F does not bring the old set back", await ctx.eval(`[...${SEC}.querySelectorAll("details")].every(d => !d.open)`));
  },
  // Coming back to a view that was left at the very top lands at the top (the board's filters and a doc's
  // frontmatter above the first block stay in view); a view left mid-way still returns to its top block (not the pixel).
  async revisit(ctx, check) {
    for (const [w, h] of [[375, 667], [1440, 900]]) {
      await ctx.viewport(w, h); await ctx.load(); await ctx.go("board"); await ctx.go("doc"); await ctx.go("board");
      check(`${w}: back on the board at the top, the status chips in view`, await ctx.eval("document.querySelector('#left').scrollTop === 0 && document.querySelector('#left .board-filters').getBoundingClientRect().top >= document.querySelector('#left .doc-head').getBoundingClientRect().bottom - 1"));
      await ctx.go("doc");
      check(`${w}: back on the doc at the top, the frontmatter in view`, await ctx.eval("document.querySelector('#left').scrollTop === 0"));
      await ctx.eval("(() => { const l = document.querySelector('#left'); l.scrollTop = Math.round(l.scrollHeight / 3); return true; })()"); await sleep(200);
      const topBlock = "(() => { const l = document.querySelector('#left'), edge = l.getBoundingClientRect().top + 56; return [...l.querySelectorAll('.docbody > *')].findIndex(b => b.getBoundingClientRect().bottom > edge); })()";
      const left = await ctx.eval(topBlock);
      await ctx.go("board"); await ctx.go("doc"); await sleep(300);
      check(`${w}: a doc left mid-way comes back to the block that was at the top (block ${left})`, left > 0 && (await ctx.eval(`(() => { const l = document.querySelector('#left'), b = l.querySelectorAll('.docbody > *')[${left}]; return Math.abs(b.getBoundingClientRect().top - l.getBoundingClientRect().top - 56) <= 2; })()`)));
    }
  },
  // Desktop chrome: the tree's scrollbar on the sidebar edge, the pane head in function groups,
  // and a collapsed sidebar reopening from the head's ☰ (no floating button over ◀).
  async desk(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    check("1440: the tree reaches the sidebar's right edge", await ctx.eval("Math.abs(document.getElementById('tree').getBoundingClientRect().right - document.getElementById('side').getBoundingClientRect().right) < 1"));
    check("1440: head buttons sit in groups with a wider gap between groups", await ctx.eval(`(() => { const g = [...document.querySelectorAll("#left .doc-head .hg")].filter(x => x.getBoundingClientRect().width > 0);
      const gaps = g.slice(1).map((x, i) => x.getBoundingClientRect().left - g[i].getBoundingClientRect().right).filter((d, i) => i > 0);
      return g.length >= 4 && gaps.every(d => d >= 8) && g[g.length - 1].querySelector("[data-tocbtn]"); })()`));
    check("1440: head buttons are one height", await ctx.eval("new Set([...document.querySelectorAll('#left .doc-head button.iconbtn')].filter(b => b.offsetParent).map(b => Math.round(b.getBoundingClientRect().height))).size === 1"));
    check("1440: no ☰ in the head while the sidebar is open", await ctx.eval("getComputedStyle(document.querySelector('#left [data-side]')).display === 'none'"));
    await ctx.click('[data-collapse="side"]');
    check("1440: collapsed — ☰ leads the head and no floating button shows", await ctx.eval("getComputedStyle(document.querySelector('#left [data-side]')).display !== 'none' && getComputedStyle(document.getElementById('reopen')).display === 'none'"));
    await ctx.click("#left [data-side]"); await sleep(200);
    check("1440: the head ☰ reopens the sidebar", await ctx.eval("!document.getElementById('side').classList.contains('collapsed') && getComputedStyle(document.querySelector('#left [data-side]')).display === 'none'"));
  },
  // Card 041: the classic shell's bugs found in the 2026-10 comparison, and what it gains from v2 — one check each.
  async classic041(ctx, check) {
    const docAt = async (tree, rel, ready = "!!document.querySelector('#left .docbody, #left .notice')") => { await ctx.eval(navAnchor({ nav: "doc", tree, rel })); await ctx.wait(ready); await sleep(300); };
    await ctx.viewport(1440, 900); await ctx.load();
    // Req-1 bugs
    await docAt("dev", "xg-skills/no-such-file.md");
    check("404: a gentle notice, not the raw fetch error", await ctx.eval("/不存在或已被移动/.test(document.querySelector('#left .notice').textContent) && !/→ 404 \\(/.test(document.querySelector('#left').textContent)"));
    await docAt("dev", "hashdata/005-lightweight-vacuum-311/design.md");
    await ctx.eval("document.getElementById('left').scrollTop = 0; true");
    await ctx.click("#left .docbody a[href='#open-questions'], #left .docbody a[data-hash='open-questions']"); await sleep(2500);   // a long smooth scroll
    check("#slug link: jumps to its heading", await ctx.eval("(() => { const h = [...document.querySelectorAll('#left .docbody h2')].find(x => x.textContent.trim() === 'Open questions'), p = document.getElementById('left'); const t = h.getBoundingClientRect().top - p.getBoundingClientRect().top; return t >= 0 && t < 160; })()"));
    await ctx.eval(`(() => { const s = document.getElementById("search"); s.value = "->"; s.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })); return true; })()`);
    await ctx.wait("!!document.querySelector('#left .hit, #left .none')"); await sleep(300);
    check("search '->': the hits are highlighted", await ctx.eval("document.querySelectorAll('#left .hit mark').length > 0"));
    await ctx.eval(`(() => { const s = document.getElementById("search"); s.value = "amp"; s.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })); return true; })()`);
    await ctx.wait("!!document.querySelector('#left .hit, #left .none')"); await sleep(300);
    check("search 'amp': no entity is cut into visible text", await ctx.eval("![...document.querySelectorAll('#left .hit')].some(h => /&amp;|&lt;|&gt;/.test(h.textContent))"));
    await docAt("dev", "xg-skills/040-viewer-refined-frontend/design.md"); await ctx.wait("!!document.querySelector('#left .docbody .mermaid svg')", 8000);
    check("mermaid keeps its source line number", await ctx.eval("!!document.querySelector('#left .docbody > .mermaid[data-srcline]')"));
    check("frontmatter: the status shows without its # comment, coloured", await ctx.eval("(() => { const s = document.querySelector('#left .frontmatter .fm-st'); return !!s && !/#/.test(s.textContent) && !/st-backlog/.test(s.className); })()"));
    const fill = "(() => { const t = document.querySelector('#left .docbody .mermaid svg .node rect, #left .docbody .mermaid svg rect'); return t ? getComputedStyle(t).fill : null; })()";
    await ctx.media([{ name: "prefers-color-scheme", value: "light" }]); await sleep(600); const f0 = await ctx.eval(fill);
    await ctx.media([{ name: "prefers-color-scheme", value: "dark" }]); await sleep(1500); const f1 = await ctx.eval(fill);
    check(`following the system theme re-renders mermaid (${f0} → ${f1})`, !!f0 && f0 !== f1);
    await ctx.media([]);
    await ctx.key("k", 4); await sleep(150); await ctx.type("040 design"); await sleep(300);
    check("⌘K '040 design': no dev/ prefix noise", await ctx.eval("document.querySelectorAll('#qoList .qrow:not(.qfall)').length <= 5"));
    await ctx.key("Escape");

    // Req-2 lite progress on the board: ticks + k/n, a status word when a card has no Req yet, legacy cards unchanged
    const want = await ctx.eval(`fetch('/api/board').then(r => r.json()).then(b => { const cs = Object.values(b).flat().map(SV.cardView);
      const legacy = cs.find(c => !c.lite && c.st === 'active') || cs.find(c => !c.lite);
      return { a: cs.find(c => c.id === 'xg-skills/040'), z: cs.find(c => c.lite && !c.req && !/done|dropped/.test(c.st)), legacy: legacy && legacy.id }; })`, true);
    const boardIn = async (mode) => { await ctx.go("board"); for (let i = 0; i < 3 && (await ctx.eval("(document.querySelector('[data-bmode]') || {}).textContent")) !== mode; i++) { await ctx.click("[data-bmode]"); await sleep(400); } };
    const face = (key) => `(() => { const c = document.querySelector('#left [data-key="${key}"]'); if (!c) return null; const t = c.querySelector('.lticks'); return { ticks: t ? t.querySelectorAll('i').length : -1, on: t ? t.querySelectorAll('i.on').length : -1, text: c.textContent }; })()`;
    for (const mode of ["grid", "kanban"]) {
      await boardIn(mode); const a = await ctx.eval(face("xg-skills/040")), z = want.z ? await ctx.eval(face(want.z.id)) : null;
      check(`${mode}: the lite card shows ${want.a.ok}/${want.a.req} as ticks`, !!a && a.ticks === want.a.req && a.on === want.a.ok && a.text.includes(want.a.ok + "/" + want.a.req));
      if (want.z) check(`${mode}: a lite card without Req (${want.z.id}) shows its status, not 0/0`, !!z && !z.text.includes("0/0") && z.text.includes(want.z.liteSt));
      if (want.legacy) check(`${mode}: a legacy card keeps its phase track`, await ctx.eval(`(() => { const c = document.querySelector('#left [data-key="${want.legacy}"]'); return !c || (!c.querySelector('.lticks') && !!c.querySelector('.pc')); })()`));
    }
    await boardIn("table");
    check("table: the lite row shows a bar and k/n", await ctx.eval(`(() => { const r = document.querySelector('#left tr[data-key="xg-skills/040"] .tprog'); return !!r && !!r.querySelector('.lbar') && r.textContent.includes(${J(want.a.ok + "/" + want.a.req)}); })()`));
    if (want.z) check("table: no 0/0 for a lite card without Req", await ctx.eval(`(() => { const r = document.querySelector('#left tr[data-key="${want.z.id}"] .tprog'); return !!r && !r.textContent.includes('0/0'); })()`));
    await boardIn("grid"); await ctx.click('#left .card[data-key="xg-skills/040"]'); await ctx.wait("!!document.querySelector('#left .card-detail')"); await sleep(1200);
    check("detail: the lite card lists its Reqs, no Trace or Tasks chip", await ctx.eval(`(() => { const d = document.querySelector('#left .card-detail'); return d.querySelectorAll('.cd-req').length === ${want.a.req} && !/Trace|Tasks/.test(d.querySelector('.cd-strip').textContent); })()`));
    check("detail: Docs links only files that exist", await ctx.eval(`fetch('/api/tree').then(r => r.json()).then(t => { const have = new Set(t.dev.map(x => x.path)); return [...document.querySelectorAll('#left .card-detail .cd-phase[data-rel]')].every(a => have.has(a.dataset.rel)); })`, true));
    await ctx.eval(navAnchor({ nav: "trace", card: "xg-skills/040" })); await ctx.wait("!!document.querySelector('#left .cd-req, #left .tr-loading, #left .muted')"); await sleep(1500);
    check("trace page: the lite card shows its Reqs, not 'no trace data'", await ctx.eval(`document.querySelectorAll('#left .cd-req').length === ${want.a.req} && !/暂无 trace/.test(document.getElementById('left').textContent)`));
    // Req-3 stars and the trail (J-12: a trail of its own; quick open keeps its ⌘K-only recents)
    await ctx.eval("localStorage.removeItem('sv-stars'); localStorage.removeItem('sv-recent-trail'); localStorage.removeItem('sv-recent-opened'); true");
    const D = "xg-skills/040-viewer-refined-frontend/design.md";
    await docAt("dev", D);
    await ctx.click("#left .doc-head [data-star]"); await sleep(200);
    check("the star button stars the doc", await ctx.eval(`(JSON.parse(localStorage.getItem('sv-stars') || '[]')).some(x => x.key === 'dev:${D}') && /★/.test(document.querySelector('#left .doc-head [data-star]').textContent)`));
    check("the tree marks the starred doc", await ctx.eval(`!!document.querySelector('#tree a.file[data-rel="${D}"] .star')`));
    await ctx.key("s"); await sleep(200);
    check("s unstars it", await ctx.eval(`!(JSON.parse(localStorage.getItem('sv-stars') || '[]')).some(x => x.key === 'dev:${D}')`));
    await ctx.key("s"); await sleep(200);
    await ctx.eval("location.reload(); true"); await sleep(600); await ctx.wait("!!document.querySelector('#tree a.file')"); await docAt("dev", D);
    check("the star survives a reload", await ctx.eval(`/★/.test(document.querySelector('#left .doc-head [data-star]').textContent)`));
    await ctx.click('[data-svpop="stars"]'); await sleep(200);
    check("the stars popover lists it", await ctx.eval(`!!document.querySelector('#svpop.show a[data-rel="${D}"]')`));
    await ctx.click(`#svpop [data-unstar="dev:${D}"]`); await sleep(200);
    check("…and unstars from there", await ctx.eval(`!(JSON.parse(localStorage.getItem('sv-stars') || '[]')).length`));
    await ctx.key("Escape"); await sleep(100);
    check("Esc closes the popover", await ctx.eval("!document.querySelector('#svpop.show')"));
    await docAt("dev", "xg-skills/040-viewer-refined-frontend/facts.md");
    check("a doc opened from anywhere joins the trail", await ctx.eval("(JSON.parse(localStorage.getItem('sv-recent-trail') || '[]')).includes('dev/xg-skills/040-viewer-refined-frontend/facts.md')"));
    check("…but not quick open's recents (R7)", await ctx.eval("!(JSON.parse(localStorage.getItem('sv-recent-opened') || '[]')).length"));
    await ctx.click('[data-svpop="trail"]'); await sleep(200);
    check("the trail popover lists the docs, newest first", await ctx.eval("(() => { const a = [...document.querySelectorAll('#svpop.show a[data-rel]')].map(x => x.dataset.rel); return a[0] === 'xg-skills/040-viewer-refined-frontend/facts.md' && a.includes('xg-skills/040-viewer-refined-frontend/design.md'); })()"));
    await ctx.key("Escape");
    check("the classic shell writes no svd2- key", await ctx.eval("!Object.keys(localStorage).some(k => k.startsWith('svd2-'))"));
    // Req-4-a forward next to back, [ and ] on the focused pane
    await docAt("dev", "xg-skills/040-viewer-refined-frontend/design.md"); await docAt("dev", "xg-skills/040-viewer-refined-frontend/facts.md");
    const crumb = "document.querySelector('#left .crumb .base').textContent";
    await ctx.key("["); await sleep(500);
    check("[ goes back", await ctx.eval(crumb) === "design.md");
    check("…and the head's forward button is enabled", await ctx.eval("!!document.querySelector('#left .doc-head [data-fwd]:not([disabled])')"));
    await ctx.key("]"); await sleep(500);
    check("] goes forward again", await ctx.eval(crumb) === "facts.md");
    // Req-4-b Esc closes the topmost layer first (J-4), and also the link preview and the board detail
    await ctx.key("f"); await sleep(150); await ctx.eval("document.activeElement.blur(); true"); await ctx.key("?", 8); await sleep(150);
    await ctx.key("Escape"); await sleep(100);
    check("Esc closes help first, the find bar stays", await ctx.eval("!document.getElementById('help').classList.contains('show') && !!document.querySelector('#left .findbar')"));
    await ctx.key("Escape"); await sleep(100);
    check("…then the find bar", await ctx.eval("!document.querySelector('#left .findbar')"));
    await docAt("dev", "xg-skills/040-viewer-refined-frontend/design.md");
    await ctx.mouseMove("#left .docbody a[data-nav='doc']"); await sleep(900);
    check("(the link preview is open)", await ctx.eval("!!document.getElementById('lp') && getComputedStyle(document.getElementById('lp')).display !== 'none'"));
    await ctx.key("Escape"); await sleep(150);
    check("Esc closes the link preview", await ctx.eval("getComputedStyle(document.getElementById('lp')).display === 'none'"));
    await ctx.go("board"); await ctx.click('#left .card[data-key="xg-skills/040"]'); await ctx.wait("!!document.querySelector('#left .card-detail')");
    await ctx.key("Escape"); await sleep(200);
    check("Esc closes the board detail", await ctx.eval("!document.querySelector('#left .card-detail')"));
    // Req-4-c citation hover cards; a plain click stays in the pane (J-5), ⇧ opens the definition beside with a connector
    await docAt("dev", "xg-skills/040-viewer-refined-frontend/design.md");
    const shiftClick = (sel) => ctx.eval(`(() => { const e = document.querySelector(${J(sel)}); if (!e) return false; e.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: true })); return true; })()`);
    const factCite = "#left .docbody a.xid[href*='Fact-']";
    const fAt = await ctx.eval(`(() => { const e = document.querySelector(${J(factCite)}); e.scrollIntoView({ block: 'center' }); const r = e.getClientRects()[0]; return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
    await sleep(300); await ctx.mouseAt(fAt[0], fAt[1]); await sleep(900);   // scroll first: a scroll dismisses the card
    check("hovering a Fact citation shows its fact", await ctx.eval("(() => { const l = document.getElementById('lp'); return !!l && getComputedStyle(l).display !== 'none' && /facts\\.md/.test(l.textContent) && /Fact-\\d+/.test(l.textContent); })()"));
    await ctx.key("Escape");
    if (await ctx.eval("!!document.querySelector('#left .docbody a.xid[href*=\"Req-\"]')")) {
      const at = await ctx.eval("(() => { const e = document.querySelector('#left .docbody a.xid[href*=\"Req-\"]'); e.scrollIntoView({ block: 'center' }); const r = e.getClientRects()[0]; return [r.x + r.width / 2, r.y + r.height / 2]; })()");
      await sleep(300); await ctx.mouseAt(at[0], at[1]); await sleep(700);   // a scroll dismisses the card, so scroll first and then hover
      check("hovering a citation defined in this doc shows its definition", await ctx.eval("/^本文/.test(document.querySelector('#lp .lp-path').textContent)"));
      await ctx.key("Escape");
    }
    await shiftClick(factCite); await ctx.wait("!!document.querySelector('#right .docbody')", 5000); await sleep(700);
    check("⇧ on a citation opens the definition in the other pane", await ctx.eval("/facts\\.md$/.test(document.querySelector('#right .crumb .base').textContent) && /design\\.md$/.test(document.querySelector('#left .crumb .base').textContent)"));
    check("…with a connector line drawn", await ctx.eval("!!document.querySelector('#xline path')"));
    await ctx.click("[data-closeright]"); await sleep(300);
    await ctx.click(factCite); await ctx.wait("/facts\\.md$/.test(document.querySelector('#left .crumb .base').textContent)", 5000);
    check("a plain click on a citation still jumps in the same pane", await ctx.eval("!document.querySelector('#right.show')"));
    // Req-4-d find feel (J-6): counting starts at the screen, typing never scrolls; the rail takes a click anywhere;
    // a keyboard selection echoes; one selection bar with find / quote / comment
    await docAt("dev", "xg-skills/040-viewer-refined-frontend/design.md");
    await ctx.eval("document.getElementById('left').scrollTop = 4000; true"); await sleep(300);
    await ctx.key("f"); await sleep(100); await ctx.type("viewer"); await sleep(400);
    check("find counts from the screen, not the top", await ctx.eval("(() => { const m = (document.querySelector('#left [data-find-count]').textContent || '').match(/(\\d+)\\s*\\/\\s*(\\d+)/); return !!m && +m[1] > 1; })()"));
    check("…and typing did not move the page", await ctx.eval("Math.abs(document.getElementById('left').scrollTop - 4000) < 2"));
    const before = await ctx.eval("document.querySelector('#left .rail i.cur') && document.querySelector('#left .rail i.cur').dataset.hit");
    await ctx.eval(`(() => { const r = document.querySelector('#left .rail'), b = r.getBoundingClientRect(), ys = [...r.querySelectorAll('i')].map(i => i.getBoundingClientRect().top);
      let y = b.top + 4; for (let t = b.top + 4; t < b.bottom; t += 3) if (ys.every(m => Math.abs(m - t) > 6)) { y = t; break; }
      r.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: b.left + 4, clientY: y })); return true; })()`); await sleep(500);
    check("a click on the rail's empty track jumps to the nearest mark", await ctx.eval(`(document.querySelector('#left .rail i.cur') || {}).dataset?.hit !== ${J(before)}`));
    await ctx.key("Escape");
    await ctx.eval("(() => { const p = document.querySelector('#left .docbody p'); p.scrollIntoView({ block: 'center' }); const t = p.firstChild; const r = document.createRange(); r.setStart(t, 0); r.setEnd(t, Math.min(6, t.length)); const s = getSelection(); s.removeAllRanges(); s.addRange(r); return true; })()"); await sleep(400);
    check("a selection made without the mouse still echoes", await ctx.eval("!!CSS.highlights.get('sv-sel-left')"));
    check("the selection bar offers find, quote and comment", await ctx.eval("(() => { const b = document.getElementById('cmt'); return getComputedStyle(b).display !== 'none' && ['find', 'quote', 'comment'].every(k => b.querySelector('[data-sel=' + k + ']')); })()"));
    const term = await ctx.eval("String(getSelection()).trim()");
    await ctx.click("#cmt [data-sel=find]"); await sleep(300);
    check("…find opens the find bar on the selected words", await ctx.eval(`(document.querySelector('#left [data-find-input]') || {}).value === ${J(term)}`));
    await ctx.key("Escape");
    // Req-4-e the TOC marks the section on screen (J-2; the current line still follows clicks only); h2–h4 carry a copy-link #
    await docAt("dev", "xg-skills/040-viewer-refined-frontend/design.md");
    await ctx.eval("(() => { const h = [...document.querySelectorAll('#left .docbody h2')][3]; document.getElementById('left').scrollTop += h.getBoundingClientRect().top - document.getElementById('left').getBoundingClientRect().top - 20; return true; })()"); await sleep(500);
    check("the TOC marks the section on screen", await ctx.eval("(() => { const s = document.querySelector('#toc a.spy'), h = [...document.querySelectorAll('#left .docbody h2')][3]; return !!s && s.textContent.trim() === h.textContent.trim(); })()"));
    check("h2–h4 carry a # that adds no text to the heading", await ctx.eval("(() => { const h = document.querySelector('#left .docbody h2'), b = h.querySelector('[data-anc]'); return !!b && b.textContent === '' && !/#/.test(h.textContent); })()"));
    await ctx.eval("document.querySelector('#left .docbody h2 [data-anc]').click(); true"); await sleep(200);
    check("…and a click on it copies the section's link", await ctx.eval("/#/.test(document.getElementById('flash').textContent)"));
    // Req-5 quick open lists cards and Fact blocks; an exact id leads; picking one opens it (J-8)
    await ctx.key("k", 4); await sleep(150); await ctx.type("040"); await sleep(400);
    const rows = "[...document.querySelectorAll('#qoList .qrow')].map(r => ((r.querySelector('.qtag') || {}).textContent || '') + '|' + (r.querySelector('.qn') || r).textContent)";
    check("⌘K 040: the card leads", /^CARD\|.*xg-skills\/040/.test((await ctx.eval(rows)).find(r => !/^(VIEW|EXT)\|/.test(r)) || ""));
    await ctx.key("Enter"); await ctx.wait("!!document.querySelector('#left .docbody')", 5000); await sleep(300);
    check("…and opens the card's design.md", await ctx.eval("document.querySelector('#left .crumb .full').textContent.endsWith('xg-skills/040-viewer-refined-frontend/design.md')"));
    await ctx.key("k", 4); await sleep(150); await ctx.type("Fact-2"); await sleep(3500);
    await ctx.eval("document.getElementById('qoInput').dispatchEvent(new Event('input', { bubbles: true })); true"); await sleep(300);
    check("⌘K Fact-2: an exact Fact-2 leads", /^FACT\|Fact-2 /.test((await ctx.eval(rows)).find(r => !/^(VIEW|EXT)\|/.test(r)) || ""));
    await ctx.key("Enter"); await ctx.wait("/facts\\.md$/.test(document.querySelector('#left .crumb .full').textContent)", 5000);
    check("…and opens its facts.md", true);
    await ctx.key("k", 4); await sleep(150); await ctx.type("040"); await sleep(400);
    check("⌘K 040: every card row carries 040", (await ctx.eval(rows)).filter(r => /^CARD\|/.test(r)).every(r => r.includes("040")));
    await ctx.key("Escape");
    // Req-6 / Req-8 board forms: grid → kanban → table → dots on one button; no grouping, no sort (Req-8 took them back)
    await ctx.eval("['sv-board-mode','sv-board-group','sv-board-sort'].forEach(k => localStorage.removeItem(k)); true"); await ctx.go("board");
    const label = (sel) => `(document.querySelector('#left ${sel}') || {}).textContent`;
    const forms = []; for (let i = 0; i < 4; i++) { await ctx.click("#left [data-bmode]"); await sleep(400); forms.push(await ctx.eval(label("[data-bmode]"))); }
    check(`the form button cycles grid → kanban → table → dots → grid (${forms.join(" ")})`, forms.join(" ") === "kanban table dots grid");
    check("no grouping and no sort button", await ctx.eval("!document.querySelector('#left [data-bgroup], #left [data-bsort]')"));
    await ctx.click("#left [data-bmode]"); await sleep(400);   // kanban
    check("kanban: one column per status, as before", await ctx.eval("(() => { const cols = document.querySelectorAll('#left .board.kanban .col').length, st = new Set([...document.querySelectorAll('#left .card')].map(c => [...c.classList].find(x => x.startsWith('st-')))); return cols === st.size && cols > 1; })()"));
    // the current-line band follows a card when the kanban scrolls sideways
    await ctx.eval("(() => { const cs = document.querySelectorAll('#left .board.kanban .col'); const c = cs[cs.length - 1].querySelector('.card'); c.scrollIntoView({ inline: 'center', block: 'nearest' }); return true; })()"); await sleep(200);
    await ctx.eval("(() => { const cs = document.querySelectorAll('#left .board.kanban .col'); cs[cs.length - 1].querySelector('.card').click(); return true; })()"); await sleep(400);
    await ctx.eval("document.querySelector('#left .board.kanban').scrollLeft -= 150; true"); await sleep(400);
    check("kanban scrolled sideways: the current-line band stays on the selected card", await ctx.eval("(() => { const ov = document.querySelector('#left .curline-ov'), c = document.querySelector('#left .card.selected'); if (!ov || !c) return false; return Math.abs(ov.getBoundingClientRect().left - c.getBoundingClientRect().left) < 3; })()"));
    await ctx.key("Escape");
    await ctx.click("#left [data-bmode]"); await sleep(400);   // table
    check("table: the progress cell fits its bar and k/n, nothing spills into next", await ctx.eval("[...document.querySelectorAll('#left .btable .tprog')].every(td => td.scrollWidth <= td.clientWidth + 1)"));
    await ctx.click("#left [data-bmode]"); await sleep(400);   // dots
    check("dots: grouped by project", await ctx.eval("(() => { const g = [...document.querySelectorAll('#left section.grp')]; return g.length > 1 && g.every(x => [...x.querySelectorAll('.sdot')].every(d => d.dataset.key.split('/')[0] === x.dataset.key)); })()"));
    const dotAt = await ctx.eval("(() => { const d = document.querySelector('#left .sdot[data-key=\"xg-skills/040\"]'); d.scrollIntoView({ block: 'center' }); const r = d.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()");
    await sleep(300); await ctx.mouseAt(dotAt[0], dotAt[1]); await sleep(400);
    check("dots: hovering a dot shows its card", await ctx.eval("(() => { const p = document.getElementById('dotpop'); return !!p && getComputedStyle(p).display !== 'none' && !!p.querySelector('.card[data-key=\"xg-skills/040\"]'); })()"));
    await ctx.mouseAt(5, 5); await sleep(300);
    check("…and leaving it hides the card", await ctx.eval("getComputedStyle(document.getElementById('dotpop')).display === 'none'"));
    await ctx.click("#left .sdot"); await ctx.wait("!!document.querySelector('#left .card-detail')", 3000);
    check("…a dot still opens the card's detail", true);
    await ctx.eval("location.reload(); true"); await sleep(600); await ctx.wait("!!document.querySelector('#tree a.file')"); await ctx.go("board"); await sleep(300);
    check("the form survives a reload", await ctx.eval(`${label("[data-bmode]")} === 'dots'`));
    await ctx.eval("localStorage.setItem('sv-board-mode', 'cols'); location.reload(); true"); await sleep(600); await ctx.wait("!!document.querySelector('#tree a.file')"); await ctx.go("board"); await sleep(300);
    check("a stored cols reads as the kanban", await ctx.eval(`${label("[data-bmode]")} === 'kanban' && !!document.querySelector('#left .board.kanban')`));
    // Req-8-e the sidebar's icons: the pane head's line icons at the pane head's size
    const icoW = await ctx.eval("Math.round(([...document.querySelectorAll('#left .doc-head .iconbtn svg')].map(s => s.getBoundingClientRect().width).find(w => w > 0)) || 0)");
    check(`sidebar buttons carry line icons at the head's size (${icoW}px)`, await ctx.eval(`(() => { const b = [...document.querySelectorAll('#side .brand-btns .iconbtn:not([data-sidetop]), #side .navbtn .k')].filter(x => x.offsetParent); return b.length >= 7 && b.every(x => { const s = x.querySelector('svg.ic'); return !!s && Math.round(s.getBoundingClientRect().width) === ${icoW}; }); })()`));
    // Req-7-a the dev tree by card (J-7): open cards first (newest first), the project's other files, closed (n) last
    await ctx.eval("localStorage.removeItem('sv-tree-open'); localStorage.removeItem('sv-tree-sort'); location.reload(); true"); await sleep(600); await ctx.wait("!!document.querySelector('#tree a.file')");
    const proj = `#tree details[data-name="dev"] > details[data-name="xg-skills"]`;
    await ctx.eval(`(() => { const d = document.querySelector('${proj}'); d.open = true; return true; })()`); await sleep(200);
    const kids = await ctx.eval(`[...document.querySelector('${proj}').children].filter(e => e.tagName === 'DETAILS' || e.tagName === 'A').map(e => e.dataset.name || ('file:' + e.dataset.rel.split('/').pop()))`);
    const cardAt = kids.findIndex(k => /^\d{3}-/.test(k)), nonCard = kids.findIndex(k => !/^\d{3}-/.test(k));
    check(`open cards come first in their project (${kids.slice(0, 3).join(", ")} …)`, cardAt === 0 && (nonCard < 0 || kids.slice(0, nonCard).every(k => /^\d{3}-/.test(k))));
    check("…newest card first", (() => { const c = kids.filter(k => /^\d{3}-/.test(k)); return c.every((k, i) => !i || c[i - 1] > k); })());
    check("closed (n) is the project's last entry", kids[kids.length - 1] === "closed" && await ctx.eval(`/^closed \\(\\d+\\)/.test(document.querySelector('${proj} > details[data-name="closed"] > summary').textContent)`));
    check("…holding the done and dropped cards", await ctx.eval(`!!document.querySelector('${proj} > details[data-name="closed"] details[data-name^="039-"]') && !document.querySelector('${proj} > details[data-name^="039-"]')`));
    await ctx.eval(`(() => { const d = document.querySelector('${proj} > details[data-name^="040-"]'); d.open = true; return true; })()`); await sleep(150);
    check("inside a card: design.md first, files before folders", await ctx.eval(`(() => { const k = [...document.querySelector('${proj} > details[data-name^="040-"]').children].filter(e => e.tagName !== 'SUMMARY'); return k[0].tagName === 'A' && k[0].dataset.rel.endsWith('/design.md') && k.findIndex(e => e.tagName === 'DETAILS') > k.findIndex(e => e.tagName === 'A'); })()`));
    await docAt("dev", "xg-skills/039-viewer-small-screen-touch/design.md");
    check("opening a doc of a closed card reveals it inside closed (n)", await ctx.eval(`document.querySelector('${proj} > details[data-name="closed"]').open && !!document.querySelector('#tree a.file.active[data-rel="xg-skills/039-viewer-small-screen-touch/design.md"]')`));
    // Req-7-b the theme button opens a choice (J-11): five themes and a brightness slider; the button still shows the current one
    await ctx.click("#themeToggle"); await sleep(200);
    check("the theme button opens five themes and a brightness slider", await ctx.eval("(() => { const p = document.getElementById('themePop'); return !!p && p.classList.contains('show') && p.querySelectorAll('[data-theme-k]').length === 5 && !!p.querySelector('#lumIn'); })()"));
    await ctx.click('#themePop [data-theme-k="space"]'); await sleep(300);
    check("深空 applies its palette, the button shows it", await ctx.eval("document.documentElement.getAttribute('data-theme') === 'space' && getComputedStyle(document.body).backgroundColor === 'rgb(13, 16, 21)' && /深空/.test(document.getElementById('themeToggle').title)"));
    await ctx.click("#themeToggle"); await sleep(150);
    await ctx.eval("(() => { const i = document.getElementById('lumIn'); i.value = 120; i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()");
    check("brightness 120% brightens the page", await ctx.eval("document.documentElement.style.filter === 'brightness(1.2)'"));
    await ctx.key("Escape"); await sleep(100);
    check("Esc closes the theme popover", await ctx.eval("!document.getElementById('themePop').classList.contains('show')"));
    await ctx.eval("location.reload(); true"); await sleep(600); await ctx.wait("!!document.querySelector('#tree a.file')");
    check("theme and brightness survive a reload", await ctx.eval("document.documentElement.getAttribute('data-theme') === 'space' && document.documentElement.style.filter === 'brightness(1.2)'"));
    await ctx.eval("localStorage.removeItem('sv-theme'); localStorage.removeItem('sv-lum'); location.reload(); true"); await sleep(600); await ctx.wait("!!document.querySelector('#tree a.file')");
    // Req-9 narrow: a bottom chip names the current section and opens the TOC; the doc scrolls under an open drawer
    await ctx.viewport(390, 844); await sleep(300); await docAt("dev", "xg-skills/040-viewer-refined-frontend/design.md");
    await ctx.eval("(() => { const h = [...document.querySelectorAll('#left .docbody h2')][3]; document.getElementById('left').scrollTop += h.getBoundingClientRect().top - document.getElementById('left').getBoundingClientRect().top - 20; return true; })()"); await sleep(500);
    check("narrow: a bottom chip names the section on screen", await ctx.eval("(() => { const c = document.getElementById('secchip'), h = [...document.querySelectorAll('#left .docbody h2')][3]; return !!c && getComputedStyle(c).display !== 'none' && c.textContent.trim() === h.textContent.trim(); })()"));
    await ctx.click("#secchip"); await sleep(300);
    check("…and opens the TOC drawer", await ctx.eval("document.getElementById('toc').classList.contains('open') && getComputedStyle(document.getElementById('secchip')).display === 'none'"));
    const y0 = await ctx.eval("document.getElementById('left').scrollTop");
    await ctx.wheel(30, 400, 300); await sleep(500);
    check("narrow: the doc scrolls under the open TOC drawer", await ctx.eval("document.getElementById('left').scrollTop") > y0 + 50);
    const crumbBefore = await ctx.eval("document.querySelector('#left .crumb .base').textContent");
    await ctx.eval(`(() => { window.__hit = 0; document.addEventListener('click', () => { window.__hit++; }, { once: true }); const e = document.elementFromPoint(30, 400); e.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: 30, clientY: 400 })); return true; })()`); await sleep(400);
    check("a tap outside the drawer closes it and does not reach the page", await ctx.eval(`!document.getElementById('toc').classList.contains('open') && document.querySelector('#left .crumb .base').textContent === ${J(crumbBefore)} && window.__hit === 0`));
    await ctx.click("#left [data-side]"); await sleep(300); const y1 = await ctx.eval("document.getElementById('left').scrollTop");
    await ctx.wheel(370, 400, 300); await sleep(500);
    check("narrow: the doc scrolls under the open sidebar too", await ctx.eval("document.getElementById('left').scrollTop") > y1 + 50);
    await ctx.key("Escape"); await ctx.viewport(1440, 900); await sleep(300);
    // close-out review fixes
    await ctx.eval("(() => { const f = document.getElementById('treeFilter'); f.value = 'facts'; f.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"); await sleep(400);
    check("filtering opens the card folders that hold a match", await ctx.eval("(() => { const a = [...document.querySelectorAll('#tree details[data-name=\"dev\"] a.file')]; return a.length > 3 && a.every(x => x.checkVisibility()); })()"));
    await ctx.eval("(() => { const f = document.getElementById('treeFilter'); f.value = ''; f.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"); await sleep(300);
    await docAt("dev", "xg-skills/040-viewer-refined-frontend/design.md");
    await ctx.eval("(() => { const p = document.querySelector('#left .docbody p'); p.scrollIntoView({ block: 'center' }); const t = p.firstChild; const r = document.createRange(); r.setStart(t, 0); r.setEnd(t, Math.min(6, t.length)); const s = getSelection(); s.removeAllRanges(); s.addRange(r); return true; })()"); await sleep(400);
    await ctx.key("f"); await sleep(400);
    check("pressing f takes the selection bar away (no stray bar in the corner)", await ctx.eval("getComputedStyle(document.getElementById('cmt')).display === 'none'"));
    await ctx.key("Escape");
    await ctx.eval("(() => { const p = document.querySelector('#left .docbody p'); const t = p.firstChild; const r = document.createRange(); r.setStart(t, 0); r.setEnd(t, Math.min(6, t.length)); const s = getSelection(); s.removeAllRanges(); s.addRange(r); return true; })()"); await sleep(400);
    await ctx.click("#cmt [data-sel=quote]"); await sleep(300);
    check("after copy as a quote the bar stays gone", await ctx.eval("getComputedStyle(document.getElementById('cmt')).display === 'none'"));
    await ctx.go("board"); await ctx.click('#left .card[data-key="xg-skills/041"], #left .trow[data-key="xg-skills/041"]'); await ctx.wait("!!document.querySelector('#left .card-detail .cd-req')", 5000);
    await ctx.click('#left .card-detail .cd-req[data-xid="Req-7"]'); await ctx.wait("!!document.querySelector('#left .docbody')", 5000); await sleep(800);
    check("a Req row in the detail jumps to that Req", await ctx.eval("(() => { const h = document.querySelector('#left .docbody [data-xid=\"Req-7\"]'), p = document.getElementById('left'); const t = h.getBoundingClientRect().top - p.getBoundingClientRect().top; return t > -5 && t < 200; })()"));

    await ctx.key("Escape");
    await ctx.key("Escape");
  },
  // Narrow-mode state survives the live refresh (a doc changing on disk re-renders the tree).
  async refresh(ctx, check, o) {
    if (!o.touch) throw new Error("refresh scenario needs --touch <file under the viewer's dev root>");
    await ctx.viewport(390, 844); await ctx.load(); await ctx.go("board");
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .sdots')"); await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board:not(.kanban) .card')");   // table → dots → grid (041: the signal form follows the table)
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board.kanban')");                // grid → kanban: not the narrow default, so a reset would show
    await ctx.go("doc"); await ctx.click("[data-tocbtn]"); await ctx.wait("document.querySelector('#toc').classList.contains('open')");
    const rev0 = await ctx.eval("fetch('/api/rev').then(r => r.json()).then(j => j.dev)");
    const now = new Date(); utimesSync(o.touch, now, now);
    await ctx.wait(`fetch('/api/rev').then(r => r.json()).then(j => j.dev !== ${JSON.stringify(rev0)})`, 8000);
    await sleep(3500);   // the page polls every 2.5s and refreshes the tree on a new token
    check("after the live refresh: TOC overlay still open", await ctx.eval("document.querySelector('#toc').classList.contains('open')"));
    check("after the live refresh: still narrow, one pane", await ctx.eval("document.documentElement.classList.contains('narrow') && getComputedStyle(document.querySelector('#side')).display === 'none'"));
    await ctx.click("#scrim"); await ctx.go("board");
    check("after the live refresh: the kanban pick survives", await ctx.eval("!!document.querySelector('#left .board.kanban')"));
  },
};
async function scenarios(o) {
  let fails = 0;
  await session(o, async (ctx) => {
    for (const name of o.scenario.split(",")) {
      const check = (label, ok) => { fails += ok ? 0 : 1; console.log(`${ok ? "ok " : "FAIL"} - ${name}: ${label}`); };
      if (!UI.SCENARIO[name]) throw new Error("unknown scenario " + name);
      await UI.SCENARIO[name](ctx, check, o);
    }
  });
  console.log(fails ? `${fails} failed` : "all scenarios passed");
  return fails ? 1 : 0;
}

function compare([a, b]) {
  const ma = JSON.parse(readFileSync(join(a, "manifest.json"), "utf8")), mb = JSON.parse(readFileSync(join(b, "manifest.json"), "utf8"));
  const names = [...new Set([...Object.keys(ma.shots), ...Object.keys(mb.shots)])].sort();
  let same = 0;
  console.log(`A ${a} (${ma.chrome}, rev ${JSON.stringify(ma.viewerRev)})\nB ${b} (${mb.chrome}, rev ${JSON.stringify(mb.viewerRev)})\n`);
  console.log("| shot | bytes | measurements |\n|---|---|---|");
  for (const n of names) {
    const fa = join(a, n), fb = join(b, n);
    const bytes = existsSync(fa) && existsSync(fb) ? (Buffer.compare(readFileSync(fa), readFileSync(fb)) === 0 ? "identical" : "differ") : "missing";
    const sa = JSON.stringify(ma.shots[n] || null), sb = JSON.stringify(mb.shots[n] || null);
    const meas = sa === sb ? "same" : `A ${sa} → B ${sb}`;
    if (bytes === "identical" && sa === sb) same++;
    console.log(`| ${n} | ${bytes} | ${meas} |`);
  }
  console.log(`\n${same}/${names.length} identical`);
  return same === names.length ? 0 : 1;
}

const o = parseArgs(process.argv.slice(2));
UI = /\/v2\/?$/.test(new URL(o.url).pathname) ? (await import("./shots-v2.mjs")).default
  : { VIEW, MEASURE, SCENARIO, ready: "!!document.querySelector('#tree a.file')", mask: ".doc-head, .findbar" };
if (UI.views && o.views === DEF.views) o.views = UI.views;
if (o.compare) process.exit(compare(o.compare));
if (o.scenario) process.exit(await scenarios(o));
if (o.eval) { await session(o, async (ctx) => { for (const vp of o.viewports.split(",")) { const [w, h] = vp.split("x").map(Number); await ctx.viewport(w, h); await ctx.load();
  for (const name of o.views.split(",")) { await ctx.go(name); console.log(`${vp} ${name}:`, JSON.stringify(await ctx.eval(o.eval))); } } }); process.exit(0); }
if (!o.out) { console.error("usage: shots.mjs --out <dir> | --compare <dirA> <dirB> | --scenario <names>"); process.exit(2); }
await shoot(o);
