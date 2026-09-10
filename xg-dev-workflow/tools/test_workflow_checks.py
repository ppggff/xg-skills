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

    def test_dates_ids_and_section_refs_not_tokens(self):
        # review #6: dates, ADR ids, uppercase id forms and § refs carry no weight
        self._card(rows="| R1 | 变更（2026-08-12，G11 残余、E7 随动、ADR-0003、§8 挂接） | 功能 | e |\n",
                   ledger="### R1 [requirement] approved\n- 陈述: 变更承接\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertEqual(self._x()[0], [])

    def test_repeated_token_single_finding(self):
        # review #6: per-cell dedup — the same missing token reports once
        self._card(rows="| R1 | 三源并集与三态区分 | 功能 | e |\n",
                   ledger="### R1 [requirement] approved\n- 陈述: 并集与区分\n"
                          "- approved: 2026-08-20 gate abc\n")
        self.assertEqual(self._x()[0], ["row-token-missing: R1 [三]"])

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

    def test_awaiting_human_marker_not_a_signature(self):
        # review #7: 待人工 documents openness — it must not demand closure;
        # an independent 人工 on the same line still signs
        self._card("- G21 待人工裁决（仍 open）\n", log=self._row("G21", status="open"))
        self.assertEqual(self._y(), ([], [], []))
        self._card("人工已裁 G7；其余待人工复核\n", log=self._row("G7", status="open"))
        self.assertEqual(self._y()[0], ["signature-open: G7 (requirement.md)"])

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


DESIGN_Z = """---
status: frozen
---
### 存储足迹

| 模块 | 存储 |
|---|---|
| 轮次账本 | 游标 |
| 备份产物 | tarball |

## How it meets the requirement

| R-id | 设计归宿 |
|---|---|
| [R1](./requirement.md) | 存储足迹 —— 安装产物经固定镜像 |
| [R2](./requirement.md) | 存储足迹的「轮次账本」行 |
| [R3](./requirement.md) | 轮次账本 —— 由 `D4` 承载 |
"""

REQ_AA = """---
status: confirmed
created: 2026-08-01
---
| ID | 需求条目 | 类型 | part | provenance |
|----|---------|------|------|------------|
| R1 | 安装产物经固定镜像承载 | 约束 | env | 人工（手段 commit 或 Dockerfile 归设计） |
| R2 | 呈现形态归设计 | 功能 | env | 人工 2026-08-01 |
"""


class DetailDisposition(unittest.TestCase):
    """(ab) 029 — the 详设 window closes at the design freeze."""

    FROZEN = "---\nstatus: frozen\n---\n# design\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.card = os.path.join(self.root, "proj/001-a")
        _write(self.root, "proj/001-a/requirement.md",
               "---\nstatus: confirmed\ncreated: 2026-08-19\n---\n")
        _write(self.root, "proj/001-a/design.md", self.FROZEN)
        _write(self.root, "proj/001-a/progress.md", "# progress\n\n- Phase: 设计\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self):
        return wc.check_detail_disposition("proj", self.card, ws._L1)

    def test_frozen_without_detail_or_note_flags(self):
        f, _s, _e = self._run()
        self.assertEqual(len(f), 1)
        self.assertTrue(f[0].startswith("detail-disposition:"))

    def test_detail_md_present_passes(self):
        _write(self.root, "proj/001-a/detail.md", "---\nstatus: baseline\n---\n")
        f, _s, e = self._run()
        self.assertEqual((f, e), ([], []))

    def test_recorded_disposition_passes(self):
        _write(self.root, "proj/001-a/progress.md",
               "# progress\n\n- sizing: XS/S — 详设 skipped（close-out review skipped）\n")
        f, _s, e = self._run()
        self.assertEqual((f, e), ([], []))

    def test_word_without_disposition_still_flags(self):
        _write(self.root, "proj/001-a/progress.md", "# progress\n\n- 详设 见 design\n")
        f, _s, _e = self._run()
        self.assertEqual(len(f), 1)

    def test_not_judged_before_freeze(self):
        _write(self.root, "proj/001-a/design.md", "---\nstatus: drafting\n---\n")
        f, _s, e = self._run()
        self.assertEqual(f, [])
        self.assertIn("not-yet-due", [c for c, _r in e])

    def test_done_card_exempt(self):
        _write(self.root, "proj/index.md",
               "| NNN | Phase | 整体状态 | Deps | Dir |\n|---|---|---|---|---|\n"
               "| 001 | 测试 | done | — | [a](./001-a/) |\n")
        f, _s, e = self._run()
        self.assertEqual(f, [])
        self.assertIn("not-yet-due", [c for c, _r in e])

    def test_grandfathered_before_cutoff(self):
        _write(self.root, "proj/001-a/requirement.md",
               "---\nstatus: confirmed\ncreated: 2026-01-01\n---\n")
        f, _s, e = self._run()
        self.assertEqual(f, [])
        self.assertIn("grandfathered", [c for c, _r in e])


class HomePointerAndHandoff(unittest.TestCase):
    """(z)/(aa) 028."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.card = os.path.join(self.root, "proj/001-a")
        _write(self.root, "proj/001-a/requirement.md",
               "---\nstatus: confirmed\ncreated: 2026-08-01\n---\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_bare_table_pointer_flags_row_named_and_decision_ref_pass(self):
        _write(self.root, "proj/001-a/design.md", DESIGN_Z)
        f, _s, _e = wc.check_home_pointer("proj", self.card, ws._L1)
        self.assertEqual(
            f, ["home-pointer: R1 cites 「存储足迹」 without naming a row"])

    def test_not_judged_before_freeze(self):
        _write(self.root, "proj/001-a/design.md",
               DESIGN_Z.replace("status: frozen", "status: drafting"))
        f, _s, e = wc.check_home_pointer("proj", self.card, ws._L1)
        self.assertEqual(f, [])
        self.assertIn("not-yet-due", [c for c, _r in e])

    def test_grandfathered_before_cutoff(self):
        _write(self.root, "proj/001-a/requirement.md",
               "---\nstatus: confirmed\ncreated: 2026-01-01\n---\n")
        _write(self.root, "proj/001-a/design.md", DESIGN_Z)
        f, _s, e = wc.check_home_pointer("proj", self.card, ws._L1)
        self.assertEqual(f, [])
        self.assertIn("grandfathered", [c for c, _r in e])

    def test_handoff_in_provenance_only_flags(self):
        _write(self.root, "proj/001-a/requirement.md", REQ_AA)
        f, _s, _e = wc.check_req_handoff("proj", self.card, ws._L1)
        self.assertEqual(
            f, ["req-handoff: R1 hands work to design in provenance only"])

    def test_handoff_in_statement_passes(self):
        _write(self.root, "proj/001-a/requirement.md",
               REQ_AA.replace("人工（手段 commit 或 Dockerfile 归设计）", "人工 2026-08-01"))
        f, _s, _e = wc.check_req_handoff("proj", self.card, ws._L1)
        self.assertEqual(f, [])


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

    def _lite_card(self, rel, status, body=""):
        _write(self.tmp.name, rel + "/design.md",
               "---\ngovernance: lite\nstatus: %s\ncreated: 2026-09-10\n---\n# x\n%s" % (status, body))

    def test_b5_lite_done_row_uses_lite_clauses(self):
        # 030 Req-4: a done lite row is judged on design.md status · 测试与验证 · a review record
        self._board("| 001 | lite | done | — | [x](./001-a/) |\n")
        self._lite_card("proj/001-a", "done",
                        "## 测试与验证\n| R2 review（S = light 自审） | diff 走读 | 无缺陷 |\n")
        f, s, *_x = wc.check_board_monotonic("proj", self.proj, ws._L1)
        self.assertEqual((f, s), ([], []))          # no test.md skip, no review finding

    def test_b5_lite_done_row_missing_pieces(self):
        self._board("| 001 | lite | done | — | [x](./001-a/) |\n")
        self._lite_card("proj/001-a", "executing", "## 任务\n- Task-1\n")
        f, _, *_x = wc.check_board_monotonic("proj", self.proj, ws._L1)
        self.assertTrue(any("design.md status 'executing'" in x for x in f))
        self.assertTrue(any("without 测试与验证" in x for x in f))
        self.assertTrue(any("without review record" in x for x in f))

    def test_ah_lite_board_sync(self):
        self._board("| 001 | lite | todo | — | [x](./001-a/) |\n"
                    "| 002 | lite | active | — | [y](./002-b/) |\n"
                    "| 003 | lite | dropped | — | [z](./003-c/) |\n"
                    "| 005 | lite | todo | — | [d](./005-d/) |\n| 006 | lite | done | — | [e](./006-e/) |\n"
                    "| 007 | lite | active | — | [f](./007-f/) |\n")
        self._lite_card("proj/001-a", "executing")
        self._lite_card("proj/002-b", "closing")
        self._lite_card("proj/003-c", "draft")
        f = wc.check_lite_board_sync("proj", os.path.join(self.proj, "001-a"), ws._L1)
        self.assertEqual(f, ["lite-board-sync: 001 board 'todo' vs design.md status 'executing' (expect 'active')"])
        self.assertEqual(wc.check_lite_board_sync("proj", os.path.join(self.proj, "002-b"), ws._L1), [])
        self.assertEqual(wc.check_lite_board_sync("proj", os.path.join(self.proj, "003-c"), ws._L1), [])
        self._lite_card("proj/005-d", "draft")
        self._lite_card("proj/006-e", "done   # 收口注记")
        self._lite_card("proj/007-f", "?")
        self.assertEqual(wc.check_lite_board_sync("proj", os.path.join(self.proj, "005-d"), ws._L1), [])
        self.assertEqual(wc.check_lite_board_sync("proj", os.path.join(self.proj, "006-e"), ws._L1), [])
        self.assertEqual(wc.check_lite_board_sync("proj", os.path.join(self.proj, "007-f"), ws._L1),
                         ["lite-board-sync: 007 design.md status '?' has no board mapping"])
        # runs inside the lite subset, never for another mode
        findings, _, exs = wc.check_card_all("proj", os.path.join(self.proj, "001-a"), ws._L1)
        self.assertTrue(any(x.startswith("lite-board-sync:") for x in findings))
        _write(self.tmp.name, "proj/004-d/requirement.md", "---\nid: 004\ncreated: 2026-01-01\n---\n")
        findings, _, exs = wc.check_card_all("proj", os.path.join(self.proj, "004-d"), ws._L1)
        self.assertFalse(any("lite-board-sync" in x for x in findings))
        self.assertFalse(any(e.check == "lite-board-sync" for e in exs))

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
            ("checkbox-monotonic", GF, "pre-2026-08-31 card"),
            ("home-pointer", CM, "design.md missing"),
            ("req-handoff", CM, "no 需求条目 table"),
            ("long-cell", CM, "requirement.md: created date unknown, long-cell era unjudged"),
            ("detail-disposition", CM, "design.md missing"),
            ("block-format", ND, "mode not doc-native"),
            ("block-anchor", ND, "mode not doc-native"),
            ("block-views", ND, "mode not doc-native"),
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
            ("checkbox-monotonic", "grandfathered", "pre-2026-08-31 card"),
            ("home-pointer", CM, "design.md missing"),
            ("req-handoff", CM, "no 需求条目 table"),
            ("long-cell", CM, "requirement.md: created date unknown, long-cell era unjudged"),
            ("detail-disposition", CM, "design.md missing"),
            ("block-format", ND, "mode not doc-native"),
            ("block-anchor", ND, "mode not doc-native"),
            ("block-views", ND, "mode not doc-native"),
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




class DocNativeBlockChecks(unittest.TestCase):
    """(ac)/(ad) — 026 slice 1: format core + git anchor over fixture git repos
    (the E9 sample set: three negative classes + no-false-positive positives)."""

    DATE = "2026-08-25"
    FM = "---\nid: 900\ntitle: t\ngovernance: doc-native-pilot\nstatus: drafting\n---\n\n"
    PROPOSED = "### Req-1 proposed — 样例\n- 陈述: 原文\n- 类型: 功能\n- why: w\n- provenance: p\n- depends-on: 无\n"

    def _env(self):
        stamp = self.DATE + "T12:00:00"
        return dict(os.environ,
                    GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                    GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                    GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
                    GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)

    def _repo(self):
        import subprocess
        root = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", root], check=True, env=self._env())
        card = os.path.join(root, "900-block-fixture")
        _write(root, "900-block-fixture/requirement.md", self.FM + self.PROPOSED)
        self._commit(root, "receipts")
        return root, card

    def _commit(self, root, msg):
        import subprocess
        subprocess.run(["git", "-C", root, "add", "."], check=True, env=self._env())
        subprocess.run(["git", "-C", root, "commit", "-q", "-m", msg],
                       check=True, env=self._env())
        out = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                             capture_output=True, text=True, env=self._env())
        return out.stdout.strip()

    def _approve(self, root, card, h, date=None):
        text = open(os.path.join(card, "requirement.md"), encoding="utf-8").read()
        text = text.replace("### Req-1 proposed", "### Req-1 approved")
        # transcription protocol is atomic: block flips AND doc status advance
        # in the same gate commit (the forward derived-status core, 029 T7,
        # flags the split shape)
        text = text.replace("status: drafting", "status: confirmed")
        text += "- approved: %s gate %s (single: 「go」)\n" % (date or self.DATE, h)
        _write(root, "900-block-fixture/requirement.md", text)
        self._commit(root, "gate")
        return text

    def test_first_approval_positive(self):
        root, card = self._repo()
        import subprocess
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        self._approve(root, card, h)
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertEqual(f, [])
        f, _, _ = wc.check_block_format(card, ws)
        self.assertEqual(f, [])

    def test_negative_text_drift(self):
        root, card = self._repo()
        import subprocess
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        text = self._approve(root, card, h)
        _write(root, "900-block-fixture/requirement.md",
               text.replace("- 陈述: 原文", "- 陈述: 被改"))
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any(x.startswith("文本被改: Req-1 field 陈述") for x in f))

    def test_negative_unreachable_hash(self):
        root, card = self._repo()
        self._approve(root, card, "1234567890ab")
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any(x.startswith("历史不可达: Req-1") for x in f))

    def test_negative_absent_at_baseline(self):
        root, card = self._repo()
        import subprocess
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        text = self._approve(root, card, h)
        text += ("\n### Req-2 approved — 伪造\n- 陈述: x\n"
                 "- approved: %s gate %s (single: 「go」)\n" % (self.DATE, h))
        _write(root, "900-block-fixture/requirement.md", text)
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any(x.startswith("基线处块缺席: Req-2") for x in f))

    def test_positive_m2_rebaseline(self):
        root, card = self._repo()
        import subprocess
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        text = self._approve(root, card, h)
        text = text.replace("- 陈述: 原文", "- 陈述: 改后")
        _write(root, "900-block-fixture/requirement.md", text)
        h2 = self._commit(root, "M2 landing")
        text += "- 变更: 就地改写 (M2 %s, %s)\n" % (h2, self.DATE)
        _write(root, "900-block-fixture/requirement.md", text)
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertEqual(f, [])

    def test_silent_retire_flagged_noted_retire_exempt(self):
        root, card = self._repo()
        import subprocess
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        text = self._approve(root, card, h)
        silent = text.replace("### Req-1 approved", "### Req-1 retired")
        _write(root, "900-block-fixture/requirement.md", silent)
        f, _, _ = wc.check_block_anchor(card, ws)
        # baseline is the receipts commit (proposed state); silent retire still flags
        self.assertTrue(any("state proposed→retired" in x for x in f))
        noted = silent + "- 退役: 不再需要 (M2 %s, %s)\n" % (h, self.DATE)
        _write(root, "900-block-fixture/requirement.md", noted)
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertEqual([x for x in f if "state" in x], [])

    def test_format_approved_note_missing_and_date(self):
        root, card = self._repo()
        import subprocess
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        # approved state, no note at all
        text = open(os.path.join(card, "requirement.md"), encoding="utf-8").read()
        _write(root, "900-block-fixture/requirement.md",
               text.replace("### Req-1 proposed", "### Req-1 approved"))
        f, _, _ = wc.check_block_format(card, ws)
        self.assertIn("approved-note-missing: Req-1", f)
        # note date != commit author date
        self._approve(root, card, h, date="2026-08-26")
        f, _, _ = wc.check_block_format(card, ws)
        self.assertTrue(any(x.startswith("note-date-mismatch: Req-1") for x in f))

    def test_non_docnative_card_skips(self):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "901-x")
        _write(root, "901-x/requirement.md",
               "---\nid: 901\ngovernance: doc-gate\n---\n")
        for fn in (wc.check_block_anchor, wc.check_block_format):
            f, s, exs = fn(card, ws)
            self.assertEqual((f, s), ([], []))
            self.assertEqual(exs[0][0], "not-yet-due")

    def test_proposed_block_not_applicable(self):
        root, card = self._repo()
        f, _, exs = wc.check_block_anchor(card, ws)
        self.assertEqual(f, [])
        self.assertTrue(any(cls == "not-yet-due" and "Req-1" in r
                            for cls, r in exs))


class DocNativeGrillV2(unittest.TestCase):
    """(y) v2 — 026 LLD-5: ask-id sweep + tier/round core over nine-col tables."""

    FM = "---\nid: 903\ngovernance: doc-native-pilot\n---\n\n"
    NINE = "| id | question | recommended | chosen | why | depends-on | tier | round | status |\n" \
           "|---|---|---|---|---|---|---|---|---|\n"

    def _card(self, grill_rows, block_note="(single Ask-1: 「go」)"):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md",
               self.FM + "### Req-1 approved — t\n- 陈述: x\n"
               "- approved: 2026-08-27 gate abcdef0 %s\n" % block_note)
        _write(d, "notes/grill-x.md", self.NINE + grill_rows)
        return d

    def test_noted_open_row_flags(self):
        d = self._card("| Ask-1 | q | r | c | w | — | 真判 | 1 | open |\n")
        f, _, _ = wc.check_grill_docnative(d, ws)
        self.assertTrue(any(x.startswith("signature-open: Ask-1") for x in f))

    def test_resolved_row_passes_and_prune_is_skip(self):
        d = self._card("| Ask-1 | q | r | c | w | — | 真判 | 1 | resolved → doc §x |\n")
        f, _, _ = wc.check_grill_docnative(d, ws)
        self.assertEqual(f, [])
        d2 = self._card("")  # row pruned entirely
        f, _, exs = wc.check_grill_docnative(d2, ws)
        self.assertEqual(f, [])
        self.assertTrue(any("prune-legal" in r for _, r in exs))

    def test_tier_vocab_and_round(self):
        d = self._card("| Ask-2 | q | r | c | w | — | 大概 | 0 | resolved → doc §x |\n")
        f, _, _ = wc.check_grill_docnative(d, ws)
        self.assertTrue(any(x.startswith("tier-vocab: Ask-2") for x in f))
        self.assertTrue(any(x.startswith("round-invalid: Ask-2") for x in f))

    def test_batch_table_round_rejects_tier2(self):
        rows = ("| Ask-2 | q | r | c | w | — | 照案 | 3 | resolved → doc §a |\n"
                "| Ask-3 | q | r | c | w | — | 照案 | 3 | resolved → doc §b |\n"
                "| Ask-4 | q | r | c | w | — | 真判 | 3 | resolved → doc §c |\n")
        f, _, _ = wc.check_grill_docnative(self._card(rows), ws)
        self.assertTrue(any(x.startswith("batch-round-tier2") for x in f))
        # solo 真判 + one batch-go row in the same gate round is the legal freeze shape
        rows2 = ("| Ask-2 | q | r | c | w | — | 真判 | 9 | resolved → doc §a |\n"
                 "| Ask-3 | q | r | c | w | — | 照案 | 9 | resolved → doc §b |\n")
        f, _, _ = wc.check_grill_docnative(self._card(rows2), ws)
        self.assertEqual([x for x in f if x.startswith("batch-round")], [])

    def test_unsure_round_cap(self):
        rows = "".join("| Ask-%d | q | r | c | w | — | 拿不准 | 4 | open |\n" % i
                       for i in range(2, 9))
        f, _, _ = wc.check_grill_docnative(self._card(rows), ws)
        self.assertTrue(any(x.startswith("unsure-over-cap") for x in f))

    def test_ninecol_era_per_file(self):
        # seven-col file on a doc-native card: created date unknown (no git) → visible skip
        d = self._card("")
        _write(d, "notes/grill-legacy.md",
               "| id | question | recommended | chosen | why | depends-on | status |\n"
               "|---|---|---|---|---|---|---|\n")
        f, _, exs = wc.check_grill_docnative(d, ws)
        self.assertTrue(any("nine-col era unjudged" in r for _, r in exs))

    def test_askid_time_boundary_in_block_format(self):
        d = self._card("", block_note="(single: 「go」)")   # post-cutoff note, no ask-id
        f, _, _ = wc.check_block_format(d, ws)
        self.assertTrue(any(x.startswith("ask-id-missing: Req-1") for x in f))
        d2 = tempfile.mkdtemp()  # pre-cutoff note stays optional
        _write(d2, "requirement.md",
               self.FM + "### Req-1 approved — t\n- 陈述: x\n"
               "- approved: 2026-08-25 gate abcdef0 (single: 「go」)\n")
        f, _, _ = wc.check_block_format(d2, ws)
        self.assertEqual([x for x in f if x.startswith("ask-id-missing")], [])


class LongCellHint(unittest.TestCase):
    """(ag) 028: over-long load-bearing slots — hints on skips, never findings."""

    FM = "---\nid: 905\ngovernance: doc-native\n---\n\n"
    LONG = "x" * 130
    SHORT = "y" * 30

    def _card(self, body, grill=None):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md", self.FM + body)
        if grill is not None:
            _write(d, "notes/grill-a.md", grill)
        return d

    def _post_cutoff(self, d):
        """No git in tmpdir → patch created-date to a post-cutoff day."""
        import unittest.mock as mock
        return mock.patch.object(wc, "_file_created",
                                 lambda card_dir, rel: "2026-08-30")

    def test_no_git_is_carrier_missing(self):
        d = self._card("### Req-1 proposed — t\n- 陈述: x\n")
        f, s, exs = wc.check_long_cells(d, ws)
        self.assertEqual((f, s), ([], []))
        self.assertTrue(any(cls == "carrier-missing" for cls, _ in exs))

    def test_long_table_cell_hints_not_finds(self):
        grill = ("| id | question | status |\n|---|---|---|\n"
                 "| Ask-1 | %s | open |\n" % self.LONG)
        d = self._card("### Req-1 proposed — t\n- 陈述: x\n", grill=grill)
        with self._post_cutoff(d):
            f, s, exs = wc.check_long_cells(d, ws)
        self.assertEqual(f, [])
        self.assertTrue(any(h.startswith("long-cell: notes/grill-a.md") and "question列" in h
                            for h in s))

    def test_short_cells_and_chosen_column_silent(self):
        grill = ("| id | question | chosen | status |\n|---|---|---|---|\n"
                 "| Ask-1 | %s | %s | open |\n" % (self.SHORT, self.LONG))
        d = self._card("### Req-1 proposed — t\n- 陈述: x\n", grill=grill)
        with self._post_cutoff(d):
            _, s, _ = wc.check_long_cells(d, ws)
        self.assertEqual(s, [])

    def test_fenced_table_silent(self):
        body = ("### Req-1 proposed — t\n- 陈述: x\n\n```\n| a | b |\n|---|---|\n"
                "| %s | c |\n```\n" % self.LONG)
        d = self._card(body)
        with self._post_cutoff(d):
            _, s, _ = wc.check_long_cells(d, ws)
        self.assertEqual(s, [])

    def test_single_line_field_hints_multiline_silent(self):
        body = ("### Req-1 proposed — t\n- 陈述: %s\n- why: w\n\n"
                "### Req-2 proposed — u\n- 陈述: 导语行。\n  %s\n" % (self.LONG, self.LONG))
        d = self._card(body)
        with self._post_cutoff(d):
            _, s, _ = wc.check_long_cells(d, ws)
        self.assertTrue(any("Req-1 field 陈述" in h for h in s))
        self.assertEqual([h for h in s if "Req-2" in h], [])

    def test_pre_cutoff_grandfathered(self):
        import unittest.mock as mock
        d = self._card("### Req-1 proposed — t\n- 陈述: %s\n" % self.LONG)
        with mock.patch.object(wc, "_file_created", lambda c, r: "2026-08-20"):
            f, s, exs = wc.check_long_cells(d, ws)
        self.assertEqual((f, s), ([], []))
        self.assertTrue(any(cls == "grandfathered" for cls, _ in exs))

    def test_exit_code_unaffected(self):
        grill = ("| id | question | status |\n|---|---|---|\n"
                 "| Ask-1 | %s | resolved → requirement.md §Req-1 |\n" % self.LONG)
        d = self._card("### Req-1 proposed — t\n- 陈述: 导语。\n- 类型: 约束\n"
                       "- why: w\n- provenance: e\n- depends-on: —\n")
        with self._post_cutoff(d):
            hints_only = wc.check_long_cells(d, ws)
        self.assertEqual(hints_only[0], [])   # never findings → never exit 1


class DocNativeBlockViews(unittest.TestCase):
    """(ae) — citations resolve, Effect coverage, generated-index consistency."""

    FM = "---\nid: 905\ngovernance: doc-native\n---\n\n"
    IDX = ("<!-- index:begin — generated by notes/crosscheck.py --write-index; "
           "do not hand-edit -->\n| id | 标题 | state |\n|---|---|---|\n"
           "| Req-1 | t | approved |\n<!-- index:end -->\n")

    def _card(self, extra="", idx=None, effect="- [ ] Eff-1: 判据 (verifies Req-1)\n"):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md",
               self.FM + (idx if idx is not None else self.IDX)
               + "### Req-1 approved — t\n- 陈述: x\n- 类型: 功能\n- provenance: p\n"
               + "- approved: 2026-08-25 gate abcdef0 (single: 「go」)\n\n"
               + "## Effect\n" + effect + extra)
        return d

    def test_clean_card_passes(self):
        f, _, _ = wc.check_block_views(self._card(), ws)
        self.assertEqual(f, [])

    def test_dangling_block_and_fact_and_eff_cites(self):
        extra = "\n引用 [Req-9] 与 [Fact-3] 与 [Eff-7] 与 [F2]。\n"
        f, _, _ = wc.check_block_views(self._card(extra=extra), ws)
        self.assertTrue(any("dangling-cite: [Req-9]" in x for x in f))
        self.assertTrue(any("dangling-cite: [Fact-3]" in x for x in f))
        self.assertTrue(any("dangling-cite: [Eff-7]" in x for x in f))
        self.assertTrue(any("dangling-cite: [F2]" in x for x in f))

    def test_ask_cites_prune_legal(self):
        f, _, _ = wc.check_block_views(self._card(extra="\n见 [Ask-99]。\n"), ws)
        self.assertEqual([x for x in f if "Ask-99" in x], [])

    def test_effect_uncovered_and_optout(self):
        f, _, _ = wc.check_block_views(self._card(effect="- [ ] Eff-1: 判据 (verifies Req-2)\n"), ws)
        self.assertTrue(any(x.startswith("effect-uncovered: Req-1") for x in f))
        d = self._card(effect="")
        t = open(os.path.join(d, "requirement.md"), encoding="utf-8").read()
        _write(d, "requirement.md", t.replace("- 陈述: x", "- 陈述: x（验收随 slice 3 定）"))
        f, _, _ = wc.check_block_views(d, ws)
        self.assertEqual([x for x in f if x.startswith("effect-uncovered")], [])

    def test_stale_index_flags(self):
        idx = self.IDX.replace("| Req-1 | t | approved |", "| Req-1 | 旧标题 | proposed |")
        f, _, _ = wc.check_block_views(self._card(idx=idx), ws)
        self.assertTrue(any(x.startswith("index-stale") for x in f))

    def test_field_missing_in_ac(self):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md",
               self.FM + "### Req-1 approved — t\n- 陈述: x\n"
               "- approved: 2026-08-25 gate abcdef0 (single: 「go」)\n")
        f, _, _ = wc.check_block_format(d, ws)
        self.assertTrue(any(x.startswith("field-missing: Req-1 类型") for x in f))
        self.assertTrue(any(x.startswith("field-missing: Req-1 provenance") for x in f))


class DocNativeReviewFixes(unittest.TestCase):
    """Close-out review High fixes (#1/#2/#3/#13) — the injection scenarios as
    misfire regressions."""

    DATE = "2026-08-25"
    FM = "---\nid: 908\ntitle: t\ngovernance: doc-native-pilot\nstatus: drafting\n---\n\n"
    BLOCK = ("### Req-1 proposed — 样例\n- 陈述: 原文\n- 类型: 功能\n- why: w\n"
             "- provenance: p\n- depends-on: 无\n")

    def _env(self):
        stamp = self.DATE + "T12:00:00"
        return dict(os.environ,
                    GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                    GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                    GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
                    GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)

    def _repo(self):
        import subprocess
        root = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", root], check=True, env=self._env())
        _write(root, "908-x/requirement.md", self.FM + self.BLOCK)
        self._commit(root, "receipts")
        return root, os.path.join(root, "908-x")

    def _commit(self, root, msg):
        import subprocess
        subprocess.run(["git", "-C", root, "add", "."], check=True, env=self._env())
        subprocess.run(["git", "-C", root, "commit", "-q", "-m", msg], check=True, env=self._env())
        return subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                              capture_output=True, text=True, env=self._env()).stdout.strip()

    def _head(self, root):
        import subprocess
        return subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                              capture_output=True, text=True, env=self._env()).stdout.strip()

    def _legal_m2(self):
        """approve → in-place rewrite with 同批 变更 + re-approve — the clean chain."""
        root, card = self._repo()
        h = self._head(root)
        text = (self.FM + self.BLOCK.replace("### Req-1 proposed", "### Req-1 approved")
                + "- approved: %s gate %s (single Ask-1: 「go」)\n" % (self.DATE, h))
        _write(root, "908-x/requirement.md", text)
        self._commit(root, "gate")
        text = text.replace("- 陈述: 原文", "- 陈述: 改后")
        _write(root, "908-x/requirement.md", text)
        h2 = self._commit(root, "M2 landing")
        text += ("- 变更: 就地改写 (M2 %s, %s)\n" % (h2, self.DATE)
                 + "- approved: %s gate %s (single Ask-2: 「go」)\n" % (self.DATE, h2))
        _write(root, "908-x/requirement.md", text)
        self._commit(root, "re-approve")
        return root, card, text

    def test_1_stale_note_grants_no_state_pass(self):
        root, card, text = self._legal_m2()
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertEqual(f, [])                       # clean chain green
        _write(root, "908-x/requirement.md",
               text.replace("### Req-1 approved", "### Req-1 retired"))
        f, _, _ = wc.check_block_anchor(card, ws)     # silent retire after legal M2
        self.assertTrue(any("state" in x and "同批" in x for x in f), f)

    def test_3_pending_reapproval_and_unresolved_hash(self):
        root, card, text = self._legal_m2()
        # strip the trailing re-approve → 代际链 pending
        pending = text[:text.rindex("- approved:")]
        _write(root, "908-x/requirement.md", pending)
        f, _, _ = wc.check_block_format(card, ws)
        self.assertTrue(any(x.startswith("pending-reapproval: Req-1") for x in f))
        # bogus second note hash → finding, not silent pass
        _write(root, "908-x/requirement.md",
               text + "- approved: %s gate abcdef9 (single Ask-3: 「再批」)\n" % self.DATE)
        f, _, _ = wc.check_block_format(card, ws)
        self.assertTrue(any(x.startswith("note-hash-unresolved: Req-1") for x in f))

    def test_2_derived_status_regression_and_proposal_section_exempt(self):
        root, card, text = self._legal_m2()
        uncancel = (text.replace("### Req-1 approved", "### Req-1 proposed")
                        .replace("status: drafting", "status: confirmed"))
        _write(root, "908-x/requirement.md", uncancel)
        f, _, _ = wc.check_block_format(card, ws)
        self.assertTrue(any(x.startswith("derived-status-regression: Req-1") for x in f))
        legal = (self.FM.replace("status: drafting", "status: confirmed")
                 + text.split("\n\n", 1)[1].replace("\n- 变更:", "\n- 变更:")  # keep block
                 + "\n## 提议变更\n\n### Req-2 proposed — 新提案\n- 陈述: x\n- 类型: 功能\n"
                 + "- why: w\n- provenance: p\n- depends-on: 无\n")
        _write(root, "908-x/requirement.md", legal)
        f, _, _ = wc.check_block_format(card, ws)
        self.assertEqual([x for x in f if x.startswith("derived-status-regression")], [], f)

    def test_2b_block_level_marker(self):
        root, card, text = self._legal_m2()
        _write(root, "908-x/requirement.md",
               text.replace("- 陈述: 改后", "- 陈述: 改后（落纸补充）"))
        f, _, _ = wc.check_transcription_markers("p", card, ws)
        self.assertTrue(any(x.startswith("stray-marker: Req-1") for x in f))

    def test_13_non_ancestor_baseline_unreachable(self):
        import subprocess
        root, card, text = self._legal_m2()
        subprocess.run(["git", "-C", root, "checkout", "-q", "-b", "side"], env=self._env())
        _write(root, "908-x/requirement.md", text.replace("- 陈述: 改后", "- 陈述: 旁支文本"))
        side = self._commit(root, "side landing")
        subprocess.run(["git", "-C", root, "checkout", "-q", "-"], env=self._env())
        forged = text + "- 变更: 指向旁支 (M2 %s, %s)\n" % (side, self.DATE)
        _write(root, "908-x/requirement.md", forged)
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any("非 HEAD 祖先" in x for x in f), f)


class DocNativeReviewFixesC(unittest.TestCase):
    """Review #5/#6/#14/#15: notation doc-form, batch-prune, Eff boundary, edges."""

    FM = "---\nid: 909\ngovernance: doc-native-pilot\nstatus: drafting\ncreated: 2026-08-27\n---\n\n"
    NINE = "| id | question | recommended | chosen | why | depends-on | tier | round | status |\n" \
           "|---|---|---|---|---|---|---|---|---|\n"
    SEVEN = "| id | question | recommended | chosen | why | depends-on | status |\n" \
            "|---|---|---|---|---|---|---|\n"

    def _card(self, grill="", note="(single Ask-1: 「go」)", grill_name="grill-x.md"):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md",
               self.FM + "### Req-1 approved — t\n- 陈述: x\n"
               "- approved: 2026-08-27 gate abcdef0 %s\n" % note)
        if grill:
            _write(d, "notes/" + grill_name, grill)
        return d

    def test_6_batch_note_row_pruned_is_finding_solo_is_skip(self):
        d = self._card(grill=self.NINE, note="(batch Ask-9: 「其他照案」)")
        f, _, _ = wc.check_grill_docnative(d, ws)
        self.assertTrue(any(x.startswith("batch-row-pruned: Ask-9") for x in f), f)
        d2 = self._card(grill=self.NINE, note="(single Ask-9: 「go」)")
        f, _, exs = wc.check_grill_docnative(d2, ws)
        self.assertEqual([x for x in f if "Ask-9" in x], [])
        self.assertTrue(any("solo prune-legal" in r for _, r in exs))

    def test_6b_sevencol_row_feeds_reverse_existence(self):
        row = "| Ask-9 | q | r | c | w | — | resolved → doc §x |\n"
        d = self._card(grill=self.SEVEN + row, note="(batch Ask-9: 「其他照案」)")
        f, _, _ = wc.check_grill_docnative(d, ws)
        self.assertEqual([x for x in f if "Ask-9" in x], [], f)   # 存量七列行在场即非 prune

    def test_5_docnative_notation_judged(self):
        bad = self.NINE + "| Ask-2 | q | r | c | w | — | 真判 | 1 | resolved → R5 |\n"
        d = self._card(grill=bad, grill_name="grill-y.md")
        f = wc._grill_shape_findings("grill-y.md", self.NINE +
                                     "| Ask-2 | q | r | c | w | — | 真判 | 1 | resolved → R5 |\n",
                                     gov="doc-native-pilot")
        self.assertTrue(any("notation" in x or "mismatch" in x for x in f), f)
        ok = wc._grill_shape_findings("grill-y.md", self.NINE +
                                      "| Ask-2 | q | r | c | w | — | 真判 | 1 | resolved → design.md §HLD-1 |\n",
                                      gov="doc-native-pilot")
        self.assertEqual([x for x in ok if "notation" in x or "mismatch" in x], [])

    def test_15_tier_empty_and_cap_boundary(self):
        rows5 = "".join("| Ask-%d | q | r | c | w | — | 拿不准 | 4 | open |\n" % i
                        for i in range(2, 7))
        f, _, _ = wc.check_grill_docnative(self._card(grill=self.NINE + rows5), ws)
        self.assertEqual([x for x in f if x.startswith("unsure-over-cap")], [])   # 5 过
        short = "| Ask-8 | q | r | c | w | — |\n"   # 七列头下才合法；九列头下缺 tier 格
        f, _, _ = wc.check_grill_docnative(self._card(grill=self.NINE + short), ws)
        self.assertTrue(any(x.startswith("tier-vocab: Ask-8") for x in f), f)

    def test_14_no_coverage_row_and_boundary(self):
        d = self._card()
        _write(d, "design.md", "---\nid: 909\nstatus: frozen\n---\n## How it meets\n[Req-1] 行\n")
        _write(d, "plan.md", "### T1: x\n- **Implements:** [Req-1](./requirement.md)\n")
        _write(d, "test.md", "| CASE5 | x | y |\n")   # 无 Eff 键行
        t2 = open(os.path.join(d, "requirement.md"), encoding="utf-8").read()
        _write(d, "requirement.md",
               t2 + "\n## Effect\n- [ ] Eff-5: 判据 (verifies Req-1)\n"
               + "\n| ID | 条目 |\n|---|---|\n| Req-1 | t |\n")
        f, _, _ = wc.check_r_trace("p", d, ws)
        self.assertTrue(any(x.startswith("trace: Eff-5 no-coverage-row") for x in f), f)


class DeadBlockDepsNotReferences(unittest.TestCase):
    """027 T2: a dead (superseded/retired) block's depends-on lines are not live
    references — no superseded-ref from dead→dead citation."""

    def test_dead_dep_no_superseded_ref(self):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md",
               "---\nid: 914\nstatus: confirmed\ngovernance: ledger\ncreated: 2026-08-01\n---\n"
               "## 需求条目\n| ID | 需求条目 |\n|---|---|\n| R1 | 活条目 |\n")
        _write(d, "decisions.md",
               "# 决策账本\n\n### R1 [requirement] approved\n- 陈述: 活。\n- depends-on: —\n"
               "- approved: 2026-08-02 gate abc1234\n\n"
               "### R2 [requirement] superseded\n- 陈述: 死。\n- depends-on: R3\n\n"
               "### R3 [requirement] retired\n- 陈述: 也死。\n- depends-on: —\n")
        findings, _, _ = wc.check_ledger(d, ws)
        self.assertFalse([f for f in findings if "superseded-ref" in f], findings)


class CheckboxMonotonic(unittest.TestCase):
    """(af) 027 HLD-5: two implications + boundary classifications."""

    PLAN_BAD = ("---\nid: 915\n---\n### T1: one\n- **Acceptance:**\n  - [ ] pending\n\n"
                "### Checkpoint: after T1\n- [x] all green so far\n")
    PLAN_OK = ("---\nid: 915\n---\n### T1: one\n- **Acceptance:**\n  - [x] done\n\n"
               "### Checkpoint: after T1\n- [x] all green so far\n")
    TEST_BAD = ("---\nstatus: passing\n---\n"
                "## Test plan\n### 回归 (regression)\n- [ ] behavior kept\n\n"
                "## Results\n| case | result |\n|---|---|\n| suite | `[x]` pass |\n")

    def _card(self, created="2026-09-01", plan=None, test=None):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md", "---\nid: 915\ncreated: %s\n---\n" % created)
        if plan:
            _write(d, "plan.md", plan)
        if test:
            _write(d, "test.md", test)
        return d

    def test_a1_premature_checkpoint_fires(self):
        f, _, _ = wc.check_checkbox_monotonic(self._card(plan=self.PLAN_BAD), ws)
        self.assertTrue(any("plan-checkpoint-premature" in x and "T1" in x for x in f), f)

    def test_a1_clean_checkpoint_silent(self):
        f, _, _ = wc.check_checkbox_monotonic(self._card(plan=self.PLAN_OK), ws)
        self.assertEqual(f, [])

    def test_a2_results_vs_regression_fires(self):
        f, _, _ = wc.check_checkbox_monotonic(self._card(test=self.TEST_BAD), ws)
        self.assertTrue(any("test-results-vs-regression" in x for x in f), f)

    def test_boundary_no_checkpoint_not_yet_due(self):
        plan = "---\nid: 915\n---\n### T1: one\n- **Acceptance:**\n  - [ ] pending\n"
        f, _, exs = wc.check_checkbox_monotonic(self._card(plan=plan), ws)
        self.assertEqual(f, [])
        self.assertIn(("not-yet-due", "plan has no Checkpoint block"), exs)

    def test_boundary_missing_sections_carrier_missing(self):
        test = "---\nstatus: passing\n---\n## Test plan\nno sections here\n"
        f, _, exs = wc.check_checkbox_monotonic(self._card(test=test), ws)
        self.assertEqual(f, [])
        kinds = [e[1] for e in exs if e[0] == "carrier-missing"]
        self.assertTrue(any("Results" in k for k in kinds), exs)
        self.assertTrue(any("回归" in k for k in kinds), exs)

    def test_pre_cutoff_grandfathered(self):
        f, _, exs = wc.check_checkbox_monotonic(
            self._card(created="2026-08-01", plan=self.PLAN_BAD), ws)
        self.assertEqual(f, [])
        self.assertEqual(exs[0][0], "grandfathered")


class CarrierPresentPromotions(unittest.TestCase):
    """027 T5 (HLD-4): four present-but-silent shapes are findings from their
    per-concern cutoffs; pre-cutoff classifies grandfathered."""

    def _card(self, created="2026-09-01", facts=None, adr=None, grill=None,
              gov="ledger"):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md",
               "---\nid: 916\nstatus: confirmed\ngovernance: %s\ncreated: %s\n---\n"
               % (gov, created))
        if facts:
            _write(d, "facts.md", facts)
        if adr:
            _write(d, "adr/0001-x.md", adr)
        if grill:
            _write(d, "notes/grill-design.md", grill)
            _write(d, "design.md", "---\nstatus: frozen\n---\n## How it meets\n")
        return d

    def test_fact_no_source_fires_post_cutoff(self):
        f, _, _ = wc.check_fact_markers(
            self._card(facts="### Fact-1 [VERIFIED]\n- 事实: x。\n"), ws)
        self.assertTrue(any("fact-no-source: Fact-1" in x for x in f), f)

    def test_fact_no_source_pre_cutoff_stays_exempt(self):
        f, _, exs = wc.check_fact_markers(
            self._card(created="2026-08-01",
                       facts="### Fact-1 [VERIFIED]\n- 事实: x。\n"), ws)
        self.assertEqual(f, [])
        self.assertIn(("carrier-missing", "VERIFIED block without 来源 field"), exs)

    def test_adr_status_unparsable_fires(self):
        f, _, _ = wc.check_adr_hygiene("p", self._card(
            adr="# a\nStatus: 待定\n"), ws)
        self.assertTrue(any("adr-status-unparsable" in x and "待定" in x for x in f), f)

    def test_adr_superseded_no_by_fires_and_grandfathers(self):
        adr = "# a\nStatus: superseded\n"
        f, _, _ = wc.check_adr_hygiene("p", self._card(adr=adr), ws)
        self.assertTrue(any("adr-superseded-no-by" in x for x in f), f)
        f2, _, exs2 = wc.check_adr_hygiene("p", self._card(created="2026-08-01", adr=adr), ws)
        self.assertEqual([x for x in f2 if "no-by" in x], [])
        self.assertTrue(any(e[0] == "grandfathered" and "no-by" in e[1] for e in exs2), exs2)

    def test_receipt_near_form_fires_post_cutoff(self):
        grill = "# log\n\n**Panel receipt: round = 9 · lenses = 1**\n"  # 冒号在闭 ** 前 = 近似形
        f, _, _ = wc.check_panel_receipts("p", self._card(grill=grill), ws)
        self.assertTrue(any("receipt-near-form" in x for x in f), f)


