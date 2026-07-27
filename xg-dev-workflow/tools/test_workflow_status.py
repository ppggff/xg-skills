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
                                                "done": True, "notes": "ok"})

    def test_no_progress_md_degrades_to_empty_list(self):
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "proj", "002-y"))
        open(os.path.join(root, "proj", "index.md"), "w").write("| 002 | 需求 | todo | — |\n")
        cards = list(ws.iter_cards(root, ["proj"]))
        self.assertEqual(cards[0]["tasks"], [])
        self.assertEqual(cards[0]["blockers"], "")


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
        # R12 detail mapping + S<n> blocks (baseline force lives in process; the tool
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

    def test_composite_adr_id_parses(self):
        led = ("### ADR-0001 D2 [design] approved\n- 陈述: d\n"
               "- approved: 2026-07-28 gate abc1234\n")
        root, _ = self._card(ledger=led, req_ids=())
        blocks, findings = ws.parse_ledger(os.path.join(root, "proj", "011-fix"))
        self.assertEqual(findings, [])
        self.assertEqual(blocks[0]["id"], "ADR-0001 D2")
        self.assertEqual(ws.ledger_status(blocks)["design"]["approved"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
