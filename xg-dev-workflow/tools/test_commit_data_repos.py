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

# Isolate from the developer machine's global git config (aliases, excludesfile — a stray
# global gitignore rule can shadow a fixture directory name on a case-insensitive filesystem).
# Set process-wide, not just on GIT_ENV below: cdr.commit_repo() runs in-process and its own
# git() calls inherit os.environ directly, so a GIT_ENV-only override wouldn't reach them.
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_SYSTEM"] = os.devnull

TOOLS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("commit_data_repos", str(TOOLS / "commit-data-repos.py"))
cdr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cdr)

GIT_ENV = dict(os.environ,
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


def commits_with_files(repo):
    """[(subject, [files]), ...] tip-first — NUL-delimited to survive git's own blank-line
    formatting inside `--name-only` output (no separator otherwise distinguishes a file list
    from the next commit's subject)."""
    out = subprocess.run(["git", "-C", str(repo), "log", "--name-only", "--format=%x00%s"],
                          capture_output=True, text=True, env=GIT_ENV).stdout
    result = []
    for chunk in out.split("\x00"):
        lines = [l for l in chunk.splitlines() if l.strip()]
        if lines:
            result.append((lines[0], lines[1:]))
    return result


def log_paths(repo):
    """Files touched by the tip commit."""
    out = subprocess.run(["git", "-C", str(repo), "show", "--stat", "--format=", "HEAD"],
                          capture_output=True, text=True, env=GIT_ENV).stdout
    return [line.split(" |")[0].strip() for line in out.splitlines() if " | " in line]


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


class CommitRepoScoped(unittest.TestCase):
    def _two_projects_dirty(self):
        repo = init_repo({"projA/f.txt": "1\n", "projB/g.txt": "1\n"})
        dirty(repo, "projA/f.txt")
        dirty(repo, "projB/g.txt")
        return repo

    def test_scoped_commit_hits_only_project_prefix(self):
        repo = self._two_projects_dirty()
        cdr.commit_repo(repo, "label", "docs", "msg", project="projA")
        self.assertEqual(log_paths(repo), ["projA/f.txt"])

    def test_out_of_scope_files_remain_and_are_warned(self):
        repo = self._two_projects_dirty()
        lines = cdr.commit_repo(repo, "label", "docs", "msg", project="projA")
        status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                 capture_output=True, text=True, env=GIT_ENV).stdout
        self.assertIn("projB/g.txt", status)
        self.assertTrue(any("projB/g.txt" in l for l in lines))

    def test_prestaged_out_of_scope_not_swept_in(self):
        repo = self._two_projects_dirty()
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=GIT_ENV)
        cdr.commit_repo(repo, "label", "docs", "msg", project="projA")
        self.assertEqual(log_paths(repo), ["projA/f.txt"])
        status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                 capture_output=True, text=True, env=GIT_ENV).stdout
        self.assertIn("projB/g.txt", status)

    def test_unknown_project_reports_nothing_to_commit(self):
        repo = self._two_projects_dirty()
        lines = cdr.commit_repo(repo, "label", "docs", "msg", project="ghost")
        self.assertTrue(any("nothing to commit" in l for l in lines))
        log = subprocess.run(["git", "-C", str(repo), "log", "--oneline"],
                              capture_output=True, text=True, env=GIT_ENV).stdout
        self.assertEqual(len(log.splitlines()), 1)  # only the fixture's init commit

    def test_kb_kind_commits_both_raw_and_wiki(self):
        repo = init_repo({"raw/cbdb/note.md": "1\n", "wiki/cbdb/concept.md": "1\n"})
        dirty(repo, "raw/cbdb/note.md")
        dirty(repo, "wiki/cbdb/concept.md")
        cdr.commit_repo(repo, "label", "kb", "msg", project="cbdb")
        self.assertEqual(sorted(log_paths(repo)), ["raw/cbdb/note.md", "wiki/cbdb/concept.md"])

    def test_fresh_repo_init_commits_gitignore_with_scoped_project(self):
        d = tempfile.mkdtemp()
        repo = Path(d)
        (repo / "projA").mkdir()
        (repo / "projA" / "f.txt").write_text("1\n", encoding="utf-8")
        cdr.commit_repo(repo, "label", "docs", "msg", project="projA")
        self.assertTrue((repo / ".gitignore").exists())
        self.assertEqual(sorted(log_paths(repo)), [".gitignore", "projA/f.txt"])


