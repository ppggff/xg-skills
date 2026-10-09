#!/usr/bin/env python3
"""Tests for active-card.py. Pure tmpdir fixtures; no repo/user data touched."""

import io
import importlib.util
import os
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("active_card", os.path.join(HERE, "active-card.py"))
active_card = importlib.util.module_from_spec(spec)
spec.loader.exec_module(active_card)


class ActiveCardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dev_root = os.path.join(self.tmp.name, "dev")
        self.state = os.path.join(self.tmp.name, "state")
        os.makedirs(os.path.join(self.dev_root, "xg-skills", "047-session-active-card"))
        os.makedirs(os.path.join(self.dev_root, "xg-skills", "notes"))
        os.makedirs(os.path.join(self.dev_root, "cbdb", "007-hybrid"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args, session="s1"):
        argv = ["--dev-root", self.dev_root, "--state-dir", self.state]
        if session is not None:
            argv += ["--session", session]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = active_card.main(argv + list(args))
        return code, out.getvalue(), err.getvalue()

    def pointer(self, session="s1"):
        path = os.path.join(self.state, session)
        return open(path).read() if os.path.exists(path) else None

    def test_set_by_number_resolves_the_card_dir(self):
        code, _, _ = self.run_tool("set", "xg-skills/047")
        self.assertEqual(code, 0)
        self.assertEqual(self.pointer(), "xg-skills/047-session-active-card\n")

    def test_set_by_dir_name(self):
        code, _, _ = self.run_tool("set", "cbdb/007-hybrid")
        self.assertEqual(code, 0)
        self.assertEqual(self.pointer(), "cbdb/007-hybrid\n")

    def test_set_unknown_card_fails_and_writes_nothing(self):
        for target in ("xg-skills/048", "xg-skills/notes", "nope/047", "047"):
            code, _, err = self.run_tool("set", target)
            self.assertNotEqual(code, 0, target)
            self.assertTrue(err, target)
        self.assertIsNone(self.pointer())

    def test_set_replaces_the_previous_card(self):
        self.run_tool("set", "xg-skills/047")
        self.run_tool("set", "cbdb/007")
        self.assertEqual(self.pointer(), "cbdb/007-hybrid\n")
        self.assertEqual(os.listdir(self.state), ["s1"])

    def test_get_prints_the_pointer(self):
        self.run_tool("set", "xg-skills/047")
        code, out, _ = self.run_tool("get")
        self.assertEqual((code, out), (0, "xg-skills/047-session-active-card\n"))

    def test_get_and_clear_without_a_pointer_are_quiet(self):
        self.assertEqual(self.run_tool("get")[:2], (0, ""))
        self.assertEqual(self.run_tool("clear")[0], 0)

    def test_clear_removes_only_this_session(self):
        self.run_tool("set", "xg-skills/047", session="s1")
        self.run_tool("set", "cbdb/007", session="s2")
        self.run_tool("clear", session="s1")
        self.assertIsNone(self.pointer("s1"))
        self.assertEqual(self.pointer("s2"), "cbdb/007-hybrid\n")

    def test_no_session_id_never_blocks(self):
        env = os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        try:
            for args in (("set", "xg-skills/047"), ("clear",), ("get",)):
                code, out, err = self.run_tool(*args, session=None)
                self.assertEqual(code, 0, args)
                self.assertEqual(out, "", args)
                self.assertIn("CLAUDE_CODE_SESSION_ID", err, args)
            self.assertFalse(os.path.exists(self.state))
        finally:
            if env is not None:
                os.environ["CLAUDE_CODE_SESSION_ID"] = env

    def test_session_comes_from_the_environment(self):
        old = os.environ.get("CLAUDE_CODE_SESSION_ID")
        os.environ["CLAUDE_CODE_SESSION_ID"] = "envsession"
        try:
            self.run_tool("set", "xg-skills/047", session=None)
            self.assertEqual(self.pointer("envsession"), "xg-skills/047-session-active-card\n")
        finally:
            if old is None:
                del os.environ["CLAUDE_CODE_SESSION_ID"]
            else:
                os.environ["CLAUDE_CODE_SESSION_ID"] = old

    def test_set_prunes_stale_pointers_of_other_sessions(self):
        os.makedirs(self.state)
        old, fresh = os.path.join(self.state, "old"), os.path.join(self.state, "fresh")
        for path in (old, fresh):
            with open(path, "w") as f:
                f.write("cbdb/007-hybrid\n")
        stale = time.time() - 31 * 86400
        os.utime(old, (stale, stale))
        self.run_tool("set", "xg-skills/047")
        self.assertEqual(sorted(os.listdir(self.state)), ["fresh", "s1"])

    def test_set_rejects_project_dot_segments(self):
        os.makedirs(os.path.join(self.tmp.name, "047-outside"))
        os.makedirs(os.path.join(self.dev_root, "047-self"))
        for target in ("../047", "./047"):
            code, _, err = self.run_tool("set", target)
            self.assertNotEqual(code, 0, target)
            self.assertTrue(err, target)
        self.assertIsNone(self.pointer())

    def test_set_rejects_names_readers_cannot_parse(self):
        os.makedirs(os.path.join(self.dev_root, "xg-skills", "048-中文"))
        code, _, err = self.run_tool("set", "xg-skills/048")
        self.assertNotEqual(code, 0)
        self.assertTrue(err)
        self.assertIsNone(self.pointer())

    def test_io_failures_never_block(self):
        blocker = os.path.join(self.tmp.name, "blocker")
        with open(blocker, "w") as f:
            f.write("x")
        argv = ["--dev-root", self.dev_root, "--state-dir", os.path.join(blocker, "state"), "--session", "s1"]
        for args in (["set", "xg-skills/047"], ["clear"], ["get"]):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = active_card.main(argv + args)
            self.assertEqual(code, 0, args)
            if args[0] == "set":
                self.assertIn("active-card:", err.getvalue())

    def test_prune_failure_does_not_undo_a_written_pointer(self):
        original = active_card.prune
        active_card.prune = lambda *_: (_ for _ in ()).throw(FileNotFoundError("raced"))
        try:
            code, _, _ = self.run_tool("set", "xg-skills/047")
        finally:
            active_card.prune = original
        self.assertEqual(code, 0)
        self.assertEqual(self.pointer(), "xg-skills/047-session-active-card\n")

    def test_session_id_cannot_escape_the_state_dir(self):
        code, _, err = self.run_tool("set", "xg-skills/047", session="../x")
        self.assertNotEqual(code, 0)
        self.assertTrue(err)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "x")))


if __name__ == "__main__":
    unittest.main()
