/* status viewer v2 — search: ⌘K quick open over docs, cards and Fact blocks (not limited by the project
   scope), and the full-text search view (limited by it), with search history. */
"use strict";
(function (V) {
  const { $, $$, esc } = V;

  /* ---- candidates ---- */
  const facts = { list: [], at: 0, loading: null };
  function factsOf(rel, src) {
    const blocks = SV.factBlocks(src), card = rel.split("/")[0] + " " + rel.split("/")[1].slice(0, 3);
    return Object.keys(blocks).map(id => ({ k: "fact", tree: "dev", rel, id, label: `${id} ${SV.factGist(blocks[id]).slice(0, 80)}`, sub: card, mtime: V.D.mtime.dev[rel] || 0 }));
  }
  function loadFacts() {   // every card's "### Fact-n" first lines, re-read when the dev tree changes
    if (facts.at === V.D.at || facts.loading) return facts.loading || Promise.resolve();
    const files = V.D.tree.dev.map(x => x.path).filter(p => /^[^/]+\/\d{3}-[^/]+\/facts\.md$/.test(p));
    // four at a time: the stdlib server's listen backlog is small, and a burst of ~30 requests gets connections reset
    const all = [], queue = files.slice(), worker = () => {
      const rel = queue.shift(); if (!rel) return Promise.resolve();
      return V.api("/raw/dev/" + rel).then(r => r.text()).then(src => { all.push(...factsOf(rel, src)); }).catch(() => {}).then(worker);
    };
    facts.loading = Promise.all([1, 2, 3, 4].map(worker))
      .then(() => { facts.list = all; facts.at = V.D.at; facts.loading = null; if (!$("#qo").hidden) render(); });
    return facts.loading;
  }
  const docItem = (tree, rel, mtime) => ({ k: "doc", tree, rel, mtime, label: (tree === "kb" ? "kb/" : "") + rel });
  const docs = () => ["dev", "kb"].reduce((a, tree) => a.concat(V.D.tree[tree].map(x => docItem(tree, x.path, x.mtime))), []);
  const navRows = () => [{ k: "go", label: "看板", sub: "所有卡片", words: "board" }, { k: "recent", label: "最近提交", sub: "dev_root 的提交", words: "recent commits log" }]
    .concat(V.GITWEB ? [{ k: "ext", label: "浏览代码", sub: "gitweb，新标签页", words: "gitweb code" }] : []);

  /* ---- quick open ---- */
  let rows = [], sel = 0;
  function hl(L, idx, a, b) { const set = new Set(idx); return [...L.slice(a, b)].map((ch, i) => (set.has(i + a) ? `<b>${esc(ch)}</b>` : esc(ch))).join(""); }
  function rowHTML(r, i) {
    const it = r.it, L = it.label, idx = r.idx || [], sp = L.indexOf(" "), cut = L.lastIndexOf("/") + 1;
    const two = (a, b, cls) => `<span class="qn">${a}</span><span class="qd${cls || ""}">${b}</span>`;
    const main = it.k === "doc" ? two(hl(L, idx, cut, L.length), hl(L, idx, 0, Math.max(0, cut - 1)))
      : it.k === "fact" ? two(hl(L, idx, 0, sp), hl(L, idx, sp + 1, L.length), " qf2")
      : it.k === "card" ? two(hl(L, idx, sp + 1, L.length), hl(L, idx, 0, sp) + "　" + esc(it.c.st))
      : two(esc(L), esc(it.sub || ""));
    const em = it.k === "doc" ? V.ago(it.mtime) : it.k === "fact" ? it.sub : it.k === "search" ? "⌘↵" : "";
    return `<button class="qr ${i === sel ? "sel" : ""} ${it.k === "search" ? "qfull" : ""}" data-q="${i}">${main}<em>${esc(em)}</em></button>`;
  }
  function emptyGroups() {
    const recent = V.recent.list("opened").slice(0, 8).map(key => {
      const i = key.indexOf(":"), tree = key.slice(0, i), rel = key.slice(i + 1), mt = V.D.mtime[tree][rel];
      return mt != null ? { it: docItem(tree, rel, mt) } : null;
    }).filter(Boolean);
    const seen = new Set(recent.map(r => r.it.tree + ":" + r.it.rel));
    const newest = docs().filter(d => !seen.has(d.tree + ":" + d.rel)).sort((a, b) => b.mtime - a.mtime).slice(0, 40).map(it => ({ it }));
    const hist = V.recent.list("search").slice(0, 5).map(s => ({ it: { k: "search", label: "搜索「" + s + "」", q: s } }));
    return [["", navRows().map(it => ({ it }))], ["最近打开", recent], ["最近搜索", hist], ["最近修改", newest]];
  }
  function queryGroups(q) {
    // ties go to the most recently changed; cards and Fact blocks match each term as a contiguous run, an exact id leads
    const score = (q, list, txt, ns, bonus) => list.map(it => {
      const m = SV.matchScore(q, txt(it), ns ? ns(it) : 0);
      return m.hit ? { it, idx: m.idx, sc: m.score + (bonus ? bonus(it) : 0) } : null;
    }).filter(Boolean).sort((a, b) => b.sc - a.sc || (b.it.mtime || 0) - (a.it.mtime || 0));
    const exact = q.split(/\s+/).map(t => (t.charAt(0) === "=" ? t : "=" + t)).join(" "), ql = q.toLowerCase();
    const label = it => it.label;
    const cards = V.D.cards.map(c => ({ k: "card", c, label: `${c.id} ${c.slug}`, mtime: V.D.mtime.dev[c.dir + "/design.md"] || 0 }));
    if (!facts.list.length) loadFacts();
    return [["", score(q, navRows(), it => it.label + " " + it.words)], ["文档", score(q, docs(), label, it => it.label.lastIndexOf("/") + 1).slice(0, 40)],
      ["卡片", score(exact, cards, label, 0, it => (it.c.n === ql || it.c.id === ql ? 100 : 0)).slice(0, 8)],
      ["Fact", score(exact, facts.list, label, 0, it => (it.id.toLowerCase() === ql ? 100 : 0)).slice(0, 6)],
      ["", [{ it: { k: "search", label: "全文搜索「" + q + "」", q } }]]];
  }
  function render() {
    const q = $("#qIn").value.trim();
    rows = []; let h = "";
    (q ? queryGroups(q) : emptyGroups()).forEach(([g, rs]) => {
      if (!rs.length) return;
      if (g) h += `<div class="qg">${g}</div>`;
      rs.forEach(r => { h += rowHTML(r, rows.length); rows.push(r); });
    });
    sel = Math.min(sel, Math.max(0, rows.length - 1));
    $("#qList").innerHTML = h || `<div class="qnone">没有找到「${esc(q)}」。试试卡号，比如 039，或者 Fact-12。</div>`;
    const s = $("#qList .qr.sel"); if (s) s.scrollIntoView({ block: "nearest" });
  }
  const paintSel = () => $$("#qList .qr").forEach((b, i) => { b.classList.toggle("sel", i === sel); if (i === sel) b.scrollIntoView({ block: "nearest" }); });
  let back = null;   // where the focus returns when quick open closes
  function open() {
    back = document.activeElement; $("#qo").hidden = false; $("#qIn").value = ""; sel = 0;
    render(); loadFacts(); setTimeout(() => $("#qIn").focus(), 10);
  }
  const close = () => {
    $("#qo").hidden = true; $("#qIn").blur();
    if (back && back.isConnected && back !== document.body) back.focus({ preventScroll: true });
    back = null;
  };
  function choose(i, e) {
    const r = rows[i]; if (!r) return;
    close();
    const it = r.it, side = V.target(e);
    if (it.k === "go") return V.goBoard(e);
    if (it.k === "recent") return V.nav(side, { kind: "recent" });
    if (it.k === "ext") return window.open(V.GITWEB, "_blank", "noopener");
    if (it.k === "search") return fullSearch(it.q, e);
    if (it.k === "card") {
      if (V.view === "board" && !e.shiftKey) return V.revealCard(it.c);
      const d = V.mainDoc(it.c); return d ? V.nav(side, { kind: "doc", tree: "dev", rel: d }) : V.toast("这张卡没有文档");
    }
    V.nav(side, { kind: "doc", tree: it.tree, rel: it.rel, xid: it.id });
  }
  function fullSearch(q, e) { q = (q || "").trim(); if (!q) return; V.recent.push("search", q, 20); V.nav(V.target(e), { kind: "search", q }); }
  V.on("init", () => {
    $("#qIn").addEventListener("input", () => { sel = 0; render(); });
    $("#qIn").addEventListener("keydown", e => {
      e.stopPropagation();
      const mod = e.metaKey || e.ctrlKey;
      if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(rows.length - 1, sel + 1); paintSel(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); paintSel(); }
      else if (e.key === "Enter" && mod) { e.preventDefault(); const q = $("#qIn").value.trim(); if (q) { close(); fullSearch(q, e); } }   // ⇧ puts it in the other pane
      else if (e.key === "Enter") { e.preventDefault(); choose(sel, e); }
      else if (e.key === "Escape" || (mod && e.key.toLowerCase() === "k")) { e.preventDefault(); close(); }
    });
    $("#qList").addEventListener("mousemove", e => { const b = e.target.closest("[data-q]"); if (b && +b.dataset.q !== sel) { sel = +b.dataset.q; paintSel(); } });
    $("#qo").addEventListener("click", e => { if (e.target.id === "qo") close(); });
  });
  V.click("[data-qclear]", (el, e) => { e.stopPropagation(); V.recent.clear(); render(); V.toast("历史已清空"); });
  V.click("#qList [data-q]", (el, e) => choose(+el.dataset.q, e));
  V.click("#qBtn", open);
  V.chord.k = () => ($("#qo").hidden ? open() : close());
  V.layer(90, () => !$("#qo").hidden, close);

  /* ---- full-text search view ---- */
  function hlq(text, q) {   // escape first, then mark each case-insensitive occurrence of the (escaped) query
    const e = esc(text), el = e.toLowerCase(), ql = esc(q).toLowerCase(); if (!ql) return e;
    let out = "", i = 0, j;
    while ((j = el.indexOf(ql, i)) !== -1) { out += e.slice(i, j) + "<mark>" + e.slice(j, j + ql.length) + "</mark>"; i = j + ql.length; }
    return out + e.slice(i);
  }
  function shell(k, q) {
    const hist = V.recent.list("search").map(s => `<option value="${esc(s)}">`).join("");
    return `<div class="phd"><button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button>` + V.paneHead(k)
      + `<div class="ppath"><bdi>搜索 / <b>${esc(q || "")}</b></bdi></div>`
      + `<button class="ib" data-t="find" data-tip="在结果里查找" data-key="f" aria-label="在结果里查找">${V.I.find}</button>`
      + `<button class="ib" data-goboard="1" data-tip="回看板" aria-label="回看板">${V.I.grid}</button>${V.paneEnd(k)}</div>`
      + `<div class="sbar"><input id="sIn" type="search" list="sHist" placeholder="全文搜索 dev_root 与知识库（至少两个字）" value="${esc(q || "")}" autocomplete="off" aria-label="全文搜索">`
      + `<datalist id="sHist">${hist}</datalist></div><div class="smeta"></div><div class="sres scroll"></div>`;
  }
  function resultsHTML(groups, q) {
    const attrs = g => `data-shit data-tree="${g.tree}" data-rel="${esc(g.path)}"`;
    return groups.map((g, i) => `<div class="sfile" data-g="${i}"${sideHide.has(g.tree + ":" + g.path) ? " hidden" : ""}><h3><button ${attrs(g)}>${esc((g.tree === "kb" ? "知识库/" : "") + g.path)}</button><em>${g.hits.length}</em></h3>`
      + g.hits.map(h => `<button class="shit" ${attrs(g)} data-line="${h.line || 0}"><i>${h.line ? ":" + h.line : ""}</i><span>${hlq(h.snippet || "", q)}</span></button>`).join("")
      + "</div>").join("");
  }
  /* ---- the side column under a search: the files hit, to jump to or hide ---- */
  let sideGroups = [], sideQ = null;
  const sideHide = new Set();   // files hidden from this query's results; a new query starts with none
  V.searchToc = () => {
    $("#sideT").textContent = "命中文件"; $("#sticks").innerHTML = "";
    $("#sbody").innerHTML = sideGroups.length ? '<div class="toc sfl">' + sideGroups.map((g, i) => {
      const key = g.tree + ":" + g.path, name = g.path.split("/").pop(), where = (g.tree === "kb" ? "知识库/" : "") + g.path;
      return `<div class="sfr"><input type="checkbox" data-sfh="${esc(key)}" ${sideHide.has(key) ? "" : "checked"} aria-label="显示 ${esc(name)} 的命中">`
        + `<button class="ti" data-sfj="${i}" data-tip="${esc(where)}"><span class="tl">${esc(name)}</span><em>${g.hits.length}</em></button></div>`;
    }).join("") + "</div>" : '<div class="hint">没有命中文件</div>';
  };
  V.on("search-files", groups => { sideGroups = groups; if (V.view === "search") V.searchToc(); });
  V.click("[data-sfj]", el => {
    const f = $(`#search .sfile[data-g="${el.dataset.sfj}"]`), r = $("#search .sres"); if (!f || !r) return;
    if (f.hidden) { f.hidden = false; sideHide.delete(f.querySelector("[data-shit]").dataset.tree + ":" + f.querySelector("[data-shit]").dataset.rel); V.searchToc(); }
    r.scrollTo({ top: f.offsetTop - r.offsetTop - 8, behavior: V.RM ? "auto" : "smooth" });
  });
  document.addEventListener("change", e => {
    const key = e.target.dataset && e.target.dataset.sfh; if (!key) return;
    if (e.target.checked) sideHide.delete(key); else sideHide.add(key);
    sideGroups.forEach((g, i) => { const f = $(`#search .sfile[data-g="${i}"]`); if (f) f.hidden = sideHide.has(g.tree + ":" + g.path); });
    V.emit("content", V.hostOf("search"));
  });
  V.views.search = (k, loc) => {
    if (sideQ !== loc.q) { sideHide.clear(); sideQ = loc.q; } sideGroups = [];
    const el = $("#search");
    el.innerHTML = shell(k, loc.q);
    $("#sIn").addEventListener("keydown", e => {
      if (e.key === "Enter") { e.preventDefault(); fullSearch(e.target.value); }
      else if (e.key === "Escape") { e.stopPropagation(); e.target.blur(); }
    });
    const meta = $(".smeta", el), res = $(".sres", el), scope = V.scope ? "，范围 " + V.scope : "";
    if (!loc.q || loc.q.length < 2) {
      meta.textContent = "输入后按 ↵ 搜索；⇧ 点结果在右栏打开。"; setTimeout(() => $("#sIn").focus(), 10); V.status(); return;
    }
    meta.textContent = "搜索中…";
    const y = loc.y || 0;
    V.json("/api/search?q=" + encodeURIComponent(loc.q) + "&project=" + encodeURIComponent(V.scope)).then(d => {
      if (V.P[k].loc !== loc) return;
      if (d.note) { meta.textContent = d.note; res.innerHTML = ""; return; }
      const groups = SV.groupHits(d.hits || []);
      meta.textContent = `${(d.hits || []).length}${d.truncated ? "+" : ""} 条命中，${groups.length} 个文件${scope}`;
      res.innerHTML = resultsHTML(groups, loc.q) || `<div class="qnone">没有找到「${esc(loc.q)}」${V.scope ? "（范围 " + esc(V.scope) + "）" : ""}。</div>`;
      res.scrollTop = y;
      V.emit("rendered", k, true); V.emit("search-files", groups);
      V.status();
    }).catch(e => { if (V.P[k].loc === loc) { meta.textContent = ""; res.innerHTML = `<div class="derr"><b>搜索失败</b><br>${esc(e.message)}</div>`; } });
    V.status();
  };
  V.statusFns.search = () => `<span><b>搜索</b>　${esc((V.P[V.navPane()].loc || {}).q || "")}</span><span>↵ 打开 · ⇧ 点击在另一栏打开 · f 在结果里查找</span><span class="sp"></span>${V.stamp()}`;
  V.click("[data-shit]", (el, e) => V.nav(e.shiftKey ? V.other(V.paneOf(el)) : V.paneOf(el), { kind: "doc", tree: el.dataset.tree, rel: el.dataset.rel, line: +el.dataset.line || 0 }));
  V.hotkey("/", () => {
    const at = V.hostOf("search");
    if (V.kindOf(at) === "search" && (at === "A" || V.isSplit()) && $("#sIn")) { V.setFocus(at); const i = $("#sIn"); i.focus(); i.select(); return; }
    V.nav(V.target(), { kind: "search", q: "" });
  });
  V.on("scope", () => { if (!$("#search").hidden) V.rerender(V.hostOf("search")); });
  V.on("leave", (k, loc) => { const r = $("#search .sres"); if (loc.kind === "search" && r) loc.y = r.scrollTop; });   // back to the results lands where they were left
})(V2);
