#!/usr/bin/env python3
"""viewer.py — a transient localhost server backing the `status` HTML viewer.

A thin, read-only, zero-parse server: it serves the static shell page (marked.js inlined),
the raw markdown of two trees (docs root + KB) under a realpath boundary, the html pages in them
(with their css / js / images, under /page/<key>/), and data endpoints
(board / tree / diff / log) that reuse workflow-status.py's computation and git's own output.
All rendering lives in the shell's JS; the server never parses markdown/frontmatter/board.

Lives only in xg-dev-workflow/tools/ (not a synced copy). stdlib-only.

Security (R6): binds 127.0.0.1 only; every route checks the Host header is localhost
(--lan binds every interface and adds the LAN IP, plus any --host, to that allowlist)
(DNS-rebinding guard); /raw, /page and the tree scan are confined to the two roots by realpath;
a page from an untrusted extra root is served sandboxed (an opaque origin), and each trust class
of pages sits under its own per-run random key, so neither other sites nor an untrusted page can
address a trusted file;
the shell + vendored asset come from a hardcoded repo path, never a user path. Writes go only
to the todo files (through todo.py) and the extra-roots list; the one cross-request state is the
card-history cache, keyed by dev_root's HEAD and the design.md mtimes — Ctrl-C stops it clean.

Ports are fixed by default (viewer 8790; the gitweb companion on loopback 8791, served by the
viewer at /gitweb/) so one `ssh -L` rule for 8790 keeps working across restarts; a busy port is
reported and the run stops rather than degrading to a random port.

Usage:
  viewer.py [--port N] [--no-browser] [--no-gitweb] [--gitweb-port N] [--dev-root DIR] [--kb-root DIR]
            [--lan] [--host NAME]...
"""
import datetime
import errno
import http.client
import http.server
import importlib.util
import json
import os
import posixpath
import re
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
VIEWER_DIR = TOOLS_DIR / "viewer"
SHELL_HTML = VIEWER_DIR / "shell.html"            # the classic frontend, frozen, at /v1
SHELL_V2_HTML = VIEWER_DIR / "shell-v2.html"     # the frontend at /; /v2 stays as an alias for old bookmarks
ASSETS = {"marked.min.js": "text/javascript",     # filename allowlist for /assets/<name>
          "mermaid.min.js": "text/javascript",    # served from the hardcoded VIEWER_DIR only
          "sv.js": "text/javascript",
          "martian-mono.woff2": "font/woff2",
          "v2.css": "text/css", "v2-widths.css": "text/css", "v2-themes.css": "text/css", "v2-time.css": "text/css",
          **{"v2-%s.js" % a: "text/javascript" for a in ("core", "tree", "board", "time", "reader", "search", "find", "todo", "edit")}}
PAGE_TYPES = {".html": "text/html", ".htm": "text/html", ".css": "text/css", ".js": "text/javascript",   # what /page serves
              ".mjs": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
              ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
              ".ico": "image/x-icon", ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf"}
PAGE_SANDBOX = "sandbox allow-scripts allow-forms allow-popups allow-modals"   # no allow-same-origin: an opaque origin
LOCALHOST_HOSTS = {"localhost", "127.0.0.1"}   # the default bind (IPv4 loopback) and Host allowlist
ALLOWED_HOSTS = set(LOCALHOST_HOSTS)           # --lan adds the LAN IP and any --host names
# gitweb pages share the viewer's origin, so they may not send anything elsewhere (repo HTML is not rendered: $prevent_xss)
GITWEB_CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
              "connect-src 'self'; form-action 'self'; base-uri 'self'; frame-ancestors 'self'")
DEFAULT_PORT = 8790                            # fixed (gitweb sits on 8791) — an ssh -L rule outlives restarts
SNAPSHOT_GREP = "auto: data snapshot"
WORKTREE = "worktree"                            # the filelog/filediff pseudo-sha for uncommitted changes
TODO_DIR = "todo"                                # the viewer writes only <dev_root>/todo/<name>.md (043, 044)
EXT_SCAN_MAX = 5000                              # an extra root lists at most this many docs (hidden dirs and node_modules skipped)
TODO_MAX = 256 * 1024
LOG_MAX = 100
HISTORY_BULK = 6                                 # a commit touching more card dirs than this is a sweep, not work on them
SEARCH_MAX = 200                               # cap search hits (bounded response)


