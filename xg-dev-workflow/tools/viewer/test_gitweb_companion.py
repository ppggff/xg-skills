#!/usr/bin/env python3
"""Tests for the gitweb companion (card 003) — stdlib unittest, no third-party deps.

Unit tests cover the pure config/forest logic; one integration test starts the
real lighttpd (skipped if unavailable) to prove the generated config's Host
allowlist denies a non-localhost Host.

Run: python3 tools/viewer/test_gitweb_companion.py
"""
import importlib.util
import os
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("gwc", str(TOOLS / "gitweb-companion.py"))
gwc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gwc)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _git(cwd, *a):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, env=env)


class TUnit(unittest.TestCase):
    def test_uniq_suffixes_collisions(self):
        seen = set()
        self.assertEqual(gwc._uniq("a", seen), "a")
        self.assertEqual(gwc._uniq("a", seen), "a-2")
        self.assertEqual(gwc._uniq("a", seen), "a-3")

    def test_build_forest_symlinks_gitdirs_and_rebuilds(self):
        tmp = Path(tempfile.mkdtemp())
        gd1, gd2 = tmp / "r1.git", tmp / "r2.git"
        gd1.mkdir(); gd2.mkdir()
        root = gwc.build_forest(tmp / "rt", [("one", str(gd1)), ("two", str(gd2))])
        self.assertTrue((root / "one").is_symlink() and os.readlink(root / "one") == str(gd1))
        self.assertTrue((root / "two").is_symlink())
        # rebuild with a different set clears the old
        root = gwc.build_forest(tmp / "rt", [("one", str(gd1))])
        self.assertTrue((root / "one").is_symlink())
        self.assertFalse((root / "two").exists())

    def test_port_open_false_when_nothing_listens(self):
        self.assertFalse(gwc._port_open(_free_port()))

    def test_await_up_false_when_child_exits(self):
        # Low-1 / port-busy: lighttpd exits when it can't bind; a dead child must read as "not up".
        proc = subprocess.Popen(["true"])       # exits immediately, like a failed bind
        self.assertFalse(gwc._await_up(proc, _free_port(), timeout=1.0))

    def test_serves_gitweb_false_for_non_gitweb_listener(self):
        # the content check must reject a foreign listener that is not our gitweb
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        try:
            self.assertFalse(gwc._serves_gitweb(srv.getsockname()[1]))
        finally:
            srv.close()

    def test_write_configs_hardening(self):
        tmp = Path(tempfile.mkdtemp())
        gwc.write_configs(tmp, {"share": "/some/gitweb"}, 8791)
        gw = (tmp / "gitweb_config.perl").read_text()
        lt = (tmp / "lighttpd.conf").read_text()
        self.assertIn("snapshot", gw)                     # snapshot feature line present…
        self.assertIn("[]", gw)                            # …disabled
        self.assertIn('server.bind = "127.0.0.1"', lt)     # localhost only
        self.assertIn("mod_access", lt)                    # load-bearing for the Host guard
        self.assertIn('$HTTP["host"] !~', lt)              # Host allowlist condition
        self.assertIn("url.access-deny", lt)
        self.assertIn("PATH", lt)                          # git findable by the CGI


class TIntegration(unittest.TestCase):
    """Start the real lighttpd over a throwaway forest and check the Host allowlist."""
    def setUp(self):
        self.disc = gwc.discover()
        if not self.disc:
            self.skipTest("lighttpd/gitweb not available")
        self.tmp = Path(tempfile.mkdtemp())
        repo = self.tmp / "repo"; repo.mkdir()
        _git(repo, "init", "-q")
        (repo / "f.txt").write_text("hi", encoding="utf-8")
        _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "init")
        self.runtime = self.tmp / "rt"
        (self.runtime / "projectroot").mkdir(parents=True)
        (self.runtime / "projectroot" / "demo").symlink_to(repo / ".git")
        self.port = _free_port()
        self.lcfg = gwc.write_configs(self.runtime, self.disc, self.port)
        self.assertTrue(gwc._validate(self.disc["lighttpd"], self.lcfg), "generated lighttpd config invalid")
        self.proc = subprocess.Popen([self.disc["lighttpd"], "-D", "-f", str(self.lcfg)])
        time.sleep(1.0)

    def tearDown(self):
        if getattr(self, "proc", None):
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()

    def _get(self, host):
        req = urllib.request.Request("http://127.0.0.1:%d/" % self.port)
        req.add_header("Host", host)
        try:
            return urllib.request.urlopen(req, timeout=3).status
        except urllib.error.HTTPError as e:
            return e.code

    def test_host_allowlist_and_multirepo(self):
        self.assertTrue(gwc._await_up(self.proc, self.port))            # real gitweb → up (content-confirmed)
        self.assertEqual(self._get("127.0.0.1:%d" % self.port), 200)   # localhost allowed
        self.assertEqual(self._get("evil.com"), 403)                    # non-local Host denied (DNS-rebind guard)
        body = urllib.request.urlopen(
            urllib.request.Request("http://127.0.0.1:%d/" % self.port,
                                   headers={"Host": "127.0.0.1:%d" % self.port}), timeout=3
        ).read().decode("utf-8", "replace")
        self.assertIn("demo", body)                                     # symlinked git-dir listed with clean projid


if __name__ == "__main__":
    unittest.main(verbosity=2)
