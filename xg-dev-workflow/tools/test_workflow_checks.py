#!/usr/bin/env python3
"""Tests for workflow-checks.py (the L2 check domain) + the --check dispatch tiers."""
import contextlib
import importlib.util
import io
import os
import re
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
        findings, skips, _ = wc.check_card_all("proj",
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
        f, s, *_x = wc.check_transcription_markers("proj", self.card, ws._L1)
        self.assertTrue(any("stray-marker: requirement.md" in x for x in f))

    def test_a1_backtick_mention_and_variants_clean(self):
        self._req(body="讲规则：`（落纸补充）` 与（落纸补充标记）与「落纸补充」都不算\n")
        self.assertEqual(wc.check_transcription_markers("proj", self.card, ws._L1)[:2], ([], []))

    def test_a1_drafting_doc_not_checked(self):
        self._req(status="drafting", body="（落纸补充）中途状态合法\n")
        self.assertEqual(wc.check_transcription_markers("proj", self.card, ws._L1)[:2], ([], []))

    # -- _card_created format guard (024 T1)
    def test_malformed_created_routes_to_no_created_branch(self):
        # "2026-8-1" compares lexically as post-2026-08-11 — without the guard the
        # card would enter the era instead of the no-created-date branch
        self._req(created="2026-8-1")
        self.assertEqual(wc._card_created(self.card, ws._L1), "")
        f, s, exs = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual((f, exs), ([], []))
        self.assertIn("grill-reverse: no-created-date", s)

    # -- A2
    def test_a2_pre_cutoff_is_grandfathered_exemption(self):
        self._req(created="2026-08-01")
        f, s, exs = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual((f, s), ([], []))
        self.assertEqual(exs, [("grandfathered", "pre-2026-08-11 card")])

    def test_a2_no_log_skips(self):
        self._req()
        _, s, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertIn("grill-reverse: no-grill-log", s)

    def test_a2_non_canonical_shape_exempts_per_file(self):
        self._req()   # created 2026-08-17: pre-shape-era → grandfathered per file
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", THREE_COL_LOG)
        _, s, exs = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(s, [])
        self.assertIn(("grandfathered", "non-canonical-grill-log (grill-x.md)"), exs)

    def test_a2_resolved_row_needs_ledger_home(self):
        self._req(gov="ledger")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", CANON_LOG)
        # canonical table but no decisions.md at all → visible skip, not a finding (#13)
        f, s, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])
        self.assertTrue(any("no-ledger" in x for x in s))
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### D2 [design] approved\n- 陈述: other\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertIn("resolved-no-home: D1", f)
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### D1 [design] approved\n- 陈述: x\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    # -- A2 shape era (022)
    def test_a2_shape_era_no_canonical_is_finding(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", THREE_COL_LOG)
        f, s, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("non-canonical-grill-log: grill-x.md") for x in f))
        self.assertFalse(any("non-canonical" in x for x in s))   # finding replaced the skip

    def test_a2_shape_era_needs_gate(self):
        self._req(status="drafting", created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", THREE_COL_LOG)
        f, s, exs = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])   # drafting card: era inactive — not-yet-due, no finding
        self.assertIn(("not-yet-due", "non-canonical-grill-log (grill-x.md)"), exs)
        self.assertIn(("not-yet-due", "shape core off (card not past a gate)"), exs)

    def test_a2_pre_shape_cutoff_no_finding(self):
        self._req(created="2026-08-17")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", THREE_COL_LOG)
        f, s, exs = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])
        self.assertIn(("grandfathered", "shape core off (pre-2026-08-18)"), exs)

    def test_a2_mixed_card_deviant_file_not_masked(self):
        self._req(gov="ledger", created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-a.md", CANON_LOG)
        _write(self.tmp.name, "proj/001-a/notes/grill-b.md", THREE_COL_LOG)
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### D1 [design] approved\n- 陈述: x\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any("non-canonical-grill-log: grill-b.md" in x for x in f))
        self.assertFalse(any("grill-a.md" in x for x in f))

    def test_a2_column_drop_flagged(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "| id | status |\n|---|---|\n| G1 | resolved |\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("column-drop: grill-x.md") for x in f))

    def test_a2_misplaced_decision_row_in_nav_table(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "\n| 轮 | 议题 | 结果 |\n|---|---|---|\n"
               "| 1 | x | resolved → D9 |\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("misplaced-decision-row: grill-x.md") for x in f))

    def test_a2_pure_nav_and_mentions_clean(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG
               + "\n轮次摘要：本轮讨论了 `resolved → D1` 的写法（反引号 mention）。\n"
               + "| verdict | note |\n|---|---|\n| ok | adopted → G3 收进 |\n"
               + "```\nresolved → D2 在 fence 内也是 mention\n```\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertFalse(any("misplaced" in x for x in f))

    def test_a2_notation_docgate_ledger_id_is_mismatch(self):
        self._req(created="2026-08-18")   # doc-gate card
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", CANON_LOG)
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("notation-mismatch: grill-x.md")
                            and "doc-gate" in x for x in f))

    def test_a2_notation_docgate_doc_section_ok(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "| id | question | recommended | chosen | why | depends-on | status |\n"
               "|---|---|---|---|---|---|---|\n"
               "| G1 | q | r | c | w | — | resolved → requirement.md §需求条目（R1–R4） |\n"
               "| G2 | q | r | c | w | G1 | resolved |\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertFalse(any("notation-mismatch" in x for x in f))

    def test_a2_notation_ledger_doc_section_is_mismatch(self):
        self._req(gov="ledger", created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "| id | question | recommended | chosen | why | depends-on | status |\n"
               "|---|---|---|---|---|---|---|\n"
               "| G1 | q | r | c | w | — | resolved → design.md §思路 |\n")
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### D1 [design] approved\n- 陈述: x\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any("notation-mismatch" in x and "ledger" in x for x in f))

    def test_a2_alignment_rows_exempt(self):
        self._req(gov="ledger", created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "| id | question | recommended | chosen | why | depends-on | status |\n"
               "|---|---|---|---|---|---|---|\n"
               "| G1 | q | r | c | w | — | resolved |\n"
               "| G2 | q | r | c | w | G1 | open（gate 待裁） |\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertFalse(any("notation-mismatch" in x for x in f))

    def test_a2_misplaced_in_prose_flagged_with_line(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "\n某轮散文写了 resolved → D7 却没进表。\n")
        f, _, *_x = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any("misplaced-decision-row: grill-x.md line 5" in x for x in f))

    # -- A3
    def test_a3_ungated_card_owes_nothing(self):
        self._req(status="drafting")
        self.assertEqual(wc.check_panel_receipts("proj", self.card, ws._L1)[:2], ([], []))

    def test_a3_gated_no_log_skips(self):
        self._req()
        _, s, *_x = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertIn("panel-receipts: no-grill-log", s)

    def test_a3_zero_receipt_block_flags(self):
        self._req(created="2026-08-17")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", "| 轮 | 议题 | 结果 |\n")
        f, _, *_x = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertTrue(any("no-receipts" in x for x in f))

    def test_a3_structural_anchor_passes(self):
        self._req(created="2026-08-17")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", "### Panel receipt — r1\n- ok\n")
        self.assertEqual(wc.check_panel_receipts("proj", self.card, ws._L1)[:2], ([], []))

    def test_a3_loose_era_word_anchor_passes(self):
        self._req(created="2026-08-12")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", "…本轮 receipts 落于此…\n")
        self.assertEqual(wc.check_panel_receipts("proj", self.card, ws._L1)[:2], ([], []))

    # -- A3 structure core (022)
    RECEIPT_OK = ("## Panel receipt — r1\n"
                  "- **Header**：round = pre-gate · round type = 全量 · "
                  "lenses = 1/2/3/4 · re-dispatch = no（首次）。\n"
                  "- adopted → G3 收进。\n"
                  "- adopted（轻）→ R2 注记（括注形）。\n"
                  "- refuted — 理由一句。\n"
                  "- lens 4 判词：a satisfied · b not satisfied（自由行不受核）。\n")

    def _shape_req(self):
        self._req(created="2026-08-18")

    def test_a3_structure_full_block_passes(self):
        self._shape_req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", CANON_LOG + self.RECEIPT_OK)
        f, _, *_x = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    def test_a3_missing_header_key_flagged(self):
        self._shape_req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "## Panel receipt — r1\n"
               "- **Header**：round = pre-gate · lenses = 1/2/3/4。\n- adopted → G3。\n")
        f, _, *_x = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("receipt-missing-key")
                            and "round type" in x and "re-dispatch" in x for x in f))

    def test_a3_bad_disposition_lead_word_without_mark(self):
        self._shape_req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + self.RECEIPT_OK + "- adopted 但同行无箭头标记。\n")
        f, _, *_x = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertTrue(any("receipt-bad-disposition" in x for x in f))

    def test_a3_clean_run_literal_passes(self):
        self._shape_req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "**Panel receipt** — 轻量复核：round = r2 · "
               "round type = 定向 · lenses = 4 · re-dispatch = yes（scope=修订）。"
               "no findings。\n")
        f, _, *_x = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    def test_a3_block_without_dispositions_flagged(self):
        self._shape_req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "## Panel receipt — r1\n"
               "- **Header**：round = pre-gate · round type = 全量 · "
               "lenses = 1/2/3/4 · re-dispatch = no。\n判词全 satisfied。\n")
        f, _, *_x = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertTrue(any("receipt-no-dispositions" in x for x in f))

    def test_a3_pre_shape_cutoff_presence_only(self):
        self._req(created="2026-08-17")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "### Panel receipt — r1\n判词自由形（021 时代不受结构核）。\n")
        self.assertEqual(wc.check_panel_receipts("proj", self.card, ws._L1)[:2], ([], []))

    # -- A5
    def test_a5_gate_line_present_clean(self):
        self._req(body="## Change log\n- 2026-08-17 — confirmed（gate `abc1234`）。\n")
        self.assertEqual(wc.check_docgate_gateline("proj", self.card, ws._L1)[:2], ([], []))

    def test_a5_missing_gate_line_flags(self):
        self._req(body="## Change log\n- created.\n")
        f, _, *_x = wc.check_docgate_gateline("proj", self.card, ws._L1)
        self.assertIn("no-gate-line: requirement.md", f)

    def test_a5_missing_changelog_section_flags(self):
        self._req(body="## Context\nx\n")
        f, _, *_x = wc.check_docgate_gateline("proj", self.card, ws._L1)
        self.assertIn("no-changelog-section: requirement.md", f)

    def test_a5_ledger_card_not_checked(self):
        self._req(gov="ledger", body="## Context\nx\n")
        self.assertEqual(wc.check_docgate_gateline("proj", self.card, ws._L1)[:2], ([], []))


