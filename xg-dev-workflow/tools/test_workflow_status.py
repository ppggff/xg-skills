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


class TraceIdCellMarkup(unittest.TestCase):
    """Emphasised / struck-through id cells are still id cells.

    A card that adds an item writes `| **R21** | …` and a retired row keeps
    `| ~~R16~~ | …`; both were invisible to the 需求条目 parser, so the trace
    matrix reported a false `not-in-需求条目` for every such row — at the very
    gate that reads the matrix to find R-ids with no design home.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_bold_and_struck_ids_are_parsed(self):
        card = make_card(self.root, "p", "096-markup")
        req = Path(card) / "requirement.md"
        req.write_text(req.read_text() + (
            "| **R21** | bold id, newly added item | 功能 | — |\n"
            "| ~~R16~~ | retired (moved to card 001) | — | — |\n"
            "| [R17] | bracketed id stays supported | 功能 | — |\n"))
        items = ws.trace_requirement(card)
        self.assertEqual(items["R21"], "bold id, newly added item")
        self.assertEqual(items["R16"], "retired (moved to card 001)")
        self.assertEqual(items["R17"], "bracketed id stays supported")


class TraceCrossCardRefs(unittest.TestCase):
    """`001 的 R34` is another card's item, not a local gap.

    Harvesting it as a local R-id invented trace rows for ids the card never had
    (a card whose items stop at R22 grew R31–R36 rows) and flagged each
    `not-in-需求条目` — noise pointed straight at the gate reader.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_cross_card_ref_makes_no_row(self):
        card = make_card(self.root, "p", "095-xcard")
        des = Path(card) / "design.md"
        des.write_text(des.read_text() + (
            "\n### 验证策略\n\n| Effect 项 | 观测点 |\n|---|---|\n"
            "| 恢复完整性（R1） | catalog 引用的数据文件全部存在，**经 001 的 R34 取得** |\n"))
        d = ws.trace_data("p", card)
        rids = [r["rid"] for r in d["rows"]]
        self.assertNotIn("R34", rids)
        self.assertIn("R1", rids)


class TraceRetiredRows(unittest.TestCase):
    """A retired item is resolved, not a gap — it gets no ⚠ flags."""

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_retired_row_has_no_gap_flags(self):
        card = make_card(self.root, "p", "094-retired")
        req = Path(card) / "requirement.md"
        req.write_text(req.read_text() +
                       "| ~~R9~~ | retired (2026-08-05: moved to card 001) | — | — |\n")
        d = ws.trace_data("p", card)
        row = next(r for r in d["rows"] if r["rid"] == "R9")
        self.assertEqual(row["flags"], [])


class ParseTasks(unittest.TestCase):
    def _parse(self, body):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "progress.md")
        open(p, "w").write(body)
        return ws.parse_tasks(p)

    def test_canonical_template_shape(self):
        rows = self._parse("## Task status\n\n| Task | Status | Notes |\n|---|---|---|\n"
                           "| T1 | done | first |\n| T2 | doing | second |\n")
        self.assertEqual([r["id"] for r in rows], ["T1", "T2"])
        self.assertEqual([r["done"] for r in rows], [True, False])
        self.assertEqual(rows[0]["notes"], "first")

    def test_postgresql_variant_part_column_checkbox_status(self):
        rows = self._parse("## Task status\n\n| Task | Part | 状态 | 备注 |\n|---|---|---|---|\n"
                           "| T0 环境+脚手架 | builder | [x] | note |\n"
                           "| T1 exec | runtime | [ ] | wip |\n")
        self.assertEqual([r["id"] for r in rows], ["T0", "T1"])
        self.assertEqual([r["done"] for r in rows], [True, False])
        self.assertEqual([r["part"] for r in rows], ["builder", "runtime"])

    def test_part_field_pinned_and_placeholder_normalized(self):
        rows = self._parse("## Task status\n\n| Task | Status | Notes |\n|---|---|---|\n"
                           "| T1 | done | first |\n")
        self.assertEqual(rows[0]["part"], "")   # no column → pinned empty
        rows = self._parse("## Task status\n\n| Task | Part | Status |\n|---|---|---|\n"
                           "| T1 | — | done |\n")
        self.assertEqual(rows[0]["part"], "")   # placeholder normalized at source

    def test_hashdata_variant_bare_numeric_id(self):
        rows = self._parse("## Task status\n\n| Task | Part | Status | Notes |\n|---|---|---|---|\n"
                           "| 1 | Catalog | done | ok |\n| 2 | Clog | PASS(manual) | ok |\n")
        self.assertEqual([r["id"] for r in rows], ["T1", "T2"])
        self.assertTrue(all(r["done"] for r in rows))

    def test_hatchdeck_variant_phase_rows_degrade_empty(self):
        rows = self._parse("## Task status\n\n| Task | Status |\n|---|---|\n"
                           "| 需求 | confirmed |\n| 设计 | frozen |\n")
        self.assertEqual(rows, [])

    def test_missing_section_or_file(self):
        self.assertEqual(self._parse("## State at a glance\n- x\n"), [])
        self.assertEqual(ws.parse_tasks("/nonexistent/progress.md"), [])

    def test_date_like_cell_is_not_a_task_id(self):
        rows = self._parse("## Task status\n\n| Task | Status |\n|---|---|\n"
                           "| 2026-07-20 | done |\n")
        self.assertEqual(rows, [])


