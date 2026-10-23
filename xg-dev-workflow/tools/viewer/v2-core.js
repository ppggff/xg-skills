/* status viewer v2 — core: the V2 namespace, storage, data, columns, theme, popovers, status bar,
   event dispatch, the Esc layer chain, panes with their own back/forward history, and live refresh.
   The area files (board, tree, reader, search, find) register into V2; none of them talk to each other
   except through it. Pure logic lives in SV (sv.js), shared with the classic shell. */
"use strict";
var V2 = (function () {
  const V = {};
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  Object.assign(V, { $, $$, esc, cssEsc: s => (window.CSS && CSS.escape ? CSS.escape(s) : String(s).replace(/["\\]/g, "\\$&")) });
  V.RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  V.GITWEB = ($('meta[name="gitweb-url"]') || {}).content || "";
  V.ROOT_NAME = { dev: "dev_root", kb: "知识库", ext: "外部目录" };   // ext docs carry their extra root's label as the first path segment
  // behaviour numbers, in one place: refresh period, how long a toast stays, and the list sizes
  V.CFG = { pollMs: 2500, toastMs: 1900, trail: 12, qoRecent: 8, qoDocs: 40, qoCards: 8 };

  /* ---- storage: every key this page writes is svd2-*, never the classic shell's sv-* ---- */
  V.store = {
    get(k, d) { try { const v = localStorage.getItem("svd2-" + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem("svd2-" + k, JSON.stringify(v)); } catch (e) {} },
    del(k) { try { localStorage.removeItem("svd2-" + k); } catch (e) {} },
  };
  V.recent = {   // bounded recall lists: opened docs, searches, find terms
    list: kind => V.store.get("recent-" + kind, []),
    push(kind, item, cap) { if (item && String(item).length >= 2) V.store.set("recent-" + kind, SV.recentPush(V.recent.list(kind), item, cap || 12)); },
    clear() { ["opened", "search", "find"].forEach(k => V.store.set("recent-" + k, [])); },
  };

  /* ---- fetch ---- */
  V.api = p => fetch(p).then(r => {
    if (r.ok) return r;
    const e = new Error(p + " → " + r.status); e.status = r.status; throw e;
  });
  V.json = p => V.api(p).then(r => r.json());

  /* ---- small ui helpers ---- */
  const svg = (d, w = 1.6) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  V.I = {
    grid: svg('<rect x="4" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5"/>'),
    cols: svg('<rect x="4" y="4" width="4.5" height="16" rx="1.2"/><rect x="10.5" y="4" width="4.5" height="11" rx="1.2"/><rect x="17" y="4" width="3.5" height="7" rx="1.2"/>'),
    tbl: svg('<path d="M4 6h16M4 10h16M4 14h16M4 18h16"/>'),
    dots: svg('<circle cx="5" cy="10" r="1.8"/><circle cx="10" cy="10" r="1.8" fill="currentColor"/><circle cx="15" cy="10" r="1.8" fill="currentColor"/><circle cx="20" cy="10" r="1.8" fill="currentColor" opacity=".4" stroke="none"/><path d="M3 16h18" opacity=".6"/>', 1.4),
    filter: svg('<path d="M4 6h16l-6 7.5V19l-4-2v-3.5z"/>'),
    trays: svg('<rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/><rect x="7" y="8" width="4.5" height="4" rx="1"/><rect x="12.5" y="8" width="4.5" height="4" rx="1"/>'),
    folder: svg('<path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>'),
    back: svg('<path d="M15 6l-6 6 6 6"/>', 1.8), fwd: svg('<path d="M9 6l6 6-6 6"/>', 1.8),
    clock: svg('<circle cx="12" cy="12" r="8"/><path d="M12 7.5V12l3 2"/>'),
    star: svg('<path d="M12 3.8l2.5 5.1 5.6.8-4 3.9.9 5.6-5-2.6-5 2.6.9-5.6-4-3.9 5.6-.8z"/>'),
    search: svg('<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>', 1.7),
    theme: svg('<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 0 0 16z" fill="currentColor"/>'),
    colL: svg('<path d="M14 7l-5 5 5 5"/><path d="M19 5v14"/>', 1.7), colR: svg('<path d="M10 7l5 5-5 5"/><path d="M5 5v14"/>', 1.7),
    menu: svg('<path d="M4 7h16M4 12h16M4 17h10"/>', 1.7),
    x: svg('<path d="M6 6l12 12M18 6L6 18"/>', 1.7),
    toc: svg('<path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01"/>', 1.7),
    find: svg('<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.3-4.3"/>', 1.7),
    hist: svg('<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1"/><path d="M3 4.5V9h4.5"/><path d="M12 8v4.5l3 2"/>', 1.7),
    split: svg('<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M12 5v14"/>', 1.7),
    mirror: svg('<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M12 5v14M6.5 10h3M14.5 10h3M6.5 13.5h3M14.5 13.5h3"/>', 1.5),
    width: svg('<path d="M3 12h18M7 8l-4 4 4 4M17 8l4 4-4 4"/>', 1.7),
    pin: svg('<path d="M9 4h6l-1 6 3 3H7l3-3z"/><path d="M12 13v7"/>', 1.7),
    up: svg('<path d="M6 15l6-6 6 6"/>', 2), down: svg('<path d="M6 9l6 6 6-6"/>', 2),
    doc: svg('<path d="M7 3.5h7l4 4V20.5H7z"/><path d="M14 3.5V8h4"/>'),
    code: svg('<path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/>', 1.7),
    tab: svg('<path d="M14 4h6v6M20 4l-8 8"/><path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>', 1.7),
    cal: svg('<rect x="4" y="5.5" width="16" height="14" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>', 1.8),
    done: svg('<path d="M5 12.5l4.5 4.5L19 7.5"/>', 2.2),
    box: svg('<rect x="5" y="5" width="14" height="14" rx="2.5"/><path d="M8.5 12l2.5 2.5 4.5-5"/>', 1.8),
    undo: svg('<path d="M9 14L4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>', 1.8),
    redo: svg('<path d="M15 14l5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>', 1.8),
    p1: svg('<path d="M6 13l6-6 6 6M6 19l6-6 6 6"/>', 2.2), p2: svg('<path d="M6 15.5l6-6 6 6"/>', 2.2), p3: svg('<path d="M6 9.5l6 6 6-6"/>', 2.2),
    tick: '<svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 6.3l2.3 2.2 4.7-5"/></svg>',
  };
  V.frac = (a, b) => `<span class="fr">${a}<i>/</i><s>${b}</s></span>`;
  const since = (s, units) => { for (const [lim, div, unit] of units) if (s < lim) return div ? Math.round(s / div) + unit : unit; };
  V.ago = sec => (sec ? since(Date.now() / 1000 - sec, [[90, 0, "now"], [3600, 60, "m"], [86400, 3600, "h"], [Infinity, 86400, "d"]]) : "");
  V.relT = ms => since((Date.now() - ms) / 1000, [[45, 0, "刚才"], [3600, 60, " 分钟前"], [86400, 3600, " 小时前"], [Infinity, 86400, " 天前"]]);
  let toastT;
  V.toast = m => { const t = $("#toast"); t.textContent = m; t.classList.add("on"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("on"), V.CFG.toastMs); };
  // the clipboard API only exists on a secure context (not a plain-http --lan IP page): fall back to execCommand inside the click
  const execCopy = text => {
    const ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;opacity:0";
    document.body.appendChild(ta); ta.select(); let ok = false; try { ok = document.execCommand("copy"); } catch (e) {} ta.remove(); return ok;
  };
  V.copy = (text, ok) => {
    const done = () => V.toast(ok), no = () => V.toast("复制失败，浏览器没有允许");
    if (!(window.isSecureContext && navigator.clipboard)) return execCopy(text) ? done() : no();
    navigator.clipboard.writeText(text).then(done, () => (execCopy(text) ? done() : no()));
  };

  /* ---- events between the area files ---- */
  const subs = {};
  V.on = (ev, fn) => (subs[ev] = subs[ev] || []).push(fn);
  V.emit = (ev, ...a) => (subs[ev] || []).forEach(fn => fn(...a));

  /* ---- data: board + both trees, re-read on every dev/kb change ---- */
  V.D = { board: {}, tree: { dev: [], kb: [] }, cards: [], byId: {}, sets: { dev: new Map(), kb: new Map() }, mtime: { dev: {}, kb: {} }, pages: { untrusted: {} }, at: 0 };
  const PH = ["需求", "设计", "详设", "实现", "测试", "评审"];
  V.phaseNow = c => {
    if (c.st === "done") return "已完成"; if (c.st === "dropped") return "已放弃";
    if (c.lite) return c.liteSt || "lite";
    const i1 = c.ph.indexOf(1); if (i1 >= 0) return PH[i1] + "中";
    const i0 = c.ph.indexOf(0); return i0 >= 0 ? PH[i0] + "待开始" : "六段完成";
  };
  V.nextOf = c => {
    const t = (c.next || "").replace(/^—.*$/, "").replace(/^done — nothing pending$/, "").trim();
    return t || (c.lite ? `Req ${c.ok}/${c.req} 已验证` : V.phaseNow(c));
  };
  V.load = () => Promise.all([V.json("/api/board"), V.json("/api/tree?html=1")]).then(([b, t]) => {
    const D = V.D; D.board = b; D.tree = t; D.pages = t.pages; D.at = Date.now();
    D.cards = Object.keys(b).reduce((a, p) => a.concat(b[p].map(SV.cardView)), []);
    D.byId = {}; D.cards.forEach(c => { D.byId[c.id] = c; });
    t.ext = t.ext || [];
    ["dev", "kb", "ext"].forEach(k => {
      D.sets[k] = new Map(t[k].map(it => [it.path.toLowerCase(), it.path]));
      D.mtime[k] = {}; t[k].forEach(it => { D.mtime[k][it.path] = it.mtime; });
    });
  });
  V.absPath = (tree, rel) => {
    const R = V.D.tree.roots; if (!R) return "";
    if (tree !== "ext") return R[tree] ? R[tree] + "/" + rel : "";
    const i = rel.indexOf("/"), root = R.ext && R.ext[rel.slice(0, i)]; return root ? root + rel.slice(i) : "";
  };
  // an html page is served from /page/<key>/: trusted files share a key, each untrusted root has its own (null = trusted)
  V.isPage = rel => /\.html$/i.test(rel || "");
  V.pageKey = (tree, rel) => { const k = tree + ":" + rel, u = V.D.pages.untrusted; let best = ""; for (const p in u) if (k.startsWith(p) && p.length > best.length) best = p; return best ? u[best] : null; };
  V.pageSandboxed = (tree, rel) => V.pageKey(tree, rel) != null;
  V.pageURL = (tree, rel) => "/page/" + (V.pageKey(tree, rel) || V.D.pages.t) + "/" + tree + "/" + rel.split("/").map(encodeURIComponent).join("/");
  V.openPageTab = (tree, rel) => window.open(V.pageURL(tree, rel), "_blank", "noopener");
  V.card = id => V.D.byId[id];
  V.cardOfPath = (tree, rel) => { if (tree !== "dev") return null; const m = /^([^/]+)\/(\d{3})-/.exec(rel || ""); return m ? V.D.byId[m[1] + "/" + m[2]] : null; };
  V.docsOf = c => V.D.tree.dev.filter(it => it.path.startsWith(c.dir + "/")).map(it => ({ rel: it.path, mtime: it.mtime }));
  V.mainDoc = c => {
    const d = V.docsOf(c), m = d.find(x => x.rel === c.dir + "/design.md") || d.find(x => x.rel === c.dir + "/requirement.md") || d[0];
    return m ? m.rel : null;
  };

  /* ---- columns: drag to resize, click to collapse; width regimes by viewport only ---- */
  const app = $("#app"); V.app = app;
  const W = V.W = Object.assign({ wn: 240, ws: 250, wa: .5, nc: false, sc: false, dc: true, nx: false, sx: false, hd: 0 }, V.store.get("w", {}));
  V.saveW = () => V.store.set("w", W);
  V.isNarrow = () => app.classList.contains("narrow");
  V.applyW = () => {
    const nar = V.isNarrow(), nt = $("#navTog");
    app.style.setProperty("--wnu", W.wn + "px"); app.style.setProperty("--wsu", W.ws + "px");
    if (W.hd) app.style.setProperty("--hd", W.hd + "px"); else app.style.removeProperty("--hd");
    app.classList.toggle("hdset", !!W.hd); app.classList.toggle("dc", !!W.dc);
    $("#reader").style.setProperty("--wa", (W.wa / (1 - W.wa)) + "fr");
    app.classList.toggle("nx", !!W.nx && nar); app.classList.toggle("sx", !!W.sx && nar);
    app.classList.toggle("nc", W.nc || nar); app.classList.toggle("sc", W.sc || nar);
    const tip = nar ? (app.classList.contains("navpop") ? "恢复左侧竖条" : "完全收起左栏") : W.nc ? "展开导航" : "收起导航";
    nt.dataset.tip = tip; nt.setAttribute("aria-label", tip);
    const st = $("#sideTog"), stip = app.classList.contains("phone") ? "关闭目录" : nar ? (W.sx ? "恢复右侧竖条" : "完全收起右栏") : W.sc ? "展开右栏" : "收起右栏";
    st.dataset.tip = stip; st.setAttribute("aria-label", stip);
    const so = $("#sideOpen"), otip = nar ? "完全收起右栏" : "展开目录";
    so.dataset.tip = otip; so.setAttribute("aria-label", otip);
  };
  V.relayout = () => V.emit("layout");
  $$(".gut").forEach(g => {
    let st = null;
    g.addEventListener("pointerdown", e => { g.setPointerCapture(e.pointerId); g.classList.add("drag"); st = { x: e.clientX, wn: W.wn, ws: W.ws }; });
    g.addEventListener("pointermove", e => {
      if (!st) return; const dx = e.clientX - st.x, k = g.dataset.g;
      if (k === "nav") { W.nc = false; W.wn = Math.max(170, Math.min(520, st.wn + dx)); }
      else if (k === "side") { W.sc = false; W.ws = Math.max(190, Math.min(520, st.ws - dx)); }
      else { const r = $("#reader").getBoundingClientRect(); W.wa = Math.max(.22, Math.min(.78, (e.clientX - r.left) / r.width)); }
      V.applyW();
    });
    const end = () => { if (!st) return; st = null; g.classList.remove("drag"); V.saveW(); V.relayout(); };
    g.addEventListener("pointerup", end); g.addEventListener("pointercancel", end);
    g.addEventListener("dblclick", () => {
      const k = g.dataset.g;
      if (k === "nav") W.nc = !W.nc; else if (k === "side") W.sc = !W.sc; else W.wa = .5;
      V.applyW(); V.saveW(); V.relayout();
    });
  });
  { const hg = $("#hgut"); let st = null;
    hg.addEventListener("pointerdown", e => { hg.setPointerCapture(e.pointerId); hg.classList.add("drag"); st = { y: e.clientY, h: $("#bdet").offsetHeight }; });
    hg.addEventListener("pointermove", e => { if (!st) return; W.dc = false; W.hd = Math.max(90, Math.min(innerHeight * .75, st.h - (e.clientY - st.y))); V.applyW(); });
    const end = () => { if (!st) return; st = null; hg.classList.remove("drag"); V.saveW(); };
    hg.addEventListener("pointerup", end); hg.addEventListener("pointercancel", end);
    hg.addEventListener("dblclick", () => V.emit("detail-close")); }
  // narrow: each side's collapse button hides its rail fully, and inside that side's drawer it brings the rail back
  V.toggleCol = (k, el) => {
    if (k === "det") return V.emit("detail-close");
    if (V.isNarrow()) {
      if (k === "nav") { W.nx = !app.classList.contains("navpop"); app.classList.remove("navpop", "treepop"); V.applyW(); V.saveW(); }
      else if (el && (el.id === "sideTog" || el.id === "sideOpen")) {   // as on the nav: the rail's button hides the rail; a phone has no rail, so it only closes the drawer
        if (!app.classList.contains("phone")) W.sx = !W.sx;
        app.classList.remove("tocpop"); V.applyW(); V.saveW();
      }
      else app.classList.toggle("tocpop");
      return;
    }
    if (k === "nav") W.nc = !W.nc; else W.sc = !W.sc;
    V.applyW(); V.saveW(); V.relayout();
  };
  V.sizeClasses = () => {
    const w = innerWidth, h = innerHeight, was = V.isNarrow();
    app.classList.toggle("narrow", w < 900); app.classList.toggle("phone", w < 600);
    app.classList.toggle("short", h < 500); app.classList.toggle("mid", w >= 900 && w < 1180);
    if (was !== V.isNarrow()) {
      app.classList.remove("treepop", "tocpop", "navpop");
      if (V.isNarrow() && V.isSplit()) V.setSplit(false);   // narrow reads in one pane; B keeps what it showed for the next split
      V.emit("narrow", V.isNarrow());
    }
    V.applyW(); V.relayout();
  };

  /* ---- theme ---- */
  V.THEMES = [["", "跟随系统", ["#E9E9E4", "#0D1015"]], ["light", "骨白", ["#E9E9E4", "#2A3CC8"]], ["dark", "深空", ["#0D1015", "#7F8EF0"]],
    ["amber", "琥珀", ["#F7F7F4", "#B9761A"]], ["amber-dark", "琥珀暗", ["#0A0B0D", "#E5A54F"]]];
  V.isDark = () => { const t = document.documentElement.getAttribute("data-theme"); return t ? /dark/.test(t) : matchMedia("(prefers-color-scheme: dark)").matches; };
  V.setTheme = (k, btn) => {
    const root = document.documentElement;
    const apply = () => { if (k) root.setAttribute("data-theme", k); else root.removeAttribute("data-theme"); V.store.set("theme", k); V.applyLum(); V.emit("theme"); };
    if (!document.startViewTransition || V.RM || !btn) return apply();
    const r = btn.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2, R = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    document.startViewTransition(apply).ready.then(() => root.animate({ clipPath: [`circle(0 at ${x}px ${y}px)`, `circle(${R}px at ${x}px ${y}px)`] },
      { duration: 540, easing: "cubic-bezier(.65,0,.25,1)", pseudoElement: "::view-transition-new(root)" })).catch(() => {});
  };
  { const t0 = V.store.get("theme", ""); if (t0) document.documentElement.setAttribute("data-theme", t0); }
  // brightness in three parts — the interface's surfaces (blum), its text (lum), the reading text (tlum) — kept per theme
  // (跟随系统 shares the look it shows, light or dark; a theme not yet set starts from the old shared value): each scales
  // the lightness of its colour tokens, read fresh from the theme, so hues stay; the reader and the editor take the text
  // tokens from their own -r copies
  const SURF = ["--chrome", "--paper", "--card", "--card2", "--ln", "--ln2"], TEXT = ["--ink", "--tx", "--mu", "--faint"];
  const lumKey = k => k + ":" + (document.documentElement.getAttribute("data-theme") || (V.isDark() ? "dark" : "light"));
  V.lumOf = k => V.store.get(lumKey(k), V.store.get(k, 100));
  V.applyLum = () => {
    const root = document.documentElement, f = k => V.lumOf(k) / 100;
    SURF.concat(TEXT, TEXT.map(p => p + "-r")).forEach(p => root.style.removeProperty(p));
    const cs = getComputedStyle(root), scale = (p, k) => { const c = cs.getPropertyValue(p).trim(); return k === 1 ? c : `oklch(from ${c} calc(l * ${k}) c h)`; };
    SURF.forEach(p => { if (f("blum") !== 1) root.style.setProperty(p, scale(p, f("blum"))); });
    TEXT.forEach(p => { root.style.setProperty(p + "-r", scale(p, f("tlum"))); if (f("lum") !== 1) root.style.setProperty(p, scale(p, f("lum"))); });
  };
  V.setLum = (k, v) => { v = Math.max(60, Math.min(200, Math.round(+v) || 100)); V.store.set(lumKey(k), v); V.applyLum(); return v; };
  V.applyLum();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { V.applyLum(); V.emit("theme"); });

  /* ---- popovers: one open at a time, placed under (or above) their anchor ---- */
  V.closePops = () => $$(".pop.on").forEach(p => { if (p.id !== "tip") p.classList.remove("on"); });
  V.pop = (id, html, anchor, align) => {
    const pop = $("#" + id); V.closePops(); pop.innerHTML = html; pop.classList.add("on");
    const r = anchor.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
    const left = align === "right" ? r.right - w : r.left;
    pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, left)) + "px";
    pop.style.top = (r.bottom + h + 12 > innerHeight && r.top - h - 6 > 8 ? r.top - h - 6 : r.bottom + 6) + "px";
    return pop;
  };
  V.isPop = id => $("#" + id).classList.contains("on");
  V.themePop = btn => {
    const cur = document.documentElement.getAttribute("data-theme") || "";
    const item = ([k, n, sw]) => `<button class="thm ${k === cur ? "on" : ""}" data-theme-k="${k}" role="menuitemradio" aria-checked="${k === cur}">`
      + `<span class="sw">${sw.map(c => `<i style="background:${c}"></i>`).join("")}</span>${n}<span class="ck">${k === cur ? V.I.tick : ""}</span></button>`;
    const lum = ([k, l]) => { const v = V.lumOf(k);
      return `<div class="lum"><span>${l}</span><input data-lum="${k}" type="range" min="60" max="200" step="2" value="${v}" aria-label="${l}亮度">`
        + `<em>${v}%</em><button data-lum0="${k}" data-tip="回到 100%">复位</button></div>`; };
    V.pop("themePop", V.THEMES.map(item).join("") + [["blum", "底色"], ["lum", "界面字"], ["tlum", "正文"]].map(lum).join(""), btn);
  };

  /* ---- status bar: the current view's line, or what the hovered control does ---- */
  let tipOn = null;
  V.statusFns = {};
  V.status = () => { if (tipOn) return; const f = V.statusFns[V.view]; $("#status").innerHTML = f ? f() : ""; };
  V.stamp = () => {   // when the data on screen was read
    const d = new Date(V.D.at || Date.now()), two = n => String(n).padStart(2, "0");
    return `<span>dev_root　${two(d.getMonth() + 1)}-${two(d.getDate())} ${two(d.getHours())}:${two(d.getMinutes())}</span>`;
  };
  function tipOf(el) {
    if (el.dataset.tip) return el.dataset.tip;
    if (el.title) { el.dataset.tip = el.title; el.removeAttribute("title"); return el.dataset.tip; }
    if (el.dataset.open) return el.dataset.open;
    return el.textContent.replace(/\s+/g, " ").trim();
  }
  document.addEventListener("mouseover", e => {
    const tb = e.target.closest("[data-tip]") || e.target.closest(".tr,.hi,.li,.sta,.qr,.kf,.thm");
    if (tb && tb !== tipOn) {
      tipOn = tb;
      $("#status").innerHTML = `<span class="tipx">${esc(tipOf(tb))}${tb.dataset.key ? `<kbd>${esc(tb.dataset.key)}</kbd>` : ""}</span>`;
    }
    else if (!tb && tipOn) { tipOn = null; V.status(); }
  });
  V.untip = () => { tipOn = null; };

  /* ---- click dispatch: area files register selectors; the first match handles the click ---- */
  const clicks = [];
  V.click = (sel, fn) => clicks.push([sel, fn]);
  V.paneOf = el => (el.closest("#pB") ? "B" : "A");
  document.addEventListener("click", e => {
    V.emit("click", e);
    for (const [sel, fn] of clicks) { const el = e.target.closest(sel); if (el && fn(el, e) !== false) return; }
  });
  // ⇧-click on a navigation target must not extend the text selection
  document.addEventListener("mousedown", e => { if (e.shiftKey && e.target.closest("[data-open],[data-card],.md a,.cite,.qr,.shit")) e.preventDefault(); });

  /* ---- keyboard: Esc closes one layer at a time; single-key hotkeys never fire with a modifier ---- */
  const layers = [], keys = {};
  V.layer = (pri, isOpen, close) => { layers.push({ pri, isOpen, close }); layers.sort((a, b) => b.pri - a.pri); };
  V.hotkey = (k, fn) => { keys[k] = fn; };
  V.chord = {};   // ⌘ + key, or ctrl+shift + key, registered by area files
  // plain ctrl + a letter is left to the text field: on macOS ctrl+K deletes to the line's end, ctrl+B moves back
  V.isChord = e => e.metaKey || (e.ctrlKey && e.shiftKey);
  document.addEventListener("keydown", e => {
    if (V.isChord(e) && !e.altKey && V.chord[e.key.toLowerCase()]) { if (V.chord[e.key.toLowerCase()](e) !== false) e.preventDefault(); return; }
    if (e.key === "Escape") { const l = layers.find(x => x.isOpen()); if (l) { e.preventDefault(); l.close(); } return; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target.closest && e.target.closest("input,textarea,select,[contenteditable]")) return;
    if (e.key === "Enter" && e.target.matches && e.target.matches("[role=link]:not(a[href])")) {   // a span or href-less link: no native activation
      e.preventDefault(); e.target.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: e.shiftKey })); return;
    }
    if (/^(Enter|Arrow)/.test(e.key) && e.target.closest && e.target.closest("button:not([data-card]),a,[role=link]")) return;
    const fn = keys[e.key]; if (fn && fn(e) !== false) e.preventDefault();
  });
  V.layer(60, () => V.isPop("tip") || $$(".pop.on").some(p => p.id !== "tip"), () => { V.closePops(); V.emit("tip-hide"); });
  const DRAWERS = ["navpop", "treepop", "tocpop"];
  V.layer(50, () => DRAWERS.some(c => app.classList.contains(c)), () => { app.classList.remove(...DRAWERS); V.applyW(); });

  /* ---- panes: A and B each show one thing — a doc, or one of the views (board, search, diff, recent) ---- */
  const P = V.P = { A: { k: "A", hist: [], fwd: [], loc: null }, B: { k: "B", hist: [], fwd: [], loc: null } };
  const SECTIONS = { board: "#board", search: "#search", diff: "#diffv", recent: "#recent", todo: "#todo" };
  V.view = "board";   // what the focused pane shows: the keys and the status bar follow it
  V.focus = "A";
  V.views = {};   // kind → render(k, loc, opt), registered by the area files
  V.isSplit = () => $("#reader").classList.contains("split");
  V.other = k => (k === "A" ? "B" : "A");
  V.kindOf = k => (P[k].loc ? P[k].loc.kind : null);
  V.hostOf = kind => ["A", "B"].find(k => V.kindOf(k) === kind) || "A";
  V.navPane = () => (V.isSplit() ? V.focus : "A");
  V.readingK = () => (V.view === "doc" ? V.navPane() : null);   // the pane whose doc the keys act on, if any
  // a view's one DOM section moves into the pane that shows it; that pane's doc chrome hides meanwhile
  function mount() {
    ["A", "B"].forEach(k => {
      const kind = V.kindOf(k), sec = SECTIONS[kind] && $(SECTIONS[kind]), el = P[k].el;
      if (sec && sec.parentElement !== el) el.appendChild(sec);
      el.className = el.className.replace(/\bh-\w+/g, "").trim();
      el.classList.toggle("hosting", !!sec); if (sec) { el.classList.add("h-" + kind); el.classList.remove("blank"); }
    });
    Object.keys(SECTIONS).forEach(kind => { $(SECTIONS[kind]).hidden = !["A", "B"].some(k => V.kindOf(k) === kind); });
    V.view = V.kindOf(V.navPane()) || "blank";
    const docShown = ["A"].concat(V.isSplit() ? ["B"] : []).some(k => V.kindOf(k) === "doc");
    app.classList.toggle("v-board", !docShown && V.view !== "search");
  }
  V.paneHead = k => `<span class="ptag">${k}</span>`;
  V.paneEnd = k => (k === "A" ? `<button class="ib${V.isSplit() ? " on" : ""}" data-t="split" data-tip="双栏对照" data-key="\\" aria-label="双栏对照">${V.I.split}</button>`
    : `<button class="ib" data-t="close" data-tip="关闭右栏" aria-label="关闭右栏">${V.I.x}</button>`);
  V.setFocus = k => {
    if (k === "B" && !V.isSplit()) k = "A";
    if (V.focus === k) return;
    V.focus = k; P.A.el.classList.toggle("focus", k === "A"); P.B.el.classList.toggle("focus", k === "B"); app.classList.toggle("fB", k === "B");
    mount(); V.emit("focus", k); V.status();
  };
  V.setSplit = on => {
    if (on && V.isNarrow()) return;
    $("#reader").classList.toggle("split", on);
    $$('[data-t="split"]').forEach(b => b.classList.toggle("on", on));
    if (on && !P.B.loc) V.emit("blank", "B");
    if (!on) V.setFocus("A");
    mount(); V.emit("split", on); V.relayout(); V.status();
  };
  const same = (a, b) => a && b && a.kind === b.kind && a.tree === b.tree && a.rel === b.rel && a.q === b.q && a.card === b.card;
  // a doc goes into history with its scroll position, so back and forward land where the reader was
  V.here = p => (p.loc && p.loc.kind === "doc" && p.body ? Object.assign({}, p.loc, { top: p.body.scrollTop, xid: null, line: 0, hash: null }) : p.loc);
  // the one way to change what a pane shows: leaving writes the reading place, history is per pane
  V.nav = (k, loc, opt = {}) => {
    if (V.isNarrow()) { app.classList.remove("navpop", "treepop", "tocpop"); V.applyW(); k = "A"; }
    if (opt.push === false && loc.top != null && same(P[k].loc, loc) && P[k].doc && !P[k].doc.err && !P[k].chg) {   // back/forward within one doc: scroll, no re-render
      P[k].loc = loc; P[k].body.scrollTop = loc.top; V.setFocus(k); V.paintHist(); V.emit("nav", k, loc); return;
    }
    if (k === "B" && !P.A.loc && opt.push !== false) k = "A";   // a new pick fills a blank A first; back/forward stay in their pane
    const p = P[k], o = P[V.other(k)];
    if (p.loc) V.emit("leave", k, p.loc);
    if (opt.push !== false && p.loc && !same(p.loc, loc)) { p.hist.push(V.here(p)); p.fwd.length = 0; }
    p.loc = loc;
    if (loc.kind !== "doc" && o.loc && o.loc.kind === loc.kind) {   // one board, one search: the other pane gives it up, keeping it in its history
      V.emit("leave", o.k, o.loc); o.hist.push(o.loc); o.fwd.length = 0; o.loc = null; V.emit("blank", o.k);
    }
    if (k === "B" && !V.isSplit()) V.setSplit(true);
    mount(); V.setFocus(k);
    if (loc.kind === "doc" && opt.user !== false) V.recent.push("opened", loc.tree + ":" + loc.rel, V.CFG.trail);
    V.views[loc.kind](k, loc, Object.assign({ entering: true }, opt));
    V.paintHist(); V.emit("nav", k, loc);
  };
  V.goBoard = e => {   // the board where it already is, else in the target pane
    const at = ["A"].concat(V.isSplit() ? ["B"] : []).find(k => V.kindOf(k) === "board");
    if (at && !(e && e.shiftKey)) return V.setFocus(at);
    V.nav(V.target(e), { kind: "board" });
  };
  V.back = k => { const p = P[k || V.navPane()]; if (!p.hist.length) return; const to = p.hist.pop(); if (p.loc) p.fwd.push(V.here(p)); V.nav(p.k, to, { push: false, user: false }); };
  V.fwd = k => { const p = P[k || V.navPane()]; if (!p.fwd.length) return; const to = p.fwd.pop(); if (p.loc) p.hist.push(V.here(p)); V.nav(p.k, to, { push: false, user: false }); };
  V.rerender = k => { const p = P[k]; if (p.loc) V.views[p.loc.kind](k, p.loc, { entering: false }); };
  V.locLabel = l => (!l ? "" : l.kind === "doc" ? l.rel.split("/").pop() : l.kind === "search" ? "搜索「" + l.q + "」"
    : l.kind === "diff" ? l.card + " 的改动" : l.kind === "recent" ? "最近提交" : l.kind === "todo" ? "todo" : "看板");
  V.paintHist = () => {
    const p = P[V.navPane()], b = $("#back"), f = $("#fwd");
    b.disabled = !p.hist.length; f.disabled = !p.fwd.length;
    const t = p.hist[p.hist.length - 1], n = p.fwd[p.fwd.length - 1], side = V.isSplit() ? p.k + " 栏" : "";
    b.dataset.tip = t ? `${side}后退到 ${V.locLabel(t)}` : "后退"; f.dataset.tip = n ? `${side}前进到 ${V.locLabel(n)}` : "前进";
  };
  V.on("focus", V.paintHist);
  // reading side by side, a doc picked from the nav lands in the focused pane; ⇧ sends it to the other one
  V.target = e => { const k = V.isSplit() ? V.focus : "A"; return e && e.shiftKey ? (k === "A" ? "B" : "A") : k; };
  V.openDoc = (tree, rel, e, extra) => V.nav(V.target(e), Object.assign({ kind: "doc", tree, rel }, extra || {}));

  /* ---- live refresh: poll the dev/kb change tokens; areas refresh in place ---- */
  let rev = null, polling = false;
  V.poll = () => {
    if (polling || document.hidden) return; polling = true;
    V.json("/api/rev").then(d => {
      const changed = rev && (d.dev !== rev.dev || d.kb !== rev.kb || d.ext !== rev.ext); rev = d;
      return changed ? V.load().then(() => V.emit("data")) : null;
    }).catch(() => {}).then(() => { polling = false; V.emit("tick"); });
  };

  /* ---- shared clicks and keys ---- */
  V.click("[data-theme-k]", el => { V.closePops(); V.setTheme(el.dataset.themeK, $("#themeBtn")); });
  V.click("#themeBtn", el => (V.isPop("themePop") ? V.closePops() : V.themePop(el)));
  V.click("[data-col]", el => { V.toggleCol(el.dataset.col, el); V.applyW(); });
  V.click("#back", () => V.back()); V.click("#fwd", () => V.fwd());
  V.click("[data-navb]", () => { app.classList.toggle("navpop"); V.applyW(); if (app.classList.contains("navpop")) V.emit("tree-show"); });
  V.click("[data-goboard]", (el, e) => { app.classList.remove("treepop"); V.goBoard(e); });
  V.hotkey("[", () => V.back()); V.hotkey("]", () => V.fwd());
  V.hotkey("b", () => V.goBoard());
  V.on("click", e => {
    const t = e.target;
    if (app.classList.contains("navpop") && (!t.closest("#nav") || t.closest("[data-open],[data-goboard]"))) { app.classList.remove("navpop"); V.applyW(); }
    if (app.classList.contains("tocpop") && !t.closest("#side,[data-t=toc],[data-sec]")) { app.classList.remove("tocpop"); V.applyW(); }
    if (app.classList.contains("treepop") && !t.closest("#treeWrap,#filesBtn")) { app.classList.remove("treepop"); $("#filesBtn").setAttribute("aria-expanded", false); }
    if (!t.closest(".pop") && !t.closest("[data-popbtn]")) V.closePops();
  });
  V.click("#filesBtn", () => {
    const on = !app.classList.contains("treepop");
    app.classList.toggle("treepop", on); $("#filesBtn").setAttribute("aria-expanded", on); if (on) V.emit("tree-show");
  });

  document.addEventListener("input", e => { const k = e.target.dataset && e.target.dataset.lum; if (k) e.target.nextElementSibling.textContent = V.setLum(k, e.target.value) + "%"; });
  V.click("[data-lum0]", el => { const k = el.dataset.lum0; V.setLum(k, 100); const i = $(`[data-lum="${k}"]`); if (i) { i.value = 100; i.nextElementSibling.textContent = "100%"; } });

  /* ---- help: every key in one panel ---- */
  const KEYS = [["全局", [["⌘K", "搜索文档、卡片与 Fact"], ["/", "全文搜索"], ["b", "看板"], ["[ ]", "焦点栏后退、前进"], ["\\", "打开或关闭右栏"], ["?", "这个面板"], ["esc", "一次关一层"], ["⌃⇧ + 键", "代替 ⌘ + 键（单按 ⌃ 留给文字编辑）"]]],
    ["文档", [["f", "在本文查找"], ["h", "钉住选中的词"], ["⇧H", "清空钉住词"], ["s", "加或取消星标"], ["⇧ 点击", "在另一栏打开"], ["↵", "跟随聚焦的引用或链接"]]],
    ["看板", [["方向键", "移动选中的卡"], ["↵ / 双击", "打开 design.md"], ["⇧ 点击", "在另一栏打开"]]],
    ["查找框", [["↵ ⇧↵", "下一个、上一个"], ["⌘↵", "钉住这个词"], ["↑ ↓", "查找历史"]]],
    ["⌘K", [["↑ ↓", "选择"], ["↵", "打开"], ["⇧↵", "在另一栏打开"], ["⌘↵", "全文搜索"], ["⇧⌘↵", "在另一栏全文搜索"]]]];
  V.toggleHelp = () => {
    const h = $("#help"); h.hidden = !h.hidden; if (h.hidden) return;
    V.closePops();
    h.firstChild.innerHTML = '<div class="pt">快捷键</div><div class="hgrid">' + KEYS.map(([g, rows]) => `<section><h4>${g}</h4>`
      + rows.map(([k, d]) => `<div><kbd>${esc(k)}</kbd><span>${esc(d)}</span></div>`).join("") + "</section>").join("") + "</div>";
  };
  V.hotkey("?", () => V.toggleHelp());
  V.click("#helpBtn", () => V.toggleHelp());
  document.addEventListener("click", e => { if (e.target.id === "help") $("#help").hidden = true; });
  V.layer(70, () => !$("#help").hidden, () => { $("#help").hidden = true; });

  /* ---- ask: the page's own confirm and prompt, in the theme. Resolves to the chosen button's value (with a text field:
     the text, for the first button), or null on Esc or a click outside; the focus goes back where it was ---- */
  let askDone = null;
  V.ask = (msg, btns, text) => new Promise(res => {
    if (askDone) askDone(null);
    const box = $("#ask .askbox"), back = document.activeElement;
    box.innerHTML = `<div class="askm">${esc(msg)}</div>` + (text != null ? `<input class="capin" value="${esc(text)}" aria-label="${esc(msg)}">` : "")
      + `<div class="qf askf"><span><kbd>↵</kbd>${esc(btns[0][1])}</span><span><kbd>esc</kbd>取消</span>`
      + btns.map(([, l], i) => `<button type="button" class="${i ? "" : "ok"}" data-ask="${i}">${esc(l)}</button>`).join("") + "</div>";
    $("#ask").hidden = false;
    askDone = i => {
      askDone = null; $("#ask").hidden = true; if (back && back.focus) back.focus();
      res(i == null ? null : text != null ? (i === 0 ? $(".capin", box).value : null) : btns[i][0]);
    };
    const f = $(".capin", box) || $("button", box); f.focus(); if (f.select) f.select();
  });
  V.layer(95, () => !$("#ask").hidden, () => askDone && askDone(null));
  V.click("#ask [data-ask]", el => askDone && askDone(+el.dataset.ask));
  V.click("#ask", (el, e) => { if (e.target.id === "ask" && askDone) askDone(null); });
  document.addEventListener("submit", e => { if (e.target.closest("#ask") && askDone) { e.preventDefault(); askDone(0); } });
  // keys stay inside: a held Esc (the one that opened it, repeating) must not close it, and letters are not hotkeys here
  document.addEventListener("keydown", e => {
    if (!e.target.closest || !e.target.closest("#ask")) return;
    e.stopPropagation();
    if (e.key === "Escape") { e.preventDefault(); if (!e.repeat && askDone) askDone(null); }
  }, true);

  /* ---- boot: after every area file has registered ---- */
  document.addEventListener("DOMContentLoaded", () => {
    P.A.el = $("#pA"); P.B.el = $("#pB");
    const ICONS = { filesBtn: "folder", back: "back", fwd: "fwd", trailBtn: "clock", starBtn: "star", qBtn: "search", themeBtn: "theme",
      navTog: "colL", sideTog: "colR", sideOpen: "colL" };
    Object.keys(ICONS).forEach(id => { $("#" + id).innerHTML = V.I[ICONS[id]]; });
    $('#nav [data-goboard]').innerHTML = V.I.grid;
    V.emit("init");
    V.sizeClasses(); addEventListener("resize", V.sizeClasses);
    $("#tree").innerHTML = '<div class="hint">加载中…</div>';
    V.load().then(() => { V.emit("data"); V.nav("A", { kind: "board" }, { push: false }); })
      .catch(e => { $("#bscroll").innerHTML = `<div class="empty-b">读不到数据：${esc(e.message)}</div>`; });
    setInterval(V.poll, V.CFG.pollMs);
  });
  return V;
})();