class CheckboxMonotonicReviewFixes(unittest.TestCase):
    """027 review fixes #4/#5/#6/#13."""

    def _card(self, plan=None, test=None):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md", "---\nid: 917\ncreated: 2026-09-01\n---\n")
        if plan:
            _write(d, "plan.md", plan)
        if test:
            _write(d, "test.md", test)
        return d

    def test_h2_section_does_not_leak_into_blocks(self):     # #4
        plan = ("### T1: a\n- **Acceptance:**\n  - [ ] 未验收\n\n"
                "### Checkpoint: after T1\n- [ ] builds green\n\n"
                "## Open questions\n- [x] 已确认某事\n")
        f, _, _ = wc.check_checkbox_monotonic(self._card(plan=plan), ws)
        self.assertEqual(f, [])

    def test_open_test_doc_not_yet_due(self):                # #5
        test = ("---\nstatus: planned\n---\n## Test plan\n### 回归\n- [ ] x\n\n"
                "## Results\n| a | `[x]` |\n")
        f, _, exs = wc.check_checkbox_monotonic(self._card(test=test), ws)
        self.assertEqual(f, [])
        self.assertIn(("not-yet-due", "test.md not closed out"), exs)

    def test_table_form_regression_rows_parsed(self):        # #6
        test = ("---\nstatus: passing\n---\n## Test plan\n"
                "### 回归\n| 行为 | 态 |\n|---|---|\n| kept | `[ ]` |\n\n"
                "## Results\n| a | `[x]` |\n")
        f, _, _ = wc.check_checkbox_monotonic(self._card(test=test), ws)
        self.assertTrue(any("test-results-vs-regression" in x for x in f), f)

    def test_regression_zero_parseable_rows_carrier_missing(self):   # #6
        test = ("---\nstatus: passing\n---\n## Test plan\n### 回归\n纯散文无勾选。\n\n"
                "## Results\n| a | `[x]` |\n")
        f, _, exs = wc.check_checkbox_monotonic(self._card(test=test), ws)
        self.assertEqual(f, [])
        self.assertIn(("carrier-missing", "回归节无可解析勾选行"), exs)

    def test_a1_one_finding_per_checkpoint_with_tids(self):  # #13
        plan = ("### T1: a\n- **Acceptance:**\n  - [ ] x\n\n"
                "### T2: b\n- **Acceptance:**\n  - [!] y\n\n"
                "### Checkpoint: after T1–T2\n- [x] green\n")
        f, _, _ = wc.check_checkbox_monotonic(self._card(plan=plan), ws)
        self.assertEqual(len(f), 1)
        self.assertIn("T1, T2", f[0])


