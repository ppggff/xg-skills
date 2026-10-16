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
    return '<div class="phd">'
      + `<button class="ib navb" data-navb data-tip="导航" aria-label="导航">${V.I.menu}</button>`
      + V.paneHead(k) + '<div class="ppath"></div>'
      + b("star", "star", "加星标", "s") + b("find", "find", "在本文查找", "f") + b("hist", "hist", "这篇文档的变更历史")
      + b("width", "width", "阅读宽度：默认 / 自定 / 铺满") + b("mirror", "mirror", "在另一栏打开这篇（镜像）")
      + (V.GITWEB ? b("gitweb", "code", "在 gitweb 打开这篇（新标签页）") : "") + b("tedit", "doc", "编辑这个 todo 文件") + V.paneEnd(k)
      + `<button class="ib tocb" data-t="toc" data-tip="目录" aria-label="目录">${V.I.toc}</button></div>`
      + '<div class="stale"><span>这篇文档在磁盘上更新了</span><button data-stale>刷新</button></div><div class="chgbar" hidden></div>'
      + `<div class="find" data-pane="${k}"></div><div class="pbody scroll"></div><div class="frail"></div>`
      + `<button class="secchip" data-sec data-tip="打开目录" aria-label="打开目录">${V.I.toc}<span></span></button>`;
  }
  const BLANK = '<div class="empty"><div><svg width="42" height="28" viewBox="0 0 46 30" fill="none" stroke="currentColor">'
    + '<rect x=".5" y=".5" width="45" height="29" rx="3"/><path d="M23 .5v29"/><path d="M28 9h12M28 14h9M28 19h11" opacity=".5"/></svg>'
    + "点正文里的 [Fact-n]，或按住 ⇧ 点一个链接，<br>文档会在这一栏打开。</div></div>";
  const BLOCK_SEL = ".md p,.md li,.md h1,.md h2,.md h3,.md h4,.md h5,.md h6,.md pre,.md tr,.md blockquote,.md .mermaid";
  V.on("init", () => ["A", "B"].forEach(k => {
    const p = P[k]; p.el.innerHTML = shell(k); p.body = $(".pbody", p.el); p.doc = null;
    if (k === "B") p.body.innerHTML = BLANK;
    p.body.addEventListener("scroll", () => onScroll(k), { passive: true });
    p.el.addEventListener("pointerdown", () => V.setFocus(k));
    p.body.addEventListener("click", e => {
      if (e.target.closest("a,button,.cite,.fmt,.fml,input,.mrule") || String(window.getSelection())) return;
      const blk = e.target.closest(BLOCK_SEL); if (blk) curLine(k, blk, e.clientY);
    });
  }));
  const keyOf = loc => loc.tree + ":" + loc.rel;
  const shown = k => (k === "A" || V.isSplit()) && V.kindOf(k) === "doc";
  const visible = k => shown(k) && !(V.isNarrow() && V.isSplit() && k !== V.focus);   // narrow shows one pane
  const tocK = () => { const f = V.navPane(), o = V.other(f); return shown(f) ? f : shown(o) ? o : null; };   // whose headings the side column lists

  /* ---- reading place: per (pane, doc), a content anchor first and pixels as the fallback ---- */
  const NOT_BLOCK = /^(lnum|curline|lastmark|mrule|fml|fmt)$/;
  const blocks = k => $$(".md > *", P[k].body).filter(el => ![...el.classList].some(c => NOT_BLOCK.test(c)));
  V.lineOf = (k, el) => {   // 0-based source line (frontmatter included) of the top-level block holding el, when blocks map 1:1
    const p = P[k], i = p.spans ? blocks(k).findIndex(b => b.contains(el)) : -1;
    return i >= 0 ? p.spans[i].start + p.doc.fmLines : null;
  };
  const blockText = el => (el.textContent || "").replace(/\s+/g, " ").trim();
  function topBlock(k) {
    const els = blocks(k), edge = P[k].body.getBoundingClientRect().top + HEAD_PAD;
    for (let i = 0; i < els.length; i++) if (els[i].getBoundingClientRect().bottom > edge) return i;
    return els.length - 1;
  }
  const memKey = (k, loc) => k + "|" + keyOf(loc);
  function savePlace(k) {
    const p = P[k], loc = p.loc; if (!loc || loc.kind !== "doc" || !p.doc || p.doc.err) return;
    const b = p.body, max = b.scrollHeight - b.clientHeight, mem = store.get("read", { order: [], map: {} }), old = mem.map[memKey(k, loc)] || {};
    const els = blocks(k), i = topBlock(k), into = els[i] ? b.getBoundingClientRect().top + HEAD_PAD - els[i].getBoundingClientRect().top : 0;
    const entry = { a: SV.anchorOf(els.map(blockText), i), o: Math.max(0, Math.round(into)), y: b.scrollTop,
      max: Math.max(old.max || 0, max > 0 ? b.scrollTop / max : 1) };
    store.set("read", SV.recallPut(mem, memKey(k, loc), entry, 50));
  }
  V.readPct = key => {
    const m = store.get("read", { map: {} }).map, most = Math.max(0, ...["A", "B"].map(k => (m[k + "|" + key] || {}).max || 0));
    return Math.round(Math.min(1, most) * 100);
  };
  function restorePlace(k) {
    const p = P[k], e = store.get("read", { map: {} }).map[memKey(k, p.loc)];
    if (!e || !e.y) return false;
    const els = blocks(k), i = SV.anchorFind(els.map(blockText), e.a), b = p.body;
    if (i >= 0) b.scrollTop += els[i].getBoundingClientRect().top - b.getBoundingClientRect().top - HEAD_PAD + Math.min(e.o || 0, els[i].offsetHeight);
    else b.scrollTop = e.y;
    if (b.scrollTop > 300) setTimeout(() => lastMark(k), 60);
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
      s.onerror = () => no(new Error("mermaid failed to load"));
      document.head.appendChild(s);
    }));
  }
  function renderMermaid(k, root) {
    const codes = $$("pre > code.language-mermaid", root); if (!codes.length) return;
    ensureMermaid().then(m => codes.forEach((code, i) => {
      const src = code.textContent, holder = document.createElement("div"), gid = "mmd" + Date.now() + i;
      holder.className = "mermaid"; holder.dataset.src = src;
      if (code.parentNode.dataset.ln) holder.dataset.ln = code.parentNode.dataset.ln;
      code.parentNode.replaceWith(holder);
      // mermaid leaves its measuring node (#d<gid>/#i<gid>) on <body> when a diagram fails to parse
      const drop = () => ["d" + gid, "i" + gid].forEach(id => { const el = document.getElementById(id); if (el && el.parentNode === document.body) el.remove(); });
      m.render(gid, src).then(r => { holder.innerHTML = r.svg; drop(); V.emit("content", k); })
        .catch(e => { holder.innerHTML = `<pre class="merr">mermaid: ${esc(e.message)}</pre>`; drop(); });
    })).catch(() => {});
  }
  function markLink(a, loc) {
    const raw = a.getAttribute("href"), key = SV.resolveLink(raw, loc.tree, loc.rel, V.D.sets) || SV.resolveWikiAny(raw, V.D.sets) || (V.cardWiki && V.cardWiki(raw));
    if (key) {
      const i = key.indexOf(":");
      a.dataset.tree = key.slice(0, i); a.dataset.rel = key.slice(i + 1); a.removeAttribute("href"); a.tabIndex = 0; a.setAttribute("role", "link");
      const ln = /#L(\d+)\]\]$/.exec(raw); if (ln) a.dataset.line = ln[1];   // [[doc#L12]] opens at that line
    } else if (/^https?:\/\//i.test(raw)) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
    else if (raw.charAt(0) === "#") { a.dataset.hash = raw.slice(1); a.removeAttribute("href"); }
    else { a.classList.add("broken"); a.removeAttribute("href"); a.dataset.tip = "找不到这个链接的目标：" + raw; }
  }
  function markDoc(k, md, loc) {
    $$("h1,h2,h3,h4,h5,h6,li", md).forEach(el => {
      const x = SV.xidHead(el.textContent); if (x && !md.querySelector(`[data-xid="${x.id}"]`)) el.dataset.xid = x.id;
    });
    $$("h1,h2,h3,h4", md).forEach((h, i) => {
      h.id = k + "-h" + i;
      if (h.tagName !== "H1") h.insertAdjacentHTML("afterbegin", '<button class="anc" data-anc data-tip="复制这一节的链接" aria-label="复制链接">#</button>');
    });
    $$("a[href]", md).forEach(a => markLink(a, loc));
  }
  // one source line number per top-level block, in the left margin; a span/block mismatch means no numbers, not wrong ones
  function lineNumbers(k) {
    const p = P[k], md = $(".md", p.body); if (!md || !p.doc || p.doc.src) return;
    $$(".lnum", md).forEach(x => x.remove());
    let els, nums;
    if (p.chg) { els = $$(":scope > [data-ln]", md); nums = els.map(b => b.dataset.ln); }   // the change view numbers its after-version
    else {
      const spans = SV.blockSpans(window.marked.lexer(p.doc.body)); els = blocks(k);
      if (spans.length !== els.length) return;
      nums = SV.blockLineNumbers(spans, p.doc.fmLines);
      p.spans = spans;   // only when spans and blocks line up 1:1
    }
    const mr = md.getBoundingClientRect();
    els.forEach((b, i) => {
      const w = document.createTreeWalker(b, NodeFilter.SHOW_TEXT); let n, line = null;
      while (!line && (n = w.nextNode())) {
        if (!n.data.trim()) continue;
        const r = document.createRange(); r.setStart(n, 0); r.setEnd(n, 1); line = r.getClientRects()[0];
      }
      const top = (line ? line.top + line.height / 2 - 5 : b.getBoundingClientRect().top + 4) - mr.top;
      md.insertAdjacentHTML("beforeend", `<span class="lnum" style="top:${top}px">${nums[i]}</span>`);
    });
  }
  const SHA = /^[0-9a-f]{7,40}$/i;
  const fmVal = v => (v || "").split(/(?:^|\s)#/)[0].trim().replace(/^["']|["']$/g, "");   // as workflow-status reads it: " # comment" and quotes off
  // 043: commits named in a doc (inline code, frontmatter go/skill) and its frontmatter branch open in gitweb
  function linkGit(k, md, loc) {
    if (!V.GITWEB) return;
    const c = V.cardOfPath(loc.tree, loc.rel), fm = P[k].doc.fields, own = x => fmVal(fm[x]);
    const repo = own("repo") || (c && (c.repo || c.p)) || "";
    const wrap = (el, href, tip) => { const a = document.createElement("a"); a.className = "gitl"; a.href = href; a.target = "_blank"; a.rel = "noopener"; a.dataset.tip = tip; el.replaceWith(a); a.appendChild(el); };
    if (repo) $$("[data-branch]", md).forEach(el => wrap(el, `${V.GITWEB}?p=${encodeURIComponent(repo)};a=shortlog;h=refs/heads/${encodeURIComponent(el.dataset.branch)}`, `在 gitweb 看分支 ${el.dataset.branch}（${repo}）`));
    const els = $$(":not(pre) > code", md).filter(el => SHA.test(el.textContent.trim())).concat($$("[data-sha]", md));
    if (!els.length) return;
    const sha = el => (el.dataset.sha || el.textContent).trim().toLowerCase(), prefer = [repo, loc.tree === "kb" ? "knowledge" : "dev-workflow"].filter(Boolean);
    V.json("/api/shas?" + [...new Set(els.map(sha))].map(h => "h=" + h).concat(prefer.map(p => "prefer=" + encodeURIComponent(p))).join("&")).then(map => {
      if (P[k].loc !== loc) return;
      els.forEach(el => { const h = sha(el), r = map[h]; if (r && el.isConnected) wrap(el, `${V.GITWEB}?p=${encodeURIComponent(r)};a=commit;h=${h}`, `在 gitweb 看这次提交（${r}）`); });
    }).catch(() => {});
  }
  function fmLine(f) {
    const keys = Object.keys(f); if (!keys.length) return "";
    const g = x => fmVal(f[x]), bits = [g("status"), g("governance"), g("created")].map(esc);
    if (g("branch")) bits.push(`<span data-branch="${esc(g("branch"))}">⎇ ${esc(g("branch"))}</span>`);
    if (SHA.test(g("go"))) bits.push(`go <span data-sha="${esc(g("go"))}">${esc(g("go"))}</span>`);
    const val = x => (SHA.test(g(x)) ? `<span data-sha="${esc(g(x))}">${esc(f[x])}</span>` : x === "branch" && g(x) ? `<span data-branch="${esc(g(x))}">${esc(f[x])}</span>` : esc(f[x]));
    return `<div class="fml">${bits.filter(Boolean).map(b => `<span>${b}</span>`).join("")}<button data-fmx aria-expanded="false">${keys.length} 项</button></div>`
      + `<div class="fmt" hidden>${keys.map(x => `<b>${esc(x)}</b><span>${val(x)}</span>`).join("")}</div>`;
  }
  function crumb(k, loc) {
    const s = loc.rel.split("/"), pre = loc.tree !== "dev" ? V.ROOT_NAME[loc.tree] + " / " : "", at = P[k].chg ? " @ " + esc(shaLabel(P[k].chg)) : "";
    $(".ppath", P[k].el).dataset.tip = V.ROOT_NAME[loc.tree] + "/" + loc.rel;
    $(".ppath", P[k].el).innerHTML = `<bdi>${esc(pre + s.slice(0, -1).join(" / "))} / <b>${esc(s[s.length - 1])}</b>${at}</bdi>`;
  }
  function lineTarget(k, loc) {   // the block holding a source line, else (no line table) the section holding it
    const p = P[k];
    if (p.spans) { const i = p.spans.findIndex(s => loc.line - 1 - p.doc.fmLines <= s.end); return blocks(k)[i >= 0 ? i : p.spans.length - 1] || null; }
    const lines = [], hs = $$(".md h1,.md h2,.md h3,.md h4,.md h5,.md h6", p.body);
    p.doc.body.split("\n").forEach((l, i) => { if (/^#{1,6}\s+\S/.test(l)) lines.push({ line: i }); });
    return hs[SV.sectionForLine(lines.length === hs.length ? lines : [], loc.line, p.doc.fmLines)] || null;
  }
  // scroll writers in priority order: an explicit target, then (entering only) the remembered place, else stay put
  function place(k, loc, opt, keepTop) {
    const p = P[k], b = p.body;
    if (!opt.entering) { b.scrollTop = keepTop; return; }
    if (loc.top != null) { b.scrollTop = loc.top; return; }
    let el = null;
    if (loc.xid) el = $(`[data-xid="${V.cssEsc(loc.xid)}"]`, b);
    if (!el && loc.hash) el = $(`#${V.cssEsc(loc.hash)}`, b) || $$("h1,h2,h3,h4", b).find(h => slug(h.textContent) === loc.hash);
    if (!el && loc.line) el = lineTarget(k, loc);
    if (el) { b.scrollTop = el.offsetTop - HEAD_PAD; flash(el); curLine(k, el, null); }
    else if (loc.xid) V.toast("没找到 " + loc.xid + " 的定义");
    else if (!restorePlace(k)) b.scrollTop = 0;
  }
  const slug = t => t.replace(/^#/, "").trim().toLowerCase().replace(/[^\w一-鿿]+/g, "-").replace(/^-+|-+$/g, "");
  function paint(k, loc, opt, text, mtime, version) {
    const p = P[k], keepTop = p.body.scrollTop, src = !/\.md$/i.test(loc.rel);
    p.spans = null;
    const fm = src ? { fields: {}, body: text } : SV.parseFrontmatter(text);
    p.doc = { text, body: fm.body, fields: fm.fields, mtime, version, src, fmLines: text.split("\n").length - fm.body.split("\n").length };
    p.el.classList.remove("blank"); $(".stale", p.el).classList.remove("on");
    const inner = src ? `<pre><code>${esc(text)}</code></pre>` : fmLine(fm.fields) + window.marked.parse(fm.body);
    p.body.innerHTML = `<article class="md${src ? " src" : ""}${opt.entering && !V.RM ? " enter" : ""}" lang="en">${inner}</article>`;   // en: the system face picks PingFang's UI cut for Chinese, as the classic shell
    const md = $(".md", p.body);
    if (!src) { markDoc(k, md, loc); renderMermaid(k, md); linkGit(k, md, loc); }
    applyMeasure(k); crumb(k, loc); lineNumbers(k);
    place(k, loc, opt, keepTop);
    p.chars = (md.textContent || "").replace(/\s/g, "").length;
    paintStar(k); V.emit("rendered", k, opt.entering);
    if (k === tocK()) toc();
    V.status();
  }
  function fail(k, loc, e) {
    const p = P[k]; p.doc = { err: true }; p.spans = null; p.el.classList.remove("blank"); crumb(k, loc);
    const why = e.status === 404 ? "<b>这个文件不存在或已被移动。</b>" : "<b>打不开这篇文档。</b><br>" + esc(e.message);
    p.body.innerHTML = `<div class="derr">${why}<br><span class="hint" style="padding:0">${esc(loc.tree + "/" + loc.rel)}</span></div>`;
    V.emit("rendered", k, true); if (k === tocK()) toc(); V.status();
  }
  V.views.doc = (k, loc, opt) => {
    const p = P[k]; p.chg = null; $(".chgbar", p.el).hidden = true;
    if (opt.entering) { p.cur = null; $$(".curline,.lastmark", p.body).forEach(x => x.remove()); }
    let mt = 0, ver = "";
    V.api("/raw/" + loc.tree + "/" + loc.rel).then(r => { mt = +r.headers.get("X-Mtime") || 0; ver = r.headers.get("X-Version") || ""; return r.text(); })
      .then(t => { if (p.loc === loc && !p.chg) paint(k, loc, opt, t, mt, ver); })
      .catch(e => { if (p.loc === loc) fail(k, loc, e); });
  };

  /* ---- reading width: default / custom / full per pane; the body sits left, each rule moves its own edge ---- */
  const MEAS = store.get("measure", {});
  ["A", "B"].forEach(k => {   // older stores: a "wide" tier, or a custom width without a left edge
    const m = MEAS[k] = Object.assign({ mode: "default" }, MEAS[k]);
    if (m.mode === "wide") m.mode = "default";
    if (typeof m.w === "number" && typeof m.l !== "number") m.l = 12;
    if (m.mode === "custom" && typeof m.w !== "number") m.mode = "default";
  });
  const M_LEFT = 12, M_MIN = 360, WNAME = { default: "默认", full: "铺满" };
  const hasCustom = m => typeof m.l === "number" && typeof m.w === "number";
  function applyMeasure(k) {
    const md = $(".md", P[k].body); if (!md || md.classList.contains("src")) return;
    const m = MEAS[k], space = P[k].body.clientWidth - M_LEFT;   // the right rule needs a gap to sit in
    if (!$(".mrule", md)) md.insertAdjacentHTML("beforeend", '<i class="mrule" data-m="l" data-tip="拖动左边界"></i><i class="mrule" data-m="r" data-tip="拖动右边界"></i>');
    if (V.isNarrow()) { md.style.removeProperty("--m-l"); md.style.removeProperty("--m-w"); return; }   // full width, rules hidden by CSS
    if (m.mode === "custom" && hasCustom(m)) {
      const c = SV.clampMeasure(m.l, m.w, space, M_MIN);
      md.style.setProperty("--m-l", c.left + "px"); md.style.setProperty("--m-w", c.width + "px");
    } else {
      md.style.setProperty("--m-l", M_LEFT + "px");
      if (m.mode === "full") md.style.setProperty("--m-w", SV.clampMeasure(M_LEFT, space - M_LEFT, space, M_MIN).width + "px"); else md.style.removeProperty("--m-w");
    }
    $('[data-t="width"]', P[k].el).dataset.tip = "阅读宽度：" + (m.mode === "custom" && hasCustom(m) ? "自定 " + Math.round(m.w) + "px" : WNAME[m.mode] || WNAME.default) + "（点击切换）";
  }
  const remeasure = k => { store.set("measure", MEAS); applyMeasure(k); lineNumbers(k); V.emit("content", k); };
  document.addEventListener("pointerdown", e => {
    const r = e.target.closest(".mrule"); if (!r) return;
    e.preventDefault();
    const k = V.paneOf(r), md = r.parentElement, body = P[k].body, x0 = e.clientX, isLeft = r.dataset.m === "l";
    const l0 = md.getBoundingClientRect().left - body.getBoundingClientRect().left, w0 = md.getBoundingClientRect().width, space = body.clientWidth - M_LEFT;
    r.classList.add("drag"); try { r.setPointerCapture(e.pointerId); } catch (x) {}
    const move = ev => {
      const dx = ev.clientX - x0, c = SV.clampMeasure(isLeft ? l0 + dx : l0, isLeft ? w0 - dx : w0 + dx, space, M_MIN);
      MEAS[k] = { mode: "custom", l: c.left, w: c.width }; applyMeasure(k);
    };
    const up = () => { r.classList.remove("drag"); document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); remeasure(k); };
    document.addEventListener("pointermove", move); document.addEventListener("pointerup", up);
  });
  V.click('[data-t="width"]', el => {   // default → the dragged width, if any → full → default
    const k = V.paneOf(el), m = MEAS[k];
    m.mode = m.mode === "default" ? (hasCustom(m) ? "custom" : "full") : m.mode === "custom" ? "full" : "default";
    remeasure(k);
  });

  /* ---- current line, last-read mark, flash ---- */
  function inkShift(el) {   // how far the ink's middle lies below the font box's middle, measured on the block's own text
    const cs = getComputedStyle(el), cv = document.createElement("canvas"), c = cv.getContext("2d");
    const lang = el.closest("[lang]") ? el.closest("[lang]").lang : ""; cv.lang = lang; if ("lang" in c) c.lang = lang;
    c.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const anc = $(":scope > .anc", el), text = (el.textContent || "").slice(anc ? anc.textContent.length : 0).trim();
    const m = c.measureText(text.slice(0, 80) || "Hg"), fa = m.fontBoundingBoxAscent, fd = m.fontBoundingBoxDescent;
    return fa + fd ? (2 * fa - m.actualBoundingBoxAscent + m.actualBoundingBoxDescent) / 2 - (fa + fd) / 2 : 0;
  }
  function curLine(k, blk, clientY) {
    const b = P[k].body, md = $(".md", b); if (!blk || !md || !b.contains(blk)) return;
    let ov = $(".curline", md);
    if (!ov) { ov = document.createElement("div"); ov.className = "curline"; md.appendChild(ov); }
    const row = blk.closest("tr"), mr = md.getBoundingClientRect(), cs = getComputedStyle(md);
    let rect;
    if (row) rect = row.getBoundingClientRect();
    else {
      const rg = document.createRange(); rg.selectNodeContents(blk);
      const anc = $(":scope > .anc", blk), ar = anc && anc.getBoundingClientRect();   // a heading's # sits in the gutter, in its own face
      const own = r => r.width > 1 && r.height > 1 && !(ar && r.left < ar.right && r.right > ar.left && r.top < ar.bottom && r.bottom > ar.top);
      rect = SV.pickLineRect([...rg.getClientRects()].filter(own), clientY) || blk.getBoundingClientRect();
    }
    const padL = parseFloat(cs.paddingLeft), padR = parseFloat(cs.paddingRight);
    // a text rect is the font box; the band covers the whole line box, centred on the glyphs' ink, which sits low in the box
    const lh = row ? 0 : parseFloat(getComputedStyle(blk).lineHeight) || 0, h = Math.max(rect.height, lh);
    const top = rect.top - (h - rect.height) / 2 + (row ? 0 : inkShift(blk));
    ov.style.top = (top - mr.top - 1) + "px"; ov.style.height = (h + 2) + "px";
    ov.style.left = (padL - 8) + "px"; ov.style.width = (mr.width - padL - padR + 16) + "px";
    P[k].cur = { blk, off: clientY == null ? null : clientY - blk.getBoundingClientRect().top };
  }
  function recur(k) {
    const c = P[k].cur; if (c && c.blk.isConnected) curLine(k, c.blk, c.off == null ? null : c.blk.getBoundingClientRect().top + c.off);
  }
  function lastMark(k) {
    if (V.RM) return;
    const b = P[k].body, md = $(".md", b); if (!md) return;
    $$(".lastmark", md).forEach(x => x.remove());
    const best = blocks(k)[topBlock(k)], m = document.createElement("div");
    m.className = "lastmark"; m.style.top = (best ? best.offsetTop : b.scrollTop) + 11 + "px"; md.appendChild(m);
    const evs = ["wheel", "touchmove", "keydown"], on = t => (t === "keydown" ? document : b);
    const drop = e => {
      if (e.type === "keydown" && !/^(Arrow|Page|Home|End| )/.test(e.key)) return;
      evs.forEach(t => on(t).removeEventListener(t, drop)); m.classList.add("out"); setTimeout(() => m.remove(), 450);
    };
    evs.forEach(t => on(t).addEventListener(t, drop, { passive: true }));
  }
  function flash(el) { if (V.RM) return; el.classList.remove("hl"); void el.offsetWidth; el.classList.add("hl"); }
  V.on("layout", () => setTimeout(() => ["A", "B"].forEach(k => {
    if (visible(k) && P[k].doc && !P[k].doc.err) { applyMeasure(k); lineNumbers(k); recur(k); V.emit("content", k); }
  }), 60));
  V.on("content", k => recur(k));

  /* ---- toc + rail of ticks + the section chip ---- */
  let heads = [];
  const headLabel = h => SV.tocLabel(h.textContent);
  function toc() {
    if (V.view === "search") return V.searchToc();
    $("#sideT").textContent = "目录";
    const k = tocK(); if (!k) return;
    const p = P[k];
    if (!p.doc || p.doc.err) { $("#sbody").innerHTML = '<div class="hint">这一栏空着</div>'; $("#sticks").innerHTML = ""; heads = []; return; }
    heads = $$(".md :is(h1,h2,h3,h4,h5,h6)", p.body);
    const items = heads.map((h, i) => {
      const x = headLabel(h), mark = x.ok ? V.I.tick : x.inf ? "<em>推</em>" : "";
      return `<button class="ti" data-ti="${i}" style="--d:${+h.tagName[1] - 1}" data-tip="${esc(x.t)}"><span class="ck2">${mark}</span><span class="tl">${esc(x.t)}</span></button>`;
    }).join("");
    $("#sbody").innerHTML = `<div class="toc">${items || '<div class="hint">这篇没有标题</div>'}</div>`;
    const hh = Math.max(6, Math.min(16, Math.floor(($("#side").clientHeight - 70) / Math.max(1, heads.length))));
    const tw = h => ({ 1: 14, 2: 10 }[h.tagName[1]] || 6);
    $("#sticks").style.setProperty("--mw", Math.max(6, ...heads.map(tw)) + "px");
    $("#sticks").innerHTML = heads.map((h, i) => {
      const x = headLabel(h);
      return `<button class="stk ${x.ok ? "ok" : ""}" data-ti="${i}" data-tip="${esc(x.t)}" style="--h:${hh}px;--w:${tw(h)}px" aria-label="${esc(x.t)}"><i></i></button>`;
    }).join("");
    spy();
  }
  function spy() {
    const tk = tocK(); if (!tk) return;
    const p = P[tk], top = p.body.scrollTop + 40; let c = -1;
    heads.forEach((h, i) => { if (h.offsetTop <= top) c = i; });
    $$("#sbody .ti").forEach((b, i) => b.classList.toggle("cur", i === c));
    $$("#sticks .stk").forEach((b, i) => b.classList.toggle("cur", i === c));
    const cb = $("#sbody .ti.cur"), sb = $("#sbody");
    if (cb && (cb.offsetTop < sb.scrollTop + 10 || cb.offsetTop > sb.scrollTop + sb.clientHeight - 30)) sb.scrollTop = cb.offsetTop - sb.clientHeight / 3;
    ["A", "B"].forEach(k => {
      const chip = $(".secchip", P[k].el), on = V.isNarrow() && k === tk && k === V.focus && c >= 0 && !!heads[c];
      chip.classList.toggle("on", on); if (on) $("span", chip).textContent = headLabel(heads[c]).t;
    });
  }
  const sr = {};
  function onScroll(k) {
    if (sr[k]) return;
    sr[k] = requestAnimationFrame(() => {
      sr[k] = 0; if (k === tocK()) spy(); if (k === V.focus) V.status();
      clearTimeout(sr["t" + k]); sr["t" + k] = setTimeout(() => savePlace(k), 400);
    });
  }
  V.on("focus", k => {
    toc();
    if (V.isNarrow() && visible(k) && P[k].doc && !P[k].doc.err) { applyMeasure(k); lineNumbers(k); recur(k); V.emit("content", k); }
  });
  V.on("nav", (k, loc) => { if (loc.kind !== "doc") { $$(".secchip").forEach(c => c.classList.remove("on")); toc(); } });
  const jumpTo = (k, el, smooth) => {
    const p = P[k], b = p.body;
    if (p.loc && p.loc.kind === "doc") { p.hist.push(V.here(p)); p.fwd.length = 0; V.paintHist(); }   // an in-doc jump can be undone with back
    if (smooth) b.scrollTo({ top: el.offsetTop - HEAD_PAD, behavior: V.RM ? "auto" : "smooth" }); else b.scrollTop = el.offsetTop - HEAD_PAD;
    flash(el); curLine(k, el, null);
  };
  V.click("[data-ti]", el => { V.app.classList.remove("tocpop"); const h = heads[+el.dataset.ti]; if (h) jumpTo(tocK(), h, true); });
  V.click('[data-t="toc"],[data-sec]', () => { V.app.classList.toggle("tocpop"); V.applyW(); });

  /* ---- citations: jump in place, else open the defining file beside this one, with a connecting line ---- */
  const factCache = {};
  function factOf(rel, id) {   // the "### Fact-n" block of a card's facts.md, fetched once per file version
    const mt = V.D.mtime.dev[rel], c = factCache[rel];
    if (c && c.mt === mt) return Promise.resolve(c.map[id] || null);
    return V.api("/raw/dev/" + rel).then(r => r.text())
      .then(src => { factCache[rel] = { mt, map: SV.factBlocks(src) }; return factCache[rel].map[id] || null; })
      .catch(() => null);
  }
  let tipT = null, tipFor = null, hideT = null;
  const hideTip = () => { clearTimeout(tipT); clearTimeout(hideT); tipFor = null; $("#tip").classList.remove("on", "wide"); };
  V.on("tip-hide", hideTip);
  function showTipAt(anchor, html, wide) {
    const t = $("#tip"); t.innerHTML = html; t.classList.add("on"); t.classList.toggle("wide", !!wide);
    const r = anchor.getBoundingClientRect(), w = t.offsetWidth, h = t.offsetHeight;
    t.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left - 20)) + "px";
    t.style.top = (r.bottom + h + 12 > innerHeight ? Math.max(8, r.top - h - 8) : r.bottom + 6) + "px";
  }
  V.tipAt = showTipAt; V.hideTip = hideTip;
  const tipHead = (b, where, extra) => `<div class="h"><b>${esc(b)}</b>${extra || ""}<span style="margin-left:auto">${esc(where)}</span></div>`;
  const inline = s => window.marked.parseInline(s.length > 260 ? s.slice(0, 260) + "…" : s);
  function claimBefore(ce, id) {   // the clause of the sentence a citation backs, as the tip's first line
    const para = (ce.closest("p,li,td") || ce.parentElement).textContent.replace(/\s+/g, " "), at = para.indexOf("[" + id);
    let pre = at < 0 ? "" : para.slice(0, at);
    pre = pre.slice(Math.max(...["。", "；", ";", "？", "！"].map(x => pre.lastIndexOf(x))) + 1);
    pre = pre.replace(/\[[A-Za-z]+-\d+[^\]]*\]/g, "").replace(/\s+/g, " ").trim();
    return pre.length > 60 ? "…" + pre.slice(-60) : pre;
  }
  function showCite(ce) {
    const k = V.paneOf(ce), loc = P[k].loc, id = ce.dataset.ref; if (!loc) return;
    tipFor = ce;
    const local = $(`[data-xid="${V.cssEsc(id)}"]`, P[k].body);
    if (local) return showTipAt(ce, tipHead(id, "本文") + `<p>${esc(local.textContent.replace(/^#/, "").trim().slice(0, 140))}</p>`);
    const home = SV.xidHomeRel(loc.rel, id); if (!home || loc.tree !== "dev") return;
    factOf(home, id).then(md => {
      if (tipFor !== ce || !md) return;
      const head = md.split("\n")[0].replace("### ", ""), body = md.replace(/^### [^\n]*\n/, "");
      const grab = key => {
        const m = body.match(new RegExp(`^- ${key}[:：]\\s*([\\s\\S]*?)(?=\\n- [^\\n]{1,8}[:：]|$)`, "m"));
        return m ? m[1].replace(/\s+/g, " ").trim() : "";
      };
      const fact = grab("事实") || SV.factGist(md), src = grab("来源"), pre = claimBefore(ce, id);
      const verified = /VERIFIED/.test(head) ? '<span style="color:var(--done)">VERIFIED</span>' : "";
      showTipAt(ce, tipHead(head.split(" ")[0], "facts.md", verified) + (pre ? `<div class="l1">${esc(pre)}<mark>[${esc(id)}]</mark></div>` : "")
        + `<div class="l2">${inline(fact)}</div>` + (src ? `<div class="l3">${inline(src)}</div>` : ""));
    });
  }
  function follow(ce, e) {
    hideTip();
    const k = V.paneOf(ce), loc = P[k].loc, id = ce.dataset.ref; if (!loc) return;
    const local = $(`[data-xid="${V.cssEsc(id)}"]`, P[k].body);
    if (local && !e.shiftKey) return jumpTo(k, local, true);
    const home = local ? loc.rel : SV.xidHomeRel(loc.rel, id), canon = home && V.D.sets[loc.tree].get(home.toLowerCase());
    if (!canon) { V.toast(`没找到 ${id} 的定义`); return; }
    if (V.isNarrow()) return V.nav(k, { kind: "doc", tree: loc.tree, rel: canon, xid: id });   // one pane on narrow: the definition replaces this doc
    const o = k === "A" ? "B" : "A", there = P[o].loc;
    if (there && there.kind === "doc" && there.rel === canon && P[o].doc) {
      const el = $(`[data-xid="${V.cssEsc(id)}"]`, P[o].body); if (el) jumpTo(o, el, false);
    } else V.nav(o, { kind: "doc", tree: loc.tree, rel: canon, xid: id });
    V.setFocus(k);
    const wait = n => {
      const el = P[o].doc && $(`[data-xid="${V.cssEsc(id)}"]`, P[o].body);
      if (el) link(ce, el); else if (n) setTimeout(() => wait(n - 1), 120);
    };
    wait(15);
  }
  let linkRAF = 0;
  function link(a, b) {   // an elbow line from the citation to its definition, drawn in and faded out
    if (V.RM) return;
    cancelAnimationFrame(linkRAF); $$(".cite.on").forEach(x => x.classList.remove("on")); a.classList.add("on");
    const svg = $("#link"), t0 = performance.now();
    const step = now => {
      const t = now - t0, ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect(), ltr = ra.left < rb.left;
      const x1 = ltr ? ra.right + 2 : ra.left - 2, y1 = ra.top + ra.height / 2, x2 = ltr ? rb.left - 4 : rb.right + 4, y2 = rb.top + 11;
      const mx = Math.round((x1 + x2) / 2) + .5, grow = Math.min(1, t / 420), op = t < 2300 ? 1 : Math.max(0, 1 - (t - 2300) / 700);
      svg.innerHTML = `<path d="M${x1},${y1} H${mx} V${y2} H${x2}" pathLength="1" style="stroke-dasharray:1;stroke-dashoffset:${1 - grow};opacity:${op * .9}"/>`
        + `<circle cx="${x1}" cy="${y1}" r="2.3" style="opacity:${op}"/><circle cx="${x2}" cy="${y2}" r="2.6" style="opacity:${op * grow}"/>`;
      if (op > 0) linkRAF = requestAnimationFrame(step); else { svg.innerHTML = ""; a.classList.remove("on"); }
    };
    linkRAF = requestAnimationFrame(step);
  }

  /* ---- internal link preview: the target doc rendered in a hovercard ---- */
  const lpCache = {};
  function showPreview(a) {
    const tree = a.dataset.tree, rel = a.dataset.rel, key = tree + ":" + rel, mt = V.D.mtime[tree][rel];
    tipFor = a;
    const where = tree === "dev" ? rel.split("/").slice(0, 2).join("/") : tree === "ext" ? "外部目录 / " + rel.split("/")[0] : V.ROOT_NAME[tree];
    const draw = html => { if (tipFor === a) showTipAt(a, tipHead(rel.split("/").pop(), where) + `<div class="md">${html}</div>`, true); };
    if (lpCache[key] && lpCache[key].mt === mt) return draw(lpCache[key].html);
    V.api("/raw/" + tree + "/" + rel).then(r => r.text())
      .then(text => {
        const tmp = document.createElement("div"); tmp.innerHTML = window.marked.parse(SV.parseFrontmatter(text).body);
        $$("a[href]", tmp).forEach(x => {   // the page must not navigate away: relative hrefs go, outside links open a tab
          if (/^https?:\/\//i.test(x.getAttribute("href"))) { x.target = "_blank"; x.rel = "noopener noreferrer"; } else x.removeAttribute("href");
        });
        lpCache[key] = { mt, html: tmp.innerHTML }; draw(lpCache[key].html);
      })
      .catch(() => draw('<p class="hint">预览不了这篇文档</p>'));
  }
  const HOVER = ".pbody .cite[data-ref], .pbody .md a[data-rel]";
  document.addEventListener("mouseover", e => {
    if ($("#tip").contains(e.target)) { clearTimeout(hideT); return; }
    const ce = e.target.closest(".pbody .cite[data-ref]"), a = !V.isNarrow() && e.target.closest(".pbody .md a[data-rel]");
    if (ce || a) clearTimeout(hideT);   // a pending close from the last link must not close this one
    if (ce && ce !== tipFor) { clearTimeout(tipT); tipT = setTimeout(() => showCite(ce), 180); }
    else if (a && a !== tipFor) { clearTimeout(tipT); tipT = setTimeout(() => showPreview(a), 250); }
  });
  // a link preview waits a moment so the pointer can move into it and scroll; a citation tip closes at once
  document.addEventListener("mouseout", e => {
    const tip = $("#tip"), to = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest(".cite,.md a[data-rel],#tip");
    if (to || !(e.target.closest(HOVER) || tip.contains(e.target))) return;
    if (tip.classList.contains("wide")) { clearTimeout(hideT); hideT = setTimeout(hideTip, 450); } else hideTip();
  });
  addEventListener("scroll", e => { if (!$("#tip").contains(e.target) && $("#tip").classList.contains("on")) hideTip(); }, true);

  /* ---- change history and the change view: a commit's after-version with its added/removed blocks ---- */
  const shaLabel = sha => (sha === "worktree" ? "未提交" : sha.slice(0, 7));
  function histHTML(k, loc, cs) {
    const back = P[k].chg ? `<button class="hi first last" data-chg="" data-pane="${k}"><i class="dt"></i><span class="hmsg">回到当前版本</span><span class="hmeta"></span></button>` : "";
    const row = (c, i) => {
      const cls = [i === 0 && !P[k].chg ? "first" : "", i === cs.length - 1 ? "last" : "", P[k].chg === c.sha ? "cur" : ""].join(" ");
      const tip = esc(shaLabel(c.sha) + " · " + c.date + " · " + c.subject);
      return `<button class="hi ${cls}" data-chg="${esc(c.sha)}" data-pane="${k}" data-tip="${tip}"><i class="dt"></i>`
        + `<span class="hmsg">${esc(c.subject)}</span><span class="hmeta">${esc(shaLabel(c.sha))}　${esc(String(c.date).slice(5, 16))}</span></button>`;
    };
    return `<div class="pt">${esc(loc.rel.split("/").pop())} 的变更历史</div>` + back + (cs.length ? cs.map(row).join("") : '<div class="qnone">没有记录到提交</div>');
  }
  function histPop(k, btn) {
    const loc = P[k].loc; if (!loc || loc.kind !== "doc") return;
    V.pop("histPop", `<div class="pt">${esc(loc.rel.split("/").pop())} 的变更历史</div><div class="qnone">读取中…</div>`, btn, "right").dataset.pane = k;
    const mine = () => V.isPop("histPop") && $("#histPop").dataset.pane === k && P[k].loc === loc;
    V.json("/api/filelog?path=" + encodeURIComponent(loc.tree + "/" + loc.rel))
      .then(d => { P[k].clog = d.commits || []; P[k].clogOf = loc; if (mine()) $("#histPop").innerHTML = histHTML(k, loc, P[k].clog); })
      .catch(() => { if (mine()) $("#histPop").innerHTML = '<div class="qnone">历史读取失败</div>'; });
  }
  function changeArticle(d, loc, k) {
    const fm = SV.parseFrontmatter(d.after || ""), body = fm.body, fmLines = (d.after || "").split("\n").length - body.split("\n").length;
    const spans = SV.blockSpans(window.marked.lexer(body)), tmp = document.createElement("div");
    tmp.innerHTML = window.marked.parse(body);
    const els = [...tmp.children], use = spans.length === els.length ? spans : els.map((_, i) => spans[i] || { start: 0, end: 0 });
    if (spans.length === els.length) SV.blockLineNumbers(spans, fmLines).forEach((n, i) => { els[i].dataset.ln = n; });
    const adds = (d.adds || []).map(x => x - 1 - fmLines), dels = (d.dels || []).map(g => ({ at: g.at - 1 - fmLines, lines: g.lines }));
    const md = document.createElement("article"); md.className = "md";
    SV.diffSegments(use, adds, dels).forEach(s => {
      if (s.del) { const g = document.createElement("div"); g.className = "chg-del"; g.textContent = s.del.join("\n"); md.appendChild(g); return; }
      for (let i = s.from; i <= s.to; i++) if (els[i]) { if (s.add) els[i].classList.add("chg-add"); md.appendChild(els[i]); }
    });
    markDoc(k, md, loc);
    return md;
  }
  // the history stays open while stepping through commits; it re-marks the one on screen
  const repaintHist = k => { if (V.isPop("histPop") && $("#histPop").dataset.pane === k && P[k].clogOf === P[k].loc) $("#histPop").innerHTML = histHTML(k, P[k].loc, P[k].clog); };
  V.on("nav", k => { if (V.isPop("histPop") && $("#histPop").dataset.pane === k) V.closePops(); });   // the list belongs to the doc that was open
  function changeView(k, sha) {
    const p = P[k], loc = p.loc;
    if (!sha) { p.chg = null; $(".chgbar", p.el).hidden = true; repaintHist(k); return V.views.doc(k, loc, { entering: false }); }
    V.json("/api/filediff?path=" + encodeURIComponent(loc.tree + "/" + loc.rel) + "&sha=" + encodeURIComponent(sha)).then(d => {
      if (p.loc !== loc) return;
      p.chg = sha;
      const top = p.body.scrollTop, md = changeArticle(d, loc, k);
      p.body.innerHTML = ""; p.body.appendChild(md); renderMermaid(k, md); applyMeasure(k); lineNumbers(k); p.body.scrollTop = top;
      const bar = $(".chgbar", p.el); bar.hidden = false;
      const what = sha === "worktree" ? "未提交的改动：磁盘上的当前版本，相对最近一次提交的新增与删除已标出（只读）" : `变更 <code>${esc(sha.slice(0, 7))}</code>：这次提交后的版本，新增与删除已标出（只读）`;
      bar.innerHTML = `<span>${what}</span><button data-chg="" data-pane="${k}">退出变更视图</button>`;
      crumb(k, loc); V.emit("rendered", k, false); if (k === tocK()) toc(); repaintHist(k);
    }).catch(() => { if (p.loc === loc) V.toast("这次提交的改动读不出来"); });
  }

  /* ---- clicks, keys, status ---- */
  function paintStar(k) {
    const b = $('[data-t="star"]', P[k].el), loc = P[k].loc, on = !!(loc && loc.kind === "doc" && V.isStar(keyOf(loc)));
    b.classList.toggle("star-on", on); b.dataset.tip = on ? "取消星标" : "加星标";
  }
  V.on("stars", () => ["A", "B"].forEach(paintStar));
  V.click(".cite[data-ref]", (el, e) => follow(el, e));
  V.click(".md a[data-rel]", (el, e) => {
    hideTip(); const k = V.paneOf(el);
    V.nav(e.shiftKey ? (k === "A" ? "B" : "A") : k, { kind: "doc", tree: el.dataset.tree, rel: el.dataset.rel, line: +el.dataset.line || 0 });
  });
  V.click(".md a[data-hash]", el => {
    const k = V.paneOf(el), h = $$("h1,h2,h3,h4", P[k].body).find(x => x.id === el.dataset.hash || slug(x.textContent) === el.dataset.hash);
    if (h) jumpTo(k, h, true);
  });
  V.click(".md a.broken", () => V.toast("这个链接的目标在 dev_root 和知识库里都找不到"));
  V.click("[data-anc]", el => {
    const loc = P[V.paneOf(el)].loc, s = slug(el.parentElement.textContent);
    V.copy(`${loc.rel.split("/").slice(-2).join("/")}#${s}`, `已复制 ${loc.rel.split("/").pop()}#${s}`);
  });
  V.click("[data-fmx]", el => {
    const tb = el.parentElement.nextElementSibling, open = tb.hidden;
    tb.hidden = !open; el.setAttribute("aria-expanded", open); V.emit("content", V.paneOf(el));
  });
  V.click("[data-stale]", el => { const k = V.paneOf(el); $(".stale", P[k].el).classList.remove("on"); V.rerender(k); });
  V.click("[data-chg]", el => { if (!el.closest("#histPop")) V.closePops(); changeView(el.dataset.pane, el.dataset.chg); });
  V.click('.phd [data-t="star"]', el => { const loc = P[V.paneOf(el)].loc; if (loc && loc.kind === "doc") V.toggleStar(keyOf(loc), el); });
  V.click('.phd [data-t="gitweb"]', el => {
    const l = P[V.paneOf(el)].loc; if (!l || l.kind !== "doc") return;
    if (l.tree === "ext") return V.toast("外部目录的文档不在 gitweb 的仓库列表里");
    window.open(`${V.GITWEB}?p=${l.tree === "kb" ? "knowledge" : "dev-workflow"};a=blob;f=${encodeURIComponent(l.rel)};hb=HEAD`, "_blank", "noopener");
  });
  V.click('.phd [data-t="hist"]', el => (V.isPop("histPop") ? V.closePops() : histPop(V.paneOf(el), el)));
  V.click('.phd [data-t="split"]', () => V.setSplit(!V.isSplit()));   // B keeps what it last showed, or waits empty
  V.click('.phd [data-t="close"]', () => V.setSplit(false));
  V.hotkey("s", () => { const k = V.readingK(); if (!k) return false; V.toggleStar(keyOf(P[k].loc), $('[data-t="star"]', P[k].el)); });
  V.hotkey("\\", () => V.setSplit(!V.isSplit()));
  V.on("split", () => toc());
  V.on("blank", k => { const p = P[k]; p.doc = null; p.el.classList.add("blank"); p.body.innerHTML = BLANK; $(".ppath", p.el).innerHTML = ""; });
  V.click('.phd [data-t="mirror"]', el => { const k = V.paneOf(el), l = P[k].loc; if (l && l.kind === "doc") V.nav(V.other(k), Object.assign({}, l, { xid: null, line: 0 })); });
  V.on("theme", () => {
    if (window.mermaid) window.mermaid.initialize({ startOnLoad: false, theme: V.isDark() ? "dark" : "default" });
    ["A", "B"].forEach(k => { if (shown(k) && P[k].doc && $(".mermaid", P[k].body)) V.rerender(k); });
  });
  V.on("tick", () => ["A", "B"].forEach(k => {
    const p = P[k], loc = p.loc;
    if (!shown(k) || !loc || loc.kind !== "doc" || !p.doc || p.doc.err) return;
    V.json("/api/rev?path=" + encodeURIComponent(loc.tree + "/" + loc.rel))
      .then(d => { if (d.mtime && d.mtime > p.doc.mtime + 1e-3 && p.loc === loc) $(".stale", p.el).classList.add("on"); }).catch(() => {});
  }));
  V.statusFns.doc = () => {
    const p = P[V.focus]; if (!p.loc || p.loc.kind !== "doc") return "";
    const b = p.body, max = b.scrollHeight - b.clientHeight, pct = max > 0 ? Math.round(b.scrollTop / max * 100) : 100;
    const mins = Math.max(1, Math.round((p.chars || 0) / 500)), keys = $(".find.on", p.el) ? "↵ 下一个 · ⇧↵ 上一个 · esc 关闭" : "f 查找 · h 钉词 · [ ] 后退前进 · \\ 对照";
    return `<span><b>${esc(p.loc.rel.split("/").pop())}</b>${V.isSplit() ? `　${V.focus} 栏` : ""}</span>`
      + `<span>${((p.chars || 0) / 1000).toFixed(1)}k 字，约 ${mins} 分钟</span><span>${pct}%<span class="prog"><i style="width:${pct}%"></i></span></span>`
      + `<span class="sp"></span><span>${keys}</span>${V.stamp()}`;
  };
})(V2);
