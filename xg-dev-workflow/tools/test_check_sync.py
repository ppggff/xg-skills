#!/usr/bin/env python3
"""Tests for check-sync.py (017 T2). Pure tmpdir fixtures; no repo/user data touched."""

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("check_sync", os.path.join(HERE, "check-sync.py"))
check_sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_sync)


class CheckSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.kb = os.path.join(self.root, "kb")
        os.makedirs(self.kb)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, data):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        return path

    def run_main(self, manifest_body):
        manifest = self.write("manifest.txt", manifest_body)
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            code = check_sync.main(
                ["--manifest", manifest, "--repo-root", self.root, "--kb-root", self.kb])
        return code, out.getvalue()

    def test_identical_pair_ok(self):
        self.write("a/x.md", "same\n")
        self.write("b/x.md", "same\n")
        code, out = self.run_main("a/x.md b/x.md\n")
        self.assertEqual(code, 0)
        self.assertIn("check-sync: ok", out)

    def test_drift_exits_1_and_names_pair(self):
        self.write("a/x.md", "one\n")
        self.write("b/x.md", "two\n")
        code, out = self.run_main("a/x.md b/x.md\n")
        self.assertEqual(code, 1)
        self.assertIn("DRIFT", out)
        self.assertIn("b/x.md != a/x.md", out)

    def test_missing_kb_member_notices_not_fails(self):
        self.write("a/x.md", "same\n")
        code, out = self.run_main("a/x.md $KB/x.md\n")
        self.assertEqual(code, 0)
        self.assertIn("NOTICE", out)
        self.assertIn("absent on this machine", out)

    def test_kb_member_present_is_compared(self):
        self.write("a/x.md", "one\n")
        self.write("kb/x.md", "two\n")
        code, out = self.run_main("a/x.md $KB/x.md\n")
        self.assertEqual(code, 1)
        self.assertIn("DRIFT", out)

    def test_missing_repo_member_is_drift(self):
        self.write("a/x.md", "same\n")
        code, out = self.run_main("a/x.md b/gone.md\n")
        self.assertEqual(code, 1)
        self.assertIn("missing", out)

    def test_three_way_set(self):
        self.write("a/x.py", "s\n")
        self.write("b/x.py", "s\n")
        self.write("c/x.py", "s\n")
        code, _ = self.run_main("a/x.py b/x.py c/x.py\n")
        self.assertEqual(code, 0)

    def test_comments_and_blank_lines_ignored(self):
        self.write("a/x.md", "s\n")
        self.write("b/x.md", "s\n")
        code, _ = self.run_main("# comment\n\na/x.md b/x.md  # trailing\n")
        self.assertEqual(code, 0)

    def test_single_member_set_is_manifest_error(self):
        code, out = self.run_main("a/only.md\n")
        self.assertEqual(code, 2)
        self.assertIn(">=2 paths", out)

    def test_missing_manifest_exits_2(self):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            code = check_sync.main(["--manifest", os.path.join(self.root, "nope.txt")])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