class BoardFields(unittest.TestCase):
    def test_tasks_field_pinned_and_blockers_normalized(self):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "001-x")
        os.makedirs(card)
        open(os.path.join(root, "proj", "index.md"), "w").write("| 001 | 需求 | todo | — |\n")
        open(os.path.join(card, "progress.md"), "w").write(
            "---\nid: 001\n---\n## State at a glance\n\n- **Blockers:** 无。\n\n"
            "## Task status\n\n| Task | Status | Notes |\n|---|---|---|\n| T1 | done | ok |\n")
        cards = list(ws.iter_cards(root, ["proj"]))
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["blockers"], "")
        self.assertEqual(cards[0]["tasks"][0], {"id": "T1", "status": "done",
                                                "done": True, "notes": "ok",
                                                "part": ""})

    def test_no_progress_md_degrades_to_empty_list(self):
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "proj", "002-y"))
        open(os.path.join(root, "proj", "index.md"), "w").write("| 002 | 需求 | todo | — |\n")
        cards = list(ws.iter_cards(root, ["proj"]))
        self.assertEqual(cards[0]["tasks"], [])
        self.assertEqual(cards[0]["blockers"], "")


class DesignSections(unittest.TestCase):
    """--check (f): design.md required-section existence, grandfathered by created date."""

    FULL = ("---\nid: 014\nstatus: drafting\ncreated: 2026-08-01\n---\n\n"
            "## 思路\n\nx\n\n## 速览\n\nx\n\n## How it meets the requirement\n\nx\n\n"
            "## 影响面\n\nx\n")

    def _card(self, design):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "014-fix")
        os.makedirs(card)
        open(os.path.join(card, "design.md"), "w").write(design)
        return card

    def test_full_sections_clean(self):
        self.assertEqual(ws.check_design_sections(self._card(self.FULL)), [])

    def test_missing_sections_flagged_without_ledger(self):
        # runs through check_card even when decisions.md is absent
        card = self._card("---\nid: 014\nstatus: drafting\ncreated: 2026-08-01\n---\n\n"
                          "## 方案与否决\n\nx\n\n## 影响面\n\nx\n")
        findings = ws.check_card("proj", card)
        self.assertIn("missing-section: design.md 思路", findings)
        self.assertIn("missing-section: design.md How it meets the requirement", findings)
        self.assertNotIn("missing-section: design.md 影响面", findings)

    def test_pre_cutoff_created_is_grandfathered(self):
        card = self._card("---\nid: 006\nstatus: frozen\ncreated: 2026-07-30\n---\n\n"
                          "## 方案与否决\n\nx\n")
        self.assertEqual(ws.check_design_sections(card), [])

    def test_no_design_md_is_clean(self):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "014-fix")
        os.makedirs(card)
        self.assertEqual(ws.check_design_sections(card), [])

    def test_chinese_variant_heading_accepted(self):
        card = self._card(self.FULL.replace("## How it meets the requirement",
                                            "## 如何满足需求"))
        self.assertEqual(ws.check_design_sections(card), [])


