#!/usr/bin/env python3
"""Tests for remap-shas.py. A throwaway git repo in a tmpdir; no repo/user data touched."""

import io
import importlib.util
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("remap_shas", os.path.join(HERE, "remap-shas.py"))
remap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remap)


def read(path):
    with open(path) as f:
        return f.read()


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = remap.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class History(unittest.TestCase):
    """base, then A B C D F; rewritten as A reworded, B+C squashed, D split in two, F dropped, G new."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        self.g("init", "-q", "-b", "main")
        self.commit({"base.txt": "base\n"}, "base")
        self.base = self.g("rev-parse", "HEAD")
        self.old = {}
        for name, files in [("A", {"a.txt": "a\n"}), ("B", {"b.txt": "b\n"}), ("C", {"c.txt": "c\n"}),
                            ("D", {"d.txt": "d\n", "e.txt": "e\n"}), ("F", {"f.txt": "f\n"})]:
            self.commit(files, name)
            self.old[name] = self.g("rev-parse", "HEAD")
        self.g("checkout", "-q", "-b", "new", self.base)
        self.new = {}
        self.pick(["A"], "A reworded")
        self.pick(["B", "C"], "B and C")
        self.g("cherry-pick", "-n", self.old["D"])
        self.g("reset", "-q")
        self.g("add", "d.txt")
        self.g("commit", "-q", "-m", "D part 1")
        self.new["D1"] = self.g("rev-parse", "HEAD")
        self.g("add", "e.txt")
        self.g("commit", "-q", "-m", "D part 2")
        self.new["D2"] = self.g("rev-parse", "HEAD")
        self.commit({"g.txt": "g\n"}, "G")
        self.map = os.path.join(self.tmp.name, "map.tsv")

    def tearDown(self):
        self.tmp.cleanup()

    def g(self, *args):
        return subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, files, msg):
        for name, text in files.items():
            with open(os.path.join(self.repo, name), "a") as f:
                f.write(text)
        self.g("add", "-A")
        self.g("commit", "-q", "-m", msg)

    def pick(self, names, msg):
        self.g("cherry-pick", "-n", *[self.old[n] for n in names])
        self.g("commit", "-q", "-m", msg)
        self.new[msg] = self.g("rev-parse", "HEAD")

    def pairs(self):
        out = {}
        for line in read(self.map).splitlines():
            if not line.startswith("#"):
                o, n, how = line.split("\t")[:3]
                out[o] = (n, how.split(":")[0])
        return out

    def test_map_pairs_each_kind_of_rewrite(self):
        code, out, _ = run("map", "--repo", self.repo, "--old", f"{self.base}..main", "--new", f"{self.base}..new", "-o", self.map)
        self.assertEqual(code, 0)
        p = self.pairs()
        self.assertEqual(p[self.old["A"]], (self.new["A reworded"], "patch-id"))
        self.assertEqual(p[self.old["B"]], (self.new["B and C"], "squash"))
        self.assertEqual(p[self.old["C"]], (self.new["B and C"], "squash"))
        self.assertEqual(p[self.old["D"]], (self.new["D2"], "split"))
        self.assertNotIn(self.old["F"], p)
        self.assertIn("unpaired " + self.old["F"][:9], out)

    def test_manual_fills_what_matching_cannot(self):
        manual = os.path.join(self.tmp.name, "manual")
        with open(manual, "w") as f:
            f.write(f"# dropped, its change went into G\n{self.old['F']} new\n")
        run("map", "--repo", self.repo, "--old", f"{self.base}..main", "--new", f"{self.base}..new",
            "--manual", manual, "-o", self.map)
        self.assertEqual(self.pairs()[self.old["F"]], (self.g("rev-parse", "new"), "manual"))

    def test_apply_replaces_old_ids_only(self):
        run("map", "--repo", self.repo, "--old", f"{self.base}..main", "--new", f"{self.base}..new", "-o", self.map)
        a, b = self.old["A"], self.new["A reworded"]
        doc = os.path.join(self.tmp.name, "doc.md")
        text = (f"commit `{a[:9]}`, full {a}, range {self.base[:9]}..{self.old['D'][:9]}, "
                f"time 1791658800, word deadbeefcafe, dropped {self.old['F'][:9]}\n")
        with open(doc, "w") as f:
            f.write(text)
        code, out, _ = run("apply", "--map", self.map, "--dry-run", doc)
        self.assertEqual((code, read(doc)), (0, text))
        self.assertIn("3 ids would be replaced", out)
        run("apply", "--map", self.map, doc)
        want = (f"commit `{b[:9]}`, full {b}, range {self.base[:9]}..{self.new['D2'][:9]}, "
                f"time 1791658800, word deadbeefcafe, dropped {self.old['F'][:9]}\n")
        self.assertEqual(read(doc), want)

    def test_apply_skips_excluded_files(self):
        run("map", "--repo", self.repo, "--old", f"{self.base}..main", "--new", f"{self.base}..new", "-o", self.map)
        d = os.path.join(self.tmp.name, "card")
        os.makedirs(d)
        for name in ("design.md", "human-messages.md"):
            with open(os.path.join(d, name), "w") as f:
                f.write(self.old["A"][:9] + "\n")
        run("apply", "--map", self.map, "--exclude", "human-messages.md", d)
        self.assertEqual(read(os.path.join(d, "design.md")), self.new["A reworded"][:9] + "\n")
        self.assertEqual(read(os.path.join(d, "human-messages.md")), self.old["A"][:9] + "\n")


class Apply(unittest.TestCase):
    def test_a_prefix_of_two_old_ids_stays(self):
        with tempfile.TemporaryDirectory() as tmp:
            m, doc = os.path.join(tmp, "map"), os.path.join(tmp, "doc")
            with open(m, "w") as f:
                f.write("a" * 7 + "1" * 33 + "\t" + "b" * 40 + "\tpatch-id\tx\n")
                f.write("a" * 7 + "2" * 33 + "\t" + "c" * 40 + "\tpatch-id\tx\n")
            with open(doc, "w") as f:
                f.write("aaaaaaa and aaaaaaa1\n")
            run("apply", "--map", m, doc)
            self.assertEqual(read(doc), "aaaaaaa and bbbbbbbb\n")


class Errors(unittest.TestCase):
    def test_git_failure_is_one_line(self):
        code, _, err = run("map", "--repo", "/nonexistent-remap-shas", "--old", "a..b", "--new", "c..d", "-o", os.devnull)
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("remap-shas: git ") and err.count("\n") == 1, err)


if __name__ == "__main__":
    unittest.main()
