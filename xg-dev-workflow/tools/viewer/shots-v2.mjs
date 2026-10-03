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
const visible = (sel) => `(() => { const e = document.querySelector(${J(sel)}); return !!e && getComputedStyle(e).display !== "none" && getComputedStyle(e).visibility !== "hidden" && e.getBoundingClientRect().width > 0; })()`;

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
    if (await ctx.eval("!!document.querySelector('meta[name=gitweb-url]').content")) check("gitweb deep link carries the project", await ctx.eval("/\\?p=[^;]+;a=summary/.test(document.querySelector('#bdet .blinks a').getAttribute('href'))"));
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
};

export default { VIEW, MEASURE, SCENARIO, views: "board,doc,search,diff",
  ready: "!!document.querySelector('#tree .tr.top') && !!document.querySelector('#bscroll [data-card], #bscroll .empty-b')", mask: ".phd, .find, .chgbar, .stale" };
export { rect, has, visible };