class LedgerCheck(unittest.TestCase):
    """--check (a)-(e) against fixture cards (010 T2)."""

    GOOD_LEDGER = (
        "### R1 [requirement] approved\n"
        "- 陈述: keep it\n- why: because\n"
        "- approved: 2026-07-28 gate abc1234\n\n"
        "### R2 [requirement] proposed\n"
        "- 陈述: pending one\n- why: tbd\n- depends-on: R1\n")

    def _card(self, ledger=None, req_status="drafting", req_ids=("R1", "R2")):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "011-fix")
        os.makedirs(card)
        open(os.path.join(root, "proj", "index.md"), "w").write("| 011 | 需求 | todo | — |\n")
        rows = "\n".join(f"| {r} | stmt {r} | 功能 | 假设 |" for r in req_ids)
        open(os.path.join(card, "requirement.md"), "w").write(
            f"---\nid: 011\nstatus: {req_status}\n---\n\n## 需求条目\n\n"
            f"| ID | 需求条目 | 类型 | provenance |\n|---|---|---|---|\n{rows}\n")
        if ledger is not None:
            open(os.path.join(card, "decisions.md"), "w").write(ledger)
        return root, card

    def _findings(self, root):
        return ws.check_card("proj", os.path.join(root, "proj", "011-fix"))

    def test_no_ledger_is_legacy_and_clean(self):
        root, _ = self._card(ledger=None, req_status="confirmed")
        self.assertEqual(self._findings(root), [])

    def test_good_ledger_passes(self):
        root, _ = self._card(ledger=self.GOOD_LEDGER)
        self.assertEqual(self._findings(root), [])

    def test_empty_depends_on_line_swallows_nothing(self):
        led = ("### R1 [requirement] proposed\n"
               "- 陈述: keep it\n- why: because\n"
               "- depends-on:\n"
               "- provenance: 假设\n")
        root, _ = self._card(ledger=led, req_ids=("R1",))
        self.assertEqual(self._findings(root), [])

    def test_bad_header(self):
        root, _ = self._card(ledger="### R1 (requirement) approved\n- 陈述: x\n",
                             req_ids=())
        self.assertTrue(any(f.startswith("bad-header") for f in self._findings(root)))

    def test_dup_active(self):
        dup = ("### R1 [requirement] proposed\n- 陈述: a\n\n"
               "### R1 [requirement] approved\n- 陈述: b\n"
               "- approved: 2026-07-28 gate abc1234\n")
        root, _ = self._card(ledger=dup, req_ids=("R1",))
        self.assertIn("dup-active: R1", self._findings(root))

    def test_dangling_id(self):
        one = ("### R1 [requirement] approved\n- 陈述: a\n"
               "- approved: 2026-07-28 gate abc1234\n")
        root, _ = self._card(ledger=one, req_ids=("R1", "R2"))
        self.assertIn("dangling-id: R2", self._findings(root))

    def test_superseded_ref(self):
        sup = "### R1 [requirement] superseded\n- 陈述: old\n"
        root, _ = self._card(ledger=sup, req_ids=("R1",))
        self.assertIn("superseded-ref: R1", self._findings(root))

    def test_status_mismatch_confirmed_with_pending(self):
        root, _ = self._card(ledger=self.GOOD_LEDGER, req_status="confirmed")
        self.assertTrue(any(f.startswith("status-mismatch: requirement.md")
                            for f in self._findings(root)))

    def test_level_without_blocks_falls_back(self):
        # design.md frozen + ledger has only requirement blocks → no design-level check
        approved = ("### R1 [requirement] approved\n- 陈述: a\n"
                    "- approved: 2026-07-28 gate abc1234\n")
        root, card = self._card(ledger=approved, req_status="confirmed", req_ids=("R1",))
        open(os.path.join(card, "design.md"), "w").write(
            "---\nid: 011\nstatus: frozen\n---\n\n## How it meets\n\n| R-id | 归属 |\n"
            "|---|---|\n| R1 | 模块 X |\n")
        self.assertEqual(self._findings(root), [])

    def test_dep_cycle(self):
        cyc = ("### R1 [requirement] proposed\n- 陈述: a\n- depends-on: R2\n\n"
               "### R2 [requirement] proposed\n- 陈述: b\n- depends-on: R1\n")
        root, _ = self._card(ledger=cyc)
        self.assertTrue(any(f.startswith("dep-cycle") for f in self._findings(root)))

    def test_bad_approve_note(self):
        noteless = "### R1 [requirement] approved\n- 陈述: a\n- why: b\n"
        root, _ = self._card(ledger=noteless, req_ids=("R1",))
        self.assertIn("bad-approve-note: R1", self._findings(root))

    def test_adr_status_mismatch(self):
        led = ("### R1 [requirement] approved\n- 陈述: a\n"
               "- approved: 2026-07-28 gate abc1234\n\n"
               "### ADR-0001 D1 [design] proposed\n- 陈述: d\n")
        root, card = self._card(ledger=led, req_ids=("R1",))
        os.makedirs(os.path.join(card, "adr"))
        open(os.path.join(card, "adr", "0001-x.md"), "w").write(
            "# ADR-0001: x\n\nStatus: accepted\n")
        self.assertTrue(any("0001-x.md accepted vs pending" in f
                            for f in self._findings(root)))

    def test_run_check_exit_codes_and_error_capture(self):
        root, _ = self._card(ledger=self.GOOD_LEDGER)
        self.assertEqual(ws.run_check(root, "proj/011"), 0)
        root2, _ = self._card(ledger="### R1 [requirement] approved\n- 陈述: a\n",
                              req_ids=("R1",))
        self.assertEqual(ws.run_check(root2, "proj/011"), 1)
        orig = ws.check_card
        ws.check_card = lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            self.assertEqual(ws.run_check(root, "proj/011"), 1)  # check-error → nonzero
        finally:
            ws.check_card = orig

    def test_card_status_pending_overlay_and_board_decisions(self):
        root, card = self._card(ledger=self.GOOD_LEDGER)
        steps, _, nxt = ws.card_status(card)
        self.assertIn("需求:drafting·待评审(1)", steps[0])
        self.assertEqual(nxt, "GATE: 需求 1 决策待批")
        cards = list(ws.iter_cards(root, ["proj"]))
        self.assertEqual([d["id"] for d in cards[0]["decisions"]], ["R1", "R2"])
        self.assertEqual(cards[0]["decisions"][0]["state"], "approved")
        self.assertEqual(cards[0]["decisions"][1]["text"], "pending one")

    def test_card_status_without_ledger_unchanged(self):
        root, card = self._card(ledger=None, req_status="confirmed")
        steps, _, _ = ws.card_status(card)
        self.assertEqual(steps[0], "需求:confirmed")
        self.assertEqual(list(ws.iter_cards(root, ["proj"]))[0]["decisions"], [])

    def test_trace_rows_carry_dstate(self):
        root, card = self._card(ledger=self.GOOD_LEDGER)
        d = ws.trace_data("proj", card)
        by = {r["rid"]: r for r in d["rows"]}
        self.assertEqual(by["R1"]["dstate"], "approved")
        self.assertEqual(by["R2"]["dstate"], "proposed")

    def test_detail_baseline_mapping_and_s_ids(self):
        # derived-status detail mapping + S<n> blocks (baseline force lives in process; the tool
        # checks the status mapping and level aggregation)
        led = ("### S1 [detail] approved\n- 陈述: concrete pick\n"
               "- approved: 2026-07-28 gate abc1234\n")
        root, card = self._card(ledger=led, req_ids=())
        open(os.path.join(card, "detail.md"), "w").write(
            "---\nid: 011\nstatus: draft\n---\n\n## 可追溯\n\n| 详设项 | design | R-id |\n"
            "|---|---|---|\n| S1 | 模块 X | R1 |\n")
        fs = self._findings(root)
        self.assertTrue(any("status-mismatch: detail.md 'draft'" in f for f in fs))
        open(os.path.join(card, "detail.md"), "w").write(
            "---\nid: 011\nstatus: baseline\n---\n\n## 可追溯\n\n| 详设项 | design | R-id |\n"
            "|---|---|---|\n| S1 | 模块 X | R1 |\n")
        self.assertEqual(self._findings(root), [])
        steps, _, _ = ws.card_status(card)
        self.assertIn("详设:baseline", steps[2])

    def test_design_ledger_view_regeneration_id_set(self):
        # R7 mechanical half: every design-cited id must be reconstructible from the
        # ledger — --check (a) dangling-id is exactly that set comparison.
        led = "### R1 [requirement] proposed\n- 陈述: a\n"
        root, card = self._card(ledger=led, req_ids=("R1",))
        open(os.path.join(card, "design.md"), "w").write(
            "---\nid: 011\nstatus: drafting\n---\n\n## How it meets\n\n| R-id | 归属 |\n"
            "|---|---|\n| R1 | 模块 X |\n| R9 | 幽灵 |\n")
        self.assertIn("dangling-id: R9", self._findings(root))

    def test_prose_cell_mention_is_not_a_reference(self):
        # review #A1: "S3" in a free-text 可追溯 cell must not become a dangling-id
        led = ("### S1 [detail] approved\n- 陈述: pick\n"
               "- approved: 2026-07-28 gate abc1234\n")
        root, card = self._card(ledger=led, req_ids=())
        open(os.path.join(card, "detail.md"), "w").write(
            "---\nid: 011\nstatus: baseline\n---\n\n## 可追溯\n\n| 详设项 | design | R-id |\n"
            "|---|---|---|\n| S1 | 落 S3 归档桶 | — |\n")
        self.assertEqual(self._findings(root), [])

    def test_dup_active_display_is_neutral(self):
        # review #B1: display never picks a winner for a dup-active id
        dup = ("### R1 [requirement] proposed\n- 陈述: a\n\n"
               "### R1 [requirement] approved\n- 陈述: b\n"
               "- approved: 2026-07-28 gate abc1234\n")
        root, card = self._card(ledger=dup, req_ids=("R1",))
        decs = ws.card_decisions(card)
        self.assertEqual(len(decs), 1)
        self.assertEqual(decs[0]["state"], "conflict")
        self.assertEqual(decs[0]["text"], "")

    def test_adr_dead_status_vs_active_rows(self):
        # review #A4: Status: deprecated/superseded while ledger rows stay active
        led = ("### ADR-0001 D1 [design] approved\n- 陈述: d\n"
               "- approved: 2026-07-28 gate abc1234\n")
        root, card = self._card(ledger=led, req_ids=())
        os.makedirs(os.path.join(card, "adr"))
        open(os.path.join(card, "adr", "0001-x.md"), "w").write(
            "# ADR-0001: x\n\nStatus: deprecated\n")
        self.assertTrue(any("deprecated vs active rows" in f for f in self._findings(root)))

    def test_composite_adr_id_parses(self):
        led = ("### ADR-0001 D2 [design] approved\n- 陈述: d\n"
               "- approved: 2026-07-28 gate abc1234\n")
        root, _ = self._card(ledger=led, req_ids=())
        blocks, findings = ws.parse_ledger(os.path.join(root, "proj", "011-fix"))
        self.assertEqual(findings, [])
        self.assertEqual(blocks[0]["id"], "ADR-0001 D2")
        self.assertEqual(ws.ledger_status(blocks)["design"]["approved"], 1)


