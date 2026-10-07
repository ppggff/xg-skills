/* status viewer v2 — todo files in the reader: a file under <dev_root>/todo/ reads like any doc, but its checkboxes can
   be ticked, its @projects show as tags, and 编辑 swaps the article for a source editor — markdown highlighted under a
   transparent textarea, @ completing a project and [[ completing a doc. Saves carry the version that was read. */
"use strict";
(function (V) {
  const { $, $$, esc } = V, P = V.P;
  const isTodo = loc => loc && loc.kind === "doc" && loc.tree === "dev" && /^todo\/[^/]+\.md$/.test(loc.rel);
  const fileOf = loc => loc.rel.slice("todo/".length);

  /* ---- reading: tickable checkboxes and @project tags ---- */
  // marked's own task items, in render order, located in the source by their raw text; a box is enabled only when
  // the line found is a task line in the same state, so an item we cannot place stays read-only rather than wrong
  const TOG = /^(\s*(?:>\s*)*(?:[-*+]|\d+[.)])\s+\[)( |x|X)(\])/;
  function taskLines(body) {
    const at = [];
    const walk = (tokens, from) => { let pos = from; (tokens || []).forEach(t => {
      const i = t.raw ? body.indexOf(t.raw, pos) : -1, s = i >= 0 ? i : pos;
      if (t.type === "list_item" && t.task) at.push(i >= 0 ? body.slice(0, i).split("\n").length - 1 : -1);
      walk(t.items, s); walk(t.tokens, s);
      if (i >= 0) pos = i + t.raw.length;
    }); };
    walk(window.marked.lexer(body), 0);
    return at;
  }
  V.on("rendered", k => {
    const p = P[k], loc = p.loc, todo = isTodo(loc) && p.doc && !p.doc.err && !p.chg;
    if (p.edit && !$(".tta", p.body)) p.edit = null;   // a re-render replaced the editor
    p.el.classList.toggle("tododoc", !!todo);
    if (!todo) return;
    const md = $(".md", p.body), lines = p.doc.text.split("\n"), at = taskLines(p.doc.body);
    $$('input[type="checkbox"]', md).forEach((box, i) => {
      const ln = at[i] >= 0 ? at[i] + p.doc.fmLines : -1, m = ln >= 0 && TOG.exec(lines[ln] || "");
      if (!m || (m[2] !== " ") !== box.checked) return;
      box.disabled = false; box.dataset.tline = ln; box.classList.add("tbox");
    });
    const walk = document.createTreeWalker(md, NodeFilter.SHOW_TEXT, { acceptNode: n => (n.parentElement.closest("code,pre,a,button") || !/(^|\s)@[\w.-]/.test(n.data) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
    const texts = []; while (walk.nextNode()) texts.push(walk.currentNode);
    texts.forEach(n => { const s = document.createElement("span"); s.innerHTML = esc(n.data).replace(/(^|\s)@([\w.-]+)/g, '$1<span class="ttag">@$2</span>'); n.replaceWith(...s.childNodes); });
  });
  document.addEventListener("change", e => {
    const box = e.target.closest && e.target.closest(".pbody .md input.tbox"); if (!box) return;
    const k = V.paneOf(box), p = P[k], loc = p.loc; if (!isTodo(loc)) return;
    const ls = p.doc.text.split("\n"), ln = +box.dataset.tline;
    ls[ln] = ls[ln].replace(TOG, (all, a, mark, b) => a + (box.checked ? "x" : " ") + b);
    const text = ls.join("\n");
    V.todoWrite("write", fileOf(loc), { text, mtime: p.doc.mtime }).then(() => { if (p.loc === loc) V.rerender(k); });
  });

  /* ---- the editor ---- */
  const HL = [   // line-level first, then inline; every rule runs on escaped text
    [/^(#{1,6} .*)$/, '<b class="h">$1</b>'],
    [/^(\s*[-*] \[[ xX]\])/, '<i class="ck">$1</i>'],
    [/(\[\[[^\]\n]*\]\])/g, '<i class="wl">$1</i>'],
    [/(`[^`\n]+`)/g, '<i class="cd">$1</i>'],
    [/(\[[^\]\n]+\]\([^)\s]+\))/g, '<i class="ln">$1</i>'],
    [/(^|\s)([@#][\w.-]+)/g, '$1<i class="tg">$2</i>'],
  ];
  function highlight(src) {
    let fence = false;
    return src.split("\n").map(l => {
      if (/^\s*(```|~~~)/.test(l)) { fence = !fence; return `<i class="cd">${esc(l)}</i>`; }
      if (fence) return `<i class="cd">${esc(l)}</i>`;
      return HL.reduce((h, [re, to]) => h.replace(re, to), esc(l));
    }).join("\n") + "\n";
  }
  const drafts = {};   // unsaved editor text per file, kept when the pane moves on; offered back on the next 编辑
  addEventListener("beforeunload", e => { if (["A", "B"].some(k => P[k].edit && $(".tta", P[k].body) && $(".tta", P[k].body).value !== P[k].edit.orig)) e.preventDefault(); });
  function open(k) {
    const p = P[k], loc = p.loc; if (!isTodo(loc) || !p.doc) return;
    const ed = { k, loc, base: p.doc.mtime, orig: p.doc.text }, draft = drafts[loc.rel];
    p.edit = ed;
    p.body.innerHTML = `<div class="tedw"><div class="tedbar"><b>编辑 ${esc(fileOf(loc))}</b><span>输入 @ 补全项目，[[ 补全文档　⌘S 保存　Esc 退出</span>`
      + `<button data-tsave>保存</button><button data-tcancel>取消</button></div><div class="ted"><pre class="thl" aria-hidden="true"></pre>`
      + `<textarea class="tta" spellcheck="false" aria-label="编辑 ${esc(fileOf(loc))}"></textarea><div class="tac" hidden></div></div></div>`;
    const ta = $(".tta", p.body), hl = $(".thl", p.body);
    ta.value = draft && draft !== ed.orig && confirm("上次有没保存的修改，恢复它吗？") ? draft : ed.orig; delete drafts[loc.rel];
    hl.innerHTML = highlight(ta.value);
    ta.addEventListener("input", () => { hl.innerHTML = highlight(ta.value); complete(ed, ta); });
    ta.addEventListener("scroll", () => { hl.scrollTop = ta.scrollTop; hl.scrollLeft = ta.scrollLeft; });
    ta.addEventListener("keydown", e => keys(ed, ta, e));
    ta.addEventListener("blur", () => setTimeout(() => { const ac = $(".tac", p.body); if (ac && !ac.contains(document.activeElement)) ac.hidden = true; }, 150));
    ta.focus();
  }
  function close(k, saved) {
    const p = P[k], ta = p.edit && $(".tta", p.body); if (!p.edit) return;
    if (!saved && ta && ta.value !== p.edit.orig && !confirm("放弃没保存的修改？")) return;
    p.edit = null; V.rerender(k);
  }
  // a save refused because the file changed elsewhere keeps the text and asks: overwrite with mine, or take theirs
  function save(k, force) {
    const p = P[k], ed = p.edit, ta = ed && $(".tta", p.body); if (!ta) return;
    const send = mtime => V.todoWrite("write", fileOf(ed.loc), { text: ta.value, mtime });
    const go = force ? V.api("/raw/dev/" + ed.loc.rel).then(r => +r.headers.get("X-Mtime") || 0).catch(() => 0).then(send) : send(ed.base);
    go.then(res => {
      if (p.edit !== ed) return;
      if (res.ok) return close(k, true);
      if (res.status === 409) $(".tedbar span", p.body).innerHTML = '<b class="tconf">这个文件在别处改过了。</b><button data-tforce>用我的覆盖</button><button data-ttheirs>放弃我的，看最新的</button>';
    });
  }
  V.on("nav", k => { const p = P[k], ta = p.edit && $(".tta", p.body); if (ta && ta.value !== p.edit.orig) drafts[p.edit.loc.rel] = ta.value; p.edit = null; });

  /* ---- completion: the token before the caret decides what is offered ---- */
  function tokenAt(ta) {
    const before = ta.value.slice(0, ta.selectionStart);
    let m = /(^|\s)@([\w.-]*)$/.exec(before);
    if (m) return { kind: "@", q: m[2], from: ta.selectionStart - m[2].length - 1 };
    m = /\[\[([^\]\n]*)$/.exec(before);
    if (m) return { kind: "[[", q: m[1], from: ta.selectionStart - m[1].length - 2 };
    return null;
  }
  function choices(tok) {
    const q = tok.q.toLowerCase();
    const pool = tok.kind === "@" ? Object.keys(V.D.board || {}).sort() : V.docChoices();
    const score = s => { const l = s.toLowerCase(), i = l.indexOf(q); if (!q) return 1; if (i >= 0) return 3 - (i > 0) + (l.lastIndexOf("/") < i); let j = 0; for (const c of l) if (c === q[j]) j++; return j === q.length ? 0.5 : -1; };
    return pool.map(s => [s, score(s)]).filter(x => x[1] > 0).sort((a, b) => b[1] - a[1]).slice(0, 8).map(x => x[0]);
  }
  function caretXY(ta) {   // a mirror of the text up to the caret, laid out like the textarea, tells where the caret sits
    const m = document.createElement("div"), cs = getComputedStyle(ta);
    ["fontFamily", "fontSize", "lineHeight", "padding", "border", "letterSpacing", "whiteSpace", "wordBreak", "overflowWrap", "tabSize"].forEach(x => { m.style[x] = cs[x]; });
    Object.assign(m.style, { position: "absolute", visibility: "hidden", width: ta.clientWidth + "px", whiteSpace: "pre-wrap" });
    m.textContent = ta.value.slice(0, ta.selectionStart);
    const s = document.createElement("span"); s.textContent = "​"; m.appendChild(s); ta.parentElement.appendChild(m);
    const at = { x: s.offsetLeft, y: s.offsetTop - ta.scrollTop + s.offsetHeight }; m.remove(); return at;
  }
  function complete(ed, ta) {
    const ac = $(".tac", P[ed.k].body), tok = tokenAt(ta), list = tok ? choices(tok) : [];
    ed.ac = tok && list.length ? { tok, list, sel: 0 } : null;
    if (!ed.ac) { ac.hidden = true; return; }
    const xy = caretXY(ta);
    ac.style.left = Math.min(xy.x, ta.clientWidth - 260) + "px"; ac.style.top = (xy.y + 4) + "px";
    paintAc(ed, ac); ac.hidden = false;
  }
  const paintAc = (ed, ac) => { ac.innerHTML = ed.ac.list.map((s, i) => `<button class="${i === ed.ac.sel ? "on" : ""}" data-tac="${i}">${ed.ac.tok.kind === "@" ? "@" : ""}${esc(s)}</button>`).join(""); };
  function accept(ed, ta, i) {
    const a = ed.ac, pick = a.list[i], ins = a.tok.kind === "@" ? "@" + pick + " " : "[[" + pick + "]]";
    const end = a.tok.kind === "[[" && ta.value.slice(ta.selectionStart, ta.selectionStart + 2) === "]]" ? ta.selectionStart + 2 : ta.selectionStart;
    ta.setRangeText(ins, a.tok.from, end, "end"); ed.ac = null;
    $(".tac", P[ed.k].body).hidden = true; $(".thl", P[ed.k].body).innerHTML = highlight(ta.value); ta.focus();
  }
  function keys(ed, ta, e) {
    if (e.isComposing || e.keyCode === 229) return;   // an IME is choosing: its Enter and arrows are not ours
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") { e.preventDefault(); e.stopPropagation(); return save(ed.k); }
    const ac = ed.ac;
    if (ac && (e.key === "ArrowDown" || e.key === "ArrowUp")) { e.preventDefault(); ac.sel = (ac.sel + (e.key === "ArrowDown" ? 1 : ac.list.length - 1)) % ac.list.length; return paintAc(ed, $(".tac", P[ed.k].body)); }
    if (ac && (e.key === "Enter" || e.key === "Tab")) { e.preventDefault(); return accept(ed, ta, ac.sel); }
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); if (ac) { ed.ac = null; $(".tac", P[ed.k].body).hidden = true; } else close(ed.k); }
  }
  document.addEventListener("mousedown", e => { const b = e.target.closest && e.target.closest(".tac [data-tac]"); if (!b) return; e.preventDefault(); const k = V.paneOf(b), ed = P[k].edit; if (ed && ed.ac) accept(ed, $(".tta", P[k].body), +b.dataset.tac); });
  V.click('.phd [data-t="tedit"]', el => open(V.paneOf(el)));
  V.click("[data-tsave]", el => save(V.paneOf(el)));
  V.click("[data-tcancel]", el => close(V.paneOf(el)));
  document.addEventListener("click", e => {   // the stale notice's 刷新 re-renders the pane: keep the text as a draft first
    const b = e.target.closest && e.target.closest("[data-stale]"); if (!b) return;
    const p = P[V.paneOf(b)], ta = p.edit && $(".tta", p.body); if (ta && ta.value !== p.edit.orig) drafts[p.edit.loc.rel] = ta.value;
  }, true);
  V.click("[data-tforce]", el => save(V.paneOf(el), true));
  V.click("[data-ttheirs]", el => { const k = V.paneOf(el); if (P[k].edit) { P[k].edit.orig = $(".tta", P[k].body).value; close(k, true); } });
})(V2);
