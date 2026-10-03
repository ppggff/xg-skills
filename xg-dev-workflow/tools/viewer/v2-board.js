/* status viewer v2 — board: four forms (cards, columns, table, signal) grouped by project, status or
   governance; the status filter popover, group trays, the card detail under the board, and a card's diff. */
"use strict";
(function (V) {
  const { $, $$, esc, store } = V;
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

  function groupsOf() {
    const vis = V.D.cards.filter(c => V.inScope(c.p) && !hidden.has(c.st));
    if (groupBy === "s") return STATES.map(st => ({ key: "s:" + st, name: st, st, cs: vis.filter(c => c.st === st).sort(newest), closed: !isOpenSt(st) })).filter(g => g.cs.length);
    if (groupBy === "g") { const gs = GOVS.concat([...new Set(vis.map(c => c.gov))].filter(g => !GOVS.includes(g)));
      return gs.map(gv => ({ key: "g:" + gv, name: gv, cs: vis.filter(c => c.gov === gv).sort(newest) })).filter(g => g.cs.length); }
    const ps = [...new Set(vis.map(c => c.p))].map(p => ({ key: "p:" + p, name: p, cs: vis.filter(c => c.p === p).sort(newest) }));
    return ps.sort((a, b) => b.cs.length - a.cs.length || a.name.localeCompare(b.name));
  }

  /* ---- head ---- */
  function headHTML() {
    const f = form(), segB = (k, l, cur, attr, tip, inner) => `<button ${attr}="${k}" class="${cur === k ? "on" : ""}" data-tip="${tip}">${inner || l}</button>`;
    return `<button class="ib navb" data-navb data-tip="导航" aria-label="导航">${V.I.menu}</button><div class="ppath"><bdi>dev_root / <b>看板</b>${V.scope ? " · " + esc(V.scope) : ""}</bdi></div>`
      + `<div class="seg" style="margin-left:auto;margin-right:10px">${[["p", "项目"], ["s", "状态"], ["g", "治理"]].map(([k, l]) => segB(k, l, groupBy, "data-grp", "按" + l + "分组")).join("")}</div>`
      + `<div class="seg">${segB("cards", "", f, "data-form", "卡片形态", V.I.grid)}${segB("cols", "", f, "data-form", "列形态：每个分组一列", V.I.cols)}${segB("table", "", f, "data-form", "表格形态：可点表头排序", V.I.tbl)}${segB("dots", "", f, "data-form", "信号形态：一张卡一个点，悬停看卡片", V.I.dots)}</div>`
      + `<div class="seg" style="margin-left:6px"><button class="${hidden.size ? "on" : ""}" data-flt data-popbtn data-tip="${hidden.size ? "已隐藏 " + [...hidden].join("、") + "，点开调整" : "按状态过滤"}" aria-label="过滤状态">${V.I.filter}</button><button class="${trays ? "on" : ""}" data-trays data-tip="${trays ? "关闭" : "打开"}分组外框">${V.I.trays}</button></div>`;
  }

  /* ---- forms ---- */
  function cardHTML(c) {
    const prog = c.lite && c.req ? `<div class="tk ${seenTicks.has(c.id) ? "" : "pre"} ${c.ok === c.req ? "full" : ""}" data-tk="${c.id}">${Array.from({ length: c.req }, (_, i) => `<i class="${i < c.ok ? "on" : ""}" style="--k:${i}"></i>`).join("")}<span class="ok">${V.I.tick}</span></div>`
      : c.lite ? '<div class="tk"></div>' : `<div class="ph6" data-st="${c.st}">${c.ph.map((v, i) => `${i ? `<span class="${v ? "on" : ""}"></span>` : ""}<b class="s${v}"></b>`).join("")}</div>`;
    const right = c.lite && c.req ? V.frac(c.ok, c.req) : `<span class="fr" style="color:var(--mu)">${esc(V.phaseNow(c))}</span>`;
    return `<button class="card ${c.id === sel ? "sel" : ""}" data-card="${c.id}" data-st="${c.st}"><div class="c1"><span class="no">${groupBy === "p" ? c.n : esc(c.p) + "/" + c.n}</span><span class="w">${c.st === "active" || groupBy === "s" ? "" : c.st}</span><span class="r">${right}</span></div><div class="sl" title="${esc(c.slug)}">${esc(c.slug)}</div><div class="nx" title="${esc(V.nextOf(c))}">${esc(V.nextOf(c))}</div>${prog}</button>`;
  }
  function groupHTML(g, cls, gridCls) {
    const open = g.closed ? [] : g.cs.filter(c => isOpenSt(c.st)), closed = g.closed ? g.cs : g.cs.filter(c => !isOpenSt(c.st)), show = unfold.has(g.key);
    let h = `<section class="${cls}"><h2 ${g.st ? `data-st="${g.st}"` : ""}>${esc(g.name)}<em>${g.cs.length}</em></h2>`;
    if (open.length) h += `<div class="${gridCls}">${open.map(cardHTML).join("")}</div>`;
    if (closed.length) {
      h += `<button class="fold" data-fold="${esc(g.key)}" data-tip="${show ? "收起" : "展开"}已结束的卡：done ${closed.filter(c => c.st === "done").length} · dropped ${closed.filter(c => c.st !== "done").length}"><span class="dots">${closed.map(c => `<i class="${c.st}"></i>`).join("")}</span></button>`;
      if (show) h += `<div class="rows">${closed.map(c => `<button class="row ${c.id === sel ? "sel" : ""}" data-card="${c.id}" data-st="${c.st}"><span class="n">${c.n}</span><span class="s">${esc(groupBy === "p" ? c.slug : c.p + " / " + c.slug)}</span>${c.lite && c.req ? V.frac(c.ok, c.req) : ""}</button>`).join("")}</div>`;
    }
    return h + "</section>";
  }
  function dotsHTML(gs) {
    const mt = cardMt(); let n = 0;
    return gs.map(g => {
      const subOf = groupBy === "s" ? c => c.p : c => c.st;
      const FILM = ["done", "active", "paused", "blocked", "todo", "backlog", "unknown", "dropped"];
      const order = groupBy === "s" ? [...new Set(g.cs.map(c => c.p))] : FILM.filter(st => g.cs.some(c => c.st === st));
      const subs = order.map(k => ({ k, cs: g.cs.filter(c => subOf(c) === k).sort((a, b) => a.n.localeCompare(b.n) || a.id.localeCompare(b.id)) }));
      return `<section class="dproj"><div class="dnum">${g.cs.length}<span class="dname">${esc(g.name)}</span></div><div class="drow">${subs.map(sb => `<div class="dgrp"><div class="dd">${sb.cs.map(c => `<button class="dot ${c.st} ${c.id === sel ? "sel" : ""}" data-card="${c.id}" data-st="${c.st}" style="--i:${n++}" aria-label="${esc(c.id + " " + c.slug)}"><span class="dtag"><span>${c.n}</span><span>·</span><span>${V.ago(mt[c.dir]) || ""}</span></span></button>`).join("")}</div><div class="dl"><span>${esc(sb.k)}</span><em>${sb.cs.length}</em></div></div>`).join("")}</div></section>`;
    }).join("");
  }
  function tableHTML(gs) {
    const mt = cardMt();
    const cols = [["n", "编号"], ["slug", "名称"], ...(groupBy !== "p" ? [["p", "项目"]] : []), ...(groupBy !== "s" ? [["st", "状态"]] : []), ...(groupBy !== "g" ? [["gov", "治理"]] : []), ["prog", "进度"], ["mt", "更新"]];
    const val = (c, k) => k === "prog" ? (c.lite ? (c.req ? c.ok / c.req : 0) : c.ph.filter(v => v === 2).length / 6) : k === "mt" ? mt[c.dir] || 0 : c[k];
    let h = `<table class="tbl"><thead><tr>${cols.map(([k, l]) => `<th data-sort="${k}" class="${sortK === k ? "on" + (sortDesc ? " desc" : "") : ""}">${l}</th>`).join("")}</tr></thead><tbody>`;
    gs.forEach(g => {
      const cs = sortK ? [...g.cs].sort((a, b) => { const x = val(a, sortK), y = val(b, sortK); return (x > y ? 1 : x < y ? -1 : 0) * (sortDesc ? -1 : 1); }) : g.cs;
      h += `<tr class="gh"><td colspan="${cols.length}">${esc(g.name)}<em>${cs.length}</em></td></tr>`;
      h += cs.map(c => `<tr data-card="${c.id}" data-st="${c.st}" class="${c.id === sel ? "sel" : ""}"><td class="n">${c.n}</td><td class="nm">${esc(c.slug)}</td>${groupBy !== "p" ? `<td class="mu">${esc(c.p)}</td>` : ""}${groupBy !== "s" ? `<td style="color:var(--c)">${c.st}</td>` : ""}${groupBy !== "g" ? `<td class="mu">${esc(c.gov)}</td>` : ""}<td>${c.lite && c.req ? `<span class="mt"><i style="width:${(c.ok / c.req * 100).toFixed(1)}%"></i></span>${V.frac(c.ok, c.req)}` : `<span class="mu">${esc(V.phaseNow(c))}</span>`}</td><td class="mu">${V.ago(mt[c.dir])}</td></tr>`).join("");
    });
    return h + "</tbody></table>";
  }
  function bodyHTML() {
    const gs = groupsOf(), f = form();
    if (!gs.length) {
      const any = V.D.cards.some(c => V.inScope(c.p));
      return `<div class="empty-b">${any ? `过滤后没有卡片。<br><button data-fltall>全部显示</button>` : `这个范围里没有卡片${V.scope ? `。<br><button data-scope-all>看全部项目</button>` : "。"}`}</div>`;
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
    tkObs = new IntersectionObserver(es => es.forEach(e => { if (!e.isIntersecting) return; seenTicks.add(e.target.dataset.tk); const el = e.target; requestAnimationFrame(() => el.classList.remove("pre")); tkObs.unobserve(el); }), { root: b, threshold: .6 });
    $$(".tk.pre", b).forEach(t => (V.RM ? t.classList.remove("pre") : tkObs.observe(t)));
    paintDetail();
  }

  /* ---- detail under the board ---- */
  const reqCache = {};
  function reqsOf(c) {   // Req headings of a lite card's design.md, re-read when the file changes
    const rel = c.dir + "/design.md", mt = V.D.mtime.dev[rel]; if (!c.lite || !mt) return null;
    const hit = reqCache[c.id]; if (hit && hit.mt === mt) return hit.list;
    if (!hit || hit.mt !== mt) {
      reqCache[c.id] = { mt, list: hit ? hit.list : undefined };
      V.api("/raw/dev/" + rel).then(r => r.text()).then(t => {
        const out = []; t.replace(/^### Req-(\d+)\s+(\S+)\s*[—-]\s*(.+)$/gm, (_, n, st, title) => out.push({ n, st, t: title }));
        reqCache[c.id] = { mt, list: out }; if (sel === c.id) paintDetail();
      }).catch(() => { reqCache[c.id] = { mt, list: [] }; });
    }
    return reqCache[c.id].list;
  }
  const gitLink = c => V.GITWEB ? esc(V.GITWEB) + "?p=" + encodeURIComponent(c.p) + ";a=summary" + (c.branch ? ";h=refs/heads/" + encodeURIComponent(c.branch) : "") : "";
  function detailHTML() {
    const c = V.card(sel), head = `<button class="ib bx" data-col="det" data-tip="关闭详情，再点一张卡会重新打开" aria-label="关闭详情">${V.I.x}</button>`;
    if (!c) return head + '<div class="hint">单击一张卡看详情，双击直接打开它的 design.md，⇧ 单击在右栏打开。</div>';
    const docs = V.docsOf(c).map(x => x.rel), has = f => docs.includes(c.dir + "/" + f);
    const key = docs.filter(d => !d.slice(c.dir.length + 1).includes("/")).sort((a, b) => (b.endsWith("/design.md") - a.endsWith("/design.md")) || a.localeCompare(b));
    const rq = reqsOf(c);
    const links = [has("progress.md") && `<button data-open="dev:${esc(c.dir)}/progress.md">progress</button>`, has("log.md") && `<button data-open="dev:${esc(c.dir)}/log.md">log</button>`,
      `<button data-diff="${esc(c.id)}">±diff</button>`, V.GITWEB && `<a href="${gitLink(c)}" target="_blank" rel="noopener" data-tip="在 gitweb 里看这个项目${c.branch ? "的 " + esc(c.branch) + " 分支" : ""}">code ↗</a>`].filter(Boolean).join("");
    const reqs = c.lite ? `<div class="rhead"><span class="vt">${Array.from({ length: c.req }, (_, i) => `<i class="${i < c.ok ? "" : "o"}"></i>`).join("")}</span><span class="bfr"><b>${c.ok}</b><i>/</i><s>${c.req}</s></span></div>`
      + (rq ? rq.map(r => `<button class="rq ${r.st === "已验证" ? "" : "open"}" data-rq data-tip="Req-${r.n} · ${esc(r.st)}"><span class="ck">${r.st === "已验证" ? V.I.tick : ""}</span><b>R${r.n}</b><span>${esc(r.t)}</span></button>`).join("") : '<div class="hint" style="padding:0">读取 Req…</div>')
      : `<div class="rhead"><span class="vt">${c.ph.map(v => `<i class="${v === 2 ? "" : v === 1 ? "h" : "o"}"></i>`).join("")}</span><span class="bfr"><s style="font-size:11px;color:var(--mu)">${esc(V.phaseNow(c))}</s></span></div>`
        + c.steps.map(s => { const i = s.indexOf(":"); return `<div class="rq"><span class="ck">${SV.stepFill(s.slice(i + 1)) === "done" ? V.I.tick : ""}</span><b>${esc(s.slice(0, i))}</b><span>${esc(s.slice(i + 1))}</span></div>`; }).join("");
    return head + `<div class="bdg" data-st="${c.st}">
      <div class="brow big"><div class="hero"><span class="hn">${c.n}</span><span class="hline"><span class="hm"><span class="hst">${c.st}</span>　${esc(c.p)}　${esc(c.gov)}${c.deps && c.deps !== "—" ? "　deps " + esc(c.deps) : ""}</span></span></div></div>
      <div class="brow"><div class="sfl"><span class="hsl">${esc(c.slug)}</span>${key.map(d => `<button class="kf" data-open="dev:${esc(d)}" data-tip="${esc(d)}">${esc(d.slice(c.dir.length + 1))}</button>`).join("")}</div></div>
      <div class="brow"><div class="bv nx">${esc(V.nextOf(c))}</div></div>
      ${c.now ? `<div class="brow"><div class="bv"><span><b>now</b>${esc(c.now)}</span></div></div>` : ""}
      ${c.block && c.block !== "—" ? `<div class="brow"><div class="bv blk"><span><b>block</b>${esc(c.block)}</span></div></div>` : ""}
      <div class="brow"><div class="blinks">${links}</div></div>
      <div class="brow"><div>${reqs}</div></div>
    </div>`;
  }
  function paintDetail() { if (V.view === "board") $("#bdet").innerHTML = detailHTML(); }
  function selectCard(id, open) {
    sel = id; store.set("sel", id);
    $$("#board [data-card]").forEach(e => e.classList.toggle("sel", e.dataset.card === id));
    if (!V.RM) { const d = $("#board .dot.sel .dtag"); if (d) d.animate([{ opacity: 0, transform: "translateY(3px)" }, { opacity: 1, transform: "none" }], { duration: 220, easing: "ease-out" }); }
    if (open !== false && V.W.dc) { V.W.dc = false; V.applyW(); V.saveW(); }
    paintDetail();
  }
  V.pickCard = id => { selectCard(id); const el = $(`#bscroll [data-card="${V.cssEsc(id)}"]`); if (el) el.scrollIntoView({ block: "nearest", behavior: V.RM ? "auto" : "smooth" }); };
  function closeDetail() { if (!sel && V.W.dc) return; sel = null; store.set("sel", null); V.W.dc = true; V.applyW(); V.saveW(); $$("#board [data-card].sel").forEach(e => e.classList.remove("sel")); paintDetail(); }
  V.on("detail-close", closeDetail);
  V.revealCard = c => { unfold.add((groupBy === "s" ? "s:" + c.st : groupBy === "g" ? "g:" + c.gov : "p:" + c.p)); hidden.delete(c.st); store.set("hide", [...hidden]); render(); V.pickCard(c.id); };
  function moveSel(key) {
    const els = $$("#bscroll [data-card]").filter(e => e.offsetParent); if (!els.length) return;
    const cur = els.find(e => e.dataset.card === sel); if (!cur) return V.pickCard(els[0].dataset.card);
    let nx = null;
    if ((key === "ArrowRight" || key === "ArrowLeft") && form() !== "cols") nx = els[els.indexOf(cur) + (key === "ArrowRight" ? 1 : -1)];
    else {
      const r = cur.getBoundingClientRect(), horiz = key === "ArrowRight" || key === "ArrowLeft", fwd = key === "ArrowRight" || key === "ArrowDown"; let best = 1e9;
      els.forEach(e => {
        const q = e.getBoundingClientRect();
        const d1 = horiz ? (fwd ? q.left - r.right : r.left - q.right) : (fwd ? q.top - r.bottom : r.top - q.bottom);
        if (d1 < -2) return;
        const d = d1 * 3 + (horiz ? Math.abs(q.top + q.height / 2 - (r.top + r.height / 2)) : Math.abs(q.left + q.width / 2 - (r.left + r.width / 2)));
        if (d < best) { best = d; nx = e; }
      });
    }
    if (nx) V.pickCard(nx.dataset.card);
  }
  const openCard = (id, e) => { const c = V.card(id), d = c && V.mainDoc(c); if (d) V.openDoc("dev", d, e); else V.toast("这张卡没有 design.md"); };

  /* ---- filter popover ---- */
  function fltPop(btn) {
    const count = st => V.D.cards.filter(c => V.inScope(c.p) && c.st === st).length;
    const sts = STATES.filter(st => count(st));
    V.pop("fltPop", `<div class="pt">显示哪些状态</div><div class="chips">${sts.map(st => `<button class="chip ${hidden.has(st) ? "off" : ""}" data-chip="${st}" data-st="${st}" data-tip="${hidden.has(st) ? "显示" : "隐藏"} ${st} 的卡"><i class="gl ${st}"></i>${st}<em>${count(st)}</em></button>`).join("")}</div>${hidden.size ? '<button class="fall" data-fltall>全部显示</button>' : ""}`, btn || $("[data-flt]"), "right");
  }
  const setHidden = () => { store.set("hide", [...hidden]); render(); V.untip(); V.status(); };

  /* ---- card diff view ---- */
  V.views.diff = (k, loc) => {
    const el = $("#diffv");
    el.innerHTML = `<div class="phd"><button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button><div class="ppath"><bdi>${esc(loc.card)} / <b>改动</b></bdi></div><button class="ib" data-goboard="1" data-tip="回看板" aria-label="回看板">${V.I.grid}</button></div><div class="dbody scroll"><div class="hint">读取中…</div></div>`;
    V.api("/api/diff?card=" + encodeURIComponent(loc.card)).then(r => r.text()).then(t => {
      const files = t.split(/\n(?=diff --git )/).filter(s => s.trim());
      $(".dbody", el).innerHTML = files.length ? files.map(f => {
        const m = /^diff --git a\/(\S+)/.exec(f), name = m ? m[1] : "";
        return `<div class="dfile"><h3>${name ? `<button data-open="dev:${esc(name)}">${esc(name)}</button>` : ""}</h3><div class="md"><pre class="dif">${f.split("\n").map(l => `<div class="${/^\+(?!\+\+)/.test(l) ? "a" : /^-(?!--)/.test(l) ? "d" : /^@@/.test(l) ? "h" : ""}">${esc(l) || " "}</div>`).join("")}</pre></div></div>`;
      }).join("") : '<div class="hint">这张卡在 dev_root 里没有未提交或最近的改动。</div>';
    }).catch(e => { $(".dbody", el).innerHTML = `<div class="derr"><b>读不到改动</b><br>${esc(e.message)}</div>`; });
    V.status();
  };
  V.statusFns.diff = () => `<span><b>±diff</b>　${esc((V.P.A.loc || {}).card || "")}</span><span class="sp"></span>${V.stamp()}`;

  /* ---- the board view ---- */
  V.views.board = () => { render(); V.status(); if (sel) { const el = $(`#bscroll [data-card="${V.cssEsc(sel)}"]`); if (el) el.scrollIntoView({ block: "nearest" }); } };
  V.statusFns.board = () => {
    const n = V.D.cards.filter(c => V.inScope(c.p)).length, hint = store.get("hintN", 0) < 5;
    return `<span><b>看板</b>　${n} 张卡${hidden.size ? "，隐藏了 " + [...hidden].join("、") : ""}</span>${hint ? "<span>单击看详情，双击打开 design.md，方向键移动</span>" : ""}<span class="sp"></span>${V.stamp()}`;
  };
  V.on("nav", (k, loc) => { if (loc.kind === "board") store.set("hintN", store.get("hintN", 0) + 1); });
  V.on("data", () => { if (V.view === "board") { render(); V.status(); } });
  V.on("scope", () => { if (V.view === "board") { render(); V.status(); } });
  V.on("narrow", () => { if (V.view === "board" && !store.get("form", null)) render(); });

  let clickT = null;
  V.on("click", e => {
    const t = e.target;
    if (V.view === "board" && sel && !t.closest("#bdet,[data-card],.pop,#hgut,.qo,#bhd")) closeDetail();
  });
  V.click("[data-grp]", el => { groupBy = el.dataset.grp; store.set("grp", groupBy); unfold.clear(); render(); });
  V.click("[data-trays]", () => { trays = !trays; store.set("trays", trays); render(); V.untip(); });
  V.click("[data-form]", el => {
    store.set("form", el.dataset.form); render();
    if (el.dataset.form === "dots" && !V.RM) { const b = $("#bscroll"); b.classList.add("denter"); setTimeout(() => b.classList.remove("denter"), 1400); }
  });
  V.click("th[data-sort]", el => { const k = el.dataset.sort; if (sortK === k) { if (sortDesc) { sortK = ""; sortDesc = false; } else sortDesc = true; } else { sortK = k; sortDesc = false; } store.set("sortK", sortK); store.set("sortDesc", sortDesc); render(); });
  V.click("[data-chip]", el => { const s = el.dataset.chip; hidden.has(s) ? hidden.delete(s) : hidden.add(s); setHidden(); fltPop(); });
  V.click("[data-fltall]", () => { hidden.clear(); setHidden(); if (V.isPop("fltPop")) fltPop(); });
  V.click("[data-scope-all]", () => V.setScope(""));
  V.click("[data-flt]", el => (V.isPop("fltPop") ? V.closePops() : fltPop(el)));
  V.click("[data-fold]", el => { const p = el.dataset.fold; unfold.has(p) ? unfold.delete(p) : unfold.add(p); render(); });
  V.click("[data-rq]", el => el.classList.toggle("x"));
  V.click("[data-diff]", (el, e) => V.nav("A", { kind: "diff", card: el.dataset.diff }));
  V.click("[data-card]", (el, e) => {
    const id = el.dataset.card;
    if (e.shiftKey) return openCard(id, e);
    if (e.detail >= 2) { clearTimeout(clickT); return openCard(id, e); }
    selectCard(id);
  });
  V.hotkey("ArrowUp", e => (V.view === "board" ? moveSel(e.key) : false));
  ["ArrowDown", "ArrowLeft", "ArrowRight"].forEach(k => V.hotkey(k, e => (V.view === "board" ? moveSel(e.key) : false)));
  V.hotkey("Enter", e => (V.view === "board" && sel ? openCard(sel, e) : false));
  V.layer(10, () => V.view === "board" && !!sel, closeDetail);
  document.addEventListener("mouseover", e => {
    const d = e.target.closest(".dot[data-card]"), pop = $("#dotpop");
    if (!d) { pop.classList.remove("on"); return; }
    const c = V.card(d.dataset.card); if (!c) return; seenTicks.add(c.id);
    pop.innerHTML = cardHTML(c); pop.classList.add("on");
    const r = d.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
    pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + "px"; pop.style.top = (r.top - h - 10 < 8 ? r.bottom + 10 : r.top - h - 10) + "px";
  });
})(V2);
