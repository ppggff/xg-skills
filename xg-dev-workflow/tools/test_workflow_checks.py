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

    def test_a2_non_canonical_shape_skips_per_file(self):
        self._req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", THREE_COL_LOG)
        _, s = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("grill-reverse: non-canonical-grill-log")
                            and "grill-x.md" in x for x in s))

    def test_a2_resolved_row_needs_ledger_home(self):
        self._req(gov="ledger")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", CANON_LOG)
        # canonical table but no decisions.md at all → visible skip, not a finding (#13)
        f, s = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])
        self.assertTrue(any("no-ledger" in x for x in s))
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### D2 [design] approved\n- 陈述: other\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertIn("resolved-no-home: D1", f)
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### D1 [design] approved\n- 陈述: x\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    # -- A2 shape era (022)
    def test_a2_shape_era_no_canonical_is_finding(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", THREE_COL_LOG)
        f, s = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("non-canonical-grill-log: grill-x.md") for x in f))
        self.assertFalse(any("non-canonical" in x for x in s))   # finding replaced the skip

    def test_a2_shape_era_needs_gate(self):
        self._req(status="drafting", created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", THREE_COL_LOG)
        f, s = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])   # drafting card: era inactive, old skip preserved
        self.assertTrue(any("non-canonical" in x for x in s))

    def test_a2_pre_shape_cutoff_behavior_unchanged(self):
        self._req(created="2026-08-17")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", THREE_COL_LOG)
        f, s = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertEqual(f, [])
        self.assertTrue(any("non-canonical" in x for x in s))

    def test_a2_mixed_card_deviant_file_not_masked(self):
        self._req(gov="ledger", created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-a.md", CANON_LOG)
        _write(self.tmp.name, "proj/001-a/notes/grill-b.md", THREE_COL_LOG)
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### D1 [design] approved\n- 陈述: x\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any("non-canonical-grill-log: grill-b.md" in x for x in f))
        self.assertFalse(any("grill-a.md" in x for x in f))

    def test_a2_column_drop_flagged(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "| id | status |\n|---|---|\n| G1 | resolved |\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("column-drop: grill-x.md") for x in f))

    def test_a2_misplaced_decision_row_in_nav_table(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "\n| 轮 | 议题 | 结果 |\n|---|---|---|\n"
               "| 1 | x | resolved → D9 |\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("misplaced-decision-row: grill-x.md") for x in f))

    def test_a2_pure_nav_and_mentions_clean(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG
               + "\n轮次摘要：本轮讨论了 `resolved → D1` 的写法（反引号 mention）。\n"
               + "| verdict | note |\n|---|---|\n| ok | adopted → G3 收进 |\n"
               + "```\nresolved → D2 在 fence 内也是 mention\n```\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertFalse(any("misplaced" in x for x in f))

    def test_a2_notation_docgate_ledger_id_is_mismatch(self):
        self._req(created="2026-08-18")   # doc-gate card
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md", CANON_LOG)
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("notation-mismatch: grill-x.md")
                            and "doc-gate" in x for x in f))

    def test_a2_notation_docgate_doc_section_ok(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "| id | question | recommended | chosen | why | depends-on | status |\n"
               "|---|---|---|---|---|---|---|\n"
               "| G1 | q | r | c | w | — | resolved → requirement.md §需求条目（R1–R4） |\n"
               "| G2 | q | r | c | w | G1 | resolved |\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertFalse(any("notation-mismatch" in x for x in f))

    def test_a2_notation_ledger_doc_section_is_mismatch(self):
        self._req(gov="ledger", created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "| id | question | recommended | chosen | why | depends-on | status |\n"
               "|---|---|---|---|---|---|---|\n"
               "| G1 | q | r | c | w | — | resolved → design.md §思路 |\n")
        _write(self.tmp.name, "proj/001-a/decisions.md",
               "### D1 [design] approved\n- 陈述: x\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any("notation-mismatch" in x and "ledger" in x for x in f))

    def test_a2_alignment_rows_exempt(self):
        self._req(gov="ledger", created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "| id | question | recommended | chosen | why | depends-on | status |\n"
               "|---|---|---|---|---|---|---|\n"
               "| G1 | q | r | c | w | — | resolved |\n"
               "| G2 | q | r | c | w | G1 | open（gate 待裁） |\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertFalse(any("notation-mismatch" in x for x in f))

    def test_a2_misplaced_in_prose_flagged_with_line(self):
        self._req(created="2026-08-18")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "\n某轮散文写了 resolved → D7 却没进表。\n")
        f, _ = wc.check_grill_reverse("proj", self.card, ws._L1)
        self.assertTrue(any("misplaced-decision-row: grill-x.md line 5" in x for x in f))

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
        f, _ = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    def test_a3_missing_header_key_flagged(self):
        self._shape_req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "## Panel receipt — r1\n"
               "- **Header**：round = pre-gate · lenses = 1/2/3/4。\n- adopted → G3。\n")
        f, _ = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("receipt-missing-key")
                            and "round type" in x and "re-dispatch" in x for x in f))

    def test_a3_bad_disposition_lead_word_without_mark(self):
        self._shape_req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + self.RECEIPT_OK + "- adopted 但同行无箭头标记。\n")
        f, _ = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertTrue(any("receipt-bad-disposition" in x for x in f))

    def test_a3_clean_run_literal_passes(self):
        self._shape_req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "**Panel receipt** — 轻量复核：round = r2 · "
               "round type = 定向 · lenses = 4 · re-dispatch = yes（scope=修订）。"
               "no findings。\n")
        f, _ = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    def test_a3_block_without_dispositions_flagged(self):
        self._shape_req()
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               CANON_LOG + "## Panel receipt — r1\n"
               "- **Header**：round = pre-gate · round type = 全量 · "
               "lenses = 1/2/3/4 · re-dispatch = no。\n判词全 satisfied。\n")
        f, _ = wc.check_panel_receipts("proj", self.card, ws._L1)
        self.assertTrue(any("receipt-no-dispositions" in x for x in f))

    def test_a3_pre_shape_cutoff_presence_only(self):
        self._req(created="2026-08-17")
        _write(self.tmp.name, "proj/001-a/notes/grill-x.md",
               "### Panel receipt — r1\n判词自由形（021 时代不受结构核）。\n")
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


