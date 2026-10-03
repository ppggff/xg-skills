/* status viewer v2 — find in page: the find bar, CSS Custom Highlights named per pane (the DOM is never
   rewritten), a clickable rail of hit marks, pinned terms in four colours remembered per view, find
   history, the selection echo and the floating selection bar. State keeps only terms and offsets, never
   a Range: a Range does not survive a re-render. */
"use strict";
(function (V) {
  const { $, $$, esc, store, P } = V;
  const DEBOUNCE = 160;
  const H = { A: fresh(), B: fresh() };
  function fresh() { return { q: "", hits: [], cur: -1, idx: null, pins: [], slots: [false, false, false, false], open: false, t: 0, histAt: -1 }; }
  const HL = window.CSS && CSS.highlights;
  const names = k => ["hit-" + k, "hitc-" + k, "echo-" + k, "p0-" + k, "p1-" + k, "p2-" + k, "p3-" + k];

  /* ---- the index: the pane's readable text, whitespace folded, with a run table back to text nodes ---- */
  const SKIP = ".anc,.lnum,.mrule,.curline,.lastmark,style,script";
  function buildIndex(k) {
    const md = $(".md", P[k].body); if (!md) return null;
    const shells = [], w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT, { acceptNode: n => (n.parentElement.closest(SKIP) ? 2 : 1) });
    let n;
    while ((n = w.nextNode())) {
      let off = 0;
      (n.data.match(/\S+|\s+/g) || []).forEach(seg => {
        const sp = /^\s/.test(seg);
        shells.push({ node: n, off, len: seg.length, isSpace: sp, text: sp ? "" : seg }); off += seg.length;
      });
    }
    return SV.buildIndexText(shells);
  }
  function rangeOf(idx, s, e) {
    const a = SV.offsetToNode(idx.runs, s), b = SV.offsetToNode(idx.runs, e); if (!a || !b) return null;
    const r = document.createRange(); r.setStart(a.node, a.nodeOff); r.setEnd(b.node, b.nodeOff); return r;
  }
  const rectOf = (idx, x) => { const r = rangeOf(idx, x[0], x[1]); return r && r.getClientRects()[0]; };
  function highlight(idx, hits, priority) {
    const hl = new Highlight(); hits.forEach(x => { const r = rangeOf(idx, x[0], x[1]); if (r) hl.add(r); });
    hl.priority = priority; return hl;
  }

  /* ---- paint: highlights + the rail; the current hit outranks pins ---- */
  function paint(k) {
    const h = H[k];
    if (HL) {
      names(k).forEach(nm => { if (!/^echo/.test(nm)) CSS.highlights.delete(nm); });
      if (h.idx) {
        const all = highlight(h.idx, h.hits.filter((x, i) => i !== h.cur), 100), cur = highlight(h.idx, h.hits.filter((x, i) => i === h.cur), 200);
        if (all.size) CSS.highlights.set("hit-" + k, all);
        if (cur.size) CSS.highlights.set("hitc-" + k, cur);
        const by = {};   // past four pins two terms share a colour: one highlight per colour, not per term
        h.pins.forEach((pn, i) => { (by[pn.slot] = by[pn.slot] || []).push(...SV.scanHits(h.idx.text, pn.term)); by[pn.slot].pri = i; });
        Object.keys(by).forEach(s => { const hl = highlight(h.idx, by[s], by[s].pri); if (hl.size) CSS.highlights.set(`p${s}-${k}`, hl); });
      }
    }
    rail(k); count(k);
  }
  function rail(k) {
    const h = H[k], r = $(".frail", P[k].el), b = P[k].body; if (!r) return;
    if (!h.idx || (!h.hits.length && !h.pins.length) || !b.scrollHeight) { r.innerHTML = ""; r.classList.remove("on"); return; }
    r.style.top = $(".phd", P[k].el).offsetHeight + 2 + "px";
    const th = r.clientHeight, br = b.getBoundingClientRect(), seen = new Set(); let html = "";
    const mark = (x, cls, i) => {
      const rc = rectOf(h.idx, x); if (!rc) return;
      const y = Math.round(SV.railTop(rc.top + b.scrollTop, br.top, b.scrollHeight, th - 3));
      if (cls !== "c" && seen.has(cls + y)) return;
      seen.add(cls + y);
      html += `<i class="${cls}" style="top:${y}px" data-s="${x[0]}" data-e="${x[1]}"${i != null ? ` data-hit="${i}"` : ""}></i>`;
    };
    h.pins.forEach(pn => SV.scanHits(h.idx.text, pn.term).forEach(x => mark(x, "p")));
    h.hits.forEach((x, i) => mark(x, i === h.cur ? "c" : "", i));
    r.innerHTML = html; r.classList.add("on");
  }
  function count(k) {
    const h = H[k], f = $(".find", P[k].el); if (!f.firstChild) return;
    odo(k, !h.q ? "" : h.hits.length ? `${h.cur + 1}/${h.hits.length}` : "无匹配");
    f.classList.toggle("nohit", !!h.q && !h.hits.length);
  }
  function odo(k, s) {   // the counter rolls its digits like an odometer
    const o = $(".odo", P[k].el); if (!o) return;
    const prev = o.dataset.v || ""; o.dataset.v = s;
    if (!s) { o.innerHTML = ""; return; }
    const a = s.padStart(prev.length, " "), b = prev.padStart(s.length, " ");
    o.innerHTML = [...a].map((ch, i) => {
      const was = b[i];
      if (V.RM || was === ch || !/\d/.test(ch) || !/\d/.test(was || "")) return `<span>${ch === " " ? "&nbsp;" : esc(ch)}</span>`;
      const up = +ch > +was;
      return `<span class="oc" style="transform:translateY(${up ? 0 : -15}px)" data-to="${up ? -15 : 0}"><span>${up ? was : ch}</span><span>${up ? ch : was}</span></span>`;
    }).join("");
    requestAnimationFrame(() => requestAnimationFrame(() => $$(".oc", o).forEach(c => { c.style.transform = `translateY(${c.dataset.to}px)`; })));
  }

  /* ---- find ---- */
  function find(k, q, still) {
    const h = H[k]; if (!h.idx) h.idx = buildIndex(k); if (!h.idx) return;
    h.q = (q || "").toLowerCase(); h.hits = h.q ? SV.scanHits(h.idx.text, h.q) : [];
    const top = P[k].body.getBoundingClientRect().top;
    h.cur = h.hits.length ? Math.max(0, h.hits.findIndex(x => { const rc = rectOf(h.idx, x); return rc && rc.top >= top; })) : -1;
    paint(k); if (!still) show(k, false);
  }
  function scrollToRect(k, rc) { const b = P[k].body; b.scrollTo({ top: b.scrollTop + rc.top - b.getBoundingClientRect().top - b.clientHeight * .35, behavior: V.RM ? "auto" : "smooth" }); }
  function show(k, force) {   // stepping through hits already on screen does not move the page
    const h = H[k], x = h.hits[h.cur]; if (!x) return;
    const rc = rectOf(h.idx, x); if (!rc) return;
    const br = P[k].body.getBoundingClientRect();
    if (!force && rc.top >= br.top + 50 && rc.bottom <= br.bottom - 30) return;
    scrollToRect(k, rc);
  }
  function step(k, dir) { const h = H[k]; if (!h.hits.length) return; h.cur = SV.stepHitIndex(h.cur, h.hits.length, dir); paint(k); show(k, true); }
  function bar(k) {
    const f = $(".find", P[k].el), h = H[k];
    const ib = (attr, tip, key, icon) => `<button class="ib" ${attr} data-tip="${tip}" data-key="${key}" aria-label="${tip}">${V.I[icon]}</button>`;
    const pins = h.pins.map((pn, i) => `<button class="fpin" data-c="${pn.slot}" data-unpin="${i}" data-tip="取消钉住「${esc(pn.term)}」">${esc(pn.term)}</button>`).join("");
    f.innerHTML = `<span class="fpins">${pins}</span><input placeholder="在本文查找" aria-label="在本文查找" autocomplete="off"><span class="odo"></span>`
      + ib("data-fpin", "钉住这个词：关掉查找后仍然高亮", "⌘↵", "pin") + ib('data-fnav="-1"', "上一个", "⇧↵", "up")
      + ib('data-fnav="1"', "下一个", "↵", "down") + ib("data-fclose", "关闭查找", "esc", "x");
    const inp = $("input", f); inp.value = h.q;
    inp.addEventListener("input", () => { h.histAt = -1; clearTimeout(h.t); h.t = setTimeout(() => find(k, inp.value), DEBOUNCE); });
    inp.addEventListener("keydown", e => {
      e.stopPropagation();
      if (e.key === "Enter") {
        e.preventDefault(); clearTimeout(h.t);   // act on what is in the box, not on the term the debounce has not applied yet
        if (h.q !== inp.value.toLowerCase()) find(k, inp.value);
        if (e.metaKey || e.ctrlKey) return pin(k, inp.value);
        V.recent.push("find", h.q, 20); step(k, e.shiftKey ? -1 : 1);
      } else if (e.key === "Escape") { e.preventDefault(); close(k); }
      else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
        e.preventDefault();
        const list = V.recent.list("find"); if (!list.length) return;
        h.histAt = Math.max(-1, Math.min(list.length - 1, h.histAt + (e.key === "ArrowUp" ? 1 : -1)));
        inp.value = h.histAt < 0 ? "" : list[h.histAt]; clearTimeout(h.t); find(k, inp.value); inp.select();
      }
    });
    count(k);
  }
  function open(k, seed, still) {
    if (V.view !== "doc" || !$(".md", P[k].body)) return;
    const h = H[k], f = $(".find", P[k].el);
    if (!h.open) { h.open = true; bar(k); f.classList.add("on"); $('[data-t="find"]', P[k].el).classList.add("on"); }
    const inp = $("input", f);
    if (seed) { inp.value = seed; clearTimeout(h.t); find(k, seed, still); }
    if (!still) { inp.focus(); inp.select(); }
    V.status();
  }
  function close(k) {
    const h = H[k]; clearTimeout(h.t); if (!h.open) return;
    V.recent.push("find", h.q, 20);
    Object.assign(h, { open: false, q: "", hits: [], cur: -1, histAt: -1 });
    const f = $(".find", P[k].el); f.classList.remove("on", "nohit"); $('[data-t="find"]', P[k].el).classList.remove("on");
    if (f.contains(document.activeElement)) document.activeElement.blur();
    remember(k); paint(k); V.status();
  }
  function selected(k) {   // a short single-line selection inside this pane, else nothing
    const s = window.getSelection(); if (!s || !s.rangeCount || !P[k].body.contains(s.anchorNode)) return "";
    const t = String(s).trim(); return t.length >= 2 && t.length <= 80 && !/\n/.test(t) ? t : "";
  }

  /* ---- pins: up to four colours (a fifth shares one), identity is the word ---- */
  function addPin(h, term) { const slot = SV.pinSlot(h.slots, h.pins.length); h.slots[slot] = true; h.pins.push({ term, slot }); }
  function pin(k, term) {
    const h = H[k], t = String(term || "").trim().toLowerCase(); if (t.length < 2 || /\n/.test(t)) return;
    const at = h.pins.findIndex(pn => pn.term === t);
    if (at >= 0) return unpin(k, at);
    if (!h.idx) h.idx = buildIndex(k);
    addPin(h, t); remember(k); paint(k); if (h.open) bar(k);
    V.toast(`已钉住「${t}」，关掉查找也会保留`);
  }
  function unpin(k, at) {
    const h = H[k], gone = h.pins.splice(at, 1)[0]; if (!gone) return;
    if (!h.pins.some(pn => pn.slot === gone.slot)) h.slots[gone.slot] = false;
    remember(k); paint(k);
    if (h.open) { const v = $(".find input", P[k].el).value; bar(k); $(".find input", P[k].el).value = v; }
  }
  function clearPins(k) {
    const h = H[k]; h.pins = []; h.slots = [false, false, false, false];
    remember(k); paint(k); if (h.open) bar(k);
    V.toast("已清空这一栏的钉住词");
  }

  /* ---- memory per (pane, doc): the term and the pins, never ranges ---- */
  const memKey = k => { const l = P[k].loc; return l && l.kind === "doc" ? k + "|" + l.tree + ":" + l.rel : null; };
  function remember(k) {
    const key = memKey(k), h = H[k]; if (!key) return;
    const mem = store.get("findmem", { order: [], map: {} });
    store.set("findmem", SV.recallPut(mem, key, { q: h.open ? h.q : "", p: h.pins.map(pn => pn.term) }, 50));
  }
  function restore(k) {
    const h = H[k], e = (store.get("findmem", { map: {} }).map[memKey(k)]) || {};
    h.pins = []; h.slots = [false, false, false, false]; (e.p || []).forEach(term => addPin(h, term));
    h.q = ""; h.hits = []; h.cur = -1;
    if (e.q) { h.open = false; open(k, e.q, true); }   // the reader already placed the page: a remembered term must not move it
    else if (h.open) { bar(k); }
  }
  function rescan(k) {
    const h = H[k]; if (!h.q && !h.pins.length) return;
    h.idx = buildIndex(k); h.hits = h.q ? SV.scanHits(h.idx.text, h.q) : [];
    h.cur = Math.min(Math.max(h.cur, h.hits.length ? 0 : -1), h.hits.length - 1);
  }
  // every content change rebuilds the index; an error panel drops everything derived from the old content
  V.on("rendered", (k, entering) => {
    const h = H[k]; clearTimeout(h.t); h.idx = null;
    if (!$(".md", P[k].body)) { h.hits = []; h.cur = -1; if (HL) names(k).forEach(n => CSS.highlights.delete(n)); rail(k); count(k); return; }
    if (entering) restore(k);
    rescan(k); paint(k);
  });
  V.on("content", k => { rescan(k); paint(k); });
  V.on("leave", k => { clearTimeout(H[k].t); remember(k); echo(k, ""); });
  V.on("layout", () => ["A", "B"].forEach(rail));

  /* ---- selection echo + the selection bar ---- */
  function echo(k, text) {
    if (!HL) return;
    const nm = "echo-" + k;
    if (!text || text.length < 2 || /\n/.test(text)) { CSS.highlights.delete(nm); return; }
    const h = H[k]; if (!h.idx) h.idx = buildIndex(k); if (!h.idx) return;
    const hl = highlight(h.idx, SV.scanHits(h.idx.text, text.toLowerCase()), 150);
    if (hl.size > 1) CSS.highlights.set(nm, hl); else CSS.highlights.delete(nm);
  }
  let selK = "A", echoT = 0;
  document.addEventListener("selectionchange", () => {
    clearTimeout(echoT);
    echoT = setTimeout(() => {
      const s = window.getSelection(), at = s && s.anchorNode && s.anchorNode.parentElement, pane = at && at.closest("#pA,#pB");
      ["A", "B"].forEach(x => echo(x, pane && V.paneOf(pane) === x ? String(s).trim() : ""));
    }, 120);
  });
  document.addEventListener("mouseup", e => {
    const pb = e.target.closest(".pbody"), sb = $("#selbar");
    if (!pb) { if (!e.target.closest("#selbar")) sb.classList.remove("on"); return; }
    setTimeout(() => {
      const s = window.getSelection(), txt = s.toString().trim();
      if (!txt || txt.length > 160 || !s.rangeCount) { sb.classList.remove("on"); return; }
      selK = V.paneOf(pb);
      const r = s.getRangeAt(0).getBoundingClientRect(); sb.classList.add("on");
      sb.style.left = Math.max(8, Math.min(innerWidth - sb.offsetWidth - 8, r.left + r.width / 2 - sb.offsetWidth / 2)) + "px";
      sb.style.top = (r.top - sb.offsetHeight - 8 < 40 ? r.bottom + 8 : r.top - sb.offsetHeight - 8) + "px";
    }, 10);
  });
  V.click("#selbar button", el => {
    const s = window.getSelection().toString().trim(), loc = P[selK].loc;
    $("#selbar").classList.remove("on");
    if (el.dataset.s === "find") open(selK, s); else V.copy(`${loc.rel.split("/").pop()}：「${s}」`, "已复制为引用");
  });

  /* ---- clicks, keys, layers ---- */
  V.click('.phd [data-t="find"]', el => { const k = V.paneOf(el); H[k].open ? close(k) : open(k, selected(k)); });
  V.click("[data-fnav]", el => step(V.paneOf(el), +el.dataset.fnav));
  V.click("[data-fclose]", el => close(V.paneOf(el)));
  V.click("[data-fpin]", el => { const k = V.paneOf(el); pin(k, $(".find input", P[k].el).value); });
  V.click("[data-unpin]", el => unpin(V.paneOf(el), +el.dataset.unpin));
  V.click(".frail.on", (el, e) => {   // a click on the rail jumps to the nearest mark
    const k = V.paneOf(el), h = H[k], y = e.clientY - el.getBoundingClientRect().top;
    let best = null, d = 1e9;
    $$("i", el).forEach(m => { const dy = Math.abs(m.offsetTop - y); if (dy < d) { d = dy; best = m; } });
    if (!best) return;
    if (best.dataset.hit != null) { h.cur = +best.dataset.hit; paint(k); show(k, true); return; }
    const rc = rectOf(h.idx, [+best.dataset.s, +best.dataset.e]); if (rc) scrollToRect(k, rc);
  });
  V.hotkey("f", () => { if (V.view !== "doc") return false; open(V.focus, selected(V.focus)); });
  V.hotkey("h", () => {
    if (V.view !== "doc") return false;
    const t = selected(V.focus); if (t) pin(V.focus, t); else V.toast("先选中一个词，再按 h 钉住");
  });
  V.hotkey("H", () => { if (V.view !== "doc") return false; clearPins(V.focus); });
  V.layer(40, () => !!$("#selbar.on"), () => $("#selbar").classList.remove("on"));
  V.layer(20, () => V.view === "doc" && H[V.focus].open, () => close(V.focus));
})(V2);