class AdrStatusReviewFixes(unittest.TestCase):
    """027 review fixes #7/#8/#10."""

    def _card(self, adr, created="2026-09-01"):
        d = tempfile.mkdtemp()
        _write(d, "requirement.md", "---\nid: 918\ncreated: %s\n---\n" % created)
        _write(d, "adr/0001-x.md", adr)
        return d

    def test_lowercase_status_parsed(self):                  # #7
        f, _, _ = wc.check_adr_hygiene("p", self._card("# a\nstatus: 待定\n"), ws)
        self.assertTrue(any("adr-status-unparsable" in x for x in f), f)

    def test_bold_status_parsed(self):                       # #7
        f, _, _ = wc.check_adr_hygiene("p", self._card("# a\nStatus: **superseded** by ADR-0003\n"), ws)
        self.assertEqual([x for x in f if "no-by" in x or "unparsable" in x], [], f)

    def test_no_status_line_exempted(self):                  # #7
        f, _, exs = wc.check_adr_hygiene("p", self._card("# a\n无状态行。\n"), ws)
        self.assertTrue(any("without parsable Status line" in e[1] for e in exs), exs)

    def test_approved_rejected_parseable(self):              # #8
        for w in ("approved", "rejected"):
            f, _, _ = wc.check_adr_hygiene("p", self._card("# a\nStatus: %s\n" % w), ws)
            self.assertEqual([x for x in f if "unparsable" in x], [], (w, f))

    def test_markdown_link_by_pointer_accepted(self):        # #10
        f, _, _ = wc.check_adr_hygiene(
            "p", self._card("# a\nStatus: superseded by [ADR-0007](./0007-x.md)\n"), ws)
        self.assertEqual([x for x in f if "no-by" in x], [], f)


