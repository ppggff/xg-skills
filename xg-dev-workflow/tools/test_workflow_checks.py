#!/usr/bin/env python3
"""Tests for workflow-checks.py (the lite half of the L2 check domain) + the --check dispatch tiers.
The 存量-only check tests live in legacy/test_legacy_checks.py (031 split)."""
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


REQ_FM = "---\nstatus: %s\ngovernance: %s\ncreated: %s\n---\n"


NEW_BOARD_HEAD = "| Card | Phase | 整体状态 | Deps | Dir |\n|--|--|--|--|--|\n"


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

    def test_b5_lite_done_row_review_doc_counts(self):
        # the review record may be a notes/review-*.md file with no 自审/review line in design.md
        self._board("| 001 | lite | done | — | [x](./001-a/) |\n")
        self._lite_card("proj/001-a", "done", "## 测试与验证\n- 已做: x\n")
        _write(self.tmp.name, "proj/001-a/notes/review-2026-09-10-x.md", "# review\n")
        self.assertEqual(wc.check_board_monotonic("proj", self.proj, ws._L1)[:2], ([], []))

    def test_ai_governance_carrier_conflict(self):
        self._board("| 001 | 需求 | active | — | [x](./001-a/) |\n")
        _write(self.tmp.name, "proj/001-a/requirement.md", "---\nid: 001\ngovernance: doc-native\ncreated: 2026-09-01\n---\n")
        self._lite_card("proj/001-a", "executing")
        f = wc.check_governance_carriers("proj", os.path.join(self.proj, "001-a"), ws._L1)
        self.assertEqual(f, ["governance-carrier-conflict: requirement.md 'doc-native' vs design.md 'lite' (requirement.md wins)"])
        _write(self.tmp.name, "proj/002-b/requirement.md", "---\nid: 002\ngovernance: doc-native\ncreated: 2026-09-01\n---\n")
        _write(self.tmp.name, "proj/002-b/design.md", "---\nstatus: drafting\n---\n")
        self.assertEqual(wc.check_governance_carriers("proj", os.path.join(self.proj, "002-b"), ws._L1), [])

    def test_ah_lite_board_sync_no_row_is_a_visible_skip(self):
        self._board("")
        self._lite_card("proj/009-z", "executing")
        f, s = wc.check_lite_board_sync("proj", os.path.join(self.proj, "009-z"), ws._L1)
        self.assertEqual(f, [])
        self.assertTrue(s and s[0].startswith("lite-board-sync: 009 no board row"))

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


