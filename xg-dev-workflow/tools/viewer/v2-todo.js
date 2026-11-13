/* status viewer v2 — todo: a directory of markdown files, <dev_root>/todo/*.md, as a view beside the board. Each file
   is read like any doc; its checklist lines are the todos, @words tag a project (older #words too), wikilinks point at
   docs. The nav lists the files under its todo section; this view shows every todo across them as a table (待办), or
   what was made, done and due in a period (回顾); the reader opens and edits a file.
   Writes carry the version the page shows, so a file changed elsewhere in between is refused, never overwritten. */
"use strict";
(function (V) {
  const { $, $$, esc } = V, store = V.store;
  // per file: text/version follow the disk; shown/base are the version on screen — edits address its lines and are
  // sent with it, so a file that moved underneath is refused (409) instead of having the wrong line changed
  const F = V.todoFiles = {};
  let loaded = false;
  const DIR = "todo/", names = () => (V.D.tree ? V.D.tree.dev.map(x => x.path).filter(p => /^todo\/[^/]+\.md$/.test(p)).map(p => p.slice(DIR.length)) : []);

  function load() {
    const want = names();
    Object.keys(F).forEach(n => { if (!want.includes(n)) delete F[n]; });
    return Promise.all(want.map(n => V.api("/raw/dev/" + DIR + encodeURIComponent(n)).then(r => r.text().then(t => {
      const f = F[n] || (F[n] = {}); f.text = t; f.version = r.headers.get("X-Version") || "";
    })).catch(() => {}))).then(() => { loaded = true; });
  }
  V.todoWrite = (op, name, extra) => fetch("/api/todo", { method: "POST", headers: { "Content-Type": "application/json", "X-SV-Write": "1" },
    body: JSON.stringify(Object.assign({ op, file: name }, extra)) })
    .then(r => r.json().catch(() => ({})).then(d => ({ ok: r.ok, status: r.status, d })))
    .then(res => {
      if (res.status === 401) { V.authLost(); return res; }   // the panel keeps its text: nothing to re-read without a login
      const why = res.d && res.d.error;
      if (!res.ok) V.toast(why === "exists" ? "已经有同名的文件" : why === "hidden" ? "没写入：文件末尾有未闭合的代码块，新条目会被藏住" : why === "not-utf8" ? "没写入：这个文件不是 UTF-8"
        : res.status === 409 ? "这个 todo 文件在别处改过了，已重新读取，请再改一次" : "保存失败（" + res.status + "）");
      return V.load().then(() => V.emit("data")).then(() => res);   // the tree, the reader and this view all re-read
    }).catch(() => { V.toast("保存失败：连不上 viewer"); return { ok: false }; });
  // the version edits are addressed by: this view's snapshot once it has painted, else (rows shown elsewhere) the disk text
  const seen = n => (F[n].shown != null ? F[n].shown : F[n].text);
  const TICK_MS = 600;
  const refresh = () => load().then(paint).catch(e => { const b = $("#tscroll"); if (b) b.innerHTML = `<div class="derr"><b>读不到 todo 目录</b><br>${esc(e.message)}</div>`; });

  // an item's text: wikilinks and links open their doc, @tags and #tags are chips — tags only in the plain text between
  // links, and every piece escaped once, so nothing lands inside an attribute
  const LINK = /\[\[([^\]]+)\]\]|\[([^\]]+)\]\(([^)\s]+)\)/g;
  const link = (key, label, miss, line) => (key ? `<button class="tdl" data-open="${esc(key)}"${line ? ` data-oline="${line}"` : ""} data-tip="${esc(key)}">${esc(label)}</button>`
    : `<span class="tdl broken" data-tip="找不到：${esc(miss)}">${esc(label)}</span>`);
  const plain = t => esc(t).replace(/(^|\s)([@#])([\w.-]+)/g, '$1<span class="ttag">$2$3</span>');
  V.todoItemHTML = (text, file) => {
    let h = "", last = 0;
    text.replace(LINK, (all, wiki, label, href, at) => {
      h += plain(text.slice(last, at)); last = at + all.length;
      const c = wiki && V.cardOf(wiki);
      h += c ? `<button class="tdl tcard" data-open="dev:${esc(V.mainDoc(c) || c.dir)}" data-tip="${esc(c.id + " " + c.slug + " · " + c.st)}"><i class="cdot" data-st="${esc(c.st)}"></i>${esc(c.n + " " + c.slug)}</button>`
        : wiki ? link(SV.resolveWikiAny("[[" + wiki + "]]", V.D.sets), wiki.split("|").pop().split("#")[0].split("/").pop(), wiki, (/#L(\d+)$/.exec(wiki) || [])[1])
        : link(SV.resolveLink(href, "dev", DIR + file, V.D.sets), label, href);
      return all;
    });
    return h + plain(text.slice(last));
  };

  // items across the files; only this view's own paint takes the snapshot (shown/base) that edits are addressed by —
  // other readers (quick open, the board) parse the disk text and leave the snapshot alone
  function itemsAll(snap) {
    return Object.keys(F).sort().flatMap(n => {
      if (snap) { F[n].shown = F[n].text; F[n].base = F[n].version; }
      const its = SV.parseTodo(snap ? F[n].shown : F[n].text);
      return its.map((it, i) => Object.assign({ file: n, meta: SV.todoMeta(it.text), prog: SV.todoProgress(its, i) }, it));
    });
  }
  /* ---- an item's marks as small labels: when it was made, when it is due (late in red), when it was done, how urgent ---- */
  const today = () => SV.todoStamp(new Date()).slice(0, 10);
  const PRIO = ["", "高", "中", "低"];
  V.todoMetaHTML = (m, done) => {
    const t = today(), when = m.created && SV.todoDate(m.created);
    return (m.prio ? `<span class="tpri p${m.prio}" data-tip="优先级：${PRIO[m.prio]}">${V.I["p" + m.prio]}</span>` : "")
      + (m.due ? `<span class="tdue${!done && m.due < t ? " late" : !done && m.due === t ? " now" : ""}" data-tip="截止 ${m.due}">${V.I.cal}${m.due.slice(5)}</span>` : "")
      + (m.done ? `<span class="tmeta" data-tip="完成 ${m.done}">${V.I.done}${m.done.slice(5)}</span>` : "")
      + (when ? `<span class="tmeta" data-tip="创建 ${m.created}">${V.relT(when.getTime())}</span>` : "");
  };
  // a multi-line item shows its first line and how many follow; the whole text opens on hover or a tap
  const moreHTML = it => (it.more.length ? `<span class="tmore" data-tmore="${esc(it.file)}|${it.line}">+${it.more.length} 行</span>` : "");
  function rowHTML(it) {
    const id = esc(it.file) + "|" + it.line, m = SV.todoMeta(it.text);
    return `<div class="titem${it.done ? " done" : ""}" style="--td:${Math.min(it.depth, 8)}"><button class="tck" data-tck="${id}" aria-label="${it.done ? "标为未完成" : "标为完成"}">${it.done ? "✓" : ""}</button>`
      + `<span class="ttx">${V.todoItemHTML(m.text, it.file)}${it.prog ? `<span class="tprog">${it.prog[0]}/${it.prog[1]}</span>` : ""}${moreHTML(it)}</span>`
      + V.todoMetaHTML(m, it.done)
      + `<button class="tfile" data-open="dev:${DIR}${esc(it.file)}" data-oline="${it.line + 1}" data-tip="打开 ${esc(it.file)} 的这一行">${esc(it.file.replace(/\.md$/, ""))}</button></div>`;
  }

  /* ---- the todo board (046): the board's table form over todo items. Four dimensions — 项目 (the first @tag), 时间 (the due
     date's bucket), 完成, 文件 — group them; two filters pick them: 完成 and a time range that any of an item's dates
     (made, done, due) falls in. 待办 and 回顾 are two presets of these options. ---- */
  const ymd = d => SV.todoStamp(d).slice(0, 10);
  function range(kind) {   // [from, to], inclusive YYYY-MM-DD; calendar days, not 24h steps
    const d = new Date(), y = d.getFullYear(), m = d.getMonth(), mon = d.getDate() - (d.getDay() + 6) % 7;
    if (kind === "today") return [ymd(d), ymd(d)];
    if (kind === "week" || kind === "lastweek") { const a = mon - (kind === "lastweek" ? 7 : 0); return [ymd(new Date(y, m, a)), ymd(new Date(y, m, a + 6))]; }
    if (kind === "month") return [ymd(new Date(y, m, 1)), ymd(new Date(y, m + 1, 0))];
    return [ymd(new Date(y, m - 1, 1)), ymd(new Date(y, m, 0))];   // lastmonth
  }
  const within = (x, r) => x && x.slice(0, 10) >= r[0] && x.slice(0, 10) <= r[1];
  const GRPS = [["p", "项目"], ["w", "时间"], ["d", "完成"], ["f", "文件"]];
  const DONES = [["open", "未完成"], ["done", "已完成"], ["all", "全部"]];
  const RANGES = [["", "全部时间"], ["today", "今天"], ["week", "本周"], ["lastweek", "上周"], ["month", "本月"], ["lastmonth", "上月"]];
  // a due bucket wears a board status, so the cards, dots and folds colour and fold like the board's
  const WHENS = [["late", "已过期", "blocked"], ["today", "今天", "active"], ["week", "本周", "paused"], ["later", "以后", "todo"], ["none", "无日期", "backlog"]];
  const PRESETS = { list: { "todo-done": "open", "todo-range": "", "todo-grp": "p" }, review: { "todo-done": "all", "todo-range": "week", "todo-grp": "d" } };
  V.todoPreset = mode => { store.set("todo-mode", mode); Object.entries(PRESETS[mode]).forEach(([k, v]) => store.set(k, v)); };
  function whenOf(it) {
    const d = it.meta.due, t = today(); if (!d) return "none";
    return d < t ? "late" : d === t ? "today" : within(d, range("week")) ? "week" : "later";
  }
  const projOf = i => i.tags[0] || "";
  const label = (list, k) => (list.find(x => x[0] === k) || ["", k])[1];
  function cardsOf(all) {
    const dn = store.get("todo-done", "open"), rg = store.get("todo-range", ""), r = rg && range(rg);
    return all.filter(i => (dn === "all" || (dn === "done") === i.done) && (!r || [i.meta.created, i.meta.done, i.meta.due].some(x => within(x, r))))
      .map(it => { const w = whenOf(it); return { id: it.file + "|" + it.line, it, w, st: it.done ? "done" : WHENS.find(x => x[0] === w)[2] }; });
  }
  function groupsOf(cs) {
    const g = store.get("todo-grp", "p"), of = (key, name, pick, extra) => Object.assign({ key, name, cs: cs.filter(pick) }, extra);
    if (g === "w") return WHENS.map(([k, l, st]) => of("w:" + k, l, c => c.w === k, { st }));   // fixed sets list every group, empty ones too
    if (g === "d") return [of("d:open", "未完成", c => !c.it.done), of("d:done", "已完成", c => c.it.done)];
    if (g === "f") return Object.keys(F).sort().map(f => of("f:" + f, f.replace(/\.md$/, ""), c => c.it.file === f));
    const ps = [...new Set(cs.map(c => projOf(c.it)))];   // projects only where items are: the list of projects keeps growing
    return ps.map(p => of("p:" + p, p ? "@" + p : "未标项目", c => projOf(c.it) === p))
      .sort((a, b) => (a.key === "p:") - (b.key === "p:") || b.cs.length - a.cs.length || a.name.localeCompare(b.name));
  }
  const SORTKEY = { due: i => i.meta.due || "9999", prio: i => i.meta.prio || 9, created: i => -((SV.todoDate(i.meta.created) || 0) && SV.todoDate(i.meta.created).getTime()),
    done: i => i.meta.done || "0000", file: i => i.file + "\0" + String(i.line).padStart(6, "0") };
  /* ---- the table form: one row per item, sortable columns, a group's done rows folded ---- */
  const COLS = [["ck", ""], ["text", "内容"], ["prio", "优先"], ["due", "截止"], ["done", "完成", "p"], ["created", "创建", "p"], ["file", "文件", "p"]];
  const SORTABLE = ["prio", "due", "done", "created", "file"];
  function trHTML(it) {
    const id = esc(it.file) + "|" + it.line, m = it.meta, t = today(), when = m.created && SV.todoDate(m.created);
    const text = `<span class="ttx">${V.todoItemHTML(m.text, it.file)}${it.prog ? `<span class="tprog">${it.prog[0]}/${it.prog[1]}</span>` : ""}${moreHTML(it)}</span>`;
    return `<tr class="${it.done ? "done" : ""}" style="--td:${Math.min(it.depth, 8)}">`
      + `<td class="c-ck"><button class="tck" data-tck="${id}" aria-label="${it.done ? "标为未完成" : "标为完成"}">${it.done ? "✓" : ""}</button></td>`
      + `<td class="c-text">${text}</td>`
      + `<td class="c-prio">${m.prio ? `<span class="tpri p${m.prio}" data-tip="优先级：${PRIO[m.prio]}">${V.I["p" + m.prio]}</span>` : ""}</td>`
      + `<td class="c-due">${m.due ? `<span class="tdue${!it.done && m.due < t ? " late" : !it.done && m.due === t ? " now" : ""}" data-tip="截止 ${m.due}">${m.due.slice(5)}</span>` : ""}</td>`
      + `<td class="c-done mu${V.hideCls("p")}" data-tip="${m.done ? "完成 " + m.done : ""}">${m.done ? m.done.slice(5) : ""}</td>`
      + `<td class="c-created mu${V.hideCls("p")}" data-tip="${m.created ? "创建 " + esc(m.created) : ""}">${when ? V.relT(when.getTime()) : ""}</td>`
      + `<td class="c-file${V.hideCls("p")}"><button class="tfile" data-open="dev:${DIR}${esc(it.file)}" data-oline="${it.line + 1}" data-tip="打开 ${esc(it.file)} 的这一行">${esc(it.file.replace(/\.md$/, ""))}</button></td></tr>`;
  }
  function tableT(gs) {   // the board's table, over todo items; done ones show in place — the 完成 filter picks them
    return V.tableHTML({ cls: "ttbl", cols: COLS.map(([k, l, hide]) => [k, l, SORTABLE.includes(k), hide]), val: (it, k) => SORTKEY[k](it), row: trHTML,
      sort: { k: store.get("todo-sort", ""), desc: store.get("todo-desc", false), attr: "data-tsortc" }, fold: () => "",
      groups: gs.map(g => ({ key: g.key, name: g.name, n: g.cs.length, show: false, open: g.cs.map(c => c.it), closed: [] })) });
  }
  function headT(k) {
    const g = store.get("todo-grp", "p");
    return `<button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button>` + V.paneHead(k)
      + `<div class="ppath"><bdi>todo / <b>${store.get("todo-mode", "list") === "review" ? "回顾" : "待办"}</b></bdi></div>`
      + `<div class="seg" style="margin-left:auto"><button data-tgrpc data-tip="分组：按${label(GRPS, g)}（点击换下一个：${GRPS.map(x => x[1]).join(" → ")}）">${label(GRPS, g)}</button></div>`
      + V.paneEnd(k);
  }
  const next = (list, cur) => list[(list.findIndex(x => x[0] === cur) + 1) % list.length][0];
  function paint() {
    const el = $("#todo"), sc = el && $("#tscroll", el); if (!sc) return;
    const all = itemsAll(true), dn = store.get("todo-done", "open"), rg = store.get("todo-range", "");
    $(".phd", el).innerHTML = headT(V.hostOf("todo"));
    const top = sc.scrollTop, cs = cardsOf(all), gs = groupsOf(cs);
    const chips = (list, cur, attr) => list.map(([k, l]) => `<button class="chip ${k === cur ? "on" : ""}" ${attr}="${k}">${l}</button>`).join("");
    const cyc = (list, cur, attr, tip) => `<button class="chip on cyc" ${attr}="${next(list, cur)}" data-tip="${tip}：点一下换下一个">${label(list, cur)}</button>`;
    sc.innerHTML = `<div class="tflt"><button class="chip tnew" data-tnew data-tip="在 inbox 里新建一条">新建</button><span class="sep"></span>${chips(DONES, dn, "data-tdonef")}<span class="sep"></span>${chips(RANGES, rg, "data-trangef")}`
      + cyc(DONES, dn, "data-tdonef", "完成") + cyc(RANGES, rg, "data-trangef", "时间") + "</div>"
      + (all.length ? tableT(gs) : `<div class="hint">还没有 todo。在左侧 todo 下新建一个文件，写 - [ ] 开头的行。</div>`);
    sc.scrollTop = top;
    V.emit("todo-count"); V.status();
  }
  // what a wikilink can name: recent docs first, then every dev doc, then the KB and the extra roots — as [[…]] targets
  V.docChoices = () => {
    const wiki = key => { const i = key.indexOf(":"), t = key.slice(0, i), r = key.slice(i + 1).replace(/\.md$/, ""); return t === "dev" ? r : t === "kb" && /^(wiki|raw)\//.test(r) ? r : t + "/" + r; };
    const all = V.recent.list("opened").concat(["dev", "kb", "ext"].flatMap(t => (V.D.tree[t] || []).map(x => t + ":" + x.path)));
    return [...new Set(all.map(wiki).concat(V.D.cards.map(c => c.id)))];   // cards last, as project/NNN
  };
  // 045: [[project/NNN]] names a card; the reader, the todo view and the board's detail all read it this way
  V.cardOf = x => { const m = /^([\w.-]+\/\d{3})$/.exec(String(x).split("|")[0].trim()); return m ? V.card(m[1]) : null; };
  V.cardWiki = raw => { const m = /^\[\[(.+?)\]\]$/.exec(String(raw).trim()), c = m && V.cardOf(m[1]), d = c && V.mainDoc(c); return d ? "dev:" + d : null; };
  V.todoItems = () => itemsAll(false);
  V.todoRowHTML = it => rowHTML(it);
  const linksCard = (text, c) => text.includes("[[" + c.id + "]]") || text.includes("[[" + c.dir + "/") || text.includes("[[" + c.id + "|");
  V.todosOfCard = c => itemsAll(false).filter(t => !t.done && linksCard(t.text, c));
  /* ---- the todo panel: ⌘J, the top-bar button, t, or 记为 todo on a selection. One field filters the open items and is
     the text of a new one (written to inbox.md with the context filled in); a row opens its link, or ticks done ---- */
  const wikiOf = (tree, rel) => (tree === "dev" ? rel : tree === "kb" && /^(wiki|raw)\//.test(rel) ? rel : tree + "/" + rel).replace(/\.md$/, "");
  // todo.py composes and appends the item on the server; the page names the file's version and its local time
  V.todoAppend = (name, item) => V.api("/raw/dev/" + DIR + encodeURIComponent(name)).then(r => r.headers.get("X-Version") || "")
    .catch(e => (e.status === 404 ? "" : Promise.reject(e)))
    .then(version => V.todoWrite("append", name, Object.assign({ project: "", link: "", stamp: SV.todoStamp(new Date(), true), version }, item)));
  const T = { q: "", sel: 0, rows: [], ctx: null, added: "", undo: null, pend: null, fade: null };
  const FADE_MS = 1500;   // a ticked row stays, struck through, this long before it leaves the list
  const box = () => $("#tdp .qbox");
  function context(opt) {   // the project and doc a new item gets: the doc or card in view, and the line a selection starts on
    const k = opt.k || V.navPane(), loc = V.P[k].loc, card = loc && loc.kind === "doc" ? V.cardOfPath(loc.tree, loc.rel) : loc && loc.kind === "board" && V.selCard ? V.card(V.selCard()) : null;
    const proj = card ? card.p : loc && loc.kind === "doc" && loc.tree === "dev" && loc.rel.includes("/") && V.D.board[loc.rel.split("/")[0]] ? loc.rel.split("/")[0] : store.get("todo-proj", "");
    let line = null; if (opt.at) { const el = opt.at.nodeType === 1 ? opt.at : opt.at.parentElement; line = el && V.lineOf(k, el); }
    const doc = loc && loc.kind === "doc" ? wikiOf(loc.tree, loc.rel) + (line != null ? "#L" + (line + 1) : "") : card && V.mainDoc(card) ? wikiOf("dev", V.mainDoc(card)) : "";
    return { card, proj, doc };
  }
  // the open items, read from the version edits are addressed by
  const openItems = () => Object.keys(F).sort().flatMap(n => SV.parseTodo(seen(n)).filter(it => !it.done).map(it => Object.assign({ file: n, meta: SV.todoMeta(it.text) }, it)));
  const prioKey = it => it.meta.prio || 2.5;   // ⏫ 🔼, then none, then 🔽
  const madeKey = it => { const d = SV.todoDate(it.meta.created); return d ? -d.getTime() : 0; };
  // the open items, plus the one just ticked while it fades
  const shownItems = () => openItems().concat(T.fade && F[T.fade.file] ? SV.parseTodo(seen(T.fade.file)).filter(it => it.done && it.line === T.fade.line)
    .map(it => Object.assign({ file: T.fade.file, meta: SV.todoMeta(it.text) }, it)) : []);
  function groups() {
    const all = shownItems(), t = today(), c = T.ctx && T.ctx.card, seenId = new Set(), take = (name, list) => {
      const rows = list.filter(it => !seenId.has(it.file + "|" + it.line)); rows.forEach(it => seenId.add(it.file + "|" + it.line));
      return rows.length ? [[name, rows]] : [];
    };
    if (T.q) {
      const label = it => it.meta.text.replace(/\[\[([^\]|#]+)[^\]]*\]\]/g, (a, w) => w.split("/").pop()) + " " + it.file.replace(/\.md$/, "");
      return [["", all.map(it => { const m = SV.matchScore(T.q, label(it)); return m.hit ? { it, sc: m.score } : null; }).filter(Boolean)
        .sort((a, b) => b.sc - a.sc || madeKey(a.it) - madeKey(b.it)).map(x => x.it)]];
    }
    return take("刚记下", T.added ? all.filter(it => it.meta.text.startsWith(T.added)) : [])
      .concat(take("逾期 · 今天到期", all.filter(it => it.meta.due && it.meta.due <= t).sort((a, b) => a.meta.due.localeCompare(b.meta.due)))
      .concat(c ? take("当前卡 · " + c.n + " " + c.slug, all.filter(it => linksCard(it.text, c))) : [])
      .concat(take(c || all.some(it => it.meta.due && it.meta.due <= t) ? "其余" : "", all.slice().sort((a, b) => prioKey(a) - prioKey(b) || madeKey(a) - madeKey(b)))));
  }
  const panelRow = (it, i) => `<div class="titem tdr${i === T.sel ? " sel" : ""}${T.added && it.meta.text.startsWith(T.added) ? " fresh" : ""}${it.done ? " done fading" : ""}" data-tdr="${i}">`
    + `<button class="tck" data-tck="${esc(it.file)}|${it.line}" aria-label="${it.done ? "标为未完成" : "标为完成"}">${it.done ? "✓" : ""}</button>`
    + `<span class="ttx">${V.todoItemHTML(it.meta.text, it.file)}${moreHTML(it)}</span>${V.todoMetaHTML(it.meta, false)}`
    + `<span class="tdf">${esc(it.file.replace(/\.md$/, ""))}</span></div>`;
  // the matched characters of a filtered row, marked in the text as shown (its links and tags stay as they are)
  function markHits(el, q) {
    const nodes = [], walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: n => (n.parentElement.closest(".tmore") ? 2 : 1) });
    let s = ""; for (let n = walk.nextNode(); n; n = walk.nextNode()) { nodes.push([n, s.length]); s += n.data; }
    const m = SV.matchScore(q, s); if (!m.hit || !m.idx.length) return;
    const hit = new Set(m.idx);
    nodes.forEach(([n, at]) => {
      if (![...n.data].some((c, i) => hit.has(at + i))) return;
      const f = document.createDocumentFragment();
      [...n.data].forEach((c, i) => { if (hit.has(at + i)) { const b = document.createElement("b"); b.className = "tdh"; b.textContent = c; f.appendChild(b); } else f.appendChild(document.createTextNode(c)); });
      n.parentNode.replaceChild(f, n);
    });
  }
  function paintPanel() {
    const b = box(); if (!b || $("#tdp").hidden) return;
    const gs = groups(); T.rows = gs.flatMap(g => g[1]); T.sel = Math.max(0, Math.min(T.sel, T.rows.length - 1));
    let i = 0;
    $(".tdlist", b).innerHTML = T.rows.length ? gs.map(([name, rows]) => (name ? `<div class="qg">${esc(name)}</div>` : "") + rows.map(it => panelRow(it, i++)).join("")).join("")
      : `<div class="hint">${T.q ? "没有匹配的待办。↵ 把它记为新的一条" : "没有未完成的待办"}</div>`;
    if (T.q) $$(".tdr .ttx", b).forEach(x => markHits(x, T.q));
    const n = openItems().length;
    $(".tdn", b).textContent = T.q ? `${T.rows.length} / ${n}` : `${n} 项未完成`;
    const c = T.ctx, add = $(".tdadd", b), projs = Object.keys(V.D.board || {}).sort();
    add.hidden = !T.q;
    if (T.q && !add.dataset.on) {   // drawn once per typed text, so a changed project or unticked link stays as set
      add.dataset.on = "1";
      add.innerHTML = `<span class="k">⌘↵ 记为新 todo</span><select class="capproj" aria-label="项目"><option value="">不标项目</option>${projs.map(p => `<option ${p === c.proj ? "selected" : ""}>${esc(p)}</option>`).join("")}</select>`
        + (c.doc ? `<label><input type="checkbox" class="capdoc" checked> 链接 <code>${esc(c.doc)}</code></label>` : "") + `<span class="to">→ inbox.md</span>`;
    }
    if (!T.q) delete add.dataset.on;
    const s = $(".tdr.sel", b); if (s) s.scrollIntoView({ block: "nearest" });
  }
  V.todoPanel = (opt = {}) => {
    const el = $("#tdp"); if (!el.hidden && !opt.text) return closePanel();
    V.closePops(); T.ctx = context(opt); T.q = (opt.text || "").trim(); T.sel = 0; T.added = "";
    const b = box();
    b.innerHTML = `<div class="tdin">${V.I.done}<input class="tdq" placeholder="筛选待办，或写一条新的…" autocomplete="off" aria-label="筛选或新增 todo"><span class="tdn"></span></div>`
      + `<div class="tdadd" hidden></div><div class="tdlist scroll"></div><div class="tdundo" hidden></div>`
      + `<div class="qf"><span><kbd>↑↓</kbd>选择</span><span><kbd>↵</kbd>打开</span><span><kbd>⇧↵</kbd>在另一栏打开</span><span><kbd>⌥↵</kbd>完成</span><span><kbd>⌘↵</kbd>新增</span><span><kbd>esc</kbd>清空 / 关闭</span><span class="tdgo"><button data-tdgo="list" data-tip="todo 视图：待办（⇧ 在另一栏）">待办 <kbd>⌥1</kbd></button><button data-tdgo="review" data-tip="todo 视图：回顾（⇧ 在另一栏）">回顾 <kbd>⌥2</kbd></button></span></div>`;
    el.hidden = false;
    const inp = $(".tdq", b); inp.value = T.q; inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length);
    (loaded ? Promise.resolve() : load()).then(paintPanel);
  };
  const closePanel = () => { $("#tdp").hidden = true; T.undo = T.pend = null; };
  function addItem() {
    const b = box(), text = T.q, proj = $(".capproj", b) ? $(".capproj", b).value : "", link = $(".capdoc", b) && $(".capdoc", b).checked ? T.ctx.doc : "";
    if (!text || b.dataset.busy) return;
    if (proj) store.set("todo-proj", proj);
    b.dataset.busy = "1";   // the text stays in the field until the line is really written
    V.todoAppend("inbox.md", { text, project: proj, link }).then(res => {
      delete b.dataset.busy;
      if (!res.ok) return;
      const inp = $(".tdq", b); inp.value = ""; T.q = ""; T.sel = 0; T.added = SV.todoMeta(text).text;
      V.toast("记下了：todo/inbox.md"); paintPanel();
    }, () => { delete b.dataset.busy; V.toast("没记下：读不到 inbox.md"); });
  }
  // a row opens its todo file at the item's line; the links in its text open their own docs
  function openRow(e) {
    const it = T.rows[T.sel]; if (!it) return;
    closePanel();
    V.openDoc("dev", DIR + it.file, e, { line: it.line + 1 });
  }
  // a tick in the panel goes through the one [data-tck] handler, which writes it a moment later; the panel offers to take
  // it back once the tick is on disk, and only while that line still reads as written — a line that moved is left alone
  function noteTick(at) {
    const it = SV.parseTodo(seen(at.file)).find(x => x.line === at.line); if (!it || it.done) return;
    const pend = T.pend = { file: at.file, line: at.line, key: SV.todoMeta(it.text).text }, fade = T.fade = { file: at.file, line: at.line };
    setTimeout(() => { if (T.fade === fade) { T.fade = null; paintPanel(); } }, FADE_MS);
    setTimeout(() => { if (T.pend === pend) T.pend = null; }, V.CFG.undoMs);   // a refused tick never lands
  }
  function offerUndo() {
    const pd = T.pend, f = pd && F[pd.file]; if (!f) return;
    const it = SV.parseTodo(seen(pd.file)).find(x => x.line === pd.line);
    if (!it || !it.done || SV.todoMeta(it.text).text !== pd.key) return;
    T.pend = null;
    const u = $(".tdundo", box()), undo = T.undo = { file: pd.file, line: pd.line, was: SV.todoLine(seen(pd.file), pd.line) };
    u.innerHTML = `<span>已完成：${esc(pd.key.slice(0, 40))}</span><button data-tdundo>撤销</button>`; u.hidden = false;
    setTimeout(() => { if (T.undo === undo) { T.undo = null; u.hidden = true; } }, V.CFG.undoMs);
  }
  V.click("[data-tdundo]", () => {
    const u = T.undo; if (!u || !F[u.file]) return;
    T.undo = null; $(".tdundo", box()).hidden = true;
    if (SV.todoLine(seen(u.file), u.line) !== u.was) return V.toast("这一条在别处改过了，没有撤销");
    V.todoWrite("tick", u.file, { line: u.line, text: u.was, done: false, today: today(),
      version: F[u.file].shown != null ? F[u.file].base : F[u.file].version });
  });
  // the todo view in one of its two presets, as the tree's 待办 / 回顾 rows open it
  const goView = (mode, e) => { closePanel(); V.todoPreset(mode); V.nav(V.target(e), { kind: "todo" }); };
  V.click("[data-tdgo]", (el, e) => goView(el.dataset.tdgo, e));
  V.on("init", () => {
    const el = $("#tdp");
    el.addEventListener("click", e => {
      if (e.target.id === "tdp") return closePanel();
      const ck = e.target.closest(".tdr [data-tck]"); if (ck) { const id = ck.dataset.tck, i = id.lastIndexOf("|"); noteTick({ file: id.slice(0, i), line: +id.slice(i + 1) }); return; }
      if (e.target.closest(".tdr [data-open], .tdr .tmore")) { if (e.target.closest("[data-open]")) closePanel(); return; }
      const row = e.target.closest(".tdr"); if (row) { T.sel = +row.dataset.tdr; openRow(e); }
    }, true);
    // a click on a button in the panel leaves the typing where it was
    el.addEventListener("click", () => { const a = document.activeElement; if (!el.hidden && !(a && a.matches("#tdp select, #tdp input"))) $(".tdq", el).focus(); });
    el.addEventListener("mousemove", e => { const r = e.target.closest(".tdr"); if (r && +r.dataset.tdr !== T.sel) { T.sel = +r.dataset.tdr; $$(".tdr", el).forEach(x => x.classList.toggle("sel", x === r)); } });
    el.addEventListener("input", e => { if (!e.target.matches(".tdq")) return; T.q = e.target.value.trim(); T.sel = 0; T.added = ""; paintPanel(); });
    el.addEventListener("keydown", e => {
      if (!e.target.matches(".tdq") || e.isComposing || e.keyCode === 229) return;
      e.stopPropagation();
      const mod = e.metaKey || e.ctrlKey, inp = e.target;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); T.sel = Math.max(0, Math.min(T.rows.length - 1, T.sel + (e.key === "ArrowDown" ? 1 : -1))); $$(".tdr", el).forEach(x => x.classList.toggle("sel", +x.dataset.tdr === T.sel)); const s = $(".tdr.sel", el); if (s) s.scrollIntoView({ block: "nearest" }); }
      else if (e.altKey && !mod && (e.code === "Digit1" || e.code === "Digit2")) { e.preventDefault(); goView(e.code === "Digit1" ? "list" : "review", e); }   // by key position: ⌥ + a digit types a symbol on a Mac
      else if (e.key === "Enter" && mod) { e.preventDefault(); addItem(); }
      else if (e.key === "Enter" && e.altKey) { e.preventDefault(); const ck = $(`.tdr[data-tdr="${T.sel}"] [data-tck]`, el); if (ck) ck.click(); }
      else if (e.key === "Enter") { e.preventDefault(); if (T.rows.length) openRow(e); else addItem(); }
      else if (e.key === "Escape") { e.preventDefault(); if (inp.value) { inp.value = ""; T.q = ""; T.sel = 0; paintPanel(); } else closePanel(); }
      else if (V.isChord(e) && e.key.toLowerCase() === "j") { e.preventDefault(); closePanel(); }
      else if (V.isChord(e) && V.chord[e.key.toLowerCase()]) { closePanel(); V.chord[e.key.toLowerCase()](e); e.preventDefault(); }
    });
  });
  V.layer(70, () => !$("#tdp").hidden, closePanel);
  V.hotkey("t", () => V.todoPanel());
  V.chord.j = () => V.todoPanel();
  V.click("#todoBtn", () => V.todoPanel());
  V.on("todo-count", () => {
    const b = $("#todoBtn"); if (!b) return;
    const all = openItems(), t = today(), late = all.some(it => it.meta.due && it.meta.due < t);
    b.dataset.n = all.length ? String(all.length) : ""; b.classList.toggle("late", late);
    paintPanel(); offerUndo();
  });
  V.todoOpen = () => Object.values(F).reduce((n, f) => n + SV.parseTodo(f.text).filter(i => !i.done).length, 0);
  const find = id => { const i = id.lastIndexOf("|"), file = id.slice(0, i), line = +id.slice(i + 1); return F[file] && SV.parseTodo(seen(file)).find(x => x.line === line) && { file, line }; };

  const showMore = el => {
    const at = find(el.dataset.tmore), it = at && SV.parseTodo(seen(at.file)).find(x => x.line === at.line); if (!it) return;
    V.tipAt(el, `<div class="h"><b>${esc(at.file)}</b><span style="margin-left:auto">第 ${at.line + 1} 行</span></div>`
      + `<div class="tfull">${esc([SV.todoMeta(it.text).text, ...it.more].join("\n"))}</div>`);
  };
  document.addEventListener("mouseover", e => { const el = e.target.closest && e.target.closest(".tmore"); if (el) showMore(el); });
  document.addEventListener("mouseout", e => {
    if (e.target.closest && e.target.closest(".tmore") && !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest(".tmore"))) V.hideTip();
  });
  V.click(".tmore", el => showMore(el));

  V.views.todo = (k, loc, opt) => {
    const el = $("#todo");
    el.innerHTML = `<div class="phd"><button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button>` + V.paneHead(k)
      + `</div><div id="tscroll" class="scroll tbl-form"><div class="hint">读取中…</div></div>`;
    if (loaded && !opt.entering) paint(); else refresh();
    V.status();
  };
  V.statusFns.todo = () => `<span><b>todo</b>　dev_root/todo/，${Object.keys(F).length} 个文件，未完成 ${V.todoOpen()}</span><span class="sp"></span>${V.stamp()}`;

  V.click("[data-tnewf]", () => V.ask("新的 todo 文件", [["ok", "新建"], ["", "取消"]], "").then(t => {
    const n = (t || "").trim().replace(/[/\\\x00-\x1f]/g, "-").replace(/\.md$/i, "") + ".md"; if (n === ".md") return;
    if (F[n]) return V.toast("已经有 " + n);
    V.todoWrite("write", n, { text: "# " + n.replace(/\.md$/i, "") + "\n\n", version: "" }).then(res => { if (res.ok) V.openDoc("dev", DIR + n); });
  }));
  // A tick shows on the row first and is written a moment later, so the row visibly changes before a filter drops it.
  V.click("[data-tck]", el => {
    const at = find(el.dataset.tck); if (!at || el.dataset.busy) return;
    const it = SV.parseTodo(seen(at.file)).find(x => x.line === at.line), row = el.closest("tr, .titem");
    el.dataset.busy = "1"; el.textContent = it.done ? "" : "✓"; if (row) row.classList.toggle("done", !it.done);
    setTimeout(() => V.todoWrite("tick", at.file, { line: at.line, text: SV.todoLine(seen(at.file), at.line), done: !it.done, today: today(),
      version: F[at.file].shown != null ? F[at.file].base : F[at.file].version }), TICK_MS);
  });
  // No per-item delete: an item's continuation lines are not on its row, so deleting is left to the source editor.
  V.click("[data-tsortc]", el => {   // first click sorts ascending, the second descending, the third back to file order
    const k = el.dataset.tsortc, by = store.get("todo-sort", ""), desc = store.get("todo-desc", false);
    if (by !== k) { store.set("todo-sort", k); store.set("todo-desc", false); } else if (!desc) store.set("todo-desc", true); else { store.set("todo-sort", ""); store.set("todo-desc", false); }
    paint();
  });
  V.click("[data-tdonef]", el => { store.set("todo-done", el.dataset.tdonef); paint(); });
  V.click("[data-trangef]", el => { store.set("todo-range", el.dataset.trangef); paint(); });
  V.click("[data-tgrpc]", () => { store.set("todo-grp", next(GRPS, store.get("todo-grp", "p"))); paint(); V.untip(); });
  V.click("[data-tren]", el => {
    const n = el.dataset.tren;
    V.ask("新文件名", [["ok", "改名"], ["", "取消"]], n.replace(/\.md$/, "")).then(t => {
      const raw = (t || "").trim(); if (!raw) return;
      const to = raw.replace(/[/\\\x00-\x1f]/g, "-").replace(/\.md$/i, "") + ".md";
      if (to !== n) V.todoWrite("rename", n, { to, version: F[n].version });
    });
  });
  V.click("[data-tdelf]", el => { const n = el.dataset.tdelf; V.ask(`删除 ${n}？里面的 todo 会一起删掉。`, [["del", "删除"], ["", "取消"]]).then(v => { if (v === "del") V.todoWrite("delete", n, { version: F[n].version }); }); });
  // No in-place edit (it changed only an item's first line, which other tools use to find the item): a double-click
  // on a row opens its file in the source editor at that line, and 新建 starts a new item at the end of inbox.md.
  document.addEventListener("dblclick", e => {
    const row = e.target.closest && e.target.closest("#todo .titem, #todo tbody tr"); if (!row || e.target.closest("a,button,input")) return;
    const box = row.querySelector("[data-tck]"), at = box && find(box.dataset.tck); if (at) V.editTodoAt(at.file, at.line);
  });
  V.click("[data-tnew]", () => (F["inbox.md"] ? Promise.resolve({ ok: true }) : V.todoWrite("write", "inbox.md", { text: "# inbox\n\n", version: "" }))
    .then(res => { if (res.ok) V.editTodoAt("inbox.md", null, true); }));
  V.on("data", () => {
    const busy = $("#todo input:focus");
    if (!$("#todo").hidden && !busy) return refresh();
    load().then(() => {   // busy: data only, the screen keeps its version; hidden: no screen, so no snapshot either
      if ($("#todo").hidden) Object.values(F).forEach(f => { f.shown = null; });
      V.emit("todo-count");
    });
  });
})(V2);
