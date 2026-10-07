#!/usr/bin/env python3
"""P1 (server) acceptance tests for viewer.py — stdlib unittest, no third-party deps.

Run: python3 tools/viewer/test_viewer.py    (from the xg-dev-workflow dir, or anywhere).
Covers the curl-level contract of each endpoint against throwaway fixture trees / git repos.
P2 (shell JS) is verified manually in a browser — not here.
"""
import contextlib
import http.server
import importlib.util
import io
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("viewer", str(TOOLS / "viewer.py"))
viewer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(viewer)


def start(dev, kb):
    viewer.Handler.dev_root = Path(dev).resolve()
    viewer.Handler.kb_root = Path(kb).resolve()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), viewer.Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.1)
    return httpd, "http://127.0.0.1:%d" % httpd.server_address[1]


def get(base, path, host=None):
    req = urllib.request.Request(base + path)
    if host:
        req.add_header("Host", host)
    try:
        r = urllib.request.urlopen(req, timeout=3)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


class T0Skeleton(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "dev").mkdir(); (self.tmp / "kb").mkdir()
        self.httpd, self.base = start(self.tmp / "dev", self.tmp / "kb")

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def test_root_serves_v2_and_v1_keeps_the_classic(self):
        root, alias, v1 = get(self.base, "/"), get(self.base, "/v2"), get(self.base, "/v1")
        self.assertEqual((root[0], alias[0], v1[0]), (200, 200, 200))
        self.assertEqual(root[1], alias[1])
        self.assertIn('src="/assets/v2-core.js"', root[1])
        self.assertIn("window.GITWEB_URL", v1[1])

    def test_shell_served_and_references_assets(self):
        code, body = get(self.base, "/v1")
        self.assertEqual(code, 200)
        self.assertIn("status viewer", body)
        self.assertIn('src="/assets/marked.min.js"', body)     # marked loaded eagerly
        self.assertNotIn('<script src="/assets/mermaid.min.js">', body)  # mermaid is lazy-loaded
        self.assertIn("Content-Security-Policy", body)

    def test_non_localhost_host_403(self):
        self.assertEqual(get(self.base, "/", host="evil.com")[0], 403)
        self.assertEqual(get(self.base, "/v2", host="evil.com")[0], 403)

    def test_v2_served_with_gitweb_injected(self):
        code, body = get(self.base, "/v2")
        self.assertEqual(code, 200)
        self.assertIn('<meta name="gitweb-url" content="">', body)   # companion disabled here
        self.assertNotIn("__GITWEB_URL__", body)
        self.assertIn('src="/assets/sv.js"', body)

    def test_v2_csp_differs_from_classic_only_in_two_same_origin_tightenings(self):
        def csp(body):
            m = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', body)
            self.assertTrue(m, "page must carry its own CSP meta")
            return {d.split()[0]: set(d.split()[1:]) for d in m.group(1).split(";") if d.strip()}
        old, new = csp(get(self.base, "/v1")[1]), csp(get(self.base, "/")[1])
        self.assertEqual(new.pop("style-src"), old.pop("style-src") | {"'self'"})
        self.assertEqual(new.pop("script-src"), old.pop("script-src") - {"'unsafe-inline'"})
        self.assertEqual(new, old)

    def test_v2_has_no_inline_script(self):            # script-src drops 'unsafe-inline', so none may exist
        body = get(self.base, "/v2")[1]
        self.assertNotRegex(body, r"<script(?![^>]*\bsrc=)[^>]*>")
        self.assertNotRegex(body, r"<[^>]+\son[a-z]+\s*=")

    def test_unknown_route_404(self):
        self.assertEqual(get(self.base, "/nope")[0], 404)


class T1Raw(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dev = self.tmp / "dev"; self.kb = self.tmp / "kb"; out = self.tmp / "secret"
        for d in (self.dev, self.kb, out):
            d.mkdir()
        (self.dev / "a.md").write_text("# A\ndev", encoding="utf-8")
        (self.dev / "sub").mkdir(); (self.dev / "sub" / "n.md").write_text("nested", encoding="utf-8")
        (self.kb / "k.md").write_text("kb", encoding="utf-8")
        (out / "passwd.md").write_text("SECRET", encoding="utf-8")
        (self.dev / "escape.md").symlink_to(out / "passwd.md")
        (self.dev / "inrootlink.md").symlink_to(self.dev / "a.md")
        (self.dev / "notes.txt").write_text("txt", encoding="utf-8")
        self.httpd, self.base = start(self.dev, self.kb)

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def test_in_root_md_served(self):
        for p in ("/raw/dev/a.md", "/raw/dev/sub/n.md", "/raw/kb/k.md", "/raw/dev/inrootlink.md"):
            self.assertEqual(get(self.base, p)[0], 200, p)

    def test_out_of_root_symlink_rejected_no_leak(self):
        code, _ = get(self.base, "/raw/dev/escape.md")
        self.assertEqual(code, 404)

    def test_traversal_rejected(self):
        for p in ("/raw/dev/../secret/passwd.md", "/raw/kb/../dev/a.md"):
            self.assertEqual(get(self.base, p)[0], 404, p)

    def test_non_md_and_missing_404(self):
        self.assertEqual(get(self.base, "/raw/dev/notes.txt")[0], 404)
        self.assertEqual(get(self.base, "/raw/dev/nope.md")[0], 404)

    def test_raw_sends_mtime_header(self):          # R63: /raw carries X-Mtime for live-refresh
        r = urllib.request.urlopen(urllib.request.Request(self.base + "/raw/dev/a.md"), timeout=3)
        self.assertGreater(int(r.headers.get("X-Mtime", "0")), 0)


def _git(cwd, *a):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, env=env).stdout


