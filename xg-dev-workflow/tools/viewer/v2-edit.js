/* status viewer v2 — todo files in the reader: a file under <dev_root>/todo/ reads like any doc, but its checkboxes can
   be ticked, its @projects show as tags, and 编辑 swaps the article for a source editor — markdown highlighted under a
   transparent textarea, @ completing a project and [[ completing a doc. Saves carry the version that was read. */
"use strict";
(function (V) {
  const { $, $$, esc } = V, P = V.P;
  const isTodo = loc => loc && loc.kind === "doc" && loc.tree === "dev" && /^todo\/[^/]+\.md$/.test(loc.rel);
  const fileOf = loc => loc.rel.slice("todo/".length);

  /* ---- reading: tickable checkboxes and @project tags ---- */
  V.on("rendered", k => {
    const p = P[k], loc = p.loc, todo = isTodo(loc) && p.doc && !p.doc.err && !p.chg;
    p.el.classList.toggle("tododoc", !!todo);
    if (!todo) return;
    const md = $(".md", p.body), items = SV.parseTodo(p.doc.text);
    $$('input[type="checkbox"]', md).forEach((box, i) => {
      const it = items[i]; if (!it) return;
      box.disabled = false; box.dataset.tline = it.line; box.classList.add("tbox");
    });
    const walk = document.createTreeWalker(md, NodeFilter.SHOW_TEXT, { acceptNode: n => (n.parentElement.closest("code,pre,a,button") || !/(^|\s)@[\w.-]/.test(n.data) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
    const texts = []; while (walk.nextNode()) texts.push(walk.currentNode);
    texts.forEach(n => { const s = document.createElement("span"); s.innerHTML = esc(n.data).replace(/(^|\s)@([\w.-]+)/g, '$1<span class="ttag">@$2</span>'); n.replaceWith(...s.childNodes); });
  });
  document.addEventListener("change", e => {
    const box = e.target.closest && e.target.closest(".pbody .md input.tbox"); if (!box) return;
    const k = V.paneOf(box), p = P[k], loc = p.loc; if (!isTodo(loc)) return;
    const text = SV.editTodo(p.doc.text, +box.dataset.tline, { done: box.checked });
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
  function open(k) {
    const p = P[k], loc = p.loc; if (!isTodo(loc) || !p.doc) return;
    const ed = { k, loc, base: p.doc.mtime, orig: p.doc.text };
    p.edit = ed;
    p.body.innerHTML = `<div class="tedw"><div class="tedbar"><b>编辑 ${esc(fileOf(loc))}</b><span>输入 @ 补全项目，[[ 补全文档　⌘S 保存　Esc 退出</span>`
      + `<button data-tsave>保存</button><button data-tcancel>取消</button></div><div class="ted"><pre class="thl" aria-hidden="true"></pre>`
      + `<textarea class="tta" spellcheck="false" aria-label="编辑 ${esc(fileOf(loc))}"></textarea><div class="tac" hidden></div></div></div>`;
    const ta = $(".tta", p.body), hl = $(".thl", p.body);
    ta.value = ed.orig; hl.innerHTML = highlight(ta.value);
    ta.addEventListener("input", () => { hl.innerHTML = highlight(ta.value); complete(ed, ta); });
    ta.addEventListener("scroll", () => { hl.scrollTop = ta.scrollTop; hl.scrollLeft = ta.scrollLeft; });
    ta.addEventListener("keydown", e => keys(ed, ta, e));
    ta.addEventListener("blur", () => setTimeout(() => { const ac = $(".tac", p.body); if (ac && !ac.contains(document.activeElement)) ac.hidden = true; }, 150));
    ta.focus();
  }
  function close(k, saved) {
    const p = P[k]; if (!p.edit) return;
    if (!saved && $(".tta", p.body).value !== p.edit.orig && !confirm("放弃没保存的修改？")) return;
    p.edit = null; V.rerender(k);
  }
  function save(k) {
    const p = P[k], ed = p.edit; if (!ed) return;
    V.todoWrite("write", fileOf(ed.loc), { text: $(".tta", p.body).value, mtime: ed.base }).then(res => { if (res.ok && p.edit === ed) close(k, true); });
  }
  V.on("nav", k => { if (P[k].edit) P[k].edit = null; });

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
})(V2);
