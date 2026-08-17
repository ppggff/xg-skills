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
        self.assertRegex(out, r"check: ok \(\d+ skipped\)")

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


REQ_FM = "---\nstatus: %s\ngovernance: %s\ncreated: %s\n---\n"
CANON_LOG = ("| id | question | recommended | chosen | why | depends-on | status |\n"
             "|---|---|---|---|---|---|---|\n"
             "| G1 | q | r | c | w | — | resolved → D1 |\n")
THREE_COL_LOG = "| 轮 | 议题 | 结果 |\n|---|---|---|\n| 1 | x | resolved → D1 |\n"


class GateAdjacent(unittest.TestCase):
    """021 T3: A1 stray-marker / A2 grill-reverse / A3 panel-receipts / A5 gate line."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.card = os.path.join(self.tmp.name, "proj", "001-a")

    def _req(self, status="confirmed", gov="doc-gate", created="2026-08-17", body=""):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % (status, gov, created) + body)

    # -- A1
    def test_a1_marker_on_gated_doc_flags(self):
        self._req(body="正文（落纸补充）残留\n")
        f, s = wc.check_transcription_markers("proj", self.card, ws._L1)
        self.assertTrue(any("stray-marker: requirement.md" in x for x in f))

    def test_a1_backtick_mention_and_variants_clean(self):
        self._req(body="讲规则：`（落纸补充）` 与（落纸补充标记）与「落纸补充」都不算\n")
        self.assertEqual(wc.check_transcription_markers("proj", self.card, ws._L1), ([], []))

    def test_a1_drafting_doc_not_checked(self):
        self._req(status="drafting", body="（落纸补充）中途状态合法\n")
        self.assertEqual(wc.check_transcription_markers("proj", self.card, ws._L1), ([], []))

    # -- A2
    def test_a2_pre_cutoff_skips(self):
        self._req(created="2026-08-01")
        f, s = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])
        self.assertTrue(s and "pre-" in s[0])

    def test_a2_no_log_skips(self):
        self._req()
        _, s = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertIn("grill-reverse: no-grill-log", s)

    def test_a2_non_canonical_shape_skips(self):
        self._req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", THREE_COL_LOG)
        _, s = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertIn("grill-reverse: non-canonical-grill-log", s)

    def test_a2_resolved_row_needs_ledger_home(self):
        self._req(gov="ledger")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", CANON_LOG)
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertIn("resolved-no-home: D1", f)
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### D1 [design] approved\n- 陈述: x\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    # -- A3
    def test_a3_ungated_card_owes_nothing(self):
        self._req(status="drafting")
        self.assertEqual(wc.check_panel_receipts("proj", self.card, ws._L1), ([], []))

    def test_a3_gated_no_log_skips(self):
        self._req()
        _, s = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertIn("panel-receipts: no-grill-log", s)

    def test_a3_zero_receipt_block_flags(self):
        self._req(created="2026-08-17")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", "| 轮 | 议题 | 结果 |\n")
        f, _ = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertTrue(any("no-receipts" in x for x in f))

    def test_a3_structural_anchor_passes(self):
        self._req(created="2026-08-17")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", "### Panel receipt — r1\n- ok\n")
        self.assertEqual(wc.check_panel_receipts("proj", self.card, ws._L1), ([], []))

    def test_a3_loose_era_word_anchor_passes(self):
        self._req(created="2026-08-12")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", "…本轮 receipts 落于此…\n")
        self.assertEqual(wc.check_panel_receipts("proj", self.card, ws._L1), ([], []))

    # -- A5
    def test_a5_gate_line_present_clean(self):
        self._req(body="## Change log\n- 2026-08-17 — confirmed（gate `abc1234`）。\n")
        self.assertEqual(wc.check_docgate_gateline("proj", self.card, ws._L1), ([], []))

    def test_a5_missing_gate_line_flags(self):
        self._req(body="## Change log\n- created.\n")
        f, _ = wc.check_docgate_gateline("proj", self.card, ws._L1)
        self.assertIn("no-gate-line: requirement.md", f)

    def test_a5_missing_changelog_section_flags(self):
        self._req(body="## Context\nx\n")
        f, _ = wc.check_docgate_gateline("proj", self.card, ws._L1)
        self.assertIn("no-changelog-section: requirement.md", f)

    def test_a5_ledger_card_not_checked(self):
        self._req(gov="ledger", body="## Context\nx\n")
        self.assertEqual(wc.check_docgate_gateline("proj", self.card, ws._L1), ([], []))


if __name__ == "__main__":
    unittest.main()
