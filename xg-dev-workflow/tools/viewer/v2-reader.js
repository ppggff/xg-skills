/* status viewer v2 — reader: a doc in pane A or B. Rendering (marked + wikilinks + id citations), link
   resolution, citation jumps and previews, line numbers, reading width, the reading place kept by content
   anchor, the TOC with its rail, the current line, mermaid, the stale notice, change history and the change view. */
"use strict";
(function (V) {
  const { $, $$, esc, store, P } = V;
  const HEAD_PAD = 16;

  /* ---- markdown: wikilinks and id citations share SV's grammar with the classic shell ---- */
  window.marked.use({ extensions: [{
    name: "wikilink", level: "inline",
    start: src => src.indexOf("[["),
    tokenizer(src) { const m = /^\[\[([^\]]+)\]\]/.exec(src); if (m) return { type: "wikilink", raw: m[0], text: m[1] }; },
    renderer: t => `<a href="[[${esc(t.text)}]]">${esc(t.text)}</a>`,
  }, {
    name: "xid", level: "inline",
    start: src => SV.xidCiteStart(src),
    tokenizer(src) { const m = SV.xidCite(src); if (m) return { type: "xid", raw: m.raw, id: m.id, clause: m.clause }; },
    renderer: t => `<span class="cite" data-ref="${esc(t.id)}" tabindex="0" role="link">[<b>${esc(t.id + t.clause)}</b>]</span>`,
  }] });

  /* ---- pane chrome ---- */
  function shell(k) {
    const b = (t, icon, tip, key) => `<button class="ib" data-t="${t}" data-tip="${tip}"${key ? ` data-key="${key}"` : ""} aria-label="${tip}">${V.I[icon]}</button>`;
    return `<div class="phd"><button class="ib navb" data-navb data-tip="导航" aria-label="导航">${V.I.menu}</button><span class="ptag">${k}</span><span class="abw"><button data-ab="A" class="${k === "A" ? "on" : ""}">A</button><button data-ab="B" class="${k === "B" ? "on" : ""}">B</button></span><div class="ppath"></div>
      <button class="ib tocb" data-t="toc" data-tip="目录" aria-label="目录">${V.I.toc}</button>${b("star", "star", "加星标", "s")}${b("find", "find", "在本文查找", "f")}${b("hist", "hist", "这篇文档的变更历史")}${b("width", "width", "阅读宽度：默认 / 宽 / 铺满")}
      ${k === "A" ? b("split", "split", "双栏对照", "\\") : b("close", "x", "关闭右栏")}</div>
      <div class="stale"><span>这篇文档在磁盘上更新了</span><button data-stale>刷新</button></div><div class="chgbar" hidden></div>
      <div class="find" data-pane="${k}"></div><div class="pbody scroll"></div><div class="frail"></div><button class="secchip" data-sec data-tip="打开目录" aria-label="打开目录">${V.I.toc}<span></span></button>`;
  }
  const BLANK_B = `<div class="empty"><div><svg width="42" height="28" viewBox="0 0 46 30" fill="none" stroke="currentColor"><rect x=".5" y=".5" width="45" height="29" rx="3"/><path d="M23 .5v29"/><path d="M28 9h12M28 14h9M28 19h11" opacity=".5"/></svg>点正文里的 [Fact-n]，或按住 ⇧ 点一个链接，<br>文档会在这一栏打开。</div></div>`;
  V.on("init", () => ["A", "B"].forEach(k => {
    const p = P[k]; p.el.innerHTML = shell(k); p.body = $(".pbody", p.el); p.doc = null;
    if (k === "B") p.body.innerHTML = BLANK_B;
    p.body.addEventListener("scroll", () => onScroll(k), { passive: true });
    p.el.addEventListener("pointerdown", () => V.setFocus(k));
    p.body.addEventListener("click", e => {
      if (e.target.closest("a,button,.cite,.fmt,.fml,input,.mrule") || String(window.getSelection())) return;
      const blk = e.target.closest(".md p,.md li,.md h1,.md h2,.md h3,.md h4,.md h5,.md pre,.md tr,.md blockquote,.md .mermaid");
      if (blk) curLine(k, blk, e.clientY);
    });
  }));
  const keyOf = loc => loc.tree + ":" + loc.rel;

  /* ---- reading place: per (pane, doc), a content anchor first and pixels as the fallback ---- */
  const NOT_BLOCK = /^(lnum|curline|lastmark|mrule|fml|fmt)$/;
  const blocks = k => $$(".md > *", P[k].body).filter(el => ![...el.classList].some(c => NOT_BLOCK.test(c)));
  const blockText = el => (el.textContent || "").replace(/\s+/g, " ").trim();
  function topBlock(k) { const els = blocks(k), edge = P[k].body.getBoundingClientRect().top + HEAD_PAD; for (let i = 0; i < els.length; i++) if (els[i].getBoundingClientRect().bottom > edge) return i; return els.length - 1; }
  const memKey = (k, loc) => k + "|" + keyOf(loc);
  function savePlace(k) {
    const p = P[k], loc = p.loc; if (!loc || loc.kind !== "doc" || !p.doc || p.doc.err) return;
    const b = p.body, max = b.scrollHeight - b.clientHeight, mem = store.get("read", { order: [], map: {} }), old = mem.map[memKey(k, loc)] || {};
    const els = blocks(k), i = topBlock(k), into = els[i] ? b.getBoundingClientRect().top + HEAD_PAD - els[i].getBoundingClientRect().top : 0;
    const entry = { a: SV.anchorOf(els.map(blockText), i), o: Math.max(0, Math.round(into)), y: b.scrollTop, max: Math.max(old.max || 0, max > 0 ? b.scrollTop / max : 1) };
    store.set("read", SV.recallPut(mem, memKey(k, loc), entry, 50));
  }
  V.readPct = key => { const m = store.get("read", { map: {} }).map; return Math.round(Math.min(1, Math.max(0, ...["A", "B"].map(k => (m[k + "|" + key] || {}).max || 0))) * 100); };
  function restorePlace(k) {
    const p = P[k], e = store.get("read", { map: {} }).map[memKey(k, p.loc)];
    if (!e || !e.y) return false;
    const els = blocks(k), i = SV.anchorFind(els.map(blockText), e.a);
    if (i >= 0) p.body.scrollTop += els[i].getBoundingClientRect().top - p.body.getBoundingClientRect().top - HEAD_PAD + Math.min(e.o || 0, els[i].offsetHeight); else p.body.scrollTop = e.y;
    if (p.body.scrollTop > 300) setTimeout(() => lastMark(k), 60);
    return true;
  }
  V.on("leave", (k, loc) => { if (loc.kind === "doc") savePlace(k); });
  addEventListener("pagehide", () => ["A", "B"].forEach(savePlace));

  /* ---- render ---- */
  const merLoad = { p: null };
  function ensureMermaid() {
    if (window.mermaid) return Promise.resolve(window.mermaid);
    return merLoad.p || (merLoad.p = new Promise((ok, no) => {
      const s = document.createElement("script"); s.src = "/assets/mermaid.min.js";
      s.onload = () => { window.mermaid.initialize({ startOnLoad: false, theme: V.isDark() ? "dark" : "default" }); ok(window.mermaid); };
      s.onerror = () => no(new Error("mermaid failed to load")); document.head.appendChild(s);
    }));
  }
  function renderMermaid(k, root) {
    const codes = $$("pre > code.language-mermaid", root); if (!codes.length) return;
    ensureMermaid().then(m => codes.forEach((code, i) => {
      const src = code.textContent, holder = document.createElement("div"), gid = "mmd" + Date.now() + i;
      holder.className = "mermaid"; holder.dataset.src = src; code.parentNode.replaceWith(holder);
      // mermaid leaves its measuring node (#d<gid>/#i<gid>) on <body> when a diagram fails to parse
      const drop = () => ["d" + gid, "i" + gid].forEach(id => { const el = document.getElementById(id); if (el && el.parentNode === document.body) el.remove(); });
      m.render(gid, src).then(r => { holder.innerHTML = r.svg; drop(); V.emit("content", k); })
        .catch(e => { holder.innerHTML = `<pre class="merr">mermaid: ${esc(e.message)}</pre>`; drop(); });
    })).catch(() => {});
  }
  function markDoc(k, md, loc) {
    $$("h1,h2,h3,h4,h5,h6,li", md).forEach(el => { const x = SV.xidHead(el.textContent); if (x && !md.querySelector(`[data-xid="${x.id}"]`)) el.dataset.xid = x.id; });
    $$("h1,h2,h3,h4", md).forEach((h, i) => {
      h.id = k + "-h" + i;
      if (h.tagName !== "H1") h.insertAdjacentHTML("afterbegin", `<button class="anc" data-anc data-tip="复制这一节的链接" aria-label="复制链接">#</button>`);
    });
    $$("a[href]", md).forEach(a => {
      const raw = a.getAttribute("href"), key = SV.resolveLink(raw, loc.tree, loc.rel, V.D.sets);
      if (key) { const i = key.indexOf(":"); a.dataset.tree = key.slice(0, i); a.dataset.rel = key.slice(i + 1); a.removeAttribute("href"); a.tabIndex = 0; a.setAttribute("role", "link"); }
      else if (/^https?:\/\//i.test(raw)) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
      else if (raw.charAt(0) === "#") { a.dataset.hash = raw.slice(1); a.removeAttribute("href"); }
      else { a.classList.add("broken"); a.removeAttribute("href"); a.dataset.tip = "找不到这个链接的目标：" + raw; }
    });
  }
  // one source line number per top-level block, in the left margin; a span/block mismatch means no numbers, not wrong ones
  function lineNumbers(k) {
    const p = P[k], md = $(".md", p.body); if (!md || !p.doc || p.doc.src) return;
    $$(".lnum", md).forEach(x => x.remove());
    const els = blocks(k), spans = SV.blockSpans(window.marked.lexer(p.doc.body));
    if (spans.length !== els.length) return;
    const nums = SV.blockLineNumbers(spans, p.doc.fmLines), mr = md.getBoundingClientRect();
    p.spans = spans;
    els.forEach((b, i) => {
      const w = document.createTreeWalker(b, NodeFilter.SHOW_TEXT); let n, line = null;
      while (!line && (n = w.nextNode())) { if (!n.data.trim()) continue; const r = document.createRange(); r.setStart(n, 0); r.setEnd(n, 1); line = r.getClientRects()[0]; }
      const top = (line ? line.top + line.height / 2 - 5 : b.getBoundingClientRect().top + 4) - mr.top;
      md.insertAdjacentHTML("beforeend", `<span class="lnum" style="top:${top}px">${nums[i]}</span>`);
    });
  }
  function fmLine(f) {
    const keys = Object.keys(f); if (!keys.length) return "";
    const g = x => (f[x] || "").split("#")[0].trim(), bits = [g("status"), g("governance"), g("created"), g("go") && "go " + g("go")].filter(Boolean);
    return `<div class="fml">${bits.map(b => `<span>${esc(b)}</span>`).join("")}<button data-fmx aria-expanded="false">${keys.length} 项</button></div><div class="fmt" hidden>${keys.map(x => `<b>${esc(x)}</b><span>${esc(f[x])}</span>`).join("")}</div>`;
  }
  function crumb(k, loc) {
    const s = loc.rel.split("/"), pre = loc.tree === "kb" ? "知识库 / " : "";
    $(".ppath", P[k].el).innerHTML = `<bdi>${esc(pre + s.slice(0, -1).join(" / "))} / <b>${esc(s[s.length - 1])}</b>${P[k].chg ? " @ " + esc(P[k].chg.slice(0, 7)) : ""}</bdi>`;
  }
  // scroll writers in priority order: an explicit target, then (entering only) the remembered place, else stay put
  function place(k, loc, opt, keepTop) {
    const p = P[k], b = p.body;
    if (!opt.entering) { b.scrollTop = keepTop; return; }
    let el = null;
    if (loc.xid) el = $(`[data-xid="${V.cssEsc(loc.xid)}"]`, b) || null;
    if (!el && loc.hash) el = $(`#${V.cssEsc(loc.hash)}`, b) || $$("h1,h2,h3,h4", b).find(h => slug(h.textContent) === loc.hash) || null;
    if (!el && loc.line && p.spans) {
      const i = p.spans.findIndex(s => loc.line - 1 - p.doc.fmLines <= s.end); el = blocks(k)[i >= 0 ? i : p.spans.length - 1] || null;
    }
    if (el) { b.scrollTop = el.offsetTop - HEAD_PAD; flash(el); curLine(k, el, null); }
    else if (loc.xid) V.toast("没找到 " + loc.xid + " 的定义");
    else if (!restorePlace(k)) b.scrollTop = 0;
  }
  const slug = t => t.replace(/^#/, "").trim().toLowerCase().replace(/[^\w一-鿿]+/g, "-").replace(/^-+|-+$/g, "");
  function paint(k, loc, opt, text, mtime) {
    const p = P[k], keepTop = p.body.scrollTop, src = !/\.md$/i.test(loc.rel);
    const fm = src ? { fields: {}, body: text } : SV.parseFrontmatter(text);
    p.doc = { text, body: fm.body, fields: fm.fields, mtime, src, fmLines: text.split("\n").length - fm.body.split("\n").length };
    p.el.classList.remove("blank"); $(".stale", p.el).classList.remove("on");
    p.body.innerHTML = `<article class="md${src ? " src" : ""}${opt.entering && !V.RM ? " enter" : ""}">${src ? `<pre><code>${esc(text)}</code></pre>` : fmLine(fm.fields) + window.marked.parse(fm.body)}</article>`;
    const md = $(".md", p.body);
    if (!src) { markDoc(k, md, loc); renderMermaid(k, md); }
    applyMeasure(k); crumb(k, loc); lineNumbers(k);
    place(k, loc, opt, keepTop);
    p.chars = (md.textContent || "").replace(/\s/g, "").length;
    paintStar(k); V.emit("rendered", k, opt.entering);
    if (k === V.focus) toc();
    V.status();
  }
  function fail(k, loc, e) {
    const p = P[k]; p.doc = { err: true }; p.el.classList.remove("blank"); crumb(k, loc);
    p.body.innerHTML = `<div class="derr">${e.status === 404 ? "<b>这个文件不存在或已被移动。</b>" : "<b>打不开这篇文档。</b><br>" + esc(e.message)}<br><span class="hint" style="padding:0">${esc(loc.tree + "/" + loc.rel)}</span></div>`;
    V.emit("rendered", k, true); if (k === V.focus) toc(); V.status();
  }
  V.views.doc = (k, loc, opt) => {
    const p = P[k]; p.chg = null; $(".chgbar", p.el).hidden = true;
    if (opt.entering) { p.cur = null; $$(".curline,.lastmark", p.body).forEach(x => x.remove()); }
    let mt = 0;
    V.api("/raw/" + loc.tree + "/" + loc.rel).then(r => { mt = +r.headers.get("X-Mtime") || 0; return r.text(); })
      .then(t => { if (p.loc === loc && !p.chg) paint(k, loc, opt, t, mt); }).catch(e => { if (p.loc === loc) fail(k, loc, e); });
  };

  /* ---- reading width: default / wide / full per pane, or a dragged width ---- */
  const MEAS = Object.assign({ A: { mode: "default" }, B: { mode: "default" } }, store.get("measure", {}));
  function applyMeasure(k) {
    const md = $(".md", P[k].body); if (!md || md.classList.contains("src")) return;
    const m = MEAS[k], w = m.mode === "custom" ? m.w + "px" : m.mode === "wide" ? "1100px" : m.mode === "full" ? "none" : "820px";
    md.style.setProperty("--measure", w);
    let r = $(".mrule", md); if (!r) { md.insertAdjacentHTML("beforeend", '<i class="mrule" data-tip="拖动调整阅读宽度"></i>'); r = $(".mrule", md); }
    r.style.left = "calc(100% - 4px)";
    $('[data-t="width"]', P[k].el).dataset.tip = "阅读宽度：" + { default: "默认", wide: "宽", full: "铺满", custom: "自定 " + m.w + "px" }[m.mode] + "（点击切换）";
  }
  document.addEventListener("pointerdown", e => {
    const r = e.target.closest(".mrule"); if (!r) return;
    e.preventDefault(); const k = V.paneOf(r), md = r.parentElement, x0 = e.clientX, w0 = md.getBoundingClientRect().width;
    const max = P[k].body.clientWidth; r.classList.add("drag"); r.setPointerCapture(e.pointerId);
    const move = ev => { MEAS[k] = { mode: "custom", w: Math.round(Math.max(360, Math.min(max, w0 + (ev.clientX - x0) * 2))) }; applyMeasure(k); };
    const up = () => { r.classList.remove("drag"); r.removeEventListener("pointermove", move); store.set("measure", MEAS); lineNumbers(k); V.emit("content", k); };
    r.addEventListener("pointermove", move); r.addEventListener("pointerup", up, { once: true });
  });
  V.click('[data-t="width"]', el => {
    const k = V.paneOf(el), order = ["default", "wide", "full"], m = MEAS[k];
    MEAS[k] = { mode: order[(order.indexOf(m.mode) + 1) % 3] }; store.set("measure", MEAS); applyMeasure(k); lineNumbers(k); V.emit("content", k);
  });

  /* ---- current line, last-read mark, flash ---- */
  function curLine(k, blk, clientY) {
    const b = P[k].body, md = $(".md", b); if (!blk || !md || !b.contains(blk)) return;
    let ov = $(".curline", md); if (!ov) { ov = document.createElement("div"); ov.className = "curline"; md.appendChild(ov); }
    const row = blk.closest("tr"), mr = md.getBoundingClientRect(), cs = getComputedStyle(md);
    let rect;
    if (row) rect = row.getBoundingClientRect();
    else { const rg = document.createRange(); rg.selectNodeContents(blk); rect = SV.pickLineRect([...rg.getClientRects()].filter(r => r.width > 1 && r.height > 1), clientY) || blk.getBoundingClientRect(); }
    const padL = parseFloat(cs.paddingLeft), padR = parseFloat(cs.paddingRight);
    ov.style.top = (rect.top - mr.top - 1) + "px"; ov.style.height = (rect.height + 2) + "px";
    ov.style.left = (padL - 8) + "px"; ov.style.width = (mr.width - padL - padR + 16) + "px";
    P[k].cur = { blk, off: clientY == null ? null : clientY - blk.getBoundingClientRect().top };
  }
  function recur(k) { const c = P[k].cur; if (c && c.blk.isConnected) curLine(k, c.blk, c.off == null ? null : c.blk.getBoundingClientRect().top + c.off); }
  function lastMark(k) {
    if (V.RM) return; const b = P[k].body, md = $(".md", b); if (!md) return;
    $$(".lastmark", md).forEach(x => x.remove());
    const best = blocks(k)[topBlock(k)], m = document.createElement("div");
    m.className = "lastmark"; m.style.top = (best ? best.offsetTop : b.scrollTop) + 11 + "px"; md.appendChild(m);
    const evs = ["wheel", "touchmove", "keydown"], drop = e => {
      if (e.type === "keydown" && !/^(Arrow|Page|Home|End| )/.test(e.key)) return;
      evs.forEach(t => (t === "keydown" ? document : b).removeEventListener(t, drop)); m.classList.add("out"); setTimeout(() => m.remove(), 450);
    };
    evs.forEach(t => (t === "keydown" ? document : b).addEventListener(t, drop, { passive: true }));
  }
  function flash(el) { if (V.RM) return; el.classList.remove("hl"); void el.offsetWidth; el.classList.add("hl"); }
  V.on("layout", () => setTimeout(() => ["A", "B"].forEach(k => { if (P[k].doc && !P[k].doc.err) { applyMeasure(k); lineNumbers(k); recur(k); V.emit("content", k); } }), 60));
  V.on("content", k => recur(k));

  /* ---- toc + rail of ticks + the section chip ---- */
  let heads = [];
  const headLabel = h => {
    let t = h.textContent.replace(/^#/, "").trim(), ok = false, inf = false;
    t = t.replace(/^((?:Req|Inv|V|Q|Task)-\d+)\s+(已验证|待验证|已放弃|放弃|提议|待确认|已确认|进行中|已定|待做)\s*[—-]?\s*/, (_, a, s) => { ok = s === "已验证"; return a + " "; });
    t = t.replace(/\s*\[VERIFIED\]/, () => { ok = true; return ""; }).replace(/\s*\[(推断|INFERRED)\]/, () => { inf = true; return ""; });
    return { t, ok, inf };
  };
  function toc() {
    $("#sideT").textContent = $("#sideS").textContent = "目录";
    if (V.view !== "doc") return;
    const p = P[V.focus];
    if (!p.doc || p.doc.err) { $("#sbody").innerHTML = '<div class="hint">这一栏空着</div>'; $("#sticks").innerHTML = ""; heads = []; return; }
    heads = $$(".md h1, .md h2, .md h3", p.body);
    $("#sbody").innerHTML = `<div class="toc">${heads.map((h, i) => { const x = headLabel(h); return `<button class="ti" data-ti="${i}" style="--d:${+h.tagName[1] - 1}" data-tip="${esc(x.t)}"><span class="ck2">${x.ok ? V.I.tick : x.inf ? "<em>推</em>" : ""}</span><span class="tl">${esc(x.t)}</span></button>`; }).join("") || '<div class="hint">这篇没有标题</div>'}</div>`;
    const hh = Math.max(6, Math.min(16, Math.floor(($("#side").clientHeight - 70) / Math.max(1, heads.length)))), tw = h => ({ 1: 14, 2: 10 }[h.tagName[1]] || 6);
    $("#sticks").style.setProperty("--mw", Math.max(6, ...heads.map(tw)) + "px");
    $("#sticks").innerHTML = heads.map((h, i) => { const x = headLabel(h); return `<button class="stk ${x.ok ? "ok" : ""}" data-ti="${i}" data-tip="${esc(x.t)}" style="--h:${hh}px;--w:${tw(h)}px" aria-label="${esc(x.t)}"><i></i></button>`; }).join("");
    spy();
  }
  function spy() {
    if (V.view !== "doc") return;
    const p = P[V.focus], top = p.body.scrollTop + 40; let c = -1;
    heads.forEach((h, i) => { if (h.offsetTop <= top) c = i; });
    $$("#sbody .ti").forEach((b, i) => b.classList.toggle("cur", i === c)); $$("#sticks .stk").forEach((b, i) => b.classList.toggle("cur", i === c));
    const cb = $("#sbody .ti.cur"), sb = $("#sbody");
    if (cb && (cb.offsetTop < sb.scrollTop + 10 || cb.offsetTop > sb.scrollTop + sb.clientHeight - 30)) sb.scrollTop = cb.offsetTop - sb.clientHeight / 3;
    ["A", "B"].forEach(k => {
      const chip = $(".secchip", P[k].el), on = V.isNarrow() && k === V.focus && c >= 0 && !!heads[c];
      chip.classList.toggle("on", on); if (on) $("span", chip).textContent = headLabel(heads[c]).t;
    });
  }
  const sr = {};
  function onScroll(k) {
    if (sr[k]) return;
    sr[k] = requestAnimationFrame(() => { sr[k] = 0; if (k === V.focus) { spy(); V.status(); } clearTimeout(sr["t" + k]); sr["t" + k] = setTimeout(() => savePlace(k), 400); });
  }
  V.on("focus", () => { if (V.view === "doc") toc(); });
  V.on("nav", (k, loc) => { if (loc.kind !== "doc") $$(".secchip").forEach(c => c.classList.remove("on")); });
  V.click("[data-ti]", el => {
    V.app.classList.remove("tocpop"); const h = heads[+el.dataset.ti], b = P[V.focus].body; if (!h) return;
    b.scrollTo({ top: h.offsetTop - HEAD_PAD, behavior: V.RM ? "auto" : "smooth" }); flash(h); curLine(V.focus, h, null);
  });
  V.click('[data-t="toc"],[data-sec]', () => V.app.classList.toggle("tocpop"));

  /* ---- citations: jump in place, else open the defining file beside this one, with a connecting line ---- */
  const factCache = {};
  function factOf(rel, id) {   // the "### Fact-n" block of a card's facts.md, fetched once per file version
    const mt = V.D.mtime.dev[rel], c = factCache[rel];
    if (c && c.mt === mt) return Promise.resolve(c.find(id));
    return V.api("/raw/dev/" + rel).then(r => r.text()).then(src => {
      const map = {}; src.replace(/^### (Fact-\d+)[^\n]*\n([\s\S]*?)(?=^### |(?![\s\S]))/gm, (all, n) => { map[n] = all; });
      factCache[rel] = { mt, find: n => map[n] || null }; return map[id] || null;
    }).catch(() => null);
  }
  let tipT = null, tipFor = null;
  const hideTip = () => { clearTimeout(tipT); tipFor = null; $("#tip").classList.remove("on", "wide"); };
  V.on("tip-hide", hideTip);
  function placeTip(anchor) {
    const t = $("#tip"), r = anchor.getBoundingClientRect(), w = t.offsetWidth, h = t.offsetHeight;
    t.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left - 20)) + "px";
    t.style.top = (r.bottom + h + 12 > innerHeight ? Math.max(8, r.top - h - 8) : r.bottom + 6) + "px";
  }
  const inline = s => window.marked.parseInline(s.length > 260 ? s.slice(0, 260) + "…" : s);
  function showCite(ce) {
    const k = V.paneOf(ce), loc = P[k].loc, id = ce.dataset.ref; if (!loc) return;
    tipFor = ce; const t = $("#tip");
    const local = $(`[data-xid="${V.cssEsc(id)}"]`, P[k].body);
    if (local) { t.innerHTML = `<div class="h"><b>${esc(id)}</b><span style="margin-left:auto">本文</span></div><p>${esc(local.textContent.replace(/^#/, "").trim().slice(0, 140))}</p>`; t.classList.add("on"); placeTip(ce); return; }
    const home = SV.xidHomeRel(loc.rel, id); if (!home || loc.tree !== "dev") return;
    factOf(home, id).then(md => {
      if (tipFor !== ce || !md) return;
      const head = md.split("\n")[0].replace("### ", ""), body = md.replace(/^### [^\n]*\n/, "");
      const grab = key => { const m = body.match(new RegExp(`^- ${key}[:：]\\s*([\\s\\S]*?)(?=\\n- [^\\n]{1,8}[:：]|$)`, "m")); return m ? m[1].replace(/\s+/g, " ").trim() : ""; };
      const fact = grab("事实") || body.replace(/\s+/g, " ").trim(), src = grab("来源");
      const para = (ce.closest("p,li,td") || ce.parentElement).textContent.replace(/\s+/g, " "), at = para.indexOf("[" + id);
      let pre = at < 0 ? "" : para.slice(0, at); const cut = Math.max(...["。", "；", ";", "？", "！"].map(x => pre.lastIndexOf(x)));
      pre = pre.slice(cut + 1).replace(/\[[A-Za-z]+-\d+[^\]]*\]/g, "").replace(/\s+/g, " ").trim();
      t.innerHTML = `<div class="h"><b>${esc(head.split(" ")[0])}</b>${/VERIFIED/.test(head) ? '<span style="color:var(--done)">VERIFIED</span>' : ""}<span style="margin-left:auto">facts.md</span></div>${pre ? `<div class="l1">${esc(pre.length > 60 ? "…" + pre.slice(-60) : pre)}<mark>[${esc(id)}]</mark></div>` : ""}<div class="l2">${inline(fact)}</div>${src ? `<div class="l3">${inline(src)}</div>` : ""}`;
      t.classList.add("on"); placeTip(ce);
    });
  }
  function follow(ce, e) {
    hideTip(); const k = V.paneOf(ce), loc = P[k].loc, id = ce.dataset.ref; if (!loc) return;
    const local = $(`[data-xid="${V.cssEsc(id)}"]`, P[k].body);
    if (local && !e.shiftKey) { const b = P[k].body; b.scrollTo({ top: local.offsetTop - HEAD_PAD, behavior: V.RM ? "auto" : "smooth" }); flash(local); curLine(k, local, null); return; }
    const home = local ? loc.rel : SV.xidHomeRel(loc.rel, id), canon = home && V.D.sets[loc.tree].get(home.toLowerCase());
    if (!canon) { V.toast(`没找到 ${id} 的定义`); return; }
    const o = V.isNarrow() ? k : k === "A" ? "B" : "A";
    if (P[o].loc && P[o].loc.kind === "doc" && P[o].loc.rel === canon && P[o].doc) {
      const el = $(`[data-xid="${V.cssEsc(id)}"]`, P[o].body); if (el) { P[o].body.scrollTop = el.offsetTop - HEAD_PAD; flash(el); curLine(o, el, null); }
    } else V.nav(o, { kind: "doc", tree: loc.tree, rel: canon, xid: id });
    if (V.isNarrow()) return;
    V.setFocus(k);
    const wait = (n) => { const el = P[o].doc && $(`[data-xid="${V.cssEsc(id)}"]`, P[o].body); if (el) link(ce, el); else if (n) setTimeout(() => wait(n - 1), 120); };
    wait(15);
  }
  let linkRAF = 0;
  function link(a, b) {
    if (V.RM) return; cancelAnimationFrame(linkRAF); $$(".cite.on").forEach(x => x.classList.remove("on")); a.classList.add("on");
    const svg = $("#link"), t0 = performance.now();
    const step = now => {
      const t = now - t0, ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect(), ltr = ra.left < rb.left;
      const x1 = ltr ? ra.right + 2 : ra.left - 2, y1 = ra.top + ra.height / 2, x2 = ltr ? rb.left - 4 : rb.right + 4, y2 = rb.top + 11, mx = Math.round((x1 + x2) / 2) + .5;
      const grow = Math.min(1, t / 420), op = t < 2300 ? 1 : Math.max(0, 1 - (t - 2300) / 700);
      svg.innerHTML = `<path d="M${x1},${y1} H${mx} V${y2} H${x2}" pathLength="1" style="stroke-dasharray:1;stroke-dashoffset:${1 - grow};opacity:${op * .9}"/><circle cx="${x1}" cy="${y1}" r="2.3" style="opacity:${op}"/><circle cx="${x2}" cy="${y2}" r="2.6" style="opacity:${op * grow}"/>`;
      if (op > 0) linkRAF = requestAnimationFrame(step); else { svg.innerHTML = ""; a.classList.remove("on"); }
    };
    linkRAF = requestAnimationFrame(step);
  }

  /* ---- internal link preview: the target doc rendered in a hovercard ---- */
  const lpCache = {};
  function showPreview(a) {
    const tree = a.dataset.tree, rel = a.dataset.rel, key = tree + ":" + rel, mt = V.D.mtime[tree][rel]; tipFor = a;
    const draw = html => { if (tipFor !== a) return; const t = $("#tip"); t.innerHTML = `<div class="h"><b>${esc(rel.split("/").pop())}</b><span style="margin-left:auto">${esc(tree === "kb" ? "知识库" : rel.split("/").slice(0, 2).join("/"))}</span></div><div class="md">${html}</div>`; t.classList.add("on", "wide"); placeTip(a); };
    if (lpCache[key] && lpCache[key].mt === mt) return draw(lpCache[key].html);
    V.api("/raw/" + tree + "/" + rel).then(r => r.text()).then(text => {
      const html = window.marked.parse(SV.parseFrontmatter(text).body.slice(0, 4000)); lpCache[key] = { mt, html }; draw(html);
    }).catch(() => draw('<p class="hint">预览不了这篇文档</p>'));
  }
  document.addEventListener("mouseover", e => {
    const ce = e.target.closest(".pbody .cite[data-ref]"), a = !V.isNarrow() && e.target.closest(".pbody .md a[data-rel]");
    if (ce && ce !== tipFor) { clearTimeout(tipT); tipT = setTimeout(() => showCite(ce), 180); }
    else if (a && a !== tipFor) { clearTimeout(tipT); tipT = setTimeout(() => showPreview(a), 250); }
  });
  document.addEventListener("mouseout", e => { if (e.target.closest(".pbody .cite[data-ref], .pbody .md a[data-rel]") && !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest(".cite,.md a[data-rel]"))) hideTip(); });
  addEventListener("scroll", e => { if (!$("#tip").contains(e.target) && $("#tip").classList.contains("on")) hideTip(); }, true);

  /* ---- change history and the change view: a commit's after-version with its added/removed blocks ---- */
  function histPop(k, btn) {
    const loc = P[k].loc; if (!loc || loc.kind !== "doc") return;
    V.pop("histPop", `<div class="pt">${esc(loc.rel.split("/").pop())} 的变更历史</div><div class="qnone">读取中…</div>`, btn, "right");
    V.json("/api/filelog?path=" + encodeURIComponent(loc.tree + "/" + loc.rel)).then(d => {
      const cs = d.commits || [];
      if (!V.isPop("histPop")) return;
      $("#histPop").innerHTML = `<div class="pt">${esc(loc.rel.split("/").pop())} 的变更历史</div>` + (P[k].chg ? `<button class="hi first last" data-chg="" data-pane="${k}"><i class="dt"></i><span class="hmsg">回到当前版本</span><span class="hmeta"></span></button>` : "")
        + (cs.length ? cs.map((c, i) => `<button class="hi ${i === 0 && !P[k].chg ? "first" : ""} ${i === cs.length - 1 ? "last" : ""} ${P[k].chg === c.sha ? "li cur" : ""}" data-chg="${esc(c.sha)}" data-pane="${k}" data-tip="${esc(c.sha.slice(0, 7) + " · " + c.date + " · " + c.subject)}"><i class="dt"></i><span class="hmsg">${esc(c.subject)}</span><span class="hmeta">${esc(c.sha.slice(0, 7))}　${esc(String(c.date).slice(5, 16))}</span></button>`).join("") : '<div class="qnone">没有记录到提交</div>');
    }).catch(() => { $("#histPop").innerHTML = '<div class="qnone">历史读取失败</div>'; });
  }
  function changeView(k, sha) {
    const p = P[k], loc = p.loc;
    if (!sha) { p.chg = null; $(".chgbar", p.el).hidden = true; return V.views.doc(k, loc, { entering: false }); }
    V.json("/api/filediff?path=" + encodeURIComponent(loc.tree + "/" + loc.rel) + "&sha=" + encodeURIComponent(sha)).then(d => {
      p.chg = sha; const fm = SV.parseFrontmatter(d.after || ""), body = fm.body, fmLines = (d.after || "").split("\n").length - body.split("\n").length;
      const spans = SV.blockSpans(window.marked.lexer(body)), tmp = document.createElement("div"); tmp.innerHTML = window.marked.parse(body);
      const els = [...tmp.children], use = spans.length === els.length ? spans : els.map((_, i) => spans[i] || { start: 0, end: 0 });
      const segs = SV.diffSegments(use, (d.adds || []).map(x => x - 1 - fmLines), (d.dels || []).map(g => ({ at: g.at - 1 - fmLines, lines: g.lines })));
      const md = document.createElement("article"); md.className = "md";
      segs.forEach(s => {
        if (s.del) { const g = document.createElement("div"); g.className = "chg-del"; g.textContent = s.del.join("\n"); md.appendChild(g); return; }
        for (let i = s.from; i <= s.to; i++) if (els[i]) { if (s.add) els[i].classList.add("chg-add"); md.appendChild(els[i]); }
      });
      const top = p.body.scrollTop; p.body.innerHTML = ""; p.body.appendChild(md); markDoc(k, md, loc); renderMermaid(k, md); applyMeasure(k); p.body.scrollTop = top;
      const bar = $(".chgbar", p.el); bar.hidden = false;
      bar.innerHTML = `<span>变更 <code>${esc(sha.slice(0, 7))}</code>：这次提交后的版本，新增与删除已标出（只读）</span><button data-chg="" data-pane="${k}">退出变更视图</button>`;
      crumb(k, loc); V.emit("rendered", k, false); if (k === V.focus) toc();
    }).catch(() => V.toast("这次提交的改动读不出来"));
  }

  /* ---- clicks, keys, status ---- */
  function paintStar(k) {
    const b = $('[data-t="star"]', P[k].el), loc = P[k].loc, on = !!(loc && loc.kind === "doc" && V.isStar(keyOf(loc)));
    b.classList.toggle("star-on", on); b.dataset.tip = on ? "取消星标" : "加星标";
  }
  V.on("stars", () => ["A", "B"].forEach(paintStar));
  V.click(".cite[data-ref]", (el, e) => follow(el, e));
  V.click(".md a[data-rel]", (el, e) => { hideTip(); const k = V.paneOf(el), o = k === "A" ? "B" : "A"; V.nav(e.shiftKey ? o : k, { kind: "doc", tree: el.dataset.tree, rel: el.dataset.rel }); });
  V.click(".md a[data-hash]", el => { const k = V.paneOf(el), h = $$("h1,h2,h3,h4", P[k].body).find(x => x.id === el.dataset.hash || slug(x.textContent) === el.dataset.hash); if (h) { P[k].body.scrollTo({ top: h.offsetTop - HEAD_PAD, behavior: "smooth" }); flash(h); } });
  V.click(".md a.broken", () => V.toast("这个链接的目标在 dev_root 和知识库里都找不到"));
  V.click("[data-anc]", el => { const k = V.paneOf(el), loc = P[k].loc, h = el.parentElement; V.copy(`${loc.rel.split("/").slice(-2).join("/")}#${slug(h.textContent)}`, `已复制 ${loc.rel.split("/").pop()}#${slug(h.textContent)}`); });
  V.click("[data-fmx]", el => { const tb = el.parentElement.nextElementSibling, open = tb.hidden; tb.hidden = !open; el.setAttribute("aria-expanded", open); V.emit("content", V.paneOf(el)); });
  V.click("[data-stale]", el => { const k = V.paneOf(el); $(".stale", P[k].el).classList.remove("on"); V.rerender(k); });
  V.click("[data-chg]", el => { V.closePops(); changeView(el.dataset.pane, el.dataset.chg); });
  V.click('.phd [data-t="star"]', el => { const loc = P[V.paneOf(el)].loc; if (loc && loc.kind === "doc") V.toggleStar(keyOf(loc), el); });
  V.click('.phd [data-t="hist"]', el => (V.isPop("histPop") ? V.closePops() : histPop(V.paneOf(el), el)));
  V.click('.phd [data-t="split"]', () => {
    if (V.isSplit()) return V.setSplit(false);
    V.setSplit(true);
    const a = P.A.loc; if (P.B.loc || !a || a.kind !== "doc") return;
    const c = V.cardOfPath(a.tree, a.rel), f = c && c.dir + "/facts.md";
    V.nav("B", { kind: "doc", tree: "dev", rel: f && V.D.sets.dev.get(f.toLowerCase()) && f !== a.rel ? f : a.rel }); V.setFocus("A");
  });
  V.click('.phd [data-t="close"]', () => V.setSplit(false));
  V.hotkey("s", () => { if (V.view !== "doc") return false; const k = V.focus, loc = P[k].loc; V.toggleStar(keyOf(loc), $('[data-t="star"]', P[k].el)); });
  V.hotkey("\\", () => { if (V.view !== "doc") return false; $('#pA [data-t="split"]').click(); });
  V.on("split", on => { if (!on && V.view === "doc") toc(); if (on && !P.B.loc) { P.B.el.classList.add("blank"); P.B.body.innerHTML = BLANK_B; } });
  V.on("theme", () => {
    if (window.mermaid) window.mermaid.initialize({ startOnLoad: false, theme: V.isDark() ? "dark" : "default" });
    ["A", "B"].forEach(k => { if (V.view === "doc" && P[k].doc && $(".mermaid", P[k].body)) V.rerender(k); });
  });
  V.on("tick", () => ["A", "B"].forEach(k => {
    const p = P[k], loc = p.loc; if (V.view !== "doc" || !loc || loc.kind !== "doc" || !p.doc || p.doc.err || (k === "B" && !V.isSplit())) return;
    V.json("/api/rev?path=" + encodeURIComponent(loc.tree + "/" + loc.rel)).then(d => { if (d.mtime && d.mtime > p.doc.mtime + 1e-3 && p.loc === loc) $(".stale", p.el).classList.add("on"); }).catch(() => {});
  }));
  V.statusFns.doc = () => {
    const p = P[V.focus]; if (!p.loc || p.loc.kind !== "doc") return "";
    const b = p.body, max = b.scrollHeight - b.clientHeight, pct = max > 0 ? Math.round(b.scrollTop / max * 100) : 100, mins = Math.max(1, Math.round((p.chars || 0) / 500));
    const find = $(".find.on", p.el);
    return `<span><b>${esc(p.loc.rel.split("/").pop())}</b>${V.isSplit() ? `　${V.focus} 栏` : ""}</span><span>${((p.chars || 0) / 1000).toFixed(1)}k 字，约 ${mins} 分钟</span><span>${pct}%<span class="prog"><i style="width:${pct}%"></i></span></span><span class="sp"></span><span>${find ? "↵ 下一个 · ⇧↵ 上一个 · esc 关闭" : "f 查找 · h 钉词 · [ ] 后退前进 · \\ 对照"}</span>${V.stamp()}`;
  };
  V.readerOf = k => ({ body: P[k].body, md: $(".md", P[k].body), doc: P[k].doc });
})(V2);