class CommitRepoSweep(unittest.TestCase):
    def test_sweep_splits_into_one_commit_per_group_and_leaves_repo_clean(self):
        repo = init_repo({"projA/f.txt": "1\n", "projB/g.txt": "1\n"})
        dirty(repo, "projA/f.txt")
        dirty(repo, "projB/g.txt")
        cdr.commit_repo(repo, "label", "docs", "msg")
        log = subprocess.run(["git", "-C", str(repo), "log", "--oneline"],
                              capture_output=True, text=True, env=GIT_ENV).stdout.splitlines()
        self.assertEqual(len(log), 3)  # fixture init + 2 group commits
        subjects = [l.split(" ", 1)[1] for l in log]
        self.assertTrue(any("[projA]" in s for s in subjects))
        self.assertTrue(any("[projB]" in s for s in subjects))
        status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                 capture_output=True, text=True, env=GIT_ENV).stdout
        self.assertEqual(status, "")

    def test_each_commit_touches_only_its_own_group(self):
        repo = init_repo({"projA/f.txt": "1\n", "projB/g.txt": "1\n"})
        dirty(repo, "projA/f.txt")
        dirty(repo, "projB/g.txt")
        cdr.commit_repo(repo, "label", "docs", "msg")
        by_subject = dict(commits_with_files(repo))
        self.assertEqual(next(f for s, f in by_subject.items() if "[projA]" in s), ["projA/f.txt"])
        self.assertEqual(next(f for s, f in by_subject.items() if "[projB]" in s), ["projB/g.txt"])

    def test_root_stragglers_get_their_own_commit(self):
        repo = init_repo({"projA/f.txt": "1\n", "index.md": "1\n"})
        dirty(repo, "projA/f.txt")
        dirty(repo, "index.md")
        cdr.commit_repo(repo, "label", "docs", "msg")
        by_subject = dict(commits_with_files(repo))
        self.assertEqual(next(f for s, f in by_subject.items() if "[(root)]" in s), ["index.md"])

    def test_fresh_repo_init_sweep_commits_gitignore(self):
        d = tempfile.mkdtemp()
        repo = Path(d)
        (repo / "projA").mkdir()
        (repo / "projA" / "f.txt").write_text("1\n", encoding="utf-8")
        lines = cdr.commit_repo(repo, "label", "docs", "msg")
        self.assertTrue((repo / ".gitignore").exists())
        by_subject = dict(commits_with_files(repo))
        self.assertEqual(next(f for s, f in by_subject.items() if "[(root)]" in s), [".gitignore"])
        self.assertEqual(next(f for s, f in by_subject.items() if "[projA]" in s), ["projA/f.txt"])
        status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                 capture_output=True, text=True, env=GIT_ENV).stdout
        self.assertEqual(status, "")
        self.assertFalse(any("nothing committed" in l for l in lines))

    def test_clean_repo_reports_nothing_to_commit(self):
        repo = init_repo({"projA/f.txt": "1\n"})
        lines = cdr.commit_repo(repo, "label", "docs", "msg")
        self.assertTrue(any("clean" in l or "nothing to commit" in l for l in lines))

    def test_message_and_reason_regression(self):
        # mirrors what main() does with --message/--reason before calling commit_repo;
        # --only is main()'s target-list filter (untested here — commit_repo has no
        # notion of it), exercised by calling commit_repo for just one repo and
        # checking the other, untouched, stays dirty.
        kb = init_repo({"raw/cbdb/note.md": "1\n"})
        docs = init_repo({"projA/f.txt": "1\n"})
        dirty(kb, "raw/cbdb/note.md")
        dirty(docs, "projA/f.txt")
        lines_kb = cdr.commit_repo(kb, "knowledge (KB)", "kb", "custom msg\n\nbecause reasons")
        self.assertTrue(any("committed" in l for l in lines_kb))
        subject = subprocess.run(["git", "-C", str(kb), "log", "-1", "--format=%s"],
                                  capture_output=True, text=True, env=GIT_ENV).stdout
        body = subprocess.run(["git", "-C", str(kb), "log", "-1", "--format=%B"],
                               capture_output=True, text=True, env=GIT_ENV).stdout
        # D2: the [group] tag is what `git log --oneline` shows for sweep attribution —
        # it must land on the subject line, not get buried after a multi-line --reason body.
        self.assertIn("custom msg", subject)
        self.assertIn("[cbdb]", subject)
        self.assertIn("because reasons", body)
        status = subprocess.run(["git", "-C", str(docs), "status", "--porcelain"],
                                 capture_output=True, text=True, env=GIT_ENV).stdout
        self.assertNotEqual(status, "")  # untouched by the kb-only call