SUP_ADR = ("---\nStatus: accepted\n---\n# ADR-0002 x\n\n## Supersedes (optional)\n\n"
           "ADR-0001 — replaces it.\n\n## 被取代表述 (required when superseding)\n\n"
           "- `旧词A` → `新词`\n")


class LedgerRows(unittest.TestCase):
    """024 T2: (x) ledger-rows — state-tiered reverse check + activation/exemptions."""

    TABLE_HEAD = ("## 需求条目\n\n| ID | 需求条目 | 类型 | provenance |\n"
                  "|---|---|---|---|\n")
    A1 = "### R1 [requirement] approved\n- 陈述: x\n- approved: 2026-08-20 gate abc\n\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.card = os.path.join(self.tmp.name, "proj", "001-a")

    def _card(self, rows="| R1 | 条目甲 | 功能 | e |\n", ledger=None,
              created="2026-08-19", gov="ledger", status="drafting"):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % (status, gov, created) + self.TABLE_HEAD + rows)
        if ledger is not None:
            _write(self.tmp.name, "proj/001-a/decisions.md", ledger)

    def _x(self):
        return wc.check_ledger_rows("proj", self.card, ws._L1)

    def test_approved_block_without_row_flags(self):
        self._card(ledger=self.A1 + "### R2 [requirement] approved\n- 陈述: y\n"
                                    "- approved: 2026-08-20 gate abc\n")
        self.assertEqual(self._x()[0], ["block-no-row: R2"])

    def test_proposed_block_without_row_is_not_yet_due(self):
        self._card(ledger=self.A1 + "### R2 [requirement] proposed\n- 陈述: y\n")
        f, s, exs = self._x()
        self.assertEqual((f, s), ([], []))
        self.assertIn(("not-yet-due", "proposed block R2 awaiting its row"), exs)

    def test_v_prefix_blocks_exempt(self):
        self._card(ledger=self.A1 + "### V1 [requirement] approved\n- 陈述: v\n"
                                    "- approved: 2026-08-20 gate abc\n")
        self.assertEqual(self._x()[0], [])

    def test_retired_accounting_row_exempt(self):
        rows = ("| R1 | 条目甲 | 功能 | e |\n"
                "| ~~R8~~ | ~~旧条目~~ retired (2026-08-19: 并入 R1) | 功能 | e |\n")
        self._card(rows=rows, ledger=self.A1 + "### R8 [requirement] retired\n"
                                               "- 陈述: old\n- retired: 2026-08-19\n")
        self.assertEqual(self._x()[0], [])

    def test_forward_direction_owned_by_a_at_composite(self):
        # E7 类1 (仅 doc → dangling-id) + 类7 (引纯 superseded id → superseded-ref):
        # findings come from (a) at the composite; (x) stays silent on both
        rows = ("| R1 | 条目甲 | 功能 | e |\n"
                "| R2 | 条目乙 | 功能 | e |\n"
                "| R3 | 条目丙 | 功能 | e |\n")
        self._card(rows=rows, status="confirmed",
                   ledger=self.A1 + "### R3 [requirement] superseded\n- 陈述: z\n")
        self.assertEqual(self._x()[0], [])
        allf, _, _ = wc.check_card_all("proj", self.card, ws._L1)
        self.assertIn("dangling-id: R2", allf)
        self.assertIn("superseded-ref: R3", allf)

    def test_doc_gate_card_without_ledger_not_yet_due(self):
        self._card(gov="doc-gate", ledger=None)
        f, s, exs = self._x()
        self.assertEqual((f, s), ([], []))
        self.assertIn(("not-yet-due", "doc-gate card, ledger is a forbidden carrier"),
                      exs)

    def test_era_drafting_card_is_active(self):
        # pre-gate created-only predicate: fires while the card is still drafting
        self._card(status="drafting",
                   ledger="### R2 [requirement] approved\n- 陈述: y\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertEqual(self._x()[0], ["block-no-row: R2"])

    def test_pre_cutoff_card_grandfathered(self):
        self._card(created="2026-08-18", ledger=self.A1)
        f, s, exs = self._x()
        self.assertEqual((f, s), ([], []))
        self.assertEqual(exs, [("grandfathered", "pre-2026-08-19 card")])

    def test_no_created_date_carrier_missing(self):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               "---\nstatus: drafting\ngovernance: ledger\n---\n"
               + self.TABLE_HEAD + "| R1 | x | 功能 | e |\n")
        _write(self.tmp.name, "proj/001-a/decisions.md", self.A1)
        f, s, exs = self._x()
        self.assertEqual((f, s), ([], []))
        self.assertIn(("carrier-missing", "no created date, row check off"), exs)

    def test_no_requirement_level_blocks_carrier_missing(self):
        self._card(ledger="### D1 [design] proposed\n- 陈述: d\n")
        self.assertIn(("carrier-missing", "no requirement-level ledger blocks"),
                      self._x()[2])

    def test_no_items_table_carrier_missing(self):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("drafting", "ledger", "2026-08-19") + "散文需求，无表\n")
        _write(self.tmp.name, "proj/001-a/decisions.md", self.A1)
        self.assertIn(("carrier-missing", "no 需求条目 table"), self._x()[2])

    # -- 判定2 token-seek (024 T3, E7 类3)
    def test_token_in_row_missing_from_block_flags(self):
        self._card(rows="| R1 | 强制搬运三个运行前提 | 功能 | e |\n",
                   ledger="### R1 [requirement] approved\n- 陈述: 强制搬运全部运行前提\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertIn("row-token-missing: R1 [三]", self._x()[0])

    def test_ledger_finer_than_row_ok(self):
        self._card(rows="| R1 | 强制搬运运行前提 | 功能 | e |\n",
                   ledger="### R1 [requirement] approved\n"
                          "- 陈述: 强制搬运三个运行前提（2026-07-31 全部三行）\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertEqual(self._x()[0], [])

    def test_rid_digits_and_code_spans_not_tokens(self):
        self._card(rows="| R1 | 承接 R7 的残余，文法 `G\\d+` 最长匹配 | 功能 | e |\n",
                   ledger="### R1 [requirement] approved\n- 陈述: 残余承接与文法\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertEqual(self._x()[0], [])

    def test_paraphrase_drift_digit_vs_cjk_numeral_flags(self):
        # recorded coarse-filter form: digit↔中文数词 drift trips the seek — the
        # fix is wording alignment, not a checker change (D6 known form)
        self._card(rows="| R1 | 第 3 步收口 | 功能 | e |\n",
                   ledger="### R1 [requirement] approved\n- 陈述: 第三步收口\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertIn("row-token-missing: R1 [3]", self._x()[0])

    # -- 判定3 括注计数 (024 T3, E7 类6)
    def test_paren_count_mismatch_flags(self):
        self._card(rows="| R1 | 判据（4 类）：甲、乙、丙 | 功能 | e |\n",
                   ledger="### R1 [requirement] approved\n- 陈述: 判据 4 类：甲、乙、丙\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertIn("count-mismatch: R1 claims 4, list has 3", self._x()[0])

    def test_paren_count_match_ok(self):
        self._card(rows="| R1 | 判据（3 类）：甲、乙、丙 | 功能 | e |\n",
                   ledger="### R1 [requirement] approved\n- 陈述: 判据 3 类：甲、乙、丙\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertEqual(self._x()[0], [])

    def test_paren_count_unlocatable_not_accounted(self):
        self._card(rows="| R1 | 判据（3 类）后文详述 | 功能 | e |\n",
                   ledger="### R1 [requirement] approved\n- 陈述: 判据 3 类后文详述\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertEqual(self._x()[0], [])

    def test_exemption_visible_verbose(self):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "ledger", "2026-08-19") + "散文需求，无表\n")
        _write(self.tmp.name, "proj/001-a/decisions.md", self.A1)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ws.run_check(self.tmp.name, "proj/001", verbose_skips=True)
        self.assertIn("skip: ledger-rows: no 需求条目 table [carrier-missing]",
                      buf.getvalue())


class QuestionGlossHook(unittest.TestCase):
    """024 T6: D22 question-gloss report-only hook — hints on the skips stream."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.card = os.path.join(self.tmp.name, "proj", "001-a")

    def _fix(self, question, created="2026-08-20"):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("drafting", "ledger", created))
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "| id | question | recommended | chosen | why | depends-on | status |\n"
               "|---|---|---|---|---|---|---|\n"
               "| G1 | %s | r | c | w | — | resolved |\n" % question)
        return wc.check_grill_reverse("proj", self.card, ws._L1)

    def test_bare_id_no_gloss_hints(self):
        f, s, _ = self._fix("R7 的哪个通道")
        self.assertIn("question-gloss: grill-x.md G1 bare id, no gloss", s)
        # report-only: rides skips, never a finding
        self.assertFalse(any("question-gloss" in x for x in f))

    def test_glossed_cell_clean(self):
        _, s, _ = self._fix("R7（doc↔ledger 行级核）的哪个通道")
        self.assertFalse(any("question-gloss" in x for x in s))

    def test_pre_cutoff_card_no_hint(self):
        _, s, _ = self._fix("R7 的哪个通道", created="2026-08-19")
        self.assertFalse(any("question-gloss" in x for x in s))


class ReceiptPremiseKeys(unittest.TestCase):
    """024 T5: premises=/suspicions= receipt keys — era-gated on RECEIPT_PREMISE_CUTOFF,
    inheriting (l)'s gated predicate; premises carries a value-domain core."""

    RCPT = ("### Panel receipt — Round 1\n\n"
            "- round = 1\n- round type: topic\n- lenses = x\n- re-dispatch = no\n"
            "%s\nDispositions:\n\n- adopted → x\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.card = os.path.join(self.tmp.name, "proj", "001-a")

    def _fix(self, keys, created="2026-08-19"):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "ledger", created))
        _write(self.tmp.name, "proj/001-a/notes/grill-requirement.md",
               self.RCPT % keys)
        return wc.check_panel_receipts("proj", self.card, ws._L1)

    def test_era_card_missing_keys_flags(self):
        f, _, _ = self._fix("")
        self.assertTrue(any("receipt-missing-key" in x and "premises =,suspicions =" in x
                            for x in f))

    def test_pre_era_card_four_keys_suffice(self):
        f, _, _ = self._fix("", created="2026-08-18")
        self.assertEqual(f, [])

    def test_value_domain_violation_flags(self):
        f, _, _ = self._fix("- premises = 阶段doc\n- suspicions = 3\n")
        self.assertTrue(any(x.startswith("receipt-bad-premises") for x in f))

    def test_facts_pack_demands_fact_ref(self):
        f, _, _ = self._fix("- premises = facts-pack（附入）\n- suspicions = 3\n")
        self.assertTrue(any(x.startswith("receipt-premises-no-fact") for x in f))
        f, _, _ = self._fix("- premises = facts-pack（[F1] 附入）\n- suspicions = 3\n")
        self.assertEqual(f, [])

    def test_backtick_mention_not_presence(self):
        f, _, _ = self._fix("- note: `premises =` 与 `suspicions =` 的值域核归实现\n")
        self.assertTrue(any("receipt-missing-key" in x and "premises =" in x for x in f))

    def test_valid_keys_clean(self):
        f, _, _ = self._fix("- premises = problem+claim（无合成前提）\n"
                            "- suspicions = n/a-非 rewrite 轮\n")
        self.assertEqual(f, [])

    def test_facts_pack_ref_below_header_not_credited(self):
        # review #2 (D13 letter): an [F<n>] only in a disposition line does not
        # satisfy the facts-pack demand — the header segment is the judged region
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "ledger", "2026-08-19"))
        _write(self.tmp.name, "proj/001-a/notes/grill-requirement.md",
               "### Panel receipt — Round 1\n\n"
               "- round = 1\n- round type: topic\n- lenses = x\n- re-dispatch = no\n"
               "- premises = facts-pack（附入）\n- suspicions = 3\n"
               "\nDispositions:\n\n- adopted → 依据 [F1] 修正\n")
        f, _, _ = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("receipt-premises-no-fact") for x in f))


