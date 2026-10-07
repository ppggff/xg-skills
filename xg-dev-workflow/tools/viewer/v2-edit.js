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
    // @tags as chips; the date and priority marks of each task as the same small labels the todo view shows
    const MARK = /[➕📅✅]\s*\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?|[⏫🔼🔽]/;
    const walk = document.createTreeWalker(md, NodeFilter.SHOW_TEXT, { acceptNode: n => (n.parentElement.closest("code,pre,a,button") || !(/(^|\s)@[\w.-]/.test(n.data) || MARK.test(n.data)) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
    const texts = []; while (walk.nextNode()) texts.push(walk.currentNode);
    texts.forEach(n => {
      const li = n.parentElement.closest("li"), m = SV.todoMeta(n.data), s = document.createElement("span");
      s.innerHTML = esc(MARK.test(n.data) ? n.data.replace(new RegExp(MARK.source, "g"), "").replace(/\s+$/, " ") : n.data).replace(/(^|\s)@([\w.-]+)/g, '$1<span class="ttag">@$2</span>')
        + (MARK.test(n.data) ? V.todoMetaHTML(m, !!(li && li.querySelector(":scope > input:checked"))) : "");
      n.replaceWith(...s.childNodes);
    });
    $$("li", md).forEach(li => {   // subtask progress on an item whose own list has tasks
      const own = li.querySelector(":scope > input[type=checkbox]"), subs = $$(":scope > ul input[type=checkbox], :scope > ol input[type=checkbox]", li);
      if (!own || !subs.length) return;
      const b = document.createElement("span"); b.className = "tprog"; b.textContent = subs.filter(x => x.checked).length + "/" + subs.length;
      const sub = li.querySelector(":scope > ul, :scope > ol"); li.insertBefore(b, sub);
    });
  });
  document.addEventListener("change", e => {
    const box = e.target.closest && e.target.closest(".pbody .md input.tbox"); if (!box) return;
    const k = V.paneOf(box), p = P[k], loc = p.loc; if (!isTodo(loc)) return;
    const ln = +box.dataset.tline, day = SV.todoStamp(new Date()).slice(0, 10);
    let text = SV.editTodo(p.doc.text, ln, { done: box.checked, today: day });   // a plain task line: the mark and ✅ today
    if (text === p.doc.text) { const ls = text.split("\n"); ls[ln] = ls[ln].replace(TOG, (all, a, mark, b) => a + (box.checked ? "x" : " ") + b); text = ls.join("\n"); }
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
  /* ---- drafts: kept in this browser per file until saved or dropped, so a reload or a crash loses nothing ---- */
  const DK = rel => "draft:" + rel;
  const dropDraft = rel => V.store.del(DK(rel));
  addEventListener("beforeunload", e => { if (["A", "B"].some(k => P[k].edit && $(".tta", P[k].body) && $(".tta", P[k].body).value !== P[k].edit.orig)) e.preventDefault(); });

  /* ---- editing primitives: every change goes through insertText so the browser's undo keeps working ---- */
  function ins(ta, text, from, to) {
    ta.focus();
    if (from != null) ta.setSelectionRange(from, to == null ? from : to);
    if (!document.execCommand("insertText", false, text)) { ta.setRangeText(text, ta.selectionStart, ta.selectionEnd, "end"); ta.dispatchEvent(new Event("input")); }
  }
  const lineStart = (v, i) => v.lastIndexOf("\n", i - 1) + 1;
  const lineEnd = (v, i) => { const j = v.indexOf("\n", i); return j < 0 ? v.length : j; };
  const stamp = () => SV.todoStamp(new Date()), day = n => SV.todoStamp(new Date(Date.now() + n * 864e5)).slice(0, 10);
  const PREFIX = /^(\s*)(?:>\s?|#{1,6}\s+|(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?)?/;
  function wrap(ta, mark) {
    const a = ta.selectionStart, b = ta.selectionEnd, sel = ta.value.slice(a, b);
    ins(ta, mark + sel + mark, a, b);
    if (!sel) ta.setSelectionRange(a + mark.length, a + mark.length);
  }
  function lines(ta, fn) {   // rewrite the selected lines; a caret (no selection) keeps its distance from the line's end
    const v = ta.value, c = ta.selectionStart, single = c === ta.selectionEnd, a = lineStart(v, c), b = lineEnd(v, ta.selectionEnd);
    const out = v.slice(a, b).split("\n").map(fn).join("\n");
    ins(ta, out, a, b);
    if (single) { const p = Math.max(a, a + out.length - (b - c)); ta.setSelectionRange(p, p); } else ta.setSelectionRange(a, a + out.length);
  }
  const setPrefix = (ta, make) => lines(ta, l => { const m = PREFIX.exec(l); return m[1] + make(l.slice(m[1].length, m[0].length), l.slice(m[0].length)); });
  const toggle = p => (old, rest) => (old.trim() === p.trim() ? rest : p + rest);
  function newTodo(ta, below) {   // a fresh unticked item with its creation time; the caret waits where the text goes
    const v = ta.value, at = below ? lineEnd(v, ta.selectionEnd) : ta.selectionStart, indent = below ? /^\s*/.exec(v.slice(lineStart(v, at), at))[0] : "";
    const head = (below && at > 0 ? "\n" : "") + indent + "- [ ] ";
    ins(ta, head + " ➕ " + stamp(), at, at);
    const c = at + head.length; ta.setSelectionRange(c, c);
  }
  function mark(ta, sym, date) {   // a date or priority mark at the end of the current line, replacing one of its kind
    const v = ta.value, a = lineStart(v, ta.selectionStart), b = lineEnd(v, ta.selectionStart), line = v.slice(a, b);
    const kind = sym === "📅" ? /\s*📅\s*\d{4}-\d{2}-\d{2}/ : /\s*[⏫🔼🔽]/;
    const add = " " + sym + (date ? " " + date : "");
    const nl = kind.test(line) ? line.replace(kind, add) : line.replace(/\s*(?=➕|$)/, add + (/➕/.test(line) ? " " : ""));
    ins(ta, nl, a, b);
  }
  const ACT = {
    b: ta => wrap(ta, "**"), i: ta => wrap(ta, "*"), code: ta => wrap(ta, "`"),
    h: ta => setPrefix(ta, old => { const n = (/^#+/.exec(old.trim()) || [""])[0].length; return n >= 3 ? "" : "#".repeat(n + 1) + " "; }),
    h1: ta => setPrefix(ta, () => "# "), h2: ta => setPrefix(ta, () => "## "), h3: ta => setPrefix(ta, () => "### "),
    ul: ta => setPrefix(ta, toggle("- ")), ol: ta => setPrefix(ta, toggle("1. ")), quote: ta => setPrefix(ta, toggle("> ")),
    task: ta => setPrefix(ta, (old, rest) => (/\[[ xX]\]/.test(old) ? rest : "- [ ] " + rest + (/➕/.test(rest) ? "" : " ➕ " + stamp()))),
    todo: ta => newTodo(ta, true),
    link: ta => ins(ta, "[["), time: ta => ins(ta, stamp()), today: ta => ins(ta, day(0)),
    due: ta => mark(ta, "📅", day(1)), due0: ta => mark(ta, "📅", day(0)), due7: ta => mark(ta, "📅", day(7)),
    p1: ta => mark(ta, "⏫"), p2: ta => mark(ta, "🔼"), p3: ta => mark(ta, "🔽"),
    fence: ta => { const a = ta.selectionStart; ins(ta, "```\n\n```"); ta.setSelectionRange(a + 4, a + 4); },
    hr: ta => ins(ta, "\n---\n"),
  };
  const TOOLS = [["b", "<b>B</b>", "加粗 ⌘B"], ["i", "<i>I</i>", "斜体 ⌘I"], ["code", "`", "行内代码"], ["h", "H", "标题（再点一级）"],
    ["ul", "•", "列表"], ["ol", "1.", "有序列表"], ["task", "☐", "设为 todo"], ["quote", "❝", "引用"], ["link", "[[", "链接文档"],
    ["time", "⏱", "插入现在时间"], ["due", "📅", "截止日期（明天，可改）"], ["p1", "⏫", "高优先级"], ["todo", "＋todo", "在下面新起一条 todo"]];
  // the / menu: Notion / Obsidian style, filtered by any of the names as you type
  const CMDS = [["todo", "todo 待办", "task"], ["h1", "标题 1", "heading"], ["h2", "标题 2", "heading"], ["h3", "标题 3", "heading"],
    ["ul", "列表", "bullet list"], ["ol", "有序列表", "numbered list"], ["quote", "引用", "quote"], ["fence", "代码块", "code block"],
    ["hr", "分隔线", "divider"], ["link", "链接文档", "link wikilink"], ["today", "今天日期", "date today"], ["time", "现在时间", "time now"],
    ["due0", "截止：今天", "due today"], ["due", "截止：明天", "due tomorrow"], ["due7", "截止：一周后", "due week"],
    ["p1", "优先级：高 ⏫", "priority high"], ["p2", "优先级：中 🔼", "priority medium"], ["p3", "优先级：低 🔽", "priority low"]];

  /* ---- open, close, save ---- */
  function open(k, line) {
    const p = P[k], loc = p.loc; if (!isTodo(loc) || !p.doc || p.edit) return;
    const ed = { k, loc, base: p.doc.mtime, orig: p.doc.text }, draft = V.store.get(DK(loc.rel), null);
    p.edit = ed;
    p.body.innerHTML = `<div class="tedw"><div class="tedbar"><b>编辑 ${esc(fileOf(loc))}</b><span>/ 命令　@ 项目　[[ 文档　⌘S 保存　Esc 退出</span>`
      + `<button data-tsave>保存</button><button data-tcancel>取消</button></div>`
      + `<div class="ttool">${TOOLS.map(([a, l, t]) => `<button data-tact="${a}" data-tip="${t}" aria-label="${t}">${l}</button>`).join("")}</div>`
      + `<div class="ted"><pre class="thl" aria-hidden="true"></pre><textarea class="tta" spellcheck="false" aria-label="编辑 ${esc(fileOf(loc))}"></textarea>`
      + `<div class="tac" hidden></div></div></div>`;
    const ta = $(".tta", p.body), hl = $(".thl", p.body);
    if (draft != null && draft !== ed.orig && confirm("这个文件有没保存的草稿，恢复它吗？")) ta.value = draft; else { ta.value = ed.orig; dropDraft(loc.rel); }
    hl.innerHTML = highlight(ta.value);
    let dt = 0;
    ta.addEventListener("input", () => {
      hl.innerHTML = highlight(ta.value); complete(ed, ta);
      clearTimeout(dt); dt = setTimeout(() => (ta.value === ed.orig ? dropDraft(loc.rel) : V.store.set(DK(loc.rel), ta.value)), 400);
    });
    ta.addEventListener("scroll", () => { hl.scrollTop = ta.scrollTop; hl.scrollLeft = ta.scrollLeft; });
    ta.addEventListener("keydown", e => keys(ed, ta, e));
    ta.addEventListener("paste", e => paste(ta, e));
    ta.addEventListener("blur", () => setTimeout(() => { const ac = $(".tac", p.body); if (ac && !ac.contains(document.activeElement)) ac.hidden = true; }, 150));
    ta.focus();
    if (line != null) {
      const pos = ta.value.split("\n").slice(0, line).reduce((n, l) => n + l.length + 1, 0);
      ta.setSelectionRange(lineEnd(ta.value, pos), lineEnd(ta.value, pos));
      ta.scrollTop = Math.max(0, line * parseFloat(getComputedStyle(ta).lineHeight) - ta.clientHeight / 3);
    }
    keyboardBar(p);
  }
  function close(k, saved) {
    const p = P[k], ta = p.edit && $(".tta", p.body); if (!p.edit) return;
    if (!saved && ta && ta.value !== p.edit.orig && !confirm("放弃没保存的修改？")) return;
    dropDraft(p.edit.loc.rel); p.edit = null; V.rerender(k);
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
  V.on("nav", k => { P[k].edit = null; });   // the draft is already in local storage
  // on a phone the toolbar rides just above the on-screen keyboard
  function keyboardBar(p) {
    const vv = window.visualViewport, bar = $(".ttool", p.body); if (!vv || !bar || !V.isNarrow()) return;
    const place = () => { if (!bar.isConnected) { vv.removeEventListener("resize", place); vv.removeEventListener("scroll", place); return; }
      bar.style.setProperty("--kb", Math.max(0, innerHeight - vv.height - vv.offsetTop) + "px"); };
    vv.addEventListener("resize", place); vv.addEventListener("scroll", place); place();
  }

  /* ---- completion: the token before the caret decides what is offered (@ project, [[ doc, / command) ---- */
  function tokenAt(ta) {
    const before = ta.value.slice(0, ta.selectionStart);
    let m = /(^|\s)@([\w.-]*)$/.exec(before);
    if (m) return { kind: "@", q: m[2], from: ta.selectionStart - m[2].length - 1 };
    m = /\[\[([^\]\n]*)$/.exec(before);
    if (m) return { kind: "[[", q: m[1], from: ta.selectionStart - m[1].length - 2 };
    m = /(^|\s)\/([^\s/]*)$/.exec(before);
    if (m) return { kind: "/", q: m[2], from: ta.selectionStart - m[2].length - 1 };
    return null;
  }
  const fuzzy = (q, s) => { const l = s.toLowerCase(), i = l.indexOf(q); if (!q) return 1; if (i >= 0) return 3 - (i > 0) + (l.lastIndexOf("/") < i); let j = 0; for (const c of l) if (c === q[j]) j++; return j === q.length ? 0.5 : -1; };
  function choices(tok) {
    const q = tok.q.toLowerCase();
    if (tok.kind === "/") return CMDS.map(c => [c, Math.max(fuzzy(q, c[0]), fuzzy(q, c[1]), fuzzy(q, c[2]))]).filter(x => x[1] > 0).sort((a, b) => b[1] - a[1]).map(x => x[0]);
    const pool = tok.kind === "@" ? Object.keys(V.D.board || {}).sort() : V.docChoices();
    return pool.map(s => [s, fuzzy(q, s)]).filter(x => x[1] > 0).sort((a, b) => b[1] - a[1]).slice(0, 8).map(x => x[0]);
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
    ac.style.left = Math.max(0, Math.min(xy.x, ta.clientWidth - 260)) + "px"; ac.style.top = (xy.y + 4) + "px";
    paintAc(ed, ac); ac.hidden = false;
  }
  const paintAc = (ed, ac) => { ac.innerHTML = ed.ac.list.map((s, i) => `<button class="${i === ed.ac.sel ? "on" : ""}" data-tac="${i}">`
    + (ed.ac.tok.kind === "/" ? `${esc(s[1])}<em>${esc(s[2])}</em>` : (ed.ac.tok.kind === "@" ? "@" : "") + esc(s)) + "</button>").join(""); };
  function accept(ed, ta, i) {
    const a = ed.ac, pick = a.list[i]; ed.ac = null; $(".tac", P[ed.k].body).hidden = true;
    if (a.tok.kind === "/") { ins(ta, "", a.tok.from, ta.selectionStart); ACT[pick[0]](ta); return; }
    const ins2 = a.tok.kind === "@" ? "@" + pick + " " : "[[" + pick + "]]";
    const end = a.tok.kind === "[[" && ta.value.slice(ta.selectionStart, ta.selectionStart + 2) === "]]" ? ta.selectionStart + 2 : ta.selectionStart;
    ins(ta, ins2, a.tok.from, end);
  }

  /* ---- keys: menus first, then save, continuation, indent, marks and pairs ---- */
  const PAIRS = { "[": "]", "(": ")", "`": "`" };
  function enter(ta, e) {   // a list line continues itself; an empty item ends the list; the caret before trailing marks counts as the end
    const v = ta.value, at = ta.selectionStart; if (at !== ta.selectionEnd) return;
    const a = lineStart(v, at), b = lineEnd(v, at), c = SV.continueLine(v.slice(a, b));
    if (!c || !/^\s*(?:[➕📅✅⏫🔼🔽].*)?$/.test(v.slice(at, b))) return;
    e.preventDefault();
    if (c.empty) return ins(ta, /^\s*/.exec(v.slice(a, b))[0], a, b);
    const head = "\n" + c.next;
    ins(ta, head + (c.todo ? " ➕ " + stamp() : ""), b, b);
    ta.setSelectionRange(b + head.length, b + head.length);
  }
  const indent = (ta, out) => lines(ta, l => (out ? l.replace(/^ {1,2}/, "") : "  " + l));
  function keys(ed, ta, e) {
    if (e.isComposing || e.keyCode === 229) return;   // an IME is choosing: its Enter and arrows are not ours
    const cmd = e.metaKey || e.ctrlKey, k = e.key;
    if (cmd && k.toLowerCase() === "s") { e.preventDefault(); e.stopPropagation(); return save(ed.k); }
    const ac = ed.ac;
    if (ac && (k === "ArrowDown" || k === "ArrowUp")) { e.preventDefault(); ac.sel = (ac.sel + (k === "ArrowDown" ? 1 : ac.list.length - 1)) % ac.list.length; return paintAc(ed, $(".tac", P[ed.k].body)); }
    if (ac && (k === "Enter" || k === "Tab")) { e.preventDefault(); return accept(ed, ta, ac.sel); }
    if (k === "Escape") { e.preventDefault(); e.stopPropagation(); if (ac) { ed.ac = null; $(".tac", P[ed.k].body).hidden = true; } else close(ed.k); return; }
    if (cmd && (k.toLowerCase() === "b" || k.toLowerCase() === "i")) { e.preventDefault(); e.stopPropagation(); return wrap(ta, k.toLowerCase() === "b" ? "**" : "*"); }
    if (cmd || e.altKey) return;
    if (k === "Enter" && !e.shiftKey) return enter(ta, e);
    if (k === "Tab") { e.preventDefault(); return indent(ta, e.shiftKey); }
    const v = ta.value, at = ta.selectionStart, sel = ta.selectionEnd > at;
    if (!sel && (k === "]" || k === ")" || k === "`") && v[at] === k) { e.preventDefault(); return ta.setSelectionRange(at + 1, at + 1); }   // step over the closing half
    if (PAIRS[k] && !(k === "`" && (v[at - 1] === "`" || v[at] === "`"))) {   // the other half comes too (not inside a run of backticks)
      e.preventDefault();
      if (sel) return wrap(ta, k === "`" ? "`" : k) || null;
      ins(ta, k + PAIRS[k], at, at); ta.setSelectionRange(at + 1, at + 1);
    }
  }
  function paste(ta, e) {   // a web address pasted over selected text becomes a link
    const url = (e.clipboardData && e.clipboardData.getData("text/plain") || "").trim(), a = ta.selectionStart, b = ta.selectionEnd;
    if (b > a && /^https?:\/\/\S+$/.test(url)) { e.preventDefault(); ins(ta, "[" + ta.value.slice(a, b) + "](" + url + ")", a, b); }
  }

  /* ---- entry points: the head button, e, a double-click on the text; the toolbar and the menus ---- */
  V.click('.phd [data-t="tedit"]', el => open(V.paneOf(el)));
  V.hotkey("e", () => { const k = V.navPane(); if (isTodo(P[k].loc)) open(k); });
  document.addEventListener("dblclick", e => {
    const md = e.target.closest && e.target.closest(".pbody .md"); if (!md || e.target.closest("a,button,input,.cite,.tdl,.ttag")) return;
    const k = V.paneOf(md); if (!isTodo(P[k].loc)) return;
    const li = e.target.closest("li"), box = li && li.querySelector(":scope > input.tbox");
    let line = box ? +box.dataset.tline : V.lineOf(k, e.target);
    if (!box && li && line != null) {   // inside a list block: the line whose text starts like this item's
      const want = (li.firstChild && li.firstChild.textContent || "").trim().slice(0, 12), ls = P[k].doc.text.split("\n");
      const j = want ? ls.findIndex((l, n) => n >= line && l.includes(want)) : -1; if (j >= 0) line = j;
    }
    window.getSelection().removeAllRanges(); open(k, line);
  });
  document.addEventListener("mousedown", e => {
    const b = e.target.closest && e.target.closest(".tac [data-tac], .ttool [data-tact]"); if (!b) return;
    e.preventDefault(); const k = V.paneOf(b), ed = P[k].edit, ta = ed && $(".tta", P[k].body); if (!ta) return;
    if (b.dataset.tact) ACT[b.dataset.tact](ta); else if (ed.ac) accept(ed, ta, +b.dataset.tac);
  });
  V.click("[data-tsave]", el => save(V.paneOf(el)));
  V.click("[data-tcancel]", el => close(V.paneOf(el)));
  V.click("[data-tforce]", el => save(V.paneOf(el), true));
  V.click("[data-ttheirs]", el => { const k = V.paneOf(el); if (P[k].edit) { P[k].edit.orig = $(".tta", P[k].body).value; close(k, true); } });
})(V2);
