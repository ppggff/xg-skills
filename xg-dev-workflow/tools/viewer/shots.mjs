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
  board:  (o) => ({ drive: `document.querySelector('[data-go="board"]').click()`, ready: "!!document.querySelector('#left .card, #left .row, #left .board, #left .rows')" }),
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
        const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
      if (!c) throw new Error("no element " + sel);
      return c;
    };
    const ctx = {
      viewer, chrome: (await cdp.send("Browser.getVersion")).product,
      eval: (expr) => evalIn(cdp, sid, expr),
      wait: (pred, timeout) => waitFor(cdp, sid, pred, timeout),
      viewport: (w, h) => cdp.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false }, sid),
      load: async () => {
        await cdp.send("Page.navigate", { url: o.url }, sid); await cdp.waitEvent("Page.loadEventFired", sid);
        if (!o.keepStorage) { await evalIn(cdp, sid, "localStorage.clear(); true"); await cdp.send("Page.reload", {}, sid); await cdp.waitEvent("Page.loadEventFired", sid); }
        await waitFor(cdp, sid, "!!document.querySelector('#tree a.file')");
      },
      go: async (name) => { const { drive, ready } = VIEW[name](o); await evalIn(cdp, sid, drive + "; true"); await waitFor(cdp, sid, ready); await sleep(400); },
      click: (sel) => evalIn(cdp, sid, `(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return false; e.click(); return true; })()`),
      shot: async () => {
        if (o.maskHead) await evalIn(cdp, sid, "document.querySelectorAll('.doc-head, .findbar').forEach(h => h.style.visibility = 'hidden'); true");
        const png = Buffer.from((await cdp.send("Page.captureScreenshot", { format: "png" }, sid)).data, "base64");
        if (o.maskHead) await evalIn(cdp, sid, "document.querySelectorAll('.doc-head, .findbar').forEach(h => h.style.visibility = ''); true");
        return png;
      },
      measure: () => evalIn(cdp, sid, MEASURE),
      touch: (on) => cdp.send("Emulation.setTouchEmulationEnabled", { enabled: on, maxTouchPoints: 1 }, sid),
      tap: async (sel) => {   // a finger tap at the element's centre (touchStart + touchEnd)
        const c = await centerOf(sel);
        await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: c[0], y: c[1] }] }, sid);
        await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }, sid);
      },
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
    await ctx.click("[data-side]"); await ctx.click('[data-find="left"]'); await ctx.wait("!!document.querySelector('#left [data-find-input]')");
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
  // Every hotkey action has a button in the pane head, at every width, and the head never overflows.
  async buttons(ctx, check) {
    for (const [w, h] of [[390, 844], [1024, 768]]) {
      await ctx.viewport(w, h); await ctx.load(); await ctx.go("doc");
      check(`${w}: doc head does not overflow`, (await ctx.measure()).headOverflow === 0);
      await ctx.click('[data-find="left"]'); await ctx.wait("!!document.querySelector('#left [data-find-input]')");
      check(`${w}: ⌕ opens the find bar`, await ctx.eval("!!document.querySelector('#left [data-find-input]')"));
      await ctx.click("[data-help]"); check(`${w}: ? opens help`, await ctx.eval("document.querySelector('#help').classList.contains('show')"));
      await ctx.eval("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); true");
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
  // The board has a rows form: the default below the breakpoint, a remembered pick anywhere,
  // and the old boolean kanban key still read.
  async rows(ctx, check) {
    await ctx.viewport(390, 844); await ctx.load(); await ctx.go("board");
    check("390: rows by default", await ctx.eval("!!document.querySelector('#left .row') && !document.querySelector('#left .card')"));
    check("390: a row shows id, title, progress and a time", await ctx.eval("(() => { const r = document.querySelector('#left .row'); return ['.rid','.rtitle','.rprog','.rwhen'].every(s => r.querySelector(s)); })()"));
    check("390: rows do not overflow the pane", await ctx.eval("[...document.querySelectorAll('#left .row')].every(r => r.scrollWidth <= r.clientWidth + 1)"));
    check("390: rows leave the title most of the width", await ctx.eval("(() => { const r = document.querySelector('#left .row'); return r.querySelector('.rtitle').getBoundingClientRect().width > r.getBoundingClientRect().width * 0.45; })()"));
    check("390: board head and chips sit on single lines", await ctx.eval("(() => { const h = document.querySelector('#left .doc-head'), f = document.querySelector('#left .board-filters'); return h.getBoundingClientRect().height < 48 && f.getBoundingClientRect().height < 40 && f.scrollWidth >= f.clientWidth; })()"));
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board:not(.kanban) .card')");   // rows → grid
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board.kanban')");                // grid → kanban
    check("the one button cycles the forms and the pick is remembered under sv-board-mode", await ctx.eval("localStorage.getItem('sv-board-mode') === 'kanban' && localStorage.getItem('sv-board-kanban') === null"));
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .btable')");                     // kanban → table
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .row')");                        // table → rows
    await ctx.click("#left .row"); check("tapping a row opens the detail drawer and marks the row", await ctx.eval("!!document.querySelector('#left .card-detail') && !!document.querySelector('#left .row.selected')"));
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
  // Hit areas below the breakpoint: head buttons and tree rows ≥ 40px, board rows ≥ 44px.
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
    check("390: board rows ≥ 44px", (await h("#left .row")) >= 44);
    check("390: row meta text ≥ 12px", (await fs("#left .row .rprog")) >= 12);
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
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board:not(.kanban) .card')");   // rows → grid
    check("375: grid cards stay inside the pane", await ctx.eval(`[...document.querySelectorAll("#left .card")].every(c => c.getBoundingClientRect().right <= ${pane}.getBoundingClientRect().right) && ${pane}.scrollWidth <= ${pane}.clientWidth`));
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board.kanban')");                // grid → kanban
    check("375: a kanban column is no wider than the board", await ctx.eval(`(() => { const b = document.querySelector("#left .board.kanban"); return [...b.querySelectorAll(".col")].every(c => c.getBoundingClientRect().width <= b.clientWidth); })()`));
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .btable')");                     // kanban → table
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .row')");                        // table → rows
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
    check("375: crumb and row meta 12px", (await fs("#left .crumb")) === 12 && (await fs("#left .row .rprog")) === 12);
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board:not(.kanban) .card')");   // rows → grid
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
    check("375: the history ▼ box is the size of its neighbours", await ctx.eval("(() => { const w = document.querySelector('#left .histwrap').getBoundingClientRect(), f = document.querySelector('#left [data-find]').getBoundingClientRect(); return Math.abs(w.height - f.height) < .5 && Math.abs(w.width - f.width) < .5; })()"));
    check("375: after two views the history ▾ shows and the head stays one line", await ctx.eval("(() => { const w = document.querySelector('#left .histwrap'); return !!w && w.getBoundingClientRect().width > 0 && document.querySelector('#left .doc-head').getBoundingClientRect().height < 48; })()"));
    await ctx.eval("(() => { const s = document.querySelector('#left select[data-hist]'); const i = [...s.options].findIndex(x => /board/i.test(x.textContent)); s.value = String(i); s.dispatchEvent(new Event('change', { bubbles: true })); return true; })()");
    await ctx.wait("!!document.querySelector('#left .btable, #left .row, #left .card')", 5000).catch(() => {});
    check("375: picking an entry from the history navigates to it", await ctx.eval("!!document.querySelector('#left .btable') && !document.querySelector('#left .docbody')"));
  },
  // Desktop chrome: the tree's scrollbar on the sidebar edge, the pane head in function groups,
  // and a collapsed sidebar reopening from the head's ☰ (no floating button over ◀).
  async desk(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    check("1440: the tree reaches the sidebar's right edge", await ctx.eval("Math.abs(document.getElementById('tree').getBoundingClientRect().right - document.getElementById('side').getBoundingClientRect().right) < 1"));
    check("1440: head buttons sit in groups with a wider gap between groups", await ctx.eval(`(() => { const g = [...document.querySelectorAll("#left .doc-head .hg")].filter(x => x.getBoundingClientRect().width > 0);
      const gaps = g.slice(1).map((x, i) => x.getBoundingClientRect().left - g[i].getBoundingClientRect().right).filter((d, i) => i > 0);
      return g.length >= 4 && gaps.every(d => d >= 8) && g[g.length - 1].querySelector("[data-help]"); })()`));
    check("1440: head buttons are one height", await ctx.eval("new Set([...document.querySelectorAll('#left .doc-head button.iconbtn')].filter(b => b.offsetParent).map(b => Math.round(b.getBoundingClientRect().height))).size === 1"));
    check("1440: no ☰ in the head while the sidebar is open", await ctx.eval("getComputedStyle(document.querySelector('#left [data-side]')).display === 'none'"));
    await ctx.click('[data-collapse="side"]');
    check("1440: collapsed — ☰ leads the head and no floating button shows", await ctx.eval("getComputedStyle(document.querySelector('#left [data-side]')).display !== 'none' && getComputedStyle(document.getElementById('reopen')).display === 'none'"));
    await ctx.click("#left [data-side]"); await sleep(200);
    check("1440: the head ☰ reopens the sidebar", await ctx.eval("!document.getElementById('side').classList.contains('collapsed') && getComputedStyle(document.querySelector('#left [data-side]')).display === 'none'"));
  },
  // Narrow-mode state survives the live refresh (a doc changing on disk re-renders the tree).
  async refresh(ctx, check, o) {
    if (!o.touch) throw new Error("refresh scenario needs --touch <file under the viewer's dev root>");
    await ctx.viewport(390, 844); await ctx.load(); await ctx.go("board");
    await ctx.click("[data-bmode]"); await ctx.wait("!!document.querySelector('#left .board:not(.kanban) .card')");   // rows → grid
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
      if (!SCENARIO[name]) throw new Error("unknown scenario " + name);
      await SCENARIO[name](ctx, check, o);
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
if (o.compare) process.exit(compare(o.compare));
if (o.scenario) process.exit(await scenarios(o));
if (o.eval) { await session(o, async (ctx) => { for (const vp of o.viewports.split(",")) { const [w, h] = vp.split("x").map(Number); await ctx.viewport(w, h); await ctx.load();
  for (const name of o.views.split(",")) { await ctx.go(name); console.log(`${vp} ${name}:`, JSON.stringify(await ctx.eval(o.eval))); } } }); process.exit(0); }
if (!o.out) { console.error("usage: shots.mjs --out <dir> | --compare <dirA> <dirB> | --scenario <names>"); process.exit(2); }
await shoot(o);
