#!/usr/bin/env python3
"""Unit tests for block_parse.py (026) — stdlib unittest, synthetic fixtures only.

Run: python3 tools/test_block_parse.py (or via unittest discover from tools/).
Golden grammar coverage (all five annotation kinds, fields, clauses,
continuation), the error-matrix negatives (bad-header, duplicate id, bad
annotations, cross-doc collision, missing requirement.md), deps_graph cycles,
and the ledger-parse/block-parse semantic-equivalence assertion (design risk
F-24: same decision in both carriers parses to the same semantics).
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

import block_parse as bp

TOOLS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("workflow_status",
                                               str(TOOLS / "workflow-status.py"))
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)

GOLDEN = """\
## 需求条目

### Req-1 approved — 样例决策
- 陈述: 主句内容
  - (a) 嵌套子弹属陈述载荷
- 类型: 功能
- why: 理由一句
- provenance: 来源锚
- depends-on: Req-2
- (a) 顶层子句甲
- (b) 顶层子句乙
- 附注: 容忍的说明行
- 来源: 025 R1 approved 2026-08-20 gate 13fed19 — verbatim
- approved: 2026-08-25 gate a01291a (batch: 「其他照案」)
- approved: 2026-08-26 gate db14047 (single G22: 「原话」)
- 变更: 改了半句 (M2 1f14702, 2026-08-25)
- 退役: 整块退役理由 (M2 deadbeef, 2026-08-26 说明)
- 澄清: 词形按定稿读 (receipt 16c3dfd, 2026-08-26 追认)

