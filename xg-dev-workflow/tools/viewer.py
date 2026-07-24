#!/usr/bin/env python3
"""viewer.py — a transient localhost server backing the `status` HTML viewer.

A thin, read-only, zero-parse server: it serves the static shell page (marked.js inlined),
the raw markdown of two trees (docs root + KB) under a realpath boundary, and data endpoints
(board / tree / diff / log) that reuse workflow-status.py's computation and git's own output.
All rendering lives in the shell's JS; the server never parses markdown/frontmatter/board.

Lives only in xg-dev-workflow/tools/ (not a synced copy). stdlib-only.

Security (R6): binds 127.0.0.1 only; every route checks the Host header is localhost
(DNS-rebinding guard); /raw and the tree scan are confined to the two roots by realpath;
the shell + vendored asset come from a hardcoded repo path, never a user path. Read-only:
no write endpoints, no disk writes, no cross-request state — Ctrl-C stops it clean.

Usage:
  viewer.py [--port N] [--no-browser] [--dev-root DIR] [--kb-root DIR]
"""
import http.server
import importlib.util
import json
import os
import posixpath
import re
import signal
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
VIEWER_DIR = TOOLS_DIR / "viewer"
SHELL_HTML = VIEWER_DIR / "shell.html"
ASSETS = {"marked.min.js": "text/javascript",     # filename allowlist for /assets/<name>
          "mermaid.min.js": "text/javascript"}    # served from the hardcoded VIEWER_DIR only
LOCALHOST_HOSTS = {"localhost", "127.0.0.1"}   # server binds 127.0.0.1 (IPv4 loopback) only
SNAPSHOT_GREP = "auto: data snapshot"
LOG_MAX = 100
SEARCH_MAX = 200                               # cap search hits (bounded response)