class FaceExtension(DocNativeBlockChecks):
    """029 T2: (ad) face widened to title + clauses via block_parse.face_diffs
    (shape grandfather: baseline without a title exempts the title face)."""

    def _approved_repo(self, proposed=None):
        import subprocess
        if proposed is not None:
            self.PROPOSED, keep = proposed, self.PROPOSED
        root, card = self._repo()
        if proposed is not None:
            self.PROPOSED = keep
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        text = self._approve(root, card, h)
        return root, card, text

    def test_title_drift_flagged(self):
        root, card, text = self._approved_repo()
        _write(root, "900-block-fixture/requirement.md",
               text.replace("— 样例", "— 被改标题"))
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any("文本被改: Req-1 field title" in x for x in f))

    def test_title_shape_grandfather(self):
        # baseline block has NO title (backfilled-title存量形) → title face exempt
        bare = self.PROPOSED.replace(" — 样例", "")
        root, card, text = self._approved_repo(proposed=bare)
        _write(root, "900-block-fixture/requirement.md",
               text.replace("### Req-1 approved", "### Req-1 approved — 补的标题"))
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertEqual([x for x in f if "title" in x], [])

    def test_clause_drift_flagged(self):
        with_clause = self.PROPOSED + "- (a) 子句甲\n"
        root, card, text = self._approved_repo(proposed=with_clause)
        _write(root, "900-block-fixture/requirement.md",
               text.replace("- (a) 子句甲", "- (a) 子句被改"))
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any("文本被改: Req-1 field clauses" in x for x in f))

    def test_clause_to_extras_flip_flagged(self):
        with_clause = self.PROPOSED + "- (a) 子句甲\n"
        root, card, text = self._approved_repo(proposed=with_clause)
        _write(root, "900-block-fixture/requirement.md",
               text.replace("- (a) 子句甲", "顶格附注化的原子句"))
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any("文本被改: Req-1 field clauses" in x for x in f))

    def test_legal_change_note_covers_title_and_clause(self):
        with_clause = self.PROPOSED + "- (a) 子句甲\n"
        root, card, text = self._approved_repo(proposed=with_clause)
        edited = text.replace("— 样例", "— 新标题").replace("子句甲", "子句乙")
        _write(root, "900-block-fixture/requirement.md", edited)
        h2 = self._commit(root, "M2 landing")
        edited += "- 变更: 标题与子句改写 (M2 %s, %s)\n" % (h2, self.DATE)
        _write(root, "900-block-fixture/requirement.md", edited)
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertEqual(f, [])


