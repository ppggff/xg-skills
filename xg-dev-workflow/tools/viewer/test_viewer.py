#!/usr/bin/env python3
"""P1 (server) acceptance tests for viewer.py — stdlib unittest, no third-party deps.

Run: python3 tools/viewer/test_viewer.py    (from the xg-dev-workflow dir, or anywhere).
Covers the curl-level contract of each endpoint against throwaway fixture trees / git repos.
P2 (shell JS) is verified manually in a browser — not here.
"""
import http.server
import importlib.util
import json
import os
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

    def test_shell_served_and_references_assets(self):
        code, body = get(self.base, "/")
        self.assertEqual(code, 200)
        self.assertIn("status viewer", body)
        self.assertIn('src="/assets/marked.min.js"', body)     # marked loaded eagerly
        self.assertNotIn('<script src="/assets/mermaid.min.js">', body)  # mermaid is lazy-loaded
        self.assertIn("Content-Security-Policy", body)

    def test_non_localhost_host_403(self):
        self.assertEqual(get(self.base, "/", host="evil.com")[0], 403)

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
                  "now", "next_progress", "blockers", "effective_next", "branch"):  # 003/R6
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

    def test_board_tasks_field_pinned(self):        # 007 T3/T4: tasks always present
        _, body = get(self.base, "/api/board")
        self.assertIn("tasks", json.loads(body)["foo"][0])

    def test_trace_ok_card(self):                    # 007 T4
        code, body = get(self.base, "/api/trace?card=foo/001")
        self.assertEqual(code, 200)
        d = json.loads(body)
        for k in ("card", "repo", "repo_anchor", "generated_at", "rows", "orphans", "error"):
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

    def test_assets_allowlist_and_traversal(self):
        self.assertEqual(get(self.base, "/assets/marked.min.js")[0], 200)
        self.assertEqual(get(self.base, "/assets/mermaid.min.js")[0], 200)
        self.assertEqual(get(self.base, "/assets/evil.js")[0], 404)        # not allowlisted
        self.assertEqual(get(self.base, "/assets/../viewer.py")[0], 404)   # traversal

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