def _load_tool(filename, modname):
    """Import a hyphenated tool file (resolve-project.py / workflow-status.py) by path."""
    spec = importlib.util.spec_from_file_location(modname, str(TOOLS_DIR / filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_rp = _load_tool("resolve-project.py", "rp")
_ws = _load_tool("workflow-status.py", "ws")
_gw = _load_tool("gitweb-companion.py", "gwc")


def resolve_roots(dev_arg=None, kb_arg=None):
    cp = _rp.config_path()
    text = cp.read_text(encoding="utf-8") if cp.exists() else None
    dev = dev_arg or (_rp.parse_dev_root(text) if text is not None else _rp.DEFAULT_DEV_ROOT)
    kb = kb_arg or (_rp.parse_kb_root(text) if text is not None else _rp.DEFAULT_KB_ROOT)
    return (Path(os.path.expanduser(dev)).resolve(strict=False),
            Path(os.path.expanduser(kb)).resolve(strict=False))


def safe_join(root: Path, relpath: str):
    """Map a URL relpath to a file under root, or None if it escapes (traversal/symlink).

    Borrows SimpleHTTPRequestHandler.translate_path's sanitizer (unquote + normpath + drop
    '.'/'..'/dirname components) to get a relative fragment, then enforces the real boundary
    with resolve()+relative_to — the stdlib sanitizer does NOT resolve symlinks, so this
    realpath check is what rejects a symlink whose target escapes the root.
    """
    path = urllib.parse.unquote(relpath, errors="surrogatepass")
    path = posixpath.normpath(path)
    frag = Path()
    for part in path.split("/"):
        if part in ("", ".", ".."):
            continue
        if os.sep in part or (os.altsep and os.altsep in part):
            continue
        frag = frag / part
    try:
        real = (root / frag).resolve(strict=False)
        real.relative_to(root)              # ValueError = escaped root; also catches NUL bytes
    except (ValueError, OSError):
        return None
    return real


class Handler(http.server.BaseHTTPRequestHandler):
    dev_root: Path = None
    kb_root: Path = None
    gitweb_url: str = ""              # 003: companion base URL injected into the shell ("" = disabled)

    def log_message(self, fmt, *args):
        sys.stderr.write("viewer %s - %s\n" % (self.command, fmt % args))

    def _host_ok(self):
        host = self.headers.get("Host", "")
        return host.split(":")[0] in LOCALHOST_HOSTS

    def _send(self, code, body, ctype="text/plain; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionError):
            pass  # client navigated away mid-transfer (common on the multi-MB mermaid asset)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        if not self._host_ok():
            self._send(403, "forbidden: non-localhost Host\n")
            return
        parsed = urllib.parse.urlparse(self.path)
        path, qs = parsed.path, urllib.parse.parse_qs(parsed.query)
        if path == "/":
            self._serve_shell()
        elif path.startswith("/assets/"):
            self._serve_asset(path[len("/assets/"):])
        elif path.startswith("/raw/"):
            self._serve_raw(path)
        elif path == "/api/tree":
            self._serve_tree()
        elif path == "/api/board":
            self._serve_board()
        elif path == "/api/diff":
            self._serve_diff(qs.get("card", [""])[0])
        elif path == "/api/trace":
            self._serve_trace(qs.get("card", [""])[0])
        elif path == "/api/log":
            self._serve_log(qs.get("n", ["20"])[0])
        elif path == "/api/search":
            self._serve_search(qs.get("q", [""])[0], qs.get("project", [""])[0])
        elif path == "/api/rev":
            self._serve_rev(qs.get("path", [""])[0])
        elif path == "/api/filelog":
            self._serve_filelog(qs.get("path", [""])[0])
        elif path == "/api/filediff":
            self._serve_filediff(qs.get("path", [""])[0], qs.get("sha", [""])[0])
        else:
            self._send(404, "not found\n")

    def _serve_shell(self):
        try:
            html = SHELL_HTML.read_text(encoding="utf-8")
        except OSError as e:
            self._send(500, "shell missing: %s\n" % e)
            return
        # R63/003: inject the gitweb companion URL (empty when disabled → shell hides the code links)
        html = html.replace("__GITWEB_URL__", self.gitweb_url)
        self._send(200, html, "text/html; charset=utf-8")

    def _serve_asset(self, name):
        # vendored JS from the hardcoded VIEWER_DIR by an exact-name allowlist — never a user path.
        ctype = ASSETS.get(name)
        if ctype is None:
            self._send(404, "not found\n")
            return
        try:
            self._send(200, (VIEWER_DIR / name).read_bytes(), ctype + "; charset=utf-8")
        except OSError:
            self._send(404, "not found\n")

    def _serve_raw(self, path):
        # /raw/{dev|kb}/<relpath> → file bytes, confined to the requested root.
        m = re.match(r"^/raw/(dev|kb)/(.*)$", path)
        if not m:
            self._send(404, "not found\n")
            return
        which, relpath = m.group(1), m.group(2)
        root = self.dev_root if which == "dev" else self.kb_root
        if not relpath.endswith(".md"):        # viewer serves markdown only
            self._send(404, "not found\n")
            return
        real = safe_join(root, relpath)         # None = traversal / out-of-root symlink
        if real is None or not real.is_file():
            self._send(404, "not found\n")      # same code: don't leak existence
            return
        try:
            data = real.read_text(encoding="utf-8")
        except OSError:
            self._send(404, "not found\n")
            return
        try:
            mt = int(real.stat().st_mtime * 1000)      # R63: lets the client detect a doc update
        except OSError:
            mt = 0
        self._send(200, data, extra={"X-Mtime": str(mt)})

    def _serve_tree(self):
        # Two-root *.md manifest (root-relative posix); the boundary applies here too:
        # followlinks=False + realpath confinement, so an out-of-root symlink target never
        # leaks a filename into the listing.
        self._json({"dev": scan_tree(self.dev_root, with_mtime=True),
                    "kb": scan_tree(self.kb_root, with_mtime=True)})

    def _serve_board(self):
        grouped = {}
        for c in _ws.iter_cards(str(self.dev_root)):
            grouped.setdefault(c["project"], []).append(c)
        self._json(grouped)

    def _serve_diff(self, card):
        base, card_dir, err = resolve_card(self.dev_root, card)
        if err:
            self._send(400, "bad card id: %s\n" % err)
            return
        rel = card_dir.relative_to(self.dev_root).as_posix()
        if base is None:                          # no deliberate commit yet → whole dir as new
            out = _diff_untracked(self.dev_root, rel)
        else:
            out = _git(self.dev_root, "-c", "core.quotepath=false", "diff", base, "--", rel)
        self._send(200, out or "(no changes since %s)\n" % (base or "card start"))

    def _serve_trace(self, card):
        # 007: always 200 + pinned-schema JSON with an `error` field — a non-2xx here
        # would surface as the shell's broken pane instead of the drawer's empty state.
        proj, _nnn, card_dir, err = _locate_card(self.dev_root, card)
        if err:
            self._json(_trace_empty(card, err))
            return
        try:
            self._json(_ws.trace_data(proj, str(card_dir)))
        except Exception as e:
            self._json(_trace_empty(card, "trace failed: %s" % e))

    def _serve_log(self, n):
        try:
            n = max(1, min(LOG_MAX, int(n)))
        except (TypeError, ValueError):
            n = 20
        out = _git(self.dev_root, "-c", "core.quotepath=false", "log", "-p",
                   "--invert-grep", "--grep=" + SNAPSHOT_GREP, "-n", str(n))
        self._send(200, out or "(no commits)\n")

    def _serve_search(self, q, project):
        q = (q or "").strip()
        if len(q) < 2:                              # avoid scanning the whole corpus on 1 char
            self._json({"hits": [], "note": "query too short"})
            return
        hits = search_trees({"dev": self.dev_root, "kb": self.kb_root}, q, project or None)
        self._json({"hits": hits[:SEARCH_MAX], "truncated": len(hits) > SEARCH_MAX})

    def _serve_rev(self, p):
        # R63: change signal for live refresh. ?path=<tree>/<rel> → that file's mtime (ms);
        # no path → a cheap 'did anything change?' token per tree (see _rev_token).
        if not p:
            self._json({"dev": _rev_token(self.dev_root), "kb": _rev_token(self.kb_root)})
            return
        m = re.match(r"^(dev|kb)/(.*)$", p)
        root = self.dev_root if (m and m.group(1) == "dev") else self.kb_root
        real = safe_join(root, m.group(2)) if m else None
        mt = 0
        if real is not None and real.is_file():
            try:
                mt = int(real.stat().st_mtime * 1000)
            except OSError:
                mt = 0
        self._json({"mtime": mt})

    def _serve_filelog(self, p):
        # R5: per-file commit history (excludes auto data-snapshots) → JSON for the viewer's change list.
        m = re.match(r"^(dev|kb)/(.*)$", p or "")
        if not m or not m.group(2).endswith(".md"):
            self._json({"commits": []})
            return
        root = self.dev_root if m.group(1) == "dev" else self.kb_root
        real = safe_join(root, m.group(2))             # validate AND use the confined path (as _serve_raw does)
        if real is None:                               # traversal / out-of-root → empty, don't leak
            self._json({"commits": []})
            return
        rel = real.relative_to(root).as_posix()
        out = _git(root, "-c", "core.quotepath=false", "log",
                   "--invert-grep", "--grep=" + SNAPSHOT_GREP,
                   "--format=%H%x1f%s%x1f%cs", "-n", str(LOG_MAX), "--", rel)
        commits = []
        for line in out.splitlines():
            parts = line.split("\x1f")
            if len(parts) == 3:
                commits.append({"sha": parts[0], "subject": parts[1], "date": parts[2]})
        self._json({"commits": commits})

    def _serve_filediff(self, p, sha):
        # R5: one commit's change to one file → the after-version + parsed add/del line info (JSON).
        m = re.match(r"^(dev|kb)/(.*)$", p or "")
        empty = {"after": "", "adds": [], "dels": []}
        if not m or not m.group(2).endswith(".md") or not re.fullmatch(r"[0-9a-fA-F]{4,64}", sha or ""):
            self._json(empty)
            return
        root = self.dev_root if m.group(1) == "dev" else self.kb_root
        real = safe_join(root, m.group(2))             # validate AND use the confined path (as _serve_raw does)
        if real is None:                               # traversal / out-of-root
            self._json(empty)
            return
        rel = real.relative_to(root).as_posix()
        after = _git(root, "-c", "core.quotepath=false", "show", "%s:%s" % (sha, rel))
        patch = _git(root, "-c", "core.quotepath=false", "show", "--format=", "-p", "--no-color", sha, "--", rel)
        adds, dels = _parse_file_patch(patch)
        self._json({"after": after, "adds": adds, "dels": dels})


def _parse_file_patch(patch):
    """Parse a single-file unified diff → (added after-line numbers, [{at, lines}] removed groups).
    Line numbers are 1-based over the after-file; a removed group's `at` is the after-line it precedes."""
    adds, dels, after_ln, started, cur = [], [], 0, False, None
    for line in (patch or "").splitlines():
        if line.startswith("@@"):
            mm = re.search(r"\+(\d+)", line)
            after_ln = int(mm.group(1)) if mm else after_ln
            started, cur = True, None
            continue
        if not started:
            continue
        tag = line[:1]
        if tag == "+":
            adds.append(after_ln); after_ln += 1; cur = None
        elif tag == "-":
            if cur is None:
                cur = {"at": after_ln, "lines": []}; dels.append(cur)
            cur["lines"].append(line[1:])
        elif tag == "\\":
            pass                                       # "\ No newline at end of file"
        else:
            after_ln += 1; cur = None                  # context line
    return adds, dels


def _trace_empty(card, err):
    """Pinned /api/trace shape (fields always present) for the error path."""
    return {"card": card or "", "repo": "", "repo_anchor": False,
            "generated_at": "", "rows": [], "orphans": [], "error": err}


def _rev_token(root: Path):
    """Change token for live refresh (R63): "<newest .md mtime ms>.<.md count>" under root.
    The count makes deletions flip the token too — max-mtime alone misses removing a non-newest file."""
    best = n = 0
    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        for fn in filenames:
            if fn.endswith(".md"):
                n += 1
                try:
                    best = max(best, int((Path(dirpath) / fn).stat().st_mtime * 1000))
                except OSError:
                    pass
    return "%d.%d" % (best, n)


def scan_tree(root: Path, with_mtime=False):
    out = []
    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            real = (Path(dirpath) / fn).resolve(strict=False)
            try:
                rel = real.relative_to(root).as_posix()
            except ValueError:
                continue  # symlink escaping the root — don't list it
            if with_mtime:
                try:
                    out.append({"path": rel, "mtime": real.stat().st_mtime})
                except OSError:
                    out.append({"path": rel, "mtime": 0})
            else:
                out.append(rel)
    return sorted(out, key=lambda x: x["path"] if with_mtime else x)


def _in_project(relpath, project):
    # dev: <proj>/…  ·  kb: raw/<proj>/… | wiki/<proj>/…  → project is a path segment either way.
    return project in relpath.split("/")


def search_trees(roots, q, project):
    """Case-insensitive substring search over *.md in both trees: content lines + filenames.

    Returns [{tree, path, line, snippet}] where a zero line number marks a filename match.
    Bounded by the caller.
    """
    ql = q.lower()
    hits = []
    for tree, root in roots.items():
        for rel in scan_tree(root):
            if project and not _in_project(rel, project):
                continue
            if ql in rel.lower():                    # filename match
                hits.append({"tree": tree, "path": rel, "line": 0, "snippet": rel})
            try:
                text = (root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if ql in line.lower():
                    hits.append({"tree": tree, "path": rel, "line": i,
                                 "snippet": line.strip()[:200]})
                    if len(hits) > SEARCH_MAX:
                        return hits
    return hits


def _card_dir(dev_root: Path, proj, nnn):
    matches = sorted((dev_root / proj).glob(nnn + "-*"))
    return matches[0].resolve(strict=False) if matches else None


def _locate_card(dev_root: Path, card: str):
    """Validate '<proj>/<NNN>' and locate its card dir. Returns (proj, nnn, dir, err).

    Shared by /api/diff (which adds the gate-commit base) and /api/trace (which must
    not pay _gate_commit's git call — 007 design)."""
    m = re.match(r"^([^/]+)/(\d{3})$", card or "")
    if not m:
        return None, None, None, "expected <project>/<NNN>"
    proj, nnn = m.group(1), m.group(2)
    cp = _rp.config_path()
    text = cp.read_text(encoding="utf-8") if cp.exists() else ""
    if proj not in {name for name, _ in _rp.parse_projects(text)}:
        return None, None, None, "unregistered project"
    card_dir = _card_dir(dev_root, proj, nnn)
    if card_dir is None:
        return None, None, None, "no such card dir"
    try:
        card_dir.relative_to(dev_root)
    except ValueError:
        return None, None, None, "card dir escapes dev_root"
    return proj, nnn, card_dir, None


def resolve_card(dev_root: Path, card: str):
    """Validate '<proj>/<NNN>' and locate its card dir + diff base. Returns (base, dir, err)."""
    proj, nnn, card_dir, err = _locate_card(dev_root, card)
    if err:
        return None, None, err
    return _gate_commit(dev_root, proj, nnn, card_dir), card_dir, None


def _gate_commit(dev_root: Path, proj, nnn, card_dir):
    """Latest non-snapshot commit whose subject is prefixed '<proj>/<NNN>' + a separator.

    'gate' here = latest deliberate card commit (phase-closing gates aren't distinguishable
    from routine card commits by subject alone). During active work this surfaces
    since-last-commit + worktree changes.
    """
    rel = card_dir.relative_to(dev_root).as_posix()
    out = _git(dev_root, "log", "--format=%H%x00%s", "--", rel)
    pat = re.compile(r"^%s/%s[:\-\s]" % (re.escape(proj), nnn))
    for line in out.splitlines():
        h, _, subj = line.partition("\x00")
        if SNAPSHOT_GREP in subj:
            continue
        if pat.match(subj):
            return h
    return None


def _diff_untracked(dev_root: Path, rel):
    """All-new / all-snapshot card: show each file under the dir as an addition."""
    parts = []
    for f in sorted((dev_root / rel).rglob("*")):
        if f.is_file():
            parts.append(_git(dev_root, "-c", "core.quotepath=false", "diff",
                              "--no-index", os.devnull, str(f)))
    return "".join(p for p in parts if p)


def _git(dev_root: Path, *args):
    try:
        r = subprocess.run(["git", "-C", str(dev_root), *args],
                           capture_output=True, text=True, timeout=15)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def serve(dev_root: Path, kb_root: Path, port=0, open_browser=True, gitweb=True, gitweb_port=None):
    Handler.dev_root = dev_root
    Handler.kb_root = kb_root
    companion = None
    if gitweb:                                  # 003: co-launch the read-only gitweb companion
        try:
            companion = _gw.start(gitweb_port or _gw.DEFAULT_PORT)
        except Exception as e:
            sys.stderr.write("gitweb companion error: %s\n" % e)
        if not companion:                       # require both up by default; --no-gitweb to opt out
            sys.stderr.write("gitweb companion failed to start — viewer + gitweb are both required; "
                             "pass --no-gitweb to run the viewer alone.\n")
            sys.exit(1)
        Handler.gitweb_url = "http://127.0.0.1:%d/" % companion["port"]
        print("gitweb companion on %s (%d repos)" % (Handler.gitweb_url, len(companion["repos"])), file=sys.stderr)
    else:
        Handler.gitweb_url = ""
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    url = "http://127.0.0.1:%d/" % httpd.server_address[1]
    print("status viewer on %s  (dev_root=%s, kb=%s)  — Ctrl-C to stop" %
          (url, dev_root, kb_root), file=sys.stderr)
    # serve_forever runs in a worker thread so the main thread can shut it down from a signal
    # handler (shutdown() must be called from a different thread). Installing the handlers
    # explicitly also overrides an inherited SIG_IGN (e.g. when launched backgrounded).
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        stop.wait()
    except KeyboardInterrupt:
        pass
    print("\nstopped.", file=sys.stderr)
    httpd.shutdown()
    httpd.server_close()
    if companion:
        _gw.stop(companion)


def main(argv):
    port, open_browser, dev_arg, kb_arg = 0, True, None, None
    gitweb, gitweb_port = True, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--port":
            port = int(argv[i + 1]); i += 2; continue
        if a == "--no-browser":
            open_browser = False
        elif a == "--no-gitweb":
            gitweb = False
        elif a == "--gitweb-port":
            gitweb_port = int(argv[i + 1]); i += 2; continue
        elif a == "--dev-root":
            dev_arg = argv[i + 1]; i += 2; continue
        elif a == "--kb-root":
            kb_arg = argv[i + 1]; i += 2; continue
        i += 1
    dev_root, kb_root = resolve_roots(dev_arg, kb_arg)
    serve(dev_root, kb_root, port=port, open_browser=open_browser, gitweb=gitweb, gitweb_port=gitweb_port)


if __name__ == "__main__":
    main(sys.argv[1:])
