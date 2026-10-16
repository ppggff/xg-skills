/* status viewer v2 — the board's time form (054): one row per card on a time axis with no grid. The card's status is
   the row's colour, its requirements are bars across the middle (written → settled, coloured by the state word then,
   darker where they overlap). Drag or scroll sideways to pan; the range only zooms. A click sets the indicator and
   selects the card, and the card detail under the board shows that moment. Data: /api/history. */
"use strict";
(function (V) {
  const { $, $$, esc, store } = V;
  const DAY = 864e5;
  const RANGES = [["14", "2 周"], ["42", "6 周"], ["all", "全部"]];
  const LST = { draft: "todo", executing: "active", closing: "paused", done: "done" };   // a lite status in the board's colours
  const KN = { done: "已验证", todo: "待验证", drop: "放弃", bad: "失败 / 阻塞", plan: "仅方案" };
  let H = null, loading = null, geo = null, pant = null, pan = 0;   // history; drawn geometry; the left edge's moment (null: follow today)
  V.timeCur = null;   // the indicator, in ms: now until it is moved

  const range = () => store.get("tmRange", "14");
  const histOf = c => (H && H[c.id]) || { status: [], reqs: {}, first: "", last: "" };
  const rangeOf = c => SV.tmRange(histOf(c), !V.OPEN_ST.includes(c.st), geo ? geo.now : Date.now());
  const two = n => String(n).padStart(2, "0");
  const fmt = ms => { const d = new Date(ms); return `${d.getMonth() + 1}-${two(d.getDate())} ${two(d.getHours())}:${two(d.getMinutes())}`; };
  const stOf = (c, cs) => (c.lite ? (cs ? LST[cs] || "unknown" : "") : c.st);   // the board-colour state of a card at a moment
  const stWord = (c, cs) => (c.lite ? cs || "" : c.st);
  function load() {
    if (loading) return loading;
    loading = V.json("/api/history").then(d => { H = d; loading = null; V.emit("time-data"); }).catch(() => { loading = null; H = H || {}; V.emit("time-data"); });
    return loading;
  }
  V.on("data", () => { if (H) load(); });

  /* ---- the form, drawn by the board with its groups ---- */
  V.timeRangeBtn = () => { const r = RANGES.find(x => x[0] === range()) || RANGES[0];
    return `<button data-tmnow data-tip="指示线回到现在">现在</button><button data-tmr data-tip="时间范围：${r[1]}（点击换下一个：${RANGES.map(x => x[1]).join(" → ")}）">${r[1]}</button>`; };
  V.timeHTML = (gs, B) => {
    if (!H) { load(); return '<div class="hint">读取卡片的历史…</div>'; }
    const now = Date.now(), box = $("#bscroll"), cs = gs.flatMap(g => g.cs);
    const d0 = new Date(Math.min(now - 14 * DAY, ...cs.map(c => SV.tmRange(histOf(c), !V.OPEN_ST.includes(c.st), now)[0]))).setHours(0, 0, 0, 0);
    const pad = parseFloat(getComputedStyle(box).paddingLeft) + parseFloat(getComputedStyle(box).paddingRight);
    const lw = 0, W = Math.max(80, box.clientWidth - pad);   // the axis takes the whole row; the card's name floats over its left end
    const span = range() === "all" ? now - d0 : Math.min(now - d0, +range() * DAY), k = W / span, total = Math.round((now - d0) * k);
    pan = Math.min(Math.max(0, pant === null ? total - W : Math.round((pant - d0) * k)), total - W);
    geo = { d0, k, W, total, now, lw };
    if (V.timeCur === null) V.timeCur = now;
    const X = ms => Math.round((Math.min(Math.max(ms, d0), now) - d0) * k);
    const pxDay = DAY * k, step = pxDay >= 44 ? 1 : pxDay >= 7 ? 7 : 14;
    let head = "";
    for (let d = d0 + DAY; d <= now; d += DAY) {
      const dt = new Date(d); if (step > 1 && dt.getDay() !== 1) continue; if (step === 14 && Math.round((d - d0) / DAY / 7) % 2) continue;
      head += `<span class="tm-d" style="left:${X(d)}px">${dt.getMonth() + 1}-${two(dt.getDate())}${step === 1 ? `<small>${"日一二三四五六"[dt.getDay()]}</small>` : ""}</span>`;
    }
    head += `<span class="tm-d now" style="left:${X(now)}px">今天</span>`;
    let alt = false;
    const row = c => { alt = !alt; return rowHTML(c, X, B, alt); };
    const body = gs.map(g => {
      const { open, closed, show } = B.split(g);
      alt = false;
      return `<div class="tm-gh"${g.st ? ` data-st="${g.st}"` : ""}>${esc(g.name)}<em>${g.cs.length}</em></div>` + open.map(row).join("")
        + (closed.length ? `<div class="tm-fold">${B.foldHTML(g, closed, show)}</div>` + (show ? closed.map(row).join("") : "") : "");
    }).join("");
    return `<div class="tmv" style="--tm-pan:${pan}px"><div class="tm-head"><div class="tm-track"><div class="tm-pan" style="width:${total}px">${head}</div></div>`
      + `<span class="tm-cur"></span></div>${body}<div class="tm-line"></div></div>`;
  };
  function rowHTML(c, X, B, alt) {
    const h = histOf(c), [a, b] = rangeOf(c), st = h.status;
    let band = "";
    if (st.length) st.forEach((e, i) => {
      const s = SV.tmMs(e.t), t2 = i + 1 < st.length ? SV.tmMs(st[i + 1].t) : geo.now;
      band += e.v === "done" ? `<i class="tm-cap" style="left:${X(s)}px"></i>` : `<i class="tm-band s-${LST[e.v] || "unknown"}" style="left:${X(s)}px;width:${Math.max(3, X(t2) - X(s))}px"></i>`;
    });
    else band = `<i class="tm-band s-${c.st}" style="left:${X(a)}px;width:${Math.max(3, X(b) - X(a))}px"></i>`;
    // requirement bars, each kept inside the card's span (shifted back rather than cut where it would fall off an end)
    const x0 = X(a), x1 = Math.max(x0 + 1, X(b)), fit = (l, w) => { w = Math.min(w, x1 - x0); return [Math.min(Math.max(l, x0), x1 - w), w]; };
    let bars = "";
    Object.keys(h.reqs).sort((p, q) => p - q).forEach(n => SV.tmSpans(h.reqs[n], a, b).forEach(x => {
      const [l, w] = fit(X(x.a), Math.max(3, X(x.b) - X(x.a)));
      bars += `<i class="tm-q k-${x.b === x.a && x.end ? x.end : x.k}" style="left:${l}px;width:${w}px"></i>`;
      if (x.end && x.b > x.a) { const [e, ew] = fit(X(x.b) - 4, 4); bars += `<i class="tm-q end k-${x.end}" style="left:${e}px;width:${ew}px"></i>`; }
    }));
    return `<div class="tm-row${alt ? " alt" : ""}" data-trow="${esc(c.id)}"><div class="tm-track"><div class="tm-pan" style="width:${geo.total}px">${band}${bars}</div></div>`
      + `<button class="tm-name ${B.selCls(c)}" data-card="${esc(c.id)}" data-st="${c.st}"><span class="n">${c.n}</span><span class="s">${esc(c.slug)}</span>`
      + `${c.lite && c.req ? V.frac(c.ok, c.req) : ""}</button></div>`;
  }
  // after the board drew the form: the indicator and its label
  V.timeAfter = () => { fitNames(); placeLine(); };
  // every row's name takes the width of the longest number and name (at most half the axis), so the fades line up;
  // the done count is left out and may run into the fade
  function fitNames() {
    const v = $("#bscroll .tmv"); if (!v) return;
    const names = $$(".tm-row .tm-name", v), track = $(".tm-head .tm-track", v); if (!names.length || !track) return;
    const need = Math.max(...names.map(b => $(".n", b).offsetWidth + 6 + $(".s", b).scrollWidth)) + 18;
    v.style.setProperty("--tm-nw", Math.round(Math.min(need, track.clientWidth / 2)) + "px");
  }
  function placeLine() {
    const v = $("#bscroll .tmv"), line = v && $(".tm-line", v), lab = v && $(".tm-cur", v); if (!line || !geo) return;
    const x = V.timeCur === null ? -1 : geo.lw + (V.timeCur - geo.d0) * geo.k - pan, off = V.timeCur === null || x < geo.lw - 1 || x > geo.lw + geo.W + 1;
    line.style.display = lab.style.display = off ? "none" : "block";
    if (!off) { line.style.left = lab.style.left = x + "px"; lab.textContent = fmt(V.timeCur); lab.classList.toggle("left", x > geo.lw + geo.W - 90); }   // near the right edge the label sits left of the line
  }
  function setPan(px) {
    if (!geo) return;
    pan = Math.min(Math.max(0, px), geo.total - geo.W);
    pant = pan >= geo.total - geo.W - 1 ? null : geo.d0 + pan / geo.k;   // at the right end it keeps following today
    const v = $("#bscroll .tmv"); if (v) v.style.setProperty("--tm-pan", pan + "px");
    placeLine();
  }
  const tAt = (track, clientX) => geo.d0 + (Math.min(Math.max(0, clientX - track.getBoundingClientRect().left), geo.W) + pan) / geo.k;
  // the indicator moves to t; with a card it selects it (which opens the detail), else the detail follows the moment
  function setCur(t, id) {
    V.timeCur = Math.min(geo.now, Math.max(geo.d0, t));
    const x = (V.timeCur - geo.d0) * geo.k;   // keep the indicator in the window
    if (x < pan + 20) setPan(x - 20); else if (x > pan + geo.W - 20) setPan(x - geo.W + 20);
    placeLine();
    if (id) V.pickCard(id); else V.emit("time-moment");
  }
  // ← → move the indicator (⇧ by the hour); ↑ ↓ stay the board's row movement
  V.timeKey = e => {
    if ((e.key !== "ArrowLeft" && e.key !== "ArrowRight") || !geo) return false;
    setCur((V.timeCur === null ? geo.now : V.timeCur) + (e.key === "ArrowLeft" ? -1 : 1) * (e.shiftKey ? 36e5 : DAY), null);
    return true;
  };

  /* ---- the moment, as the board's card (hover) and as the board's card detail (selected) ---- */
  const countsOf = reqs => ["todo", "done", "drop", "bad", "plan"].map(k => [k, reqs.filter(r => r.k === k).length]).filter(x => x[1]);
  function cardAt(c, t) {
    const h = histOf(c), { cs, reqs } = SV.tmStateAt(h, t), [a, b] = rangeOf(c), ok = reqs.filter(r => r.k === "done").length;
    const near = reqs.filter(r => r.k !== "done" || (r.last && Math.abs(SV.tmMs(r.last.t) - t) < 6 / geo.k));
    const word = t < a ? "还没开" : stWord(c, cs) + (t > b && !V.OPEN_ST.includes(c.st) ? " · 已结束" : "");
    return `<div class="card tmc" data-st="${stOf(c, cs) || c.st}"><div class="c1"><span class="no">${esc(c.id)}</span><span class="w">${esc(word)}</span>`
      + `<span class="r">${reqs.length ? V.frac(ok, reqs.length) : ""}</span></div><div class="sl">${esc(c.slug)}</div>`
      + `<div class="nx">${fmt(t)}${reqs.length ? " · " + countsOf(reqs).map(([k, n]) => KN[k] + " " + n).join(" · ") : ""}</div>`
      + (reqs.length ? `<div class="tk ${ok === reqs.length ? "full" : ""}"><i style="--p:${(ok / reqs.length).toFixed(3)}"></i><span class="ok">${V.I.tick}</span></div>` : "")
      + (near.length ? `<div class="tmq">${near.slice(0, 8).map(rqHTML).join("")}${near.length > 8 ? `<div class="more">… 另有 ${near.length - 8} 个</div>` : ""}</div>` : "") + "</div>";
  }
  const rqHTML = r => `<div class="rq ${r.k === "done" ? "" : r.k === "drop" ? "open drop" : "open"}" data-tip="Req-${r.n} · ${esc(r.w || "无状态词")}${r.last ? " · 最近变化 " + esc(r.last.t.slice(5)) : ""}">`
    + `<span class="ck">${r.k === "done" ? V.I.tick : ""}</span><b>R${r.n}</b><span>${esc(r.title)}</span></div>`;
  // the detail's parts for the selected card at the indicator: null when the form has no indicator
  V.timeMoment = c => {
    if (V.timeCur === null || !H || !geo) return null;
    const t = V.timeCur, h = histOf(c), { cs, reqs } = SV.tmStateAt(h, t), [a, b] = rangeOf(c), ok = reqs.filter(r => r.k === "done").length;
    const label = { new: e => "写入（" + esc(e.word || "无") + "）", word: e => esc(e.from || "无") + " → " + esc(e.to), title: () => "改标题", stmt: () => "改陈述", gone: () => "删除" };
    const near = Object.keys(h.reqs).flatMap(n => h.reqs[n].map(e => ({ n, e }))).filter(x => Math.abs(SV.tmMs(x.e.t) - t) < 12 * 36e5).sort((p, q) => p.e.t.localeCompare(q.e.t));
    const order = ["todo", "bad", "plan", "done", "drop"], sorted = reqs.slice().sort((p, q) => order.indexOf(p.k) - order.indexOf(q.k) || p.n - q.n);
    const word = t < a ? "卡还没开" : "卡 " + stWord(c, cs) + (t > b && !V.OPEN_ST.includes(c.st) ? "，已结束" : "");
    return {
      nx: `<div class="bv nx">${fmt(t)} 这一刻 · ${esc(word)}</div>`,
      frac: reqs.length ? `${ok}/${reqs.length}` : "",
      counts: `<div class="bv">${countsOf(reqs).map(([k, n]) => `<span><b>${KN[k]}</b>${n}</span>`).join("") || "<span>这一刻没有需求</span>"}</div>`,
      near: near.length ? `<div class="btodo"><div class="bth">前后 12 小时的变化<em>${near.length}</em></div>`
        + near.map(x => `<div class="tmev${SV.tmMs(x.e.t) > t ? " later" : ""}"><code>${esc(x.e.t.slice(5))}</code><b>R${x.n}</b><span>${label[x.e.type](x.e)}</span></div>`).join("") + "</div>" : "",
      reqs: reqs.length ? `<div class="rhead"><span class="vt">${sorted.map(r => `<i class="${r.k === "done" ? "" : "o"}"></i>`).join("")}</span><span class="bfr"><b>${ok}</b><i>/</i><s>${reqs.length}</s></span></div>`
        + sorted.map(rqHTML).join("") : "",
    };
  };

  /* ---- pointer (mouse or touch): a sideways drag pans, a short press sets the indicator, hovering shows the moment.
     A press on a row's bars sets the indicator and selects the card; one on the date head sets the indicator only; the
     name up to where its wash starts fading takes no time — a press there selects the card and leaves the indicator ---- */
  let drag = null;
  const pop = () => $("#dotpop");
  const hit = t => t.closest && t.closest("#bscroll .tm-row .tm-track, #bscroll .tm-head .tm-track");
  const trackOf = id => (id ? $(`#bscroll .tm-row[data-trow="${V.cssEsc(id)}"] .tm-track`) : $("#bscroll .tm-head .tm-track"));
  document.addEventListener("pointerdown", e => {
    const el = e.button === 0 && hit(e.target); if (!el || !geo) return;
    const row = el.closest(".tm-row");
    drag = { x: e.clientX, y: e.clientY, pan, moved: false, id: row ? row.dataset.trow : null };
    if (e.pointerType === "mouse") e.preventDefault();
  });
  document.addEventListener("pointermove", e => {
    if (drag && e.pointerType === "mouse" && !e.buttons) { drag = null; document.body.classList.remove("tm-panning"); }   // the release was missed
    if (drag) {
      const dx = e.clientX - drag.x;
      if (!drag.moved && Math.abs(dx) > 3 && Math.abs(dx) >= Math.abs(e.clientY - drag.y)) { drag.moved = true; document.body.classList.add("tm-panning"); pop().classList.remove("on"); }
      if (drag.moved) { setPan(drag.pan - dx); return; }
    }
    if (e.pointerType !== "mouse") return;
    const el = e.target.closest && e.target.closest("#bscroll .tm-row .tm-track"); if (!el || !geo) return;
    const row = el.closest(".tm-row"), tr = $(".tm-track", row), c = V.card(row.dataset.trow); if (!c) return;
    const p = pop(); p.innerHTML = cardAt(c, tAt(tr, e.clientX)); p.classList.add("on");
    const w = p.offsetWidth, hgt = p.offsetHeight;
    p.style.left = Math.max(8, Math.min(innerWidth - w - 8, e.clientX + 14)) + "px";
    p.style.top = (e.clientY + 16 + hgt > innerHeight - 8 ? Math.max(8, e.clientY - hgt - 12) : e.clientY + 16) + "px";
  });
  document.addEventListener("pointerup", e => {
    if (!drag) return;
    const d = drag; drag = null; document.body.classList.remove("tm-panning");
    // the row is looked up again: a refresh while the pointer was down replaces it
    const tr = trackOf(d.id);
    if (!d.moved && geo && tr && Math.abs(e.clientY - d.y) < 8) setCur(tAt(tr, e.clientX), d.id);
  });
  document.addEventListener("pointercancel", () => { drag = null; document.body.classList.remove("tm-panning"); });
  document.addEventListener("wheel", e => {
    if (!geo || !e.target.closest || !e.target.closest("#bscroll .tmv") || Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
    e.preventDefault(); setPan(pan + e.deltaX); pop().classList.remove("on");
  }, { passive: false });
  document.addEventListener("mouseleave", () => pop().classList.remove("on"));
  $("#bscroll").addEventListener("scroll", () => pop().classList.remove("on"), { passive: true });
  // a new width redraws the axis (window, side columns, the detail's gutter): the moment at the left edge stays
  let lastW = 0;
  new ResizeObserver(() => { const w = $("#bscroll").clientWidth; if (w === lastW) return; lastW = w; if ($("#bscroll .tmv")) V.setForm("time"); }).observe($("#bscroll"));
  V.click("[data-tmnow]", () => { V.timeCur = Date.now(); pant = null; V.setForm("time"); V.emit("time-moment"); V.untip(); });
  V.click("[data-tmr]", () => { const i = RANGES.findIndex(x => x[0] === range()); store.set("tmRange", RANGES[(i + 1) % RANGES.length][0]); pant = null; V.setForm("time"); V.untip(); });
})(V2);