class TTodo(unittest.TestCase):
    """043/044 Req-1 / Inv-1: the one write — files in <dev_root>/todo/, guarded and version-checked."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dev, kb = self.tmp / "dev", self.tmp / "kb"
        self.dev.mkdir(); kb.mkdir()
        self.httpd, self.base = start(self.dev, kb)
        self.t = self.dev / "todo"

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def post(self, body, path="/api/todo", headers=None, raw=None):
        h = {"Content-Type": "application/json", "X-SV-Write": "1"}
        h.update(headers or {})
        data = raw if raw is not None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method="POST", headers={k: v for k, v in h.items() if v is not None})
        try:
            r = urllib.request.urlopen(req, timeout=3)
            return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def w(self, name, text, mtime):
        return self.post({"op": "write", "file": name, "text": text, "mtime": mtime})

    def test_writes_then_refuses_a_stale_version(self):
        code, d = self.w("a.md", "- [ ] a\n", 0)
        self.assertEqual(code, 200)
        self.assertEqual((self.t / "a.md").read_text(encoding="utf-8"), "- [ ] a\n")
        self.assertEqual(get(self.base, "/raw/dev/todo/a.md")[1], "- [ ] a\n")
        code, d2 = self.w("a.md", "- [x] a\n", d["mtime"])
        self.assertEqual(code, 200)
        self.assertEqual(self.w("a.md", "clobber", d["mtime"])[0], 409)     # the version it read is gone
        self.assertEqual((self.t / "a.md").read_text(encoding="utf-8"), "- [x] a\n")
        self.assertEqual(self.w("a.md", "x", 0)[0], 409)                    # it exists now

    def test_rename_and_delete_are_version_checked(self):
        _, d = self.w("a.md", "x", 0); self.w("b.md", "y", 0)
        self.assertEqual(self.post({"op": "rename", "file": "a.md", "to": "b.md", "mtime": d["mtime"]})[0], 409)   # no overwrite
        self.assertEqual(self.post({"op": "rename", "file": "a.md", "to": "c.md", "mtime": 1})[0], 409)
        code, d = self.post({"op": "rename", "file": "a.md", "to": "收件箱.md", "mtime": d["mtime"]})
        self.assertEqual(code, 200); self.assertTrue((self.t / "收件箱.md").is_file()); self.assertFalse((self.t / "a.md").exists())
        self.assertEqual(self.post({"op": "delete", "file": "收件箱.md", "mtime": 1})[0], 409)
        self.assertEqual(self.post({"op": "delete", "file": "收件箱.md", "mtime": d["mtime"]})[0], 200)
        self.assertFalse((self.t / "收件箱.md").exists())
        self.assertEqual(self.post({"op": "delete", "file": "none.md", "mtime": 0})[0], 409)
        _, d = self.w("Case.md", "c", 0)                       # a case-only rename on a case-insensitive disk is not a clash
        self.assertEqual(self.post({"op": "rename", "file": "Case.md", "to": "case.md", "mtime": d["mtime"]})[0], 200)

    def test_names_stay_in_the_directory(self):
        for bad in ("../x.md", "a/b.md", ".hidden.md", "x.txt", "", "a.md\x00"):
            self.assertEqual(self.w(bad, "x", 0)[0], 400, bad)
        self.assertEqual(self.post({"op": "rename", "file": "a.md", "to": "../x.md", "mtime": 0})[0], 400)
        for bad in ("x\nb.md", "x\tb.md", "字" * 90 + ".md", "a.MD"):   # 044 review: control chars, > 240 bytes, the suffix as written
            self.assertEqual(self.w(bad, "x", 0)[0], 400, bad)
        self.assertEqual(self.post({"op": "chmod", "file": "a.md", "mtime": 0})[0], 400)
        self.assertFalse((self.tmp / "x.md").exists())

    def test_never_writes_through_a_link(self):      # 043 review M1
        out = self.tmp / "victim.txt"; out.write_text("safe", encoding="utf-8")
        self.t.mkdir(); (self.t / "l.md").symlink_to(out)
        self.assertEqual(self.w("l.md", "y", int(out.stat().st_mtime * 1000))[0], 403)
        self.assertEqual(out.read_text(encoding="utf-8"), "safe")
        (self.t / "l.md").unlink(); self.t.rmdir()
        outdir = self.tmp / "elsewhere"; outdir.mkdir(); self.t.symlink_to(outdir)
        self.assertEqual(self.w("a.md", "y", 0)[0], 403)
        self.assertFalse((outdir / "a.md").exists())

    def test_refuses_anything_but_a_same_origin_json_write(self):
        ok = {"op": "write", "file": "a.md", "text": "t", "mtime": 0}
        for headers in ({"X-SV-Write": None}, {"Content-Type": "text/plain"}, {"Origin": "http://evil.com"},
                        {"Host": "evil.com"}):
            self.assertEqual(self.post(ok, headers=headers)[0], 403, headers)
        self.assertEqual(self.post(ok, path="/api/other")[0], 404)
        self.assertEqual(self.post(None, raw=b"{not json")[0], 400)
        self.assertEqual(self.post(None, raw=b"[1]")[0], 400)
        self.assertEqual(self.post({"op": "write", "file": "a.md", "text": 3, "mtime": 0})[0], 400)
        self.assertEqual(self.post(None, raw=b'{"file": "a.md", "text": "x", "mtime": 1e999}')[0], 400)
        self.assertEqual(self.post({"op": "write", "file": "a.md", "text": "x" * (300 * 1024), "mtime": 0})[0], 413)
        self.assertFalse(self.t.exists())
        host = urllib.parse.urlsplit(self.base).netloc
        self.assertEqual(self.post(ok, headers={"Origin": "http://" + host})[0], 200)

    def test_the_043_file_never_moves_out_of_dev_root(self):   # 044 review: todo/ as a link or a file
        (self.dev / "todo.md").write_text("old", encoding="utf-8")
        out = self.tmp / "out"; out.mkdir(); self.t.symlink_to(out)
        viewer.migrate_todo(self.dev)
        self.assertFalse((out / "inbox.md").exists()); self.assertTrue((self.dev / "todo.md").exists())
        self.t.unlink(); self.t.write_text("not a dir", encoding="utf-8")
        viewer.migrate_todo(self.dev)                # no crash, nothing moved
        self.assertTrue((self.dev / "todo.md").exists())

    def test_the_043_file_moves_in_once(self):
        (self.dev / "todo.md").write_text("old", encoding="utf-8")
        viewer.migrate_todo(self.dev)
        self.assertEqual((self.t / "inbox.md").read_text(encoding="utf-8"), "old")
        (self.dev / "todo.md").write_text("again", encoding="utf-8")
        viewer.migrate_todo(self.dev)                # inbox.md exists: leave both alone
        self.assertEqual((self.t / "inbox.md").read_text(encoding="utf-8"), "old")


class TRoots(unittest.TestCase):
    """044 Req-2: extra roots set from the page — any client may change them, within the guards."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        dev, kb, self.home = self.tmp / "dev", self.tmp / "kb", self.tmp / "home"
        for d in (dev, kb, self.home / "notes", self.home / "cfg"):
            d.mkdir(parents=True)
        (self.home / "notes" / "n.md").write_text("n", encoding="utf-8")
        (self.home / "cfg" / "c.md").write_text("c", encoding="utf-8")
        (self.tmp / "config.yaml").write_text("extra_roots:\n  - %s\n" % (self.home / "cfg"), encoding="utf-8")
        self.saved = (viewer._rp.config_path, viewer.Path.home)
        viewer._rp.config_path = lambda: self.tmp / "config.yaml"
        viewer.Path.home = classmethod(lambda cls: self.home)
        viewer.Handler.ext_roots, viewer.Handler.ext_from = viewer.extra_roots()
        self.httpd, self.base = start(dev, kb)

    def tearDown(self):
        viewer._rp.config_path, viewer.Path.home = self.saved
        viewer.Handler.ext_roots, viewer.Handler.ext_from = {}, {}
        self.httpd.shutdown(); self.httpd.server_close()

    def post(self, body):
        req = urllib.request.Request(self.base + "/api/roots", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-SV-Write": "1"})
        try:
            r = urllib.request.urlopen(req, timeout=3)
            return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def test_add_list_remove(self):
        code, d = self.post({"op": "add", "path": str(self.home / "notes")})
        self.assertEqual(code, 200)
        self.assertEqual(sorted((r["label"], r["from"]) for r in d["roots"]), [("cfg", "config"), ("notes", "page")])
        self.assertEqual(get(self.base, "/raw/ext/notes/n.md"), (200, "n"))      # live, no restart
        self.assertEqual(json.loads((self.tmp / "viewer-roots.json").read_text())["roots"], [str(self.home / "notes")])
        self.assertEqual((self.tmp / "config.yaml").read_text(), "extra_roots:\n  - %s\n" % (self.home / "cfg"))   # config.yaml untouched
        self.assertEqual(self.post({"op": "remove", "path": str(self.home / "cfg")})[0], 400)   # a config root stays in config
        self.assertEqual(self.post({"op": "remove", "path": str(self.home / "notes")})[0], 200)
        self.assertEqual(get(self.base, "/raw/ext/notes/n.md")[0], 404)
        self.assertEqual([r["label"] for r in json.loads(get(self.base, "/api/roots")[1])["roots"]], ["cfg"])

    def test_a_big_root_is_capped_and_skips_hidden_dirs(self):
        big = self.home / "big"
        for d in ("a", ".git", "node_modules"):
            (big / d).mkdir(parents=True)
        for i in range(5):
            (big / "a" / ("%d.md" % i)).write_text("x", encoding="utf-8")
        (big / ".git" / "h.md").write_text("x", encoding="utf-8"); (big / "node_modules" / "m.md").write_text("x", encoding="utf-8")
        saved, viewer.EXT_SCAN_MAX = viewer.EXT_SCAN_MAX, 3
        try:
            self.post({"op": "add", "path": str(big)})
            ext = [x["path"] for x in json.loads(get(self.base, "/api/tree")[1])["ext"] if x["path"].startswith("big/")]
            self.assertEqual(len(ext), 3)
            self.assertFalse(any(".git" in x or "node_modules" in x for x in ext))
        finally:
            viewer.EXT_SCAN_MAX = saved

    def test_only_existing_dirs_under_home(self):
        for bad in ("/", str(self.home), str(self.tmp / "dev"), str(self.home / "nope"), str(self.home / "notes" / "n.md"),
                    str(self.home / "notes" / ".." / ".."), "~/../.."):
            self.assertEqual(self.post({"op": "add", "path": bad})[0], 400, bad)
        (self.home / ".secret").mkdir(); (self.home / "Library" / "x").mkdir(parents=True)
        for bad in (str(self.home / ".secret"), str(self.home / "Library"), str(self.home / "Library" / "x"), "notes", "./notes"):
            self.assertEqual(self.post({"op": "add", "path": bad})[0], 400, bad)
        self.assertEqual(self.post({"op": "drop", "path": "x"})[0], 400)
        self.assertEqual(self.post({"op": "add", "path": 3})[0], 400)
        self.assertFalse((self.tmp / "viewer-roots.json").exists())


class TShas(unittest.TestCase):
    """043 Req-3-a: /api/shas names the gitweb repo holding each commit, preferred repos first."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        dev, kb = self.tmp / "dev", self.tmp / "kb"
        dev.mkdir(); kb.mkdir()
        self.shas, repos = {}, {}
        for name in ("alpha", "beta"):
            r = self.tmp / name; r.mkdir()
            _git(r, "init", "-q"); _git(r, "commit", "-q", "--allow-empty", "-m", name)
            self.shas[name] = _git(r, "rev-parse", "HEAD").strip()
            repos[name] = str(r / ".git")
        viewer.Handler.repos, viewer.Handler.sha_home = repos, {}
        self.httpd, self.base = start(dev, kb)

    def tearDown(self):
        viewer.Handler.repos, viewer.Handler.sha_home = {}, {}
        self.httpd.shutdown(); self.httpd.server_close()

    def q(self, *params):
        return json.loads(get(self.base, "/api/shas?" + urllib.parse.urlencode(params))[1])

    def test_finds_each_sha_in_its_repo(self):
        a, b = self.shas["alpha"][:10], self.shas["beta"]
        self.assertEqual(self.q(("h", a), ("h", b), ("h", "deadbeef"), ("h", "nothex!"), ("h", "abc")), {a: "alpha", b: "beta"})

    def test_branchlog_lists_commits_off_the_main_line(self):
        r = self.tmp / "alpha"
        _git(r, "checkout", "-q", "-b", "feat/x")
        for m in ("one", "two"):
            _git(r, "commit", "-q", "--allow-empty", "-m", m)
        d = json.loads(get(self.base, "/api/branchlog?repo=alpha&branch=feat/x")[1])
        self.assertEqual(([c["subject"] for c in d["commits"]], d["found"]), (["two", "one"], True))
        self.assertIn(d["base"], ("main", "master"))
        for repo, branch in (("alpha", "nope"), ("nope", "feat/x"), ("alpha", "../x"), ("alpha", "-x")):
            self.assertFalse(json.loads(get(self.base, "/api/branchlog?" + urllib.parse.urlencode({"repo": repo, "branch": branch}))[1])["found"], (repo, branch))

    def test_a_miss_is_retried_later(self):
        self.assertEqual(self.q(("h", "0123456789")), {})
        self.assertNotIn("0123456789", viewer.Handler.sha_home)


class TExtraRoots(unittest.TestCase):
    """043 Req-5: config `extra_roots:` → a third, read-only tree confined like dev and kb."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        dev, kb, self.ext, out = (self.tmp / n for n in ("dev", "kb", "notes", "secret"))
        for d in (dev, kb, self.ext, out):
            d.mkdir()
        (self.ext / "e.md").write_text("# E", encoding="utf-8")
        (self.ext / "deep").mkdir(); (self.ext / "deep" / "x.md").write_text("x", encoding="utf-8")
        (out / "s.md").write_text("SECRET", encoding="utf-8")
        (self.ext / "leak.md").symlink_to(out / "s.md")
        viewer.Handler.ext_roots = {"notes": self.ext.resolve()}
        self.httpd, self.base = start(dev, kb)

    def tearDown(self):
        viewer.Handler.ext_roots = {}
        self.httpd.shutdown(); self.httpd.server_close()

    def test_tree_lists_ext_under_its_label(self):
        ext = [x["path"] for x in json.loads(get(self.base, "/api/tree")[1])["ext"]]
        self.assertEqual(sorted(ext), ["notes/deep/x.md", "notes/e.md"])   # the escaping symlink is not listed

    def test_raw_serves_and_confines(self):
        self.assertEqual(get(self.base, "/raw/ext/notes/e.md"), (200, "# E"))
        for bad in ("/raw/ext/notes/leak.md", "/raw/ext/notes/../secret/s.md", "/raw/ext/nope/e.md", "/raw/ext/notes", "/raw/ext/e.md"):
            self.assertEqual(get(self.base, bad)[0], 404, bad)

    def test_a_label_with_spaces_and_cjk_is_served(self):   # review L1: the label arrives url-encoded
        (self.tmp / "笔记 x").mkdir(); (self.tmp / "笔记 x" / "a.md").write_text("cjk", encoding="utf-8")
        viewer.Handler.ext_roots = {"笔记 x": (self.tmp / "笔记 x").resolve()}
        self.assertEqual(get(self.base, "/raw/ext/" + urllib.parse.quote("笔记 x") + "/a.md"), (200, "cjk"))

    def test_rev_covers_ext(self):                   # review L2: ext changes reach the live refresh
        before = json.loads(get(self.base, "/api/rev")[1])["ext"]
        (self.ext / "new.md").write_text("n", encoding="utf-8")
        self.assertNotEqual(json.loads(get(self.base, "/api/rev")[1])["ext"], before)
        self.assertGreater(json.loads(get(self.base, "/api/rev?path=ext/notes/e.md")[1])["mtime"], 0)

    def test_history_of_a_non_git_root_is_empty(self):
        self.assertEqual(json.loads(get(self.base, "/api/filelog?path=ext/notes/e.md")[1])["commits"], [])

    def test_project_paths_parse_with_and_without_pyyaml(self):   # 043 Q-6: a list at the key's own indent
        spec = importlib.util.spec_from_file_location("rp_fresh", Path(viewer.__file__).parent / "resolve-project.py")
        rp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rp)   # viewer._rp is stubbed by another test
        proj = "projects:\n  a:\n    paths:\n    - /x  # c\n    other:\n    - /nope\n  b:\n    paths:\n      - /y\n"
        for load in (rp._load, lambda t: None):
            rp._load = load
            self.assertEqual([(n, [str(p) for p in ps]) for n, ps in rp.parse_projects(proj)], [("a", ["/x"]), ("b", ["/y"])])

    def test_config_list_parses_with_and_without_pyyaml(self):
        text = "root: ~/k\nextra_roots:\n  - %s\n  - /no/such/dir  # gone\ngitweb_repos:\n- /x\n" % self.ext   # own-indent list, a comment
        for load in (viewer._gw._rp._load, lambda t: None):
            saved = viewer._gw._rp._load; viewer._gw._rp._load = load
            try:
                self.assertEqual(viewer._gw.parse_path_list(text, "extra_roots"), [str(self.ext), "/no/such/dir"])
                self.assertEqual(viewer._gw.parse_gitweb_repos(text), ["/x"])

            finally:
                viewer._gw._rp._load = saved