class CLIIntegration(unittest.TestCase):
    """Drives the real script via subprocess — main()'s argparse/config wiring is the
    tool's actual public interface; the rest of this suite exercises commit_repo()
    directly and never proves --only/config-loading/--project actually connect."""

    def _fake_home(self, kb_files, docs_files):
        home = tempfile.mkdtemp()
        cfg_dir = Path(home) / ".config" / "xg-knowledge-wiki"
        cfg_dir.mkdir(parents=True)
        kb, docs = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        (cfg_dir / "config.yaml").write_text(f"root: {kb}\ndev_root: {docs}\n", encoding="utf-8")
        for rel, content in kb_files.items():
            p = kb / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        for rel, content in docs_files.items():
            p = docs / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return home, kb, docs

    def _run(self, home, *args):
        env = dict(GIT_ENV, HOME=home)
        return subprocess.run(["python3", str(TOOLS / "commit-data-repos.py"), *args],
                               capture_output=True, text=True, env=env)

    def test_project_flag_scopes_both_repos(self):
        # same project name ("cbdb") dirty in both repos — R4: --project applies to both
        home, kb, docs = self._fake_home({"raw/cbdb/note.md": "1\n"}, {"cbdb/plan.md": "1\n"})
        res = self._run(home, "--project", "cbdb")
        self.assertEqual(res.returncode, 0)
        self.assertIn("committed", res.stdout)
        # both repos are freshly created here, so D3 rides .gitignore along in each
        self.assertEqual(log_paths(kb), [".gitignore", "raw/cbdb/note.md"])
        self.assertEqual(log_paths(docs), [".gitignore", "cbdb/plan.md"])

    def test_only_selects_a_single_repo(self):
        home, kb, docs = self._fake_home({"raw/cbdb/note.md": "1\n"}, {"projA/f.txt": "1\n"})
        res = self._run(home, "--only", "kb", "--project", "cbdb")
        self.assertEqual(res.returncode, 0)
        self.assertIn("knowledge (KB)", res.stdout)
        self.assertNotIn("dev-workflow (docs)", res.stdout)
        # docs repo was never even touched — not yet a git repo at all
        self.assertFalse((docs / ".git").exists())

    def test_message_and_reason_reach_the_commit(self):
        home, kb, docs = self._fake_home({}, {"projA/f.txt": "1\n"})
        res = self._run(home, "--message", "custom subject", "--reason", "because reasons")
        self.assertEqual(res.returncode, 0)
        body = subprocess.run(["git", "-C", str(docs), "log", "-1", "--format=%B"],
                               capture_output=True, text=True, env=GIT_ENV).stdout
        self.assertIn("custom subject", body)
        self.assertIn("because reasons", body)

    def test_clean_repos_exit_zero_with_no_error(self):
        home, kb, docs = self._fake_home({}, {})
        for repo in (kb, docs):
            subprocess.run(["git", "init", "-q", str(repo)], check=True, env=GIT_ENV)
        res = self._run(home)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stderr, "")