class FactMarkerCheck(unittest.TestCase):
    """--check (g): facts.md marker↔来源 integrity, plus the calibration that keeps the
    correcting idiom ("this VERIFIED fact supersedes an earlier 推断") from firing."""

    def _card(self, facts):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "012-facts")
        os.makedirs(card)
        open(os.path.join(card, "facts.md"), "w").write(facts)
        return card

    def test_flags_self_attributed_inference(self):
        card = self._card(
            "### F6 [VERIFIED]\n- 事实: extra args cannot drop the flag\n"
            "- 来源: 由 [F1] + [F5] 的参数拼接位置推断（仍未实测）\n")
        self.assertTrue(any("F6" in f for f in ws.check_fact_markers(card)))

    def test_accepts_measured_fact(self):
        card = self._card(
            "### F7 [VERIFIED]\n- 事实: the names are hardcoded\n"
            "- 来源: `minio_reset()` in `cb3x`（本轮实测确认）\n")
        self.assertEqual(ws.check_fact_markers(card), [])

    def test_correcting_idiom_is_not_a_finding(self):
        """A VERIFIED block may say it supersedes an earlier 推断 — three real cards did."""
        card = self._card(
            "### F7 [VERIFIED]\n- 事实: the read chain is X\n"
            "- 来源: `steps/resume.md` step 3（已核原文；取代早前推断级 F7）\n\n"
            "### F14 [VERIFIED]\n- 事实: build311 suffices\n"
            "- 来源: 容器内实测 —— go build 通过\n"
            "- 说明: 修正了 design 里那条**推断**\n")
        self.assertEqual(ws.check_fact_markers(card), [])

    def test_superseded_block_is_exempt(self):
        card = self._card(
            "### F21 [superseded 2026-07-31 → F22]\n- 事实（已被证伪）: data lives in S3\n"
            "- 来源: 由两个事实的组合推断，未实测\n")
        self.assertEqual(ws.check_fact_markers(card), [])

    def test_inferred_marker_never_flagged(self):
        card = self._card(
            "### F2 [推断]\n- 事实: probably X\n- 来源: 由 F1 推断，未实测\n")
        self.assertEqual(ws.check_fact_markers(card), [])

    def test_no_facts_file(self):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "013-none")
        os.makedirs(card)
        self.assertEqual(ws.check_fact_markers(card), [])