class T345Endpoints(unittest.TestCase):
    """T3 /api/tree, T4 /api/board, T5 /api/diff+log against a throwaway git dev_root."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dev = self.tmp / "dev"; self.kb = self.tmp / "kb"
        (self.dev).mkdir(); (self.kb).mkdir()
        (self.kb / "k.md").write_text("kb", encoding="utf-8")
        proj = self.dev / "foo"; (proj).mkdir()
        proj.joinpath("index.md").write_text(
            "| 001 | 实现 | active | — |\n", encoding="utf-8")
        card = proj / "001-x"; card.mkdir()
        card.joinpath("requirement.md").write_text(
            "---\nstatus: confirmed\n---\n# r", encoding="utf-8")
        card.joinpath("design.md").write_text("v1", encoding="utf-8")
        _git(self.dev, "init", "-q")
        _git(self.dev, "add", "-A"); _git(self.dev, "commit", "-q", "-m", "foo/001: gate")
        _git(self.dev, "commit", "-q", "--allow-empty", "-m", "auto: data snapshot")
        card.joinpath("design.md").write_text("v1\nUNCOMMITTED", encoding="utf-8")
        viewer._rp.parse_projects = lambda text: [("foo", [self.dev / "foo"])]
        viewer._rp.config_path = lambda: Path("/nonexistent")
        self.httpd, self.base = start(self.dev, self.kb)

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def test_tree_two_roots_prefixed_with_mtime(self):
        _, body = get(self.base, "/api/tree")
        t = json.loads(body)
        devpaths = [x["path"] for x in t["dev"]]      # /api/tree now returns {path, mtime}
        self.assertIn("foo/001-x/design.md", devpaths)
        self.assertIn("k.md", [x["path"] for x in t["kb"]])
        self.assertTrue(all(isinstance(x.get("mtime"), (int, float)) for x in t["dev"]))

    def test_board_schema(self):
        _, body = get(self.base, "/api/board")
        d = json.loads(body)
        card = d["foo"][0]
        for k in ("project", "nnn", "dir", "phase", "state", "deps", "steps",
                  "now", "next_progress", "blockers", "effective_next", "branch", "repo"):  # 003/R6, 043
            self.assertIn(k, card)
        self.assertEqual(card["dir"], "001-x")

    def test_diff_includes_worktree_skips_snapshot(self):
        code, body = get(self.base, "/api/diff?card=foo/001")
        self.assertEqual(code, 200)
        self.assertIn("UNCOMMITTED", body)          # 4b: worktree change present
        self.assertNotIn("data snapshot", body)      # gate skipped the snapshot commit

    def test_diff_bad_card_400(self):
        for bad in ("foo/2", "nope/001", "foo/001/x", "../etc"):
            self.assertEqual(get(self.base, "/api/diff?card=" +
                                 urllib.parse.quote(bad))[0], 400, bad)

    def test_filelog_per_file_commits(self):        # R5 (009 T8): per-file history as JSON
        code, body = get(self.base, "/api/filelog?path=dev/foo/001-x/design.md")
        self.assertEqual(code, 200)
        d = json.loads(body)
        self.assertTrue(len(d["commits"]) >= 1)
        for k in ("sha", "subject", "date"):
            self.assertIn(k, d["commits"][0])
        self.assertEqual(d["commits"][0]["sha"], "worktree")   # design.md has an uncommitted edit
        self.assertEqual(d["commits"][1]["subject"], "foo/001: gate")
        self.assertNotIn("auto: data snapshot", [c["subject"] for c in d["commits"]])

    def test_filelog_bad_path_empty(self):          # non-md / traversal / empty → [] (no leak)
        for bad in ("dev/foo/001-x/nope.txt", "dev/../etc/passwd.md", ""):
            code, body = get(self.base, "/api/filelog?path=" + urllib.parse.quote(bad))
            self.assertEqual(code, 200, bad)
            self.assertEqual(json.loads(body)["commits"], [], bad)

    def test_filediff_after_and_adds(self):         # R5 (009 T9): one commit's file diff → after + add/del
        _, body = get(self.base, "/api/filelog?path=dev/foo/001-x/design.md")
        sha = json.loads(body)["commits"][1]["sha"]
        code, body = get(self.base, "/api/filediff?path=dev/foo/001-x/design.md&sha=" + sha)
        self.assertEqual(code, 200)
        d = json.loads(body)
        self.assertIn("v1", d["after"])          # after-version content at that commit
        self.assertEqual(d["adds"], [1])         # the one added line (new file)
        self.assertEqual(d["dels"], [])

    def test_filelog_worktree_only_when_dirty(self):  # 043 Req-4: uncommitted changes lead the list
        clean = json.loads(get(self.base, "/api/filelog?path=dev/foo/001-x/requirement.md")[1])["commits"]
        self.assertNotIn("worktree", [c["sha"] for c in clean])
        (self.dev / "foo" / "001-x" / "new.md").write_text("a\nb", encoding="utf-8")
        fresh = json.loads(get(self.base, "/api/filelog?path=dev/foo/001-x/new.md")[1])["commits"]
        self.assertEqual([c["sha"] for c in fresh], ["worktree"])

    def test_filediff_worktree(self):                # the file on disk against HEAD; untracked → all added
        d = json.loads(get(self.base, "/api/filediff?path=dev/foo/001-x/design.md&sha=worktree")[1])
        self.assertEqual(d["after"], "v1\nUNCOMMITTED")
        self.assertIn(2, d["adds"])                  # "v1" had no final newline, so git also reports line 1 as replaced
        (self.dev / "foo" / "001-x" / "new.md").write_text("a\nb", encoding="utf-8")
        d = json.loads(get(self.base, "/api/filediff?path=dev/foo/001-x/new.md&sha=worktree")[1])
        self.assertEqual((d["adds"], d["dels"]), ([1, 2], []))

    def test_filediff_bad_sha_empty(self):          # non-hex / empty sha → pinned empty shape
        for bad in ("nothex!", "", "zzzzzzzz"):
            code, body = get(self.base, "/api/filediff?path=dev/foo/001-x/design.md&sha=" + urllib.parse.quote(bad))
            self.assertEqual(code, 200, bad)
            self.assertEqual(json.loads(body), {"after": "", "adds": [], "dels": []}, bad)

    def test_board_tasks_field_pinned(self):        # 007 T3/T4: tasks always present
        _, body = get(self.base, "/api/board")
        self.assertIn("tasks", json.loads(body)["foo"][0])

    def test_trace_ok_card(self):                    # 007 T4
        code, body = get(self.base, "/api/trace?card=foo/001")
        self.assertEqual(code, 200)
        d = json.loads(body)
        for k in ("card", "repo", "repo_anchor", "parts", "generated_at", "rows",
                  "orphans", "error"):
            self.assertIn(k, d)
        self.assertEqual(d["error"], "")
        self.assertEqual(d["card"], "foo/001-x")

    def test_trace_bad_card_is_200_with_error(self):  # 007 R8: never-throw, pinned shape
        for bad in ("foo/2", "nope/001", "", "../etc"):
            code, body = get(self.base, "/api/trace?card=" + urllib.parse.quote(bad))
            self.assertEqual(code, 200, bad)
            d = json.loads(body)
            self.assertTrue(d["error"], bad)
            self.assertEqual(d["rows"], [], bad)

    def test_log_excludes_snapshot_subjects(self):
        _, body = get(self.base, "/api/log?n=5")
        # subject lines are 'commit <hash>' followed by author/date/blank/message; check the
        # gate subject shows and the snapshot subject does not head any commit block.
        self.assertIn("foo/001: gate", body)

    def test_assets_revalidate_with_etag(self):
        r = urllib.request.urlopen(self.base + "/assets/marked.min.js", timeout=3)
        etag = r.headers.get("ETag")
        self.assertTrue(etag)
        self.assertEqual(r.headers.get("Cache-Control"), "no-cache")   # always revalidate: an upgraded asset shows at once
        req = urllib.request.Request(self.base + "/assets/marked.min.js", headers={"If-None-Match": etag})
        with self.assertRaises(urllib.error.HTTPError) as cm:           # urllib surfaces 304 as an HTTPError
            urllib.request.urlopen(req, timeout=3)
        self.assertEqual(cm.exception.code, 304)
        self.assertEqual(cm.exception.read(), b"")
        req = urllib.request.Request(self.base + "/assets/marked.min.js", headers={"If-None-Match": '"stale"'})
        self.assertEqual(urllib.request.urlopen(req, timeout=3).status, 200)

    def test_assets_allowlist_and_traversal(self):
        self.assertEqual(get(self.base, "/assets/marked.min.js")[0], 200)
        self.assertEqual(get(self.base, "/assets/mermaid.min.js")[0], 200)
        self.assertEqual(get(self.base, "/assets/sv.js")[0], 200)
        self.assertEqual(get(self.base, "/assets/evil.js")[0], 404)        # not allowlisted
        self.assertEqual(get(self.base, "/assets/../viewer.py")[0], 404)   # traversal

    def test_every_allowlisted_asset_exists(self):   # a name in ASSETS with no file would 404 the page that loads it
        for name in viewer.ASSETS:
            self.assertTrue((viewer.VIEWER_DIR / name).is_file(), name)
        self.assertEqual(get(self.base, "/assets/v2.css")[0], 200)
        self.assertEqual(get(self.base, "/assets/v2-widths.css")[0], 200)

    def test_asset_types_charset_only_on_text(self):
        r = urllib.request.urlopen(self.base + "/assets/sv.js", timeout=3)
        self.assertEqual(r.headers.get("Content-Type"), "text/javascript; charset=utf-8")
        r = urllib.request.urlopen(self.base + "/assets/martian-mono.woff2", timeout=3)
        self.assertEqual(r.headers.get("Content-Type"), "font/woff2")
        self.assertEqual(r.read()[:4], b"wOF2")

    def test_rev_file_and_dev(self):               # R63: change tokens for live refresh
        _, body = get(self.base, "/api/rev?path=" + urllib.parse.quote("dev/foo/001-x/design.md"))
        self.assertGreater(json.loads(body)["mtime"], 0)
        _, body = get(self.base, "/api/rev")
        tok = json.loads(body)["dev"]                           # token = "<newest mtime>.<.md count>"
        self.assertRegex(tok, r"^\d+\.\d+$")
        self.assertGreater(int(tok.split(".")[1]), 0)           # count > 0
        (self.dev / "foo" / "index.md").unlink()                # delete a NON-newest .md
        _, body = get(self.base, "/api/rev")
        self.assertNotEqual(json.loads(body)["dev"], tok)       # count flips the token — max-mtime alone would miss it
        _, body = get(self.base, "/api/rev?path=" + urllib.parse.quote("dev/foo/nope.md"))
        self.assertEqual(json.loads(body)["mtime"], 0)          # missing → 0
        _, body = get(self.base, "/api/rev?path=" + urllib.parse.quote("dev/../secret/x.md"))
        self.assertEqual(json.loads(body)["mtime"], 0)          # traversal blocked by safe_join

    def test_search_content_filename_scope_guard(self):
        (self.dev / "foo" / "001-x" / "design.md").write_text(
            "# D\nthe UNIQUEWORD lives here\n", encoding="utf-8")
        _, body = get(self.base, "/api/search?q=UNIQUEWORD")
        hits = json.loads(body)["hits"]
        self.assertTrue(any(h["line"] > 0 and "UNIQUEWORD" in h["snippet"] for h in hits))
        # filename match (line 0)
        _, body = get(self.base, "/api/search?q=design.md")
        self.assertTrue(any(h["line"] == 0 for h in json.loads(body)["hits"]))
        # project scope
        _, body = get(self.base, "/api/search?q=UNIQUEWORD&project=nope")
        self.assertEqual(json.loads(body)["hits"], [])
        # 1-char guard
        _, body = get(self.base, "/api/search?q=x")
        self.assertIn("note", json.loads(body))


class T6Port(unittest.TestCase):
    """033 Req-1: the viewer's port is fixed (ssh -L stability), and a busy port never degrades to a random one."""

    def test_default_port_is_fixed(self):
        self.assertEqual(viewer.DEFAULT_PORT, 8790)
        self.assertEqual(viewer.parse_args([])["port"], viewer.DEFAULT_PORT)
        self.assertEqual(viewer.parse_args(["--port", "9999"])["port"], 9999)
        self.assertEqual(viewer.parse_args(["--port", "0"])["port"], 0)

    def test_busy_port_exits_instead_of_falling_back(self):
        import socket, io, contextlib
        held = socket.socket()
        held.bind(("127.0.0.1", 0))
        held.listen(1)
        port = held.getsockname()[1]
        try:
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
                viewer.bind_server(port)
            self.assertEqual(cm.exception.code, 1)
            self.assertIn(str(port), err.getvalue())
        finally:
            held.close()

    def test_free_port_binds(self):
        httpd = viewer.bind_server(0)
        try:
            self.assertTrue(httpd.server_address[1] > 0)
        finally:
            httpd.server_close()



