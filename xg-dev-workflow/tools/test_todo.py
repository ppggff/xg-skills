#!/usr/bin/env python3
"""Tests for todo.py. Pure tmpdir fixtures; no repo/user data touched."""

import io
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("todo", os.path.join(HERE, "todo.py"))
todo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(todo)

SV_JS = os.path.join(HERE, "viewer", "sv.js")
NOW = "2026-10-13 09:30"


class TodoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dev_root = os.path.join(self.tmp.name, "dev")
        self.tdir = os.path.join(self.dev_root, "todo")
        os.makedirs(self.tdir)
        home = mock.patch.dict(os.environ, {"HOME": os.path.join(self.tmp.name, "home")})
        home.start()
        self.addCleanup(home.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args, stdin="", projects=("xg-skills", "cbdb"), now=NOW):
        argv = ["--dev-root", self.dev_root] + (["--now", now] if now else []) + list(args)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(todo, "known_projects", lambda: set(projects)), \
                mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out), redirect_stderr(err):
            code = todo.main(argv)
        return code, out.getvalue(), err.getvalue()

    def ok(self, *args, stdin="", now=NOW):
        code, out, err = self.run_tool(*args, stdin=stdin, now=now)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def read(self, name="inbox.md"):
        with open(os.path.join(self.tdir, name), encoding="utf-8") as f:
            return f.read()

    def write(self, name, text):
        with open(os.path.join(self.tdir, name), "w", encoding="utf-8") as f:
            f.write(text)

    # --- add ---

    def test_add_creates_inbox_with_project_and_stamp(self):
        rec = self.ok("add", "--project", "xg-skills", stdin="run the viewer tests\n")
        self.assertEqual(self.read(), "# inbox\n\n- [ ] run the viewer tests @xg-skills ➕ 2026-10-13 09:30\n")
        self.assertEqual(rec, {"file": "inbox.md", "created": NOW, "key": "run the viewer tests @xg-skills",
                               "text": "run the viewer tests", "listed": "run the viewer tests", "project": "xg-skills"})

    def test_a_new_file_is_titled_after_its_name(self):
        self.ok("add", "--file", "work log.md", stdin="x")
        self.assertTrue(self.read("work log.md").startswith("# work log\n\n- [ ] x"))

    def test_add_without_project_has_no_tag(self):
        rec = self.ok("add", stdin="plain")
        self.assertIn("- [ ] plain ➕ 2026-10-13 09:30\n", self.read())
        self.assertIsNone(rec["project"])

    def test_add_does_not_repeat_a_tag_the_text_has(self):
        self.ok("add", "--project", "cbdb", stdin="ask about @cbdb locks")
        self.assertIn("- [ ] ask about @cbdb locks ➕", self.read())

    def test_add_appends_to_an_existing_file_keeping_its_lines(self):
        self.write("inbox.md", "# test\n\n- [ ] old @cbdb  ➕ 2026-10-12 19:14")
        self.ok("add", stdin="new one")
        self.assertEqual(self.read(), "# test\n\n- [ ] old @cbdb  ➕ 2026-10-12 19:14\n- [ ] new one ➕ 2026-10-13 09:30\n")

    def test_add_resolves_project_from_cwd(self):
        with mock.patch.object(todo, "project_of_cwd", lambda cwd: "cbdb" if cwd == "/code/cbdb" else None):
            rec = self.ok("add", "--cwd", "/code/cbdb", stdin="x")
            self.assertEqual(rec["project"], "cbdb")
            self.assertIsNone(self.ok("add", "--cwd", "/elsewhere", stdin="y")["project"])

    def test_add_refuses_empty_text_and_bad_file_names(self):
        self.assertNotEqual(self.run_tool("add", stdin="  \n\n")[0], 0)
        for name in ("../x.md", ".hidden.md", "a/b.md", "notes.txt"):
            code, out, err = self.run_tool("add", "--file", name, stdin="x")
            self.assertNotEqual(code, 0, name)
            self.assertEqual(out, "")
            self.assertTrue(err.strip())

    # --- multi-line round trip ---

    TRICKY = "first line @alice\nsecond\n\n\n```\n- [ ] not an item\n* [x] nor this\n1. [ ] nor this\n\\escaped already\n    deep"

    def test_multiline_round_trip_and_done(self):
        rec = self.ok("add", "--project", "xg-skills", stdin=self.TRICKY)
        self.ok("add", stdin="after")
        items = self.ok("list", "--open")
        self.assertEqual([i["text"] for i in items], [self.TRICKY, "after"])
        self.assertEqual(items[0]["key"], rec["key"])
        res = self.ok("done", "--file", "inbox.md", "--created", NOW, "--key", rec["key"])
        self.assertTrue(res["ok"])
        self.assertEqual([i["text"] for i in self.ok("list", "--open")], ["after"])
        lines = self.read().split("\n")
        self.assertTrue(lines[2].startswith("- [x] first line @alice @xg-skills ➕ 2026-10-13 09:30 ✅ 2026-10-13"))

    def test_continuation_lines_are_indented_and_escaped(self):
        self.ok("add", stdin="a\n- [ ] b\n\\c")
        self.assertIn("- [ ] a ➕ 2026-10-13 09:30\n    \\- [ ] b\n    \\\\c\n", self.read())

    def test_carriage_returns_and_line_separators_become_newlines(self):
        rec = self.ok("add", stdin="one\rtwo\r\nthree\u2028four")
        self.assertEqual(rec["text"], "one\ntwo\nthree\nfour")
        self.assertEqual(self.ok("list")[0]["text"], "one\ntwo\nthree\nfour")
        self.assertNotIn("\r", self.read())
        self.assertTrue(self.ok("done", "--file", "inbox.md", "--created", rec["created"], "--key", rec["key"])["ok"])

    def test_a_first_line_with_its_own_created_mark_still_matches(self):
        rec = self.ok("add", stdin="meet ➕ 2026-01-01 about it")
        got = self.ok("list")[0]
        self.assertEqual((got["created"], got["key"]), (rec["created"], rec["key"]))
        self.assertTrue(self.ok("done", "--file", "inbox.md", "--created", rec["created"], "--key", rec["key"])["ok"])

    def test_a_trailing_project_tag_in_the_text_round_trips(self):
        cases = [("fix bug @xg-skills", ["--project", "xg-skills"]), ("ping @xg-skills", []), ("x @xg-skills", ["--project", "cbdb"]),
                 ("ask about @cbdb locks", ["--project", "cbdb"])]
        for text, extra in cases:
            self.ok("add", *extra, stdin=text)
        self.assertEqual([i["text"] for i in self.ok("list")], [t for t, _ in cases])

    def test_add_refuses_an_item_an_unclosed_fence_would_hide(self):
        self.write("inbox.md", "```\nnotes\n")
        code, out, err = self.run_tool("add", stdin="hidden")
        self.assertNotEqual(code, 0)
        self.assertIn("fence", err)
        self.assertEqual(self.read(), "```\nnotes\n")

    def test_links_are_refused(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(outside)
        with open(os.path.join(outside, "real.md"), "w") as f:
            f.write("- [ ] x\n")
        os.symlink(os.path.join(outside, "real.md"), os.path.join(self.tdir, "link.md"))
        self.assertNotEqual(self.run_tool("add", "--file", "link.md", stdin="y")[0], 0)
        shutil.rmtree(self.tdir)
        os.symlink(outside, self.tdir)
        self.assertNotEqual(self.run_tool("add", stdin="y")[0], 0)
        self.assertEqual(os.listdir(outside), ["real.md"])

    def test_the_lock_lives_under_the_shared_config_dir_not_tmp(self):
        path = todo.lock_path(self.tdir)
        self.assertTrue(path.startswith(os.path.join(self.tmp.name, "home", ".config", "xg-knowledge-wiki") + os.sep), path)

    def test_stamps_carry_seconds_by_default_and_parse_with_or_without_them(self):
        rec = self.ok("add", stdin="timed", now=None)
        self.assertRegex(rec["created"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.ok("add", stdin="exact", now="2026-10-13 09:30:15")
        self.assertIn("- [ ] exact ➕ 2026-10-13 09:30:15\n", self.read())
        got = {i["text"]: i for i in self.ok("list")}
        self.assertEqual(got["exact"]["created"], "2026-10-13 09:30:15")
        self.assertEqual(got["exact"]["key"], "exact")
        res = self.ok("done", "--file", "inbox.md", "--created", "2026-10-13 09:30:15", "--key", "exact", now="2026-10-14 08:00:01")
        self.assertTrue(res["ok"])
        self.assertIn("- [x] exact ➕ 2026-10-13 09:30:15 ✅ 2026-10-14\n", self.read())

    def test_add_returns_the_text_list_will_read_back(self):
        rec = self.ok("add", "--project", "xg-skills", stdin="ship 📅 2026-10-20 ⏫ it\nsecond line")
        self.assertEqual(rec["text"], "ship 📅 2026-10-20 ⏫ it\nsecond line")
        self.assertEqual(rec["listed"], self.ok("list")[0]["text"])
        self.assertEqual(rec["listed"], "ship it\nsecond line")

    # --- list ---

    def test_list_reads_every_todo_file_and_skips_others(self):
        self.write("inbox.md", "- [ ] one @cbdb ➕ 2026-10-12 10:00\n- [x] gone ✅ 2026-10-12\n")
        self.write("work.md", "# w\n\n- [ ] two\n  - [ ] sub\n")
        self.write(".hidden.md", "- [ ] hidden\n")
        self.write("notes.txt", "- [ ] txt\n")
        items = self.ok("list")
        self.assertEqual([(i["file"], i["text"], i["done"]) for i in items],
                         [("inbox.md", "one", False), ("inbox.md", "gone", True), ("work.md", "two", False), ("work.md", "sub", False)])
        self.assertEqual(items[0]["project"], "cbdb")
        self.assertEqual(items[0]["created"], "2026-10-12 10:00")
        self.assertEqual(items[2]["created"], "")
        self.assertEqual([i["text"] for i in self.ok("list", "--open")], ["one", "two", "sub"])
        self.assertEqual([i["text"] for i in self.ok("list", "--open", "--project", "cbdb")], ["one"])

    def test_list_reports_each_item_depth(self):
        self.write("work.md", "- [ ] top\n  - [ ] sub\n    - [x] subsub\n\t- [ ] tabbed\n")
        self.assertEqual([(i["text"], i["depth"]) for i in self.ok("list")], [("top", 0), ("sub", 2), ("subsub", 4), ("tabbed", 1)])

    def test_list_keeps_a_trailing_tag_that_is_not_a_project(self):
        self.write("inbox.md", "- [ ] ping @alice ➕ 2026-10-12 10:00\n")
        self.assertEqual(self.ok("list")[0]["text"], "ping @alice")

    def test_list_ignores_items_inside_code_fences(self):
        self.write("inbox.md", "```\n- [ ] fenced\n```\n- [ ] real\n")
        self.assertEqual([i["text"] for i in self.ok("list")], ["real"])

    def test_writing_leaves_only_the_todo_file_in_the_dir(self):
        self.ok("add", stdin="x")
        self.ok("done", "--file", "inbox.md", "--created", NOW, "--key", "x")
        self.assertEqual(os.listdir(self.tdir), ["inbox.md"])

    def test_list_skips_a_file_that_is_not_utf8(self):
        self.write("inbox.md", "- [ ] good\n")
        with open(os.path.join(self.tdir, "bad.md"), "wb") as f:
            f.write(b"- [ ] \xff\xfe\n")
        code, out, err = self.run_tool("list")
        self.assertEqual(code, 0)
        self.assertEqual([i["text"] for i in json.loads(out)], ["good"])
        self.assertIn("bad.md", err)

    def test_list_with_no_todo_dir_is_empty(self):
        shutil.rmtree(self.tdir)
        self.assertEqual(self.ok("list"), [])

    # --- done ---

    def test_done_matches_first_line_only(self):
        rec = self.ok("add", stdin="A")
        self.write("inbox.md", self.read() + "    orphan continuation\n")
        self.assertTrue(self.ok("done", "--file", "inbox.md", "--created", NOW, "--key", rec["key"])["ok"])

    def test_done_not_found_is_reported_not_failed(self):
        self.ok("add", stdin="A")
        res = self.ok("done", "--file", "inbox.md", "--created", "2026-01-01 00:00", "--key", "A")
        self.assertEqual(res, {"ok": False, "reason": "not-found"})
        self.assertEqual(self.ok("done", "--file", "missing.md", "--created", NOW, "--key", "A")["reason"], "not-found")

    def test_done_with_empty_created_matches_hand_written_items(self):
        self.write("work.md", "- [ ] hand  written\n")
        key = self.ok("list")[0]["key"]
        self.assertEqual(key, "hand written")
        self.assertTrue(self.ok("done", "--file", "work.md", "--created", "", "--key", key)["ok"])
        self.assertIn("- [x] hand  written ✅ 2026-10-13", self.read("work.md"))

    def test_done_skips_items_already_done(self):
        self.write("inbox.md", "- [x] A ➕ 2026-10-13 09:30 ✅ 2026-10-13\n- [ ] A ➕ 2026-10-13 09:30\n")
        self.assertEqual(self.ok("done", "--file", "inbox.md", "--created", NOW, "--key", "A")["line"], 1)

    # --- concurrency ---

    def test_a_write_between_read_and_replace_is_kept(self):
        self.write("inbox.md", "- [ ] mine ➕ 2026-10-13 09:30\n")
        real_read = todo.read_file
        calls = {"n": 0}

        def racing_read(path):
            got = real_read(path)
            calls["n"] += 1
            if calls["n"] == 1:
                with open(path, "a", encoding="utf-8") as f:
                    f.write("- [ ] theirs\n")
                st = os.stat(path)
                os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000))
            return got

        with mock.patch.object(todo, "read_file", racing_read):
            self.ok("done", "--file", "inbox.md", "--created", NOW, "--key", "mine")
        text = self.read()
        self.assertIn("- [ ] theirs", text)
        self.assertIn("- [x] mine", text)
        self.assertGreaterEqual(calls["n"], 2)

    def test_a_replace_keeping_the_mtime_is_still_seen(self):
        path = os.path.join(self.tdir, "inbox.md")
        self.write("inbox.md", "- [ ] a\n")
        _, stamp = todo.read_file(path)
        st = os.stat(path)
        self.write("other.md", "- [ ] b\n")
        os.replace(os.path.join(self.tdir, "other.md"), path)
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
        self.assertNotEqual(todo.read_file(path)[1], stamp)

    def test_a_file_that_keeps_changing_fails_without_writing(self):
        self.write("inbox.md", "- [ ] mine ➕ 2026-10-13 09:30\n")
        real_read = todo.read_file

        def always_racing(path):
            got = real_read(path)
            st = os.stat(path)
            os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000))
            return got

        with mock.patch.object(todo, "read_file", always_racing):
            code, out, err = self.run_tool("done", "--file", "inbox.md", "--created", NOW, "--key", "mine")
        self.assertNotEqual(code, 0)
        self.assertIn("kept changing", err)
        self.assertEqual(self.read(), "- [ ] mine ➕ 2026-10-13 09:30\n")

    # --- viewer agreement ---

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_viewer_parses_what_the_script_writes(self):
        self.write("inbox.md", "# t\n\n- [ ] before\n")
        rec = self.ok("add", "--project", "xg-skills", stdin=self.TRICKY)
        self.ok("add", stdin="after")
        js = ("const SV=require(process.argv[1]);const t=require('fs').readFileSync(process.argv[2],'utf8');"
              "console.log(JSON.stringify(SV.parseTodo(t).map(i=>({text:i.text,tags:i.tags,depth:i.depth,meta:SV.todoMeta(i.text)}))))")
        out = subprocess.run(["node", "-e", js, SV_JS, os.path.join(self.tdir, "inbox.md")],
                             capture_output=True, text=True, check=True).stdout
        seen = json.loads(out)
        self.assertEqual(len(seen), 3)
        self.assertEqual([s["depth"] for s in seen], [0, 0, 0])
        self.assertEqual(seen[1]["meta"]["text"], rec["key"])
        self.assertEqual(seen[1]["meta"]["created"], NOW)
        self.assertEqual(seen[1]["tags"], ["alice", "xg-skills"])
        self.assertEqual(seen[2]["meta"]["text"], "after")


if __name__ == "__main__":
    unittest.main()