NEW_PARTS_DESIGN = """## Chosen approach

body text

### Decomposition / Parts (optional)

| Part | 含哪些 module | R | seam |
|------|--------------|---|------|
| **观测** | mod-a, mod-b | R1, R3 | 候选值语义 |
| 推进 | mod-c | R3 | — |

### Design qualities

- text after the table
"""

LEGACY_PARTS_DESIGN = """## Chosen approach

### Decomposition / Parts(卡内 part 化,组件轴;用户 2026-07-24)

| Part | 内容 | 性质 / R | seam 契约 |
|------|------|---------|-----------|
| **P1 catalog 侧移植** | handlers | 使能;支撑 R3/R4 | RPC 语义 |
| **P4 工具功能** | tool | **交付价值** R1~R5 | 候选值 |
"""


class TracePlanPart(unittest.TestCase):
    """trace_plan(): the task `Part:` field — parsed, placeholder-normalized, pinned."""

    def _plan(self, body):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "022-plan")
        os.makedirs(card)
        open(os.path.join(card, "plan.md"), "w").write(body)
        return ws.trace_plan(card)

    def test_part_parsed_and_normalized(self):
        tasks = self._plan("### T1: one\n- **Implements:** R1\n- **Part:** 观测\n"
                           "- **Acceptance:**\n  - [x] ok\n"
                           "### T2: two\n- **Part:** —\n  - [ ] pending\n"
                           "### T3: three\n  - [ ] pending\n"
                           "### T4: four\n- **Part:** **观测**\n  - [ ] wip\n")
        self.assertEqual(tasks["1"]["part"], "观测")
        self.assertEqual(tasks["2"]["part"], "")   # placeholder → ""
        self.assertEqual(tasks["3"]["part"], "")   # absent → pinned empty
        self.assertEqual(tasks["4"]["part"], "观测")   # markup stripped (015 review #1)