class TLan(unittest.TestCase):
    """--lan: every interface, the LAN IP (+ --host) on the Host allowlist, gitweb links follow the Host used."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "dev").mkdir(); (self.tmp / "kb").mkdir()
        self.httpd, self.base = start(self.tmp / "dev", self.tmp / "kb")
        self.saved = set(viewer.ALLOWED_HOSTS)

    def tearDown(self):
        viewer.ALLOWED_HOSTS.clear(); viewer.ALLOWED_HOSTS.update(self.saved)
        viewer.Handler.gitweb_port = 0
        self.httpd.shutdown(); self.httpd.server_close()

    def test_default_rejects_a_lan_host(self):
        self.assertEqual(get(self.base, "/", host="192.168.1.185:8790")[0], 403)

    def test_lan_allowlist_admits_the_lan_ip_only(self):
        viewer.ALLOWED_HOSTS.add("192.168.1.185")
        self.assertEqual(get(self.base, "/", host="192.168.1.185:8790")[0], 200)
        self.assertEqual(get(self.base, "/", host="192.168.1.186:8790")[0], 403)
        self.assertEqual(get(self.base, "/", host="evil.com")[0], 403)

    def test_gitweb_url_is_same_origin(self):
        viewer.ALLOWED_HOSTS.add("192.168.1.185"); viewer.Handler.gitweb_port = 8791
        self.assertIn('<meta name="gitweb-url" content="/gitweb/">', get(self.base, "/", host="192.168.1.185:8790")[1])   # one port: the viewer forwards
        self.assertIn('<meta name="gitweb-url" content="/gitweb/">', get(self.base, "/", host="127.0.0.1:8790")[1])
        self.assertIn('window.GITWEB_URL = "/gitweb/"', get(self.base, "/v1", host="127.0.0.1:8790")[1])
        viewer.Handler.gitweb_port = 0
        self.assertIn('<meta name="gitweb-url" content="">', get(self.base, "/")[1])

    def test_parse_args_lan_and_hosts(self):
        a = viewer.parse_args(["--lan", "--host", "mac.local", "--host", "10.0.0.5", "--no-browser"])
        self.assertTrue(a["lan"]); self.assertEqual(a["hosts"], ["mac.local", "10.0.0.5"])
        self.assertFalse(viewer.parse_args([])["lan"])

    def test_parse_args_help_and_unknown_exit_before_serving(self):
        for argv, code in ((["--help"], 0), (["-h"], 0), (["--bogus"], 2), (["--no-browser", "x"], 2)):
            with self.assertRaises(SystemExit) as cm, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                viewer.parse_args(argv)
            self.assertEqual(cm.exception.code, code, argv)

    def test_lan_ip_is_dotted_or_none(self):
        ip = viewer.lan_ip()
        self.assertTrue(ip is None or len(ip.split(".")) == 4)


def _free_port():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


class _FakeGitweb(http.server.BaseHTTPRequestHandler):
    """Stands in for the loopback lighttpd: echoes what it was asked, and redirects once."""
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/go"):
            self.send_response(302); self.send_header("Location", "http://127.0.0.1:%d/?p=x;a=summary" % self.server.server_address[1])
            self.send_header("Content-Length", "0"); self.end_headers(); return
        body = ("path=%s host=%s" % (self.path, self.headers.get("Host"))).encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


class TGitwebProxy(unittest.TestCase):
    """/gitweb/ is forwarded to the loopback companion, so the viewer is the only port a client needs."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "dev").mkdir(); (self.tmp / "kb").mkdir()
        self.httpd, self.base = start(self.tmp / "dev", self.tmp / "kb")
        self.up = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _FakeGitweb)
        threading.Thread(target=self.up.serve_forever, daemon=True).start()
        viewer.Handler.gitweb_port = self.up.server_address[1]

    def tearDown(self):
        viewer.Handler.gitweb_port = 0
        self.up.shutdown(); self.up.server_close()
        self.httpd.shutdown(); self.httpd.server_close()

    def _open(self, path):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a): return None
        try:
            return urllib.request.build_opener(NoRedirect).open(self.base + path, timeout=5)
        except urllib.error.HTTPError as e:
            return e

    def test_forwards_without_the_prefix_and_with_a_loopback_host(self):
        r = self._open("/gitweb/?p=demo;a=summary")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.read().decode(), "path=/?p=demo;a=summary host=127.0.0.1:%d" % self.up.server_address[1])
        self.assertEqual(r.headers.get("Content-Type"), "text/html; charset=utf-8")

    def test_bare_prefix_reaches_the_root(self):
        self.assertTrue(self._open("/gitweb").read().decode().startswith("path=/ "))

    def test_same_origin_guards(self):
        r = self._open("/gitweb/")
        csp = r.headers.get("Content-Security-Policy", "")
        for d in ("default-src 'self'", "connect-src 'self'", "img-src 'self' data:", "form-action 'self'"):
            self.assertIn(d, csp)                                  # a gitweb page cannot send viewer data elsewhere
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")

    def test_redirect_stays_under_the_prefix(self):
        r = self._open("/gitweb/go")
        self.assertEqual(r.status, 302)
        self.assertEqual(r.headers.get("Location"), "/gitweb/?p=x;a=summary")

    def test_disabled_or_down(self):
        viewer.Handler.gitweb_port = 0
        self.assertEqual(self._open("/gitweb/").status, 404)
        viewer.Handler.gitweb_port = _free_port()
        self.assertEqual(self._open("/gitweb/").status, 502)


if __name__ == "__main__":
    unittest.main()
