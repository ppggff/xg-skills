// shots-v2.mjs — the refined frontend's (/v2) half of the screenshot harness: how to drive each view,
// what to measure, and its behavioural scenarios. Loaded by shots.mjs when --url ends in /v2; the page
// exposes its namespace as window.V2, so views are driven through V2.nav, the same call a click makes.
//   node tools/viewer/shots.mjs --url http://127.0.0.1:18790/v2 --scenario skeleton,storage,board
const J = JSON.stringify;
const nav = (k, loc) => `V2.nav(${J(k)}, ${J(loc)})`;
const docLoc = (o) => { const [tree, ...rest] = o.doc.split("/"); return { kind: "doc", tree, rel: rest.join("/") }; };

const VIEW = {
  board: () => ({ drive: nav("A", { kind: "board" }), ready: "!!document.querySelector('#bscroll [data-card], #bscroll .empty-b')" }),
  doc: (o) => ({ drive: nav("A", docLoc(o)), ready: "!!document.querySelector('#pA .md, #pA .derr')" }),
  search: (o) => ({ drive: nav("A", { kind: "search", q: o.q }), ready: "!!document.querySelector('#search .sfile, #search .qnone, #search .derr')" }),
  diff: (o) => ({ drive: nav("A", { kind: "diff", card: o.card }), ready: "!!document.querySelector('#diffv .dfile, #diffv .hint:not(:first-child), #diffv .derr') || (document.querySelector('#diffv .dbody') && !/读取中/.test(document.querySelector('#diffv .dbody').textContent))" }),
};
const MEASURE = `(() => { const r = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect();
  const cs = getComputedStyle(e); return cs.display === "none" || cs.visibility === "hidden" ? { display: "none" } : { x: Math.round(b.x), w: Math.round(b.width), h: Math.round(b.height) }; };
  return { nav: r("#nav"), centre: r("#centre"), side: r("#side"), pA: r("#pA"), pB: r("#pB"),
    pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth, inner: [innerWidth, innerHeight] }; })()`;

const rect = (sel) => `(() => { const e = document.querySelector(${J(sel)}); if (!e) return null; const r = e.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; })()`;
const has = (sel) => `!!document.querySelector(${J(sel)})`;

