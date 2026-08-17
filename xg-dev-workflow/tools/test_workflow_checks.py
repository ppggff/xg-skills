#!/usr/bin/env python3
"""Tests for workflow-checks.py (the L2 check domain) + the --check dispatch tiers."""
import contextlib
import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("workflow_status", str(TOOLS / "workflow-status.py"))
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)
wc = ws._checks()


def _write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def _run(root, arg):
    """run_check with captured stdout → (exit, output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ws.run_check(root, arg)
    return code, buf.getvalue()


BAD_LEDGER = "### bogus heading that is not a block\n"


class DispatchTiers(unittest.TestCase):
    """021 T2: the three-tier --check dispatch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_slash_arg_stays_card_scope(self):
        _write(self.root, "proj/001-a/requirement.md", "---\nstatus: drafting\n---\n")
        code, out = _run(self.root, "proj/001")
        self.assertEqual(code, 0)
        self.assertNotIn("001-a:", out)   # card scope: no dir prefix

    def test_bare_project_name_is_project_scope(self):
        # two cards would have been "ambiguous card" pre-021; now = full sweep
        _write(self.root, "proj/index.md", "| 001 | x | todo | — |\n")
        _write(self.root, "proj/001-a/requirement.md", "---\nstatus: drafting\n---\n")
        _write(self.root, "proj/001-a/decisions.md", BAD_LEDGER)
        _write(self.root, "proj/002-b/requirement.md", "---\nstatus: drafting\n---\n")
        code, out = _run(self.root, "proj")
        self.assertEqual(code, 1)
        self.assertIn("001-a: bad-header", out)   # per-card prefix proves the sweep

    def test_single_card_project_bare_name_goes_project_scope(self):
        # old behavior resolved the bare name to the single card; new = project scope
        _write(self.root, "solo/001-only/requirement.md", "---\nstatus: drafting\n---\n")
        _write(self.root, "solo/001-only/decisions.md", BAD_LEDGER)
        code, out = _run(self.root, "solo")
        self.assertEqual(code, 1)
        self.assertIn("001-only: bad-header", out)

    def test_cwd_relative_project_dir_not_treated_as_card_dir(self):
        # from dev_root cwd, a bare project name used to hit resolve_card's isdir branch
        _write(self.root, "proj/index.md", "| 001 | x | todo | — |\n")
        _write(self.root, "proj/001-a/requirement.md", "---\nstatus: drafting\n---\n")
        _write(self.root, "proj/001-a/decisions.md", BAD_LEDGER)
        old = os.getcwd()
        os.chdir(self.root)
        try:
            code, out = _run(self.root, "proj")
        finally:
            os.chdir(old)
        self.assertEqual(code, 1)
        self.assertIn("001-a: bad-header", out)


class SkipAndIsolation(unittest.TestCase):
    """021 T2: skip contract + per-check exception isolation (R9)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        _write(self.root, "proj/001-a/requirement.md", "---\nstatus: drafting\n---\n")

    def _with_entries(self, extra):
        orig = wc.CARD_CHECKS
        wc.CARD_CHECKS = orig + extra
        self.addCleanup(lambda: setattr(wc, "CARD_CHECKS", orig))

    def test_skip_visible_but_never_gates(self):
        self._with_entries((("fake", lambda p, c, ws: ([], ["fake(no-carrier)"])),))
        code, out = _run(self.root, "proj/001")
        self.assertEqual(code, 0)
        self.assertIn("skip: fake(no-carrier)", out)
        self.assertIn("check: ok (1 skipped)", out)

    def test_per_check_exception_isolated(self):
        boom = lambda p, c, ws: (_ for _ in ()).throw(RuntimeError("boom"))
        self._with_entries((("bad", boom),
                            ("after", lambda p, c, ws: (["late-finding"], []))))
        findings, skips = wc.check_card_all("proj",
                                            os.path.join(self.root, "proj/001-a"), ws._L1)
        self.assertTrue(any(f.startswith("check-error:bad:") for f in findings))
        self.assertIn("late-finding", findings)   # the rest still ran

    def test_idempotent(self):
        card = os.path.join(self.root, "proj/001-a")
        self.assertEqual(wc.check_card_all("proj", card, ws._L1),
                         wc.check_card_all("proj", card, ws._L1))


if __name__ == "__main__":
    unittest.main()