class LegacySplit(unittest.TestCase):
    """031: the 存量-only checks live in legacy/legacy_checks.py — a lite card never loads them, a
    missing legacy half fails loudly (exit 2, stderr), and the assembled registry keeps the pre-split order."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        _write(self.root, "proj/index.md", "| Card | Phase | 整体状态 | Deps | Dir |\n|---|---|---|---|---|\n"
               "| 001 | lite | todo | — | [001-a](./001-a/) |\n| 002 | 需求 | active | — | [002-b](./002-b/) |\n")
        _write(self.root, "proj/001-a/design.md", "---\nid: 001\ntitle: a\nproject: proj\ngovernance: lite\nstatus: draft\ncreated: 2026-09-14\n---\n# 001 a\n")
        _write(self.root, "proj/002-b/requirement.md", "---\nstatus: drafting\ngovernance: ledger\ncreated: 2026-09-14\n---\n# 002\n")

    def _no_legacy(self):
        def boom():
            raise wc.LegacyChecksUnavailable("legacy half unavailable (test)")
        orig = wc._legacy
        wc._legacy = boom
        self.addCleanup(lambda: setattr(wc, "_legacy", orig))
        pinned = wc.__dict__.pop("CARD_CHECKS", None)   # an earlier test's cleanup may have pinned the registry
        if pinned is not None:
            self.addCleanup(lambda: setattr(wc, "CARD_CHECKS", pinned))

    def test_lite_card_never_touches_the_legacy_half(self):
        self._no_legacy()
        findings, skips, exs = wc.check_card_all("proj", os.path.join(self.root, "proj/001-a"), ws._L1)
        self.assertNotIn("check-error", " ".join(findings))
        self.assertIn(("not-yet-due", "lite", "lite card: mode checks not applicable"), [(e.cls, e.check, e.reason) for e in exs])

    def test_missing_legacy_half_exits_2_not_a_finding(self):
        self._no_legacy()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                ws.run_check(self.root, "proj/002")
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("legacy half unavailable", err.getvalue())
        self.assertNotIn("check-error", out.getvalue())

    def test_registry_order_and_forwarding(self):
        ids = [e[0] for e in wc.CARD_CHECKS]
        self.assertEqual(ids, list(wc.CARD_ORDER))
        self.assertEqual(len(ids), 29)
        self.assertEqual(ids[-1], "lite-doc-form")           # 032: appended after lite-board-sync
        self.assertEqual(ids[10:12], ["links", "status-field"])   # lite checks stay interleaved where they were
        self.assertTrue(callable(wc.check_grill_reverse))          # a legacy name resolves through __getattr__
        with self.assertRaises(AttributeError):
            wc.no_such_check_anywhere


class ConstraintsBasis(unittest.TestCase):
    """031 Inv-4: every check a lite card runs (LITE_CHECKS + the project scope) names the constraints.md
    row it enforces as the first token of its manifest basis."""

    def test_lite_and_project_checks_point_at_a_constraints_row(self):
        rules = open(os.path.join(TOOLS, "..", "references", "constraints.md"), encoding="utf-8").read()
        ids = set(re.findall(r"^- ([A-Z][a-z]+-\d+) \(", rules, re.M))
        self.assertGreater(len(ids), 20)
        entries = [e for e in wc.CARD_CHECKS if e[0] in wc.LITE_CHECKS] + list(wc.PROJECT_CHECKS)
        self.assertEqual(len(entries), len(wc.LITE_CHECKS) + len(wc.PROJECT_CHECKS))
        for cid, _fn, meta in entries:
            head = meta["basis"].split(" · ")[0]
            self.assertIn(head, ids, "%s basis %r names no constraints.md row" % (cid, meta["basis"]))


LITE_FM = ("---\nid: %s\ntitle: t\nproject: proj\ngovernance: lite\nstatus: %s\ncreated: %s\n"
           "go: abc\n%s---\n")


class LiteDocForm(unittest.TestCase):
    """032 Req-5: the lite doc-form check (aj) — ten sub-checks behind one lite-only registry entry.
    Gate: created >= LITE_DOC_FORM_CUTOFF or a `skill:` frontmatter field → findings; an older lite card
    without the field gets the same lines as skips (pre-cutoff hints) plus a grandfathered exemption;
    a non-lite card never runs it. `skill:` trailing the skill repo HEAD is always a hint."""

    GOOD_DESIGN = (
        "# 001 t\n## 当前摘要\nx\n## 目标与边界\n"
        "### Req-1 待验证 — a\n- 陈述:\n  lead\n  - (a) uses a lock on the spool file\n  - (b) two\n"
        "- 验证: v\n- 来源: s\n- 变更: 2026-09-16 x（人：「好」）\n- 确认: 2026-09-16 go\n"
        "## 当前方案\n### 契约与不变量\n### Inv-1 lock\n- 不变量: one holder\n- 归宿: Req-1\n- 检验: test\n"
        "## 待解问题与证据\n- Q-1 x\n## 任务\nplan.md\n## 测试与验证\n| 项 | 结果 |\n|---|---|\n| V1 | ok |\n"
        "## 授权记录\n- 2026-09-16 · **go** · Req-1 · 人原话：「go」· 基线 abc\n")

    BAD_DESIGN = (
        "# 001 t\n## 当前摘要\nx\n## 目标与边界\n"
        "### Req-1 待验证 — a\n- 陈述: (a) takes a lock (b) sends a signal (c) three\n"
        "- 验证: v\n- 来源: s\n- 变更: 2026-09-15 dropped (b)\n- 确认: 2026-09-14 go\n"
        "## 当前方案\n| 案 | 代价 |\n|---|---|\n| A | " + "长" * 130 + " |\n"
        "## 待解问题与证据\n- Fact-3 says so\n## 任务\nx\n## 测试与验证\nx\n"
        "## 授权记录\n- 2026-09-15 · **go（续）** · Req-1 · 按 lite.md 视为 go · 基线 abc\n"
        "- 2026-09-14 · **go** · Req-1 · 人原话：「nope」· 基线 abc\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        _write(self.root, "proj/index.md", NEW_BOARD_HEAD +
               "| 001 | lite | active | — | [001-a](./001-a/) |\n"
               "| 002 | lite | done | — | [002-b](./002-b/) |\n"
               "| 003 | 需求 | active | — | [003-c](./003-c/) |\n")
        orig = wc._skill_repo_head
        wc._skill_repo_head = lambda: "abc1234"
        self.addCleanup(lambda: setattr(wc, "_skill_repo_head", orig))
        kb = os.path.join(self.root, "kb")
        os.makedirs(kb)
        orig_kb = wc._kb_root
        wc._kb_root = lambda: kb
        self.addCleanup(lambda: setattr(wc, "_kb_root", orig_kb))

    def _card(self, rel, status, created, skill, design, messages, extra=()):
        fm = LITE_FM % (rel[:3], status, created, ("skill: %s   # note\n" % skill) if skill else "")
        _write(self.root, "proj/%s/design.md" % rel, fm + design)
        _write(self.root, "proj/%s/notes/human-messages.md" % rel, messages)
        for name, text in extra:
            _write(self.root, "proj/%s/%s" % (rel, name), text)
        return os.path.join(self.root, "proj", rel)

    def _tags(self, lines):
        return sorted(l.split(":")[0].replace("lite-doc-form (pre-cutoff hint)", "").strip(" /")
                      for l in lines if "doc-form" in l or l.startswith(("long-cell", "inline-clause")))

    def test_clean_gated_card_has_no_findings(self):
        card = self._card("001-a", "executing", "2026-09-16", "abc1234", self.GOOD_DESIGN,
                          "- 2026-09-16 「go」\n", extra=[("notes/lens-2026-09-16.md", "x")])
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        self.assertEqual((f, s), ([], []))

    def test_each_violation_flags_once_on_a_gated_card(self):
        card = self._card("001-a", "done", "2026-09-16", "old1111", self.BAD_DESIGN,
                          "- 2026-09-14 「开卡」\n")
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        tags = sorted(l.split(":")[0] for l in f)
        self.assertEqual(tags, sorted([
            "doc-form/long-cell", "doc-form/inline-clause", "doc-form/inv-missing",
            "doc-form/observations-missing", "doc-form/fact-home",
            "doc-form/go-quote", "doc-form/go-quote", "doc-form/change-unconfirmed",
            "doc-form/messages-stale", "doc-form/lens-missing"]))
        self.assertTrue(any("skill-behind" in x and "old1111" in x and "abc1234" in x for x in s), s)
        self.assertTrue(any("视为 go" in x for x in s), s)   # the wording hint rides the skips stream

    def test_pre_cutoff_card_gets_hints_not_findings(self):
        card = self._card("002-b", "done", "2026-09-12", None, self.BAD_DESIGN, "- 2026-09-12 「开卡」\n")
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        self.assertEqual(f, [])
        self.assertEqual(sum(1 for x in s if x.startswith("lite-doc-form (pre-cutoff hint): doc-form/")), 10)
        self.assertIn(("grandfathered", "pre-cutoff lite card: doc-form findings shown as hints"), exs)

    def test_skill_field_alone_gates_an_older_card(self):
        card = self._card("002-b", "done", "2026-09-12", "abc1234", self.BAD_DESIGN, "- 2026-09-12 「开卡」\n")
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        self.assertEqual(len(f), 10)

    def test_lens_skip_note_satisfies_go4(self):
        design = self.GOOD_DESIGN.replace("人原话：「go」· 基线 abc", "人原话：「go」· lens: 未做（纯文档改动）· 基线 abc")
        card = self._card("001-a", "executing", "2026-09-16", "abc1234", design, "- 2026-09-16 「go」\n")
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        self.assertEqual(f, [])

    def test_prose_clause_citations_are_not_inline_clauses(self):
        design = self.GOOD_DESIGN.replace("- 验证: v", "- 验证: (a) and (b) both walked; Req-1(a) cited")
        card = self._card("001-a", "executing", "2026-09-16", "abc1234", design, "- 2026-09-16 「go」\n",
                          extra=[("notes/lens-2026-09-16.md", "x")])
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        self.assertEqual(f, [])

    def test_non_lite_card_never_runs_it_and_registry_is_lite_only(self):
        _write(self.root, "proj/003-c/requirement.md", REQ_FM % ("drafting", "ledger", "2026-09-16"))
        f, s, exs = wc.check_card_all("proj", os.path.join(self.root, "proj/003-c"), ws._L1)
        self.assertFalse([x for x in f + s if "doc-form" in x])
        self.assertNotIn("lite-doc-form", [e[0] for e in wc.card_entries(False)])
        self.assertIn("lite-doc-form", wc.LITE_CHECKS)
        self.assertIn("lite-doc-form", wc.LITE_ONLY_CHECKS)

    def test_auth_section_missing_is_a_finding_on_a_live_card(self):
        design = self.GOOD_DESIGN.split("## 授权记录")[0]
        card = self._card("001-a", "executing", "2026-09-16", "abc1234", design, "- 2026-09-16 「go」\n",
                          extra=[("notes/lens-2026-09-16.md", "x")])
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        self.assertEqual([x.split(":")[0] for x in f], ["doc-form/auth-missing"])

    def test_star_bullets_parse_in_both_files(self):
        design = self.GOOD_DESIGN.replace("- 2026-09-16 · **go**", "* 2026-09-16 · **go**") + \
            "* 2026-09-15 · **go（续）** · Req-1 · 视为 go\n"
        card = self._card("001-a", "executing", "2026-09-16", "abc1234", design, "* 2026-09-16 「go」\n",
                          extra=[("notes/lens-2026-09-16.md", "x")])
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        self.assertEqual([x.split(":")[0] for x in f], ["doc-form/go-quote"])
        self.assertFalse([x for x in s if "no `- YYYY-MM-DD" in x])

    def test_change_lines_must_be_newest_first(self):
        design = self.GOOD_DESIGN.replace("- 变更: 2026-09-16 x（人：「好」）\n",
                                          "- 变更: 2026-09-15 y（人：「好」）\n- 变更: 2026-09-16 x（人：「好」）\n")
        card = self._card("001-a", "executing", "2026-09-16", "abc1234", design, "- 2026-09-16 「go」\n",
                          extra=[("notes/lens-2026-09-16.md", "x")])
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        self.assertEqual([x.split(":")[0] for x in f], ["doc-form/change-order"])

    def test_cjk_marker_without_space_and_marker_outside_陈述(self):
        ok = self.GOOD_DESIGN.replace("  - (a) uses a lock on the spool file", "  - (a)使用锁保护 spool 文件")
        card = self._card("001-a", "executing", "2026-09-16", "abc1234", ok, "- 2026-09-16 「go」\n",
                          extra=[("notes/lens-2026-09-16.md", "x")])
        self.assertEqual(wc.check_lite_doc_form("proj", card, ws._L1)[0], [])
        bad = self.GOOD_DESIGN.replace("- 陈述:\n  lead\n  - (a) uses a lock on the spool file\n  - (b) two\n",
                                       "- 陈述: (a) uses a lock (b) two\n- 备注:\n  - (a) marker elsewhere\n")
        card = self._card("002-b", "executing", "2026-09-16", "abc1234", bad, "- 2026-09-16 「go」\n",
                          extra=[("notes/lens-2026-09-16.md", "x")])
        self.assertEqual([x.split(":")[0] for x in wc.check_lite_doc_form("proj", card, ws._L1)[0]], ["doc-form/inline-clause"])

    def test_inv_exemption_line_satisfies_doc8_and_any_status_is_judged(self):
        no_inv = self.GOOD_DESIGN.replace("### Inv-1 lock\n- 不变量: one holder\n- 归宿: Req-1\n- 检验: test\n", "")
        card = self._card("001-a", "draft", "2026-09-16", "abc1234", no_inv, "- 2026-09-16 「go」\n")
        self.assertIn("doc-form/inv-missing", [x.split(":")[0] for x in wc.check_lite_doc_form("proj", card, ws._L1)[0]])
        exempt = no_inv.replace("### 契约与不变量\n", "### 契约与不变量\n- Inv: 无（纯文本改动，无运行期契约）\n")
        card = self._card("002-b", "draft", "2026-09-16", "abc1234", exempt, "- 2026-09-16 「go」\n")
        self.assertNotIn("doc-form/inv-missing", [x.split(":")[0] for x in wc.check_lite_doc_form("proj", card, ws._L1)[0]])

    def test_prose_mention_of_go_is_not_a_go_entry(self):
        design = self.GOOD_DESIGN + "- 2026-09-16 · **补记** · 上面那条 **go** 的基线是 abc\n"
        card = self._card("001-a", "executing", "2026-09-16", "abc1234", design, "- 2026-09-16 「go」\n",
                          extra=[("notes/lens-2026-09-16.md", "x")])
        self.assertEqual(wc.check_lite_doc_form("proj", card, ws._L1)[0], [])

    def test_undated_messages_file_is_a_skip_not_silence(self):
        card = self._card("001-a", "executing", "2026-09-16", "abc1234", self.GOOD_DESIGN, "# 人话\n「go」\n",
                          extra=[("notes/lens-2026-09-16.md", "x")])
        f, s, exs = wc.check_lite_doc_form("proj", card, ws._L1)
        self.assertTrue(any("no `- YYYY-MM-DD" in x for x in s), s)

    def test_run_check_streams(self):
        self._card("001-a", "done", "2026-09-16", "abc1234", self.BAD_DESIGN, "- 2026-09-14 「开卡」\n")
        self._card("002-b", "done", "2026-09-12", None, self.BAD_DESIGN, "- 2026-09-12 「开卡」\n")
        code, out = _run(self.root, "proj/001")
        self.assertEqual(code, 1)
        self.assertIn("⚠ doc-form/go-quote", out)
        code, out = _run(self.root, "proj/002")
        self.assertEqual(code, 0)
        self.assertIn("skip: lite-doc-form (pre-cutoff hint): doc-form/go-quote", out)