class ReverseCore(DocNativeBlockChecks):
    """029 T4: (ad) HEAD-prefix annotation core + dual-source reverse core."""

    def _gated_repo(self):
        """approve committed → HEAD holds the approved block + its note."""
        import subprocess
        root, card = self._repo()
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        text = self._approve(root, card, h)   # _approve commits the gate
        return root, card, text

    def test_annotation_rewrite_flagged(self):
        root, card, text = self._gated_repo()
        _write(root, "900-block-fixture/requirement.md",
               text.replace("「go」", "「ok」"))
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any("注记前缀被改: Req-1" in x for x in f), f)

    def test_unapprove_plus_note_delete_combo(self):
        root, card, text = self._gated_repo()
        tampered = "\n".join(l for l in text.splitlines()
                             if not l.startswith("- approved:")) + "\n"
        tampered = tampered.replace("### Req-1 approved", "### Req-1 proposed")
        _write(root, "900-block-fixture/requirement.md", tampered)
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any("反向回退: Req-1 state approved→proposed" in x
                            for x in f), f)
        self.assertTrue(any("注记前缀被改: Req-1" in x for x in f), f)

    def test_committed_deletion_baseline_arm(self):
        import subprocess
        root, card = self._repo()
        two = (self.PROPOSED
               + "\n### Req-2 proposed — 次样例\n- 陈述: 次原文\n- 类型: 功能\n"
                 "- why: w2\n- provenance: p2\n- depends-on: 无\n")
        _write(root, "900-block-fixture/requirement.md", self.FM + two)
        h = self._commit(root, "receipts2")
        text = (self.FM + two.replace("Req-1 proposed", "Req-1 approved")
                             .replace("Req-2 proposed", "Req-2 approved"))
        text += ("- approved: %s gate %s (single: 「go」)\n" % (self.DATE, h))
        _write(root, "900-block-fixture/requirement.md", text)
        self._commit(root, "gate")
        # commit a deletion of Req-2 (guard bypassed by direct git) — HEAD
        # no longer holds it; Req-1's baseline snapshot still does
        gone = (self.FM + two.split("\n### Req-2")[0].replace(
            "Req-1 proposed", "Req-1 approved")
            + "- approved: %s gate %s (single: 「go」)\n" % (self.DATE, h))
        _write(root, "900-block-fixture/requirement.md", gone)
        self._commit(root, "tamper: drop Req-2")
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any(x.startswith("反向缺席: Req-2") and "基线" in x
                            for x in f), f)

    def test_whole_doc_delete_head_arm(self):
        root, card, text = self._gated_repo()
        _write(root, "900-block-fixture/design.md",
               "---\nstatus: drafting\n---\n\n### HLD-1 approved — 设\n"
               "- 陈述: d\n- 类型: 功能\n- why: w\n- provenance: p\n- depends-on: 无\n"
               "- approved: %s gate 1234567 (single: 「go」)\n" % self.DATE)
        self._commit(root, "design landed")
        os.remove(os.path.join(card, "design.md"))
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any("反向缺席: HLD-1" in x and "HEAD:design.md" in x
                            for x in f), f)

    def test_new_doc_first_landing_not_flagged(self):
        root, card, text = self._gated_repo()
        _write(root, "900-block-fixture/design.md",
               "---\nstatus: drafting\n---\n\n### HLD-1 proposed — 设\n"
               "- 陈述: d\n- 类型: 功能\n- why: w\n- provenance: p\n- depends-on: 无\n")
        f, _, exs = wc.check_block_anchor(card, ws)
        self.assertFalse(any("历史不可达" in x and "design" in x for x in f), f)
        self.assertTrue(any("first landing" in e[1] and "design.md" in e[1]
                            for e in exs), exs)

    def test_legal_clarify_append_passes(self):
        root, card, text = self._gated_repo()
        _write(root, "900-block-fixture/requirement.md",
               text + "- 澄清: 补一句(人工「可」, 2026-09-01)\n")
        f, _, _ = wc.check_block_anchor(card, ws)
        self.assertEqual([x for x in f if "Req-1" in x], [])


