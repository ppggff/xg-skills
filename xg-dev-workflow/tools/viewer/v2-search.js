/* status viewer v2 — search: ⌘K quick open over docs, cards and Fact blocks (not limited by the project
   scope), and the full-text search view (limited by it), with search history. */
"use strict";
(function (V) {
  const { $, $$, esc } = V;

  /* ---- candidates ---- */
  const facts = { list: [], at: 0, loading: null };
  function factsOf(rel, src) {
    const blocks = SV.factBlocks(src), card = rel.split("/")[0] + " " + rel.split("/")[1].slice(0, 3);
    return Object.keys(blocks).map(id => ({ k: "fact", tree: "dev", rel, id, label: `${id} ${SV.factGist(blocks[id]).slice(0, 80)}`, sub: card }));
  }
  function loadFacts() {   // every card's "### Fact-n" first lines, re-read when the dev tree changes
    if (facts.at === V.D.at || facts.loading) return facts.loading || Promise.resolve();
    const files = V.D.tree.dev.map(x => x.path).filter(p => /^[^/]+\/\d{3}-[^/]+\/facts\.md$/.test(p));
    facts.loading = Promise.all(files.map(rel => V.api("/raw/dev/" + rel).then(r => r.text()).then(src => factsOf(rel, src)).catch(() => [])))
      .then(all => { facts.list = [].concat(...all); facts.at = V.D.at; facts.loading = null; if (!$("#qo").hidden) render(); });
    return facts.loading;
  }
  const docItem = (tree, rel, mtime) => ({ k: "doc", tree, rel, mtime, label: (tree === "kb" ? "kb/" : "") + rel });
  const docs = () => ["dev", "kb"].reduce((a, tree) => a.concat(V.D.tree[tree].map(x => docItem(tree, x.path, x.mtime))), []);
  const navRows = () => [{ k: "go", label: "看板", sub: "所有卡片" }].concat(V.GITWEB ? [{ k: "ext", label: "浏览代码", sub: "gitweb，新标签页" }] : []);

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
    const recent = V.recent.list("opened").slice(0, 6).map(key => {
      const i = key.indexOf(":"), tree = key.slice(0, i), rel = key.slice(i + 1), mt = V.D.mtime[tree][rel];
      return mt != null ? { it: docItem(tree, rel, mt) } : null;
    }).filter(Boolean);
    const seen = new Set(recent.map(r => r.it.tree + ":" + r.it.rel));
    const newest = docs().filter(d => !seen.has(d.tree + ":" + d.rel)).sort((a, b) => b.mtime - a.mtime).slice(0, 40).map(it => ({ it }));
    const hist = V.recent.list("search").slice(0, 5).map(s => ({ it: { k: "search", label: "搜索「" + s + "」", q: s } }));
    return [["", navRows().map(it => ({ it }))], ["最近打开", recent], ["最近搜索", hist, true], ["最近修改", newest]];
  }
  function queryGroups(q) {
    const score = (list, txt, ns) => list.map(it => { const m = SV.matchScore(q, txt(it), ns ? ns(it) : 0); return m.hit ? { it, idx: m.idx, sc: m.score } : null; })
      .filter(Boolean).sort((a, b) => b.sc - a.sc);
    const label = it => it.label, cards = V.D.cards.map(c => ({ k: "card", c, label: `${c.id} ${c.slug}` }));
    if (!facts.list.length) loadFacts();
    return [["", score(navRows(), label)], ["文档", score(docs(), label, it => it.label.lastIndexOf("/") + 1).slice(0, 12)],
      ["卡片", score(cards, label).slice(0, 8)], ["Fact", score(facts.list, label).slice(0, 6)],
      ["", [{ it: { k: "search", label: "全文搜索「" + q + "」", q } }]]];
  }
  function render() {
    const q = $("#qIn").value.trim();
    rows = []; let h = "";
    (q ? queryGroups(q) : emptyGroups()).forEach(([g, rs, clear]) => {
      if (!rs.length) return;
      if (g) h += `<div class="qg">${g}${clear ? '<button data-qclear data-tip="清空最近打开、搜索与查找的历史">清空</button>' : ""}</div>`;
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
    const it = r.it, side = e && e.shiftKey ? "B" : "A";
    if (it.k === "go") return V.nav("A", { kind: "board" });
    if (it.k === "ext") return window.open(V.GITWEB, "_blank", "noopener");
    if (it.k === "search") return fullSearch(it.q);
    if (it.k === "card") {
      if (V.view === "board" && !e.shiftKey) return V.revealCard(it.c);
      const d = V.mainDoc(it.c); return d ? V.nav(side, { kind: "doc", tree: "dev", rel: d }) : V.toast("这张卡没有文档");
    }
    V.nav(side, { kind: "doc", tree: it.tree, rel: it.rel, xid: it.id });
  }
  function fullSearch(q) { q = (q || "").trim(); if (!q) return; V.recent.push("search", q, 20); V.nav("A", { kind: "search", q }); }
  V.on("init", () => {
    $("#qIn").addEventListener("input", () => { sel = 0; render(); });
    $("#qIn").addEventListener("keydown", e => {
      e.stopPropagation();
      const mod = e.metaKey || e.ctrlKey;
      if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(rows.length - 1, sel + 1); paintSel(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); paintSel(); }
      else if (e.key === "Enter" && mod) { e.preventDefault(); const q = $("#qIn").value.trim(); if (q) { close(); fullSearch(q); } }
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
  function shell(q) {
    const hist = V.recent.list("search").map(s => `<option value="${esc(s)}">`).join("");
    return `<div class="phd"><button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button>`
      + `<div class="ppath"><bdi>搜索 / <b>${esc(q || "")}</b></bdi></div>`
      + `<button class="ib" data-goboard="1" data-tip="回看板" aria-label="回看板">${V.I.grid}</button></div>`
      + `<div class="sbar"><input id="sIn" type="search" list="sHist" placeholder="全文搜索 dev_root 与知识库（至少两个字）" value="${esc(q || "")}" autocomplete="off" aria-label="全文搜索">`
      + `<datalist id="sHist">${hist}</datalist></div><div class="smeta"></div><div class="sres scroll"></div>`;
  }
  function resultsHTML(groups, q) {
    const attrs = g => `data-shit data-tree="${g.tree}" data-rel="${esc(g.path)}"`;
    return groups.map(g => `<div class="sfile"><h3><button ${attrs(g)}>${esc((g.tree === "kb" ? "知识库/" : "") + g.path)}</button><em>${g.hits.length}</em></h3>`
      + g.hits.map(h => `<button class="shit" ${attrs(g)} data-line="${h.line || 0}"><i>${h.line ? ":" + h.line : ""}</i><span>${hlq(h.snippet || "", q)}</span></button>`).join("")
      + "</div>").join("");
  }
  V.views.search = (k, loc) => {
    const el = $("#search");
    el.innerHTML = shell(loc.q);
    $("#sIn").addEventListener("keydown", e => {
      if (e.key === "Enter") { e.preventDefault(); fullSearch(e.target.value); }
      else if (e.key === "Escape") { e.stopPropagation(); e.target.blur(); }
    });
    const meta = $(".smeta", el), res = $(".sres", el), scope = V.scope ? "，范围 " + V.scope : "";
    if (!loc.q || loc.q.length < 2) {
      meta.textContent = "输入后按 ↵ 搜索；⇧ 点结果在右栏打开。"; setTimeout(() => $("#sIn").focus(), 10); V.status(); return;
    }
    meta.textContent = "搜索中…";
    V.json("/api/search?q=" + encodeURIComponent(loc.q) + "&project=" + encodeURIComponent(V.scope)).then(d => {
      if (V.P.A.loc !== loc) return;
      if (d.note) { meta.textContent = d.note; res.innerHTML = ""; return; }
      const groups = SV.groupHits(d.hits || []);
      meta.textContent = `${(d.hits || []).length}${d.truncated ? "+" : ""} 条命中，${groups.length} 个文件${scope}`;
      res.innerHTML = resultsHTML(groups, loc.q) || `<div class="qnone">没有找到「${esc(loc.q)}」${V.scope ? "（范围 " + esc(V.scope) + "）" : ""}。</div>`;
      V.status();
    }).catch(e => { if (V.P.A.loc === loc) { meta.textContent = ""; res.innerHTML = `<div class="derr"><b>搜索失败</b><br>${esc(e.message)}</div>`; } });
    V.status();
  };
  V.statusFns.search = () => `<span><b>搜索</b>　${esc((V.P.A.loc || {}).q || "")}</span><span>↵ 打开 · ⇧ 点击在右栏打开</span><span class="sp"></span>${V.stamp()}`;
  V.click("[data-shit]", (el, e) => V.nav(e.shiftKey ? "B" : "A", { kind: "doc", tree: el.dataset.tree, rel: el.dataset.rel, line: +el.dataset.line || 0 }));
  V.hotkey("/", () => {
    if (V.view === "search") { const i = $("#sIn"); i.focus(); i.select(); return; }
    V.nav("A", { kind: "search", q: "" });
  });
  V.on("scope", () => { if (V.view === "search") V.rerender("A"); });
})(V2);