class TraceParts(unittest.TestCase):
    """trace_parts(): Parts-table parsing — the R column is the new-format marker
    (no R column → legacy → treated as un-split, ADR-0001 D4/D9)."""

    def _card(self, design):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "020-parts")
        os.makedirs(card)
        open(os.path.join(card, "design.md"), "w").write(design)
        return card

    def test_new_format_parses_order_and_multival(self):
        parts, r2p = ws.trace_parts(self._card(NEW_PARTS_DESIGN))
        self.assertEqual(parts, ["观测", "推进"])
        self.assertEqual(r2p["R1"], ["观测"])
        self.assertEqual(r2p["R3"], ["观测", "推进"])  # multi-part R (005 evidence)

    def test_legacy_table_without_R_column_is_unsplit(self):
        parts, r2p = ws.trace_parts(self._card(LEGACY_PARTS_DESIGN))
        self.assertEqual(parts, [])
        self.assertEqual(r2p, {})

    def test_no_parts_section(self):
        parts, r2p = ws.trace_parts(self._card("## Chosen approach\n\ntext\n"))
        self.assertEqual((parts, r2p), ([], {}))
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "021-nodesign")
        os.makedirs(card)
        self.assertEqual(ws.trace_parts(card), ([], {}))

    def test_terminator_stops_at_next_h2(self):
        # Parts is the LAST ### inside its ## section; a naive ^###\s terminator
        # would swallow the following ## section's table rows.
        design = ("## Chosen approach\n\n### Decomposition / Parts\n\n"
                  "| Part | R |\n|---|---|\n| alpha | R1 |\n\n"
                  "## 影响面\n\n| Part | R |\n|---|---|\n| ghost | R9 |\n")
        parts, r2p = ws.trace_parts(self._card(design))
        self.assertEqual(parts, ["alpha"])
        self.assertNotIn("R9", r2p)


