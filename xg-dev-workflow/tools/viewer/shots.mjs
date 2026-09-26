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
import { mkdirSync, writeFileSync, readFileSync, existsSync, utimesSync } from "node:fs";
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

async function launchChrome(chromePath) {
  const userDir = join(process.env.TMPDIR || "/tmp", "sv-shots-" + process.pid);
  const child = spawn(chromePath, ["--headless=new", "--remote-debugging-port=0", "--user-data-dir=" + userDir,
    "--no-first-run", "--no-default-browser-check", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1"],
    { stdio: ["ignore", "ignore", "pipe"] });
  const wsUrl = await new Promise((ok, no) => {
    let buf = "";
    child.stderr.on("data", (d) => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) ok(m[1]); });
    child.on("exit", (code) => no(new Error("chrome exited " + code + "\n" + buf)));
    setTimeout(() => no(new Error("chrome did not announce DevTools\n" + buf)), 15000);
  });
  return { child, wsUrl };
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
  const cleanup = () => { while (cleanups.length) { try { cleanups.pop()(); } catch {} } };
  const onSignal = () => { cleanup(); process.exit(130); };
  process.once("SIGINT", onSignal); process.once("SIGTERM", onSignal);
  try {
    const viewer = await ensureViewer(o.url); cleanups.push(viewer.stop);
    await resolveDoc(o);
    const { child, wsUrl } = await launchChrome(o.chrome); cleanups.push(() => child.kill());
    const cdp = await CDP.connect(wsUrl); cleanups.push(() => cdp.close());
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
  } finally { cleanup(); process.off("SIGINT", onSignal); process.off("SIGTERM", onSignal); }
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
    await ctx.click('[data-bmode="kanban"]'); await ctx.wait("!!document.querySelector('#left .board.kanban')");
    check("picking kanban is remembered under sv-board-mode", await ctx.eval("localStorage.getItem('sv-board-mode') === 'kanban' && localStorage.getItem('sv-board-kanban') === null"));
    await ctx.click('[data-bmode="rows"]'); await ctx.wait("!!document.querySelector('#left .row')");
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
    check("390: every visible head button ≥ 40px", (await h("#left .doc-head .iconbtn")) >= 40);
    await ctx.click("[data-side]");
    check("390: sidebar nav buttons ≥ 40px", (await h("#side .navbtn")) >= 40);
    check("390: tree rows ≥ 40px", (await h("#tree summary")) >= 40);
    check("390: tree text ≥ 13px", (await fs("#tree summary")) >= 13);
    await ctx.click("#scrim"); await ctx.go("board");
    check("390: board rows ≥ 44px", (await h("#left .row")) >= 44);
    check("390: row title links ≥ 36px", (await h("#left .row .rtitle")) >= 36);
    check("390: status chips ≥ 40px", (await h("#left .fchip")) >= 40);
    check("390: row meta text ≥ 13px", (await fs("#left .row .rprog")) >= 13);
    await ctx.viewport(1920, 1080); await ctx.load(); await ctx.go("doc");
    check("1920: head buttons keep their desktop size", (await h("#left .doc-head .iconbtn")) < 40);
  },
  // Narrow-mode state survives the live refresh (a doc changing on disk re-renders the tree).
  async refresh(ctx, check, o) {
    if (!o.touch) throw new Error("refresh scenario needs --touch <file under the viewer's dev root>");
    await ctx.viewport(390, 844); await ctx.load(); await ctx.go("board");
    await ctx.click('[data-bmode="kanban"]'); await ctx.wait("!!document.querySelector('#left .board.kanban')");   // not the narrow default, so a reset would show
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
