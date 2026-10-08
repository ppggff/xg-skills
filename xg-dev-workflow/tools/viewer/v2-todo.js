/* status viewer v2 — todo: a directory of markdown files, <dev_root>/todo/*.md, as a view beside the board. Each file
   is read like any doc; its checklist lines are the todos, @words tag a project (older #words too), wikilinks point at
   docs. The nav lists the files under its todo section; this view shows every todo across them as a table (待办), or
   what was made, done and due in a period (回顾); the reader opens and edits a file.
   Writes carry the version the page shows, so a file changed elsewhere in between is refused, never overwritten. */
"use strict";
(function (V) {
  const { $, esc } = V, store = V.store;
  // per file: text/mtime follow the disk; shown/base are the version on screen — edits address its lines and are
  // saved against its mtime, so a file that moved underneath is refused (409) instead of having the wrong line changed
  const F = V.todoFiles = {};
  let editing = null, loaded = false;
  const unfold = new Set();   // groups whose done items are shown
  const DIR = "todo/", names = () => (V.D.tree ? V.D.tree.dev.map(x => x.path).filter(p => /^todo\/[^/]+\.md$/.test(p)).map(p => p.slice(DIR.length)) : []);

  function load() {
    const want = names();
    Object.keys(F).forEach(n => { if (!want.includes(n)) delete F[n]; });
    return Promise.all(want.map(n => V.api("/raw/dev/" + DIR + encodeURIComponent(n)).then(r => r.text().then(t => {
      const f = F[n] || (F[n] = {}); f.text = t; f.mtime = +r.headers.get("X-Mtime") || 0;
    })).catch(() => {}))).then(() => { loaded = true; });
  }
  V.todoWrite = (op, name, extra) => fetch("/api/todo", { method: "POST", headers: { "Content-Type": "application/json", "X-SV-Write": "1" },
    body: JSON.stringify(Object.assign({ op, file: name }, extra)) })
    .then(r => r.json().catch(() => ({})).then(d => ({ ok: r.ok, status: r.status, d })))
    .then(res => {
      if (!res.ok) V.toast(res.d && res.d.error === "exists" ? "已经有同名的文件" : res.status === 409 ? "这个 todo 文件在别处改过了，已重新读取，请再改一次" : "保存失败（" + res.status + "）");
      return V.load().then(() => V.emit("data")).then(() => res);   // the tree, the reader and this view all re-read
    }).catch(() => { V.toast("保存失败：连不上 viewer"); return { ok: false }; });
  // the version edits are addressed by: this view's snapshot once it has painted, else (rows shown elsewhere) the disk text
  const seen = n => (F[n].shown != null ? F[n].shown : F[n].text);
  const save = (name, text) => V.todoWrite("write", name, { text, mtime: F[name] ? (F[name].shown != null ? F[name].base : F[name].mtime) : 0 });
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
      if (snap) { F[n].shown = F[n].text; F[n].base = F[n].mtime; }
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
  function rowHTML(it) {
    const id = esc(it.file) + "|" + it.line, m = SV.todoMeta(it.text);
    if (editing === id) return `<div class="titem ed"><input class="tedit" data-id="${id}" value="${esc(it.text)}" aria-label="改这一条"></div>`;
    return `<div class="titem${it.done ? " done" : ""}" style="--td:${Math.min(it.depth, 8)}"><button class="tck" data-tck="${id}" aria-label="${it.done ? "标为未完成" : "标为完成"}">${it.done ? "✓" : ""}</button>`
      + `<span class="ttx" data-ted="${id}" data-tip="双击修改">${V.todoItemHTML(m.text, it.file)}${it.prog ? `<span class="tprog">${it.prog[0]}/${it.prog[1]}</span>` : ""}</span>`
      + V.todoMetaHTML(m, it.done)
      + `<button class="tfile" data-open="dev:${DIR}${esc(it.file)}" data-oline="${it.line + 1}" data-tip="打开 ${esc(it.file)} 的这一行">${esc(it.file.replace(/\.md$/, ""))}</button>`
      + `<button class="tdel" data-tdel="${id}" data-tip="删除这一条" aria-label="删除">×</button></div>`;
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
  V.todoPreset = mode => { store.set("todo-mode", mode); Object.entries(PRESETS[mode]).forEach(([k, v]) => store.set(k, v)); if (mode === "review") unfold.add("d:done"); };
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
    if (g === "d") return [of("d:open", "未完成", c => !c.it.done), of("d:done", "已完成", c => c.it.done, { all: true })];
    if (g === "f") return Object.keys(F).sort().map(f => of("f:" + f, f.replace(/\.md$/, ""), c => c.it.file === f));
    const ps = [...new Set(cs.map(c => projOf(c.it)))];   // projects only where items are: the list of projects keeps growing
    return ps.map(p => of("p:" + p, p ? "@" + p : "未标项目", c => projOf(c.it) === p))
      .sort((a, b) => (a.key === "p:") - (b.key === "p:") || b.cs.length - a.cs.length || a.name.localeCompare(b.name));
  }
  const SORTKEY = { due: i => i.meta.due || "9999", prio: i => i.meta.prio || 9, created: i => -((SV.todoDate(i.meta.created) || 0) && SV.todoDate(i.meta.created).getTime()),
    done: i => i.meta.done || "0000", file: i => i.file + "\0" + String(i.line).padStart(6, "0") };
  /* ---- the table form: one row per item, sortable columns, a group's done rows folded ---- */
  const COLS = [["ck", ""], ["text", "内容"], ["prio", "优先级"], ["due", "截止"], ["done", "完成"], ["created", "创建"], ["file", "文件"], ["x", ""]];
  const SORTABLE = ["prio", "due", "done", "created", "file"];
  function trHTML(it) {
    const id = esc(it.file) + "|" + it.line, m = it.meta, t = today(), when = m.created && SV.todoDate(m.created);
    const text = editing === id ? `<input class="tedit" data-id="${id}" value="${esc(it.text)}" aria-label="改这一条">`
      : `<span class="ttx" data-ted="${id}" data-tip="双击修改">${V.todoItemHTML(m.text, it.file)}${it.prog ? `<span class="tprog">${it.prog[0]}/${it.prog[1]}</span>` : ""}</span>`;
    return `<tr class="${it.done ? "done" : ""}" style="--td:${Math.min(it.depth, 8)}">`
      + `<td class="c-ck"><button class="tck" data-tck="${id}" aria-label="${it.done ? "标为未完成" : "标为完成"}">${it.done ? "✓" : ""}</button></td>`
      + `<td class="c-text">${text}</td>`
      + `<td class="c-prio">${m.prio ? `<span class="tpri p${m.prio}" data-tip="优先级：${PRIO[m.prio]}">${V.I["p" + m.prio]}</span>` : ""}</td>`
      + `<td class="c-due">${m.due ? `<span class="tdue${!it.done && m.due < t ? " late" : !it.done && m.due === t ? " now" : ""}" data-tip="截止 ${m.due}">${m.due.slice(5)}</span>` : ""}</td>`
      + `<td class="c-done mu" data-tip="${m.done ? "完成 " + m.done : ""}">${m.done ? m.done.slice(5) : ""}</td>`
      + `<td class="c-created mu" data-tip="${m.created ? "创建 " + esc(m.created) : ""}">${when ? V.relT(when.getTime()) : ""}</td>`
      + `<td class="c-file"><button class="tfile" data-open="dev:${DIR}${esc(it.file)}" data-oline="${it.line + 1}" data-tip="打开 ${esc(it.file)} 的这一行">${esc(it.file.replace(/\.md$/, ""))}</button></td>`
      + `<td class="c-x"><button class="tdel" data-tdel="${id}" data-tip="删除这一条" aria-label="删除">×</button></td></tr>`;
  }
  function tableT(gs) {   // the board's table, over todo items; done rows fold behind a text toggle
    const its = l => l.map(c => c.it);
    return V.tableHTML({ cls: "ttbl", cols: COLS.map(([k, l]) => [k, l, SORTABLE.includes(k)]), val: (it, k) => SORTKEY[k](it), row: trHTML,
      sort: { k: store.get("todo-sort", ""), desc: store.get("todo-desc", false), attr: "data-tsortc" },
      fold: (g, closed, show) => `<button class="tdone" data-tfoldg="${esc(g.key)}">${show ? "收起" : "展开"}已完成 ${closed.length}</button>`,
      groups: gs.map(g => ({ key: g.key, name: g.name, n: g.cs.length, show: unfold.has(g.key),
        open: its(g.all ? g.cs : g.cs.filter(c => !c.it.done)), closed: its(g.all ? [] : g.cs.filter(c => c.it.done)) })) });
  }
  function headT(k) {
    const g = store.get("todo-grp", "p");
    return `<button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button>` + V.paneHead(k)
      + `<div class="ppath"><bdi>todo / <b>${store.get("todo-mode", "list") === "review" ? "回顾" : "待办"}</b></bdi></div>`
      + `<div class="seg" style="margin-left:auto"><button data-tgrpc data-tip="分组：按${label(GRPS, g)}（点击换下一个：${GRPS.map(x => x[1]).join(" → ")}）">${label(GRPS, g)}</button></div>`
      + V.paneEnd(k);
  }
  function paint() {
    const el = $("#todo"), sc = el && $("#tscroll", el); if (!sc) return;
    const all = itemsAll(true), dn = store.get("todo-done", "open"), rg = store.get("todo-range", "");
    $(".phd", el).innerHTML = headT(V.hostOf("todo"));
    const top = sc.scrollTop, cs = cardsOf(all), gs = groupsOf(cs);
    const chips = (list, cur, attr) => list.map(([k, l]) => `<button class="chip ${k === cur ? "on" : ""}" ${attr}="${k}">${l}</button>`).join("");
    sc.innerHTML = `<div class="tflt">${chips(DONES, dn, "data-tdonef")}<span class="sep"></span>${chips(RANGES, rg, "data-trangef")}</div>`
      + (all.length ? tableT(gs) : `<div class="hint">还没有 todo。在左侧 todo 下新建一个文件，写 - [ ] 开头的行。</div>`);
    sc.scrollTop = top;
    const ed = $(".tedit", sc); if (ed) { ed.focus(); ed.setSelectionRange(ed.value.length, ed.value.length); }
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
  V.todosOfCard = c => itemsAll(false).filter(t => !t.done && (t.text.includes("[[" + c.id + "]]") || t.text.includes("[[" + c.dir + "/") || t.text.includes("[[" + c.id + "|")));
  /* ---- capture: t anywhere, or 记为 todo on a selection — a line into inbox.md with the context filled in ---- */
  const wikiOf = (tree, rel) => (tree === "dev" ? rel : tree === "kb" && /^(wiki|raw)\//.test(rel) ? rel : tree + "/" + rel).replace(/\.md$/, "");
  V.todoAppend = (name, body) => V.api("/raw/dev/" + DIR + encodeURIComponent(name)).then(r => r.text().then(t => [t, +r.headers.get("X-Mtime") || 0]))
    .catch(e => (e.status === 404 ? ["", 0] : Promise.reject(e)))
    .then(([t, mtime]) => V.todoWrite("write", name, { text: SV.addTodo(t, body), mtime }));
  V.capture = (opt = {}) => {
    const k = opt.k || V.navPane(), loc = V.P[k].loc, card = loc && loc.kind === "doc" ? V.cardOfPath(loc.tree, loc.rel) : loc && loc.kind === "board" && V.selCard ? V.card(V.selCard()) : null;
    const proj = card ? card.p : loc && loc.kind === "doc" && loc.tree === "dev" && loc.rel.includes("/") && V.D.board[loc.rel.split("/")[0]] ? loc.rel.split("/")[0] : store.get("todo-proj", "");
    let line = null; if (opt.at) { const el = opt.at.nodeType === 1 ? opt.at : opt.at.parentElement; line = el && V.lineOf(k, el); }
    const doc = loc && loc.kind === "doc" ? wikiOf(loc.tree, loc.rel) + (line != null ? "#L" + (line + 1) : "") : card && V.mainDoc(card) ? wikiOf("dev", V.mainDoc(card)) : "";
    const projs = Object.keys(V.D.board || {}).sort(), box = $("#cap .capbox");
    box.innerHTML = `<input class="capin" value="${esc(opt.text || "")}" placeholder="随手记一件事，写进 todo/inbox.md" aria-label="要记的事">`
      + `<div class="caprow"><select class="capproj" aria-label="项目"><option value="">不标项目</option>${projs.map(p => `<option ${p === proj ? "selected" : ""}>${esc(p)}</option>`).join("")}</select>`
      + (doc ? `<label><input type="checkbox" class="capdoc" checked> 链接 <code>${esc(doc)}</code></label>` : "") + "</div>"
      + `<div class="qf askf"><span><kbd>↵</kbd>记下</span><span><kbd>esc</kbd>关闭</span><button class="ok">记下</button></div>`;
    box.dataset.doc = doc; $("#cap").hidden = false;
    const inp = $(".capin", box); inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length);
  };
  const capClose = () => { $("#cap").hidden = true; };
  V.layer(70, () => !$("#cap").hidden, capClose);
  V.hotkey("t", () => V.capture());
  V.click("#cap", (el, e) => { if (e.target.id === "cap") capClose(); });
  document.addEventListener("submit", e => {
    const box = e.target.closest("#cap .capbox"); if (!box) return;
    e.preventDefault();
    const text = $(".capin", box).value.trim(), proj = $(".capproj", box).value, link = $(".capdoc", box) && $(".capdoc", box).checked ? box.dataset.doc : "";
    if (!text) return $(".capin", box).focus();
    if (proj) store.set("todo-proj", proj);
    const body = text + (proj && !text.includes("@" + proj) ? " @" + proj : "") + (link ? " [[" + link + "]]" : "") + " ➕ " + SV.todoStamp(new Date());
    if (box.dataset.busy) return;
    box.dataset.busy = "1";   // the box stays open, text and all, until the line is really written
    V.todoAppend("inbox.md", body).then(res => {
      delete box.dataset.busy;
      if (res.ok) { capClose(); V.toast("记下了：todo/inbox.md"); }
    }, () => { delete box.dataset.busy; V.toast("没记下：读不到 inbox.md"); });
  });
  V.todoOpen = () => Object.values(F).reduce((n, f) => n + SV.parseTodo(f.text).filter(i => !i.done).length, 0);
  const find = id => { const i = id.lastIndexOf("|"), file = id.slice(0, i), line = +id.slice(i + 1); return F[file] && SV.parseTodo(seen(file)).find(x => x.line === line) && { file, line }; };

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
    V.todoWrite("write", n, { text: "# " + n.replace(/\.md$/i, "") + "\n\n", mtime: 0 }).then(res => { if (res.ok) V.openDoc("dev", DIR + n); });
  }));
  V.click("[data-tck]", el => { const at = find(el.dataset.tck); if (!at) return; const it = SV.parseTodo(seen(at.file)).find(x => x.line === at.line); save(at.file, SV.editTodo(seen(at.file), at.line, { done: !it.done, today: today() })); });
  V.click("[data-tdel]", el => { const at = find(el.dataset.tdel); if (at) save(at.file, SV.editTodo(seen(at.file), at.line, { remove: true })); });
  V.click("[data-tfoldg]", el => { const g = el.dataset.tfoldg; unfold.has(g) ? unfold.delete(g) : unfold.add(g); paint(); });
  V.click("[data-tsortc]", el => {   // first click sorts ascending, the second descending, the third back to file order
    const k = el.dataset.tsortc, by = store.get("todo-sort", ""), desc = store.get("todo-desc", false);
    if (by !== k) { store.set("todo-sort", k); store.set("todo-desc", false); } else if (!desc) store.set("todo-desc", true); else { store.set("todo-sort", ""); store.set("todo-desc", false); }
    paint();
  });
  const next = (list, cur) => list[(list.findIndex(x => x[0] === cur) + 1) % list.length][0];
  V.click("[data-tdonef]", el => { store.set("todo-done", el.dataset.tdonef); paint(); });
  V.click("[data-trangef]", el => { store.set("todo-range", el.dataset.trangef); paint(); });
  V.click("[data-tgrpc]", () => { store.set("todo-grp", next(GRPS, store.get("todo-grp", "p"))); paint(); V.untip(); });
  V.click("[data-tren]", el => {
    const n = el.dataset.tren;
    V.ask("新文件名", [["ok", "改名"], ["", "取消"]], n.replace(/\.md$/, "")).then(t => {
      const raw = (t || "").trim(); if (!raw) return;
      const to = raw.replace(/[/\\\x00-\x1f]/g, "-").replace(/\.md$/i, "") + ".md";
      if (to !== n) V.todoWrite("rename", n, { to, mtime: F[n].mtime });
    });
  });
  V.click("[data-tdelf]", el => { const n = el.dataset.tdelf; V.ask(`删除 ${n}？里面的 todo 会一起删掉。`, [["del", "删除"], ["", "取消"]]).then(v => { if (v === "del") V.todoWrite("delete", n, { mtime: F[n].mtime }); }); });
  document.addEventListener("dblclick", e => { const t = e.target.closest("#todo [data-ted]"); if (t && !e.target.closest("[data-open]")) { editing = t.dataset.ted; paint(); } });
  document.addEventListener("keydown", e => {
    const inp = e.target.closest && e.target.closest("#todo .tedit"); if (!inp) return;
    if (e.key === "Escape") { e.stopPropagation(); editing = null; paint(); }
    else if (e.key === "Enter") { e.preventDefault(); const v = inp.value.trim(), at = find(inp.dataset.id); editing = null; if (v && at) save(at.file, SV.editTodo(seen(at.file), at.line, { text: v })); else paint(); }
  }, true);
  document.addEventListener("focusout", e => { if (e.target.closest && e.target.closest("#todo .tedit") && editing !== null) { editing = null; paint(); } });
  V.on("data", () => {
    const busy = editing !== null || $("#todo input:focus");
    if (!$("#todo").hidden && !busy) return refresh();
    load().then(() => {   // busy: data only, the screen keeps its version; hidden: no screen, so no snapshot either
      if ($("#todo").hidden) Object.values(F).forEach(f => { f.shown = null; });
      V.emit("todo-count");
    });
  });
})(V2);