class TraceDataParts(unittest.TestCase):
    """trace_data(): part axis fields are pinned (always present); grouping data
    comes from design (R→parts, freeze-ready) + plan (task part)."""

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def _parts_card(self, with_plan=True):
        card = os.path.join(self.root, "p", "030-split")
        os.makedirs(card)
        write = lambda name, text: open(os.path.join(card, name), "w").write(text)
        write("requirement.md", "## 需求条目\n\n| ID | 条目 | 类型 |\n|---|---|---|\n"
              "| R1 | first | 功能 |\n| R3 | third | 功能 |\n")
        write("design.md", NEW_PARTS_DESIGN +
              "\n## How it meets the requirement\n\n| R-id | home |\n|---|---|\n"
              "| [R1](./requirement.md) | mod-a |\n| [R3](./requirement.md) | mod-c |\n")
        if with_plan:
            write("plan.md", "### T1: one\n- **Implements:** [R1](./requirement.md)\n"
                  "- **Part:** 观测\n- **Acceptance:**\n  - [x] ok\n\n"
                  "### T2: two\n- **Implements:** [R3](./requirement.md)\n"
                  "- **Part:** 推进\n- **Acceptance:**\n  - [ ] wip\n")
        return card

    def test_pinned_empty_on_unsplit_card(self):
        card = make_card(self.root, "p", "099-fix")
        d = ws.trace_data("p", card)
        self.assertEqual(d["parts"], [])
        self.assertTrue(all(r["parts"] == [] for r in d["rows"]))
        self.assertTrue(all(t["part"] == "" for r in d["rows"] for t in r["tasks"]))

    def test_parts_populated_from_design_and_plan(self):
        d = ws.trace_data("p", self._parts_card())
        self.assertEqual(d["parts"], ["观测", "推进"])
        r1 = next(r for r in d["rows"] if r["rid"] == "R1")
        r3 = next(r for r in d["rows"] if r["rid"] == "R3")
        self.assertEqual(r1["parts"], ["观测"])
        self.assertEqual(r3["parts"], ["观测", "推进"])
        self.assertEqual(r1["tasks"][0]["part"], "观测")

    def test_freeze_scenario_no_plan(self):
        d = ws.trace_data("p", self._parts_card(with_plan=False))
        self.assertEqual(d["parts"], ["观测", "推进"])
        r3 = next(r for r in d["rows"] if r["rid"] == "R3")
        self.assertEqual(r3["parts"], ["观测", "推进"])

    def _render(self, card):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ws.render_trace("p", card)
        return buf.getvalue()

    def test_render_groups_by_part(self):
        out = self._render(self._parts_card())
        self.assertIn("Part: 观测", out)
        self.assertIn("Part: 推进", out)
        self.assertIn("↔", out)   # multi-part R3 marked in each group
        self.assertLess(out.index("Part: 观测"), out.index("Part: 推进"))

    def test_render_unsplit_has_no_part_lines(self):
        out = self._render(make_card(self.root, "p", "098-plain"))
        self.assertNotIn("Part:", out)
        self.assertNotIn("↔", out)