class GrillSignature(unittest.TestCase):
    """024 T4: (y) grill-signature — co-occurrence signature, union id index,
    closure = status not open (first word) ∧ chosen non-empty (placeholder-aware)."""

    LOG_HEAD = ("| id | question | recommended | chosen | why | depends-on | status |\n"
                "|---|---|---|---|---|---|---|\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.card = os.path.join(self.tmp.name, "proj", "001-a")

    def _card(self, body, log=None, created="2026-08-19", gov="ledger",
              status="drafting", log2=None):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % (status, gov, created) + body)
        if log is not None:
            _write(self.tmp.name, "proj/001-a/notes/grill-requirement.md",
                   self.LOG_HEAD + log)
        if log2 is not None:
            _write(self.tmp.name, "proj/001-a/notes/grill-design.md",
                   self.LOG_HEAD + log2)

    def _y(self):
        return wc.check_grill_signature("proj", self.card, ws._L1)

    def _row(self, gid, status="resolved", chosen="是"):
        return "| %s | q | r | %s | w | — | %s |\n" % (gid, chosen, status)

    def test_open_row_flags(self):
        self._card("边界定案（人工 2026-08-20，G1）\n", log=self._row("G1", status="open"))
        self.assertEqual(self._y()[0], ["signature-open: G1 (requirement.md)"])

    def test_placeholder_chosen_flags(self):
        self._card("边界定案（人工 2026-08-20，G1）\n",
                   log=self._row("G1", chosen="—"))
        self.assertEqual(self._y()[0], ["signature-open: G1 (requirement.md)"])

    def test_closed_row_passes(self):
        self._card("边界定案（人工 2026-08-20，G1）\n", log=self._row("G1"))
        self.assertEqual(self._y()[:2], ([], []))

    def test_resolved_arrow_target_not_substring_trapped(self):
        self._card("边界定案（人工 2026-08-20，G1）\n",
                   log=self._row("G1", status="resolved → Scope/Open"))
        self.assertEqual(self._y()[0], [])

    def test_no_log_and_missing_id_carrier_missing(self):
        self._card("边界定案（人工 2026-08-20，G1）\n")
        f, s, exs = self._y()
        self.assertEqual((f, s), ([], []))
        self.assertIn(("carrier-missing", "no grill-log, signatures not checkable"), exs)
        self._card("边界定案（人工 2026-08-20，G2）\n", log=self._row("G1"))
        f, s, exs = self._y()
        self.assertEqual(f, [])
        self.assertIn(("carrier-missing", "signature id G2 not in grill-log index"), exs)

    def test_longest_match_suffix_id_not_degraded(self):
        # `G6b` must not resolve to G6's (closed) row — carrier-missing for G6b
        self._card("沿 `G6b` 判定（人工 2026-08-20）\n", log=self._row("G6"))
        f, s, exs = self._y()
        self.assertEqual(f, [])
        self.assertIn(("carrier-missing", "signature id G6b not in grill-log index"),
                      exs)

    def test_slash_and_range_expansion(self):
        rows = "".join(self._row("G%d" % i) for i in (1, 2, 3, 4, 5))
        self._card("定案（人工 2026-08-20，G1/G2 与 G3–G5）\n", log=rows)
        self.assertEqual(self._y(), ([], [], []))
        rows_gap = "".join(self._row("G%d" % i) for i in (1, 2, 3, 5))
        self._card("定案（人工 2026-08-20，G1/G2 与 G3–G5）\n", log=rows_gap)
        f, s, exs = self._y()
        self.assertEqual(f, [])
        self.assertIn(("carrier-missing", "signature id G4 not in grill-log index"),
                      exs)

    def test_uppercase_prefixed_substring_not_a_gid(self):
        # review #3: PG16 must not mint a phantom G16
        self._card("核对 PG16 行为（人工 2026-08-20）\n",
                   log=self._row("G16", status="open"))
        self.assertEqual(self._y(), ([], [], []))

    def test_backtick_gid_visible_union_index(self):
        # extraction precedes code-span strip; index unions across grill-logs
        self._card("沿 `G7` 定案（人工 2026-08-20）；另 G8 拍板（人工）\n",
                   log=self._row("G7", status="open"), log2=self._row("G8"))
        self.assertEqual(self._y()[0], ["signature-open: G7 (requirement.md)"])

    def test_accounting_lines_out_of_scope(self):
        self._card("| ID | 需求条目 |\n|---|---|\n"
                   "| ~~R8~~ | ~~旧~~ retired (G9 人工照案) |\n",
                   log=self._row("G9", status="open"))
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### R8 [requirement] retired\n- 陈述: x\n"
               "- retired: 2026-08-20（G9 人工照案）\n")
        self.assertEqual(self._y()[0], [])

    def test_history_masked(self):
        self._card("正文无署名\n\n## Change log\n\n- 2026-08-20 — G3 人工照案。\n",
                   log=self._row("G1"))
        self.assertEqual(self._y(), ([], [], []))

    def test_pre_cutoff_grandfathered_and_no_created_carrier_missing(self):
        self._card("定案（人工 2026-08-20，G1）\n", log=self._row("G1", status="open"),
                   created="2026-08-18")
        f, s, exs = self._y()
        self.assertEqual((f, s), ([], []))
        self.assertEqual(exs, [("grandfathered", "pre-2026-08-19 card")])
        _write(self.tmp.name, "proj/001-a/requirement.md",
               "---\nstatus: drafting\ngovernance: ledger\n---\n定案（人工，G1）\n")
        f, s, exs = self._y()
        self.assertEqual((f, s), ([], []))
        self.assertIn(("carrier-missing", "no created date, signature check off"), exs)

    def test_chosen_less_table_rows_carrier_missing_not_finding(self):
        # review #1: a canonical table without a chosen column is structurally
        # undecidable — its ids resolve to carrier-missing, never signature-open
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("drafting", "ledger", "2026-08-19")
               + "定案（人工 2026-08-20，G3）\n")
        _write(self.tmp.name, "proj/001-a/notes/grill-requirement.md",
               "| id | question | recommended | why | status |\n"
               "|---|---|---|---|---|\n"
               "| G3 | q | rec | w | resolved → R1 |\n")
        f, s, exs = self._y()
        self.assertEqual(f, [])
        self.assertIn(("carrier-missing", "signature id G3 not in grill-log index"),
                      exs)

    def test_mode_agnostic_doc_gate_checked(self):
        self._card("定案（人工 2026-08-20，G1）\n", gov="doc-gate",
                   log=self._row("G1", status="open"))
        self.assertEqual(self._y()[0], ["signature-open: G1 (requirement.md)"])


