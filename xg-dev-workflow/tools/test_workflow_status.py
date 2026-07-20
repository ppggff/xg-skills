#!/usr/bin/env python3
"""Unit tests for workflow-status.py internals — stdlib unittest, no third-party deps.

Run: python3 tools/test_workflow_status.py    (from the xg-dev-workflow dir, or anywhere).
Covers the pure derivation layer (commit-to-card matching, task-table parsing, trace
building) against synthetic inputs and throwaway fixture trees / git repos; the HTTP
surface is covered by viewer/test_viewer.py.
"""
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("workflow_status", str(TOOLS / "workflow-status.py"))
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)


class CardInMessage(unittest.TestCase):
    def test_hash_substring_is_not_a_card_ref(self):
        # a400654 contains "006" in the abbreviated hash; message names card 005 only.
        line = "a400654 xg-dev-workflow: viewer per-section collapse F (005 T2)"
        self.assertFalse(ws.card_in_message("006", line))
        self.assertTrue(ws.card_in_message("005", line))

    def test_card_in_subject_matches(self):
        line = "7b0e0a2 viewer: current-line band picks the semantic unit (006 T2)"
        self.assertTrue(ws.card_in_message("006", line))

    def test_no_message_part(self):
        self.assertFalse(ws.card_in_message("006", "deadbeef"))
        self.assertFalse(ws.card_in_message("006", ""))


class TaskCommits(unittest.TestCase):
    def _repo_with(self, subjects):
        d = tempfile.mkdtemp()
        env = dict(os.environ,
                   GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        subprocess.run(["git", "init", "-q", d], check=True, env=env)
        for i, s in enumerate(subjects):
            p = os.path.join(d, "f%d" % i)
            open(p, "w").write(s)
            subprocess.run(["git", "-C", d, "add", "."], check=True, env=env)
            subprocess.run(["git", "-C", d, "commit", "-q", "-m", s], check=True, env=env)
        return d

    def test_strict_filters_on_message_not_hash(self):
        repo = self._repo_with(["viewer: band fix (006 T2)",
                                "viewer: collapse rework (005 T2)"])
        lines, tier = ws.task_commits(repo, "2", "006")
        self.assertEqual(tier, "strict")
        self.assertEqual(len(lines), 1)
        self.assertIn("(006 T2)", lines[0])

    def test_loose_when_no_card_qualified_hit(self):
        repo = self._repo_with(["viewer: collapse rework (005 T2)"])
        lines, tier = ws.task_commits(repo, "2", "006")
        self.assertEqual(tier, "loose")
        self.assertEqual(len(lines), 1)


def make_card(root, project, dirname, repo=None, plan=True):
    """Fixture card with R1 (designed/planned/tested) and R2 (requirement-only)."""
    card = os.path.join(root, project, dirname)
    os.makedirs(card)
    write = lambda name, text: open(os.path.join(card, name), "w").write(text)
    write("requirement.md", "## 需求条目\n\n| ID | 条目 | 类型 |\n|---|---|---|\n"
          "| R1 | first item | 功能 |\n| R2 | second item | 约束 |\n")
    write("design.md", "## How it meets the requirement\n\n| R-id | home |\n|---|---|\n"
          "| [R1](./requirement.md) | mod-a |\n\n"
          "## 验证策略\n\n| R-id | E2E |\n|---|---|\n| [R1](./requirement.md) | walk |\n")
    if plan:
        write("plan.md", "### T1: slice one\n- **Implements:** [R1](./requirement.md)\n"
              "- **Acceptance:**\n  - [x] ok\n")
    write("test.md", "| Coverage | test |\n|---|---|\n| R1 | test_one |\n")
    if repo:
        write("progress.md", "---\nid: 099\nrepo: %s\n---\n" % repo)
    return card


class TraceData(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def _repo(self, subjects):
        return TaskCommits._repo_with(self, subjects)

    def _row(self, data, rid):
        return next(r for r in data["rows"] if r["rid"] == rid)

    def test_strict_and_flags(self):
        repo = self._repo(["fix band (099 T1)"])
        card = make_card(self.root, "p", "099-fix", repo=repo)
        d = ws.trace_data("p", card)
        r1, r2 = self._row(d, "R1"), self._row(d, "R2")
        self.assertEqual(r1["present"],
                         {"design": True, "verify": True, "task": True,
                          "test": True, "commit": "strict"})
        self.assertEqual(r1["flags"], [])
        self.assertEqual(r2["present"]["commit"], "none")
        self.assertIn("no-design-home", r2["flags"])
        self.assertIn("no-task", r2["flags"])
        self.assertTrue(d["repo_anchor"])
        self.assertTrue(d["generated_at"])

    def test_loose_and_none(self):
        repo = self._repo(["mentions T1 without card"])
        card = make_card(self.root, "p", "099-fix", repo=repo)
        d = ws.trace_data("p", card)
        self.assertEqual(self._row(d, "R1")["present"]["commit"], "loose")
        repo2 = self._repo(["unrelated subject"])
        card2 = make_card(self.root, "q", "098-fix", repo=repo2)
        d2 = ws.trace_data("q", card2)
        self.assertEqual(self._row(d2, "R1")["present"]["commit"], "none")

    def test_unchecked_without_repo_anchor(self):
        card = make_card(self.root, "noproj", "097-fix")
        d = ws.trace_data("noproj", card)
        self.assertFalse(d["repo_anchor"])
        r1 = self._row(d, "R1")
        self.assertEqual(r1["present"]["commit"], "unchecked")
        self.assertEqual(r1["tasks"][0]["commit_state"], "unchecked")


if __name__ == "__main__":
    unittest.main(verbosity=1)