class ExtrasHint(DocNativeBlockChecks):
    """029 T5 (HLD-7): extras drift vs anchor baseline — report-only hint."""

    WITH_EXTRAS = ("### Req-1 proposed — 样例\n- 陈述: 原文\n- 类型: 功能\n- why: w\n"
                   "- provenance: p\n- depends-on: 无\n附注:合法附注一行\n")

    def _hinted_repo(self):
        import subprocess
        keep, self.PROPOSED = self.PROPOSED, self.WITH_EXTRAS
        root, card = self._repo()
        self.PROPOSED = keep
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        text = self._approve(root, card, h)
        return root, card, text

    def test_extras_change_hints_not_finds(self):
        root, card, text = self._hinted_repo()
        _write(root, "900-block-fixture/requirement.md",
               text.replace("附注:合法附注一行", "附注:被改的附注"))
        f, hints, _ = wc.check_block_anchor(card, ws)
        self.assertEqual([x for x in f if "Req-1" in x], [])
        self.assertTrue(any(h.startswith("extras-hint: Req-1") for h in hints), hints)

    def test_extras_addition_hints(self):
        root, card, text = self._hinted_repo()
        _write(root, "900-block-fixture/requirement.md",
               text.replace("附注:合法附注一行", "附注:合法附注一行\n附注:新增第二行"))
        f, hints, _ = wc.check_block_anchor(card, ws)
        self.assertTrue(any(h.startswith("extras-hint: Req-1") for h in hints), hints)

    def test_extras_reflow_silent(self):
        root, card, text = self._hinted_repo()
        _write(root, "900-block-fixture/requirement.md",
               text.replace("附注:合法附注一行", "附注:合法附注一行   "))
        f, hints, _ = wc.check_block_anchor(card, ws)
        self.assertEqual([h for h in hints if "extras-hint" in h], [])

    def test_hint_rides_skip_slot_only(self):
        # exit-code semantics ride the runner's existing contract (findings
        # slot alone sets exit 1); the hint must never leak into slot 1
        root, card, text = self._hinted_repo()
        _write(root, "900-block-fixture/requirement.md",
               text.replace("附注:合法附注一行", "附注:被改的附注"))
        f, hints, _ = wc.check_block_anchor(card, ws)
        self.assertEqual(f, [])
        self.assertTrue(all(h.startswith("extras-hint:") for h in hints), hints)