const SCENARIO = {
  // The page comes up on real data at every width class, the regime classes follow the viewport only,
  // and nothing overflows the page horizontally.
  async skeleton(ctx, check) {
    for (const [w, h, cls] of [[1440, 900, ""], [1024, 768, "mid"], [768, 1024, "narrow"], [390, 844, "phone"]]) {
      await ctx.viewport(w, h); await ctx.load(); await ctx.go("board");
      check(`${w}: real cards on the board`, await ctx.eval("document.querySelectorAll('#bscroll [data-card]').length > 0"));
      check(`${w}: the tree lists the projects`, await ctx.eval("document.querySelectorAll('#tree .tr.top.dir').length > 0"));
      if (cls) check(`${w}: .app.${cls}`, await ctx.eval(`document.getElementById('app').classList.contains(${J(cls)})`));
      check(`${w}: no horizontal page overflow`, await ctx.eval("document.documentElement.scrollWidth <= document.documentElement.clientWidth"));
      check(`${w}: the status bar names the board`, await ctx.eval("/看板/.test(document.getElementById('status').textContent)"));
    }
    check("390: the narrow default form is the table", await ctx.eval(has("#bscroll .tbl")));
  },
  // The two frontends share one origin: v2 reads and writes svd2-* only, and leaves the classic sv-* keys alone.
  async storage(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load();
    await ctx.eval("localStorage.setItem('sv-theme', 'dark'); localStorage.setItem('sv-board-mode', 'kanban'); location.reload(); true");
    await ctx.sleep(300); await ctx.wait(VIEW.board().ready);
    check("a classic sv-theme does not theme v2", await ctx.eval("!document.documentElement.hasAttribute('data-theme')"));
    await ctx.eval("V2.setTheme('amber'); true");
    await ctx.click('[data-form="cols"]'); await ctx.click('[data-grp="s"]'); await ctx.click("[data-trays]");
    await ctx.click("#bscroll [data-card]");
    check("the classic keys keep their values", await ctx.eval("localStorage.getItem('sv-theme') === 'dark' && localStorage.getItem('sv-board-mode') === 'kanban'"));
    check("every other key is svd2-*", await ctx.eval("Object.keys(localStorage).filter(k => !/^sv-(theme|board-mode)$/.test(k)).every(k => k.startsWith('svd2-'))"));
    check("v2 wrote its own keys", await ctx.eval("['svd2-theme','svd2-form','svd2-grp','svd2-trays','svd2-sel'].every(k => localStorage.getItem(k) !== null)"));
  },
  // Board: forms, grouping, the filter popover and its memory, trays that never move a card, the detail, arrows, the diff.
  async board(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    for (const f of ["cards", "cols", "table", "dots"]) {
      await ctx.click(`[data-form="${f}"]`);
      const sel = { cards: "#bscroll .grid .card", cols: "#bscroll .kcols .kcol", table: "#bscroll .tbl tr[data-card]", dots: "#bscroll .dot" }[f];
      check(`form ${f} renders`, await ctx.eval(has(sel)));
      if (f === "table") continue;
      const before = await ctx.eval(rect("#bscroll [data-card]"));
      await ctx.click("[data-trays]"); const after = await ctx.eval(rect("#bscroll [data-card]")); await ctx.click("[data-trays]");
      check(`form ${f}: toggling trays leaves the first card where it was (${J(before)} → ${J(after)})`, J(before) === J(after));
    }
    await ctx.click('[data-form="cards"]');
    await ctx.click('[data-grp="s"]');
    check("grouped by status: no card repeats its status word", await ctx.eval("[...document.querySelectorAll('#bscroll .card .w')].every(w => w.textContent === '')"));
    await ctx.click('[data-grp="p"]');
    await ctx.click("[data-flt]");
    check("the filter opens as a popover", await ctx.eval("document.getElementById('fltPop').classList.contains('on')"));
    await ctx.click('#fltPop [data-chip="active"]');
    check("hiding active: no active card left, the filter button stays pressed", await ctx.eval("!document.querySelector('#bscroll [data-st=active][data-card]') && document.querySelector('[data-flt]').classList.contains('on')"));
    check("the status bar says what is hidden", await ctx.eval("/隐藏了 active/.test(document.getElementById('status').textContent)"));
    await ctx.eval("location.reload(); true"); await ctx.sleep(300); await ctx.wait(VIEW.board().ready);
    check("the hidden set survives a reload", await ctx.eval("!document.querySelector('#bscroll [data-st=active][data-card]')"));
    await ctx.click("[data-flt]"); await ctx.click("#fltPop [data-fltall]");
    check("全部显示 restores every status", await ctx.eval(has("#bscroll [data-st=active][data-card]")));
    await ctx.key("Escape");
    await ctx.click("#bscroll .card[data-card]");
    check("a click selects the card and opens the detail", await ctx.eval("!!document.querySelector('#bscroll .card.sel') && !document.getElementById('app').classList.contains('dc') && !!document.querySelector('#bdet .hn')"));
    const first = await ctx.eval("document.querySelector('#bscroll .card.sel').dataset.card");
    await ctx.key("ArrowRight");
    check("→ moves the selection", await ctx.eval(`document.querySelector('#bscroll .card.sel').dataset.card !== ${J(first)}`));
    check("the detail lists the card's links", await ctx.eval(has("#bdet [data-diff]")));
    if (await ctx.eval("!!document.querySelector('meta[name=gitweb-url]').content")) {
      check("gitweb deep link carries the project", await ctx.eval("/\\?p=[^;]+;a=summary/.test(document.querySelector('#bdet .blinks a').getAttribute('href'))"));
    } else console.log("skip - board: gitweb deep link (this viewer runs without the companion)");
    await ctx.key("Escape");
    check("Esc closes the detail", await ctx.eval("document.getElementById('app').classList.contains('dc')"));
    await ctx.go("diff");
    check("the diff view renders for the card", await ctx.eval("!!document.querySelector('#diffv .dfile, #diffv .hint')"));
  },
  // Nav: the project scope narrows tree, board and search; folds a user opens survive a reload, a reveal
  // does not persist; sort and one-click collapse per section.
  async tree(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    const proj = await ctx.eval("document.querySelector('#scopeSel option:nth-child(2)').value");
    await ctx.eval(`(() => { const s = document.getElementById('scopeSel'); s.value = ${J(proj)}; s.dispatchEvent(new Event('change', { bubbles: true })); return true; })()`);
    check(`scope ${proj}: the tree shows only that project`, await ctx.eval(`[...document.querySelectorAll('#tree .tr.top.dir .nm')].every(n => n.textContent === ${J(proj)})`));
    check(`scope ${proj}: the board shows only its cards`, await ctx.eval(`[...document.querySelectorAll('#bscroll [data-card]')].every(c => c.dataset.card.startsWith(${J(proj + "/")}))`));
    await ctx.eval("(() => { const s = document.getElementById('scopeSel'); s.value = ''; s.dispatchEvent(new Event('change', { bubbles: true })); return true; })()");
    const key = await ctx.eval("document.querySelector('#tree .tr.top.dir').dataset.foldK");
    await ctx.click(`#tree [data-fold-k="${key}"]`);
    check("a click opens a project folder", await ctx.eval(`document.querySelector('#tree [data-fold-k="${key}"]').classList.contains('open')`));
    await ctx.eval("location.reload(); true"); await ctx.sleep(300); await ctx.wait("!!document.querySelector('#tree .tr.top.dir')");
    check("the user-opened fold survives a reload", await ctx.eval(`document.querySelector('#tree [data-fold-k="${key}"]').classList.contains('open')`));
    await ctx.eval(nav("A", docLoc(o))); await ctx.wait("!!document.querySelector('#pA .md, #pA .derr')");
    check("opening a doc reveals and marks it in the tree", await ctx.eval(has("#tree .tr.cur[data-open]")));
    const revealed = await ctx.eval("JSON.parse(localStorage.getItem('svd2-tree-open') || '[]')");
    check("the reveal is not written to the remembered folds", !revealed.some((k) => k.startsWith("dev:" + o.doc.slice(4).split("/").slice(0, 2).join("/"))));
    await ctx.click('[data-tcol="dev"]');
    check("F collapses the dev section's folders", await ctx.eval("JSON.parse(localStorage.getItem('svd2-tree-open')).every(k => !k.startsWith('dev:'))"));
    await ctx.click('[data-tcol="dev"]');
    check("F again restores them", await ctx.eval(`JSON.parse(localStorage.getItem('svd2-tree-open')).includes(${J(key)})`));
    await ctx.click('[data-tsort="kb"]');
    check("the KB section switches to modified-time sort", await ctx.eval("document.querySelector('[data-tsort=kb]').textContent === 'T' && JSON.parse(localStorage.getItem('svd2-tree-sort')).kb.key === 'mtime'"));
  },
  // Reader: links resolve, citations jump (a Fact opens its facts.md beside), hover previews, line numbers,
  // the reading width cycles per pane, the reading place comes back by content anchor, a 404 says so.
  async reader(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    check("markdown rendered with a TOC", await ctx.eval("document.querySelectorAll('#pA .md h2').length > 0 && document.querySelectorAll('#sbody .ti').length > 0"));
    check("source line numbers sit beside the blocks", await ctx.eval("document.querySelectorAll('#pA .lnum').length > 3"));
    const w0 = await ctx.eval("document.querySelector('#pA .md').getBoundingClientRect().width");
    await ctx.click('#pA [data-t="width"]');
    const w1 = await ctx.eval("document.querySelector('#pA .md').getBoundingClientRect().width");
    check(`the width button widens the measure (${w0} → ${w1})`, w1 > w0);
    for (let i = 0; i < 3 && !(await ctx.eval("/默认/.test(document.querySelector('#pA [data-t=width]').dataset.tip)")); i++) await ctx.click('#pA [data-t="width"]');
    check("…and comes back to the default after the cycle", Math.abs(await ctx.eval("document.querySelector('#pA .md').getBoundingClientRect().width") - w0) < 1);
    const cite = await ctx.eval("(() => { const c = document.querySelector('#pA .cite[data-ref^=Fact]'); return c ? c.dataset.ref : null; })()");
    if (cite) {
      await ctx.click(`#pA .cite[data-ref="${cite}"]`);
      await ctx.wait(`!!document.querySelector('#pB [data-xid="${cite}"]')`);
      check(`[${cite}] opens facts.md in pane B at its block`, await ctx.eval("document.getElementById('reader').classList.contains('split') && /facts\\.md$/.test(V2.P.B.loc.rel)"));
      await ctx.sleep(400);
      check("the connecting line is drawn", await ctx.eval("!!document.querySelector('#link path')"));
      await ctx.mouseMove(`#pA .cite[data-ref="${cite}"]`); await ctx.sleep(500);
      check("hovering a Fact citation previews it", await ctx.eval("document.getElementById('tip').classList.contains('on') && /Fact-/.test(document.getElementById('tip').textContent)"));
      await ctx.click('#pB [data-t="close"]');
    }
    const lk = await ctx.eval("(() => { const a = document.querySelector('#pA .md a[data-rel]'); return a ? a.dataset.rel : null; })()");
    if (lk) {
      await ctx.mouseMove("#pA .md a[data-rel]"); await ctx.sleep(700);
      check("hovering an internal link previews the target doc", await ctx.eval("document.getElementById('tip').classList.contains('wide')"));
    }
    await ctx.eval("V2.P.A.body.scrollTop = V2.P.A.body.scrollHeight / 2; true"); await ctx.sleep(600);
    const mid = await ctx.eval("V2.P.A.body.scrollTop");
    await ctx.go("board"); await ctx.go("doc");
    check(`coming back restores the reading place (${mid} → ${await ctx.eval("V2.P.A.body.scrollTop")})`, Math.abs(await ctx.eval("V2.P.A.body.scrollTop") - mid) < 60);
    await ctx.eval(nav("A", { kind: "doc", tree: "dev", rel: "no/such/file.md" })); await ctx.wait(has("#pA .derr"));
    check("a missing file says so", await ctx.eval("/不存在/.test(document.querySelector('#pA .derr').textContent)"));
  },
  // Search: ⌘K matches docs, cards and Facts, ⌘↵ hands the query to full-text search, a hit opens at its line.
  async search(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    await ctx.key("k", 4);
    check("⌘K opens quick open", await ctx.eval("!document.getElementById('qo').hidden"));
    check("an empty query lists the board and recent docs", await ctx.eval("/看板/.test(document.getElementById('qList').textContent) && document.querySelectorAll('#qList .qr').length > 5"));
    await ctx.sleep(100); await ctx.type(o.card.split("/")[1]); await ctx.sleep(300);
    check("the box has the focus and the typed query", await ctx.eval(`document.activeElement.id === 'qIn' && document.getElementById('qIn').value === ${J(o.card.split("/")[1])}`));
    check(`typing ${o.card.split("/")[1]} offers the card`, await ctx.eval(`[...document.querySelectorAll('#qList .qr')].some(r => r.textContent.includes(${J(o.card.split("/")[1])}))`));
    await ctx.key("Enter", 4); await ctx.wait(VIEW.search(o).ready.replace(/#search/g, "#search"));
    check("⌘↵ runs the full-text search", await ctx.eval("V2.view === 'search' && JSON.parse(localStorage.getItem('svd2-recent-search'))[0] === " + J(o.card.split("/")[1])));
    await ctx.go("search");
    check("results are grouped by file", await ctx.eval(has("#search .sfile")));
    const line = await ctx.eval("(() => { const h = document.querySelector('#search .shit[data-line]:not([data-line=\"0\"])'); return h ? +h.dataset.line : 0; })()");
    if (line) { await ctx.click('#search .shit[data-line]:not([data-line="0"])'); await ctx.wait(has("#pA .md"));
      check(`a hit opens its doc scrolled to line ${line}`, await ctx.eval("V2.P.A.body.scrollTop > 0 || V2.P.A.body.scrollHeight <= V2.P.A.body.clientHeight")); }
    await ctx.go("board"); await ctx.key("/");
    check("/ opens the search view with the box focused", await ctx.eval("V2.view === 'search' && document.activeElement.id === 'sIn'"));
  },
  // Find: highlights per pane without touching the DOM, Enter flushes the pending term, Esc closes only the
  // find bar, pins survive closing and come back with the doc, history walks with ↑.
  async find(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    const html0 = await ctx.eval("document.querySelector('#pA .md').innerHTML.length");
    const term = await ctx.eval("document.querySelector('#pA .md h2').textContent.replace(/^#/, '').trim().slice(0, 2)");
    await ctx.key("f");
    check("f opens the find bar focused", await ctx.eval("document.activeElement.matches('#pA .find input')"));
    await ctx.type(term); await ctx.key("Enter");
    check("Enter right after typing acts on the typed term", await ctx.eval("CSS.highlights.has('hit-A') && /^\\d+\\/\\d+$/.test(document.querySelector('#pA .odo').textContent.replace(/\\s/g, ''))"));
    check("highlights never rewrite the doc", await ctx.eval(`document.querySelector('#pA .md').innerHTML.length === ${html0}`));
    check("the rail shows the hits", await ctx.eval("document.querySelectorAll('#pA .frail i').length > 0"));
    await ctx.key("Enter", 4);
    check("⌘↵ pins the term", await ctx.eval("CSS.highlights.has('p0-A') && document.querySelectorAll('#pA .fpin').length === 1"));
    await ctx.key("Escape");
    check("Esc closes the find bar and keeps the pin", await ctx.eval("!document.querySelector('#pA .find').classList.contains('on') && CSS.highlights.has('p0-A') && !CSS.highlights.has('hit-A')"));
    await ctx.go("board"); await ctx.go("doc");
    check("the pin comes back with the doc", await ctx.eval("CSS.highlights.has('p0-A')"));
    await ctx.key("f"); await ctx.key("ArrowUp");
    check("↑ in the box recalls the last find term", await ctx.eval("document.querySelector('#pA .find input').value === " + J(term.toLowerCase()) + ""));
    await ctx.key("Escape"); await ctx.key("H");
    check("⇧H clears this pane's pins", await ctx.eval("!CSS.highlights.has('p0-A')"));
  },
  // Two panes: ⇧ opens beside, each pane keeps its own back and forward, the focus decides which one moves.
  async panes(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    const other = await ctx.eval(`(() => { const r = ${J(o.doc.slice(4))}, d = r.replace(/[^/]+$/, ''); return V2.D.tree.dev.map(x => x.path).find(p => p.startsWith(d) && p !== r && p.endsWith('.md')); })()`);
    await ctx.eval(`V2.openDoc("dev", ${J(other)}, { shiftKey: true }); true`); await ctx.wait(has("#pB .md"));
    check("⇧-open lands in pane B", await ctx.eval(`V2.isSplit() && V2.P.B.loc.rel === ${J(other)}`));
    await ctx.eval(`V2.nav("B", { kind: "doc", tree: "dev", rel: ${J(o.doc.slice(4))} }); true`); await ctx.sleep(500);
    await ctx.eval("V2.setFocus('A'); true");
    check("A's back stack does not hold B's visit", await ctx.eval("V2.P.A.hist.every(l => l.kind !== 'doc' || l.rel !== " + J(other) + ")"));
    await ctx.eval("V2.setFocus('B'); true"); await ctx.key("[");
    check("[ with B focused steps B back", await ctx.eval(`V2.P.B.loc.rel === ${J(other)}`));
    await ctx.key("]");
    check("] steps it forward again", await ctx.eval(`V2.P.B.loc.rel === ${J(o.doc.slice(4))}`));
    await ctx.click('#pA [data-t="hist"]'); await ctx.wait("!!document.querySelector('#histPop .hi, #histPop .qnone:not(:first-child)') || /没有记录/.test(document.getElementById('histPop').textContent)");
    const sha = await ctx.eval("(() => { const b = document.querySelector('#histPop [data-chg]:not([data-chg=\"\"])'); return b ? b.dataset.chg : null; })()");
    if (sha) { await ctx.click(`#histPop [data-chg="${sha}"]`); await ctx.wait("!document.querySelector('#pA .chgbar').hidden");
      check("a commit opens the change view with its marks", await ctx.eval("/变更/.test(document.querySelector('#pA .chgbar').textContent)"));
      await ctx.click('#pA .chgbar [data-chg=""]'); await ctx.sleep(500);
      check("…and exits back to the current version", await ctx.eval("document.querySelector('#pA .chgbar').hidden")); }
  },
  // Live refresh: a touched doc gets a notice, not a swap; the board refreshes in place keeping its state.
  async refresh(ctx, check, o) {
    if (!o.touch) throw new Error("refresh needs --touch <a file under the dev root>; pass the doc under test");
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    await ctx.click('[data-form="cols"]'); await ctx.click("[data-trays]");
    await ctx.eval("document.querySelector('#bscroll').scrollTop = 120; const k = document.querySelector('.kcols'); if (k) k.scrollLeft = 80; true");
    await ctx.eval("document.querySelector('#tree [data-fold-k]').click(); document.getElementById('tree').scrollTop = 40; true");
    await ctx.click("#bscroll [data-card]");
    const st0 = await ctx.eval("JSON.stringify([document.querySelector('#bscroll').scrollTop, (document.querySelector('.kcols') || {}).scrollLeft, document.querySelector('#bscroll .sel').dataset.card])");
    ctx.touchFile(o.touch); await ctx.sleep(6000);
    const st1 = await ctx.eval("JSON.stringify([document.querySelector('#bscroll').scrollTop, (document.querySelector('.kcols') || {}).scrollLeft, (document.querySelector('#bscroll .sel') || {}).dataset?.card])");
    check(`board after a refresh keeps scroll and selection (${st0} → ${st1})`, st0 === st1);
    check("…and the form and trays", await ctx.eval("!!document.querySelector('.kcols') && document.getElementById('app').classList.contains('notray')"));
    check("…and the tree keeps its own scroll (not pulled to the current doc)", await ctx.eval("document.getElementById('tree').scrollTop === 40 || document.getElementById('tree').scrollHeight <= document.getElementById('tree').clientHeight + 40"));
    await ctx.eval(nav("A", { kind: "doc", tree: "dev", rel: o.touch.split("/dev-workflow/")[1] || o.doc.slice(4) })); await ctx.wait(has("#pA .md"));
    const term = await ctx.eval("document.querySelector('#pA .md h2').textContent.replace(/^#/, '').trim().slice(0, 2)");
    await ctx.key("f"); await ctx.type(term); await ctx.key("Enter", 4); await ctx.key("Escape");
    await ctx.eval("V2.P.A.body.scrollTop = 200; true"); await ctx.sleep(300);
    ctx.touchFile(o.touch); await ctx.sleep(4000);
    check("a changed doc shows the notice and does not swap itself", await ctx.eval("document.querySelector('#pA .stale').classList.contains('on') && Math.abs(V2.P.A.body.scrollTop - 200) < 2"));
    await ctx.click("#pA [data-stale]"); await ctx.sleep(800);
    check("…and the pinned term survives the refresh", await ctx.eval("CSS.highlights.has('p0-A')"));
    check("refreshing from the notice keeps the place", await ctx.eval("!document.querySelector('#pA .stale').classList.contains('on') && Math.abs(V2.P.A.body.scrollTop - 200) < 40"));
  },
  // Keys: Esc closes one layer per press, top first; a single-key hotkey never fires with a modifier.
  async keys(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    await ctx.key("f"); await ctx.eval("document.activeElement.blur(); true");
    await ctx.click("#themeBtn");
    await ctx.key("k", 4); await ctx.sleep(100);
    check("three layers open: find bar, theme popover, quick open", await ctx.eval("document.querySelector('#pA .find.on') && !document.getElementById('qo').hidden") === true || await ctx.eval("!!document.querySelector('#pA .find.on') && !document.getElementById('qo').hidden"));
    await ctx.key("Escape");
    check("Esc 1 closes quick open only", await ctx.eval("document.getElementById('qo').hidden && !!document.querySelector('#pA .find.on')"));
    await ctx.key("Escape");
    check("Esc 2 closes the popover, the find bar stays", await ctx.eval("!document.getElementById('themePop').classList.contains('on') && !!document.querySelector('#pA .find.on')"));
    await ctx.key("Escape");
    check("Esc 3 closes the find bar", await ctx.eval("!document.querySelector('#pA .find.on')"));
    await ctx.key("b", 1); await ctx.key("b", 4);
    check("⌥b / ⌘b do not jump to the board", await ctx.eval("V2.view === 'doc'"));
    await ctx.key("f", 4);
    check("⌘f is left to the browser", await ctx.eval("!document.querySelector('#pA .find.on')"));
    await ctx.key("b");
    check("b alone goes to the board", await ctx.eval("V2.view === 'board'"));
  },
  // Narrow (<900): the left strip can go away entirely; the head's ☰ then opens the full nav as a drawer.
  async narrow(ctx, check) {
    await ctx.viewport(768, 1024); await ctx.load(); await ctx.go("doc");
    check("768: nav is a strip, no ☰ in the head yet", await ctx.eval("document.getElementById('nav').getBoundingClientRect().width === 34 && getComputedStyle(document.querySelector('#pA .navb')).display === 'none'"));
    await ctx.click("#navTog");
    check("collapsing removes the strip and shows ☰", await ctx.eval("document.getElementById('app').classList.contains('nx') && getComputedStyle(document.querySelector('#pA .navb')).display !== 'none'"));
    const w0 = await ctx.eval("Math.round(document.getElementById('centre').getBoundingClientRect().width)");
    await ctx.click("#pA [data-navb]");
    check("☰ opens the drawer with the tree", await ctx.eval("document.getElementById('app').classList.contains('navpop') && document.querySelectorAll('#tree .tr').length > 0"));
    check(`the drawer does not move the other columns (${w0})`, w0 === await ctx.eval("Math.round(document.getElementById('centre').getBoundingClientRect().width)"));
    await ctx.click("#tree [data-goboard]");
    check("picking in the drawer closes it", await ctx.eval("!document.getElementById('app').classList.contains('navpop') && V2.view === 'board'"));
    await ctx.eval("location.reload(); true"); await ctx.sleep(300); await ctx.wait(VIEW.board().ready);
    check("the choice is remembered", await ctx.eval("document.getElementById('app').classList.contains('nx')"));
    await ctx.wait(has("#scopeSel"));
    check("768: inputs are 16px (no iOS zoom)", await ctx.eval("parseFloat(getComputedStyle(document.getElementById('scopeSel')).fontSize) >= 16"));
    await ctx.key("k", 4); await ctx.sleep(100);
    check("768: the quick-open box is 16px too", await ctx.eval("parseFloat(getComputedStyle(document.getElementById('qIn')).fontSize) >= 16"));
    await ctx.key("Escape");
  },
  // Themes: 骨白/深空 select with a tone step, 琥珀 with the classic outline; neither leaks into the other.
  async themes(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    await ctx.click('[data-form="cards"]'); await ctx.click("#bscroll .card[data-card]");
    const sty = "(() => { const c = getComputedStyle(document.querySelector('#bscroll .card.sel')); return [c.outlineStyle, c.borderTopLeftRadius]; })()";
    for (const [t, outline, square] of [["light", false, false], ["dark", false, false], ["amber", true, true], ["amber-dark", true, true]]) {
      await ctx.eval(`V2.setTheme(${J(t)}); true`); await ctx.sleep(100);
      const [o, r] = await ctx.eval(sty);
      check(`${t}: selected card ${outline ? "outlined" : "toned, no outline"}, ${square ? "square" : "rounded"} corners`, (o !== "none") === outline && (r === "0px") === square);
    }
  },
  // The mockup's details (Req-8) and the board's spacing rules (Req-4), each of which would go unnoticed if it vanished.
  async details(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    await ctx.click('[data-form="cards"]'); await ctx.click('[data-grp="p"]');
    const gaps = await ctx.eval(`(() => { const b = document.getElementById('bscroll').getBoundingClientRect(), t = [...document.querySelectorAll('#bscroll .proj')].map(x => x.getBoundingClientRect());
      return [Math.round(t[0].top - b.top), Math.round(t[0].left - b.left), Math.round(b.right - t[0].right - (document.getElementById('bscroll').offsetWidth - document.getElementById('bscroll').clientWidth)), t[1] ? Math.round(t[1].top - t[0].bottom) : 16]; })()`);
    check(`trays on: head gap = side gaps, trays 16px apart (${J(gaps)})`, Math.abs(gaps[0] - gaps[1]) <= 1 && Math.abs(gaps[1] - gaps[2]) <= 1 && gaps[3] === 16);
    await ctx.click("#bscroll .card[data-card]");
    check("the detail's status word wears the status colour", await ctx.eval("getComputedStyle(document.querySelector('#bdet .hst')).color !== getComputedStyle(document.querySelector('#bdet .hm')).color"));
    check("trays on: the selected card stands out from its neighbours", await ctx.eval("(() => { const s = getComputedStyle(document.querySelector('#bscroll .card.sel')), n = getComputedStyle(document.querySelector('#bscroll .card:not(.sel)')); return s.backgroundColor !== n.backgroundColor || s.borderColor !== n.borderColor; })()"));
    const lite = await ctx.eval("!!document.querySelector('#bdet [data-rq]')");
    if (lite) { await ctx.click("#bdet [data-rq]"); check("a Req line in the detail unfolds on click", await ctx.eval("document.querySelector('#bdet [data-rq]').classList.contains('x')")); }
    await ctx.click('[data-form="cols"]'); await ctx.key("ArrowRight"); const c1 = await ctx.eval("document.querySelector('#bscroll .sel').dataset.card");
    await ctx.key("ArrowLeft");
    check("columns: ← moves back across lanes", await ctx.eval(`document.querySelector('#bscroll .sel').dataset.card !== ${J(c1)}`));
    await ctx.eval("document.querySelector('#bscroll .sel').focus(); true"); await ctx.click("[data-trays]");
    await ctx.eval("document.querySelector('[data-trays]').focus(); true"); await ctx.key("Enter");
    check("Enter on a focused control does that control, not 'open the selected card'", await ctx.eval("V2.view === 'board'"));
    // tree: closed folder, relative times, stars and the trail
    await ctx.go("doc");
    check("tree: a closed (n) group and relative times on files", await ctx.eval("[...document.querySelectorAll('#tree .tr.grp .nm')].some(n => /^closed \\(\\d+\\)$/.test(n.textContent)) && [...document.querySelectorAll('#tree .tr[data-open] em')].some(e => /^(now|\\d+[mhd])$/.test(e.textContent))"));
    await ctx.key("s");
    await ctx.click("#starBtn");
    check("s stars the doc; the star popover lists it", await ctx.eval("document.getElementById('starPop').classList.contains('on') && document.querySelectorAll('#starPop .sta').length > 0"));
    await ctx.click("#starPop [data-unstar]"); await ctx.click("#trailBtn");
    check("the trail popover lists the doc just read", await ctx.eval("document.getElementById('trailPop').classList.contains('on') && document.querySelectorAll('#trailPop [data-open]').length > 0"));
    await ctx.key("Escape");
    // reader: current line, TOC rail ticks, the selection bar, status-bar tips
    await ctx.click("#pA .md p"); check("a click marks the current line", await ctx.eval("!!document.querySelector('#pA .curline')"));
    await ctx.click('[data-col="side"]');
    check("collapsed TOC shows its ticks", await ctx.eval("document.querySelectorAll('#sticks .stk').length > 0 && getComputedStyle(document.getElementById('srail')).display !== 'none'"));
    await ctx.click('#srail [data-col="side"]');
    await ctx.eval("(() => { const p = document.querySelector('#pA .md p'), r = document.createRange(); r.selectNodeContents(p.firstChild || p); const s = getSelection(); s.removeAllRanges(); s.addRange(r); p.dispatchEvent(new MouseEvent('mouseup', { bubbles: true })); return true; })()");
    await ctx.sleep(100);
    check("selecting text shows the selection bar", await ctx.eval("document.getElementById('selbar').classList.contains('on')"));
    await ctx.mouseMove('#pA [data-t="hist"]');
    check("hovering a control says what it does in the status bar", await ctx.eval("/变更历史/.test(document.getElementById('status').textContent)"));
    // quick open's Fact candidates
    await ctx.key("k", 4); await ctx.sleep(100); await ctx.type("Fact-1"); await ctx.sleep(1500);
    check("⌘K offers Fact blocks", await ctx.eval("[...document.querySelectorAll('#qList .qg')].some(g => g.textContent.startsWith('Fact'))"));
    await ctx.key("Escape");
    // a remembered find term does not pull the page away from where the reader lands
    await ctx.key("f"); await ctx.type("的"); await ctx.sleep(300); await ctx.go("board");
    await ctx.eval("V2.nav('A', " + J({ ...docLoc(o), xid: "Req-1" }) + "); true"); await ctx.sleep(1200);
    const y = await ctx.eval("(() => { const el = document.querySelector('#pA [data-xid=\"Req-1\"]'); return el ? Math.round(el.getBoundingClientRect().top - V2.P.A.body.getBoundingClientRect().top) : null; })()");
    if (y != null) check(`with a remembered find term, an id jump still lands on its target (${y}px from the top)`, Math.abs(y - 16) < 40);
  },
  // Regressions from the hands-on walk (2026-10-04): each was a real defect found by clicking through as a user.
  async walk(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    await ctx.eval("V2.W.wn = 320; V2.applyW(); true"); await ctx.click("#navTog");
    check("a dragged nav width does not stop the collapse (34px strip)", await ctx.eval("document.getElementById('nav').getBoundingClientRect().width === 34"));
    await ctx.click("#navTog");
    await ctx.eval("V2.W.ws = 320; V2.applyW(); true"); await ctx.go("doc"); await ctx.click("#sideTog");
    check("…nor the side collapse", await ctx.eval("document.getElementById('side').getBoundingClientRect().width === 34"));
    await ctx.click("#sideOpen"); await ctx.go("board");
    await ctx.eval("(() => { const c = document.querySelector('#bscroll .card[data-card]'); c.dispatchEvent(new MouseEvent('click', { bubbles: true, shiftKey: true, detail: 1 })); return true; })()");
    await ctx.wait(has("#pA .md"));
    check("⇧-click on the board opens the card in A (nothing to sit beside)", await ctx.eval("V2.view === 'doc' && !V2.isSplit() && V2.P.A.loc.kind === 'doc'"));
    await ctx.key("k", 4); await ctx.sleep(100); await ctx.type("Fact-1"); await ctx.sleep(4000);
    const got = await ctx.eval("new Set(performance.getEntriesByType('resource').filter(e => /\\/facts\\.md$/.test(e.name) && e.responseStatus === 200).map(e => e.name)).size");
    const all = await ctx.eval("V2.D.tree.dev.filter(x => /^[^/]+\\/\\d{3}-[^/]+\\/facts\\.md$/.test(x.path)).length");
    check(`quick open loads every card's facts.md, none dropped (${got}/${all})`, got === all);
    await ctx.key("Escape");
    await ctx.viewport(768, 1024); await ctx.go("doc"); await ctx.sleep(300);
    const cite = await ctx.eval("(() => { const c = document.querySelector('#pA .cite[data-ref^=Fact]'); return c ? c.dataset.ref : null; })()");
    if (cite) {
      await ctx.click(`#pA .cite[data-ref="${cite}"]`); await ctx.wait(`!!document.querySelector('#pB [data-xid="${cite}"]')`); await ctx.sleep(200);
      check("narrow: a citation opens in the other pane, which takes the screen", await ctx.eval("V2.focus === 'B' && getComputedStyle(document.getElementById('pA')).display === 'none'"));
      await ctx.click('#pB .abw [data-ab="A"]');
      check("narrow: the A/B switch shows A and hides B", await ctx.eval("getComputedStyle(document.getElementById('pB')).display === 'none' && getComputedStyle(document.getElementById('pA')).display !== 'none'"));
    }
  },
  // The human's 2026-10-05 review of the live page, one check per point.
  async walk2(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    const proj = o.doc.split("/")[1];
    check("splitting opens an empty B, not a guessed file", await (async () => { await ctx.click('#pA [data-t="split"]'); await ctx.sleep(300); return ctx.eval("V2.isSplit() && !V2.P.B.loc && document.getElementById('pB').classList.contains('blank')"); })());
    const other = await ctx.eval(`V2.D.tree.dev.map(x => x.path).find(p => p.startsWith(${J(o.doc.slice(4).replace(/[^/]+$/, ""))}) && p !== ${J(o.doc.slice(4))} && p.endsWith('.md'))`);
    await ctx.eval(`V2.nav("B", { kind: "doc", tree: "dev", rel: ${J(other)} }); true`); await ctx.wait(has("#pB .md"));
    check("the tree marks only the focused pane's doc (B)", await ctx.eval(`(() => { const c = [...document.querySelectorAll('#tree .tr.cur[data-open]')]; return c.length === 1 && c[0].dataset.open === ${J("dev:" + other)}; })()`));
    await ctx.eval("V2.setFocus('A'); true");
    check("…and follows the focus to A", await ctx.eval(`(() => { const c = [...document.querySelectorAll('#tree .tr.cur[data-open]')]; return c.length === 1 && c[0].dataset.open === ${J("dev:" + o.doc.slice(4))}; })()`));
    const third = await ctx.eval(`V2.D.tree.dev.map(x => x.path).find(p => p.startsWith(${J(o.doc.slice(4).replace(/[^/]+$/, ""))}) && !p.slice(${o.doc.slice(4).replace(/[^/]+$/, "").length}).includes('/') && ![${J(o.doc.slice(4))}, ${J(other)}].includes(p) && p.endsWith('.md'))`);
    if (third) {
      await ctx.eval("V2.setFocus('B'); true"); await ctx.click(`#tree [data-open="dev:${third}"]`); await ctx.wait(`V2.P.B.loc.rel === ${J(third)}`);
      check("with B focused, a tree pick opens in B and leaves A alone", await ctx.eval(`V2.P.A.loc.rel === ${J(o.doc.slice(4))} && V2.focus === 'B'`));
      await ctx.eval(`(() => { document.querySelector('#tree [data-open="dev:${other}"]').dispatchEvent(new MouseEvent('click', { bubbles: true, shiftKey: true })); return true; })()`);
      await ctx.wait(`V2.P.A.loc.rel === ${J(other)}`);
      check("…and ⇧ sends it to the other pane (A)", await ctx.eval(`V2.P.B.loc.rel === ${J(third)}`));
      await ctx.eval(`V2.nav("A", { kind: "doc", tree: "dev", rel: ${J(o.doc.slice(4))} }); V2.setFocus('A'); true`); await ctx.sleep(400);
    }
    await ctx.click(`#tree [data-fold-k="dev:${proj}"]`);
    check("the project holding the open doc folds when clicked", await ctx.eval(`!document.querySelector('#tree [data-fold-k="dev:${proj}"]').classList.contains('open')`));
    await ctx.click(`#tree [data-fold-k="dev:${proj}"]`);
    check("folders show a relative time", await ctx.eval("[...document.querySelectorAll('#tree .tr.dir')].every(r => /^(now|\\d+[mhd])$/.test((r.querySelector('em') || {}).textContent || ''))"));
    check("closed (n) is the project's last entry", await ctx.eval(`(() => { const rows = [...document.querySelectorAll('#tree .tr')], at = rows.findIndex(r => r.dataset.foldK === ${J("dev:" + proj)});
      const end = rows.findIndex((r, i) => i > at && r.style.getPropertyValue('--d') === '0'), top = rows.slice(at + 1, end < 0 ? rows.length : end).filter(r => r.style.getPropertyValue('--d') === '1');
      return !top.some(r => /^closed/.test(r.textContent)) || /^closed \\(/.test(top[top.length - 1].querySelector('.nm').textContent); })()`));
    check("no horizontal scroll in either pane", await ctx.eval("['A','B'].every(k => V2.P[k].body.scrollWidth <= V2.P[k].body.clientWidth)"));
    await ctx.viewport(768, 1024); await ctx.sleep(300); await ctx.eval("V2.setFocus('B'); true"); await ctx.sleep(300);
    check("narrow: the pane that comes into view gets its line numbers", await ctx.eval("(() => { const t = [...document.querySelectorAll('#pB .lnum')].map(x => parseFloat(x.style.top)); return t.length > 2 && new Set(t).size === t.length; })()"));
  },
  // Collapsing a section under a project scope leaves the other projects' remembered folds alone.
  async foldscope(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    const [p1, p2] = await ctx.eval("[...document.querySelectorAll('#scopeSel option')].slice(1, 3).map(o => o.value)");
    await ctx.click(`#tree [data-fold-k="dev:${p1}"]`);
    await ctx.eval(`(() => { const s = document.getElementById('scopeSel'); s.value = ${J(p2)}; s.dispatchEvent(new Event('change', { bubbles: true })); return true; })()`);
    await ctx.click('[data-tcol="dev"]');
    check(`F under scope ${p2} keeps ${p1}'s remembered fold`, await ctx.eval(`JSON.parse(localStorage.getItem('svd2-tree-open')).includes(${J("dev:" + p1)})`));
  },
};

export default { VIEW, MEASURE, SCENARIO, views: "board,doc,search,diff",
  ready: "!!document.querySelector('#tree .tr.top') && !!document.querySelector('#bscroll [data-card], #bscroll .empty-b')", mask: ".phd, .find, .chgbar, .stale" };