FM_DN = "---\nid: 900\ngovernance: doc-native-pilot\nstatus: drafting\n---\n\n"
BLOCK_OK = ("### Req-1 approved — 样例\n- 陈述: 原文\n- 类型: 功能\n- why: w\n"
            "- provenance: p\n- depends-on: 无\n"
            "- approved: 2026-08-25 gate abcdef0 (single: 「go」)\n")


class DiffGuard(unittest.TestCase):
    """(026 LLD-8) the docs-repo pre-commit guard over doc-native cards."""

    def _docs_repo(self, block=BLOCK_OK, governance=FM_DN):
        return init_repo({"proj/900-x/requirement.md": governance + block})

    def test_approved_edit_blocked(self):
        repo = self._docs_repo()
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + BLOCK_OK.replace("- 陈述: 原文", "- 陈述: 被改"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("BLOCKED" in l for l in lines))
        self.assertTrue(any("approved-block-touched" in l and "Req-1" in l for l in lines))
        # nothing committed — worktree still dirty
        st = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                            capture_output=True, text=True, env=GIT_ENV)
        self.assertTrue(st.stdout.strip())

    def test_same_batch_change_note_passes(self):
        repo = self._docs_repo()
        edited = (BLOCK_OK.replace("- 陈述: 原文", "- 陈述: 被改")
                  + "- 变更: 就地改写 (M2 1234567, 2026-08-27)\n")
        dirty(repo, "proj/900-x/requirement.md", FM_DN + edited)
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("committed" in l for l in lines), lines)

    def test_annotation_append_passes(self):
        repo = self._docs_repo()
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + BLOCK_OK + "- approved: 2026-08-27 gate 7654321 (single: 「再批」)\n")
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("committed" in l for l in lines), lines)

    def test_removed_block_blocked(self):
        repo = self._docs_repo()
        dirty(repo, "proj/900-x/requirement.md", FM_DN + "（空）\n")
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("removed" in l for l in lines), lines)

    def test_allow_flag_commits_and_books_log(self):
        repo = self._docs_repo()
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + BLOCK_OK.replace("- 陈述: 原文", "- 陈述: 被改"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj", allow=True)
        self.assertTrue(any("committed" in l for l in lines), lines)
        log = (repo / "proj/900-x/log.md").read_text(encoding="utf-8")
        self.assertIn("diff 守卫显式放行", log)
        self.assertIn("Req-1", log)
        # the booked log line rides the same commit
        st = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                            capture_output=True, text=True, env=GIT_ENV)
        self.assertFalse(st.stdout.strip())

    def test_non_docnative_card_unguarded(self):
        repo = init_repo({"proj/901-y/requirement.md":
                          "---\nid: 901\ngovernance: doc-gate\n---\n" + BLOCK_OK})
        dirty(repo, "proj/901-y/requirement.md",
              "---\nid: 901\ngovernance: doc-gate\n---\n"
              + BLOCK_OK.replace("- 陈述: 原文", "- 陈述: 被改"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("committed" in l for l in lines), lines)

    def test_proposed_block_edit_passes(self):
        block = BLOCK_OK.replace("### Req-1 approved", "### Req-1 proposed")
        block = "\n".join(l for l in block.splitlines()
                          if not l.startswith("- approved:")) + "\n"
        repo = self._docs_repo(block=block)
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + block.replace("- 陈述: 原文", "- 陈述: 随便改"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("committed" in l for l in lines), lines)

    def test_kb_repo_unguarded(self):
        repo = init_repo({"raw/proj/note.md": "x\n"})
        dirty(repo, "raw/proj/note.md", "y\n")
        lines = cdr.commit_repo(repo, "kb", "kb", "m", project="proj")
        self.assertTrue(any("committed" in l for l in lines), lines)


class DiffGuardReviewFixes(unittest.TestCase):
    """Review #4/#11: HEAD-side mode gate + per-doc fail-open."""

    def test_4_same_batch_downgrade_does_not_disarm(self):
        repo = init_repo({"proj/900-x/requirement.md": FM_DN + BLOCK_OK})
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN.replace("doc-native-pilot", "doc-gate")
              + BLOCK_OK.replace("- 陈述: 原文", "- 陈述: 被改"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("BLOCKED" in l for l in lines), lines)

    def test_11_bad_doc_fails_open_per_doc_only(self):
        repo = init_repo({"proj/900-x/requirement.md": FM_DN + BLOCK_OK,
                          "proj/900-x/design.md": "### HLD-1 approved — t\n- 陈述: 设\n"
                          "- approved: 2026-08-25 gate abcdef0 (single: 「go」)\n"})
        (repo / "proj/900-x/design.md").write_bytes(b"\xff\xfe broken")   # undecodable
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + BLOCK_OK.replace("- 陈述: 原文", "- 陈述: 被改"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        # requirement.md's tamper still caught; design.md degrades alone
        self.assertTrue(any("requirement.md Req-1" in l for l in lines), lines)


class CardScope(unittest.TestCase):
    """027 HLD-6: --card = card dir + project board files (docs); KB project-level;
    zero/multiple matches loud-fail; --project/sweep untouched."""

    def _docs(self):
        return init_repo({
            "proj/027-alpha/requirement.md": "a\n",
            "proj/028-beta/requirement.md": "b\n",
            "proj/index.md": "board\n",
            "proj/roadmap.md": "map\n",
        })

    def _dirty(self, d):
        Path(d, "proj/027-alpha/plan.md").write_text("p\n", encoding="utf-8")
        Path(d, "proj/028-beta/plan.md").write_text("q\n", encoding="utf-8")
        Path(d, "proj/index.md").write_text("board v2\n", encoding="utf-8")

    def test_card_commit_excludes_sibling_card(self):
        d = self._docs()
        self._dirty(d)
        lines = cdr.commit_repo(Path(d), "docs", "docs", "msg (027 T6)", card="proj/027")
        self.assertTrue(any("committed" in ln for ln in lines), lines)
        shown = subprocess.run(["git", "-C", d, "show", "--stat", "--name-only",
                                "--format=", "HEAD"], capture_output=True, text=True,
                               env=GIT_ENV).stdout
        self.assertIn("proj/027-alpha/plan.md", shown)     # 反向：本卡路径全入列
        self.assertIn("proj/index.md", shown)              # 共享文件搭车（显式接受）
        self.assertNotIn("028-beta", shown)                # 他卡文档永不入列
        self.assertTrue(any("left uncommitted" in ln and "028-beta" in ln
                            for ln in lines), lines)

    def test_card_no_match_loud(self):
        d = self._docs()
        self._dirty(d)
        lines = cdr.commit_repo(Path(d), "docs", "docs", "msg", card="proj/099")
        self.assertTrue(any("0 card dirs match" in ln for ln in lines), lines)
        log = subprocess.run(["git", "-C", d, "log", "--oneline"], capture_output=True,
                             text=True, env=GIT_ENV).stdout
        self.assertNotIn("msg", log)

    def test_card_multi_match_loud(self):
        d = self._docs()
        Path(d, "proj/027-dup").mkdir()
        Path(d, "proj/027-dup/x.md").write_text("x\n", encoding="utf-8")
        lines = cdr.commit_repo(Path(d), "docs", "docs", "msg", card="proj/027")
        self.assertTrue(any("2 card dirs match" in ln for ln in lines), lines)

    def test_card_kb_half_project_level(self):
        kb = init_repo({"raw/proj/n.md": "n\n", "wiki/proj/c.md": "c\n",
                        "raw/other/o.md": "o\n"})
        Path(kb, "raw/proj/n.md").write_text("n2\n", encoding="utf-8")
        Path(kb, "raw/other/o.md").write_text("o2\n", encoding="utf-8")
        lines = cdr.commit_repo(Path(kb), "kb", "kb", "msg", card="proj/027")
        self.assertTrue(any("committed" in ln for ln in lines), lines)
        shown = subprocess.run(["git", "-C", kb, "show", "--name-only", "--format=",
                                "HEAD"], capture_output=True, text=True, env=GIT_ENV).stdout
        self.assertIn("raw/proj/n.md", shown)
        self.assertNotIn("raw/other", shown)

    def test_project_mode_regression_unchanged(self):
        d = self._docs()
        self._dirty(d)
        lines = cdr.commit_repo(Path(d), "docs", "docs", "msg", project="proj")
        shown = subprocess.run(["git", "-C", d, "show", "--name-only", "--format=",
                                "HEAD"], capture_output=True, text=True, env=GIT_ENV).stdout
        self.assertIn("027-alpha/plan.md", shown)
        self.assertIn("028-beta/plan.md", shown)   # project 级仍全量（既有语义不动）


class CardScopeReviewFixes(unittest.TestCase):
    """027 review fix #3: --card validation guards BOTH repos (main-level)."""

    def test_main_prevalidation_blocks_kb_half(self):
        import io, sys as _sys
        docs = init_repo({"proj/027-a/requirement.md": "r\n"})
        kb = init_repo({"raw/proj/n.md": "n\n"})
        Path(kb, "raw/proj/n.md").write_text("n2\n", encoding="utf-8")
        cfg = tempfile.mkdtemp()
        cfgfile = Path(cfg, "config.yaml")
        cfgfile.write_text("root: %s\ndev_root: %s\n" % (kb, docs), encoding="utf-8")
        orig_cp, orig_argv = cdr.config_path, _sys.argv
        cdr.config_path = lambda: cfgfile
        _sys.argv = ["commit-data-repos.py", "--card", "proj/099", "-m", "should-not-land"]
        out = io.StringIO()
        try:
            _stdout = _sys.stdout
            _sys.stdout = out
            try:
                cdr.main()
            except SystemExit:
                pass
            finally:
                _sys.stdout = _stdout
        finally:
            cdr.config_path, _sys.argv = orig_cp, orig_argv
        self.assertIn("0 card dirs match", out.getvalue())
        log = subprocess.run(["git", "-C", kb, "log", "--oneline"], capture_output=True,
                             text=True, env=GIT_ENV).stdout
        self.assertNotIn("should-not-land", log)   # KB 半未提交


class DiffGuardFace(unittest.TestCase):
    """029 T2: guard face widened to title + clauses (block_parse.face_diffs)."""

    BLOCK_CL = BLOCK_OK.replace("- approved:", "- (a) 子句甲\n- approved:", 1)

    def _repo(self):
        return init_repo({"proj/900-x/requirement.md": FM_DN + self.BLOCK_CL})

    def test_title_edit_blocked(self):
        repo = self._repo()
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + self.BLOCK_CL.replace("— 样例", "— 被改标题"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("approved-block-touched" in l and "title" in l
                            for l in lines), lines)

    def test_clause_edit_blocked(self):
        repo = self._repo()
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + self.BLOCK_CL.replace("子句甲", "子句被改"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("approved-block-touched" in l and "clauses" in l
                            for l in lines), lines)

    def test_title_clause_edit_with_note_passes(self):
        repo = self._repo()
        edited = (self.BLOCK_CL.replace("— 样例", "— 新标题")
                  .replace("子句甲", "子句乙")
                  + "- 变更: 标题子句改写 (M2 1234567, 2026-09-01)\n")
        dirty(repo, "proj/900-x/requirement.md", FM_DN + edited)
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("committed" in l for l in lines), lines)


class DiffGuardModeProbe(unittest.TestCase):
    """029 T3: quote-tolerant mode probe, judged identically to check-side
    card_mode; write-side selection = is_guarded union."""

    FM_Q = '---\nid: 900\ngovernance: "doc-native"\nstatus: drafting\n---\n\n'

    def test_quoted_governance_guard_on(self):
        repo = init_repo({"proj/900-x/requirement.md": self.FM_Q + BLOCK_OK})
        dirty(repo, "proj/900-x/requirement.md",
              self.FM_Q + BLOCK_OK.replace("- 陈述: 原文", "- 陈述: 被改"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("approved-block-touched" in l for l in lines), lines)

    def test_quoted_governance_both_sides_agree(self):
        repo = init_repo({"proj/900-x/requirement.md": self.FM_Q + BLOCK_OK})
        import importlib.util
        from pathlib import Path as _P
        spec = importlib.util.spec_from_file_location(
            "ws_probe", str(_P(__file__).resolve().parent / "workflow-status.py"))
        ws2 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ws2)
        self.assertEqual(ws2.card_mode(str(repo / "proj/900-x")), "doc-native")
        self.assertEqual(cdr._card_governance(repo, "proj/900-x"), "doc-native")

    def test_design_only_card_reads_lite_and_stays_unguarded(self):
        # 030 Req-4(c): same carrier order as _mode_doc; "lite" is not doc-native → guard off (no behavior change)
        repo = init_repo({"proj/901-l/design.md": "---\nid: 901\ngovernance: lite\nstatus: draft\n---\n# 901\n"})
        self.assertEqual(cdr._card_governance(repo, "proj/901-l"), "lite")
        self.assertEqual(cdr._card_governance(repo, "proj/none"), "")

    def test_state_rewrite_still_guarded_union_arm(self):
        # HEAD block approved(+note); worktree rewrites the state word AND the
        # 陈述 — old-state predicate would drop it, the union arm keeps it
        repo = init_repo({"proj/900-x/requirement.md": FM_DN + BLOCK_OK})
        tampered = (BLOCK_OK.replace("### Req-1 approved", "### Req-1 proposed")
                    .replace("- 陈述: 原文", "- 陈述: 被改"))
        dirty(repo, "proj/900-x/requirement.md", FM_DN + tampered)
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("approved-block-touched" in l and "state" in l
                            for l in lines), lines)