class NoGrillLogUpgrade(unittest.TestCase):
    """029 T6 (HLD-2/HLD-3): blocks-without-log = finding from the cutoff on;
    every non-firing branch keeps the raw skip verbatim."""

    BLOCK = ("### Req-1 proposed — 样例\n- 陈述: 主句。\n- 类型: 功能\n- why: w\n"
             "- provenance: p\n- depends-on: 无\n")

    def _card(self, created, body, governance="doc-native"):
        root = tempfile.mkdtemp()
        fm = "---\nid: 900\ngovernance: %s\nstatus: drafting\ncreated: %s\n---\n\n" % (
            governance, created)
        _write(root, "900-x/requirement.md", fm + body)
        return os.path.join(root, "900-x")

    def test_blocks_without_log_finds(self):
        card = self._card("2026-09-02", self.BLOCK)
        f, s, _ = wc.check_grill_reverse("proj", card, ws)
        self.assertTrue(any(x.startswith("no-grill-log:") for x in f), (f, s))
        self.assertEqual(s, [])

    def test_scaffold_keeps_verbatim_skip(self):
        card = self._card("2026-09-02", "（背景散文,无条目 block)\n")
        f, s, _ = wc.check_grill_reverse("proj", card, ws)
        self.assertEqual(f, [])
        self.assertIn("grill-reverse: no-grill-log", s)

    def test_pre_cutoff_keeps_verbatim_skip(self):
        card = self._card("2026-09-01", self.BLOCK)
        f, s, _ = wc.check_grill_reverse("proj", card, ws)
        self.assertEqual(f, [])
        self.assertIn("grill-reverse: no-grill-log", s)

    def test_non_docnative_mode_keeps_skip(self):
        card = self._card("2026-09-02", self.BLOCK, governance="doc-gate")
        f, s, _ = wc.check_grill_reverse("proj", card, ws)
        self.assertEqual(f, [])
        self.assertIn("grill-reverse: no-grill-log", s)

    def test_log_present_no_finding(self):
        card = self._card("2026-09-02", self.BLOCK)
        _write(os.path.dirname(card), "900-x/notes/grill-requirement.md", "# log\n")
        f, s, _ = wc.check_grill_reverse("proj", card, ws)
        self.assertFalse(any(x.startswith("no-grill-log:") for x in f))

    def test_l_receipts_skip_untouched(self):
        card = self._card("2026-09-02", self.BLOCK)
        f, s, _ = wc.check_panel_receipts("proj", card, ws)
        # (l) keeps its own verbatim skip — the finding is (k)'s alone
        self.assertEqual(f, [])


