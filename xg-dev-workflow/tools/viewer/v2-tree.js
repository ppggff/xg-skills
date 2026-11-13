/* status viewer v2 — nav: the dev tree (organized by card) and the KB tree, per-section
   sort and one-click collapse, remembered folds, stars and the trail of recently opened docs. */
"use strict";
(function (V) {
  const { $, $$, esc } = V;
  const OPEN_ST = ["active", "blocked", "paused", "todo", "backlog", "unknown"];
  V.OPEN_ST = OPEN_ST;

  /* ---- fold state: user toggles persist (merged, so another tab's folds survive); reveals are session-only ---- */
  const DEF_OPEN = ["todo", "dev", "kb"];
  const openF = new Set(V.store.get("tree-open", DEF_OPEN));
  if (!V.store.get("todo-sec", false)) { openF.add("todo"); V.store.set("todo-sec", true); V.store.set("tree-open", [...openF]); }   // the section is new: open once
  const reveal = new Set();
  let snap = { dev: null, kb: null, ext: null };   // what one-click collapse closed, so a second click can restore it
  const isOpen = k => openF.has(k) || reveal.has(k);
  function toggleFold(k) {
    const was = isOpen(k);
    reveal.delete(k); if (was) openF.delete(k); else openF.add(k);
    V.store.set("tree-open", SV.mergeTreeOpen(V.store.get("tree-open", DEF_OPEN), [k], was ? [] : [k]));
    snap[k.split(":")[0]] = null;
    render();
  }
  const sorts = Object.assign({ todo: { key: "name", dir: 1 }, dev: { key: "name", dir: 1 }, kb: { key: "name", dir: 1 }, ext: { key: "name", dir: 1 } }, V.store.get("tree-sort", {}));

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
    return `${esc(nm)}<i class="trc">${c ? esc(c.p + " " + c.n) : tree !== "dev" ? V.ROOT_NAME[tree] : ""}</i>`;
  };
  function starPop(btn) {
    const row = x => `<button class="sta" data-open="${esc(x.key)}"><span class="s">★</span><span>${docName(x.key)}</span><em>${V.relT(x.t)}</em>`
      + `<u data-unstar="${esc(x.key)}" data-tip="取消星标">×</u></button>`;
    V.pop("starPop", '<div class="pt">星标文档</div>' + (stars.length ? stars.map(row).join("") : '<div class="qnone">还没有星标。打开文档后点右上角的 ☆，或按 s。</div>'), btn);
  }
  function trailPop(btn) {
    const items = V.recent.list("opened").slice(0, 10);
    V.pop("trailPop", `<div class="pt">足迹</div>` + (items.length ? items.map(key => {
      const pct = V.readPct ? V.readPct(key) : 0;
      return `<button class="li" data-open="${esc(key)}"><span>${docName(key)}</span><em>${pct ? `读到 ${pct}%` : ""}</em></button>`;
    }).join("") : '<div class="qnone">还没有打开过文档</div>'), btn);
  }

  /* ---- render ---- */
  const curKeys = () => { const k = V.readingK(), l = k && V.P[k].loc; return l && l.kind === "doc" ? [l.tree + ":" + l.rel] : []; };   // the focused pane's doc only
  const row = (d, cls, fold, name, extra, attr) => `<button class="tr ${cls}" style="--d:${d}" ${attr}>`
    + `<span class="cv">${fold ? "<i></i>" : ""}</span><span class="nm">${name}</span>${extra || ""}</button>`;
  const when = (tree, mt) => (sorts[tree].key === "mtime" ? `<em>${V.ago(mt)}</em>` : "");   // times only under a time sort
  function fileRow(tree, rel, name, d, cur) {
    const key = tree + ":" + rel, mt = V.D.mtime[tree][rel];
    return row(d, cur.includes(key) ? "cur" : "", 0, esc(name), (V.isStar(key) ? '<em class="star">★</em>' : "") + when(tree, mt), `data-open="${esc(key)}"`);
  }
  function nodeRows(tree, node, base, d, cmp, cur, filesFirst) {
    let h = "";
    const dirs = Object.keys(node.dirs).map(n => ({ name: n, mtime: node.dirs[n].mtime, node: node.dirs[n] })).sort(cmp);
    const dirRows = () => dirs.forEach(e => {
      const k = tree + ":" + base + e.name, open = isOpen(k);
      h += row(d, "dir " + (open ? "open" : ""), 1, esc(e.name), when(tree, e.mtime), `data-fold-k="${esc(k)}"`);
      if (open) h += nodeRows(tree, e.node, base + e.name + "/", d + 1, cmp, cur, filesFirst);
    });
    if (!filesFirst) dirRows();
    node.files.slice().sort(cmp).forEach(f => { h += fileRow(tree, f.path, f.name, d, cur); });
    if (filesFirst) dirRows();
    return h;
  }
  function cardRows(c, d, cmp, cur) {
    const k = "dev:" + c.dir, open = isOpen(k);
    const node = SV.buildTree(V.docsOf(c).map(x => ({ path: x.rel.slice(c.dir.length + 1), mtime: x.mtime })));
    let h = row(d, "dir " + (open ? "open" : ""), 1, esc(c.dirName), when("dev", node.mtime), `data-fold-k="${esc(k)}" data-tip="${esc(c.dir + " · " + c.st)}"`);
    if (!open) return h;
    const fix = n => { n.files.forEach(f => { f.path = c.dir + "/" + f.path; }); Object.values(n.dirs).forEach(fix); }; fix(node);
    const cmpD = (a, b) => sorts.dev.key === "name" ? (b.name === "design.md") - (a.name === "design.md") || cmp(a, b) : cmp(a, b);
    return h + nodeRows("dev", node, c.dir + "/", d + 1, cmpD, cur, true);
  }
  const ctl = (t, flat) => `<button class="tc" data-tsort="${t}" data-tip="排序：名称 / 修改时间">${sorts[t].key === "mtime" ? "T" : "A"}</button>`
    + `<button class="tc" data-tdir="${t}" data-tip="排序方向">${sorts[t].dir > 0 ? "↑" : "↓"}</button>`
    + (flat ? "" : `<button class="tc ${snap[t] ? "on" : ""}" data-tcol="${t}" data-tip="${snap[t] ? "恢复折叠前的展开" : "折叠这一区的全部文件夹"}">F</button>`);
  // todo: the two views of the todo page first, then the files of dev_root/todo/ with their open counts
  function todoRows(cur) {
    const mode = V.store.get("todo-mode", "list"), on = m => (V.view === "todo" && mode === m ? "cur" : "");
    const view = (m, icon, name, extra) => `<button class="tr ${on(m)}" style="--d:0" data-todo="${m}"><span class="cv">${icon}</span><span class="nm">${name}</span>${extra}</button>`;
    let h = view("list", V.I.box, "待办", `<em>${V.todoOpen ? V.todoOpen() || "" : ""}</em>`) + view("review", V.I.hist, "回顾", "");
    const files = V.D.tree.dev.filter(it => /^todo\/[^/]+\.md$/.test(it.path)).map(it => ({ name: it.path.slice(5), path: it.path, mtime: it.mtime }));
    files.sort(SV.sortCmp(sorts.todo.key, sorts.todo.dir)).forEach(f => {
      const key = "dev:" + f.path, tf = V.todoFiles && V.todoFiles[f.name], open = tf && tf.text != null ? SV.parseTodo(tf.text).filter(i => !i.done).length : 0;
      h += row(0, "tfr " + (cur.includes(key) ? "cur" : ""), 0, esc(f.name.replace(/\.md$/, "")), when("todo", f.mtime) + `<em>${open || ""}</em>`
        + `<u class="tfx" data-tren="${esc(f.name)}" data-tip="改名">✎</u><u class="tfx" data-tdelf="${esc(f.name)}" data-tip="删除这个文件">×</u>`, `data-open="${esc(key)}"`);
    });
    return h;
  }
  function render(reveal) {
    const tree = $("#tree"), top = tree.scrollTop, cur = curKeys(), D = V.D;
    const cards = D.cards;
    let h = `<button class="tr top ${V.view === "board" ? "cur" : ""}" style="--d:0" data-goboard="1">`
      + `<span class="cv">${V.I.grid}</span><span class="nm">看板</span><em>${cards.length}</em></button>`
      + `<button class="tr top ${V.view === "recent" ? "cur" : ""}" style="--d:0" data-recent="1" data-tip="dev_root 最近 25 次提交">`
      + `<span class="cv">${V.I.hist}</span><span class="nm">最近提交</span></button>`;
    if (V.GITWEB) h += `<a class="tr top" style="--d:0" href="${esc(V.GITWEB)}" target="_blank" rel="noopener" data-tip="浏览代码：gitweb，在新标签页打开">`
      + `<span class="cv">${V.I.code}</span><span class="nm">浏览代码</span></a>`;
    h += `<div class="tsec"><button class="nm" data-fold-k="todo">todo</button><button class="tc" data-tnewf data-tip="新建 todo 文件">＋</button>${ctl("todo", true)}</div>`;
    if (isOpen("todo")) h += todoRows(cur);
    // dev: projects → open cards → closed (n) → the project's other files; todo/ has its own section above
    const dc = SV.sortCmp(sorts.dev.key, sorts.dev.dir), devOpen = isOpen("dev");
    h += `<div class="tsec"><button class="nm" data-fold-k="dev">dev_root</button>${ctl("dev")}</div>`;
    if (devOpen) {
      const devItems = D.tree.dev.filter(it => !it.path.startsWith("todo/"));
      const root = SV.buildTree(devItems.filter(it => !V.cardOfPath("dev", it.path)));
      const projs = [...new Set(devItems.map(it => it.path.split("/")[0]).filter(p => devItems.some(it => it.path.startsWith(p + "/"))))]
        .map(p => ({ name: p, mtime: Math.max(0, ...devItems.filter(it => it.path.startsWith(p + "/")).map(it => it.mtime)) })).sort(dc);
      const byNo = (a, b) => (sorts.dev.key === "mtime" ? dc({ name: a.n, mtime: a.mt }, { name: b.n, mtime: b.mt })
        : (b.n < a.n ? -1 : b.n > a.n ? 1 : 0) * sorts.dev.dir);   // by name, newest card first under ↑
      projs.forEach(pj => {
        const k = "dev:" + pj.name, open = isOpen(k);
        const pc = cards.filter(c => c.p === pj.name).map(c => Object.assign(c, { mt: D.mtime.dev[c.dir + "/design.md"] || 0 })).sort(byNo);
        const live = pc.filter(c => OPEN_ST.includes(c.st)), closed = pc.filter(c => !OPEN_ST.includes(c.st));
        const tip = `${esc(pj.name)}：进行中 ${live.length}，共 ${pc.length} 张卡`;
        h += row(0, "dir top " + (open ? "open" : ""), 1, esc(pj.name), when("dev", pj.mtime), `data-fold-k="${esc(k)}" data-tip="${tip}"`);
        if (!open) return;
        live.forEach(c => { h += cardRows(c, 1, dc, cur); });
        if (root.dirs[pj.name]) h += nodeRows("dev", root.dirs[pj.name], pj.name + "/", 1, dc, cur, false);
        if (closed.length) {   // always last in the project, after its other folders and files
          const ek = "dev:" + pj.name + "/closed", eo = isOpen(ek), cmt = Math.max(0, ...closed.flatMap(c => V.docsOf(c).map(x => x.mtime)));
          h += row(1, "dir grp " + (eo ? "open" : ""), 1, `closed (${closed.length})`, when("dev", cmt), `data-fold-k="${esc(ek)}" data-tip="done 与 dropped 的卡"`);
          if (eo) closed.forEach(c => { h += cardRows(c, 2, dc, cur); });
        }
      });
      root.files.slice().sort(dc).forEach(f => { h += fileRow("dev", f.path, f.name, 0, cur); });
    }
    // kb: the knowledge base
    h += `<div class="tsec"><button class="nm" data-fold-k="kb">知识库</button>${ctl("kb")}</div>`;
    if (isOpen("kb")) {
      h += nodeRows("kb", SV.buildTree(D.tree.kb), "", 0, SV.sortCmp(sorts.kb.key, sorts.kb.dir), cur, false);
    }
    // extra roots, read-only: from config.yaml's extra_roots and from the page (the ⚙ in this head)
    const ext = D.tree.ext || [];   // a render before the first data has no ext list yet
    h += `<div class="tsec"><button class="nm" data-fold-k="ext">外部目录</button><button class="tc" data-troots data-tip="设置外部目录">⚙</button>${ext.length ? ctl("ext") : ""}</div>`;
    if (isOpen("ext") && ext.length) h += nodeRows("ext", SV.buildTree(ext), "", 0, SV.sortCmp(sorts.ext.key, sorts.ext.dir), cur, false);
    tree.innerHTML = h; tree.scrollTop = top;
    const cr = $("#tree .tr.cur:not([data-goboard])"), y = cr && cr.offsetTop - tree.offsetTop;   // offsetTop counts from #nav, above the tree's own top
    if (reveal && cr && (y < tree.scrollTop || y > tree.scrollTop + tree.clientHeight - 30)) tree.scrollTop = y - tree.clientHeight / 3;
  }
  // opening a doc unfolds its ancestors for this session only — a programmatic expand is not a preference
  V.revealDoc = (tree, rel) => {
    const segs = rel.split("/"); reveal.add(tree);
    if (tree === "dev" && segs[0] === "todo") reveal.add("todo");
    for (let i = 1; i < segs.length; i++) reveal.add(tree + ":" + segs.slice(0, i).join("/"));
    const c = V.cardOfPath(tree, rel); if (c && !OPEN_ST.includes(c.st)) reveal.add("dev:" + c.p + "/closed");
  };
  function collapse(t) {   // only the folders this render shows are touched, and the write merges like a single toggle
    const shown = $$(`#tree [data-fold-k^="${t}:"]`).map(el => el.dataset.foldK);
    if (snap[t]) { snap[t].forEach(k => openF.add(k)); snap[t] = null; }
    else { snap[t] = shown.filter(k => openF.has(k)); shown.forEach(k => { openF.delete(k); reveal.delete(k); }); }
    V.store.set("tree-open", SV.mergeTreeOpen(V.store.get("tree-open", DEF_OPEN), shown, shown.filter(k => openF.has(k))));
    render();
  }

  V.click("[data-fold-k]", el => toggleFold(el.dataset.foldK));
  V.click("[data-recent]", (el, e) => { V.app.classList.remove("treepop"); V.nav(V.target(e), { kind: "recent" }); });
  V.click("[data-todo]", (el, e) => { V.app.classList.remove("treepop"); V.todoPreset(el.dataset.todo); V.nav(V.target(e), { kind: "todo" }); });
  V.click("[data-tsort]", el => {   // a time sort starts newest first, a name sort A→Z
    const s = sorts[el.dataset.tsort]; s.key = s.key === "name" ? "mtime" : "name"; s.dir = s.key === "name" ? 1 : -1; V.store.set("tree-sort", sorts); render(); });
  V.click("[data-tdir]", el => { const s = sorts[el.dataset.tdir]; s.dir = -s.dir; V.store.set("tree-sort", sorts); render(); });
  V.click("[data-tcol]", el => collapse(el.dataset.tcol));
  /* ---- extra roots set from the page (044): list, add, remove; changes apply at once ---- */
  function rootPop(anchor, roots) {
    const rows = roots.map(r => `<div class="rr"><b>${esc(r.label)}</b><span data-tip="${esc(r.path)}">${esc(r.path)}</span>`
      + `<button class="rt${r.trusted ? " on" : ""}" data-rtrust="${esc(r.path)}" data-v="${r.trusted ? 0 : 1}" `
      + `data-tip="${r.trusted ? "这里的网页与 viewer 同源，点击改为沙箱" : "这里的网页在沙箱里运行，点击改为信任"}">${r.trusted ? "信任" : "沙箱"}</button>`
      + (r.from === "page" ? `<button data-rdel="${esc(r.path)}" data-tip="移除">×</button>` : `<em data-tip="在 config.yaml 的 extra_roots 里改">config</em>`) + "</div>").join("");
    V.pop("rootPop", `<div class="pt">外部目录（只读）</div>${rows || '<div class="qnone">还没有外部目录</div>'}`
      + `<form class="radd"><input placeholder="~/某个目录" aria-label="新的外部目录"><button>添加</button></form>`
      + '<label class="rnote"><input type="checkbox" class="rtrust"> 信任这个目录：里面的网页不加沙箱，能读写 viewer 的数据</label>'
      + '<div class="rnote">只能添加家目录之下已存在的目录；局域网里能打开 viewer 的设备也能改。</div>', anchor, "left");
  }
  const roots = (op, path, trusted) => fetch("/api/roots", { method: "POST", headers: { "Content-Type": "application/json", "X-SV-Write": "1" },
    body: JSON.stringify(trusted == null ? { op, path } : { op, path, trusted }) })
    .then(r => r.json().catch(() => ({})).then(d => {
      if (r.status === 401) return V.authLost();
      if (!r.ok) return V.toast(d.error || "没改成（" + r.status + "）");
      if (op === "add") reveal.add("ext");   // show what was just added
      return V.load().then(() => V.emit("data")).then(() => rootPop($("[data-troots]"), d.roots));
    })).catch(() => V.toast("没改成：连不上 viewer"));
  V.click("[data-troots]", el => (V.isPop("rootPop") ? V.closePops() : V.json("/api/roots").then(d => rootPop(el, d.roots)).catch(() => V.toast("读不到外部目录设置"))));
  V.click("[data-rdel]", el => roots("remove", el.dataset.rdel));
  const TRUST_ASK = "信任后，这个目录里的网页与 viewer 同源，能读写 viewer 的全部数据";
  V.click("[data-rtrust]", el => {   // one click could trust by mistake, so turning trusted asks first
    const on = el.dataset.v === "1", go = () => roots("trust", el.dataset.rtrust, on);
    if (on) V.ask(TRUST_ASK, [["ok", "信任"], ["", "取消"]]).then(v => { if (v) go(); }); else go();
  });
  document.addEventListener("submit", e => {
    const f = e.target.closest("#rootPop .radd"); if (!f) return; e.preventDefault();
    const v = $("input", f).value.trim(); if (v) roots("add", v, $("#rootPop .rtrust").checked);
  });
  V.click("[data-unstar]", (el, e) => { e.stopPropagation(); V.toggleStar(el.dataset.unstar); starPop($("#starBtn")); });
  V.click("[data-open]", (el, e) => {
    if (e.target.closest("[data-tren],[data-tdelf]")) return false;   // a todo file row's rename and delete
    V.closePops(); V.app.classList.remove("treepop");
    const key = el.dataset.open, i = key.indexOf(":"), rel = key.slice(i + 1);
    if ((e.metaKey || e.ctrlKey) && V.isPage(rel)) return void V.openPageTab(key.slice(0, i), rel);   // ⌘-click: a page in its own tab
    V.openDoc(key.slice(0, i), rel, e, el.dataset.oline ? { line: +el.dataset.oline } : undefined);
  });
  V.click("#starBtn", el => (V.isPop("starPop") ? V.closePops() : starPop(el)));
  V.click("#trailBtn", el => (V.isPop("trailPop") ? V.closePops() : trailPop(el)));
  ["data", "tree-show", "stars", "focus", "split", "todo-count"].forEach(ev => V.on(ev, () => render(ev === "tree-show")));
  V.on("nav", (k, loc) => { if (loc.kind === "doc") V.revealDoc(loc.tree, loc.rel); render(true); });
})(V2);
