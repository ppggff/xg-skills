/* status viewer v2 — nav: project scope, the dev tree (organized by card) and the KB tree, per-section
   sort and one-click collapse, remembered folds, stars and the trail of recently opened docs. */
"use strict";
(function (V) {
  const { $, $$, esc } = V;
  const OPEN_ST = ["active", "blocked", "paused", "todo", "backlog", "unknown"];
  V.OPEN_ST = OPEN_ST;

  /* ---- fold state: user toggles persist (merged, so another tab's folds survive); reveals are session-only ---- */
  const openF = new Set(V.store.get("tree-open", ["dev", "kb"]));
  const reveal = new Set();
  let snap = { dev: null, kb: null };   // what one-click collapse closed, so a second click can restore it
  const isOpen = k => openF.has(k) || reveal.has(k);
  function toggleFold(k) {
    const was = isOpen(k);
    reveal.delete(k); if (was) openF.delete(k); else openF.add(k);
    V.store.set("tree-open", SV.mergeTreeOpen(V.store.get("tree-open", []), [k], was ? [] : [k]));
    snap[k.split(":")[0]] = null;
    render();
  }
  const sorts = Object.assign({ dev: { key: "name", dir: 1 }, kb: { key: "name", dir: 1 } }, V.store.get("tree-sort", {}));

  /* ---- stars ---- */
  let stars = V.store.get("stars", []);
  V.isStar = key => stars.some(x => x.key === key);
  V.toggleStar = (key, btn) => {
    if (!key) return; const on = !V.isStar(key);
    stars = on ? [{ key, t: Date.now() }].concat(stars.filter(x => x.key !== key)) : stars.filter(x => x.key !== key);
    V.store.set("stars", stars); render(); V.emit("stars");
    V.toast(on ? "已加星标，左上角的 ☆ 里找得到" : "已取消星标");
    if (!on || !btn || V.RM) return;
    const r = btn.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    for (let i = 0; i < 7; i++) {
      const d = document.createElement("i"), a = i / 7 * Math.PI * 2 - Math.PI / 2;
      d.className = "spark"; d.style.left = cx - 2 + "px"; d.style.top = cy - 2 + "px"; document.body.appendChild(d);
      d.animate([{ transform: "translate(0,0) scale(1)", opacity: 1 }, { transform: `translate(${Math.cos(a) * 16}px,${Math.sin(a) * 16}px) scale(.3)`, opacity: 0 }],
        { duration: 480, easing: "cubic-bezier(.2,.8,.2,1)" }).onfinish = () => d.remove();
    }
    btn.animate([{ transform: "scale(1)" }, { transform: "scale(1.35)" }, { transform: "scale(1)" }], { duration: 320, easing: "ease-out" });
  };
  const docName = key => {   // "<name><card tag>" for a tree:rel key, as the star and trail lists show it
    const i = key.indexOf(":"), tree = key.slice(0, i), rel = key.slice(i + 1), c = V.cardOfPath(tree, rel);
    const nm = c ? rel.slice(c.dir.length + 1) : rel;
    return `${esc(nm)}<i class="trc">${c ? esc(c.p + " " + c.n) : tree === "kb" ? "知识库" : ""}</i>`;
  };
  function starPop(btn) {
    V.pop("starPop", `<div class="pt">星标文档</div>` + (stars.length ? stars.map(x => `<button class="sta" data-open="${esc(x.key)}"><span class="s">★</span><span>${docName(x.key)}</span><em>${V.relT(x.t)}</em><u data-unstar="${esc(x.key)}" data-tip="取消星标">×</u></button>`).join("")
      : '<div class="qnone">还没有星标。打开文档后点右上角的 ☆，或按 s。</div>'), btn);
  }
  function trailPop(btn) {
    const items = V.recent.list("opened").slice(0, 10);
    V.pop("trailPop", `<div class="pt">足迹</div>` + (items.length ? items.map(key => {
      const pct = V.readPct ? V.readPct(key) : 0;
      return `<button class="li" data-open="${esc(key)}"><span>${docName(key)}</span><em>${pct ? `读到 ${pct}%` : ""}</em></button>`;
    }).join("") : '<div class="qnone">还没有打开过文档</div>'), btn);
  }

  /* ---- render ---- */
  const curKeys = () => ["A", "B"].map(k => V.P[k].loc).filter(l => l && l.kind === "doc" && V.view === "doc").map(l => l.tree + ":" + l.rel);
  const row = (d, cls, fold, name, extra, attr) => `<button class="tr ${cls}" style="--d:${d}" ${attr}><span class="cv">${fold ? "<i></i>" : ""}</span><span class="nm">${name}</span>${extra || ""}</button>`;
  function fileRow(tree, rel, name, d, cur) {
    const key = tree + ":" + rel, mt = V.D.mtime[tree][rel];
    return row(d, cur.includes(key) ? "cur" : "", 0, esc(name), (V.isStar(key) ? '<em class="star">★</em>' : "") + `<em>${V.ago(mt)}</em>`, `data-open="${esc(key)}"`);
  }
  function nodeRows(tree, node, base, d, cmp, cur, filesFirst) {
    let h = "";
    const dirs = Object.keys(node.dirs).map(n => ({ name: n, mtime: node.dirs[n].mtime, node: node.dirs[n] })).sort(cmp);
    const dirRows = () => dirs.forEach(e => {
      const k = tree + ":" + base + e.name, open = isOpen(k) || cur.some(c => c.startsWith(k + "/"));
      h += row(d, "dir " + (open ? "open" : ""), 1, esc(e.name), "", `data-fold-k="${esc(k)}"`);
      if (open) h += nodeRows(tree, e.node, base + e.name + "/", d + 1, cmp, cur, filesFirst);
    });
    if (!filesFirst) dirRows();
    node.files.slice().sort(cmp).forEach(f => { h += fileRow(tree, f.path, f.name, d, cur); });
    if (filesFirst) dirRows();
    return h;
  }
  function cardRows(c, d, cmp, cur) {
    const k = "dev:" + c.dir, inCur = cur.some(x => x.startsWith(k + "/")), open = isOpen(k) || inCur;
    let h = row(d, "dir " + (open ? "open" : ""), 1, esc(c.dirName), "", `data-fold-k="${esc(k)}" data-tip="${esc(c.dir + " · " + c.st)}"`);
    if (!open) return h;
    const files = V.docsOf(c).map(x => ({ path: x.rel, mtime: x.mtime })), node = SV.buildTree(files.map(f => ({ path: f.path.slice(c.dir.length + 1), mtime: f.mtime })));
    const fix = n => { n.files.forEach(f => { f.path = c.dir + "/" + f.path; }); Object.values(n.dirs).forEach(fix); }; fix(node);
    const cmpD = (a, b) => sorts.dev.key === "name" ? (b.name === "design.md") - (a.name === "design.md") || cmp(a, b) : cmp(a, b);
    return h + nodeRows("dev", node, c.dir + "/", d + 1, cmpD, cur, true);
  }
  const ctl = t => `<span class="tc" data-tsort="${t}" data-tip="排序：名称 / 修改时间">${sorts[t].key === "mtime" ? "T" : "A"}</span><span class="tc" data-tdir="${t}" data-tip="排序方向">${sorts[t].dir > 0 ? "↑" : "↓"}</span><span class="tc ${snap[t] ? "on" : ""}" data-tcol="${t}" data-tip="${snap[t] ? "恢复折叠前的展开" : "折叠这一区的全部文件夹"}">F</span>`;
  function render() {
    const tree = $("#tree"), top = tree.scrollTop, cur = curKeys(), D = V.D;
    const cards = D.cards.filter(c => V.inScope(c.p));
    let h = `<button class="tr top ${V.view === "board" ? "cur" : ""}" style="--d:0" data-goboard="1"><span class="cv">${V.I.grid}</span><span class="nm">看板</span><em>${cards.length}</em></button>`;
    if (V.GITWEB) h += `<a class="tr top" style="--d:0" href="${esc(V.GITWEB)}" target="_blank" rel="noopener" data-tip="浏览代码：gitweb，在新标签页打开"><span class="cv">${V.I.code}</span><span class="nm">浏览代码</span></a>`;
    // dev: projects → open cards → closed (n) → the project's other files
    const dc = SV.sortCmp(sorts.dev.key, sorts.dev.dir), devOpen = isOpen("dev");
    h += `<div class="tsec"><button class="nm" data-fold-k="dev">dev_root</button>${ctl("dev")}</div>`;
    if (devOpen) {
      const devItems = D.tree.dev.filter(it => it.path.indexOf("/") < 0 || V.inScope(it.path.split("/")[0]));
      const root = SV.buildTree(devItems.filter(it => !V.cardOfPath("dev", it.path)));
      const projs = [...new Set(devItems.map(it => it.path.split("/")[0]).filter((p, i, a) => devItems.some(it => it.path.startsWith(p + "/"))))]
        .map(p => ({ name: p, mtime: Math.max(0, ...devItems.filter(it => it.path.startsWith(p + "/")).map(it => it.mtime)) })).sort(dc);
      const byNo = (a, b) => sorts.dev.key === "mtime" ? dc({ name: a.n, mtime: a.mt }, { name: b.n, mtime: b.mt }) : (b.n < a.n ? -1 : b.n > a.n ? 1 : 0) * sorts.dev.dir;
      projs.forEach(pj => {
        const k = "dev:" + pj.name, open = isOpen(k) || cur.some(c => c.startsWith(k + "/"));
        const pc = cards.filter(c => c.p === pj.name).map(c => Object.assign(c, { mt: D.mtime.dev[c.dir + "/design.md"] || 0 })).sort(byNo);
        const live = pc.filter(c => OPEN_ST.includes(c.st)), closed = pc.filter(c => !OPEN_ST.includes(c.st));
        h += row(0, "dir top " + (open ? "open" : ""), 1, esc(pj.name), "", `data-fold-k="${esc(k)}" data-tip="${esc(pj.name)}：进行中 ${live.length}，共 ${pc.length} 张卡"`);
        if (!open) return;
        live.forEach(c => { h += cardRows(c, 1, dc, cur); });
        if (closed.length) {
          const ek = "dev:" + pj.name + "/closed", eo = isOpen(ek) || closed.some(c => cur.some(x => x.startsWith("dev:" + c.dir + "/")));
          h += row(1, "dir grp " + (eo ? "open" : ""), 1, `closed (${closed.length})`, "", `data-fold-k="${esc(ek)}" data-tip="done 与 dropped 的卡"`);
          if (eo) closed.forEach(c => { h += cardRows(c, 2, dc, cur); });
        }
        if (root.dirs[pj.name]) h += nodeRows("dev", root.dirs[pj.name], pj.name + "/", 1, dc, cur, false);
      });
      root.files.slice().sort(dc).forEach(f => { h += fileRow("dev", f.path, f.name, 0, cur); });
    }
    // kb: the knowledge base, scoped to raw/<project> and wiki/<project>
    h += `<div class="tsec"><button class="nm" data-fold-k="kb">知识库</button>${ctl("kb")}</div>`;
    if (isOpen("kb")) {
      const kbItems = D.tree.kb.filter(it => { const s = it.path.split("/"); return s.length < 3 || V.inScope(s[1]); });
      h += nodeRows("kb", SV.buildTree(kbItems), "", 0, SV.sortCmp(sorts.kb.key, sorts.kb.dir), cur, false);
    }
    tree.innerHTML = h; tree.scrollTop = top;
    const cr = $("#tree .tr.cur:not([data-goboard])");
    if (cr && (cr.offsetTop < tree.scrollTop || cr.offsetTop > tree.scrollTop + tree.clientHeight - 30)) tree.scrollTop = cr.offsetTop - tree.clientHeight / 3;
  }
  function scopeBar() {
    const D = V.D;
    $("#scopeBar").innerHTML = `<span>范围</span><select id="scopeSel" aria-label="项目范围" data-tip="项目范围：作用于树、看板和全文搜索（⌘K 不受限）"><option value="">全部项目</option>${(D.projects || []).map(p => `<option ${p === V.scope ? "selected" : ""}>${esc(p)}</option>`).join("")}</select>`;
  }
  // opening a doc unfolds its ancestors for this session only — a programmatic expand is not a preference
  V.revealDoc = (tree, rel) => {
    const segs = rel.split("/"); reveal.add(tree);
    for (let i = 1; i < segs.length; i++) reveal.add(tree + ":" + segs.slice(0, i).join("/"));
    const c = V.cardOfPath(tree, rel); if (c && !OPEN_ST.includes(c.st)) reveal.add("dev:" + c.p + "/closed");
  };
  function collapse(t) {
    if (snap[t]) { snap[t].forEach(k => openF.add(k)); snap[t] = null; }
    else { snap[t] = [...openF].filter(k => k.startsWith(t + ":")); snap[t].forEach(k => openF.delete(k)); [...reveal].filter(k => k.startsWith(t + ":")).forEach(k => reveal.delete(k)); }
    V.store.set("tree-open", [...openF]); render();
  }

  V.click("[data-fold-k]", el => toggleFold(el.dataset.foldK));
  V.click("[data-tsort]", el => { const s = sorts[el.dataset.tsort]; s.key = s.key === "name" ? "mtime" : "name"; V.store.set("tree-sort", sorts); render(); });
  V.click("[data-tdir]", el => { const s = sorts[el.dataset.tdir]; s.dir = -s.dir; V.store.set("tree-sort", sorts); render(); });
  V.click("[data-tcol]", el => collapse(el.dataset.tcol));
  V.click("[data-unstar]", (el, e) => { e.stopPropagation(); V.toggleStar(el.dataset.unstar); starPop($("#starBtn")); });
  V.click("[data-open]", (el, e) => {
    V.closePops(); V.app.classList.remove("treepop");
    const key = el.dataset.open, i = key.indexOf(":");
    V.openDoc(key.slice(0, i), key.slice(i + 1), e);
  });
  V.click("#starBtn", el => (V.isPop("starPop") ? V.closePops() : starPop(el)));
  V.click("#trailBtn", el => (V.isPop("trailPop") ? V.closePops() : trailPop(el)));
  document.addEventListener("change", e => { if (e.target.id === "scopeSel") V.setScope(e.target.value); });
  ["data", "scope", "tree-show", "stars", "focus", "split"].forEach(ev => V.on(ev, () => { if (ev === "data") scopeBar(); render(); }));
  V.on("nav", (k, loc) => { if (loc.kind === "doc") V.revealDoc(loc.tree, loc.rel); render(); });
})(V2);