class DerivedStatusForwardAndCreatedGuard(unittest.TestCase):
    """029 T7 (HLD-8/HLD-9): forward derived-status + governed created guard."""

    APPROVED = ("### Req-1 approved — 样例\n- 陈述: 主句。\n- 类型: 功能\n- why: w\n"
                "- provenance: p\n- depends-on: 无\n"
                "- approved: 2026-09-01 gate 1234567 (single: 「go」)\n")

    def _card(self, fm_extra, body):
        root = tempfile.mkdtemp()
        fm = "---\nid: 900\ngovernance: doc-native\n%s---\n\n" % fm_extra
        _write(root, "900-x/requirement.md", fm + body)
        return os.path.join(root, "900-x")

    def _blocks(self, card):
        return ws._block_parse().card_blocks(card)[0]

    def test_forward_all_approved_status_stalled(self):
        card = self._card("status: drafting\ncreated: 2026-09-01\n", self.APPROVED)
        f = wc._derived_status_findings(card, ws, self._blocks(card))
        self.assertTrue(any(x.startswith("derived-status-forward: requirement.md")
                            for x in f), f)

    def test_forward_quiet_with_proposed_block(self):
        body = self.APPROVED + "\n### Req-2 proposed — 次\n- 陈述: s\n- 类型: 功能\n- why: w\n- provenance: p\n- depends-on: 无\n"
        card = self._card("status: drafting\ncreated: 2026-09-01\n", body)
        f = wc._derived_status_findings(card, ws, self._blocks(card))
        self.assertFalse(any("forward" in x for x in f), f)

    def test_forward_quiet_when_status_binding(self):
        card = self._card("status: confirmed\ncreated: 2026-09-01\n", self.APPROVED)
        f = wc._derived_status_findings(card, ws, self._blocks(card))
        self.assertFalse(any("forward" in x for x in f), f)

    def test_forward_retired_blocks_dont_block_or_fire_alone(self):
        body = self.APPROVED + "\n### Req-2 retired — 退\n- 陈述: s\n- 类型: 功能\n- why: w\n- provenance: p\n- depends-on: 无\n"
        card = self._card("status: drafting\ncreated: 2026-09-01\n", body)
        f = wc._derived_status_findings(card, ws, self._blocks(card))
        self.assertTrue(any("forward" in x for x in f), f)

    def test_created_missing_on_governed_finds(self):
        card = self._card("status: drafting\n", "散文。\n")
        f, _, _ = wc.check_governance(card, ws)
        self.assertTrue(any(x.startswith("created-missing:") for x in f), f)

    def test_created_malformed_on_governed_finds(self):
        card = self._card("status: drafting\ncreated: 09/01/2026\n", "散文。\n")
        f, _, _ = wc.check_governance(card, ws)
        self.assertTrue(any(x.startswith("created-missing:") for x in f), f)

    def test_legacy_card_untouched(self):
        root = tempfile.mkdtemp()
        _write(root, "900-x/requirement.md", "无 frontmatter 的 legacy 卡\n")
        f, _, exs = wc.check_governance(os.path.join(root, "900-x"), ws)
        self.assertFalse(any("created-missing" in x for x in f), f)
        self.assertTrue(any("(i2)" in e[1] for e in exs))


class ReviewRoundFixes(DocNativeBlockChecks):
    """029 review #3/#6/#14: committed-deletion label, forward union +
    transported exemption, retired-only quiet."""

    def test_committed_doc_deletion_is_finding_not_first_landing(self):
        root, card = self._repo()
        import subprocess
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        self._approve(root, card, h)
        _write(root, "900-block-fixture/design.md",
               "---\nstatus: drafting\n---\n\n### HLD-1 approved — 设\n"
               "- 陈述: d\n- 类型: 功能\n- why: w\n- provenance: p\n- depends-on: 无\n"
               "- approved: %s gate 1234567 (single: 「go」)\n" % self.DATE)
        self._commit(root, "design landed")
        os.remove(os.path.join(card, "design.md"))
        self._commit(root, "tamper: drop design.md")
        f, _, exs = wc.check_block_anchor(card, ws)
        self.assertTrue(any("反向缺席: design.md 曾入库" in x for x in f), f)
        self.assertFalse(any("first landing" in e[1] and "design" in e[1]
                             for e in exs), exs)

    APPROVED_NOTE = "- approved: 2026-09-01 gate 1234567 (single: 「go」)\n"

    def _fw_card(self, body, status="drafting"):
        root = tempfile.mkdtemp()
        fm = ("---\nid: 900\ngovernance: doc-native\nstatus: %s\n"
              "created: 2026-09-01\n---\n\n" % status)
        _write(root, "900-x/requirement.md", fm + body)
        card = os.path.join(root, "900-x")
        return card, ws._block_parse().card_blocks(card)[0]

    def test_forward_union_catches_note_without_state(self):
        body = ("### Req-1 proposed — 样例\n- 陈述: s\n- 类型: 功能\n- why: w\n"
                "- provenance: p\n- depends-on: 无\n" + self.APPROVED_NOTE)
        card, blocks = self._fw_card(body)
        f = wc._derived_status_findings(card, ws, blocks)
        self.assertTrue(any("derived-status-forward" in x for x in f), f)

    def test_forward_transported_shape_exempt(self):
        body = ("### Req-1 approved — 搬运\n- 陈述: s\n- 类型: 功能\n- why: w\n"
                "- provenance: p\n- depends-on: 无\n"
                "- 来源: 025 R1 approved 2026-08-20 gate 13fed19 — verbatim\n"
                + self.APPROVED_NOTE)
        card, blocks = self._fw_card(body)
        f = wc._derived_status_findings(card, ws, blocks)
        self.assertFalse(any("forward" in x for x in f), f)

    def test_forward_retired_only_quiet(self):
        body = ("### Req-1 retired — 退\n- 陈述: s\n- 类型: 功能\n- why: w\n"
                "- provenance: p\n- depends-on: 无\n")
        card, blocks = self._fw_card(body)
        f = wc._derived_status_findings(card, ws, blocks)
        self.assertFalse(any("forward" in x for x in f), f)

    def test_marker_in_extras_caught_by_j(self):
        root, card = self._repo()
        import subprocess
        h = subprocess.run(["git", "-C", root, "rev-parse", "--short=7", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        text = self._approve(root, card, h)
        _write(root, "900-block-fixture/requirement.md",
               text.replace("- approved:", "（落纸补充）藏在附注行\n- approved:", 1))
        f, _, _ = wc.check_transcription_markers("proj", card, ws)
        self.assertTrue(any("stray-marker: Req-1" in x for x in f), f)


if __name__ == "__main__":
    unittest.main()
