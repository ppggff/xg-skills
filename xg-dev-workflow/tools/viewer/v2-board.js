/* status viewer v2 — board: four forms (cards, columns, table, signal) grouped by project, status or
   governance; the status filter popover, group trays, the card detail under the board, and a card's diff. */
"use strict";
(function (V) {
  const { $, $$, esc, store } = V;
  const GRPS = [["p", "项目"], ["s", "状态"], ["g", "治理"]];
  const FORMS = [["cards", "卡片", "grid"], ["cols", "列", "cols"], ["table", "表格", "tbl"], ["dots", "信号", "dots"]];
  const STATES = ["active", "blocked", "paused", "todo", "backlog", "unknown", "done", "dropped"];
  const GOVS = ["lite", "doc-gate", "ledger", "doc-native", "doc-native-pilot", "legacy"];
  const hidden = new Set(store.get("hide", []));
  const unfold = new Set();
  let sel = store.get("sel", null), groupBy = store.get("grp", "p"), trays = store.get("trays", true);
  let sortK = store.get("sortK", ""), sortDesc = store.get("sortDesc", false);
  const form = () => store.get("form", null) || (V.isNarrow() ? "table" : "cards");
  const seenTicks = new Set();
  const isOpenSt = st => V.OPEN_ST.includes(st);
  const cardMt = () => SV.cardMtimes(V.D.tree.dev);
  const newest = (a, b) => (b.n < a.n ? -1 : b.n > a.n ? 1 : a.id.localeCompare(b.id));
  const selCls = c => (c.id === sel ? "sel" : "");

  function groupsOf() {
    const vis = V.D.cards.filter(c => !hidden.has(c.st));
    const of = (key, name, pick, extra) => Object.assign({ key, name, cs: vis.filter(pick).sort(newest) }, extra);
    if (groupBy === "s") return STATES.map(st => of("s:" + st, st, c => c.st === st, { st, closed: !isOpenSt(st) })).filter(g => g.cs.length);
    if (groupBy === "g") {
      const gs = GOVS.concat([...new Set(vis.map(c => c.gov))].filter(g => !GOVS.includes(g)));
      return gs.map(gv => of("g:" + gv, gv, c => c.gov === gv)).filter(g => g.cs.length);
    }
    const ps = [...new Set(vis.map(c => c.p))].map(p => of("p:" + p, p, c => c.p === p));
    return ps.sort((a, b) => b.cs.length - a.cs.length || a.name.localeCompare(b.name));
  }

  /* ---- head ---- */
  function headHTML() {
    const f = form();
    const g = GRPS.find(x => x[0] === groupBy) || GRPS[0], fm = FORMS.find(x => x[0] === f) || FORMS[0];
    const grp = `<button data-grpc data-tip="分组：按${g[1]}（点击换下一个：${GRPS.map(x => x[1]).join(" → ")}）">${g[1]}</button>`;
    const forms = `<button data-formc data-tip="形态：${fm[1]}（点击换下一个：${FORMS.map(x => x[1]).join(" → ")}）">${V.I[fm[2]]}</button>`;
    const fltTip = hidden.size ? "已隐藏 " + [...hidden].join("、") + "，点开调整" : "按状态过滤";
    const k = V.hostOf("board");
    return `<button class="ib navb" data-navb data-tip="导航" aria-label="导航">${V.I.menu}</button>` + V.paneHead(k)
      + `<div class="ppath"><bdi>dev_root / <b>看板</b></bdi></div>`
      + `<div class="seg" style="margin-left:auto">${grp}${forms}`
      + `<button class="${hidden.size ? "on" : ""}" data-flt data-popbtn data-tip="${fltTip}" aria-label="过滤状态">${V.I.filter}</button>`
      + `<button class="${trays ? "on" : ""}" data-trays data-tip="${trays ? "关闭" : "打开"}分组外框">${V.I.trays}</button></div>` + V.paneEnd(k);
  }

  /* ---- forms ---- */
  function progHTML(c) {
    if (c.lite && c.req) {
      const ticks = Array.from({ length: c.req }, (_, i) => `<i class="${i < c.ok ? "on" : ""}" style="--k:${i}"></i>`).join("");
      return `<div class="tk ${seenTicks.has(c.id) ? "" : "pre"} ${c.ok === c.req ? "full" : ""}" data-tk="${esc(c.id)}">${ticks}<span class="ok">${V.I.tick}</span></div>`;
    }
    if (c.lite) return '<div class="tk"></div>';
    return `<div class="ph6" data-st="${c.st}">${c.ph.map((v, i) => `${i ? `<span class="${v ? "on" : ""}"></span>` : ""}<b class="s${v}"></b>`).join("")}</div>`;
  }
  function cardHTML(c) {
    const right = c.lite && c.req ? V.frac(c.ok, c.req) : `<span class="fr" style="color:var(--mu)">${esc(V.phaseNow(c))}</span>`;
    const no = groupBy === "p" ? c.n : esc(c.p) + "/" + c.n, word = c.st === "active" || groupBy === "s" ? "" : c.st;
    return `<button class="card ${selCls(c)}" data-card="${esc(c.id)}" data-st="${c.st}">`
      + `<div class="c1"><span class="no">${no}</span><span class="w">${word}</span><span class="r">${right}</span></div>`
      + `<div class="sl" title="${esc(c.slug)}">${esc(c.slug)}</div><div class="nx" title="${esc(V.nextOf(c))}">${esc(V.nextOf(c))}</div>`
      + progHTML(c) + "</button>";
  }
  function rowHTML(c) {
    const name = esc(groupBy === "p" ? c.slug : c.p + " / " + c.slug);
    return `<button class="row ${selCls(c)}" data-card="${esc(c.id)}" data-st="${c.st}"><span class="n">${c.n}</span>`
      + `<span class="s">${name}</span>${c.lite && c.req ? V.frac(c.ok, c.req) : ""}</button>`;
  }
  // every form keeps a group's done/dropped cards behind one fold until it is opened
  const split = g => ({ open: g.closed ? [] : g.cs.filter(c => isOpenSt(c.st)), closed: g.closed ? g.cs : g.cs.filter(c => !isOpenSt(c.st)), show: unfold.has(g.key) });
  function foldHTML(g, closed, show) {
    const done = closed.filter(c => c.st === "done").length, tip = `${show ? "收起" : "展开"}已结束的卡：done ${done} · dropped ${closed.length - done}`;
    return `<button class="fold" data-fold="${esc(g.key)}" data-tip="${tip}"><span class="dots">${closed.map(c => `<i class="${c.st}"></i>`).join("")}</span></button>`;
  }
  function groupHTML(g, cls, gridCls) {
    const { open, closed, show } = split(g);
    let h = `<section class="${cls}"><h2 ${g.st ? `data-st="${g.st}"` : ""}>${esc(g.name)}<em>${g.cs.length}</em></h2>`;
    if (open.length) h += `<div class="${gridCls}">${open.map(cardHTML).join("")}</div>`;
    if (closed.length) {
      h += foldHTML(g, closed, show);
      if (show) h += `<div class="rows">${closed.map(rowHTML).join("")}</div>`;
    }
    return h + "</section>";
  }
  function dotsHTML(gs) {
    const mt = cardMt(), FILM = ["done", "active", "paused", "blocked", "todo", "backlog", "unknown", "dropped"];
    let n = 0;
    const dot = c => `<button class="dot ${c.st} ${selCls(c)}" data-card="${esc(c.id)}" data-st="${c.st}" style="--i:${n++}" aria-label="${esc(c.id + " " + c.slug)}">`
      + `<span class="dtag"><span>${c.n}</span><span>·</span><span>${V.ago(mt[c.dir]) || ""}</span></span></button>`;
    return gs.map(g => {
      const { open, closed, show } = split(g), cs = show ? g.cs : open;
      const subOf = groupBy === "s" ? c => c.p : c => c.st;
      const order = groupBy === "s" ? [...new Set(cs.map(c => c.p))] : FILM.filter(st => cs.some(c => c.st === st));
      const subs = order.map(k => ({ k, cs: cs.filter(c => subOf(c) === k).sort((a, b) => a.n.localeCompare(b.n) || a.id.localeCompare(b.id)) }));
      const lanes = subs.map(sb => `<div class="dgrp"><div class="dd">${sb.cs.map(dot).join("")}</div>`
        + `<div class="dl"><span>${esc(sb.k)}</span><em>${sb.cs.length}</em></div></div>`).join("");
      return `<section class="dproj"><div class="dnum">${g.cs.length}<span class="dname">${esc(g.name)}</span></div><div class="drow">${lanes}</div>`
        + (closed.length ? foldHTML(g, closed, show) : "") + "</section>";
    }).join("");
  }
  function tableHTML(gs) {
    const mt = cardMt();
    const cols = [["n", "编号"], ["slug", "名称"]].concat(groupBy !== "p" ? [["p", "项目"]] : [], groupBy !== "s" ? [["st", "状态"]] : [],
      groupBy !== "g" ? [["gov", "治理"]] : [], [["prog", "进度"], ["nx", "下一步"], ["mt", "更新"]]);
    const val = (c, k) => k === "prog" ? (c.lite ? (c.req ? c.ok / c.req : 0) : c.ph.filter(v => v === 2).length / 6) : k === "mt" ? mt[c.dir] || 0 : k === "nx" ? V.nextOf(c) : c[k];
    const cmp = (a, b) => { const x = val(a, sortK), y = val(b, sortK); return (x > y ? 1 : x < y ? -1 : 0) * (sortDesc ? -1 : 1); };
    const prog = c => c.lite && c.req
      ? `<span class="mt"><i style="width:${(c.ok / c.req * 100).toFixed(1)}%"></i></span>${V.frac(c.ok, c.req)}`
      : `<span class="mu">${esc(V.phaseNow(c))}</span>`;
    const row = c => `<tr data-card="${esc(c.id)}" data-st="${c.st}" class="${selCls(c)}"><td class="n">${c.n}</td><td class="nm" data-tip="${esc(c.id + " " + c.slug)}">${esc(c.slug)}</td>`
      + (groupBy !== "p" ? `<td class="mu">${esc(c.p)}</td>` : "") + (groupBy !== "s" ? `<td style="color:var(--c)">${c.st}</td>` : "")
      + (groupBy !== "g" ? `<td class="mu">${esc(c.gov)}</td>` : "") + `<td>${prog(c)}</td><td class="mu nxc" data-tip="${esc(V.nextOf(c))}">${esc(V.nextOf(c))}</td>`
      + `<td class="mu">${V.ago(mt[c.dir])}</td></tr>`;
    const th = cols.map(([k, l]) => `<th data-sort="${k}" class="${sortK === k ? "on" + (sortDesc ? " desc" : "") : ""}">${l}</th>`).join("");
    let h = `<table class="tbl"><thead><tr>${th}</tr></thead><tbody>`;
    gs.forEach(g => {
      const { open, closed, show } = split(g), sorted = list => (sortK ? [...list].sort(cmp) : list);
      h += `<tr class="gh"><td colspan="${cols.length}">${esc(g.name)}<em>${g.cs.length}</em></td></tr>` + sorted(open).map(row).join("")
        + (closed.length ? `<tr class="tfold"><td colspan="${cols.length}">${foldHTML(g, closed, show)}</td></tr>` + (show ? sorted(closed).map(row).join("") : "") : "");
    });
    return h + "</tbody></table>";
  }
  function bodyHTML() {
    const gs = groupsOf(), f = form();
    if (!gs.length) {
      if (V.D.cards.length) return '<div class="empty-b">过滤后没有卡片。<br><button data-fltall>全部显示</button></div>';
      return '<div class="empty-b">没有卡片。</div>';
    }
    if (f === "dots") return dotsHTML(gs);
    if (f === "table") return tableHTML(gs);
    if (f === "cols") return `<div class="kcols">${gs.map(g => groupHTML(g, "proj kcol", "kstack")).join("")}</div>`;
    return gs.map(g => groupHTML(g, "proj", "grid")).join("");
  }
  let tkObs = null;
  function render() {
    const b = $("#bscroll"), top = b.scrollTop, kc = $(".kcols", b), left = kc ? kc.scrollLeft : 0;
    $("#bhd").innerHTML = headHTML();
    b.classList.toggle("tbl-form", form() === "table");
    b.innerHTML = bodyHTML(); b.scrollTop = top;
    const k2 = $(".kcols", b); if (k2) k2.scrollLeft = left;
    V.app.classList.toggle("notray", !trays);
    if (tkObs) tkObs.disconnect();
    tkObs = new IntersectionObserver(es => es.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target; seenTicks.add(el.dataset.tk);
      requestAnimationFrame(() => el.classList.remove("pre")); tkObs.unobserve(el);
    }), { root: b, threshold: .6 });
    $$(".tk.pre", b).forEach(t => (V.RM ? t.classList.remove("pre") : tkObs.observe(t)));
    paintDetail();
  }

  /* ---- detail under the board ---- */
  const reqCache = {};
  function reqsOf(c) {   // Req headings of a lite card's design.md, re-read when the file changes
    const rel = c.dir + "/design.md", mt = V.D.mtime.dev[rel]; if (!c.lite || !mt) return null;
    const hit = reqCache[c.id]; if (hit && hit.mt === mt) return hit.list;
    reqCache[c.id] = { mt, list: hit ? hit.list : undefined };
    V.api("/raw/dev/" + rel).then(r => r.text())
      .then(t => { reqCache[c.id] = { mt, list: SV.reqHeads(t) }; if (sel === c.id) paintDetail(); })
      .catch(() => { reqCache[c.id] = { mt, list: [] }; });
    return reqCache[c.id].list;
  }
  const gitLink = c => esc(V.GITWEB) + "?p=" + encodeURIComponent(c.p) + ";a=summary" + (c.branch ? ";h=refs/heads/" + encodeURIComponent(c.branch) : "");
  function linksHTML(c) {
    const docs = V.docsOf(c).map(x => x.rel), has = f => docs.includes(c.dir + "/" + f);
    const gitTip = "在 gitweb 里看这个项目" + (c.branch ? "的 " + esc(c.branch) + " 分支" : "");
    return [has("progress.md") && `<button data-open="dev:${esc(c.dir)}/progress.md">progress</button>`,
      has("log.md") && `<button data-open="dev:${esc(c.dir)}/log.md">log</button>`,
      `<button data-diff="${esc(c.id)}">±diff</button>`,
      V.GITWEB && `<a href="${gitLink(c)}" target="_blank" rel="noopener" data-tip="${gitTip}">code ↗</a>`].filter(Boolean).join("");
  }
  function reqsHTML(c) {
    if (c.lite) {
      const rq = reqsOf(c), bars = Array.from({ length: c.req }, (_, i) => `<i class="${i < c.ok ? "" : "o"}"></i>`).join("");
      const rows = rq ? rq.map(r => `<button class="rq ${r.st === "已验证" ? "" : "open"}" data-rq data-tip="Req-${r.n} · ${esc(r.st)}">`
        + `<span class="ck">${r.st === "已验证" ? V.I.tick : ""}</span><b>R${r.n}</b><span>${esc(r.t)}</span></button>`).join("")
        : '<div class="hint" style="padding:0">读取 Req…</div>';
      return `<div class="rhead"><span class="vt">${bars}</span><span class="bfr"><b>${c.ok}</b><i>/</i><s>${c.req}</s></span></div>` + rows;
    }
    const bars = c.ph.map(v => `<i class="${v === 2 ? "" : v === 1 ? "h" : "o"}"></i>`).join("");
    const steps = c.steps.map(s => {
      const i = s.indexOf(":"), done = SV.stepFill(s.slice(i + 1)) === "done";
      return `<div class="rq"><span class="ck">${done ? V.I.tick : ""}</span><b>${esc(s.slice(0, i))}</b><span>${esc(s.slice(i + 1))}</span></div>`;
    }).join("");
    return `<div class="rhead"><span class="vt">${bars}</span><span class="bfr"><s style="font-size:11px;color:var(--mu)">${esc(V.phaseNow(c))}</s></span></div>` + steps;
  }
  function detailHTML() {
    const c = V.card(sel), head = `<button class="ib bx" data-col="det" data-tip="关闭详情，再点一张卡会重新打开" aria-label="关闭详情">${V.I.x}</button>`;
    if (!c) return head + '<div class="hint">单击一张卡看详情，双击直接打开它的 design.md，⇧ 单击在右栏打开。</div>';
    const key = V.docsOf(c).map(x => x.rel).filter(d => !d.slice(c.dir.length + 1).includes("/"))
      .sort((a, b) => (b.endsWith("/design.md") - a.endsWith("/design.md")) || a.localeCompare(b));
    const files = key.map(d => `<button class="kf" data-open="dev:${esc(d)}" data-tip="${esc(d)}">${esc(d.slice(c.dir.length + 1))}</button>`).join("");
    const meta = `<span class="hst">${c.st}</span>　${esc(c.p)}　${esc(c.gov)}${c.deps && c.deps !== "—" ? "　deps " + esc(c.deps) : ""}`;
    const row = inner => `<div class="brow">${inner}</div>`;
    return head + `<div class="bdg" data-st="${c.st}">`
      + `<div class="brow big"><div class="hero"><span class="hn">${c.n}</span><span class="hline"><span class="hm">${meta}</span></span></div></div>`
      + row(`<div class="sfl"><span class="hsl">${esc(c.slug)}</span>${files}</div>`)
      + row(`<div class="bv nx">${esc(V.nextOf(c))}</div>`)
      + (c.now ? row(`<div class="bv"><span><b>now</b>${esc(c.now)}</span></div>`) : "")
      + (c.block && c.block !== "—" ? row(`<div class="bv blk"><span><b>block</b>${esc(c.block)}</span></div>`) : "")
      + row(`<div class="blinks">${linksHTML(c)}</div>`)
      + row(`<div>${reqsHTML(c)}</div>`) + "</div>";
  }
  const onShow = () => !$("#board").hidden;
  function paintDetail() { if (onShow()) $("#bdet").innerHTML = detailHTML(); }
  function selectCard(id, open) {
    sel = id; store.set("sel", id);
    $$("#board [data-card]").forEach(e => e.classList.toggle("sel", e.dataset.card === id));
    const tag = !V.RM && $("#board .dot.sel .dtag");
    if (tag) tag.animate([{ opacity: 0, transform: "translateY(3px)" }, { opacity: 1, transform: "none" }], { duration: 220, easing: "ease-out" });
    if (open !== false && V.W.dc) { V.W.dc = false; V.applyW(); V.saveW(); }
    paintDetail();
  }
  V.pickCard = id => {
    selectCard(id);
    const el = $(`#bscroll [data-card="${V.cssEsc(id)}"]`); if (el) el.scrollIntoView({ block: "nearest", behavior: V.RM ? "auto" : "smooth" });
  };
  function closeDetail() {
    if (!sel && V.W.dc) return;
    sel = null; store.set("sel", null); V.W.dc = true; V.applyW(); V.saveW();
    $$("#board [data-card].sel").forEach(e => e.classList.remove("sel")); paintDetail();
  }
  V.on("detail-close", closeDetail);
  V.revealCard = c => {
    unfold.add(groupBy === "s" ? "s:" + c.st : groupBy === "g" ? "g:" + c.gov : "p:" + c.p);
    hidden.delete(c.st); store.set("hide", [...hidden]); render(); V.pickCard(c.id);
  };
  function moveSel(key) {
    const els = $$("#bscroll [data-card]").filter(e => e.offsetParent); if (!els.length) return;
    const cur = els.find(e => e.dataset.card === sel); if (!cur) return V.pickCard(els[0].dataset.card);
    const horiz = key === "ArrowRight" || key === "ArrowLeft", fwd = key === "ArrowRight" || key === "ArrowDown";
    let nx = null;
    if (horiz && form() !== "cols") nx = els[els.indexOf(cur) + (fwd ? 1 : -1)];
    else {   // nearest card in that direction, preferring the same row or column
      const r = cur.getBoundingClientRect(); let best = 1e9;
      els.forEach(e => {
        const q = e.getBoundingClientRect();
        const ahead = horiz ? (fwd ? q.left - r.right : r.left - q.right) : (fwd ? q.top - r.bottom : r.top - q.bottom);
        if (ahead < -2) return;
        const off = horiz ? Math.abs(q.top + q.height / 2 - (r.top + r.height / 2)) : Math.abs(q.left + q.width / 2 - (r.left + r.width / 2));
        if (ahead * 3 + off < best) { best = ahead * 3 + off; nx = e; }
      });
    }
    if (nx) V.pickCard(nx.dataset.card);
  }
  const openCard = (id, e) => {
    const c = V.card(id), d = c && V.mainDoc(c);
    if (d) V.openDoc("dev", d, e); else V.toast("这张卡没有 design.md");
  };

  /* ---- filter popover ---- */
  function fltPop(btn) {
    const count = st => V.D.cards.filter(c => c.st === st).length;
    const chips = STATES.filter(st => count(st)).map(st => `<button class="chip ${hidden.has(st) ? "off" : ""}" data-chip="${st}" data-st="${st}" `
      + `data-tip="${hidden.has(st) ? "显示" : "隐藏"} ${st} 的卡"><i class="gl ${st}"></i>${st}<em>${count(st)}</em></button>`).join("");
    const all = hidden.size ? '<button class="fall" data-fltall>全部显示</button>' : "";
    V.pop("fltPop", `<div class="pt">显示哪些状态</div><div class="chips">${chips}</div>${all}`, btn || $("[data-flt]"), "right");
  }
  const setHidden = () => { store.set("hide", [...hidden]); render(); V.untip(); V.status(); };

  /* ---- git views: a card's diff, and the recent commits of dev_root ---- */
  const filesHTML = t => SV.diffFiles(t).map(f => `<div class="dfile"><h3>${f.name ? `<button data-open="dev:${esc(f.name)}">${esc(f.name)}</button>` : ""}</h3><div class="md"><pre class="dif">`
    + f.lines.map(l => `<div class="${l.cls}">${esc(l.text) || " "}</div>`).join("") + "</pre></div></div>").join("");
  V.views.diff = (k, loc) => {
    const el = $("#diffv");
    el.innerHTML = `<div class="phd"><button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button>` + V.paneHead(k)
      + `<div class="ppath"><bdi>${esc(loc.card)} / <b>改动</b></bdi></div>`
      + `<button class="ib" data-goboard="1" data-tip="回看板" aria-label="回看板">${V.I.grid}</button>${V.paneEnd(k)}</div>`
      + '<div class="dbody scroll"><div class="hint">读取中…</div></div>';
    V.api("/api/diff?card=" + encodeURIComponent(loc.card)).then(r => r.text()).then(t => {
      if (V.P[k].loc !== loc) return;
      $(".dbody", el).innerHTML = filesHTML(t) || '<div class="hint">这张卡在 dev_root 里没有未提交或最近的改动。</div>';
    }).catch(e => { if (V.P[k].loc === loc) $(".dbody", el).innerHTML = `<div class="derr"><b>读不到改动</b><br>${esc(e.message)}</div>`; });
    V.status();
  };
  V.views.recent = (k, loc, opt) => {   // a refresh keeps the scroll; entering starts at the top
    const el = $("#recent"), old = $(".dbody", el), top = opt.entering || !old ? 0 : old.scrollTop;
    el.innerHTML = `<div class="phd"><button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button>` + V.paneHead(k)
      + '<div class="ppath"><bdi>dev_root / <b>最近提交</b></bdi></div>'
      + `<button class="ib" data-goboard="1" data-tip="回看板" aria-label="回看板">${V.I.grid}</button>${V.paneEnd(k)}</div>`
      + `<div class="dbody scroll">${old && !opt.entering ? old.innerHTML : '<div class="hint">读取中…</div>'}</div>`;
    $(".dbody", el).scrollTop = top;
    V.api("/api/log?n=25").then(r => r.text()).then(t => {
      if (V.P[k].loc !== loc) return;
      const b = $(".dbody", el), y = b.scrollTop;
      b.innerHTML = SV.splitCommits(t).map(c => `<section class="commit"><h2>${esc(c.subject)}<em>${esc(c.sha.slice(0, 7))}　${esc(c.date)}</em></h2>${filesHTML(c.diff)}</section>`).join("")
        || '<div class="hint">dev_root 还没有提交。</div>';
      b.scrollTop = y;
    }).catch(e => { if (V.P[k].loc === loc) $(".dbody", el).innerHTML = `<div class="derr"><b>读不到提交记录</b><br>${esc(e.message)}</div>`; });
    V.status();
  };
  V.statusFns.recent = () => `<span><b>最近提交</b>　dev_root，最新 25 次</span><span class="sp"></span>${V.stamp()}`;
  V.on("data", () => { if (!$("#recent").hidden) V.rerender(V.hostOf("recent")); });
  V.statusFns.diff = () => `<span><b>±diff</b>　${esc((V.P[V.navPane()].loc || {}).card || "")}</span><span class="sp"></span>${V.stamp()}`;

  /* ---- the board view ---- */
  V.views.board = () => {
    render(); V.status();
    const el = sel && $(`#bscroll [data-card="${V.cssEsc(sel)}"]`); if (el) el.scrollIntoView({ block: "nearest" });
  };
  V.statusFns.board = () => {
    const n = V.D.cards.length, hint = store.get("hintN", 0) < 5;
    return `<span><b>看板</b>　${n} 张卡${hidden.size ? "，隐藏了 " + [...hidden].join("、") : ""}</span>`
      + (hint ? "<span>单击看详情，双击打开 design.md，方向键移动</span>" : "") + `<span class="sp"></span>${V.stamp()}`;
  };
  V.on("nav", (k, loc) => { if (loc.kind === "board") store.set("hintN", store.get("hintN", 0) + 1); });
  V.on("data", () => { if (onShow()) { render(); V.status(); } });
  V.on("narrow", () => { if (onShow() && !store.get("form", null)) render(); });
  V.on("split", () => { if (onShow()) render(); });

  V.on("click", e => { if (sel && e.target.closest("#bscroll") && !e.target.closest("[data-card],[data-fold]")) closeDetail(); });
  const next = (list, cur) => list[(list.findIndex(x => x[0] === cur) + 1) % list.length][0];
  V.setGroup = g => { groupBy = g; store.set("grp", groupBy); unfold.clear(); render(); V.untip(); };
  V.setForm = f => {
    store.set("form", f); render(); V.untip();
    if (f !== "dots" || V.RM) return;
    const b = $("#bscroll"); b.classList.add("denter"); setTimeout(() => b.classList.remove("denter"), 1400);
  };
  V.click("[data-grpc]", () => V.setGroup(next(GRPS, groupBy)));
  V.click("[data-formc]", () => V.setForm(next(FORMS, form())));
  V.click("[data-trays]", () => { trays = !trays; store.set("trays", trays); render(); V.untip(); });
  V.click("th[data-sort]", el => {   // a header cycles ascending → descending → unsorted
    const k = el.dataset.sort;
    if (sortK !== k) { sortK = k; sortDesc = false; } else if (!sortDesc) sortDesc = true; else { sortK = ""; sortDesc = false; }
    store.set("sortK", sortK); store.set("sortDesc", sortDesc); render();
  });
  V.click("[data-chip]", el => { const s = el.dataset.chip; hidden.has(s) ? hidden.delete(s) : hidden.add(s); setHidden(); fltPop(); });
  V.click("[data-fltall]", () => { hidden.clear(); setHidden(); if (V.isPop("fltPop")) fltPop(); });
  V.click("[data-flt]", el => (V.isPop("fltPop") ? V.closePops() : fltPop(el)));
  V.click("[data-fold]", el => { const p = el.dataset.fold; unfold.has(p) ? unfold.delete(p) : unfold.add(p); render(); });
  V.click("[data-rq]", el => el.classList.toggle("x"));
  V.click("[data-diff]", (el, e) => { const k = V.paneOf(el); V.nav(e.shiftKey ? V.other(k) : k, { kind: "diff", card: el.dataset.diff }); });
  V.click("[data-card]", (el, e) => (e.shiftKey || e.detail >= 2 ? openCard(el.dataset.card, e) : selectCard(el.dataset.card)));
  const boardKeys = () => V.view === "board";
  ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].forEach(k => V.hotkey(k, e => (boardKeys() ? moveSel(e.key) : false)));
  V.hotkey("Enter", e => (boardKeys() && sel ? openCard(sel, e) : false));
  V.layer(10, () => V.view === "board" && !!sel, closeDetail);
  document.addEventListener("mouseover", e => {
    const d = e.target.closest(".dot[data-card]"), pop = $("#dotpop");
    if (!d) { pop.classList.remove("on"); return; }
    const c = V.card(d.dataset.card); if (!c) return;
    seenTicks.add(c.id); pop.innerHTML = cardHTML(c); pop.classList.add("on");
    const r = d.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
    pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + "px";
    pop.style.top = (r.top - h - 10 < 8 ? r.bottom + 10 : r.top - h - 10) + "px";
  });
})(V2);
