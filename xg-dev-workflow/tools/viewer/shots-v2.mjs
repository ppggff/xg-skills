// shots-v2.mjs — the main frontend's (/, alias /v2) half of the screenshot harness: how to drive each view,
// what to measure, and its behavioural scenarios. Loaded by shots.mjs unless --url ends in /v1; the page
// exposes its namespace as window.V2, so views are driven through V2.nav, the same call a click makes.
//   node tools/viewer/shots.mjs --url http://127.0.0.1:18790/ --scenario skeleton,storage,board
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
    await ctx.eval("V2.setForm('cols'); true"); await ctx.eval("V2.setGroup('s'); true"); await ctx.click("[data-trays]");
    await ctx.click("#bscroll [data-card]");
    check("the classic keys keep their values", await ctx.eval("localStorage.getItem('sv-theme') === 'dark' && localStorage.getItem('sv-board-mode') === 'kanban'"));
    check("every other key is svd2-*", await ctx.eval("Object.keys(localStorage).filter(k => !/^sv-(theme|board-mode)$/.test(k)).every(k => k.startsWith('svd2-'))"));
    check("v2 wrote its own keys", await ctx.eval("['svd2-theme','svd2-form','svd2-grp','svd2-trays','svd2-sel'].every(k => localStorage.getItem(k) !== null)"));
  },
  // Board: forms, grouping, the filter popover and its memory, trays that never move a card, the detail, arrows, the diff.
  async board(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    for (const f of ["cards", "cols", "table", "dots"]) {
      await ctx.eval(`V2.setForm(${J(f)}); true`);
      const sel = { cards: "#bscroll .grid .card", cols: "#bscroll .kcols .kcol", table: "#bscroll .tbl tr[data-card]", dots: "#bscroll .dot" }[f];
      check(`form ${f} renders`, await ctx.eval(has(sel)));
      if (f === "table") continue;
      const before = await ctx.eval(rect("#bscroll [data-card]"));
      await ctx.click("[data-trays]"); const after = await ctx.eval(rect("#bscroll [data-card]")); await ctx.click("[data-trays]");
      check(`form ${f}: toggling trays leaves the first card where it was (${J(before)} → ${J(after)})`, J(before) === J(after));
    }
    await ctx.eval("V2.setForm('cards'); true");
    await ctx.eval("V2.setGroup('s'); true");
    check("grouped by status: no card repeats its status word", await ctx.eval("[...document.querySelectorAll('#bscroll .card .w')].every(w => w.textContent === '')"));
    await ctx.eval("V2.setGroup('p'); true");
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
  // Nav: folds a user opens survive a reload, a reveal does not persist; sort and one-click collapse per section.
  async tree(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
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
    await ctx.eval("V2.setForm('cols'); true"); await ctx.click("[data-trays]");
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
    check("two layers open: find bar and theme popover", await ctx.eval("!!document.querySelector('#pA .find.on') && document.getElementById('themePop').classList.contains('on')"));
    await ctx.key("Escape");
    check("Esc 1 closes the popover, the find bar stays", await ctx.eval("!document.getElementById('themePop').classList.contains('on') && !!document.querySelector('#pA .find.on')"));
    await ctx.click("#themeBtn"); await ctx.key("k", 4); await ctx.sleep(100);
    check("quick open replaces the popover over the find bar", await ctx.eval("!document.getElementById('qo').hidden && !document.getElementById('themePop').classList.contains('on')"));
    await ctx.key("Escape");
    check("Esc 2 closes quick open only", await ctx.eval("document.getElementById('qo').hidden && !!document.querySelector('#pA .find.on')"));
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
    check("768: inputs are 16px (no iOS zoom)", await ctx.eval("(() => { const i = document.getElementById('app').appendChild(document.createElement('input')), f = parseFloat(getComputedStyle(i).fontSize); i.remove(); return f >= 16; })()"));
    await ctx.key("k", 4); await ctx.sleep(100);
    check("768: the quick-open box is 16px too", await ctx.eval("parseFloat(getComputedStyle(document.getElementById('qIn')).fontSize) >= 16"));
    await ctx.key("Escape");
  },
  // Themes: 骨白/深空 select with a tone step, 琥珀 with the classic outline; neither leaks into the other.
  async themes(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    await ctx.eval("V2.setForm('cards'); true"); await ctx.click("#bscroll .card[data-card]");
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
    await ctx.eval("V2.setForm('cards'); true"); await ctx.eval("V2.setGroup('p'); true");
    const gaps = await ctx.eval(`(() => { const b = document.getElementById('bscroll').getBoundingClientRect(), t = [...document.querySelectorAll('#bscroll .proj')].map(x => x.getBoundingClientRect());
      return [Math.round(t[0].top - b.top), Math.round(t[0].left - b.left), Math.round(b.right - t[0].right - (document.getElementById('bscroll').offsetWidth - document.getElementById('bscroll').clientWidth)), t[1] ? Math.round(t[1].top - t[0].bottom) : 16]; })()`);
    check(`trays on: head gap = side gaps, trays 16px apart (${J(gaps)})`, Math.abs(gaps[0] - gaps[1]) <= 1 && Math.abs(gaps[1] - gaps[2]) <= 1 && gaps[3] === 16);
    await ctx.click("#bscroll .card[data-card]");
    check("the detail's status word wears the status colour", await ctx.eval("getComputedStyle(document.querySelector('#bdet .hst')).color !== getComputedStyle(document.querySelector('#bdet .hm')).color"));
    check("trays on: the selected card stands out from its neighbours", await ctx.eval("(() => { const s = getComputedStyle(document.querySelector('#bscroll .card.sel')), n = getComputedStyle(document.querySelector('#bscroll .card:not(.sel)')); return s.backgroundColor !== n.backgroundColor || s.borderColor !== n.borderColor; })()"));
    const lite = await ctx.eval("!!document.querySelector('#bdet [data-rq]')");
    if (lite) { await ctx.click("#bdet [data-rq]"); check("a Req line in the detail unfolds on click", await ctx.eval("document.querySelector('#bdet [data-rq]').classList.contains('x')")); }
    await ctx.eval("V2.setForm('cols'); true"); await ctx.key("ArrowRight"); const c1 = await ctx.eval("document.querySelector('#bscroll .sel').dataset.card");
    await ctx.key("ArrowLeft");
    check("columns: ← moves back across lanes", await ctx.eval(`document.querySelector('#bscroll .sel').dataset.card !== ${J(c1)}`));
    await ctx.eval("document.querySelector('#bscroll .sel').focus(); true"); await ctx.click("[data-trays]");
    await ctx.eval("document.querySelector('[data-trays]').focus(); true"); await ctx.key("Enter");
    check("Enter on a focused control does that control, not 'open the selected card'", await ctx.eval("V2.view === 'board'"));
    // tree: closed folder, relative times, stars and the trail
    await ctx.go("doc");
    check("tree: a closed (n) group, and no times under the name sort", await ctx.eval("[...document.querySelectorAll('#tree .tr.grp .nm')].some(n => /^closed \\(\\d+\\)$/.test(n.textContent)) && ![...document.querySelectorAll('#tree .tr[data-open] em')].some(e => /^(now|\\d+[mhd])$/.test(e.textContent))"));
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
    await ctx.wait(has("#pB .md"));
    check("⇧-click on the board opens the card in B, beside the board", await ctx.eval("V2.kindOf('A') === 'board' && V2.isSplit() && V2.P.B.loc.kind === 'doc'"));
    await ctx.key("k", 4); await ctx.sleep(100); await ctx.type("Fact-1"); await ctx.sleep(4000);
    const got = await ctx.eval("new Set(performance.getEntriesByType('resource').filter(e => /\\/facts\\.md$/.test(e.name) && e.responseStatus === 200).map(e => e.name)).size");
    const all = await ctx.eval("V2.D.tree.dev.filter(x => /^[^/]+\\/\\d{3}-[^/]+\\/facts\\.md$/.test(x.path)).length");
    check(`quick open loads every card's facts.md, none dropped (${got}/${all})`, got === all);
    await ctx.key("Escape");
    await ctx.viewport(768, 1024); await ctx.go("doc"); await ctx.sleep(300);
    const cite = await ctx.eval("(() => { const c = document.querySelector('#pA .cite[data-ref^=Fact]'); return c ? c.dataset.ref : null; })()");
    if (cite) {
      await ctx.click(`#pA .cite[data-ref="${cite}"]`); await ctx.wait(`!!document.querySelector('#pA [data-xid="${cite}"]')`); await ctx.sleep(200);
      check("narrow: a citation opens its definition in the one pane, no split", await ctx.eval("V2.focus === 'A' && !V2.isSplit() && /facts\\.md$/.test(V2.P.A.loc.rel)"));
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
    await ctx.click('[data-tsort="dev"]');
    check("under the time sort every folder shows a relative time", await ctx.eval("[...document.querySelectorAll('#tree .tr.dir[data-fold-k^=\"dev:\"]')].every(r => /^(now|\\d+[mhd])$/.test((r.querySelector('em') || {}).textContent || ''))"));
    await ctx.click('[data-tsort="dev"]');
    check("closed (n) is the project's last entry", await ctx.eval(`(() => { const rows = [...document.querySelectorAll('#tree .tr')], at = rows.findIndex(r => r.dataset.foldK === ${J("dev:" + proj)});
      const end = rows.findIndex((r, i) => i > at && r.style.getPropertyValue('--d') === '0'), top = rows.slice(at + 1, end < 0 ? rows.length : end).filter(r => r.style.getPropertyValue('--d') === '1');
      return !top.some(r => /^closed/.test(r.textContent)) || /^closed \\(/.test(top[top.length - 1].querySelector('.nm').textContent); })()`));
    check("no horizontal scroll in either pane", await ctx.eval("['A','B'].every(k => V2.P[k].body.scrollWidth <= V2.P[k].body.clientWidth)"));
    await ctx.viewport(768, 1024); await ctx.sleep(300); await ctx.eval("V2.setFocus('B'); true"); await ctx.sleep(300);
    check("narrow: the pane that comes into view gets its line numbers", await ctx.eval("(() => { const t = [...document.querySelectorAll('#pB .lnum')].map(x => parseFloat(x.style.top)); return t.length > 2 && new Set(t).size === t.length; })()"));
  },
  // The human's fourth round: one cycling button per board setting, popovers over the narrow drawers,
  // the collapsed side rail aligned with the head row, and a side column that collapses fully when narrow.
  async round4(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");
    check("the board head: one button for grouping, one for the form, none per value", await ctx.eval("document.querySelectorAll('#bhd [data-grpc]').length === 1 && document.querySelectorAll('#bhd [data-formc]').length === 1 && !document.querySelector('#bhd [data-grp], #bhd [data-form]')"));
    const grps = [], forms = [];
    for (let i = 0; i < 3; i++) { await ctx.click("#bhd [data-grpc]"); grps.push(await ctx.eval("JSON.parse(localStorage.getItem('svd2-grp'))")); }
    check(`grouping cycles 项目 → 状态 → 治理 → 项目 (${grps.join(" ")})`, grps.join("") === "sgp");
    for (let i = 0; i < 4; i++) { await ctx.click("#bhd [data-formc]"); forms.push(await ctx.eval("JSON.parse(localStorage.getItem('svd2-form'))")); }
    check(`form cycles cards → cols → table → dots → cards (${forms.join(" ")})`, forms.join(",") === "cols,table,dots,cards");
    check("the button shows the current grouping", await ctx.eval("document.querySelector('#bhd [data-grpc]').textContent.trim() === '项目'"));

    await ctx.go("doc"); await ctx.eval("V2.W.sc = true; V2.applyW(); true"); await ctx.sleep(300);
    const align = "(() => { const a = document.getElementById('sideOpen').getBoundingClientRect(), b = document.querySelector('#pA .phd [data-t=star]').getBoundingClientRect(); return Math.abs(a.top - b.top) <= 1; })()";
    check("wide: the collapsed side rail's first button lines up with the head row", await ctx.eval(align));
    await ctx.viewport(768, 1024); await ctx.sleep(400);
    check("narrow: the same", await ctx.eval(align));

    await ctx.eval("V2.W.nx = true; V2.applyW(); true"); await ctx.sleep(200);
    await ctx.click("#pA [data-navb]"); await ctx.sleep(250); await ctx.click("#themeBtn"); await ctx.sleep(250);
    await ctx.viewport(1440, 900); await ctx.sleep(200); await ctx.click("#trailBtn"); await ctx.sleep(150); await ctx.eval("V2.chord.k(); true"); await ctx.sleep(150);
    check("quick open covers a popover that was open", await ctx.eval("(() => { const r = document.querySelector('#qo .qbox').getBoundingClientRect(), e = document.elementFromPoint(r.left + 20, r.top + 20); return !!e && !!e.closest('#qo'); })() && !document.getElementById('trailPop').classList.contains('on')"));
    await ctx.key("Escape"); await ctx.viewport(768, 1024); await ctx.sleep(300); await ctx.click("#pA [data-navb]"); await ctx.sleep(250); await ctx.click("#themeBtn"); await ctx.sleep(250);
    check("narrow drawer: the theme popover shows above it", await ctx.eval("(() => { const r = document.getElementById('themePop').getBoundingClientRect(), e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!e && !!e.closest('#themePop'); })()"));
    await ctx.key("Escape"); await ctx.key("Escape");

    await ctx.click("#sideOpen"); await ctx.sleep(250);
    check("narrow: the side rail collapses fully", await ctx.eval("document.getElementById('app').classList.contains('sx') && document.getElementById('side').getBoundingClientRect().width === 0"));
    check("…and the pane head gets a TOC button", await ctx.eval("getComputedStyle(document.querySelector('#pA .tocb')).display !== 'none'"));
    check("…and nothing of the rail is left over the pane head", await ctx.eval("(() => { const b = [...document.querySelectorAll('#pA .phd .ib')].filter(x => x.checkVisibility()).pop(), r = b.getBoundingClientRect(), e = document.elementFromPoint(r.right - 3, r.top + r.height / 2); return !!e && !e.closest('#side'); })()"));
    await ctx.eval("V2.W.nx = false; V2.applyW(); true"); await ctx.viewport(390, 844); await ctx.sleep(300);
    check("phone with the side collapse remembered: the nav strip keeps its 40px", await ctx.eval("getComputedStyle(document.getElementById('app')).gridTemplateColumns.split(' ')[0] === '40px'"));
    await ctx.click("#pA .tocb"); await ctx.sleep(200);
    check("phone: the drawer's button only closes it", await ctx.eval("document.getElementById('sideTog').dataset.tip === '关闭目录'"));
    await ctx.click("#sideTog"); await ctx.sleep(200);
    check("…and does so, the collapse untouched", await ctx.eval("!document.getElementById('app').classList.contains('tocpop') && V2.W.sx === true"));
    await ctx.viewport(768, 1024); await ctx.sleep(300);
    await ctx.click("#pA .tocb"); await ctx.sleep(250);
    check("…which opens the whole side column as a drawer, titled, with a restore button", await ctx.eval("document.getElementById('app').classList.contains('tocpop') && getComputedStyle(document.querySelector('#side .chd')).display !== 'none' && document.querySelectorAll('#sbody .ti').length > 0 && /恢复右侧竖条/.test(document.getElementById('sideTog').dataset.tip)"));
    await ctx.eval("location.reload(); true"); await ctx.sleep(400); await ctx.wait("!!document.querySelector('#tree .tr.top')"); await ctx.go("doc");
    check("the full collapse is remembered", await ctx.eval("document.getElementById('app').classList.contains('sx')"));
    await ctx.click("#pA .tocb"); await ctx.sleep(200); await ctx.click("#sideTog"); await ctx.sleep(250);
    check("restore brings the rail back and closes the drawer", await ctx.eval("!document.getElementById('app').classList.contains('sx') && !document.getElementById('app').classList.contains('tocpop') && document.getElementById('side').getBoundingClientRect().width > 0"));
  },
  // The human's fifth round: no project scope, narrow tables fit the pane, the TOC button sits last in the head,
  // one button on the narrow side rail (it hides the rail, as the nav's does), the collapsed nav keeps its dot in place.
  async round5(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    check("no project scope in the nav", await ctx.eval("!document.getElementById('scopeBar') && !document.getElementById('scopeSel')"));
    const dot = "Math.round(document.querySelector('#nav .brand i').getBoundingClientRect().top)";
    const open = await ctx.eval(dot);
    await ctx.eval("V2.W.nc = true; V2.applyW(); true"); await ctx.sleep(250);
    check(`collapsed nav: the dot stays where it was (${open}px)`, await ctx.eval(dot) === open);
    check("…and the first button starts below the head line", await ctx.eval("(() => { const b = [...document.querySelectorAll('#nav .chd .ib')].find(x => x.checkVisibility()), h = document.querySelector('#pA .phd').getBoundingClientRect(); return b.getBoundingClientRect().top >= h.bottom; })()"));
    await ctx.eval("V2.W.nc = false; V2.applyW(); true");
    await ctx.viewport(768, 1024); await ctx.sleep(400);
    check("narrow: the side rail has one button, and it hides the rail", await ctx.eval("!document.getElementById('sideX') && document.getElementById('sideOpen').dataset.tip === '完全收起右栏'"));
    await ctx.viewport(390, 844); await ctx.sleep(400);
    check("phone: the TOC button is the last one in the head", await ctx.eval("(() => { const b = [...document.querySelectorAll('#pA .phd .ib')].filter(x => x.checkVisibility()); return b[b.length - 1].classList.contains('tocb'); })()"));
    const fits = await ctx.eval(`(() => { const md = document.querySelector('#pA .md'), t = document.createElement('table');
      t.innerHTML = '<tr>' + '<th>column heading</th>'.repeat(6) + '</tr><tr>' + '<td>a_rather_long_token_without_spaces_inside</td>'.repeat(6) + '</tr>';
      md.appendChild(t); const ok = t.getBoundingClientRect().right <= md.getBoundingClientRect().right + 1 && t.scrollWidth <= t.clientWidth + 1; t.remove(); return ok; })()`);
    check("phone: a wide table fits the pane, no sideways scroll", fits);
    await ctx.go("board"); await ctx.eval("V2.setForm('table'); true"); await ctx.sleep(500);
    const tableFits = "(() => { const t = document.querySelector('#bscroll .tbl'), b = document.getElementById('bscroll'); return t.getBoundingClientRect().right <= b.getBoundingClientRect().right + 1 && b.scrollWidth <= b.clientWidth + 1; })()";
    for (const w of [390, 768, 1024, 1440]) {
      await ctx.viewport(w, 900); await ctx.sleep(400);
      check(`${w}: the board table fits without sideways scroll`, await ctx.eval(tableFits));
    }
    await ctx.viewport(390, 844); await ctx.sleep(400);
    check("phone: the board table keeps 编号 · 名称 · 状态 · 进度, the progress text uncut", await ctx.eval("(() => { const v = [...document.querySelectorAll('#bscroll .tbl thead th')].filter(th => th.offsetWidth > 0).map(th => th.textContent.replace(/[↑↓ ]/g, '')); return v.join() === '编号,名称,状态,进度' && [...document.querySelectorAll('#bscroll .tbl td.c-prog')].every(td => td.scrollWidth <= td.clientWidth + 1); })()"));
    await ctx.eval("V2.setForm('cards'); true");
  },
  // Card 043: an in-doc jump can be undone with back and redone with forward; one factor scales every text size.
  async round6(ctx, check) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc"); await ctx.sleep(400);
    const top = "Math.round(V2.P.A.body.scrollTop)";
    await ctx.eval("V2.P.A.body.scrollTop = 120; true"); await ctx.sleep(200);
    const before = await ctx.eval(top);
    await ctx.eval("document.querySelectorAll('[data-ti]')[4].click(); true"); await ctx.sleep(900);
    const jumped = await ctx.eval(top);
    check(`a TOC jump moves the reader (${before} → ${jumped})`, Math.abs(jumped - before) > 50);
    await ctx.eval("document.querySelector('#pA .md').dataset.probe = '1'; V2.back('A'); true"); await ctx.sleep(400);
    check("044: the edit button shows only on a todo file", await ctx.eval("getComputedStyle(document.querySelector('#pA .phd [data-t=tedit]')).display === 'none'"));
    check(`back returns to where the jump started (${await ctx.eval(top)}), same article, no re-render`, Math.abs(await ctx.eval(top) - before) <= 2 && await ctx.eval("document.querySelector('#pA .md').dataset.probe === '1'"));
    await ctx.eval("V2.fwd('A'); true"); await ctx.sleep(400);
    check(`forward goes back to the jump target (${await ctx.eval(top)})`, Math.abs(await ctx.eval(top) - jumped) <= 2);
    const fs = "parseFloat(getComputedStyle(document.querySelector('#pA .md p')).fontSize)";
    const base = await ctx.eval(fs);
    await ctx.eval("document.documentElement.style.setProperty('--fz', '1.2'); true"); await ctx.sleep(200);
    check(`--fz scales the text (${base}px → ${await ctx.eval(fs)}px)`, Math.abs(await ctx.eval(fs) - base * 1.2) < 0.2);
    await ctx.eval("document.documentElement.style.removeProperty('--fz'); true");
    // todo: read-only here (the harness serves the real dev_root, so nothing is written)
    await ctx.click("[data-todo]"); await ctx.wait("!!document.querySelector('#todo .tadd')");
    check("todo opens beside the board, with an add row", await ctx.eval("V2.kindOf('A') === 'todo' && !document.getElementById('todo').hidden"));
    check("…and ⌘K lists it", await ctx.eval("(() => { V2.chord.k(); const ok = [...document.querySelectorAll('#qList .qr')].some(r => /todo/.test(r.textContent)); V2.chord.k(); return ok; })()"));
  },
  // The human's third round: the change history stays open, find works on search results, quick open's old sizes,
  // the classic code fonts, the help panel, the search side list, mirror, and the brightness slider.
  async round3(ctx, check, o) {
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    check("inline code: Sarasa first, on a chip", await ctx.eval("(() => { const c = document.querySelector('#pA .md :not(pre) > code'); if (!c) return true; const s = getComputedStyle(c); return /^\"?Sarasa Fixed SC/.test(s.fontFamily) && s.backgroundColor !== 'rgba(0, 0, 0, 0)'; })()"));
    check("code blocks: Sarasa first", await ctx.eval("(() => { const c = document.querySelector('#pA .md pre'); return !c || /^\"?Sarasa Fixed SC/.test(getComputedStyle(c).fontFamily); })()"));
    await ctx.click("#pA [data-t=hist]"); await ctx.wait("document.querySelectorAll('#histPop [data-chg]:not([data-chg=\"\"])').length > 1", 5000);
    await ctx.click("#histPop [data-chg]:not([data-chg=''])"); await ctx.wait("!document.querySelector('#pA .chgbar').hidden", 5000); await ctx.sleep(300);
    check("picking a commit leaves the history open", await ctx.eval("document.getElementById('histPop').classList.contains('on')"));
    check("…the picked row stays one line", await ctx.eval("(() => { const c = document.querySelector('#histPop .hi.cur'), o = [...document.querySelectorAll('#histPop .hi:not(.cur)')].pop(); return !!c && Math.abs(c.offsetHeight - o.offsetHeight) <= 2; })()"));
    const first = await ctx.eval("document.querySelector('#histPop .hi.cur').dataset.chg");
    await ctx.click("#histPop .hi:not(.cur)[data-chg]:not([data-chg=''])"); await ctx.sleep(800);
    check("…and the next pick steps to another commit", await ctx.eval(`document.querySelector('#histPop .hi.cur') && document.querySelector('#histPop .hi.cur').dataset.chg !== ${J(first)}`));
    await ctx.key("Escape"); await ctx.click("#pA .chgbar [data-chg]");
    await ctx.click("#pA [data-t=mirror]"); await ctx.wait("!!document.querySelector('#pB .md')");
    check("mirror opens the same doc in B", await ctx.eval("V2.isSplit() && V2.P.B.loc.rel === V2.P.A.loc.rel"));
    await ctx.eval("V2.setSplit(false); true");

    await ctx.key("?", 8); await ctx.sleep(100);
    check("? opens the key help", await ctx.eval("!document.getElementById('help').hidden && document.querySelectorAll('#help kbd').length > 15"));
    await ctx.key("Escape");
    check("Esc closes it", await ctx.eval("document.getElementById('help').hidden"));

    await ctx.eval(nav("A", { kind: "search", q: "viewer" }) + "; true"); await ctx.wait("!!document.querySelector('#search .shit')"); await ctx.sleep(300);
    check("search: the side column lists the files hit", await ctx.eval("document.querySelectorAll('#sbody .sfr').length === document.querySelectorAll('#search .sfile').length && document.querySelectorAll('#sbody .sfr').length > 1"));
    await ctx.eval("(() => { const c = document.querySelector('#sbody [data-sfh]'); c.checked = false; c.dispatchEvent(new Event('change', { bubbles: true })); return true; })()");
    check("…unticking a file hides its hits", await ctx.eval("document.querySelector('#search .sfile[data-g=\"0\"]').hidden"));
    await ctx.click("#sbody [data-sfj='2']"); await ctx.sleep(700);
    check("…a file name jumps to its hits", await ctx.eval("document.querySelector('#search .sres').scrollTop > 0"));
    await ctx.key("f"); await ctx.type("viewer"); await ctx.sleep(350);
    check("f finds inside the search results", await ctx.eval("(CSS.highlights.get('hit-A') || { size: 0 }).size + (CSS.highlights.get('hitc-A') || { size: 0 }).size > 0 && document.querySelectorAll('#pA .frail i').length > 0"));
    await ctx.key("Escape");

    for (const rel of (await ctx.eval("V2.D.tree.dev.map(x => x.path).filter(p => p.endsWith('.md')).slice(0, 9)"))) await ctx.eval(`V2.nav("A", { kind: "doc", tree: "dev", rel: ${J(rel)} }); true`);
    await ctx.sleep(300); await ctx.eval("V2.chord.k(); true"); await ctx.sleep(150);
    check("⌘K lists eight recently opened docs", await ctx.eval("(() => { const rows = [...document.querySelectorAll('#qList > *')], i = rows.findIndex(r => r.textContent.startsWith('最近打开')); let n = 0; for (let j = i + 1; j < rows.length && !rows[j].classList.contains('qg'); j++) n++; return n === 8; })()"));
    check("…and a 最近提交 row", await ctx.eval("[...document.querySelectorAll('#qList .qr')].some(r => r.textContent.startsWith('最近提交'))"));
    await ctx.type("md"); await ctx.sleep(250);
    check("⌘K shows up to forty docs", await ctx.eval("(() => { const rows = [...document.querySelectorAll('#qList > *')], i = rows.findIndex(r => r.textContent === '文档'); let n = 0; for (let j = i + 1; j < rows.length && !rows[j].classList.contains('qg'); j++) n++; return n === 40; })()"));
    await ctx.key("Escape");

    await ctx.click("#themeBtn"); await ctx.sleep(100);
    await ctx.eval("(() => { const i = document.getElementById('lumIn'); i.value = 120; i.dispatchEvent(new Event('input', { bubbles: true })); return true; })()");
    check("brightness 120% brightens the page", await ctx.eval("document.documentElement.style.filter === 'brightness(1.2)'"));
    await ctx.eval("location.reload(); true"); await ctx.sleep(400); await ctx.wait("!!document.querySelector('#tree .tr.top')");
    check("…and is remembered", await ctx.eval("document.documentElement.style.filter === 'brightness(1.2)'"));
    await ctx.click("#themeBtn"); await ctx.click("[data-lum0]");
    await ctx.viewport(390, 844); await ctx.eval(`V2.nav("A", { kind: "doc", tree: "dev", rel: ${J(o.doc.slice(4).split("/")[0] + "/index.md")} }); true`); await ctx.wait("!!document.querySelector('#pA .md table')"); await ctx.sleep(300);
    check("narrow: tables wrap into the pane, none scrolls sideways", await ctx.eval("[...document.querySelectorAll('#pA .md table')].every(t => t.scrollWidth <= t.clientWidth + 1)"));
    await ctx.viewport(1440, 900);
    check("复位 brings back the page as designed", await ctx.eval("document.documentElement.style.filter === '' && document.getElementById('lumIn').value === '100'"));
  },
  // The two panes sit above their content: either can hold the board, a search, a diff, the recent commits or a doc.
  async panes2(ctx, check, o) {
    const shiftClick = (sel) => ctx.eval(`(() => { const e = document.querySelector(${J(sel)}); if (!e) return false; e.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: true })); return true; })()`);
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("doc");
    await shiftClick("#tree [data-goboard]"); await ctx.wait("!!document.querySelector('#pB #bscroll [data-card]')");
    check("⇧ on 看板 opens the board in B, the doc stays in A", await ctx.eval("V2.kindOf('A') === 'doc' && V2.kindOf('B') === 'board' && V2.view === 'board'"));
    check("the board's head in B carries the pane tag and a close button", await ctx.eval("!!document.querySelector('#bhd .ptag') && document.querySelector('#bhd .ptag').textContent === 'B' && !!document.querySelector('#bhd [data-t=close]')"));
    check("the doc chrome of B is hidden while it hosts the board", await ctx.eval("getComputedStyle(document.querySelector('#pB > .pbody')).display === 'none'"));
    await ctx.click("#pB #bscroll .card[data-card]"); await ctx.key("Enter"); await ctx.wait("V2.kindOf('B') === 'doc'"); await ctx.sleep(300);
    check("Enter on a card in B opens it in B", await ctx.eval("V2.kindOf('B') === 'doc' && V2.kindOf('A') === 'doc'"));
    await ctx.eval("V2.back('B'); true"); await ctx.wait("!!document.querySelector('#pB #bscroll [data-card]')");
    check("back in B returns to the board", await ctx.eval("V2.kindOf('B') === 'board'"));
    await ctx.eval("V2.setFocus('A'); V2.nav('A', { kind: 'board' }); true"); await ctx.wait("!!document.querySelector('#pA #bscroll [data-card]')"); await ctx.sleep(200);
    check("opening the board in A takes it from B: B is blank and keeps it in its history", await ctx.eval("V2.kindOf('A') === 'board' && V2.kindOf('B') === null && V2.P.B.hist.some(l => l.kind === 'board') && document.getElementById('pB').classList.contains('blank')"));
    await ctx.eval("V2.nav('B', { kind: 'recent' }); true"); await ctx.wait("!!document.querySelector('#pB #recent .commit, #pB #recent .hint:not(:first-child)')", 8000);
    check("the recent commits open in B", await ctx.eval("V2.kindOf('B') === 'recent' && document.querySelectorAll('#pB #recent .commit').length > 0"));
    await ctx.viewport(768, 1024); await ctx.sleep(400);
    check("narrow: the split closes, A takes the screen, and the head has no split button", await ctx.eval("!V2.isSplit() && getComputedStyle(document.getElementById('pB')).display === 'none' && getComputedStyle(document.querySelector('#bhd [data-t=split]')).display === 'none'"));
    await ctx.eval("V2.setSplit(true); true"); await ctx.sleep(200);
    check("narrow: a split cannot be opened", await ctx.eval("!V2.isSplit() && getComputedStyle(document.getElementById('pB')).display === 'none'"));
    await ctx.eval("V2.nav('B', { kind: 'recent' }); true"); await ctx.sleep(400);
    check("narrow: a view sent to B lands in A", await ctx.eval("V2.kindOf('A') === 'recent' && !V2.isSplit()"));
  },
  // Details of the classic shell that v2 was missing or weaker on, one check each.
  async parity(ctx, check, o) {
    const shiftClick = (sel) => ctx.eval(`(() => { const e = document.querySelector(${J(sel)}); if (!e) return false; e.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: true })); return true; })()`);
    const qo = async (q) => { await ctx.eval("document.getElementById('qo').hidden || V2.chord.k(); V2.chord.k(); true"); await ctx.sleep(50); await ctx.type(q); await ctx.sleep(250); };
    const qoRows = "[...document.querySelectorAll('#qList > *')].map(e => e.className.startsWith('qg') ? '#' + e.firstChild.textContent : (e.querySelector('.qn') || e).textContent + '|' + ((e.querySelector('.qd') || {}).textContent || ''))";
    await ctx.viewport(1440, 900); await ctx.load(); await ctx.go("board");

    // tree: times only under a time sort, which starts newest first; the sort controls take the keyboard
    const timeEm = "[...document.querySelectorAll('#tree .tr:not(.top) em, #tree .tr.dir em')].filter(e => /^(now|\\d+[mhd])$/.test(e.textContent)).length";
    check("name sort: the tree shows no times", await ctx.eval(timeEm) === 0);
    check("the sort controls are buttons", await ctx.eval("[...document.querySelectorAll('#tree .tsec .tc')].every(e => e.tagName === 'BUTTON')"));
    await ctx.click('[data-tsort="dev"]');
    check("time sort: the tree shows times", await ctx.eval(timeEm) > 0);
    check("switching to time sort starts newest first", await ctx.eval("JSON.parse(localStorage.getItem('svd2-tree-sort')).dev.dir === -1"));
    await ctx.click('[data-tsort="dev"]');
    check("back to name sort runs A→Z", await ctx.eval("JSON.parse(localStorage.getItem('svd2-tree-sort')).dev.dir === 1"));

    // board: the table has a next column and full names on hover
    await ctx.eval("V2.setForm('table'); true");
    check("table: a 下一步 column", await ctx.eval("[...document.querySelectorAll('#bscroll .tbl th')].some(t => t.textContent === '下一步')"));
    check("table: a cut name is readable from its tip", await ctx.eval("[...document.querySelectorAll('#bscroll .tbl td.nm')].every(t => t.dataset.tip)"));

    // ⇧ from the board or the search results opens beside them, the board or the results stay
    await ctx.eval("V2.setForm('cards'); true");
    await shiftClick("#bscroll .card[data-card]"); await ctx.wait("!!document.querySelector('#pB .md')");
    check("⇧ on a card: the board stays and the doc opens in B", await ctx.eval("V2.kindOf('A') === 'board' && V2.kindOf('B') === 'doc'"));
    check("…side by side", await ctx.eval("(() => { const a = document.getElementById('board').getBoundingClientRect(), b = document.getElementById('pB').getBoundingClientRect(); return a.width > 200 && b.width > 200 && a.right <= b.left + 6; })()"));
    check("beside: the side column lists B's headings", await ctx.eval("getComputedStyle(document.getElementById('side')).display !== 'none' && document.querySelectorAll('#sbody .ti').length > 0"));
    const selBefore = await ctx.eval("(document.querySelector('#bscroll .card.sel') || {}).dataset?.card || null");
    await ctx.eval("V2.setFocus('B'); true"); await ctx.key("ArrowDown"); await ctx.key("ArrowDown");
    check("beside, B focused: arrows leave the board selection alone", await ctx.eval("(document.querySelector('#bscroll .card.sel') || {}).dataset?.card || null") === selBefore);
    await ctx.eval("V2.setFocus('A'); true");
    await ctx.eval(nav("A", { kind: "search", q: "viewer" }) + "; true"); await ctx.wait("!!document.querySelector('#search .shit')");
    await ctx.eval("document.querySelector('#search .sres').scrollTop = 300; true");
    await shiftClick("#search .shit:nth-of-type(2)"); await ctx.sleep(500);
    check("⇧ on a search hit: the results stay and the doc opens in B", await ctx.eval("V2.kindOf('A') === 'search' && V2.kindOf('B') === 'doc'"));
    await ctx.click("#pB [data-t=close]");
    const sy = await ctx.eval("document.querySelector('#search .sres').scrollTop");
    await ctx.click("#search .shit"); await ctx.wait("!!document.querySelector('#pA .md')");
    await ctx.eval("V2.back('A'); true"); await ctx.wait("!!document.querySelector('#search .shit')"); await ctx.sleep(200);
    check(`back to the search results keeps their scroll (${sy})`, Math.abs(await ctx.eval("document.querySelector('#search .sres').scrollTop") - sy) < 4);

    // ⌘K: English words reach the nav rows, ties go to the newest, card and Fact groups match contiguously, clear is always there
    await qo("board");
    check("⌘K board finds the board row", /^看板/.test((await ctx.eval(qoRows))[0]));
    await ctx.key("Escape"); await qo("design");
    const dr = (await ctx.eval(qoRows)).filter(r => r.startsWith("design.md|"));
    const newest = await ctx.eval("fetch('/api/tree').then(r => r.json()).then(t => t.dev.filter(x => /design\\.md$/.test(x.path)).sort((a, b) => b.mtime - a.mtime)[0].path)", true);
    check(`⌘K design: the newest design.md comes first (${dr[0]} vs ${newest})`, !!dr[0] && newest.startsWith(dr[0].split("|")[1].replace(/\/$/, "").trim()));
    await ctx.key("Escape"); await qo("040");
    const r040 = await ctx.eval(qoRows), grp = (rs, g) => { const i = rs.indexOf("#" + g); if (i < 0) return []; const j = rs.findIndex((r, k) => k > i && r.startsWith("#")); return rs.slice(i + 1, j < 0 ? undefined : j); };
    check("⌘K 040: every card row carries 040", grp(r040, "卡片").length > 0 && grp(r040, "卡片").every(r => r.includes("040")));
    check("⌘K 040: every Fact row carries 040", grp(r040, "Fact").every(r => r.includes("040")));
    await ctx.key("Escape"); await qo("Fact-2"); await ctx.sleep(1500); await ctx.eval("document.getElementById('qIn').dispatchEvent(new Event('input')); true"); await ctx.sleep(100);
    const f2 = grp(await ctx.eval(qoRows), "Fact");
    check(`⌘K Fact-2: the exact id leads (${f2[0]})`, !!f2[0] && f2[0].startsWith("Fact-2|"));
    await ctx.key("Escape"); await ctx.eval("localStorage.removeItem('svd2-recent-search'); true"); await qo("");
    check("⌘K: clear history is there with no search history", await ctx.eval(has("#qo [data-qclear]")));
    await ctx.key("Escape");

    // reader: two width rules each moving one edge, the custom width stays in the cycle, h1–h6 in the TOC
    await ctx.go("doc");
    check("two width rules", await ctx.eval("document.querySelectorAll('#pA .md > .mrule').length") === 2);
    const box = () => ctx.eval("(() => { const r = document.querySelector('#pA .md').getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right)]; })()");
    const drag = (which, dx) => ctx.eval(`(() => { const r = document.querySelectorAll('#pA .md > .mrule')[${which}], b = r.getBoundingClientRect(), x = b.left + 4, y = b.top + 40;
      const ev = (t, cx) => r.dispatchEvent(new PointerEvent(t, { bubbles: true, clientX: cx, clientY: y, pointerId: 1 }));
      ev("pointerdown", x); ev("pointermove", x + ${dx}); ev("pointerup", x + ${dx}); return true; })()`);
    const b0 = await box(); await drag(0, 60); const b1 = await box();
    check(`left rule: the left edge moves, the right stays (${J(b0)} → ${J(b1)})`, Math.abs(b1[0] - b0[0] - 60) <= 2 && Math.abs(b1[1] - b0[1]) <= 2);
    await drag(1, -80); const b2 = await box();
    check(`right rule: the right edge moves, the left stays (${J(b1)} → ${J(b2)})`, Math.abs(b2[1] - b1[1] + 80) <= 2 && Math.abs(b2[0] - b1[0]) <= 2);
    const tipOf = () => ctx.eval("document.querySelector('#pA [data-t=width]').dataset.tip");
    const seen = [];
    for (let i = 0; i < 3; i++) { await ctx.click("#pA [data-t=width]"); seen.push(await tipOf()); }
    check(`the width cycle comes back to the dragged width (${seen.join(" → ")})`, /自定/.test(seen[2]) && J(await box()) === J(b2));
    check("the TOC lists every heading level", await ctx.eval("document.querySelectorAll('#sbody .ti').length === document.querySelectorAll('#pA .md :is(h1,h2,h3,h4,h5,h6)').length"));
    check("the path has a tip", await ctx.eval("!!document.querySelector('#pA .ppath').dataset.tip"));

    // find: the frontmatter is not searched, ⌘K works from the find box, one-letter terms are not remembered, pins keep their colours on the rail
    await ctx.key("f"); await ctx.type("lite"); await ctx.sleep(300);
    check("find skips the frontmatter", await ctx.eval("['hit-A', 'hitc-A'].flatMap(n => [...(CSS.highlights.get(n) || [])]).every(r => !r.startContainer.parentElement.closest('.fml,.fmt'))"));
    await ctx.key("k", 4); await ctx.sleep(100);
    check("⌘K opens from the find box", await ctx.eval("!document.getElementById('qo').hidden"));
    await ctx.key("Escape");
    await ctx.eval("(() => { const i = document.querySelector('#pA .find input'); i.focus(); i.value = 'x'; i.dispatchEvent(new Event('input')); return true; })()"); await ctx.sleep(250);
    await ctx.key("Enter"); await ctx.key("Escape");
    check("a one-letter find is not remembered", await ctx.eval("!(JSON.parse(localStorage.getItem('svd2-recent-find') || '[]')).includes('x')"));
    for (const t of ["viewer", "req"]) { await ctx.key("f"); await ctx.type(t); await ctx.sleep(250); await ctx.key("Enter", 4); await ctx.key("Escape"); }
    check("pins keep their colours on the rail", await ctx.eval("document.querySelectorAll('#pA .frail i.p0').length > 0 && document.querySelectorAll('#pA .frail i.p1').length > 0"));
    await ctx.key("H", 8);

    // citations and links take Enter; a link preview can be entered and scrolled
    await ctx.eval("document.querySelector('#pA .cite[data-ref^=Fact]').focus(); true"); await ctx.key("Enter"); await ctx.sleep(600);
    check("Enter on a focused citation follows it", await ctx.eval("!!V2.P.B.loc && /facts\\.md$/.test(V2.P.B.loc.rel)"));
    check("split: the focused pane's head is marked", await ctx.eval("getComputedStyle(document.querySelector('#pA .phd')).boxShadow !== 'none' && getComputedStyle(document.querySelector('#pB .phd')).boxShadow === 'none'"));
    await ctx.click("#pB [data-t=close]");
    await ctx.sleep(300);   // closing B re-lays A out a moment later
    await ctx.mouseMove("#pA .md a[data-rel]");
    await ctx.wait("document.getElementById('tip').classList.contains('wide')", 3000);
    check("the link preview takes the pointer and scrolls", await ctx.eval("(() => { const s = getComputedStyle(document.getElementById('tip')); return s.pointerEvents === 'auto' && s.overflowY === 'auto'; })()"));
    await ctx.mouseMove("#tip"); await ctx.sleep(700);
    check("moving into the preview keeps it open", await ctx.eval("document.getElementById('tip').classList.contains('on')"));
    await ctx.key("Escape");

    // a quick move from one link to the next keeps the second preview
    // two links on one screen: hover the first, then move straight to the second
    const pair = await ctx.eval(`(() => { const ls = [...document.querySelectorAll('#pA .md a[data-rel]')], b = V2.P.A.body;
      for (let i = 0; i + 1 < ls.length; i++) if (ls[i + 1].offsetTop - ls[i].offsetTop < 300 && ls[i].dataset.rel !== ls[i + 1].dataset.rel) {
        b.scrollTop += ls[i].getBoundingClientRect().top - b.getBoundingClientRect().top - 100;
        const c = e => { const r = e.getClientRects()[0]; return [r.x + r.width / 2, r.y + r.height / 2, e.dataset.rel.split('/').pop()]; };
        return [c(ls[i]), c(ls[i + 1])]; }
      return null; })()`);
    if (pair) {
      await ctx.sleep(300); await ctx.mouseAt(pair[0][0], pair[0][1]); await ctx.wait("document.getElementById('tip').classList.contains('wide')", 3000);
      await ctx.mouseAt(pair[1][0], pair[1][1]); await ctx.sleep(900);
      check(`hopping to the next link keeps its preview open (${pair[1][2]})`, await ctx.eval(`(() => { const t = document.getElementById('tip'); return t.classList.contains('on') && t.textContent.includes(${J(pair[1][2])}); })()`));
      await ctx.key("Escape");
    }

    // ⇧⌘↵ in ⌘K puts the full-text search beside the doc being read, at the same place
    await ctx.eval("V2.P.A.body.scrollTop = 1500; true"); await ctx.sleep(500);
    await qo("viewer"); await ctx.key("Enter", 12); await ctx.wait("!!document.querySelector('#pB #search .smeta')"); await ctx.sleep(400);
    check("⇧⌘↵: the search opens in B, beside the doc in A", await ctx.eval("V2.kindOf('B') === 'search' && V2.kindOf('A') === 'doc'"));
    check("…and A keeps its place", await ctx.eval("V2.P.A.body.scrollTop > 1000"));
    await ctx.click("#pB [data-t=close]");

    // the change view numbers its lines
    await ctx.go("doc"); await ctx.click("#pA [data-t=hist]"); await ctx.wait("!!document.querySelector('#histPop [data-chg]:not([data-chg=\"\"])')", 5000);
    await ctx.click("#histPop [data-chg]:not([data-chg=''])"); await ctx.wait("!document.querySelector('#pA .chgbar').hidden", 5000); await ctx.sleep(300);
    check("the change view has line numbers", await ctx.eval("document.querySelectorAll('#pA .lnum').length > 0"));

    // a blank B takes no doc keys; full width never runs past a narrow split pane
    await ctx.go("doc"); await ctx.eval("V2.setSplit(false); V2.P.B.loc = null; true"); await ctx.click('#pA [data-t="split"]'); await ctx.eval("V2.setFocus('B'); true");
    check("a blank B: no reading pane for s or f", await ctx.eval("V2.readingK() === null"));
    await ctx.eval("V2.setSplit(false); true");
    await ctx.viewport(1000, 800); await ctx.eval("localStorage.setItem('svd2-measure', JSON.stringify({ A: { mode: 'full' }, B: { mode: 'full' } })); true"); await ctx.load(); await ctx.go("doc");
    await ctx.eval(`V2.nav("B", ${J(docLoc(o))}); true`); await ctx.wait("!!document.querySelector('#pB .md')"); await ctx.sleep(300);
    check("full width in a narrow split pane stays inside it", await ctx.eval("['A','B'].every(k => { const b = V2.P[k].body, m = b.querySelector('.md'); return m.getBoundingClientRect().right <= b.getBoundingClientRect().right; })"));

    // narrow: no width controls; the table folds the closed cards like the other forms
    await ctx.viewport(768, 1024); await ctx.load(); await ctx.go("doc");
    check("narrow: the width button and rules are hidden", await ctx.eval("getComputedStyle(document.querySelector('#pA [data-t=width]')).display === 'none' && [...document.querySelectorAll('#pA .mrule')].every(r => getComputedStyle(r).display === 'none')"));
    await ctx.go("board");
    check("narrow table: no closed card until its fold is opened", await ctx.eval("!document.querySelector('#bscroll tr[data-st=done], #bscroll tr[data-st=dropped]') && !!document.querySelector('#bscroll [data-fold]')"));
    await ctx.click("#bscroll [data-fold]");
    check("…and the fold opens them", await ctx.eval(has("#bscroll tr[data-st=done], #bscroll tr[data-st=dropped]")));
    await ctx.eval("V2.setForm('dots'); true");
    check("dots: every card sits on the line, done and dropped included, no fold", await ctx.eval("!document.querySelector('#bscroll [data-fold]') && document.querySelectorAll('#bscroll .dot').length === [...document.querySelectorAll('#bscroll .dnum')].reduce((n, e) => n + parseInt(e.textContent), 0) && !!document.querySelector('#bscroll .dot.done')"));
  },
};

export default { VIEW, MEASURE, SCENARIO, views: "board,doc,search,diff",
  ready: "!!document.querySelector('#tree .tr.top') && !!document.querySelector('#bscroll [data-card], #bscroll .empty-b')", mask: ".phd, .find, .chgbar, .stale" };
