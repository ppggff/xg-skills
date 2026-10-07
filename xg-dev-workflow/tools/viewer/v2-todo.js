/* status viewer v2 — todo: notes and todos kept in <dev_root>/todo.md, a view beside the board. Items are the
   file's checklist lines; #words tag a project, markdown links point at docs. The page writes the whole file back
   with the version it read, so an edit made elsewhere in between is refused rather than overwritten. */
"use strict";
(function (V) {
  const { $, $$, esc } = V, store = V.store;
  // text/mtime follow the disk; shown/base are the version on screen — edits address its lines and are saved against
  // its mtime, so a file that moved underneath is refused (409) instead of having the wrong line changed
  const T = V.todo = { text: "", mtime: 0, loaded: false, shown: "", base: 0 };
  let tag = store.get("todo-tag", ""), showDone = false, editing = null;

  function load() {
    return V.api("/raw/dev/todo.md").then(r => { T.mtime = +r.headers.get("X-Mtime") || 0; return r.text(); })
      .catch(e => { if (e.status === 404) { T.mtime = 0; return ""; } throw e; })
      .then(t => { T.text = t; T.loaded = true; });
  }
  function save(text) {
    return fetch("/api/todo", { method: "POST", headers: { "Content-Type": "application/json", "X-SV-Write": "1" }, body: JSON.stringify({ text, mtime: T.base }) })
      .then(r => r.json().catch(() => ({})).then(d => ({ ok: r.ok, status: r.status, d })))
      .then(({ ok, status, d }) => {
        if (ok) { T.text = text; T.mtime = d.mtime; editing = null; return paint(); }
        V.toast(status === 409 ? "todo.md 在别处改过了，已重新读取，请再改一次" : "保存失败（" + status + "）");
        return refresh();
      }).catch(() => V.toast("保存失败：连不上 viewer"));
  }
  const refresh = () => load().then(paint).catch(e => { const b = $("#todo .tbody"); if (b) b.innerHTML = `<div class="derr"><b>读不到 todo.md</b><br>${esc(e.message)}</div>`; });

  // an item's text: links to docs open them, #tags are chips, the rest is plain text
  function itemHTML(text) {
    return esc(text).replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (all, label, href) => {
      const raw = href.replace(/&amp;/g, "&"), kb = raw.startsWith("kb:");
      const key = SV.resolveLink(kb ? raw.slice(3) : raw, kb ? "kb" : "dev", kb ? "index.md" : "todo.md", V.D.sets);
      return key ? `<button class="tdl" data-open="${esc(key)}" data-tip="${esc(key)}">${label}</button>` : `<span class="tdl broken" data-tip="找不到：${esc(raw)}">${label}</span>`;
    }).replace(/(^|\s)#([\w.-]+)/g, (all, sp, t) => `${sp}<span class="ttag">#${t}</span>`);
  }
  function rowHTML(it) {
    if (editing === it.line) return `<div class="titem ed"><input class="tedit" data-line="${it.line}" value="${esc(it.text)}" aria-label="改这一条"></div>`;
    return `<div class="titem${it.done ? " done" : ""}"><button class="tck" data-tck="${it.line}" aria-label="${it.done ? "标为未完成" : "标为完成"}">${it.done ? "✓" : ""}</button>`
      + `<span class="ttx" data-ted="${it.line}" data-tip="双击修改">${itemHTML(it.text)}</span>`
      + `<button class="tdel" data-tdel="${it.line}" data-tip="删除这一条" aria-label="删除">×</button></div>`;
  }
  function paint() {
    const el = $("#todo"), body = el && $(".tbody", el); if (!body) return;
    T.shown = T.text; T.base = T.mtime;
    const items = SV.parseTodo(T.shown), tags = [...new Set(items.flatMap(i => i.tags))].sort();
    if (tag && !tags.includes(tag)) tag = "";
    const shown = items.filter(i => !tag || i.tags.includes(tag)), open = shown.filter(i => !i.done), done = shown.filter(i => i.done);
    const projs = Object.keys(V.D.board || {}).sort(), cur = store.get("todo-proj", "");
    const chips = tags.length ? `<div class="tchips"><button class="chip ${tag ? "" : "on"}" data-ttag="">全部<em>${items.filter(i => !i.done).length}</em></button>`
      + tags.map(t => `<button class="chip ${t === tag ? "on" : ""}" data-ttag="${esc(t)}">#${esc(t)}<em>${items.filter(i => !i.done && i.tags.includes(t)).length}</em></button>`).join("") + "</div>" : "";
    body.innerHTML = `<form class="tadd"><input class="tin" placeholder="写一条 todo 或笔记，回车添加" aria-label="新的一条">`
      + `<select class="tproj" aria-label="项目"><option value="">不标项目</option>${projs.map(p => `<option ${p === cur ? "selected" : ""}>${esc(p)}</option>`).join("")}</select>`
      + `<input class="tdoc" list="tdocs" placeholder="引用文档（可选）" aria-label="引用文档"><datalist id="tdocs">${docOptions()}</datalist><button class="tgo">添加</button></form>`
      + chips + (open.length ? open.map(rowHTML).join("") : `<div class="hint">${items.length ? "这里没有未完成的" : "还没有 todo。写在上面，存在 dev_root/todo.md。"}</div>`)
      + (done.length ? `<button class="tfold" data-tdone>${showDone ? "收起" : "展开"}已完成 ${done.length}</button>` + (showDone ? done.map(rowHTML).join("") : "") : "");
    const ed = $(".tedit", body); if (ed) { ed.focus(); ed.setSelectionRange(ed.value.length, ed.value.length); }
    V.emit("todo-count"); V.status();
  }
  const docOptions = () => V.recent.list("opened").concat(V.D.tree.dev.map(x => "dev:" + x.path)).filter((k, i, a) => a.indexOf(k) === i)
    .map(k => `<option value="${esc(k.startsWith("dev:") ? k.slice(4) : k)}">`).join("");
  V.todoOpen = () => SV.parseTodo(T.text).filter(i => !i.done).length;

  V.views.todo = (k, loc, opt) => {
    const el = $("#todo");
    el.innerHTML = `<div class="phd"><button class="ib navb" data-navb aria-label="导航">${V.I.menu}</button>` + V.paneHead(k)
      + '<div class="ppath"><bdi>dev_root / <b>todo</b></bdi></div>'
      + `<button class="ib" data-goboard="1" data-tip="回看板" aria-label="回看板">${V.I.grid}</button>${V.paneEnd(k)}</div>`
      + '<div class="tbody scroll"><div class="hint">读取中…</div></div>';
    if (T.loaded && !opt.entering) paint(); else refresh();
    V.status();
  };
  V.statusFns.todo = () => `<span><b>todo</b>　dev_root/todo.md，未完成 ${V.todoOpen()}</span><span class="sp"></span>${V.stamp()}`;

  document.addEventListener("submit", e => {
    const f = e.target.closest("#todo .tadd"); if (!f) return;
    e.preventDefault();
    const text = $(".tin", f).value.trim(), proj = $(".tproj", f).value, doc = $(".tdoc", f).value.trim();
    if (!text) return $(".tin", f).focus();
    store.set("todo-proj", proj);
    const link = doc ? ` [${doc.split("/").pop().replace(/\.md$/, "")}](${doc})` : "";
    save(SV.addTodo(T.shown, text + (proj && !text.includes("#" + proj) ? " #" + proj : "") + link));
  });
  V.click("[data-tck]", el => { const it = SV.parseTodo(T.shown).find(i => i.line === +el.dataset.tck); if (it) save(SV.editTodo(T.shown, it.line, { done: !it.done })); });
  V.click("[data-tdel]", el => save(SV.editTodo(T.shown, +el.dataset.tdel, { remove: true })));
  V.click("[data-ttag]", el => { tag = el.dataset.ttag; store.set("todo-tag", tag); paint(); });
  V.click("[data-tdone]", () => { showDone = !showDone; paint(); });
  document.addEventListener("dblclick", e => { const t = e.target.closest("#todo [data-ted]"); if (t && !e.target.closest("[data-open]")) { editing = +t.dataset.ted; paint(); } });
  document.addEventListener("keydown", e => {
    const inp = e.target.closest && e.target.closest("#todo .tedit"); if (!inp) return;
    if (e.key === "Escape") { e.stopPropagation(); editing = null; paint(); }
    else if (e.key === "Enter") { e.preventDefault(); const v = inp.value.trim(), line = +inp.dataset.line; editing = null; if (v) save(SV.editTodo(T.shown, line, { text: v })); else paint(); }
  }, true);
  document.addEventListener("focusout", e => { if (e.target.closest && e.target.closest("#todo .tedit") && editing !== null) { editing = null; paint(); } });
  V.on("data", () => { if (!$("#todo").hidden && editing === null && !$("#todo .tin:focus, #todo .tdoc:focus")) refresh(); else if (T.loaded) load().then(() => V.emit("todo-count")); });
  V.on("init", () => load().then(() => V.emit("todo-count")).catch(() => {}));
})(V2);
