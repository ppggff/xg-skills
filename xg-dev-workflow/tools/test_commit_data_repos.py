#!/usr/bin/env python3
"""Unit tests for commit-data-repos.py — stdlib unittest, no third-party deps.

Run: python3 tools/test_commit_data_repos.py    (from the xg-dev-workflow dir, or anywhere).
Covers the pure scope-resolver layer (project<->pathspec mapping, porcelain -z parsing,
sweep grouping) against synthetic inputs, and the commit executor against throwaway
tempfile git repos — same fixture style as test_workflow_status.py.
"""
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("commit_data_repos", str(TOOLS / "commit-data-repos.py"))
cdr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cdr)

# Isolate from the developer machine's global git config (aliases, excludesfile — a stray
# global gitignore rule can shadow a fixture directory name on a case-insensitive filesystem).
GIT_ENV = dict(os.environ,
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def init_repo(files=None):
    """A tempdir git repo, optionally seeded with an initial commit of `files`."""
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", d], check=True, env=GIT_ENV)
    if files:
        for rel, content in files.items():
            p = Path(d) / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        subprocess.run(["git", "-C", d, "add", "-A"], check=True, env=GIT_ENV)
        subprocess.run(["git", "-C", d, "commit", "-q", "-m", "init"], check=True, env=GIT_ENV)
    return Path(d)


def dirty(repo, rel, content="changed\n"):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def log_paths(repo):
    """Files touched by the tip commit."""
    out = subprocess.run(["git", "-C", str(repo), "show", "--stat", "--format=", "HEAD"],
                          capture_output=True, text=True, env=GIT_ENV).stdout
    return [line.strip().split(" |")[0] for line in out.splitlines() if line.strip()]


class ScopedPathspecs(unittest.TestCase):
    def test_docs_kind_is_bare_project_prefix(self):
        self.assertEqual(cdr.scoped_pathspecs("docs", "xg-skills"), ["xg-skills"])

    def test_kb_kind_is_raw_and_wiki(self):
        self.assertEqual(cdr.scoped_pathspecs("kb", "cbdb"), ["raw/cbdb", "wiki/cbdb"])


class ParsePorcelainZ(unittest.TestCase):
    def test_regular_untracked_deleted(self):
        raw = " M a.txt\x00?? b.txt\x00 D c.txt\x00"
        self.assertEqual(cdr.parse_porcelain_z(raw), ["a.txt", "b.txt", "c.txt"])

    def test_rename_consumes_orig_path_field(self):
        raw = "RM new.txt\x00old.txt\x00"
        self.assertEqual(cdr.parse_porcelain_z(raw), ["new.txt"])

    def test_chinese_filename(self):
        raw = "?? 中文目录/文件.txt\x00"
        self.assertEqual(cdr.parse_porcelain_z(raw), ["中文目录/文件.txt"])

    def test_empty(self):
        self.assertEqual(cdr.parse_porcelain_z(""), [])


class GroupOf(unittest.TestCase):
    def test_docs_kind_top_level_dir_is_group(self):
        self.assertEqual(cdr.group_of("xg-skills/008-x/plan.md", "docs"), "xg-skills")

    def test_docs_kind_root_file_is_root_group(self):
        self.assertEqual(cdr.group_of("index.md", "docs"), "(root)")

    def test_kb_kind_raw_and_wiki_merge_to_same_project(self):
        self.assertEqual(cdr.group_of("raw/cbdb/note.md", "kb"), "cbdb")
        self.assertEqual(cdr.group_of("wiki/cbdb/concept.md", "kb"), "cbdb")

    def test_kb_kind_root_fallback(self):
        self.assertEqual(cdr.group_of("README.md", "kb"), "(root)")
        self.assertEqual(cdr.group_of("raw/loose.md", "kb"), "(root)")


class ExistingPathspecs(unittest.TestCase):
    def test_unknown_project_is_empty(self):
        repo = init_repo({"a/f.txt": "1\n"})
        self.assertEqual(cdr.existing_pathspecs(repo, cdr.scoped_pathspecs("docs", "ghost")), [])

    def test_known_project_kept(self):
        repo = init_repo({"a/f.txt": "1\n"})
        self.assertEqual(cdr.existing_pathspecs(repo, cdr.scoped_pathspecs("docs", "a")), ["a"])

    def test_deleted_but_still_tracked_path_kept(self):
        repo = init_repo({"a/f.txt": "1\n"})
        os.remove(repo / "a" / "f.txt")
        self.assertEqual(cdr.existing_pathspecs(repo, cdr.scoped_pathspecs("docs", "a")), ["a"])

    def test_kb_partial_match_kept_partial_dropped(self):
        repo = init_repo({"raw/cbdb/note.md": "1\n"})  # only raw/ exists, no wiki/
        self.assertEqual(cdr.existing_pathspecs(repo, cdr.scoped_pathspecs("kb", "cbdb")),
                          ["raw/cbdb"])


class SweepGroups(unittest.TestCase):
    def test_groups_by_project_with_root_fallback(self):
        repo = init_repo({"a/f.txt": "1\n", "b/g.txt": "1\n", "index.md": "1\n"})
        dirty(repo, "a/f.txt", "2\n")
        (repo / "b" / "new.txt").write_text("new\n", encoding="utf-8")
        dirty(repo, "index.md", "2\n")
        groups = cdr.sweep_groups(repo, "docs")
        self.assertEqual(set(groups), {"a", "b", "(root)"})
        self.assertEqual(groups["a"], ["a/f.txt"])
        self.assertEqual(groups["b"], ["b/new.txt"])
        self.assertEqual(groups["(root)"], ["index.md"])

    def test_kb_raw_wiki_merge_into_one_group(self):
        repo = init_repo({"raw/cbdb/note.md": "1\n"})
        dirty(repo, "raw/cbdb/note.md", "2\n")
        (repo / "wiki" / "cbdb").mkdir(parents=True)
        (repo / "wiki" / "cbdb" / "concept.md").write_text("new\n", encoding="utf-8")
        groups = cdr.sweep_groups(repo, "kb")
        self.assertEqual(set(groups), {"cbdb"})
        self.assertEqual(sorted(groups["cbdb"]), ["raw/cbdb/note.md", "wiki/cbdb/concept.md"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