class SupersedeResidue(unittest.TestCase):
    """021 T4: A4′ machine anchors + resident conditional sweep + --from-card."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.card = os.path.join(self.tmp.name, "proj", "001-a")
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-08-17"))

    def test_no_anchor_predicate_off(self):
        self.assertEqual(wc.check_supersede_residue("proj", self.card, ws._L1)[:2], ([], []))

    def test_adr_terms_flag_body_residue(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/design.md", "---\nstatus: frozen\n---\n正文还在说旧词A。\n")
        f, _, *_x = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertTrue(any("superseded-phrase: design.md" in x for x in f))

    def test_history_sections_masked(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: frozen\n---\n## Change log\n- 旧词A 已被取代（历史）。\n")
        f, _, *_x = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertEqual([x for x in f if "superseded-phrase" in x], [])

    def test_superseding_adr_without_section_flags(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md",
               "---\nStatus: accepted\n---\n## Supersedes (optional)\n\nADR-0001 — y.\n")
        f, _, *_x = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertIn("adr-retired-missing: adr/0002-x.md", f)

    def test_malformed_list_line_flags(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md",
               SUP_ADR.replace("- `旧词A` → `新词`", "- 旧词A 没有反引号"))
        f, _, *_x = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("adr-retired-format:") for x in f))

    def test_changelog_sublist_anchor(self):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-08-17") +
               "## Change log\n- 2026-08-17 — M2 变更，被取代表述：\n  - `旧词B` → `新词`\n")
        _write(self.tmp.name, "proj/001-a/design.md", "---\nstatus: frozen\n---\n旧词B 残留。\n")
        f, _, *_x = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertTrue(any("[旧词B]" in x for x in f))

    def test_dead_adr_and_short_terms_excluded(self):
        # a superseded ADR's terms are no longer authoritative; a 1-char term is format (T9)
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md",
               SUP_ADR.replace("Status: accepted", "Status: superseded by ADR-0003"))
        _write(self.tmp.name, "proj/001-a/adr/0003-z.md",
               SUP_ADR.replace("- `旧词A` → `新词`", "- `/` → `空格`"))
        terms, findings, _ = wc._csp().terms_from_card(self.card)
        self.assertEqual(terms, [])
        self.assertTrue(any("adr-retired-format" in x for x in findings))

    def test_sweep_scope_excludes_execution_docs(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/progress.md", "历史叙述提到旧词A。\n")
        f, _, *_x = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertEqual([x for x in f if "superseded-phrase" in x], [])

    def test_replay_cjk_quote_forms(self):
        # 021 review #1 — replay of the pre-021 corpus shapes: a pure-quote line
        # yields the phrase; a quote wrapping inline code is ambiguous → format
        adr = SUP_ADR.replace(
            "- `旧词A` → `新词`",
            "- 「旧短语整句」 → 新说法\n- 「`in-progress` **允许直接继续**」 —— 未限定动作\n"
            "- `<old phrase>` → `<replacement>`")
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", adr)
        terms, findings, _ = wc._csp().terms_from_card(self.card)
        self.assertEqual(terms, ["旧短语整句"])
        self.assertTrue(any("adr-retired-format" in x for x in findings))  # mixed form
        self.assertEqual([x for x in findings if "old phrase" in x], [])   # placeholder silent

    def test_backticked_mention_exempt_in_resident_sweep(self):
        # 021 review #2 — the docstring's escape hatch actually works now
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: frozen\n---\n历史上叫 `旧词A`，现已改名。\n```\n旧词A in fence\n```\n还在用旧词A的这行要报。\n")
        f, _, *_x = wc.check_supersede_residue("proj", self.card, ws._L1)
        hits = [x for x in f if "superseded-phrase" in x]
        self.assertEqual(len(hits), 1)
        self.assertIn(":8 ", hits[0] + " ")   # only the bare-use line survives

    def test_gate_line_in_template_comment_not_counted(self):
        # 021 review #4 — the audit anchor can't be satisfied by template guidance
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-08-17") +
               "## Change log\n- created.\n"
               "<!-- gate passages land here as `- <date> — <状态>（gate abc123）` -->\n")
        f, _, *_x = wc.check_docgate_gateline("proj", self.card, ws._L1)
        self.assertIn("no-gate-line: requirement.md", f)

    def test_from_card_parity_with_manual_terms(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/design.md", "---\n---\n旧词A here.\n")
        csp = wc._csp()
        terms, findings, _ = csp.terms_from_card(self.card)
        self.assertEqual((terms, findings), (["旧词A"], []))
        self.assertEqual(csp.scan(self.card, terms),
                         csp.scan(self.card, ["旧词A"]))   # E3 对拍：--from-card ≡ 手工词表


class CardScopedBC(unittest.TestCase):
    """021 T5: B1 links / B2′ status / B6 r-trace / B7 fact-refs / B8 cap / C4 ADR."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.card = os.path.join(self.tmp.name, "proj", "001-a")
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-08-17"))
        self.kb = os.path.join(self.tmp.name, "kb")
        os.makedirs(self.kb, exist_ok=True)
        orig = wc._kb_root
        wc._kb_root = lambda: self.kb
        self.addCleanup(lambda: setattr(wc, "_kb_root", orig))

    # -- B1
    def test_b1_block_form_aliases(self):
        _write(self.kb, "wiki/proj/other.md", "---\naliases:\n  - blocky\n---\nx")
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n[[wiki/proj/blocky]]\n")
        self.assertEqual(wc.check_links("proj", self.card, ws._L1)[:2], ([], []))

    def test_b7_h3_fact_list_section(self):
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n### 事实清单\n- F9: 实测。\n\n引 [F9]。\n")
        self.assertEqual(wc.check_fact_refs("proj", self.card, ws._L1)[:2], ([], []))

    def test_b1_wikilink_resolution_and_alias(self):
        _write(self.kb, "wiki/proj/real.md", "x")
        _write(self.kb, "wiki/proj/other.md", "---\naliases: [nick]\n---\nx")
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n[[wiki/proj/real]] [[wiki/proj/nick]] "
               "[[wiki/proj/gone]] `[[wiki/proj/mention]]` [[wiki/<project>/<slug>]]\n")
        f, s, *_x = wc.check_links("proj", self.card, ws._L1)
        self.assertEqual(f, ["broken-wikilink: design.md [[wiki/proj/gone]]"])

    def test_b1_relative_links(self):
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n[a](./requirement.md) [b](./notes/gone.md)\n")
        f, _, *_x = wc.check_links("proj", self.card, ws._L1)
        self.assertEqual(f, ["broken-link: design.md ./notes/gone.md"])

    def test_b1_no_kb_root_skips_whole_check(self):
        wc_orig = wc._kb_root
        wc._kb_root = lambda: os.path.join(self.tmp.name, "nope")
        try:
            f, s, *_x = wc.check_links("proj", self.card, ws._L1)
        finally:
            wc._kb_root = wc_orig
        self.assertEqual((f, s), ([], ["links: no-kb-root"]))

    # -- B2′
    def test_b2_missing_status_flags(self):
        _write(self.tmp.name, "proj/001-a/design.md", "no frontmatter\n")
        f, _, *_x = wc.check_status_field("proj", self.card, ws._L1)
        self.assertEqual(f, ["missing-status: design.md"])

    # -- B6
    def _req_with_items(self, extra_docs=()):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-08-17") +
               "## 需求条目\n| ID | 需求条目 | 类型 | prov |\n|--|--|--|--|\n"
               "| R1 | one | 功能 | e |\n| R2 | two | 功能 | e |\n")
        for rel, text in extra_docs:
            _write(self.tmp.name, "proj/001-a/" + rel, text)

    def test_b6_frozen_design_missing_home_flags(self):
        self._req_with_items(extra_docs=[("design.md",
            "---\nstatus: frozen\n---\n## How it meets the requirement\n"
            "| R | home |\n|--|--|\n| R1 | m |\n")])
        f, _, *_x = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertIn("trace: R2 no-design-home", f)
        self.assertNotIn("trace: R1 no-design-home", f)

    def test_b6_drafting_design_not_gated(self):
        self._req_with_items(extra_docs=[("design.md", "---\nstatus: drafting\n---\n")])
        f, _, *_x = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertEqual([x for x in f if "no-design-home" in x], [])

    def test_b6_not_in_items_always_fires(self):
        self._req_with_items(extra_docs=[("design.md",
            "---\nstatus: drafting\n---\n## How it meets the requirement\n"
            "| R | home |\n|--|--|\n| R9 | ghost |\n")])
        f, _, *_x = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertIn("trace: R9 not-in-需求条目", f)

    def test_b6_prose_only_requirement_exempt(self):
        f, _, *_x = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    # -- B7
    def test_b7_head_trailing_annotation_tolerated(self):
        _write(self.tmp.name, "proj/001-a/facts.md",
               "### F24 [VERIFIED] —— 待实测注记\n- 来源: `x`\n")
        _write(self.tmp.name, "proj/001-a/design.md", "---\nstatus: drafting\n---\n引 [F24]。\n")
        self.assertEqual(wc.check_fact_refs("proj", self.card, ws._L1)[:2], ([], []))

    def test_b6_pre_cutoff_card_downstream_dims_off(self):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-07-10") +
               "## 需求条目\n| ID | 需求条目 | 类型 | prov |\n|--|--|--|--|\n| R1 | one | 功能 | e |\n")
        _write(self.tmp.name, "proj/001-a/design.md", "---\nstatus: frozen\n---\n")
        _write(self.tmp.name, "proj/001-a/plan.md", "---\nstatus: active\n---\n")
        f, _, *_x = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    def test_b7_bare_ref_resolution(self):
        _write(self.tmp.name, "proj/001-a/facts.md",
               "### F1 [VERIFIED]\n- 来源: 实测 `x`\n### F2 [VERIFIED superseded]\n- 来源: y\n")
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n用 [F1] 与 [F2] 与 [F9]，`[F7]` 只是提及。\n")
        f, _, *_x = wc.check_fact_refs("proj", self.card, ws._L1)
        self.assertIn("dangling-fref: [F2] (design.md)", f)   # superseded ≠ active
        self.assertIn("dangling-fref: [F9] (design.md)", f)
        self.assertNotIn("dangling-fref: [F1] (design.md)", f)
        self.assertEqual([x for x in f if "F7" in x], [])

    def test_b7_doc_local_fact_list_and_cross_card(self):
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n## 事实清单\n- F3: 实测。\n\n正文引 [F3] 和 "
               "[002:F1] 和 [003:F1]。\n")
        _write(self.tmp.name, "proj/002-b/facts.md", "### F1 [VERIFIED]\n- 来源: `x`\n")
        f, _, *_x = wc.check_fact_refs("proj", self.card, ws._L1)
        self.assertEqual([x for x in f if "[F3]" in x], [])
        self.assertEqual([x for x in f if "002:F1" in x], [])
        self.assertIn("dangling-fref: [003:F1] (design.md)", f)

    # -- B8
    def test_b8_cap_and_done_exemption(self):
        big = "---\nstatus: in-progress\n---\n" + "x\n" * 200
        _write(self.tmp.name, "proj/001-a/progress.md", big)
        _write(self.tmp.name, "proj/index.md",
               "| Card | Phase | 整体状态 | Deps |\n|--|--|--|--|\n| 001 | 实现 | active | — |\n")
        f, _, *_x = wc.check_progress_cap("proj", self.card, ws._L1)
        self.assertTrue(f and f[0].startswith("progress-over-cap:"))
        _write(self.tmp.name, "proj/index.md",
               "| Card | Phase | 整体状态 | Deps |\n|--|--|--|--|\n| 001 | 测试 | done | — |\n")
        self.assertEqual(wc.check_progress_cap("proj", self.card, ws._L1)[:2], ([], []))

    # -- C4
    def test_c4_amendment_overcap_forwardref(self):
        _write(self.tmp.name, "proj/001-a/adr/0001-x.md",
               "Status: accepted\n## Amendment\nbad\n" + "l\n" * 300)
        _write(self.tmp.name, "proj/001-a/adr/0002-y.md",
               "Status: superseded by ADR-0003\nptr ADR-0003\nagain ADR-0003\nthird ADR-0003\n")
        _write(self.tmp.name, "proj/001-a/adr/0003-z.md", "Status: accepted\nfine\n")
        f, _, *_x = wc.check_adr_hygiene("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("adr-amendment: adr/0001-x.md") for x in f))
        self.assertTrue(any(x.startswith("adr-over-cap: adr/0001-x.md") for x in f))
        self.assertTrue(any(x.startswith("adr-forward-ref: adr/0002-y.md") for x in f))
        self.assertEqual([x for x in f if "0003-z" in x], [])


NEW_BOARD_HEAD = "| Card | Phase | 整体状态 | Deps | Dir |\n|--|--|--|--|--|\n"


class ProjectScoped(unittest.TestCase):
    """021 T6: B3 board-rows / B4 root-strays / B5 board-monotonic / B1 project half
    + G6 markup-tolerant state parse."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.proj = os.path.join(self.tmp.name, "proj")

    def _board(self, rows):
        _write(self.tmp.name, "proj/index.md", NEW_BOARD_HEAD + rows)

    def test_state_markup_stripped_at_parse(self):
        self._board("| 001 | 实现 | **paused** | — | [x](./001-a/) |\n")
        self.assertEqual(ws.board(self.proj)["001"]["state"], "paused")

    def test_b3_both_directions(self):
        self._board("| 001 | 实现 | active | — | [x](./001-a/) |\n"
                    "| 009 | 需求 | todo | — | ghost |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "---\nstatus: drafting\n---\n")
        _write(self.tmp.name, "proj/002-b/requirement.md", "---\nstatus: drafting\n---\n")
        f, _, *_x = wc.check_board_rows("proj", self.proj, ws._L1)
        self.assertIn("board-missing-row: 002-b", f)
        self.assertIn("board-orphan-row: 009", f)

    def test_b3_old_format_exempt_and_missing_index_flags(self):
        _write(self.tmp.name, "proj/index.md", "| 001 | Title | Phase | Status |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        self.assertEqual(wc.check_board_rows("proj", self.proj, ws._L1)[:2], ([], []))
        os.remove(os.path.join(self.proj, "index.md"))
        f, _, *_x = wc.check_board_rows("proj", self.proj, ws._L1)
        self.assertEqual(f, ["no-index: index.md missing"])

    def test_b4_root_whitelist(self):
        self._board("")
        _write(self.tmp.name, "proj/roadmap.md", "x")
        _write(self.tmp.name, "proj/notes/a.md", "x")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        _write(self.tmp.name, "proj/stray.md", "x")
        os.makedirs(os.path.join(self.proj, "junkdir"))
        f, _, *_x = wc.check_root_strays("proj", self.proj, ws._L1)
        self.assertTrue(any(x.startswith("root-stray: junkdir") for x in f))
        self.assertTrue(any(x.startswith("root-stray: stray.md") for x in f))
        self.assertEqual(len(f), 2)

    def test_b5_cycle_state_and_done_constraints(self):
        self._board("| 001 | 测试 | done | 002 | [x](./001-a/) |\n"
                    "| 002 | 实现 | weird | 001 | [y](./002-b/) |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        _write(self.tmp.name, "proj/001-a/test.md", "---\nstatus: planned\n---\n")
        _write(self.tmp.name, "proj/002-b/requirement.md", "x")
        f, _, *_x = wc.check_board_monotonic("proj", self.proj, ws._L1)
        self.assertTrue(any("board-dep-cycle" in x for x in f))
        self.assertTrue(any("board-state: 002 'weird'" in x for x in f))
        self.assertTrue(any("done without close-out review" in x for x in f))
        self.assertTrue(any("test.md status 'planned'" in x for x in f))

    def test_b5_done_without_testmd_skips(self):
        self._board("| 001 | 测试 | done | — | [x](./001-a/) |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        _write(self.tmp.name, "proj/001-a/progress.md", "XS/S — review skipped\n")
        f, s, *_x = wc.check_board_monotonic("proj", self.proj, ws._L1)
        self.assertEqual(f, [])
        self.assertIn("board-monotonic: 001 done without test.md", s)

    def test_b5_interpunct_deps_and_freetext(self):
        self._board("| 001 | 实现 | active | 002 · 003 | [x](./001-a/) |\n")
        self.assertEqual(wc._deps_tokens("002 · 003"), ["002", "003"])
        self.assertEqual(wc._deps_tokens("是 005 的前置"), [])

    def test_b5_done_with_skip_note_and_passing_clean(self):
        self._board("| 001 | 测试 | done | — | [x](./001-a/) |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        _write(self.tmp.name, "proj/001-a/progress.md", "XS/S — review skipped\n")
        _write(self.tmp.name, "proj/001-a/test.md", "---\nstatus: passing\n---\n")
        self.assertEqual(wc.check_board_monotonic("proj", self.proj, ws._L1)[:2], ([], []))

    def test_b5_skip_note_wrapped_across_lines_still_counts(self):
        # the Close-out bullet may wrap mid-phrase (022 retro: a bolded
        # "review\n  skipped" false-positived the substring match)
        self._board("| 001 | 测试 | done | — | [x](./001-a/) |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        _write(self.tmp.name, "proj/001-a/progress.md",
               "- **Close-out:** sweep run · **XS/S — review\n  skipped**（理由）\n")
        _write(self.tmp.name, "proj/001-a/test.md", "---\nstatus: passing\n---\n")
        self.assertEqual(wc.check_board_monotonic("proj", self.proj, ws._L1)[:2], ([], []))

    def test_b5_freetext_deps_cell_yields_no_edges(self):
        # `是 005 的前置` is prose, not the Deps grammar — no edge, no false cycle (T9)
        self._board("| 005 | 实现 | active | 006(载体) | [x](./005-a/) |\n"
                    "| 006 | 实现 | active | 是 005 的前置 | [y](./006-b/) |\n")
        _write(self.tmp.name, "proj/005-a/requirement.md", "x")
        _write(self.tmp.name, "proj/006-b/requirement.md", "x")
        f, _, *_x = wc.check_board_monotonic("proj", self.proj, ws._L1)
        self.assertEqual([x for x in f if "dep-cycle" in x], [])

    def test_b1_project_half_scans_root_docs(self):
        kb = os.path.join(self.tmp.name, "kb")
        os.makedirs(kb)
        orig = wc._kb_root
        wc._kb_root = lambda: kb
        self.addCleanup(lambda: setattr(wc, "_kb_root", orig))
        self._board("")
        _write(self.tmp.name, "proj/roadmap.md", "[gone](./notes/none.md) [[wiki/proj/x]]\n")
        f, _, *_x = wc.check_project_links("proj", self.proj, ws._L1)
        self.assertIn("broken-link: roadmap.md ./notes/none.md", f)
        self.assertIn("broken-wikilink: roadmap.md [[wiki/proj/x]]", f)


class ExemptionChannel(unittest.TestCase):
    """023 T1: three-arity return adapter + exemption record stamping."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        _write(self.root, "proj/001-a/requirement.md", "---\nstatus: drafting\n---\n")
        self.card = os.path.join(self.root, "proj/001-a")

    def _with_entries(self, extra):
        orig = wc.CARD_CHECKS
        wc.CARD_CHECKS = orig + extra
        self.addCleanup(lambda: setattr(wc, "CARD_CHECKS", orig))

    def test_adapter_normalizes_three_arities(self):
        self.assertEqual(wc._normalize(["f"]), (["f"], [], []))
        self.assertEqual(wc._normalize((["f"], ["s"])), (["f"], ["s"], []))
        self.assertEqual(wc._normalize((["f"], ["s"], [("grandfathered", "why")])),
                         (["f"], ["s"], [("grandfathered", "why")]))

    def test_bare_list_entry_still_runs(self):
        self._with_entries((("bare", lambda p, c, ws: ["bare-finding"]),))
        f, _, _ = wc.check_card_all("proj", self.card, ws._L1)
        self.assertIn("bare-finding", f)

    def test_exemption_stamped_with_check_card_and_gate(self):
        self._with_entries((("emitter", lambda p, c, ws:
                             ([], [], [("grandfathered", "pre-cutoff")])),))
        _, _, exs = wc.check_card_all("proj", self.card, ws._L1)
        mine = [e for e in exs if e.check == "emitter"]
        self.assertEqual(len(mine), 1)
        self.assertEqual((mine[0].cls, mine[0].reason, mine[0].scope,
                          mine[0].card, mine[0].gated),
                         ("grandfathered", "pre-cutoff", "card", "001-a", False))

    def test_gated_true_after_a_gate_passed(self):
        _write(self.root, "proj/001-a/requirement.md", "---\nstatus: confirmed\n---\n")
        self._with_entries((("emitter", lambda p, c, ws:
                             ([], [], [("not-yet-due", "x")])),))
        _, _, exs = wc.check_card_all("proj", self.card, ws._L1)
        self.assertTrue([e for e in exs if e.check == "emitter"][0].gated)

    def test_project_scope_stamps_project_records(self):
        orig = wc.PROJECT_CHECKS
        wc.PROJECT_CHECKS = orig + (
            ("pemit", lambda p, d, ws: ([], [], [("grandfathered", "old-board")])),)
        self.addCleanup(lambda: setattr(wc, "PROJECT_CHECKS", orig))
        _write(self.root, "proj/index.md", "| 001 | x | todo | — |\n")
        _, _, exs = wc.check_project("proj", os.path.join(self.root, "proj"), ws._L1)
        mine = [e for e in exs if e.check == "pemit"]
        self.assertEqual((mine[0].scope, mine[0].card, mine[0].gated),
                         ("project", "", True))


class EmissionTableConsistency(unittest.TestCase):
    """023 T3 (E2, card half): the exact emission set of a fixture card equals the
    classification table's rows for the paths it exercises — an extra or missing
    emission point fails set equality, which the finding-set comparison (R5) can
    never see."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        kb = os.path.join(self.root, "kb")
        os.makedirs(kb)
        orig = wc._kb_root
        wc._kb_root = lambda: kb
        self.addCleanup(lambda: setattr(wc, "_kb_root", orig))

    def _triples(self, card):
        _, _, exs = wc.check_card_all("proj", os.path.join(self.root, card), ws._L1)
        return {(e.check, e.cls, e.reason) for e in exs}

    def test_legacy_gated_pre_cutoff_card_exact_set(self):
        _write(self.root, "proj/001-a/requirement.md",
               "---\nstatus: confirmed\ncreated: 2026-08-01\n---\n")
        ND, GF, CM = "not-yet-due", "grandfathered", "carrier-missing"
        self.assertEqual(self._triples("proj/001-a"), {
            ("design-sections", CM, "design.md missing"),
            ("fact-markers", CM, "facts.md missing/empty"),
            ("part-consistency", ND, "un-split card (no Parts table)"),
            ("governance", GF, "(i2) pre-2026-08-10 card"),
            ("governance", ND, "(i3) mode not ledger"),
            ("governance", ND, "(i4) mode not doc-gate"),
            ("ledger", GF, "legacy card without decisions.md"),
            ("transcription-marker", CM, "phase doc missing"),
            ("grill-reverse", GF, "pre-2026-08-11 card"),
            ("panel-receipts", GF, "pre-2026-08-11 card"),
            ("docgate-gateline", ND, "mode not doc-gate"),
            ("supersede-residue", CM, "no retired-phrase anchors (pre-021 card)"),
            ("links", CM, "phase doc missing/empty"),
            ("status-field", CM, "phase doc missing"),
            ("r-trace", CM, "no 需求条目 table"),
            ("fact-refs", CM, "phase doc missing/empty"),
            ("progress-cap", CM, "progress.md missing"),
            ("adr-hygiene", CM, "no adr dir or empty"),
            ("ledger-rows", GF, "pre-2026-08-19 card"),
            ("grill-signature", GF, "pre-2026-08-19 card"),
        })

    def test_docgate_draft_card_exact_set_and_ungated_flag(self):
        _write(self.root, "proj/002-b/requirement.md",
               "---\nstatus: drafting\ngovernance: doc-gate\ncreated: 2026-08-19\n---\n")
        ND, CM = "not-yet-due", "carrier-missing"
        self.assertEqual(self._triples("proj/002-b"), {
            ("design-sections", CM, "design.md missing"),
            ("fact-markers", CM, "facts.md missing/empty"),
            ("part-consistency", ND, "un-split card (no Parts table)"),
            ("governance", ND, "(i2) governed card, field check off"),
            ("governance", ND, "(i3) mode not ledger"),
            ("ledger", ND, "doc-gate card, ledger is a forbidden carrier"),
            ("transcription-marker", ND, "doc not past its gate"),
            ("transcription-marker", CM, "phase doc missing"),
            ("panel-receipts", ND, "card not past a gate"),
            ("docgate-gateline", ND, "doc not past its gate"),
            ("docgate-gateline", CM, "gated doc missing"),
            ("supersede-residue", CM, "no retired-phrase anchors"),
            ("supersede-residue", CM, "phase doc missing, anchors not harvested"),
            ("supersede-residue", CM, "no Change-log section / 被取代表述 sub-list"),
            ("links", CM, "phase doc missing/empty"),
            ("status-field", CM, "phase doc missing"),
            ("r-trace", CM, "no 需求条目 table"),
            ("fact-refs", CM, "phase doc missing/empty"),
            ("progress-cap", CM, "progress.md missing"),
            ("adr-hygiene", CM, "no adr dir or empty"),
            ("ledger-rows", ND, "doc-gate card, ledger is a forbidden carrier"),
            ("grill-signature", CM, "no grill-log, signatures not checkable"),
        })
        _, _, exs = wc.check_card_all("proj", os.path.join(self.root, "proj/002-b"),
                                      ws._L1)
        self.assertTrue(all(not e.gated for e in exs))   # E3: draft card stays gated=False

    def _project_triples(self, project_dir):
        _, _, raw = wc._run_entries(wc.PROJECT_CHECKS, ("po", project_dir), ws._L1)
        return {(cid, cls, reason) for cls, cid, reason in raw}

    def test_project_scope_old_format_exact_set(self):
        _write(self.root, "po/index.md", "| 001 | x | todo | — |\n")
        _write(self.root, "po/001-a/requirement.md", "---\nstatus: drafting\n---\n")
        GF, CM = "grandfathered", "carrier-missing"
        self.assertEqual(self._project_triples(os.path.join(self.root, "po")), {
            ("links", CM, "project doc missing/empty"),      # roadmap.md absent
            ("board-rows", GF, "old-format board"),
            ("board-monotonic", GF, "old-format board"),
        })

    def test_project_scope_new_format_exact_set(self):
        _write(self.root, "pn/index.md",
               "| Card | Phase | 整体状态 | Deps |\n|--|--|--|--|\n"
               "| 001 | 实现 | active | — |\n"
               "| 002 | 设计 |  | — |\n"
               "| 003 | 需求 | ? | — |\n")
        _write(self.root, "pn/roadmap.md", "x\n")
        for d in ("001-a", "002-b", "003-c"):
            _write(self.root, "pn/%s/requirement.md" % d, "---\nstatus: drafting\n---\n")
        ND, CM = "not-yet-due", "carrier-missing"
        self.assertEqual(self._project_triples(os.path.join(self.root, "pn")), {
            ("board-monotonic", CM, "board row state empty"),
            ("board-monotonic", ND, "board row state '?'"),
            ("board-monotonic", ND, "not done, done-series off"),
        })


class ExemptionRendering(unittest.TestCase):
    """023 T2: default counting tier (gate-scoped, two buckets) + --verbose-skips
    itemization + tail-N sourcing from printed skip lines."""

    EMIT = [("grandfathered", "pre-cutoff x"), ("grandfathered", "pre-cutoff y"),
            ("carrier-missing", "no z"), ("not-yet-due", "dim off")]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        _write(self.root, "proj/001-a/requirement.md", "---\nstatus: confirmed\n---\n")
        _write(self.root, "proj/002-b/requirement.md", "---\nstatus: drafting\n---\n")
        _write(self.root, "proj/index.md", "| 001 | x | todo | — |\n")
        # registry REPLACED (not appended): the real checks emit their own
        # exemptions on these bare fixtures, which would pollute the counts
        self._with_entries((("emit", lambda p, c, ws2: ([], [], list(self.EMIT))),))

    def _with_entries(self, entries):
        orig = wc.CARD_CHECKS
        wc.CARD_CHECKS = entries
        self.addCleanup(lambda: setattr(wc, "CARD_CHECKS", orig))

    def _run_verbose(self, arg):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ws.run_check(self.root, arg, verbose_skips=True)
        return code, buf.getvalue()

    def test_counting_line_two_buckets_card_scope(self):
        code, out = _run(self.root, "proj/001")
        self.assertEqual(code, 0)
        self.assertIn("skip: exempt: 2 grandfathered · 1 carrier-silent (--verbose-skips)",
                      out)
        self.assertNotIn("not-yet-due", out)

    def test_gate_scoped_draft_card_prints_no_counting_line(self):
        code, out = _run(self.root, "proj/002")
        self.assertEqual(code, 0)
        self.assertNotIn("exempt:", out)

    def test_verbose_itemizes_all_classes_no_gate_predicate(self):
        code, out = self._run_verbose("proj/002")
        self.assertEqual(code, 0)
        for line in ("skip: emit: pre-cutoff x [grandfathered]",
                     "skip: emit: no z [carrier-missing]",
                     "skip: emit: dim off [not-yet-due]"):
            self.assertIn(line, out)
        self.assertNotIn("exempt:", out)   # verbose replaces the counting tier

    def test_dedup_folds_repeat_hits(self):
        self._with_entries((("emit", lambda p, c, ws2: ([], [], list(self.EMIT))),
                            ("dup", lambda p, c, ws2:
                             ([], [], [("grandfathered", "same"),
                                       ("grandfathered", "same")])),))
        code, out = _run(self.root, "proj/001")
        self.assertIn("3 grandfathered", out)   # 2 from EMIT + 1 folded from dup

    def test_project_scope_prefixes_cards_and_adds_project_line(self):
        orig = wc.PROJECT_CHECKS
        wc.PROJECT_CHECKS = (
            ("pemit", lambda p, d, ws2: ([], [], [("grandfathered", "old-board")])),)
        self.addCleanup(lambda: setattr(wc, "PROJECT_CHECKS", orig))
        code, out = _run(self.root, "proj")
        self.assertIn("skip: 001-a: exempt: 2 grandfathered · 1 carrier-silent", out)
        self.assertIn("skip: project exempt: 1 grandfathered (--verbose-skips)", out)
        self.assertNotIn("002-b: exempt:", out)   # draft card stays silent

    def test_tail_counts_printed_skip_lines(self):
        code, out = _run(self.root, "proj/001")
        self.assertEqual(code, 0)
        n = sum(1 for ln in out.splitlines() if ln.startswith("skip: "))
        self.assertIn("check: ok (%d skipped)" % n, out)

    def test_findings_suppress_tail_not_counting_line(self):
        self._with_entries((("emit", lambda p, c, ws2: ([], [], list(self.EMIT))),
                            ("bad", lambda p, c, ws2: (["boom-finding"], [])),))
        code, out = _run(self.root, "proj/001")
        self.assertEqual(code, 1)
        self.assertIn("skip: exempt:", out)
        self.assertNotIn("check: ok", out)

    def test_finding_lines_identical_across_modes(self):
        # E4/R5 hermetic form: the exemption tier never leaks into the ⚠ set
        self._with_entries((("emit", lambda p, c, ws2: ([], [], list(self.EMIT))),
                            ("bad", lambda p, c, ws2: (["boom-finding"], [])),))
        code_d, out_d = _run(self.root, "proj/001")
        code_v, out_v = self._run_verbose("proj/001")
        pick = lambda out: [ln for ln in out.splitlines() if ln.startswith("⚠")]
        self.assertEqual(pick(out_d), pick(out_v))
        self.assertEqual((code_d, code_v), (1, 1))

    def test_counting_equals_verbose_itemization(self):
        # E2/R10: counting-line numbers = per-class verbose line counts, same card same run
        code, out = _run(self.root, "proj/001")
        m = re.search(r"exempt: (\d+) grandfathered · (\d+) carrier-silent", out)
        self.assertTrue(m)
        _, out_v = self._run_verbose("proj/001")
        vg = sum(1 for ln in out_v.splitlines() if ln.endswith("[grandfathered]"))
        vc = sum(1 for ln in out_v.splitlines() if ln.endswith("[carrier-missing]"))
        self.assertEqual((int(m.group(1)), int(m.group(2))), (vg, vc))


if __name__ == "__main__":
    unittest.main()