SUP_ADR = ("---\nStatus: accepted\n---\n# ADR-0002 x\n\n## Supersedes (optional)\n\n"
           "ADR-0001 — replaces it.\n\n## 被取代表述 (required when superseding)\n\n"
           "- `旧词A` → `新词`\n")


class SupersedeResidue(unittest.TestCase):
    """021 T4: A4′ machine anchors + resident conditional sweep + --from-card."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.card = os.path.join(self.tmp.name, "proj", "001-a")
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-08-17"))

    def test_no_anchor_predicate_off(self):
        self.assertEqual(wc.check_supersede_residue("proj", self.card, ws._L1), ([], []))

    def test_adr_terms_flag_body_residue(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/design.md", "---\nstatus: frozen\n---\n正文还在说旧词A。\n")
        f, _ = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertTrue(any("superseded-phrase: design.md" in x for x in f))

    def test_history_sections_masked(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: frozen\n---\n## Change log\n- 旧词A 已被取代（历史）。\n")
        f, _ = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertEqual([x for x in f if "superseded-phrase" in x], [])

    def test_superseding_adr_without_section_flags(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md",
               "---\nStatus: accepted\n---\n## Supersedes (optional)\n\nADR-0001 — y.\n")
        f, _ = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertIn("adr-retired-missing: adr/0002-x.md", f)

    def test_malformed_list_line_flags(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md",
               SUP_ADR.replace("- `旧词A` → `新词`", "- 旧词A 没有反引号"))
        f, _ = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertTrue(any(x.startswith("adr-retired-format:") for x in f))

    def test_changelog_sublist_anchor(self):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-08-17") +
               "## Change log\n- 2026-08-17 — M2 变更，被取代表述：\n  - `旧词B` → `新词`\n")
        _write(self.tmp.name, "proj/001-a/design.md", "---\nstatus: frozen\n---\n旧词B 残留。\n")
        f, _ = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertTrue(any("[旧词B]" in x for x in f))

    def test_dead_adr_and_short_terms_excluded(self):
        # a superseded ADR's terms are no longer authoritative; a 1-char term is format (T9)
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md",
               SUP_ADR.replace("Status: accepted", "Status: superseded by ADR-0003"))
        _write(self.tmp.name, "proj/001-a/adr/0003-z.md",
               SUP_ADR.replace("- `旧词A` → `新词`", "- `/` → `空格`"))
        terms, findings = wc._csp().terms_from_card(self.card)
        self.assertEqual(terms, [])
        self.assertTrue(any("adr-retired-format" in x for x in findings))

    def test_sweep_scope_excludes_execution_docs(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/progress.md", "历史叙述提到旧词A。\n")
        f, _ = wc.check_supersede_residue("proj", self.card, ws._L1)
        self.assertEqual([x for x in f if "superseded-phrase" in x], [])

    def test_replay_cjk_quote_forms(self):
        # 021 review #1 — replay of the pre-021 corpus shapes: a pure-quote line
        # yields the phrase; a quote wrapping inline code is ambiguous → format
        adr = SUP_ADR.replace(
            "- `旧词A` → `新词`",
            "- 「旧短语整句」 → 新说法\n- 「`in-progress` **允许直接继续**」 —— 未限定动作\n"
            "- `<old phrase>` → `<replacement>`")
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", adr)
        terms, findings = wc._csp().terms_from_card(self.card)
        self.assertEqual(terms, ["旧短语整句"])
        self.assertTrue(any("adr-retired-format" in x for x in findings))  # mixed form
        self.assertEqual([x for x in findings if "old phrase" in x], [])   # placeholder silent

    def test_backticked_mention_exempt_in_resident_sweep(self):
        # 021 review #2 — the docstring's escape hatch actually works now
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: frozen\n---\n历史上叫 `旧词A`，现已改名。\n```\n旧词A in fence\n```\n还在用旧词A的这行要报。\n")
        f, _ = wc.check_supersede_residue("proj", self.card, ws._L1)
        hits = [x for x in f if "superseded-phrase" in x]
        self.assertEqual(len(hits), 1)
        self.assertIn(":8 ", hits[0] + " ")   # only the bare-use line survives

    def test_gate_line_in_template_comment_not_counted(self):
        # 021 review #4 — the audit anchor can't be satisfied by template guidance
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-08-17") +
               "## Change log\n- created.\n"
               "<!-- gate passages land here as `- <date> — <状态>（gate abc123）` -->\n")
        f, _ = wc.check_docgate_gateline("proj", self.card, ws._L1)
        self.assertIn("no-gate-line: requirement.md", f)

    def test_from_card_parity_with_manual_terms(self):
        _write(self.tmp.name, "proj/001-a/adr/0002-x.md", SUP_ADR)
        _write(self.tmp.name, "proj/001-a/design.md", "---\n---\n旧词A here.\n")
        csp = wc._csp()
        terms, findings = csp.terms_from_card(self.card)
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
        self.assertEqual(wc.check_links("proj", self.card, ws._L1), ([], []))

    def test_b7_h3_fact_list_section(self):
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n### 事实清单\n- F9: 实测。\n\n引 [F9]。\n")
        self.assertEqual(wc.check_fact_refs("proj", self.card, ws._L1), ([], []))

    def test_b1_wikilink_resolution_and_alias(self):
        _write(self.kb, "wiki/proj/real.md", "x")
        _write(self.kb, "wiki/proj/other.md", "---\naliases: [nick]\n---\nx")
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n[[wiki/proj/real]] [[wiki/proj/nick]] "
               "[[wiki/proj/gone]] `[[wiki/proj/mention]]` [[wiki/<project>/<slug>]]\n")
        f, s = wc.check_links("proj", self.card, ws._L1)
        self.assertEqual(f, ["broken-wikilink: design.md [[wiki/proj/gone]]"])

    def test_b1_relative_links(self):
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n[a](./requirement.md) [b](./notes/gone.md)\n")
        f, _ = wc.check_links("proj", self.card, ws._L1)
        self.assertEqual(f, ["broken-link: design.md ./notes/gone.md"])

    def test_b1_no_kb_root_skips_whole_check(self):
        wc_orig = wc._kb_root
        wc._kb_root = lambda: os.path.join(self.tmp.name, "nope")
        try:
            f, s = wc.check_links("proj", self.card, ws._L1)
        finally:
            wc._kb_root = wc_orig
        self.assertEqual((f, s), ([], ["links: no-kb-root"]))

    # -- B2′
    def test_b2_missing_status_flags(self):
        _write(self.tmp.name, "proj/001-a/design.md", "no frontmatter\n")
        f, _ = wc.check_status_field("proj", self.card, ws._L1)
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
        f, _ = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertIn("trace: R2 no-design-home", f)
        self.assertNotIn("trace: R1 no-design-home", f)

    def test_b6_drafting_design_not_gated(self):
        self._req_with_items(extra_docs=[("design.md", "---\nstatus: drafting\n---\n")])
        f, _ = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertEqual([x for x in f if "no-design-home" in x], [])

    def test_b6_not_in_items_always_fires(self):
        self._req_with_items(extra_docs=[("design.md",
            "---\nstatus: drafting\n---\n## How it meets the requirement\n"
            "| R | home |\n|--|--|\n| R9 | ghost |\n")])
        f, _ = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertIn("trace: R9 not-in-需求条目", f)

    def test_b6_prose_only_requirement_exempt(self):
        f, _ = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    # -- B7
    def test_b7_head_trailing_annotation_tolerated(self):
        _write(self.tmp.name, "proj/001-a/facts.md",
               "### F24 [VERIFIED] —— 待实测注记\n- 来源: `x`\n")
        _write(self.tmp.name, "proj/001-a/design.md", "---\nstatus: drafting\n---\n引 [F24]。\n")
        self.assertEqual(wc.check_fact_refs("proj", self.card, ws._L1), ([], []))

    def test_b6_pre_cutoff_card_downstream_dims_off(self):
        _write(self.tmp.name, "proj/001-a/requirement.md",
               REQ_FM % ("confirmed", "doc-gate", "2026-07-10") +
               "## 需求条目\n| ID | 需求条目 | 类型 | prov |\n|--|--|--|--|\n| R1 | one | 功能 | e |\n")
        _write(self.tmp.name, "proj/001-a/design.md", "---\nstatus: frozen\n---\n")
        _write(self.tmp.name, "proj/001-a/plan.md", "---\nstatus: active\n---\n")
        f, _ = wc.check_r_trace("proj", self.card, ws._L1)
        self.assertEqual(f, [])

    def test_b7_bare_ref_resolution(self):
        _write(self.tmp.name, "proj/001-a/facts.md",
               "### F1 [VERIFIED]\n- 来源: 实测 `x`\n### F2 [VERIFIED superseded]\n- 来源: y\n")
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n用 [F1] 与 [F2] 与 [F9]，`[F7]` 只是提及。\n")
        f, _ = wc.check_fact_refs("proj", self.card, ws._L1)
        self.assertIn("dangling-fref: [F2] (design.md)", f)   # superseded ≠ active
        self.assertIn("dangling-fref: [F9] (design.md)", f)
        self.assertNotIn("dangling-fref: [F1] (design.md)", f)
        self.assertEqual([x for x in f if "F7" in x], [])

    def test_b7_doc_local_fact_list_and_cross_card(self):
        _write(self.tmp.name, "proj/001-a/design.md",
               "---\nstatus: drafting\n---\n## 事实清单\n- F3: 实测。\n\n正文引 [F3] 和 "
               "[002:F1] 和 [003:F1]。\n")
        _write(self.tmp.name, "proj/002-b/facts.md", "### F1 [VERIFIED]\n- 来源: `x`\n")
        f, _ = wc.check_fact_refs("proj", self.card, ws._L1)
        self.assertEqual([x for x in f if "[F3]" in x], [])
        self.assertEqual([x for x in f if "002:F1" in x], [])
        self.assertIn("dangling-fref: [003:F1] (design.md)", f)

    # -- B8
    def test_b8_cap_and_done_exemption(self):
        big = "---\nstatus: in-progress\n---\n" + "x\n" * 200
        _write(self.tmp.name, "proj/001-a/progress.md", big)
        _write(self.tmp.name, "proj/index.md",
               "| Card | Phase | 整体状态 | Deps |\n|--|--|--|--|\n| 001 | 实现 | active | — |\n")
        f, _ = wc.check_progress_cap("proj", self.card, ws._L1)
        self.assertTrue(f and f[0].startswith("progress-over-cap:"))
        _write(self.tmp.name, "proj/index.md",
               "| Card | Phase | 整体状态 | Deps |\n|--|--|--|--|\n| 001 | 测试 | done | — |\n")
        self.assertEqual(wc.check_progress_cap("proj", self.card, ws._L1), ([], []))

    # -- C4
    def test_c4_amendment_overcap_forwardref(self):
        _write(self.tmp.name, "proj/001-a/adr/0001-x.md",
               "Status: accepted\n## Amendment\nbad\n" + "l\n" * 300)
        _write(self.tmp.name, "proj/001-a/adr/0002-y.md",
               "Status: superseded by ADR-0003\nptr ADR-0003\nagain ADR-0003\nthird ADR-0003\n")
        _write(self.tmp.name, "proj/001-a/adr/0003-z.md", "Status: accepted\nfine\n")
        f, _ = wc.check_adr_hygiene("proj", self.card, ws._L1)
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
        f, _ = wc.check_board_rows("proj", self.proj, ws._L1)
        self.assertIn("board-missing-row: 002-b", f)
        self.assertIn("board-orphan-row: 009", f)

    def test_b3_old_format_exempt_and_missing_index_flags(self):
        _write(self.tmp.name, "proj/index.md", "| 001 | Title | Phase | Status |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        self.assertEqual(wc.check_board_rows("proj", self.proj, ws._L1), ([], []))
        os.remove(os.path.join(self.proj, "index.md"))
        f, _ = wc.check_board_rows("proj", self.proj, ws._L1)
        self.assertEqual(f, ["no-index: index.md missing"])

    def test_b4_root_whitelist(self):
        self._board("")
        _write(self.tmp.name, "proj/roadmap.md", "x")
        _write(self.tmp.name, "proj/notes/a.md", "x")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        _write(self.tmp.name, "proj/stray.md", "x")
        os.makedirs(os.path.join(self.proj, "junkdir"))
        f, _ = wc.check_root_strays("proj", self.proj, ws._L1)
        self.assertTrue(any(x.startswith("root-stray: junkdir") for x in f))
        self.assertTrue(any(x.startswith("root-stray: stray.md") for x in f))
        self.assertEqual(len(f), 2)

    def test_b5_cycle_state_and_done_constraints(self):
        self._board("| 001 | 测试 | done | 002 | [x](./001-a/) |\n"
                    "| 002 | 实现 | weird | 001 | [y](./002-b/) |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        _write(self.tmp.name, "proj/001-a/test.md", "---\nstatus: planned\n---\n")
        _write(self.tmp.name, "proj/002-b/requirement.md", "x")
        f, _ = wc.check_board_monotonic("proj", self.proj, ws._L1)
        self.assertTrue(any("board-dep-cycle" in x for x in f))
        self.assertTrue(any("board-state: 002 'weird'" in x for x in f))
        self.assertTrue(any("done without close-out review" in x for x in f))
        self.assertTrue(any("test.md status 'planned'" in x for x in f))

    def test_b5_done_without_testmd_skips(self):
        self._board("| 001 | 测试 | done | — | [x](./001-a/) |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        _write(self.tmp.name, "proj/001-a/progress.md", "XS/S — review skipped\n")
        f, s = wc.check_board_monotonic("proj", self.proj, ws._L1)
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
        self.assertEqual(wc.check_board_monotonic("proj", self.proj, ws._L1), ([], []))

    def test_b5_skip_note_wrapped_across_lines_still_counts(self):
        # the Close-out bullet may wrap mid-phrase (022 retro: a bolded
        # "review\n  skipped" false-positived the substring match)
        self._board("| 001 | 测试 | done | — | [x](./001-a/) |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "x")
        _write(self.tmp.name, "proj/001-a/progress.md",
               "- **Close-out:** sweep run · **XS/S — review\n  skipped**（理由）\n")
        _write(self.tmp.name, "proj/001-a/test.md", "---\nstatus: passing\n---\n")
        self.assertEqual(wc.check_board_monotonic("proj", self.proj, ws._L1), ([], []))

    def test_b5_freetext_deps_cell_yields_no_edges(self):
        # `是 005 的前置` is prose, not the Deps grammar — no edge, no false cycle (T9)
        self._board("| 005 | 实现 | active | 006(载体) | [x](./005-a/) |\n"
                    "| 006 | 实现 | active | 是 005 的前置 | [y](./006-b/) |\n")
        _write(self.tmp.name, "proj/005-a/requirement.md", "x")
        _write(self.tmp.name, "proj/006-b/requirement.md", "x")
        f, _ = wc.check_board_monotonic("proj", self.proj, ws._L1)
        self.assertEqual([x for x in f if "dep-cycle" in x], [])

    def test_b1_project_half_scans_root_docs(self):
        kb = os.path.join(self.tmp.name, "kb")
        os.makedirs(kb)
        orig = wc._kb_root
        wc._kb_root = lambda: kb
        self.addCleanup(lambda: setattr(wc, "_kb_root", orig))
        self._board("")
        _write(self.tmp.name, "proj/roadmap.md", "[gone](./notes/none.md) [[wiki/proj/x]]\n")
        f, _ = wc.check_project_links("proj", self.proj, ws._L1)
        self.assertIn("broken-link: roadmap.md ./notes/none.md", f)
        self.assertIn("broken-wikilink: roadmap.md [[wiki/proj/x]]", f)


if __name__ == "__main__":
    unittest.main()
