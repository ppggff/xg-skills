/* status viewer v2 — todo: a directory of markdown files, <dev_root>/todo/*.md, as a view beside the board. Each file
   is read like any doc; its checklist lines are the todos, @words tag a project (older #words too), wikilinks point at
   docs. This view lists the files and gathers every todo across them; the reader opens and edits a file.
   Writes carry the version the page shows, so a file changed elsewhere in between is refused, never overwritten. */
"use strict";
(function (V) {
  const { $, esc } = V, store = V.store;
  // per file: text/mtime follow the disk; shown/base are the version on screen — edits address its lines and are
  // saved against its mtime, so a file that moved underneath is refused (409) instead of having the wrong line changed
  const F = V.todoFiles = {};
  let tag = store.get("todo-tag", ""), showDone = false, editing = null, loaded = false;
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
  const save = (name, text) => V.todoWrite("write", name, { text, mtime: F[name] ? F[name].base : 0 });
  const refresh = () => load().then(paint).catch(e => { const b = $("#todo .tmain"); if (b) b.innerHTML = `<div class="derr"><b>读不到 todo 目录</b><br>${esc(e.message)}</div>`; });

  // an item's text: wikilinks and links open their doc, @tags and #tags are chips — tags only in the plain text between
  // links, and every piece escaped once, so nothing lands inside an attribute
  const LINK = /\[\[([^\]]+)\]\]|\[([^\]]+)\]\(([^)\s]+)\)/g;
  const link = (key, label, miss) => (key ? `<button class="tdl" data-open="${esc(key)}" data-tip="${esc(key)}">${esc(label)}</button>`
    : `<span class="tdl broken" data-tip="找不到：${esc(miss)}">${esc(label)}</span>`);
  const plain = t => esc(t).replace(/(^|\s)([@#])([\w.-]+)/g, '$1<span class="ttag">$2$3</span>');
  V.todoItemHTML = (text, file) => {
    let h = "", last = 0;
    text.replace(LINK, (all, wiki, label, href, at) => {
      h += plain(text.slice(last, at)); last = at + all.length;
      h += wiki ? link(SV.resolveWikiAny("[[" + wiki + "]]", V.D.sets), wiki.split("|").pop().split("/").pop(), wiki)
        : link(SV.resolveLink(href, "dev", DIR + file, V.D.sets), label, href);
      return all;
    });
    return h + plain(text.slice(last));
  };

  function itemsAll() {
    return Object.keys(F).sort().flatMap(n => { F[n].shown = F[n].text; F[n].base = F[n].mtime; return SV.parseTodo(F[n].shown).map(it => Object.assign({ file: n }, it)); });
  }
  function rowHTML(it) {
    const id = esc(it.file) + "|" + it.line;
    if (editing === id) return `<div class="titem ed"><input class="tedit" data-id="${id}" value="${esc(it.text)}" aria-label="改这一条"></div>`;
    return `<div class="titem${it.done ? " done" : ""}"><button class="tck" data-tck="${id}" aria-label="${it.done ? "标为未完成" : "标为完成"}">${it.done ? "✓" : ""}</button>`
      + `<span class="ttx" data-ted="${id}" data-tip="双击修改">${V.todoItemHTML(it.text, it.file)}</span>`
      + `<button class="tfile" data-open="dev:${DIR}${esc(it.file)}" data-tip="打开 ${esc(it.file)}">${esc(it.file.replace(/\.md$/, ""))}</button>`
      + `<button class="tdel" data-tdel="${id}" data-tip="删除这一条" aria-label="删除">×</button></div>`;
  }
  function paint() {
    const el = $("#todo"), main = el && $(".tmain", el), side = el && $(".tfiles", el); if (!main) return;
    const items = itemsAll(), tags = [...new Set(items.flatMap(i => i.tags))].sort(), files = Object.keys(F).sort();
    if (tag && !tags.includes(tag)) tag = "";
    const shown = items.filter(i => !tag || i.tags.includes(tag)), open = shown.filter(i => !i.done), done = shown.filter(i => i.done);
    const projs = Object.keys(V.D.board || {}).sort(), cur = store.get("todo-proj", ""), into = store.get("todo-into", "inbox.md");
    side.innerHTML = `<div class="tfh">文件</div>` + files.map(n => `<div class="tf"><button data-open="dev:${DIR}${esc(n)}" data-tip="在阅读栏打开">${esc(n.replace(/\.md$/, ""))}</button>`
      + `<em>${SV.parseTodo(F[n].text).filter(i => !i.done).length || ""}</em><button class="tfx" data-tren="${esc(n)}" data-tip="改名">✎</button>`
      + `<button class="tfx" data-tdelf="${esc(n)}" data-tip="删除这个文件">×</button></div>`).join("")
      + `<form class="tnew"><input placeholder="新建文件…" aria-label="新建 todo 文件"></form>`;
    const chips = tags.length ? `<div class="tchips"><button class="chip ${tag ? "" : "on"}" data-ttag="">全部<em>${items.filter(i => !i.done).length}</em></button>`
      + tags.map(t => `<button class="chip ${t === tag ? "on" : ""}" data-ttag="${esc(t)}">@${esc(t)}<em>${items.filter(i => !i.done && i.tags.includes(t)).length}</em></button>`).join("") + "</div>" : "";
    main.innerHTML = `<form class="tadd"><input class="tin" placeholder="写一条 todo，回车添加" aria-label="新的一条">`
      + `<select class="tinto" aria-label="写进哪个文件">${(files.includes(into) ? files : [into].concat(files)).map(n => `<option ${n === into ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>`
      + `<select class="tproj" aria-label="项目"><option value="">不标项目</option>${projs.map(p => `<option ${p === cur ? "selected" : ""}>${esc(p)}</option>`).join("")}</select>`
      + `<input class="tdoc" list="tdocs" placeholder="引用文档（可选）" aria-label="引用文档"><datalist id="tdocs">${V.docChoices().map(d => `<option value="${esc(d)}">`).join("")}</datalist><button class="tgo">添加</button></form>`
      + chips + (open.length ? open.map(rowHTML).join("") : `<div class="hint">${items.length ? "这里没有未完成的" : "还没有 todo。写在上面，存在 dev_root/todo/ 里。"}</div>`)
      + (done.length ? `<button class="tfold" data-tdone>${showDone ? "收起" : "展开"}已完成 ${done.length}</button>` + (showDone ? done.map(rowHTML).join("") : "") : "");
    const ed = $(".tedit", main); if (ed) { ed.focus(); ed.setSelectionRange(ed.value.length, ed.value.length); }
    V.emit("todo-count"); V.status();
  }
  // what a wikilink can name: recent docs first, then every dev doc, then the KB and the extra roots — as [[…]] targets
  V.docChoices = () => {
    const wiki = key => { const i = key.indexOf(":"), t = key.slice(0, i), r = key.slice(i + 1).replace(/\.md$/, ""); return t === "dev" ? r : t === "kb" && /^(wiki|raw)\//.test(r) ? r : t + "/" + r; };
    const all = V.recent.list("opened").concat(["dev", "kb", "ext"].flatMap(t => (V.D.tree[t] || []).map(x => t + ":" + x.path)));
    return [...new Set(all.map(wiki))];
  };
  V.todoOpen = () => Object.values(F).reduce((n, f) => n + SV.parseTodo(f.text).filter(i => !i.done).length, 0);
  const find = id => { const i = id.lastIndexOf("|"), file = id.slice(0, i), line = +id.slice(i + 1); return F[file] && SV.parseTodo(F[file].shown).find(x => x.line === line) && { file, line }; };

  V.views.todo = (k, loc, opt) => {
    const el = $("#todo");
    el.innerHTML = `<div class="phd"><button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button>` + V.paneHead(k)
      + '<div class="ppath"><bdi>dev_root / <b>todo</b></bdi></div>'
      + `<button class="ib" data-goboard="1" data-tip="回看板" aria-label="回看板">${V.I.grid}</button>${V.paneEnd(k)}</div>`
      + '<div class="tbody"><nav class="tfiles scroll"></nav><div class="tmain scroll"><div class="hint">读取中…</div></div></div>';
    if (loaded && !opt.entering) paint(); else refresh();
    V.status();
  };
  V.statusFns.todo = () => `<span><b>todo</b>　dev_root/todo/，${Object.keys(F).length} 个文件，未完成 ${V.todoOpen()}</span><span class="sp"></span>${V.stamp()}`;

  document.addEventListener("submit", e => {
    const add = e.target.closest("#todo .tadd"), mk = e.target.closest("#todo .tnew"); if (!add && !mk) return;
    e.preventDefault();
    if (mk) {
      const n = $("input", mk).value.trim().replace(/[/\\\x00-\x1f]/g, "-").replace(/\.md$/i, "") + ".md"; if (n === ".md") return;
      if (F[n]) return V.toast("已经有 " + n);
      return V.todoWrite("write", n, { text: "# " + n.replace(/\.md$/i, "") + "\n\n", mtime: 0 });
    }
    const text = $(".tin", add).value.trim(), proj = $(".tproj", add).value, into = $(".tinto", add).value, doc = $(".tdoc", add).value.trim();
    if (!text) return $(".tin", add).focus();
    store.set("todo-proj", proj); store.set("todo-into", into);
    const body = text + (proj && !new RegExp("[@#]" + proj.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b").test(text) ? " @" + proj : "") + (doc ? " [[" + doc + "]]" : "");
    save(into, SV.addTodo(F[into] ? F[into].shown : "", body));
  });
  V.click("[data-tck]", el => { const at = find(el.dataset.tck); if (!at) return; const it = SV.parseTodo(F[at.file].shown).find(x => x.line === at.line); save(at.file, SV.editTodo(F[at.file].shown, at.line, { done: !it.done })); });
  V.click("[data-tdel]", el => { const at = find(el.dataset.tdel); if (at) save(at.file, SV.editTodo(F[at.file].shown, at.line, { remove: true })); });
  V.click("[data-ttag]", el => { tag = el.dataset.ttag; store.set("todo-tag", tag); paint(); });
  V.click("[data-tdone]", () => { showDone = !showDone; paint(); });
  V.click("[data-tren]", el => {
    const n = el.dataset.tren, raw = (prompt("新文件名", n.replace(/\.md$/, "")) || "").trim(); if (!raw) return;
    const to = raw.replace(/[/\\\x00-\x1f]/g, "-").replace(/\.md$/i, "") + ".md";
    if (to !== n) V.todoWrite("rename", n, { to, mtime: F[n].mtime });
  });
  V.click("[data-tdelf]", el => { const n = el.dataset.tdelf; if (confirm(`删除 ${n}？里面的 todo 会一起删掉。`)) V.todoWrite("delete", n, { mtime: F[n].mtime }); });
  document.addEventListener("dblclick", e => { const t = e.target.closest("#todo [data-ted]"); if (t && !e.target.closest("[data-open]")) { editing = t.dataset.ted; paint(); } });
  document.addEventListener("keydown", e => {
    const inp = e.target.closest && e.target.closest("#todo .tedit"); if (!inp) return;
    if (e.key === "Escape") { e.stopPropagation(); editing = null; paint(); }
    else if (e.key === "Enter") { e.preventDefault(); const v = inp.value.trim(), at = find(inp.dataset.id); editing = null; if (v && at) save(at.file, SV.editTodo(F[at.file].shown, at.line, { text: v })); else paint(); }
  }, true);
  document.addEventListener("focusout", e => { if (e.target.closest && e.target.closest("#todo .tedit") && editing !== null) { editing = null; paint(); } });
  V.on("data", () => {
    const busy = editing !== null || $("#todo .tin:focus, #todo .tdoc:focus, #todo .tnew input:focus");
    if (!$("#todo").hidden && !busy) refresh(); else load().then(() => V.emit("todo-count"));   // busy: data only; the screen keeps its version
  });
})(V2);
