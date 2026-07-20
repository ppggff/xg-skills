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


if __name__ == "__main__":
    unittest.main(verbosity=1)
