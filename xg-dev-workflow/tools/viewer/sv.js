"use strict";
// ---------------------------------------------------------------------------
// Pure helpers (unit-tested in test-shell.mjs). No DOM here — exported via window
// / module.exports so the node test can import them.
// ---------------------------------------------------------------------------
var SV = (function () {
  // Split a doc's front matter (--- fence) into {fields, body}; flat key: value only.
  function parseFrontmatter(text) {
    if (!text.startsWith("---")) return { fields: {}, body: text };
    var end = text.indexOf("\n---", 3);
    if (end === -1) return { fields: {}, body: text };
    var head = text.slice(3, end), fields = {};
    head.split("\n").forEach(function (line) {
      var m = line.match(/^(\w+):\s*(.+)$/);
      if (m) fields[m[1]] = m[2].trim();
    });
    return { fields: fields, body: text.slice(end + 4).replace(/^\n+/, "") };
  }

  // Normalize a doc link to "<tree>:<relpath>" (canonical case), or null if unresolvable.
  function resolveLink(href, curTree, curRel, treeSets) {
    href = String(href).trim();
    var wiki = href.match(/^\[\[(.+?)\]\]$/);
    var target, tree;
    if (wiki) {
      var x = wiki[1].split("|")[0].split("#")[0].trim();
      if (/^(wiki|raw)\//.test(x)) { tree = "kb"; target = x.endsWith(".md") ? x : x + ".md"; }
      else return null;                                       // legacy bare/colon → broken
    } else {
      if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith("#")) return null;
      var path = href.split("#")[0];
      if (!/\.(md|html)$/.test(path)) return null;
      tree = curTree;
      var dir = curRel.indexOf("/") === -1 ? "" : curRel.replace(/\/[^/]*$/, "");
      target = normalizePath(dir, path);
      if (target === null) return null;
    }
    var canon = treeSets[tree] && treeSets[tree].get(target.toLowerCase());  // case-insensitive
    return canon ? tree + ":" + canon : null;
  }

  function normalizePath(dir, rel) {
    var parts = (dir ? dir.split("/") : []);
    rel.split("/").forEach(function (p) {
      if (parts === null || p === "" || p === ".") return;
      if (p === "..") { if (!parts.length) { parts = null; return; } parts.pop(); }
      else parts.push(p);
    });
    return parts === null ? null : parts.join("/");
  }

  // Project names from the two trees' paths: a dev path contributes its first segment ONLY if
  // it's inside a project dir (has a "/"), so top-level files like index.md/log.md are excluded;
  // a kb path contributes raw/<proj> | wiki/<proj>'s second segment.
  function projectsFromTree(dev, kb) {
    var set = {};
    (dev || []).forEach(function (p) { if (p.indexOf("/") !== -1) set[p.split("/")[0]] = 1; });
    // kb: raw/<proj>/<file> | wiki/<proj>/<file> → the project is segment[1], but only when a
    // file sits under it (length > 2); this excludes the KB's own wiki/index.md, wiki/log.md.
    (kb || []).forEach(function (p) { var s = p.split("/"); if (s.length > 2) set[s[1]] = 1; });
    return Object.keys(set).sort();
  }

  // Fold items [{path, mtime}] (mtime optional) into a nested {dirs:{name:node}, files:[...]}
  // tree. Files within a dir are sorted by mtime ASCENDING (oldest first); dirs render first
  // (see nodeHtml) sorted by name. Accepts bare-string items too (mtime defaults 0).
  function buildTree(items) {
    var root = { dirs: {}, files: [], mtime: 0 };
    (items || []).forEach(function (it) {
      var p = typeof it === "string" ? it : it.path, mtime = typeof it === "string" ? 0 : (it.mtime || 0);
      var segs = p.split("/"), node = root;
      node.mtime = Math.max(node.mtime, mtime);   // R1: dir mtime = newest descendant (lets a dir float by recency)
      for (var i = 0; i < segs.length - 1; i++) {
        var d = segs[i];
        node.dirs[d] = node.dirs[d] || { dirs: {}, files: [], mtime: 0 };
        node = node.dirs[d];
        node.mtime = Math.max(node.mtime, mtime);
      }
      node.files.push({ name: segs[segs.length - 1], path: p, mtime: mtime });
    });
    sortFiles(root);
    return root;
  }
  function sortFiles(node) {
    node.files.sort(function (a, b) { return a.mtime - b.mtime || a.name.localeCompare(b.name); });
    Object.keys(node.dirs).forEach(function (d) { sortFiles(node.dirs[d]); });
  }
  // R1: comparator for tree nodes ({name, mtime}) — name (A) or modified (T), asc/desc; name breaks mtime ties.
  function sortCmp(key, dir) {
    dir = dir < 0 ? -1 : 1;
    return key === "mtime"
      ? function (a, b) { return (a.mtime - b.mtime) * dir || a.name.localeCompare(b.name); }
      : function (a, b) { return a.name.localeCompare(b.name) * dir; };
  }
  // R5/R9/R10 (ADR-0003): fzf-style matcher. The query splits on whitespace into terms — ALL must match
  // (AND), order-independent. A leading `=` makes a term an exact contiguous substring; otherwise it is a
  // fuzzy subsequence scored by OPTIMAL alignment (word-boundary starts + consecutive runs rewarded, gaps
  // penalised with a bounded start+extension cost). Each term scores against the full path and — when
  // nameStart>0 — the filename tail, taking the better plus a filename bonus (名>路径). smart-case: a term
  // with an uppercase char matches case-sensitively. Returns {hit, score, idx} — idx = matched positions in
  // `str` (highlights name AND path). nameStart omitted (nav items) ⇒ pure whole-string matching.
  var MS_BASE = 16, MS_BOUNDARY = 16, MS_CONSEC = 8, MS_GAP_START = 3, MS_GAP_EXT = 1, MS_NAME_BONUS = 32;
  function msBoundary(str, i) {
    return i === 0 || /[\/\-_.\s]/.test(str[i - 1]) || (/[a-z]/.test(str[i - 1]) && /[A-Z]/.test(str[i]));
  }
  function msParse(q) {
    var out = [], parts = String(q == null ? "" : q).split(/\s+/);
    for (var i = 0; i < parts.length; i++) {
      var t = parts[i]; if (!t) continue;
      if (t.charAt(0) === "=") { if (t.length > 1) out.push({ exact: true, ndl: t.slice(1) }); }
      else out.push({ exact: false, ndl: t });
    }
    return out;
  }
  function msAlign(term, str) {                     // one term vs one string → {hit,score,idx (in str coords)}
    var cs = /[A-Z]/.test(term.ndl);                // smart-case
    var ndl = cs ? term.ndl : term.ndl.toLowerCase();
    var hay = cs ? str : str.toLowerCase();
    var n = hay.length, m = ndl.length;
    if (!m) return { hit: true, score: 0, idx: [] };
    if (term.exact) {
      var p = hay.indexOf(ndl); if (p < 0) return { hit: false, score: 0, idx: [] };
      var eidx = []; for (var e = 0; e < m; e++) eidx.push(p + e);
      return { hit: true, score: m * (MS_BASE + MS_CONSEC) + (msBoundary(str, p) ? MS_BOUNDARY : 0), idx: eidx };
    }
    var jg = 0; for (var gi = 0; gi < n && jg < m; gi++) if (hay.charAt(gi) === ndl.charAt(jg)) jg++;
    if (jg < m) return { hit: false, score: 0, idx: [] };     // cheap subsequence reject before the DP
    var NEG = -1e9, sc = [], bk = [];
    for (var j = 0; j < m; j++) { var r1 = [], r2 = []; for (var c = 0; c < n; c++) { r1.push(NEG); r2.push(-1); } sc.push(r1); bk.push(r2); }
    for (var i = 0; i < n; i++) {
      for (var jj = 0; jj < m && jj <= i; jj++) {
        if (hay.charAt(i) !== ndl.charAt(jj)) continue;
        var chScore = MS_BASE + (msBoundary(str, i) ? MS_BOUNDARY : 0);
        if (jj === 0) { if (chScore > sc[0][i]) { sc[0][i] = chScore; bk[0][i] = -1; } continue; }
        for (var k = jj - 1; k < i; k++) {
          if (sc[jj - 1][k] === NEG) continue;
          var gap = i - k - 1;
          var val = sc[jj - 1][k] + chScore + (gap === 0 ? MS_CONSEC : -(MS_GAP_START + (gap - 1) * MS_GAP_EXT));
          if (val > sc[jj][i]) { sc[jj][i] = val; bk[jj][i] = k; }
        }
      }
    }
    var best = NEG, bi = -1;
    for (var x = 0; x < n; x++) if (sc[m - 1][x] > best) { best = sc[m - 1][x]; bi = x; }
    var idx = [], jb = m - 1, ib = bi;
    while (ib >= 0 && jb >= 0) { idx.push(ib); ib = bk[jb][ib]; jb--; }
    idx.reverse();
    return { hit: true, score: best, idx: idx };
  }
  function matchScore(q, str, nameStart) {
    var terms = msParse(q);
    if (!terms.length) return { hit: true, score: 0, idx: [] };
    nameStart = nameStart || 0;
    var total = 0, set = {};
    for (var t = 0; t < terms.length; t++) {
      var full = msAlign(terms[t], str);
      if (!full.hit) return { hit: false, score: -Infinity, idx: [] };
      var sTerm = full.score, tidx = full.idx;
      if (nameStart > 0) {
        var nm = msAlign(terms[t], str.slice(nameStart));
        if (nm.hit && nm.score + MS_NAME_BONUS >= sTerm) {
          sTerm = nm.score + MS_NAME_BONUS;
          tidx = nm.idx.map(function (v) { return v + nameStart; });
        }
      }
      total += sTerm;
      for (var g = 0; g < tidx.length; g++) set[tidx[g]] = 1;
    }
    var out = []; for (var key in set) out.push(+key); out.sort(function (a, b) { return a - b; });
    return { hit: true, score: total, idx: out };
  }
  // R6/R7/R8: push an item onto a "recent use" list — dedup (move existing to front), cap, recency-ordered.
  function recentPush(list, item, cap) {
    var out = (list || []).filter(function (x) { return x !== item; });
    out.unshift(item);
    return out.slice(0, cap || 8);
  }

  // Group trace rows by design part, design order → [{part, rows}] (015).
  // null when the card is un-split (parts empty) — caller renders flat; rows with
  // no part land in a trailing "—" group; a multi-part row appears in each group.
  function groupTraceRows(rows, parts) {
    if (!parts || !parts.length) return null;
    var groups = parts.map(function (p) {
      return { part: p, rows: (rows || []).filter(function (r) {
        return (r.parts || []).indexOf(p) !== -1; }) };
    });
    var rest = (rows || []).filter(function (r) { return !(r.parts || []).length; });
    if (rest.length) groups.push({ part: "—", rows: rest });
    return groups;
  }

  // Group search hits by file, preserving first-seen order → [{tree, path, hits:[...]}].
  function groupHits(hits) {
    var order = [], by = {};
    (hits || []).forEach(function (h) {
      var k = h.tree + ":" + h.path;
      if (!by[k]) { by[k] = { tree: h.tree, path: h.path, hits: [] }; order.push(k); }
      by[k].hits.push(h);
    });
    return order.map(function (k) { return by[k]; });
  }

  // Flatten a doc's headings into a TOC list [{depth,text,slug}] (slug = anchor id).
  function tocFromHeadings(headings) {
    return (headings || []).map(function (h) {
      return { depth: h.depth, text: h.text,
               slug: h.text.toLowerCase().replace(/[^\w一-鿿]+/g, "-").replace(/^-+|-+$/g, "") };
    });
  }

  function colorizeDiff(text) {
    return text.split("\n").map(function (line) {
      var cls = line.startsWith("@@") ? "hunk"
              : (line.startsWith("+") && !line.startsWith("+++")) ? "add"
              : (line.startsWith("-") && !line.startsWith("---")) ? "del" : "";
      var safe = line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      return cls ? '<span class="' + cls + '">' + safe + "</span>" : safe;
    }).join("\n");
  }

  function commentBlock(tree, relpath, headings, selStartLine, excerpt) {
    var h = null;
    for (var i = 0; i < headings.length; i++) {
      if (headings[i].line <= selStartLine) h = headings[i]; else break;
    }
    var anchor = h ? "#" + h.text : "";
    var quoted = excerpt.split("\n").map(function (l) { return "> " + l; }).join("\n");
    return "[" + tree + ":" + relpath + anchor + "]\n" + quoted;
  }

  // Pure state→presentation mappings (unit-tested here; used by the board + doc renderers below).
  function stName(state) {                          // R5: canonical 整体状态 name; ?/empty → distinct "unknown"
    var s = String(state).toLowerCase();
    if (s === "?" || s === "" || s === "unknown") return "unknown";
    return /^(active|done|blocked|paused|todo|backlog|dropped)$/.test(s) ? s : "backlog";
  }
  function stepFill(state) {                         // R4: phase state → gate-track node fill (done/doing/pending)
    var s = String(state).toLowerCase().trim();
    if (!s || /^(—|\?|planned|not-started)(\s|$)/.test(s)) return "pending";   // prefix: a lite cell carries a ` · Req n / 已验证 k` tail
    if (/^(drafting|draft|active|implementing|in-progress|doing|todo|testing|blocked|failing|executing|closing)/.test(s)) return "doing";
    return "done";
  }
  var STATUS_TONE = { frozen: "done", approved: "done", confirmed: "done", baseline: "done", passing: "done",
    done: "done", active: "active", "in-progress": "active", drafting: "paused", draft: "paused",
    blocked: "blocked", superseded: "backlog" };
  function statusTone(s) { return STATUS_TONE[String(s).toLowerCase()] || "backlog"; }   // R3: doc-status → pill tone

  // 006: scope-safe persist merge — saved' = (saved − present) ∪ open. `present` is the set of
  // folder keys in the current render: a scoped/filtered render must only rewrite the keys it can
  // see, or persisting under a project scope wipes every other project's saved open state. Also
  // what makes stray async-toggle persists idempotent (they re-write the state they just applied).
  function mergeTreeOpen(saved, present, open) {
    var inPresent = {}, out = [], seen = {};
    present.forEach(function (k) { inPresent[k] = 1; });
    saved.forEach(function (k) { if (!inPresent[k] && !seen[k]) { seen[k] = 1; out.push(k); } });
    open.forEach(function (k) { if (!seen[k]) { seen[k] = 1; out.push(k); } });
    return out;
  }

  // 006: pick the band rect for a click at `y` — the SMALLEST rect containing y, not the first.
  // Range client rects list container border boxes (tbody / li / blockquote children) before their
  // text-line rects, so "first containing" always lands on the enclosing box. ±2px edge tolerance.
  function pickLineRect(rects, y) {
    if (!rects.length) return null;
    if (y == null) return rects[0];
    var best = null;
    for (var i = 0; i < rects.length; i++) {
      var r = rects[i];
      if (y >= r.top - 2 && y <= r.bottom + 2 && (!best || r.height < best.height)) best = r;
    }
    return best || rects[0];
  }

  // 007: drawer task summary — counts over server-parsed rows (done judged server-side, R3).
  function taskCounts(tasks) {
    var done = 0;
    (tasks || []).forEach(function (t) { if (t.done) done++; });
    return { done: done, total: (tasks || []).length };
  }
  function taskTone(t) {                             // 007: task-row status → badge tone
    if (t.done) return "done";
    var s = String(t.status || "").toLowerCase();
    if (/block|\[!\]|fail/.test(s)) return "blocked";
    if (/doing|active|wip|进行/.test(s)) return "active";
    return "backlog";
  }
  // 007 R4/R7: per-R presence → five display cells. commit is four-valued; "unchecked"
  // (no repo anchor) maps to "na", never to a gap.
  var COMMIT_CELL = { strict: "ok", loose: "q", none: "miss", unchecked: "na" };
  function traceCells(row) {
    var p = (row && row.present) || {};
    return [
      { k: "design", state: p.design ? "ok" : "miss" },
      { k: "verify", state: p.verify ? "ok" : "miss" },
      { k: "task", state: p.task ? "ok" : "miss" },
      { k: "test", state: p.test ? "ok" : "miss" },
      { k: "commit", state: COMMIT_CELL[p.commit] || "na" },
    ];
  }

  // 007: drawer one-line summary — rows with ≥1 real gap (loose/unchecked commit is a hint, not a gap).
  function traceGaps(rows) {
    var n = 0;
    (rows || []).forEach(function (r) {
      if (traceCells(r).some(function (c) { return c.state === "miss"; }) ||
          (r.flags || []).indexOf("not-in-需求条目") !== -1) n++;
    });
    return n;
  }

  // 010: card-drawer "Decisions" rows from the ledger (active blocks only; "" = no ledger).
  function escd(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  // ---- code highlighting (source view, fenced blocks): one html string per line, a few token classes, state carried across lines ----
  var HL_KW = {};
  ("if else elif for while do return break continue def class import from as with try except finally raise func function var let const "
    + "new this self None True False null true false nil package type struct interface map chan go defer switch case default in is not and "
    + "or lambda yield async await pass global export extends static public private protected void int char long unsigned bool string fi "
    + "then esac done local select from where insert update delete create table into values join on by group order").split(" ")
    .forEach(function (w) { HL_KW[w] = 1; });
  var HL_LANG = { hash: /^(py|python|sh|bash|zsh|shell|console|rb|ruby|pl|r|yaml|yml|toml|conf|cfg|ini|mk|make|cmake|dockerfile)$/,
    slash: /^(js|javascript|mjs|cjs|ts|typescript|tsx|jsx|go|golang|c|h|cc|cpp|c\+\+|hpp|java|rs|rust|swift|kt|scala|css|scss|proto)$/, dash: /^(sql|plpgsql|lua|hs)$/ };
  function hlKind(ext) {
    ext = String(ext || "").toLowerCase();
    if (ext === "md" || ext === "markdown") return "md";
    if (ext === "json" || ext === "jsonl") return "json";
    for (var k in HL_LANG) if (HL_LANG[k].test(ext)) return k;
    return "";
  }
  function hsp(cls, s) { return s ? '<span class="' + cls + '">' + escd(s) + "</span>" : ""; }
  var HL_STR = "\"(?:[^\"\\\\]|\\\\.)*\"?|'(?:[^'\\\\]|\\\\.)*'?|`(?:[^`\\\\]|\\\\.)*`?";
  var HL_RE = {
    hash: new RegExp("()(#)|(" + HL_STR + ")|(\\b\\d[\\w.]*)|([A-Za-z_]\\w*)", "g"),
    slash: new RegExp("(\\/\\*)|(\\/\\/)|(" + HL_STR + ")|(\\b\\d[\\w.]*)|([A-Za-z_]\\w*)", "g"),
    dash: new RegExp("()(--)|(" + HL_STR + ")|(\\b\\d[\\w.]*)|([A-Za-z_]\\w*)", "g"),
    json: new RegExp("()()(" + HL_STR + ")|(-?\\b\\d[\\w.]*)|([A-Za-z_]\\w*)", "g"),
  };
  function hlCode(line, st, kind) {
    var out = "", last = 0, re = HL_RE[kind], m, cls;
    if (st.blk) {
      var e = line.indexOf("*/"); if (e < 0) return hsp("hl-c", line);
      out = hsp("hl-c", line.slice(0, e + 2)); last = e + 2; st.blk = false;
    }
    if (kind === "hash" && /^\s*[\w.-]+\s*[:=]/.test(line) && last === 0) {   // a config key
      var k = /^(\s*)([\w.-]+)/.exec(line); out = escd(k[1]) + hsp("hl-a", k[2]); last = k[0].length;
    }
    re.lastIndex = last;
    while ((m = re.exec(line))) {
      out += escd(line.slice(last, m.index));
      if (m[1]) {
        var end = line.indexOf("*/", m.index + 2);
        if (end < 0) { st.blk = true; return out + hsp("hl-c", line.slice(m.index)); }
        out += hsp("hl-c", line.slice(m.index, end + 2)); last = re.lastIndex = end + 2; continue;
      }
      if (m[2]) return out + hsp("hl-c", line.slice(m.index));
      if (m[3]) cls = kind === "json" && /^\s*:/.test(line.slice(m.index + m[3].length)) ? "hl-a" : "hl-s";
      else if (m[4]) cls = "hl-n";
      else cls = HL_KW[m[5]] || HL_KW[m[5].toLowerCase()] && kind === "dash" ? "hl-k" : "";
      out += cls ? hsp(cls, m[0]) : escd(m[0]); last = re.lastIndex;
    }
    return out + escd(line.slice(last));
  }
  var MD_INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[\[[^\]]+\]\]|\[[^\]]*\]\([^)]*\))|(<!--.*?-->)/g;
  function hlMd(line, st, i) {
    if (i === 0 && line === "---") { st.fm = true; return hsp("hl-m", line); }
    if (st.fm) {
      if (line === "---") { st.fm = false; return hsp("hl-m", line); }
      var k = /^(\s*)([\w.-]+)(:)/.exec(line);
      return k ? escd(k[1]) + hsp("hl-a", k[2]) + escd(line.slice(k[1].length + k[2].length)) : escd(line);
    }
    var f = /^\s*(```|~~~)\s*([\w+-]*)/.exec(line);
    if (f) { st.fence = st.fence ? null : { kind: hlKind(f[2]), st: {} }; return hsp("hl-m", line); }
    if (st.fence) return st.fence.kind && st.fence.kind !== "md" ? hlCode(line, st.fence.st, st.fence.kind) : hsp("hl-q", line);
    if (st.com || /^\s*<!--/.test(line) && line.indexOf("-->") < 0) { st.com = line.indexOf("-->") < 0; return hsp("hl-c", line); }
    if (/^#{1,6}\s/.test(line)) return hsp("hl-h", line);
    var out = "", last = 0, m, lead = /^(\s*)([-*+]|\d+[.)]|>)(\s+\[[ xX]\])?(?=\s|$)/.exec(line);
    if (lead) { out = escd(lead[1]) + hsp("hl-m", lead[2] + (lead[3] || "")); last = lead[0].length; }
    MD_INLINE.lastIndex = last;
    while ((m = MD_INLINE.exec(line))) {
      out += escd(line.slice(last, m.index));
      out += hsp(m[1] ? "hl-s" : m[2] ? "hl-b" : m[3] ? "hl-l" : "hl-c", m[0]); last = MD_INLINE.lastIndex;
    }
    return out + escd(line.slice(last));
  }
  function hlLines(text, ext) {
    var kind = hlKind(ext), st = {}, lines = String(text).replace(/\n$/, "").split("\n");
    return lines.map(function (l, i) { return kind === "md" ? hlMd(l, st, i) : kind ? hlCode(l, st, kind) : escd(l); });
  }

  function decisionRows(decisions) {
    if (!decisions || !decisions.length) return "";
    var pend = decisions.filter(function (d) { return d.state !== "approved"; }).length;
    var head = '<div class="cd-row"><span class="cd-k">Decisions</span><span class="cd-v">' +
      decisions.length + (pend ? ' · <span class="trcell q">待评审 ' + pend + "</span>"
                               : ' · <span class="trcell ok">全批</span>') + "</span></div>";
    return head + decisions.map(function (d) {
      if (d.state === "conflict")   // dup-active: never render a winner (ADR-0001 D3)
        return '<div class="cd-row cd-dec"><span class="cd-k">' + escd(d.id) + '</span><span class="cd-v">' +
          '<span class="trcell miss">⚠ 冲突(dup-active)</span> <span class="cd-src">' + escd(d.level) + "</span></span></div>";
      var ok = d.state === "approved";
      return '<div class="cd-row cd-dec"><span class="cd-k">' + escd(d.id) + '</span><span class="cd-v">' +
        '<span class="trcell ' + (ok ? "ok" : "q") + '">' + (ok ? "✓" : "●") + " " + escd(d.state) + "</span>" +
        ' <span class="cd-src">' + escd(d.level) + "</span> " + escd(d.text || "") + "</span></div>";
    }).join("");
  }

  // 017 D1: governance-mode badge for the board tile eyebrow + drawer bar. "" for legacy/none
  // (pre-017 cards stay unmarked); "invalid" renders warn so a typo'd field is visible on sight.
  function governanceBadge(g) {
    if (!g || g === "legacy") return "";
    return '<span class="badge gov' + (g === "invalid" ? " warn" : "") + '" title="governance mode">' + escd(g) + "</span>";
  }

  // R4: which heading-section covers a 1-based full-file line? headings are 0-based over the
  // frontmatter-stripped body; fmLines = lines the frontmatter block occupied. -1 = before first heading.
  function sectionForLine(headings, fileLine, fmLines) {
    if (!fileLine) return -1;
    var target = fileLine - 1 - (fmLines || 0), idx = -1;
    for (var i = 0; i < (headings || []).length; i++) { if (headings[i].line <= target) idx = i; else break; }
    return idx;
  }

  // R5: build a merged, block-level diff render plan.
  //   spans     = per top-level block source-line span {start, end} (0-based body lines, end exclusive)
  //   addedBody = 0-based body line numbers that are additions
  //   dels      = [{at, lines}] removed-line groups (at = 0-based body line they preceded)
  // Returns ordered segments — {del:[lines]} · {add:true, from, to} · {plain:true, from, to}
  // (from/to = inclusive block-index range); contiguous same-state blocks merge into one segment.
  function diffSegments(spans, addedBody, dels) {
    var n = spans.length, added = {};
    (addedBody || []).forEach(function (l) { added[l] = 1; });
    var isAdd = spans.map(function (s) {
      for (var ln = s.start; ln < s.end; ln++) if (added[ln]) return true;
      return false;
    });
    function delBlock(at) { for (var i = 0; i < n; i++) if (spans[i].start >= at) return i; return n; }
    var delByBlock = {};
    (dels || []).forEach(function (d) { var b = delBlock(d.at); (delByBlock[b] = delByBlock[b] || []).push(d.lines); });
    var segs = [], i = 0;
    function flushDel(b) { (delByBlock[b] || []).forEach(function (lines) { segs.push({ del: lines }); }); }
    while (i < n) {
      flushDel(i);
      var state = isAdd[i], j = i + 1;
      while (j < n && isAdd[j] === state && !delByBlock[j]) j++;   // break a run where a del must be inserted
      segs.push(state ? { add: true, from: i, to: j - 1 } : { plain: true, from: i, to: j - 1 });
      i = j;
    }
    flushDel(n);
    return segs;
  }

  // T1 (016): clamp a dragged {left, width} measure box into [0, paneW] with a minimum width —
  // crossing (width < min) collapses to min width anchored at left; a pane narrower than min
  // degrades to filling the whole pane rather than overflowing it.
  function clampMeasure(left, width, paneW, min) {
    var maxW = Math.max(paneW, 0);
    min = Math.min(min, maxW);
    width = Math.min(Math.max(width, min), maxW);
    left = Math.min(Math.max(left, 0), maxW - width);
    return { left: left, width: width };
  }

  // T3 (016) [F8]: token → source-line span, one per rendered block. Skips 'space' tokens (no
  // DOM block) and a top-level HTML-comment token (marked.parse() turns it into a Comment node,
  // not an Element child — counting it desyncs spans.length from the actual block count).
  function blockSpans(tokens) {
    var spans = [], ln = 0;
    (tokens || []).forEach(function (tk) {
      var lines = ((tk.raw || "").match(/\n/g) || []).length;
      var isComment = tk.type === "html" && /^<!--[\s\S]*-->$/.test((tk.raw || "").trim());
      if (tk.type !== "space" && !isComment) spans.push({ start: ln, end: ln + lines });
      ln += lines;
    });
    return spans;
  }
  // the source lines of blocks i0..i1, trailing blank lines dropped; a block before another ends on a newline, so its
  // end is exclusive, while the last block may not, so it runs to the end of the body
  function srcSlice(body, spans, i0, i1) {
    var lines = String(body).split("\n");
    return lines.slice(spans[i0].start, spans[i1 + 1] ? spans[i1].end : lines.length).join("\n").replace(/\s+$/, "");
  }
  function blockLineNumbers(spans, fmLines) {
    return (spans || []).map(function (s) { return s.start + (fmLines || 0) + 1; });
  }

  // T4 (016) S1: pure assembly of the normalized index text + its run table, from run "shells"
  // the caller already produced by walking idx.root's Text nodes and splitting each one into
  // non-whitespace/whitespace segments (DOM traversal stays in the caller; this is string-only).
  // A whitespace shell folds to exactly one space char in idx.text regardless of its original
  // length (`len`) — that length is kept on the run for offsetToNode to map back correctly.
  function buildIndexText(runs) {
    var text = "", out = [], at = 0;
    (runs || []).forEach(function (r) {
      out.push({ at: at, node: r.node, off: r.off, len: r.len, isSpace: !!r.isSpace });
      if (r.isSpace) { text += " "; at += 1; } else { text += r.text; at += r.text.length; }
    });
    return { text: text.toLowerCase(), runs: out };
  }
  // S2: non-overlapping, document-order hit scan. Case-sensitive — the caller normalizes both
  // idx.text and the query to lowercase before calling, once, at the index/query boundary.
  function scanHits(text, needle) {
    if (!needle) return [];
    var hits = [], i = 0, at;
    while ((at = text.indexOf(needle, i)) !== -1) { hits.push([at, at + needle.length]); i = at + needle.length; }
    return hits;
  }
  // S1: normalized-text offset → {node, nodeOff}. A whitespace run's idx.text span is always
  // exactly 1 char, so `off - r.at` is always 0 there — the formula below lands on the run's own
  // original start without a separate isSpace branch (never off+len, which would swallow the
  // folded whitespace into a Range's boundary).
  function offsetToNode(runs, off) {
    var list = runs || [];
    for (var i = 0; i < list.length; i++) {
      var r = list[i], w = r.isSpace ? 1 : r.len;
      if (off >= r.at && off < r.at + w) return { node: r.node, nodeOff: r.off + (off - r.at) };
    }
    return null;
  }
  // T6: next/previous hit index, wrapping at both endpoints. cur === -1 (no current yet) treats
  // "next" as starting at the first hit and "previous" as starting at the last one — the natural
  // default pairing rather than an arbitrary single starting point.
  function stepHitIndex(cur, total, dir) {
    if (!total) return -1;
    if (cur < 0) return dir < 0 ? total - 1 : 0;
    return ((cur + dir) % total + total) % total;
  }
  // S3: a view's memory key. Pane-prefixed because two panes on the same file are the point of a
  // split view — a single key would let them overwrite each other's position. Kept next to
  // histLabel: both are branch tables over view.kind, and they go stale together.
  function viewKey(side, view, project) {
    var v = view || {}, k = v.kind;
    if (k === "doc") return side + "|doc:" + v.tree + "/" + v.rel;
    if (k === "diff") return side + "|diff:" + v.card;
    if (k === "trace") return side + "|trace:" + v.card;
    if (k === "search") return side + "|search:" + v.q;
    if (k === "board") return side + "|board:" + (project || "");   // switching project changes the whole content
    if (k === "recent") return side + "|recent";
    return side + "|" + k;   // an unregistered kind still gets a key of its own rather than throwing
  }
  // the dropdown label. The file name alone is useless in dev_root, where nearly every
  // card ships a design.md — the parent dir is what tells two entries apart.
  function histLabel(v) {
    if (!v) return "?";
    if (v.kind === "doc") return "📄 " + String(v.rel || "").split("/").slice(-2).join("/");
    if (v.kind === "search") return "🔍 " + v.q;
    if (v.kind === "diff") return "± " + v.card;
    if (v.kind === "trace") return "🔗 " + v.card;
    return (v.kind === "recent" ? "commits" : "board");
  }
  // the per-pane visit list behind the dropdown — separate from the back/forward stack,
  // so a step back never drops what was opened after it. A revisit keeps its position: rows that
  // move under the cursor between two picks are what makes a reordering list unpickable.
  function mruPut(list, key, view, cap) {
    var out = list || [];
    if (out.some(function (x) { return x.key === key; })) return out;
    return [{ key: key, view: view }].concat(out).slice(0, cap || 20);
  }
  // S4: MRU put over {order, map}. The evicted key's entry goes with it — otherwise the cap bounds
  // the order list while the map grows forever.
  function recallPut(store, key, entry, cap) {
    var s = store && store.map ? store : { order: [], map: {} };
    var order = recentPush(s.order, key, cap || 50), map = {};
    order.forEach(function (k) { map[k] = k === key ? entry : s.map[k]; });
    return { order: order, map: map };
  }
  // S4/D5: the content anchor — block index plus a prefix of that block's text. The index alone
  // breaks on any edit above it; the prefix alone is ambiguous; together the index is a fast path
  // and the prefix is the rescue.
  function anchorOf(blockTexts, scrollIdx) {
    var list = blockTexts || [];
    if (scrollIdx < 0 || scrollIdx >= list.length) return null;
    return { b: scrollIdx, p: (list[scrollIdx] || "").slice(0, 40) };
  }
  function anchorFind(blockTexts, anchor) {
    var list = blockTexts || [];
    if (!anchor || !anchor.p) return -1;
    if (list[anchor.b] && list[anchor.b].indexOf(anchor.p) === 0) return anchor.b;
    for (var i = 0; i < list.length; i++) if (list[i].indexOf(anchor.p) === 0) return i;
    return -1;
  }
  // S5/D14: allocate from an occupancy table rather than by array index, so unpinning a middle
  // item leaves every other pin's color untouched. Past 4 pins colors repeat (R7: no cap, identity
  // is the highlighted word itself).
  function pinSlot(slotUsed, count) {
    var used = slotUsed || [];
    for (var i = 0; i < 4; i++) if (!used[i]) return i;
    return count % 4;
  }
  // S6: pixel-derived track position (design rejected a text-offset ratio — a large mermaid
  // diagram or wide table would make that ratio diverge from the true scroll position).
  function railTop(hitTop, rootTop, contentH, trackH) {
    if (!contentH) return 0;
    var top = (hitTop - rootTop) / contentH * trackH;
    return Math.max(0, Math.min(top, trackH - 2));
  }

  // ---- doc-native id anchors: definition-site parse + bracket-cite grammar ----
  // the id is what anchors a block, not its status word — lite cards write Chinese ones
  // (待验证 …), Inv blocks write none, and a Fact is a list item in facts.md, never a heading.
  var XID_ID = "(?:Req|HLD|LLD|Task|Ask|Eff|Fact|Crit|Layer|Inv)";
  var XID_HEAD = new RegExp("^(" + XID_ID + "-\\d+)(?![\\w-])\\s*(\\S*)");
  var XID_STATE = /^(proposed|approved|superseded|retired)$/;   // the four that still colour the dot
  // `(?!\()` keeps a citation that is already a markdown link — [ADR-0001](./adr/0001-x.md) — a link:
  // tokenizing the bracket alone would leave its target dangling as text.
  var XID_CITE = new RegExp("^\\[(" + XID_ID + "-\\d+)(-[a-z])?\\](?!\\()");
  function stepFace(label, state, governance) {   // 031: a lite card's one cell shows its status string on the face
    if (governance === "lite" && state) return { text: state, title: label + ": " + state };
    return { text: label, title: label + (state ? ": " + state : "") };
  }
  function xidHead(text) {
    var m = XID_HEAD.exec((text || "").trim());
    return m ? { id: m[1], state: XID_STATE.test(m[2]) ? m[2] : "" } : null;
  }
  // the file that by convention holds an id the current doc does not. Only Fact ids have
  // one (a card's facts.md); every other id is defined where it is used, so pointing elsewhere would
  // navigate away for nothing.
  function xidHomeRel(rel, id) {
    var parts = String(rel || "").split("/");
    if (!/^Fact-\d+$/.test(id || "")) return null;
    return parts.length > 2 && /^\d{3}-/.test(parts[1]) ? parts[0] + "/" + parts[1] + "/facts.md" : null;
  }
  function xidCite(src) {
    var m = XID_CITE.exec(src);
    return m ? { id: m[1], clause: m[2] || "", raw: m[0] } : null;
  }
  function xidCiteStart(src) {   // where the next citation could begin (marked's `start` hook)
    var m = new RegExp("\\[" + XID_ID + "-\\d").exec(src);
    return m ? m.index : -1;
  }

  // Board form: "grid" (card grid) · "kanban" · "table" (one row per card). The stored
  // preference wins; the old boolean key is read as one of the first two; null = no preference,
  // and the renderer then picks the table below the width breakpoint, the grid above it.
  function boardMode(stored, legacyKanban) {
    if (stored === "rows") return "table";   // the rows form was retired for the table
    if (stored === "grid" || stored === "kanban" || stored === "table") return stored;
    if (legacyKanban === "1") return "kanban";
    if (legacyKanban === "0") return "grid";
    return null;
  }
  // Newest mtime per card dir ("<project>/<NNN-slug>") from the dev tree's flat {path, mtime} list.
  function cardMtimes(entries) {
    var out = {};
    (entries || []).forEach(function (e) {
      var m = /^([^/]+\/\d{3}-[^/]+)\//.exec(e.path || ""); if (!m) return;
      if (!(out[m[1]] >= e.mtime)) out[m[1]] = e.mtime;
    });
    return out;
  }
  // A legacy card's current phase: the first step not yet done (its label), else the last one.
  function legacyPhase(steps) {
    var last = "";
    for (var i = 0; i < (steps || []).length; i++) {
      var s = steps[i], j = s.indexOf(":"), label = j === -1 ? s : s.slice(0, j), state = j === -1 ? "" : s.slice(j + 1);
      if (stepFill(state) !== "done") return label;
      last = label;
    }
    return last;
  }
  // A lite card's one step cell is "设计:<status> · Req n / 已验证 k"; the row shows "k/n", or the status when there are no Reqs yet.
  function liteProgress(steps) {
    var s = (steps || [])[0] || "", i = s.indexOf(":"), body = i === -1 ? s : s.slice(i + 1);
    var m = /Req (\d+) \/ 已验证 (\d+)/.exec(body);
    if (m) return m[2] + "/" + m[1];
    return body.split(" · ")[0];
  }

  // ---- added for the refined frontend (/v2); the classic shell uses cardView and reqHeads too ----
  // One /api/board card as the refined board reads it: lite Req counts, the six-phase fill (2 done ·
  // 1 doing · 0 pending), the lite status word, and "next" without its prefix.
  function cardView(c) {
    var lite = c.governance === "lite", steps = c.steps || [], s0 = steps[0] || "";
    var m = lite ? /Req (\d+) \/ 已验证 (\d+)/.exec(s0) : null, dir = String(c.dir || "");
    return { p: c.project, n: c.nnn, id: c.project + "/" + c.nnn, dirName: dir, dir: c.project + "/" + dir, slug: dir.replace(/^\d+-/, ""),
      st: stName(c.state), gov: c.governance || "legacy", lite: lite, req: m ? +m[1] : 0, ok: m ? +m[2] : 0,
      liteSt: lite ? (s0.split(":")[1] || "").split(" · ")[0].trim() : "",
      ph: steps.map(function (s) { var f = stepFill(s.slice(s.indexOf(":") + 1)); return f === "done" ? 2 : f === "doing" ? 1 : 0; }),
      steps: steps, next: String(c.effective_next || "").replace(/^next:\s*/, ""), now: c.now || "", block: c.blockers || "",
      deps: c.deps || "", branch: c.branch || "", repo: c.repo || "" };
  }
  // A facts.md's "### Fact-n …" blocks: {"Fact-n": "<the block, heading included>"}; the first one wins.
  function factBlocks(src) {
    var out = {}, re = /^### (Fact-\d+)[^\n]*\n([\s\S]*?)(?=^### |(?![\s\S]))/gm, m;
    while ((m = re.exec(String(src || "")))) if (!out[m[1]]) out[m[1]] = m[0];
    return out;
  }
  // A Fact block's one-line gist: its "- 事实:" field, else the body, markup and runs of space folded.
  function factGist(block) {
    var body = String(block || "").replace(/^### [^\n]*\n/, ""), m = /^- 事实[:：]\s*([^\n]*)/m.exec(body);
    return (m ? m[1] : body).replace(/[`*]/g, "").replace(/\s+/g, " ").trim();
  }
  // A lite design.md's commitment headings: "### Req-n <状态词> — <title>" → [{n, st, t}].
  function reqHeads(src) {
    var out = [], re = /^### Req-(\d+)\s+(\S+)\s*[—-]\s*(.+)$/gm, m;
    while ((m = re.exec(String(src || "")))) out.push({ n: m[1], st: m[2], t: m[3].trim() });
    return out;
  }
  // A TOC entry from a heading: the id's status word moves into a tick (已验证) or goes, and a
  // [VERIFIED] / [推断] tag becomes the tick or the 推 mark.
  function tocLabel(text) {
    var ok = false, inf = false, t = String(text || "").replace(/^#/, "").trim();
    t = t.replace(/^((?:Req|Inv|V|Q|Task)-\d+)\s+(已验证|待验证|已放弃|放弃|提议|待确认|已确认|进行中|已定|待做)\s*[—-]?\s*/, function (_, a, s) { ok = s === "已验证"; return a + " "; });
    t = t.replace(/\s*\[VERIFIED\]/, function () { ok = true; return ""; }).replace(/\s*\[(推断|INFERRED)\]/, function () { inf = true; return ""; });
    return { t: t, ok: ok, inf: inf };
  }
  // A card's `git diff` text split per file: [{name, lines: [{cls: "a"|"d"|"h"|"", text}]}].
  function diffFiles(text) {
    return String(text || "").split(/\n(?=diff --git )/).filter(function (s) { return s.trim(); }).map(function (f) {
      var m = /^diff --git a\/(\S+)/.exec(f);
      return { name: m ? m[1] : "", lines: f.split("\n").map(function (l) {
        return { cls: /^\+(?!\+\+)/.test(l) ? "a" : /^-(?!--)/.test(l) ? "d" : /^@@/.test(l) ? "h" : "", text: l }; }) };
    });
  }
  // GitHub-style heading anchor: lowercase, punctuation dropped, each whitespace a hyphen (never folded)
  function slug(text) {
    return String(text || "").trim().toLowerCase().replace(/[^\p{L}\p{N}\p{M}\s_-]/gu, "").replace(/\s/g, "-");
  }
  // `git log -p` output → one entry per commit: sha, date, subject, and the diff part only
  function splitCommits(text) {
    return String(text || "").split(/\n(?=commit [0-9a-f]{7,})/).filter(function (b) { return /^commit [0-9a-f]{7,}/.test(b); }).map(function (b) {
      var at = b.indexOf("\ndiff --git "), date = /\nDate:\s+(.+)/.exec(b), subj = /\n\n {4}(.+)/.exec(b);
      return { sha: /^commit ([0-9a-f]+)/.exec(b)[1], date: date ? date[1].trim() : "", subject: subj ? subj[1].trim() : "", diff: at < 0 ? "" : b.slice(at + 1) };
    });
  }
  // 043/044: the todo format is tools/todo-format.md, shared with todo.py (the only writer) and pinned by
  // todo-cases.json; only "- [ ] " / "- [x] " lines outside code fences are items. ASCII rules, like todo.py's.
  var TODO_RE = /^([ \t]*(?:[-*+]|[0-9]+[.)])[ \t]+\[)( |x|X)(\][ \t]+)([\s\S]*)$/;   // text: to the line's end, U+2028 too   // lead · mark · "] " · text — the marker is kept on edit
  var FENCE_RE = /^ {0,3}(`{3,}|~{3,})(.*)$/;
  // one backslash more (+1) or less (-1) before the list marker of a line that reads as an item without them
  var ESC_RE = /^([ \t]*)(?:(\\*)([-*+])|([0-9]+)(\\*)([.)]))([\s\S]*)$/;
  function shiftEscape(l, by) {
    var m = ESC_RE.exec(l); if (!m) return l;
    var run = m[3] ? m[2] : m[5];
    if (!TODO_RE.test(m[1] + (m[3] || m[4] + m[6]) + m[7]) || run.length + by < 0) return l;
    run = new Array(run.length + by + 1).join("\\");
    return m[1] + (m[3] ? run + m[3] : m[4] + run + m[6]) + m[7];
  }
  function parseTodo(text) {
    var out = [], fence = null, ls = String(text || "").replace(/^﻿/, "").replace(/\r\n?/g, "\n").split("\n");
    for (var i = 0; i < ls.length; i++) {
      var l = ls[i], f = FENCE_RE.exec(l);
      if (fence === null) {
        if (f && !(f[1].charAt(0) === "`" && f[2].indexOf("`") >= 0)) { fence = f[1]; continue; }
      } else {   // a fence closes on the same character, at least as long, with nothing after it
        if (f && f[1].charAt(0) === fence.charAt(0) && f[1].length >= fence.length && !f[2].trim()) fence = null;
        continue;
      }
      var m = TODO_RE.exec(l), tags = [];
      if (!m) continue;
      m[4].replace(/\[\[[^\]]*\]\]|\[[^\]]*\]\([^)]*\)/g, " ")   // a tag inside a link's text or target is not a tag
        .replace(/(^|[ \t])[@#]([A-Za-z0-9_.-]+)/g, function (all, sp, t) { if (tags.indexOf(t) < 0) tags.push(t); return all; });
      // continuation lines sit at the item's text column; a blank line counts when one follows; they are never fences
      var pad = new Array(m[1].length).join(" "), cont = function (x) { return x.slice(0, pad.length) === pad && !TODO_RE.test(x); };
      var raw = [], j = i + 1;
      for (; j < ls.length; j++) {
        if (cont(ls[j])) raw.push(ls[j].slice(pad.length));
        else if (ls[j] === "" && cont(ls.slice(j + 1).filter(function (x) { return x !== ""; })[0] || "")) raw.push("");
        else break;
      }
      var more = raw.map(function (x, k) { return shiftEscape(/  $/.test(x) && raw[k + 1] ? x.slice(0, -2) : x, -1); });
      out.push({ line: i, done: m[2] !== " ", text: m[4], tags: tags, depth: /^[ \t]*/.exec(m[1])[0].length, more: more });
      i = j - 1;
    }
    return out;
  }
  // line n of a todo file as todo.py reads it (byte order mark dropped, CRLF folded) — what a tick names
  function todoLine(text, n) { return String(text || "").replace(/^\ufeff/, "").replace(/\r\n?/g, "\n").split("\n")[n] || ""; }
  // 045: an item's Obsidian Tasks marks — ➕ created (date, maybe a time, maybe with seconds), 📅 due, ✅ done, ⏫ 🔼 🔽 priority (1 high
  // … 3 low, 0 none) — and its text with the marks taken out
  function todoMeta(text) {
    var t = String(text || ""), d = function (sym) { var m = new RegExp(sym + "[ \\t]*([0-9]{4}-[0-9]{2}-[0-9]{2})(?:[ \\t]+([0-9]{2}:[0-9]{2}(?::[0-9]{2})?))?").exec(t); return m ? m[1] + (m[2] ? " " + m[2] : "") : ""; };
    var p = /⏫/.test(t) ? 1 : /🔼/.test(t) ? 2 : /🔽/.test(t) ? 3 : 0;
    var plain = t.replace(TODO_MARKS, "").replace(/[ \t]{2,}/g, " ").replace(/^[ \t]+|[ \t]+$/g, "");
    return { created: d("➕"), due: d("📅").slice(0, 10), done: d("✅").slice(0, 10), prio: p, text: plain };
  }
  // 045: a mark's date or date-and-time as a local Date (a bare "YYYY-MM-DD" would otherwise parse as UTC midnight)
  function todoDate(s) { var d = new Date(String(s || "").length === 10 ? s + "T00:00" : String(s || "").replace(" ", "T")); return isNaN(d) ? null : d; }
  // 054: the board's time form — a history stamp ("YYYY-MM-DD HH:MM", local) as ms; a Req state word's kind
  function tmMs(s) { var d = todoDate(s); return d ? d.getTime() : NaN; }
  function tmKind(w) { w = String(w || ""); return /已验证/.test(w) ? "done" : /放弃|撤回/.test(w) ? "drop" : /失败|阻塞/.test(w) ? "bad" : /仅方案/.test(w) ? "plan" : "todo"; }
  var TM_SETTLED = /已验证|放弃|撤回/;
  // 054: a card's span: its first status (else its dir's first commit) to done when its last status is done (a card
  // reopened after done runs on), else, for a closed card, its dir's last commit; else now
  function tmRange(h, closed, now) {
    var st = (h && h.status) || [], done = st.length && st[st.length - 1].v === "done" ? st[st.length - 1] : null;
    var a = st.length ? tmMs(st[0].t) : h && h.first ? tmMs(h.first) : now;
    var b = done ? tmMs(done.t) : !st.length && closed && h && h.last ? tmMs(h.last) : now;
    return [Math.min(a, b), b];
  }
  // 054: a Req's life as intervals of one state word inside [lo, hi]: written → each change → settled; a settled one
  // stops there (end = its kind) until a later change opens it again; written already settled is a point
  function tmSpans(ev, lo, hi) {
    var out = [], w = null, a = 0;
    (ev || []).forEach(function (e) {
      var at = tmMs(e.t), to = e.type === "new" ? e.word || "" : e.to;
      if (e.type === "new" || (e.type === "word" && w === null)) {
        if (TM_SETTLED.test(to)) out.push({ a: at, b: at, k: tmKind(to), end: tmKind(to) }); else { w = to; a = at; }
      } else if (e.type === "word") {
        var x = { a: a, b: at, k: tmKind(w) }; out.push(x);
        if (TM_SETTLED.test(to)) { x.end = tmKind(to); w = null; } else { w = to; a = at; }
      } else if (e.type === "gone" && w !== null) { out.push({ a: a, b: at, k: tmKind(w) }); w = null; }
    });
    if (w !== null) out.push({ a: a, b: hi, k: tmKind(w) });
    return out.map(function (x) { return { a: Math.max(x.a, lo), b: Math.min(x.b, hi), k: x.k, end: x.end }; })
      .filter(function (x) { return x.b >= x.a; });
  }
  // 054: the card's status and every Req's state at one moment: the title as it was, the last change up to it
  function tmStateAt(h, t) {
    var cs = null, st = (h && h.status) || [], reqs = [];
    for (var i = 0; i < st.length && tmMs(st[i].t) <= t; i++) cs = st[i].v;
    Object.keys((h && h.reqs) || {}).forEach(function (n) {
      var w = null, title = "", last = null;
      h.reqs[n].forEach(function (e) {
        if (tmMs(e.t) > t) return;
        last = e;
        if (e.type === "new") { w = e.word || ""; title = e.title || ""; } else if (e.type === "word") w = e.to;
        else if (e.type === "title") title = e.to; else if (e.type === "gone") w = null;
      });
      if (w !== null) reqs.push({ n: +n, w: w, k: tmKind(w), title: title, last: last });
    });
    reqs.sort(function (a, b) { return a.n - b.n; });
    return { cs: cs, reqs: reqs };
  }
  // 045: an item's subtasks are the items right after it that sit deeper: [done, total], or null when it has none
  function todoProgress(items, i) {
    var n = 0, k = 0;
    for (var j = i + 1; j < items.length && items[j].depth > items[i].depth; j++) { n++; if (items[j].done) k++; }
    return n ? [k, n] : null;
  }
  // 044: a wikilink may name any doc by its path — dev_root by default, kb (also via wiki/ or raw/), or ext/<label>/…;
  // ".md" is optional; an html page names its ".html". resolveLink keeps the older, KB-only reading for the classic shell.
  function resolveWikiAny(href, treeSets) {
    var w = String(href).trim().match(/^\[\[(.+?)\]\]$/);
    if (!w) return null;
    var x = w[1].split("|")[0].split("#")[0].trim(), tree = "dev", m = x.match(/^(dev|kb|ext)\//);
    if (m) { tree = m[1]; x = x.slice(m[0].length); } else if (/^(wiki|raw)\//.test(x)) tree = "kb";
    var t = /\.(md|html)$/i.test(x) ? x : x + ".md", canon = treeSets[tree] && treeSets[tree].get(t.toLowerCase());
    return canon ? tree + ":" + canon : null;
  }
  // 045: how a list line continues on Enter — the next line's prefix (same indent, quote and bullet; an ordered number
  // +1; a task restarts unticked), and whether this item is empty (only its prefix and date marks), which ends the list
  // the marks spelled out: 📅 🔼 🔽 are astral, so a [character class] without the u flag would split them
  var TODO_MARKS = /(?:➕|📅|✅)[ \t]*[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[ \t]+[0-9]{2}:[0-9]{2}(?::[0-9]{2})?)?|⏫|🔼|🔽/g;
  var LIST_RE = /^(\s*(?:>\s?)*)(?:([-*+])|(\d+)([.)]))(\s+)(\[[ xX]\]\s+)?(.*)$/;
  function continueLine(line) {
    var m = LIST_RE.exec(line || "");
    if (!m) { var q = /^(\s*(?:>\s?)+)(.*)$/.exec(line || ""); return q ? { next: q[1], empty: !q[2].trim(), todo: false } : null; }
    var bullet = m[2] || (+m[3] + 1) + m[4], rest = m[7].replace(TODO_MARKS, "").trim();
    return { next: m[1] + bullet + m[5] + (m[6] ? "[ ] " : ""), empty: !rest, todo: !!m[6] };
  }
  function todoStamp(d, withSeconds) {   // "YYYY-MM-DD HH:MM[:SS]", local time — the Obsidian Tasks date with the minute
    var p = function (n) { return (n < 10 ? "0" : "") + n; };
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + " " + p(d.getHours()) + ":" + p(d.getMinutes()) + (withSeconds ? ":" + p(d.getSeconds()) : "");
  }
  // 046: the editor's todo button on one line — a task prefix on, or off, and a created mark when it turns on; the
  // caret keeps its place in the text (never inside the prefix, never past the end of the text before the mark)
  var LINE_PREFIX = /^(\s*)(?:>\s?|#{1,6}\s+|(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?)?/;
  function toggleTask(line, off, stamp) {
    var m = LINE_PREFIX.exec(line), lead = m[1], rest = line.slice(m[0].length), on = !/\[[ xX]\]/.test(m[0]);
    var mark = on && !/➕/.test(rest), text = mark ? rest.replace(/[ \t]+$/, "") : rest;   // no doubled space before the mark
    var head = lead + (on ? "- [ ] " : ""), body = mark ? text + " ➕ " + stamp : text;
    return { line: head + body, caret: head.length + Math.max(0, Math.min(off - m[0].length, text.length)) };
  }
  // 046: what a picked completion replaces and where the caret lands — an @project takes the rest of the word after
  // the caret and adds a space only when none follows; a [[doc]] takes a half-typed rest up to its ]] (not across
  // another link)
  function completeSpan(v, from, caret, kind, pick) {
    var rest = String(v).slice(caret), end, text;
    if (kind === "@") {
      end = caret + /^[\w.-]*/.exec(rest)[0].length;
      var spaced = v[end] === " " || v[end] === "\t";
      text = "@" + pick + (spaced ? "" : " ");
      return { start: from, end: end, text: text, caret: from + text.length + (spaced ? 1 : 0) };
    }
    var m = /^[^\[\]\n]*\]\]/.exec(rest);
    end = caret + (m ? m[0].length : 0); text = "[[" + pick + "]]";
    return { start: from, end: end, text: text, caret: from + text.length };
  }


  return { boardMode: boardMode, cardMtimes: cardMtimes, liteProgress: liteProgress, legacyPhase: legacyPhase,
           cardView: cardView, factBlocks: factBlocks, factGist: factGist, reqHeads: reqHeads, tocLabel: tocLabel, diffFiles: diffFiles, splitCommits: splitCommits, slug: slug,
           parseFrontmatter: parseFrontmatter, resolveLink: resolveLink, normalizePath: normalizePath, sectionForLine: sectionForLine, diffSegments: diffSegments,
           projectsFromTree: projectsFromTree, buildTree: buildTree, sortCmp: sortCmp, matchScore: matchScore, recentPush: recentPush, tocFromHeadings: tocFromHeadings,
           groupHits: groupHits, groupTraceRows: groupTraceRows, colorizeDiff: colorizeDiff, commentBlock: commentBlock,
           stName: stName, stepFill: stepFill, statusTone: statusTone, pickLineRect: pickLineRect,
           mergeTreeOpen: mergeTreeOpen, taskCounts: taskCounts, taskTone: taskTone,
           traceCells: traceCells, traceGaps: traceGaps, decisionRows: decisionRows,
           governanceBadge: governanceBadge, clampMeasure: clampMeasure,
           blockSpans: blockSpans, blockLineNumbers: blockLineNumbers, srcSlice: srcSlice, hlLines: hlLines,
           buildIndexText: buildIndexText, scanHits: scanHits, offsetToNode: offsetToNode, stepHitIndex: stepHitIndex,
           railTop: railTop, pinSlot: pinSlot,
           viewKey: viewKey, histLabel: histLabel, mruPut: mruPut, recallPut: recallPut, anchorOf: anchorOf, anchorFind: anchorFind,
           xidHead: xidHead, xidCite: xidCite, xidCiteStart: xidCiteStart, xidHomeRel: xidHomeRel, stepFace: stepFace,
           parseTodo: parseTodo, todoLine: todoLine, resolveWikiAny: resolveWikiAny,
           continueLine: continueLine, todoStamp: todoStamp, todoMeta: todoMeta, todoProgress: todoProgress,
           todoDate: todoDate, toggleTask: toggleTask, completeSpan: completeSpan,
           tmMs: tmMs, tmKind: tmKind, tmRange: tmRange, tmSpans: tmSpans, tmStateAt: tmStateAt };
})();
if (typeof module !== "undefined" && module.exports) module.exports = SV;
if (typeof window !== "undefined") window.SV = SV;