class DiffGuardReviewRound(unittest.TestCase):
    """029 review #1/#2: annotation-prefix face + parse-injection interception."""

    def test_annotation_rewrite_blocked(self):
        repo = init_repo({"proj/900-x/requirement.md": FM_DN + BLOCK_OK})
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + BLOCK_OK.replace("「go」", "「我没批准」"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("annotations 非前缀" in l for l in lines), lines)

    def test_annotation_rewrite_not_laundered_by_change_note(self):
        repo = init_repo({"proj/900-x/requirement.md": FM_DN + BLOCK_OK})
        tampered = (BLOCK_OK.replace("「go」", "「我没批准」")
                    + "- 变更: 想洗白 (M2 1234567, 2026-09-01)\n")
        dirty(repo, "proj/900-x/requirement.md", FM_DN + tampered)
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("annotations 非前缀" in l for l in lines), lines)

    def test_duplicate_field_injection_blocked(self):
        repo = init_repo({"proj/900-x/requirement.md": FM_DN + BLOCK_OK})
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + BLOCK_OK.replace("- 类型: 功能",
                                       "- 类型: 功能\n- 陈述: 含义相反的第二行"))
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("parse-injection" in l and "duplicate-field" in l
                            for l in lines), lines)

    def test_preexisting_parse_finding_not_blocking(self):
        dup = BLOCK_OK + "\n### Req-1 proposed — 撞名\n- 陈述: 旧疾\n"
        repo = init_repo({"proj/900-x/requirement.md": FM_DN + dup})
        dirty(repo, "proj/900-x/requirement.md",
              FM_DN + dup + "\n（无害追加散文）\n")
        lines = cdr.commit_repo(repo, "docs", "docs", "m", project="proj")
        self.assertTrue(any("committed" in l for l in lines), lines)


if __name__ == "__main__":
    unittest.main()