class VPrefixLedger(unittest.TestCase):
    """V<n> (shared verification-criteria definitions) are requirement-level ledger
    rows — reference checks must fire on requirement-only cards (015 review #2)."""

    def _card(self, decisions):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "032-vpfx")
        os.makedirs(card)
        open(os.path.join(card, "decisions.md"), "w").write(decisions)
        return card

    def test_superseded_v_ref_flagged_on_requirement_only_card(self):
        card = self._card(
            "### V1 [requirement] superseded\n- 陈述: old snapshot definition\n\n"
            "### R1 [requirement] proposed\n- 陈述: x\n- depends-on: V1\n")
        self.assertTrue(any("superseded-ref: V1" in f for f in ws.check_card("proj", card)))

    def test_dangling_v_ref_flagged(self):
        card = self._card("### R1 [requirement] proposed\n- 陈述: x\n- depends-on: V9\n")
        self.assertTrue(any("dangling-id: V9" in f for f in ws.check_card("proj", card)))

    def test_placeholder_depends_on_ignored(self):
        # retro 2026-08-04: "- depends-on: —" placeholders flagged as dangling ids
        # twice during card 015 — normalize at the parser like every other field.
        blocks, _ = ws.parse_ledger(self._card(
            "### R1 [requirement] proposed\n- 陈述: x\n- depends-on: —\n"))
        self.assertEqual(blocks[0]["deps"], [])

    def test_v_header_parses(self):
        blocks, findings = ws.parse_ledger(self._card(
            "### V2 [requirement] proposed\n- 陈述: tsum definition\n"))
        self.assertEqual(findings, [])
        self.assertEqual(blocks[0]["id"], "V2")


class PartConsistency(unittest.TestCase):
    """--check (h): plan `Part:` values ⊆ canonical part names — active only with a
    new-format Parts table; legacy/un-split cards skip. Runs in the section_findings
    group (a card without decisions.md is still checked)."""

    def _card(self, design, plan):
        root = tempfile.mkdtemp()
        card = os.path.join(root, "proj", "031-check")
        os.makedirs(card)
        open(os.path.join(card, "design.md"), "w").write(design)
        open(os.path.join(card, "plan.md"), "w").write(plan)
        return card

    BAD_PLAN = ("### T1: one\n- **Part:** 观测\n  - [x] ok\n"
                "### T2: two\n- **Part:** 觀測\n  - [ ] typo\n")

    def test_bad_value_named(self):
        card = self._card(NEW_PARTS_DESIGN, self.BAD_PLAN)
        findings = ws.check_part_consistency(card)
        self.assertEqual(len(findings), 1)
        self.assertIn("T2", findings[0])
        self.assertIn("觀測", findings[0])

    def test_legacy_and_unsplit_skip(self):
        card = self._card(LEGACY_PARTS_DESIGN, self.BAD_PLAN)
        self.assertEqual(ws.check_part_consistency(card), [])
        card = self._card("## Chosen approach\n", self.BAD_PLAN)
        self.assertEqual(ws.check_part_consistency(card), [])

    def test_placeholder_part_not_flagged(self):
        plan = "### T1: one\n- **Part:** —\n  - [x] ok\n"
        card = self._card(NEW_PARTS_DESIGN, plan)
        self.assertEqual(ws.check_part_consistency(card), [])

    def test_bold_part_value_matches_design(self):
        # 015 review #1: design cells are conventionally bold — a plan author copying
        # that style must not trip a false part-mismatch.
        plan = "### T1: one\n- **Part:** **观测**\n  - [x] ok\n"
        card = self._card(NEW_PARTS_DESIGN, plan)
        self.assertEqual(ws.check_part_consistency(card), [])

    def test_placeholder_part_cell_not_registered(self):
        design = NEW_PARTS_DESIGN.replace("| 推进 | mod-c | R3 | — |",
                                          "| TBD | mod-c | R3 | — |")
        parts, _ = ws.trace_parts(self._card(design, ""))
        self.assertEqual(parts, ["观测"])   # TBD cell is a placeholder, not a part

    def test_runs_without_ledger_via_check_card(self):
        card = self._card(NEW_PARTS_DESIGN, self.BAD_PLAN)   # no decisions.md
        self.assertTrue(any("part-mismatch" in f for f in ws.check_card("proj", card)))

    def test_parts_R_column_feeds_referenced_ids(self):
        design = NEW_PARTS_DESIGN.replace("R1, R3", "R1, R99")
        card = self._card(design, "### T1: one\n- **Part:** 观测\n  - [x] ok\n")
        self.assertIn("R99", ws._referenced_ids(card))


if __name__ == "__main__":
    unittest.main(verbosity=1)