def _load_tool(filename, modname):
    """Import a hyphenated tool file (resolve-project.py / workflow-status.py) by path."""
    spec = importlib.util.spec_from_file_location(modname, str(TOOLS_DIR / filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_rp = _load_tool("resolve-project.py", "rp")
_todo = _load_tool("todo.py", "todo")   # the one writer of todo files: its lock, versions and line edits
_ws = _load_tool("workflow-status.py", "ws")
_gw = _load_tool("gitweb-companion.py", "gwc")


def resolve_roots(dev_arg=None, kb_arg=None):
    cp = _rp.config_path()
    text = cp.read_text(encoding="utf-8") if cp.exists() else None
    dev = dev_arg or (_rp.parse_dev_root(text) if text is not None else _rp.DEFAULT_DEV_ROOT)
    kb = kb_arg or (_rp.parse_kb_root(text) if text is not None else _rp.DEFAULT_KB_ROOT)
    return (Path(os.path.expanduser(dev)).resolve(strict=False),
            Path(os.path.expanduser(kb)).resolve(strict=False))


DAY_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
STAMP_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")
TAG_NAME_RE = re.compile(r"[A-Za-z0-9_.-]*")


def ok_todo_name(x):
    try:
        return isinstance(x, str) and bool(_todo.check_name(x))
    except _todo.TodoError:
        return False


def todo_body_ok(op, body):
    """The fields each todo op needs, with the types and shapes todo.py expects (dates in the page's local time)."""
    def str_(k):
        return isinstance(body.get(k), str)

    if op == "write":
        return str_("text")
    if op == "rename":
        return ok_todo_name(body.get("to"))
    if op == "delete":
        return True
    if op == "tick":
        return (type(body.get("line")) is int and body["line"] >= 0 and str_("text") and type(body.get("done")) is bool
                and str_("today") and bool(DAY_RE.fullmatch(body["today"])))
    if op == "append":
        return (str_("text") and body["text"].strip() != "" and str_("project") and bool(TAG_NAME_RE.fullmatch(body["project"]))
                and str_("link") and not re.search(r"\[\[|\]\]|[\r\n\u2028\u2029]", body["link"])
                and str_("stamp") and bool(STAMP_RE.fullmatch(body["stamp"])))
    return False


def migrate_todo(dev_root: Path):
    """043 kept todos in <dev_root>/todo.md; 044 keeps a directory of them. Move the old file in once."""
    old, tdir = dev_root / "todo.md", dev_root / TODO_DIR
    new = tdir / "inbox.md"
    if tdir.is_symlink() or (tdir.exists() and not tdir.is_dir()):   # the move must stay inside dev_root
        if old.is_file():
            print("left %s in place: %s is not a plain directory" % (old, tdir), file=sys.stderr)
        return
    movable = lambda: old.is_file() and not old.is_symlink() and not new.exists()
    if not movable():   # nothing to move: no lock taken, no todo/ made
        return
    with _todo.locked(str(tdir)):
        if movable():
            os.rename(old, new)
            print("moved %s to %s (todos are a directory now)" % (old, new), file=sys.stderr)


def root_allowed(real: Path):
    """A page-set root: strictly under the home directory, not inside a hidden directory or ~/Library (config and
    keys live there, and ~/Library is too big to walk on every refresh)."""
    home = Path.home().resolve()
    if real == home or home not in real.parents:
        return False
    parts = real.relative_to(home).parts
    return not any(x.startswith(".") for x in parts) and parts[0] != "Library"


def ui_roots_path():
    return _rp.config_path().parent / "viewer-roots.json"   # the viewer's own file; config.yaml is never rewritten


def ui_roots():
    try:
        roots = json.loads(ui_roots_path().read_text(encoding="utf-8")).get("roots", [])
        return [r for r in roots if isinstance(r, str)]
    except (OSError, ValueError, AttributeError):
        return []


def ui_trusted():
    """The extra roots marked trusted on the page (realpaths). An absent, old or broken file trusts none."""
    try:
        t = json.loads(ui_roots_path().read_text(encoding="utf-8")).get("trusted", [])
        return {x for x in t if isinstance(x, str)} if isinstance(t, list) else set()
    except (OSError, ValueError, AttributeError):
        return set()


def save_ui_roots(roots, trusted):
    f = ui_roots_path()
    f.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=f.parent, prefix=".viewer-roots.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as h:
            json.dump({"roots": roots, "trusted": sorted(trusted)}, h, ensure_ascii=False, indent=2)
        os.replace(tmp, f)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def extra_roots():
    """Config `extra_roots:` plus the page-set ones → ({label: Path}, {label: "config" | "page"}): directories whose
    docs the viewer also shows, read-only. A label is the directory name, suffixed when two collide; a missing
    directory is skipped, and one listed in both places counts once, as config."""
    cp = _rp.config_path()
    text = cp.read_text(encoding="utf-8") if cp.exists() else ""
    out, src, seen, have = {}, {}, set(), set()
    for p, where in [(p, "config") for p in _gw.parse_path_list(text, "extra_roots")] + [(p, "page") for p in ui_roots()]:
        root = Path(p).resolve(strict=False)
        if where == "page" and not root_allowed(root):   # re-checked on every load: a saved path may have become a link
            continue
        if root.is_dir() and root not in have:
            have.add(root)
            label = _gw._uniq(root.name, seen)
            out[label], src[label] = root, where
    return out, src


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
    ext_roots = {}                                   # label -> Path, from config `extra_roots:` and the page; read-only like dev and kb
    ext_from = {}                                    # label -> "config" | "page"
    ext_trusted = set()                              # realpaths of the extra roots marked trusted; the rest serve sandboxed
    # one key per trust class, in every /page URL: other sites cannot learn either (only same-origin /api/tree hands
    # them out), and an untrusted page knows only its own, so it can neither load a trusted file nor open a trusted page
    page_keys = {"t": secrets.token_urlsafe(12), "u": secrets.token_urlsafe(12)}
    repos = {}                                       # gitweb label -> git dir, the companion's repos (empty without gitweb)
    sha_home = {}                                    # sha -> repo label, filled by /api/shas (misses are not kept: the commit may come later)
    dev_root: Path = None
    kb_root: Path = None
    gitweb_port: int = 0              # 003: companion port; its URL is built per request from the Host used (0 = disabled)

    def log_message(self, fmt, *args):
        sys.stderr.write("viewer %s - %s\n" % (self.command, fmt % args))

    def _host_ok(self):
        host = self.headers.get("Host", "")
        return host.split(":")[0] in ALLOWED_HOSTS

    def gitweb_url(self):
        return "/gitweb/" if self.gitweb_port else ""   # same origin: the viewer forwards to the loopback companion

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

    roots_lock = threading.Lock()   # todo writes hold todo.py's lock instead

    def do_POST(self):
        # The writes: todo files (043/044) and the page-set extra roots (044). A cross-site page cannot send them:
        # JSON plus a custom header needs a CORS preflight the viewer never answers, and Origin must match.
        if not self._host_ok():
            self._send(403, "forbidden: non-localhost Host\n")
            return
        route = urllib.parse.urlparse(self.path).path
        if route not in ("/api/todo", "/api/roots"):
            self._send(404, "not found\n")
            return
        origin = self.headers.get("Origin")
        if (origin and urllib.parse.urlsplit(origin).netloc != self.headers.get("Host", "")) or \
                self.headers.get("X-SV-Write") != "1" or not self.headers.get("Content-Type", "").startswith("application/json"):
            self._send(403, "forbidden\n")
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if not 0 < n <= TODO_MAX:
            self._send(413, "too large\n")
            return
        try:
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            if route == "/api/roots":
                op, path, trusted = body["op"], body["path"], body.get("trusted", False)
                if op not in ("add", "remove", "trust") or not isinstance(path, str) or type(trusted) is not bool \
                        or (op == "trust" and "trusted" not in body):
                    raise ValueError
                self._roots_op(op, path, trusted)
                return
            op, name, version = body.get("op", "write"), body["file"], body["version"]
        except (ValueError, KeyError, TypeError, AttributeError, UnicodeDecodeError, OverflowError):
            self._send(400, "bad request\n")
            return
        if not isinstance(version, str) or not ok_todo_name(name) or not todo_body_ok(op, body):
            self._send(400, "bad request\n")
            return
        self._todo_op(op, name, version, body)

    def _roots_json(self):
        return [{"label": l, "path": str(r), "from": self.ext_from.get(l, "config"), "trusted": str(r) in self.ext_trusted}
                for l, r in self.ext_roots.items()]

    def _roots_op(self, op, path, trusted=False):
        """add / remove a page-set extra root, or trust / distrust any extra root. Only an existing directory under the
        home directory (not home itself); roots from config.yaml are left to config.yaml, their trust lives in the
        viewer's file. Every change is logged."""
        with self.roots_lock:
            mine, trust, p = ui_roots(), ui_trusted(), path.strip()
            if not (p.startswith("/") or p == "~" or p.startswith("~/")):
                self._json({"error": "请写完整路径（/… 或 ~/…）"}, 400)
                return
            real = Path(os.path.expanduser(p)).resolve(strict=False)
            if op == "trust":
                if real not in self.ext_roots.values():
                    self._json({"error": "这个目录不在外部目录里"}, 400)
                    return
                (trust.add if trusted else trust.discard)(str(real))
            elif op == "add":
                if not real.is_dir() or not root_allowed(real):
                    self._json({"error": "只能添加家目录之下已存在的目录，且不能是隐藏目录或 ~/Library"}, 400)
                    return
                if str(real) not in mine:
                    mine.append(str(real))
                (trust.add if trusted else trust.discard)(str(real))
            else:
                if str(real) not in mine:
                    self._json({"error": "这个目录不是在页面里加的（在 config.yaml 里删）"}, 400)
                    return
                mine.remove(str(real))
                trust.discard(str(real))
            try:
                save_ui_roots(mine, trust)
            except OSError as e:
                self._json({"error": str(e)}, 500)
                return
            Handler.ext_roots, Handler.ext_from = extra_roots()
            Handler.ext_trusted = ui_trusted()
            sys.stderr.write("viewer roots - %s %s %s trusted=%s (from %s)\n"
                             % (self.client_address[0], op, real, str(real) in Handler.ext_trusted, self.headers.get("Host", "")))
            self._json({"roots": self._roots_json()})

    def _todo_op(self, op, name, version, body):
        """One write to a todo file, done by todo.py under its lock and only at the version the page read ("" = absent)."""
        tdir = self.dev_root / TODO_DIR
        if tdir.is_symlink() or (tdir.exists() and not tdir.is_dir()):   # a link could carry the write outside dev_root
            self._send(403, "forbidden: todo/ is not a plain directory\n")
            return
        if (tdir / name).is_symlink() or (op == "rename" and (tdir / body["to"]).is_symlink()):
            self._send(403, "forbidden: a link\n")
            return
        t = str(tdir)
        try:
            if op == "delete":
                _todo.delete_at(t, name, version)
                self._json({"version": ""})
                return
            if op == "rename":
                self._json({"version": _todo.rename_at(t, name, body["to"], version)})
                return
            if op == "tick":
                def change(text):
                    lines = _todo.normalize(text).split("\n")
                    if body["line"] >= len(lines) or lines[body["line"]] != body["text"]:
                        raise _todo.TodoError("changed")   # the line the page ticked is not that line any more
                    return _todo.toggle(text, body["line"], body["done"], body["today"])
            elif op == "append":
                block = _todo.compose(body["text"], body["project"], body["link"], body["stamp"])
                change = lambda text: _todo.append_checked(text, name, block)
            else:
                change = lambda text: _todo.normalize(body["text"])
            self._json({"version": _todo.write_at(t, name, version, change)})
        except _todo.Conflict as e:
            self._json({"error": str(e), "version": e.version}, 409)
        except _todo.Hidden:
            self._json({"error": "hidden"}, 422)
        except _todo.TodoError:
            self._json({"error": "changed", "version": _todo.file_version(str(tdir / name))}, 409)
        except ValueError:   # not UTF-8
            self._json({"error": "not-utf8"}, 422)
        except OSError as e:
            self._json({"error": str(e)}, 500)

    def do_GET(self):
        if not self._host_ok():
            self._send(403, "forbidden: non-localhost Host\n")
            return
        parsed = urllib.parse.urlparse(self.path)
        path, qs = parsed.path, urllib.parse.parse_qs(parsed.query)
        if path in ("/", "/v2"):
            self._serve_shell(SHELL_V2_HTML)
        elif path == "/v1":
            self._serve_shell(SHELL_HTML)
        elif path.startswith("/assets/"):
            self._serve_asset(path[len("/assets/"):])
        elif path.startswith("/raw/"):
            self._serve_raw(path)
        elif path.startswith("/page/"):
            self._serve_page(path)
        elif path == "/gitweb" or path.startswith("/gitweb/"):
            self._proxy_gitweb(parsed)
        elif path == "/api/tree":
            self._serve_tree(qs.get("html", [""])[0] == "1")
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
        elif path == "/api/branchlog":
            self._serve_branchlog(qs.get("repo", [""])[0], qs.get("branch", [""])[0])
        elif path == "/api/roots":
            self._json({"roots": self._roots_json()})
        elif path == "/api/history":
            self._json(card_history(self.dev_root))
        elif path == "/api/shas":
            self._serve_shas(qs.get("h", []), qs.get("prefer", []))
        else:
            self._send(404, "not found\n")

    def _serve_shell(self, page):
        try:
            html = page.read_text(encoding="utf-8")
        except OSError as e:
            self._send(500, "shell missing: %s\n" % e)
            return
        # R63/003: inject the gitweb companion URL (empty when disabled → shell hides the code links);
        # built from the Host the browser used, so a LAN client gets a LAN link (the Host passed _host_ok).
        html = html.replace("__GITWEB_URL__", self.gitweb_url())
        self._send(200, html, "text/html; charset=utf-8")

    def _proxy_gitweb(self, parsed):
        # /gitweb/<rest> → the loopback companion's /<rest>; its own redirects come back under the prefix.
        if not self.gitweb_port:
            self._send(404, "not found\n")
            return
        upstream = (parsed.path[len("/gitweb"):] or "/") + ("?" + parsed.query if parsed.query else "")
        try:
            c = http.client.HTTPConnection("127.0.0.1", self.gitweb_port, timeout=300)   # lighttpd sends a CGI response only once it is complete: a big blame says nothing until git is done
            c.request("GET", upstream, headers={"Host": "127.0.0.1:%d" % self.gitweb_port, "Accept-Encoding": "identity"})
            r = c.getresponse()
            body = r.read()
            c.close()
        except (OSError, http.client.HTTPException):
            self._send(502, "gitweb companion unreachable\n")
            return
        extra = {"Content-Security-Policy": GITWEB_CSP, "X-Content-Type-Options": "nosniff"}
        for k in ("Content-Disposition", "Last-Modified", "ETag", "Cache-Control", "Expires"):
            if r.getheader(k):
                extra[k] = r.getheader(k)
        loc = r.getheader("Location")
        if loc:
            u = urllib.parse.urlsplit(loc)
            if u.netloc in ("", "127.0.0.1:%d" % self.gitweb_port):
                loc = "/gitweb" + (u.path or "/") + ("?" + u.query if u.query else "")
            extra["Location"] = loc
        ctype = r.getheader("Content-Type", "application/octet-stream")
        if ctype.startswith("text/html"):   # an XML subset in gitweb's doctype prints "]>" in HTML
            body = re.sub(rb"<!DOCTYPE html \[.*?\]>", b"<!DOCTYPE html>", body, count=1, flags=re.S)
        self._send(r.status, body, ctype, extra)

    def _serve_asset(self, name):
        # static files from the hardcoded VIEWER_DIR by an exact-name allowlist — never a user path.
        ctype = ASSETS.get(name)
        if ctype is None:
            self._send(404, "not found\n")
            return
        try:
            path = VIEWER_DIR / name
            st = path.stat()
            etag = '"%x-%x"' % (st.st_size, st.st_mtime_ns)
            cache = {"ETag": etag, "Cache-Control": "no-cache"}   # revalidate every time: a 304 spares the 3 MB mermaid
            if self.headers.get("If-None-Match") == etag:
                self._send(304, b"", extra=cache)
                return
            if ctype.startswith("text/"):
                ctype += "; charset=utf-8"
            self._send(200, path.read_bytes(), ctype, extra=cache)
        except OSError:
            self._send(404, "not found\n")

    def _root_of(self, which, relpath):
        """(root, path under it) for a tree name — dev, kb, or ext whose first segment names an extra root."""
        if which == "dev":
            return self.dev_root, relpath
        if which == "kb":
            return self.kb_root, relpath
        label, _, rest = relpath.partition("/")
        root = self.ext_roots.get(urllib.parse.unquote(label))
        return (root, rest) if which == "ext" and root and rest else (None, None)

    def _serve_raw(self, path):
        # /raw/{dev|kb|ext}/<relpath> → file bytes, confined to the requested root.
        m = re.match(r"^/raw/(dev|kb|ext)/(.*)$", path)
        if not m:
            self._send(404, "not found\n")
            return
        root, relpath = self._root_of(m.group(1), m.group(2))
        if root is None or not relpath.endswith(".md"):        # viewer serves markdown only
            self._send(404, "not found\n")
            return
        real = safe_join(root, relpath)         # None = traversal / out-of-root symlink
        if real is None or not real.is_file():
            self._send(404, "not found\n")      # same code: don't leak existence
            return
        try:
            mt = int(real.stat().st_mtime * 1000)      # R63: lets the client detect a doc update; taken before the read,
        except OSError:                                # so a write in between leaves an older mtime (a later save is refused, not lost)
            mt = 0
        ver = _todo.file_version(str(real))          # what a todo write names; ns-precise, also taken before the read
        try:
            data = real.read_text(encoding="utf-8")
        except (OSError, ValueError):                  # ValueError: not UTF-8, which the viewer does not show
            self._send(404, "not found\n")
            return
        self._send(200, data, extra={"X-Mtime": str(mt), "X-Version": ver})

    def _serve_tree(self, html=False):
        # Two-root *.md manifest (root-relative posix); the boundary applies here too:
        # followlinks=False + realpath confinement, so an out-of-root symlink target never
        # leaks a filename into the listing. html=1 (the v2 shell) adds *.html and the page keys.
        exts = (".md", ".html") if html else (".md",)
        ext = [dict(it, path=label + "/" + it["path"]) for label, root in self.ext_roots.items()
               for it in scan_tree(root, with_mtime=True, limit=EXT_SCAN_MAX, exts=exts)]
        out = {"dev": scan_tree(self.dev_root, with_mtime=True, exts=exts),
               "kb": scan_tree(self.kb_root, with_mtime=True, exts=exts), "ext": ext,
               "roots": {"dev": str(self.dev_root), "kb": str(self.kb_root),
                         "ext": {label: str(root) for label, root in self.ext_roots.items()}}}
        if html:
            out["pages"] = dict(self.page_keys, untrusted=self._untrusted_prefixes())
        self._json(out)

    def _untrusted(self):
        return [r for r in self.ext_roots.values() if str(r) not in self.ext_trusted]

    def _untrusted_prefixes(self):
        """"<tree>:<rel>/" prefixes under which a page takes the untrusted key: each untrusted root wherever a tree
        reaches it — as its own label, inside another root, or containing one (then the whole tree)."""
        trees = [("dev:", self.dev_root), ("kb:", self.kb_root)] + [("ext:%s/" % l, r) for l, r in self.ext_roots.items()]
        out = set()
        for u in self._untrusted():
            for pre, root in trees:
                if u == root or u in root.parents:
                    out.add(pre)
                elif root in u.parents:
                    out.add(pre + u.relative_to(root).as_posix() + "/")
        return sorted(out)

    def _serve_page(self, path):
        # /page/<key>/{dev|kb|ext}/<relpath> → a page or one of its files; the key must match the file's trust class,
        # judged by realpath (a file under any untrusted root is untrusted, whichever tree reached it)
        m = re.match(r"^/page/([^/]+)/(dev|kb|ext)/(.*)$", path)
        kind = m and next((k for k, v in self.page_keys.items() if secrets.compare_digest(v, m.group(1))), None)
        root, relpath = self._root_of(m.group(2), m.group(3)) if kind else (None, None)
        real = safe_join(root, relpath) if root else None
        ctype = PAGE_TYPES.get(real.suffix.lower()) if real else None   # the file's own type: a link named .html is not a page
        untrusted = real is not None and any(u == real or u in real.parents for u in self._untrusted())
        extra = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}   # no-store: a trust change takes effect on the next load
        if ctype is None or not real.is_file() or untrusted != (kind == "u"):
            self._send(404, "not found\n", extra=extra)
            return
        if untrusted:
            extra["Content-Security-Policy"] = PAGE_SANDBOX
        try:
            data = real.read_bytes()
        except OSError:
            self._send(404, "not found\n", extra=extra)
            return
        self._send(200, data, ctype, extra)

    def _serve_board(self):
        # schema = iter_cards' pinned fields (incl. 017 `governance`, 020 `carriers` —
        # additive; the carrier closed-list mapping lives only in workflow-status.py)
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
            self._json({"dev": _rev_token(self.dev_root), "kb": _rev_token(self.kb_root),
                        "ext": ",".join(_rev_token(r, EXT_SCAN_MAX) for r in self.ext_roots.values())})
            return
        m = re.match(r"^(dev|kb|ext)/(.*)$", p)
        root, relpath = self._root_of(m.group(1), m.group(2)) if m else (None, None)
        real = safe_join(root, relpath) if root else None
        mt = 0
        if real is not None and real.is_file():
            try:
                mt = int(real.stat().st_mtime * 1000)
            except OSError:
                mt = 0
        self._json({"mtime": mt})

    def _serve_filelog(self, p):
        # R5: per-file commit history (excludes auto data-snapshots) → JSON for the viewer's change list.
        m = re.match(r"^(dev|kb|ext)/(.*)$", p or "")
        if not m or not m.group(2).endswith(".md"):
            self._json({"commits": []})
            return
        root, relpath = self._root_of(m.group(1), m.group(2))
        real = safe_join(root, relpath) if root else None             # validate AND use the confined path (as _serve_raw does)
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
        if _git(root, "status", "--porcelain", "--", rel).strip():
            day = datetime.date.fromtimestamp(real.stat().st_mtime).isoformat()
            commits.insert(0, {"sha": WORKTREE, "subject": "未提交的改动", "date": day})
        self._json({"commits": commits})

    def _serve_filediff(self, p, sha):
        # R5: one commit's change to one file → the after-version + parsed add/del line info (JSON).
        m = re.match(r"^(dev|kb|ext)/(.*)$", p or "")
        empty = {"after": "", "adds": [], "dels": []}
        if not m or not m.group(2).endswith(".md") or not (sha == WORKTREE or re.fullmatch(r"[0-9a-fA-F]{4,64}", sha or "")):
            self._json(empty)
            return
        root, relpath = self._root_of(m.group(1), m.group(2))
        real = safe_join(root, relpath) if root else None             # validate AND use the confined path (as _serve_raw does)
        if real is None:                               # traversal / out-of-root
            self._json(empty)
            return
        rel = real.relative_to(root).as_posix()
        if sha == WORKTREE:                            # the file on disk against HEAD; an untracked file is all added
            after = real.read_text(encoding="utf-8", errors="replace") if real.is_file() else ""
            if _git(root, "ls-files", "--", rel).strip():
                adds, dels = _parse_file_patch(_git(root, "-c", "core.quotepath=false", "diff", "--no-color", "HEAD", "--", rel))
            else:
                adds, dels = list(range(1, len(after.splitlines()) + 1)), []
            self._json({"after": after, "adds": adds, "dels": dels})
            return
        after = _git(root, "-c", "core.quotepath=false", "show", "%s:%s" % (sha, rel))
        patch = _git(root, "-c", "core.quotepath=false", "show", "--format=", "-p", "--no-color", sha, "--", rel)
        adds, dels = _parse_file_patch(patch)
        self._json({"after": after, "adds": adds, "dels": dels})


    def _serve_branchlog(self, repo, branch):
        # 043: a card's branch → its commits not on the repo's main line (newest first, at most 30).
        gd = self.repos.get(repo)
        if not gd or not re.fullmatch(r"[\w][\w./-]*", branch or "") or ".." in branch:
            self._json({"commits": [], "base": "", "found": False})
            return
        head = "refs/heads/" + branch
        if not _gitd(gd, "rev-parse", "--verify", "-q", head).strip():
            self._json({"commits": [], "base": "", "found": False})
            return
        # the remote main line first: for a card working on main itself that leaves its unpushed commits
        base = next((b for b in ("refs/remotes/origin/HEAD", "refs/remotes/origin/main", "refs/remotes/origin/master",
                                 "refs/heads/main", "refs/heads/master")
                     if b != head and _gitd(gd, "rev-parse", "--verify", "-q", b).strip()), "")
        out = _gitd(gd, "log", "--format=%H%x1f%s%x1f%cs", "-n", "30", base + ".." + head if base else head)
        commits = [dict(zip(("sha", "subject", "date"), l.split("\x1f"))) for l in out.splitlines() if l.count("\x1f") == 2]
        self._json({"commits": commits, "base": re.sub(r"^refs/(heads|remotes)/", "", base), "found": True})

    def _serve_shas(self, shas, prefer):
        # 043: which gitweb repo holds each sha (7-40 hex), trying the preferred labels first; unknown → absent.
        shas = [h.lower() for h in shas if re.fullmatch(r"[0-9a-fA-F]{7,40}", h)][:60]
        order = [l for l in prefer if l in self.repos] + [l for l in self.repos if l not in prefer]
        ck = lambda h: h + "|" + order[0] if order else h   # a short sha may live in two repos: the answer depends on who asks first
        todo = [h for h in dict.fromkeys(shas) if ck(h) not in self.sha_home]
        for label in order:
            if not todo:
                break
            found = _sha_lookup(self.repos[label], todo)
            for h in found:
                self.sha_home[ck(h)] = label
            todo = [h for h in todo if h not in found]
        self._json({h: self.sha_home[ck(h)] for h in shas if self.sha_home.get(ck(h))})

def _gitd(git_dir, *args):
    """git against a bare git dir (the companion's repos are known by git dir, not work tree)."""
    try:
        return subprocess.run(["git", "--git-dir", git_dir, *args], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _sha_lookup(git_dir, shas):
    """The subset of shas that name a commit in this repo (one git process for the lot)."""
    try:
        r = subprocess.run(["git", "--git-dir", git_dir, "cat-file", "--batch-check=%(objecttype)"],
                           input="".join(h + "^{commit}\n" for h in shas), capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {h for h, line in zip(shas, r.stdout.splitlines()) if line.strip() == "commit"}


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
    return {"card": card or "", "repo": "", "repo_anchor": False, "parts": [],
            "generated_at": "", "rows": [], "orphans": [], "error": err}


def _rev_token(root: Path, limit=None):
    """Change token for live refresh (R63): "<newest mtime ms>.<count>" over the .md and .html files under root.
    The count makes deletions flip the token too — max-mtime alone misses removing a non-newest file."""
    best = n = 0
    for dirpath, dirnames, filenames in _walk(root, limit):
        for fn in filenames:
            if fn.endswith((".md", ".html")) and not (limit and n >= limit):
                n += 1
                try:
                    best = max(best, int((Path(dirpath) / fn).stat().st_mtime * 1000))
                except OSError:
                    pass
        if limit and n >= limit:
            break
    return "%d.%d" % (best, n)


def _walk(root, limit):
    """os.walk; with a limit (an extra root) hidden directories and node_modules are not entered."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        if limit:
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
        yield dirpath, dirnames, filenames


def scan_tree(root: Path, with_mtime=False, limit=None, exts=(".md",)):
    out = []
    for dirpath, _dirnames, filenames in _walk(root, limit):
        if limit and len(out) >= limit:
            break
        for fn in filenames:
            if limit and len(out) >= limit:
                break
            if not fn.endswith(exts):
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


def _cat_blobs(root: Path, specs):
    """The texts of many "<rev>:<path>" specs through one `git cat-file --batch` ("" for a missing one)."""
    if not specs:
        return []
    try:
        out = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"], input=("\n".join(specs) + "\n").encode(),
                             capture_output=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return [""] * len(specs)
    texts, i = [], 0
    for _ in specs:
        nl = out.find(b"\n", i)
        if nl < 0:                                 # output cut short: the rest stay empty rather than shifting
            break
        head, i = out[i:nl].split(), nl + 1
        if len(head) == 3 and head[1] == b"blob":
            n = int(head[2])
            texts.append(out[i:i + n].decode("utf-8", "replace"))
            i += n + 1
        else:
            texts.append("")
    return texts + [""] * (len(specs) - len(texts))


_REQ_HEAD = re.compile(r"### Req-(\d+)\s+(\S+)\s*[—-]+\s*(.*)")


def _doc_state(text):
    """A lite design.md's status and, per Req, (state word, title, statement digest)."""
    st = re.search(r"^status:\s*(\w+)", text, re.M)
    reqs = {}
    for block in re.split(r"(?m)^(?=### Req-\d+)", text)[1:]:
        h = _REQ_HEAD.match(block)
        if not h:
            continue
        stmt = re.search(r"^- 陈述:(.*(?:\n  .*)*)", block.split("\n## ")[0], re.M)
        reqs[h.group(1)] = (h.group(2), h.group(3).strip(), re.sub(r"\s+", " ", stmt.group(1)).strip() if stmt else "")
    return (st.group(1) if st else ""), reqs


_history = {"key": None, "data": None}
_history_lock = threading.Lock()


def card_history(dev_root: Path):
    """Every card's life from dev_root's git history (/api/history): for a lite card the status of each design.md
    revision and every Req's state, title and statement changes; for every card its dir's first and last commit
    (sweeps that name no card skipped, unless a dir has nothing else). An uncommitted design.md counts as a last revision at its mtime. Cached
    until HEAD or a lite design.md changes."""
    docs = {}
    for f in sorted(dev_root.glob("*/[0-9][0-9][0-9]-*/design.md")):
        try:
            if "governance: lite" in f.read_text(encoding="utf-8", errors="replace")[:3000]:
                docs[f.relative_to(dev_root).as_posix()] = (f, f.stat().st_mtime_ns)
        except OSError:
            pass
    key = (_git(dev_root, "rev-parse", "HEAD").strip(), tuple((k, m) for k, (_, m) in docs.items()))
    with _history_lock:
        if _history["key"] == key:
            return _history["data"]
    # paths relative to dev_root, which may sit inside a larger repo; cat-file wants them from the repo's top
    prefix = _git(dev_root, "rev-parse", "--show-prefix").strip()
    try:
        r = subprocess.run(["git", "-C", str(dev_root), "-c", "core.quotepath=false", "log", "--reverse", "--relative",
                            "--date=format-local:%Y-%m-%d %H:%M", "--format=%x1e%H%x1f%cd%x1f%s", "--name-only"],
                           capture_output=True, timeout=120)
        failed, log = r.returncode != 0, r.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        failed, log = True, ""
    span, swept, revs = {}, {}, {k: [] for k in docs}
    for chunk in log.split("\x1e")[1:]:
        head, _, names = chunk.partition("\n")
        parts = head.split("\x1f", 2)
        if len(parts) != 3:
            continue
        sha, t, subject = parts
        names = [n for n in names.splitlines() if n]
        dirs = {m.group(1) + "/" + m.group(2) for m in (re.match(r"^([^/]+)/(\d{3})-[^/]+/", n) for n in names) if m}
        named = dirs if len(dirs) == 1 else {d for d in dirs if re.search(r"\b%s\b" % d.split("/")[1], subject)} if len(dirs) <= HISTORY_BULK else set()
        for d in dirs:
            (span if d in named else swept).setdefault(d, [t, t])[1] = t
        for n in names:
            if n in revs:
                revs[n].append((sha, t))
    out = {d: {"status": [], "reqs": {}, "first": a, "last": b} for d, (a, b) in {**swept, **span}.items()}   # a dir only swept keeps the sweeps' span
    order = [(k, sha, t) for k, rs in revs.items() for sha, t in rs]
    texts = dict(zip(((k, sha) for k, sha, _ in order), _cat_blobs(dev_root, ["%s:%s%s" % (sha, prefix, k) for k, sha, _ in order])))
    for k, (f, mt) in docs.items():
        steps = [(t, texts.get((k, sha), "")) for sha, t in revs[k]]
        try:
            now = f.read_text(encoding="utf-8", errors="replace")
        except OSError:                                # gone since the scan: its committed revisions still count
            now = steps[-1][1] if steps else ""
        if now and (not steps or steps[-1][1] != now):
            steps.append((datetime.datetime.fromtimestamp(mt / 1e9).strftime("%Y-%m-%d %H:%M"), now))
        if not steps:
            continue
        cid = k.split("/")[0] + "/" + k.split("/")[1][:3]
        card = out.setdefault(cid, {"status": [], "reqs": {}, "first": steps[0][0], "last": steps[-1][0]})
        last_st, prev = None, {}
        for t, text in steps:
            st, reqs = _doc_state(text)
            if st and st != last_st:
                card["status"].append({"t": t, "v": st})
                last_st = st
            for n, (word, title, stmt) in reqs.items():
                ev, p = card["reqs"].setdefault(n, []), prev.get(n)
                if p is None:
                    ev.append({"t": t, "type": "new", "word": word, "title": title})
                    continue
                if word != p[0]:
                    ev.append({"t": t, "type": "word", "from": p[0], "to": word})
                if title != p[1]:
                    ev.append({"t": t, "type": "title", "from": p[1], "to": title})
                if stmt != p[2]:
                    ev.append({"t": t, "type": "stmt"})
            for n in prev:
                if n not in reqs:
                    card["reqs"].setdefault(n, []).append({"t": t, "type": "gone"})
            prev = reqs
    if not failed:                                     # a failed log is served, never cached
        with _history_lock:
            _history["key"], _history["data"] = key, out
    return out


def _git(dev_root: Path, *args):
    try:
        r = subprocess.run(["git", "-C", str(dev_root), *args],
                           capture_output=True, text=True, timeout=15)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _viewer_on(port):
    """Whether 127.0.0.1:port answers with this viewer's shell (not just any listener)."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=0.6) as r:
            return "status viewer" in r.read(4096).decode("utf-8", "replace")
    except Exception:
        return False


def lan_ip():
    """The interface address a LAN client reaches us on (no packet is sent), or None."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


def bind_server(port, bind="127.0.0.1"):
    """Bind the fixed port, or name who holds it and stop — never fall back to a random port,
    which would break the ssh -L rule the fixed port exists for."""
    try:
        httpd = http.server.ThreadingHTTPServer((bind, port), Handler)
    except OSError as e:
        if e.errno != errno.EADDRINUSE:
            raise
        who = "another status viewer" if _viewer_on(port) else "another program"
        sys.stderr.write("port %d is busy (%s). The viewer's port is fixed; stop that one "
                         "or pass --port N.\n" % (port, who))
        sys.exit(1)
    httpd.daemon_threads = True
    return httpd


def serve(dev_root: Path, kb_root: Path, port=DEFAULT_PORT, open_browser=True, gitweb=True, gitweb_port=None,
          lan=False, hosts=()):
    Handler.dev_root = dev_root
    Handler.kb_root = kb_root
    Handler.ext_roots, Handler.ext_from = extra_roots()
    Handler.ext_trusted = ui_trusted()
    migrate_todo(dev_root)
    bind = "0.0.0.0" if lan else "127.0.0.1"
    ip = lan_ip() if lan else None
    if lan:
        ALLOWED_HOSTS.update([ip] if ip else [])
        ALLOWED_HOSTS.update(hosts)
    httpd = bind_server(port, bind)      # before the companion: a failed bind must not leave a fresh lighttpd behind
    companion = None
    if gitweb:                                  # 003: co-launch the read-only gitweb companion
        try:
            companion = _gw.start(gitweb_port or _gw.DEFAULT_PORT)   # loopback only, even with --lan: clients reach it through /gitweb/
        except Exception as e:
            sys.stderr.write("gitweb companion error: %s\n" % e)
        if not companion:                       # require both up by default; --no-gitweb to opt out
            sys.stderr.write("gitweb companion failed to start — viewer + gitweb are both required; "
                             "pass --no-gitweb to run the viewer alone.\n")
            sys.exit(1)
        Handler.gitweb_port = companion["port"]
        Handler.repos = dict(_gw.collect_repos())
        print("gitweb companion on 127.0.0.1:%d, served at /gitweb/ (%d repos)" % (companion["port"], len(companion["repos"])), file=sys.stderr)
    else:
        Handler.gitweb_port = 0
    url = "http://127.0.0.1:%d/" % httpd.server_address[1]
    print("status viewer on %s  (dev_root=%s, kb=%s)  — Ctrl-C to stop" %
          (url, dev_root, kb_root), file=sys.stderr)
    if lan:
        print("--lan: also on http://%s:%d/ (Host allowlist: %s) — anyone on this network can read dev_root, the KB "
              "and every repo (gitweb at /gitweb/), and rewrite the files in <dev_root>/todo/" % (ip or "<your LAN ip>", httpd.server_address[1], ", ".join(sorted(ALLOWED_HOSTS))), file=sys.stderr)
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


def parse_args(argv):
    port, open_browser, dev_arg, kb_arg = DEFAULT_PORT, True, None, None
    gitweb, gitweb_port, lan, hosts = True, None, False, []
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
        elif a == "--lan":
            lan = True
        elif a == "--host":
            hosts.append(argv[i + 1]); i += 2; continue
        elif a in ("-h", "--help"):
            print(__doc__[__doc__.index("Usage:"):].rstrip())
            sys.exit(0)
        else:                                   # never serve on a mistyped flag: a stray server squats the fixed port
            sys.stderr.write("viewer.py: unknown argument %r (see --help)\n" % a)
            sys.exit(2)
        i += 1
    return {"port": port, "open_browser": open_browser, "dev_arg": dev_arg, "kb_arg": kb_arg,
            "gitweb": gitweb, "gitweb_port": gitweb_port, "lan": lan, "hosts": hosts}


def main(argv):
    a = parse_args(argv)
    dev_root, kb_root = resolve_roots(a["dev_arg"], a["kb_arg"])
    serve(dev_root, kb_root, port=a["port"], open_browser=a["open_browser"],
          gitweb=a["gitweb"], gitweb_port=a["gitweb_port"], lan=a["lan"], hosts=a["hosts"])


if __name__ == "__main__":
    main(sys.argv[1:])