### Req-2 proposed — 依赖目标
- 陈述: 无依赖
- 类型: 约束
- why: w
- provenance: p
- depends-on: 无
"""


class ParseGolden(unittest.TestCase):
    def setUp(self):
        self.blocks, self.findings = bp.parse_doc_blocks(GOLDEN, doc="requirement.md")

    def test_clean_parse_no_findings(self):
        self.assertEqual(self.findings, [])
        self.assertEqual(len(self.blocks), 2)

    def test_head_fields(self):
        b = self.blocks[0]
        self.assertEqual((b["prefix"], b["num"], b["state"], b["title"]),
                         ("Req", "1", "approved", "样例决策"))
        self.assertEqual(b["doc"], "requirement.md")
        self.assertEqual(sorted(b["fields"]),
                         ["depends-on", "provenance", "why", "类型", "陈述"])

    def test_continuation_joins_open_field(self):
        self.assertIn("嵌套子弹属陈述载荷", self.blocks[0]["fields"]["陈述"])

    def test_clauses_and_extras(self):
        b = self.blocks[0]
        self.assertEqual([c[0] for c in b["clauses"]], ["a", "b"])
        self.assertTrue(any("附注" in x for x in b["extras"]))

    def test_all_five_annotation_kinds(self):
        kinds = [a["kind"] for a in self.blocks[0]["annotations"]]
        self.assertEqual(kinds, ["来源", "approved", "approved", "变更", "退役", "澄清"])

    def test_approved_extra_slots(self):
        a1, a2 = [a for a in self.blocks[0]["annotations"] if a["kind"] == "approved"]
        self.assertEqual((a1["extra"]["mode"], a1["extra"]["ask_id"]), ("batch", None))
        self.assertEqual((a2["extra"]["mode"], a2["extra"]["ask_id"],
                          a2["extra"]["verbatim"]), ("single", "G22", "原话"))
        self.assertEqual(a1["extra"]["hash"], "a01291a")

    def test_change_retire_clarify_source_extras(self):
        by = {a["kind"]: a for a in self.blocks[0]["annotations"]}
        self.assertEqual(by["变更"]["extra"]["hash"], "1f14702")
        self.assertEqual(by["退役"]["extra"]["尾注"], "2026-08-26 说明")
        self.assertIn("receipt 16c3dfd", by["澄清"]["extra"]["凭据"])
        self.assertEqual(by["来源"]["extra"], {"源卡": "025", "源id": "R1"})


class ErrorMatrix(unittest.TestCase):
    def test_bad_header_near_miss_must_report(self):
        for bad in ("### Req-3 batch — 未知状态词", "### REQ-3 approved — case 错",
                    "### Foo-1 approved — 未知前缀"):
            _, findings = bp.parse_doc_blocks(bad + "\n- 陈述: x\n")
            self.assertTrue(any(f.startswith("bad-header") for f in findings), bad)

    def test_duplicate_id_first_wins(self):
        text = GOLDEN + "\n### Req-1 proposed — 撞名\n- 陈述: 后来者\n"
        blocks, findings = bp.parse_doc_blocks(text)
        self.assertTrue(any(f.startswith("duplicate-id: Req-1") for f in findings))
        self.assertEqual(len(blocks), 3)  # 解析继续

    def test_duplicate_field(self):
        text = "### Req-9 approved — d\n- 陈述: 一\n- 陈述: 二\n"
        _, findings = bp.parse_doc_blocks(text)
        self.assertTrue(any(f.startswith("duplicate-field: Req-9") for f in findings))

    def test_bad_annotation_each_kind(self):
        cases = (
            "- approved: 2026-08-25 gate ZZZ (batch: 「话」)",     # 坏 hash
            "- approved: 2026-08-25 gate a01291a (both: 「话」)",  # 坏 mode
            "- 变更: 缺尾注 (M2 1f14702)",
            "- 退役: 缺括注",
            "- 澄清: 无凭据槽（语义不变）",
            "- 来源: 024 T3 approved — verbatim",                  # 非 (c4) 形
        )
        for line in cases:
            text = "### Req-8 approved — t\n- 陈述: x\n%s\n" % line
            _, findings = bp.parse_doc_blocks(text)
            self.assertTrue(any(f.startswith("bad-annotation: Req-8") for f in findings),
                            line)

    def test_annotation_state_word_set_closed(self):
        # superseded/retired remain legal state words on the header
        text = "### HLD-4 superseded — s\n- 陈述: x\n"
        blocks, findings = bp.parse_doc_blocks(text)
        self.assertEqual(findings, [])
        self.assertEqual(blocks[0]["state"], "superseded")


class CardBlocks(unittest.TestCase):
    def _card(self, files):
        d = tempfile.mkdtemp()
        for name, text in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(text)
        return d

    def test_missing_requirement_is_a_finding(self):
        d = self._card({})
        blocks, findings = bp.card_blocks(d)
        self.assertEqual(len(blocks), 0)
        self.assertIn("doc-missing: requirement.md", findings)

    def test_cross_doc_collision_first_wins(self):
        d = self._card({
            "requirement.md": "### Req-1 approved — 甲\n- 陈述: 家在需求\n",
            "design.md": "### Req-1 approved — 乙\n- 陈述: 撞名\n"
                         "\n### HLD-1 approved — 丙\n- 陈述: 正常\n",
        })
        blocks, findings = bp.card_blocks(d)
        self.assertEqual(blocks["Req-1"]["title"], "甲")
        self.assertIn("HLD-1", blocks)
        self.assertTrue(any(f.startswith("duplicate-id-cross-doc: Req-1") for f in findings))

    def test_doc_order_requirement_design_detail(self):
        d = self._card({
            "requirement.md": "### Req-1 approved — a\n- 陈述: x\n",
            "design.md": "### HLD-1 approved — b\n- 陈述: x\n",
            "detail.md": "### LLD-1 approved — c\n- 陈述: x\n",
        })
        blocks, _ = bp.card_blocks(d)
        self.assertEqual(list(blocks), ["Req-1", "HLD-1", "LLD-1"])


class DepsGraph(unittest.TestCase):
    def test_cycle_detected(self):
        text = ("### Req-1 approved — a\n- 陈述: x\n- depends-on: Req-2\n"
                "\n### Req-2 approved — b\n- 陈述: x\n- depends-on: Req-1\n")
        blocks, _ = bp.parse_doc_blocks(text)
        _, cycles = bp.deps_graph(blocks)
        self.assertTrue(cycles)

    def test_dangling_visible_as_missing_node(self):
        # 悬空 dep 不在 parse 层定罪（Part A 025 域名合法留至归一），但消费方可见
        text = "### Req-1 approved — a\n- 陈述: x\n- depends-on: R21\n"
        blocks, findings = bp.parse_doc_blocks(text)
        edges, cycles = bp.deps_graph(blocks)
        self.assertEqual(findings, [])
        self.assertIn("R21", edges["Req-1"])
        self.assertNotIn("R21", edges)

    def test_placeholder_deps_dropped(self):
        text = "### Req-1 approved — a\n- 陈述: x\n- depends-on: 无\n"
        blocks, _ = bp.parse_doc_blocks(text)
        edges, _ = bp.deps_graph(blocks)
        self.assertEqual(edges["Req-1"], [])


class ExpandRanges(unittest.TestCase):
    def test_range_and_singles(self):
        self.assertEqual(bp.expand_ranges("Req-1..Req-3, HLD-2"),
                         ["Req-1", "Req-2", "Req-3", "HLD-2"])


class LedgerEquivalence(unittest.TestCase):
    """F-24: the same decision carried as a ledger row and as a doc-native block
    parses to the same semantics (id number, state, deps) — independently
    written parsers, asserted equal on the shared semantic core."""

    def test_same_decision_both_carriers(self):
        ledger = ("### R7 [requirement] approved\n"
                  "- 陈述: 同一决策\n- depends-on: R2, R3\n")
        block = ("### Req-7 approved — 同一决策\n"
                 "- 陈述: 同一决策\n- depends-on: Req-2, Req-3\n")
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "decisions.md"), "w", encoding="utf-8") as f:
            f.write(ledger)
        lrows, lfind = ws.parse_ledger(d)
        brows, bfind = bp.parse_doc_blocks(block)
        self.assertEqual((lfind, bfind), ([], []))
        lr, br = lrows[0], brows[0]
        self.assertEqual(lr["id"].lstrip("R"), br["num"])
        self.assertEqual(lr["state"], br["state"])
        self.assertEqual([x.lstrip("R") for x in lr["deps"]],
                         [x.split("-")[1] for x in
                          br["fields"]["depends-on"].split(", ")])

    def test_bad_header_finding_shape_matches_ledger_precedent(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "decisions.md"), "w", encoding="utf-8") as f:
            f.write("### R1 [requirement] frozen\n- 陈述: x\n")
        _, lfind = ws.parse_ledger(d)
        _, bfind = bp.parse_doc_blocks("### Req-1 frozen — 坏状态词\n- 陈述: x\n")
        self.assertTrue(lfind and lfind[0].startswith("bad-header"))
        self.assertTrue(bfind and bfind[0].startswith("bad-header"))


class RenderIndex(unittest.TestCase):
    def test_requirement_scope_shape(self):
        blocks, _ = bp.parse_doc_blocks(GOLDEN, doc="requirement.md")
        out = ws.render_index(blocks)
        self.assertTrue(out.startswith(ws.INDEX_BEGIN) and out.endswith(ws.INDEX_END))
        self.assertIn("| Req-1 | 样例决策 | approved |", out)

    def test_scope_filters_other_docs(self):
        blocks, _ = bp.parse_doc_blocks(
            "### HLD-1 approved — 设计块\n- 陈述: x\n", doc="design.md")
        out = ws.render_index(blocks, scope="requirement")
        self.assertNotIn("HLD-1", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
