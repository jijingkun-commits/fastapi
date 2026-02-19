"""问数澄清护栏与多轮补充继承测试。"""

import json
import sys
import types
import unittest
from unittest.mock import patch

from langchain_core.messages import HumanMessage


# 说明：本用例只验证 analyze_data_intent 的澄清/继承逻辑，不依赖 vanna。
# 为避免测试环境缺少 vanna 依赖导致模块导入失败，注入轻量 semantic 桩。
if "app.ai.semantic" not in sys.modules:
    semantic_stub = types.ModuleType("app.ai.semantic")

    def _stub_get_vanna():
        raise RuntimeError("test stub: get_vanna should not be called in analyze_data_intent tests")

    semantic_stub.get_vanna = _stub_get_vanna
    sys.modules["app.ai.semantic"] = semantic_stub

from app.ai.workflow.data_graph import analyze_data_intent


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, payload: dict):
        self.payload = payload

    def invoke(self, _prompt: str):
        return _FakeResponse(json.dumps(self.payload, ensure_ascii=False))


class TestDataGraphClarifyGuard(unittest.TestCase):
    """覆盖“重复追问/补充继承”关键回归场景。"""

    def _invoke(self, user_text: str, llm_payload: dict, **state_overrides):
        state = {
            "messages": [HumanMessage(content=user_text)],
            **state_overrides,
        }
        with patch(
            "app.ai.workflow.data_graph.get_scene_llm", return_value=_FakeLLM(llm_payload)
        ):
            return analyze_data_intent(state)

    def test_first_round_can_only_clarify_display_mode(self):
        """首轮已识别指标+时间时，可只追问展示方式。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "贷款余额",
            "time_range": "2025-06-30",
            "filters": [],
            "dimensions": ["机构"],
            "chart_type": "",
            "clarification_needed": "你想看明细、占比还是图表？",
        }

        result = self._invoke("查询2025-06-30各机构贷款余额分布", llm_payload)

        self.assertEqual(result.get("matched_metric"), "贷款余额")
        self.assertEqual(result.get("time_range"), "2025-06-30")
        self.assertIsNotNone(result.get("clarification_needed"))
        self.assertIn("图表", result.get("clarification_needed"))
        self.assertNotIn("时间范围", result.get("clarification_needed"))

    def test_reply_tubiao_should_not_reask_metric_and_time(self):
        """次轮仅回复“图标”时，不应再追问指标+时间。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "",
            "time_range": "",
            "filters": [],
            "dimensions": [],
            "chart_type": "",
            "clarification_needed": "你想看哪一个指标以及时间范围？",
        }

        result = self._invoke(
            "图标",
            llm_payload,
            matched_metric="贷款余额",
            time_range="2025-06-30",
            dimensions=["机构"],
            last_clarify_slot="display_mode",
            clarify_count=1,
            pending_handoff={
                "target_agent": "data_expert",
                "task_description": "在2025-06-30各机构贷款余额分布基础上，按图表展示。",
            },
        )

        self.assertIsNone(result.get("clarification_needed"))
        self.assertEqual(result.get("matched_metric"), "贷款余额")
        self.assertEqual(result.get("time_range"), "2025-06-30")
        self.assertTrue(result.get("continuation_mode"))
        self.assertEqual(result.get("query_context", {}).get("clarify_reason"), "skip_redundant_clarify_after_display_mode")
        self.assertTrue(result.get("query_context", {}).get("used_default_org_level"))
        self.assertEqual(result.get("query_context", {}).get("org_level"), "分行")

    def test_reply_fenhang_should_keep_previous_metric_time(self):
        """次轮仅回复“分行”时，应视为层级补充，不重置指标/时间。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "",
            "time_range": "",
            "filters": [],
            "dimensions": [],
            "chart_type": "",
            "clarification_needed": "请补充指标和时间范围",
        }

        result = self._invoke(
            "分行",
            llm_payload,
            matched_metric="贷款余额",
            time_range="2025-06-30",
            dimensions=["机构"],
            viz_type="图表",
            last_clarify_slot="display_mode",
            clarify_count=1,
            query_context={"org_level": None},
            pending_handoff={
                "target_agent": "data_expert",
                "task_description": "继续生成2025-06-30各机构贷款余额分布图表。",
            },
        )

        self.assertIsNone(result.get("clarification_needed"))
        self.assertEqual(result.get("matched_metric"), "贷款余额")
        self.assertEqual(result.get("time_range"), "2025-06-30")
        self.assertEqual(result.get("query_context", {}).get("org_level"), "分行")

    def test_reply_tubiao_without_history_should_allow_clarification(self):
        """无历史上下文时仅说“图标”，应允许追问关键槽位。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "",
            "time_range": "",
            "filters": [],
            "dimensions": [],
            "chart_type": "图表",
            "clarification_needed": "请补充具体指标和时间范围",
        }

        result = self._invoke("图标", llm_payload)

        self.assertIsNotNone(result.get("clarification_needed"))
        self.assertIn("指标", result.get("clarification_needed"))
        self.assertIn("时间范围", result.get("clarification_needed"))
        self.assertIsNone(result.get("matched_metric"))
        self.assertIsNone(result.get("time_range"))

    def test_schema_metadata_query_should_not_require_metric_and_time(self):
        """库表元数据查询应走 schema 路由，不应被追问指标和时间。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "",
            "time_range": "",
            "filters": [],
            "dimensions": [],
            "chart_type": "",
            "clarification_needed": "请补充指标和时间范围",
        }

        result = self._invoke("查询我数据库中一共有几张表", llm_payload)

        self.assertIsNone(result.get("clarification_needed"))
        self.assertEqual(result.get("data_intent"), "free_query")
        self.assertIsNone(result.get("matched_metric"))
        self.assertIsNone(result.get("time_range"))
        self.assertTrue(result.get("query_context", {}).get("is_schema_metadata_query"))
        self.assertEqual(
            result.get("query_context", {}).get("clarify_reason"),
            "skip_metric_time_clarify_for_metadata_query",
        )

    def test_handoff_task_description_can_restore_context(self):
        """handoff.task_description 含完整上下文时，应被正确继承。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "",
            "time_range": "",
            "filters": [],
            "dimensions": [],
            "chart_type": "",
            "clarification_needed": "请补充指标和时间范围",
        }

        result = self._invoke(
            "图标",
            llm_payload,
            last_clarify_slot="display_mode",
            clarify_count=1,
            pending_handoff={
                "target_agent": "data_expert",
                "task_description": "用户确认展示方式：图标。请基于2025-06-30各机构贷款余额分布生成图表，默认按分行展示。",
            },
        )

        self.assertEqual(result.get("matched_metric"), "贷款余额")
        self.assertEqual(result.get("time_range"), "2025-06-30")
        self.assertIsNone(result.get("clarification_needed"))
        self.assertTrue(result.get("query_context", {}).get("used_handoff_context"))
        self.assertEqual(result.get("query_context", {}).get("org_level"), "分行")

    def test_short_new_metric_should_not_be_treated_as_continuation(self):
        """短输入新指标（如“存款户数”）应视为新问题，避免错误继承旧时间。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "",
            "time_range": "",
            "filters": [],
            "dimensions": [],
            "chart_type": "",
            "clarification_needed": "请补充指标和时间范围",
        }

        result = self._invoke(
            "存款户数",
            llm_payload,
            matched_metric="贷款余额",
            time_range="2025-06-30",
            dimensions=["机构"],
            last_clarify_slot="display_mode",
            clarify_count=1,
            query_context={"original_question": "查询2025-06-30各机构贷款余额分布"},
        )

        self.assertFalse(result.get("continuation_mode"))
        self.assertEqual(result.get("query_context", {}).get("continuation_reason"), "metric_switched")
        self.assertTrue(result.get("query_context", {}).get("context_reset_for_new_query"))
        self.assertEqual(result.get("matched_metric"), "存款户数")
        self.assertIsNone(result.get("time_range"))
        self.assertIsNotNone(result.get("clarification_needed"))
        self.assertIn("时间范围", result.get("clarification_needed"))


    def test_metric_switch_should_use_handoff_metric_baseline(self):
        """existing_metric 为空但 handoff 有指标时，也应识别指标切换。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "",
            "time_range": "",
            "filters": [],
            "dimensions": [],
            "chart_type": "",
            "clarification_needed": "请补充指标和时间范围",
        }

        result = self._invoke(
            "存款户数",
            llm_payload,
            matched_metric="",
            time_range="",
            dimensions=["机构"],
            last_clarify_slot="display_mode",
            clarify_count=1,
            pending_handoff={
                "target_agent": "data_expert",
                "task_description": "基于2025-06-30各机构贷款余额分布继续处理。",
                "frame": {
                    "metric": "贷款余额",
                    "time_range": "2025-06-30",
                    "dimensions": ["机构"],
                    "chart_type": "图表",
                },
            },
        )

        self.assertFalse(result.get("continuation_mode"))
        self.assertEqual(result.get("query_context", {}).get("continuation_reason"), "metric_switched")
        self.assertTrue(result.get("query_context", {}).get("context_reset_for_new_query"))
        self.assertEqual(result.get("matched_metric"), "存款户数")
        self.assertIsNone(result.get("time_range"))

    def test_optional_caliber_clarification_should_not_block_ready_query(self):
        """指标+时间齐备时，口径型可选澄清不应阻断执行。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "贷款余额",
            "time_range": "2025-06-30",
            "filters": [],
            "dimensions": ["客户"],
            "chart_type": "",
            "clarification_needed": (
                "需确认数据口径：1)贷款余额是否含贴现/垫款；2)客户口径是否集团合并；"
                "3)币种口径是折人民币还是原币。"
            ),
            "clarify_level": "optional",
        }

        result = self._invoke("查询2025-06-30贷款余额前10名客户", llm_payload)

        self.assertIsNone(result.get("clarification_needed"))
        self.assertEqual(result.get("matched_metric"), "贷款余额")
        self.assertEqual(result.get("time_range"), "2025-06-30")
        self.assertEqual(
            result.get("query_context", {}).get("clarify_reason"),
            "skip_optional_clarify_level",
        )

    def test_required_clarification_should_still_block_ready_query(self):
        """clarify_level=required 时，即使指标+时间齐备也应保留澄清。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "贷款余额",
            "time_range": "2025-06-30",
            "filters": [],
            "dimensions": ["客户"],
            "chart_type": "",
            "clarification_needed": "请确认客户口径是否按集团合并",
            "clarify_level": "required",
        }

        result = self._invoke("查询2025-06-30贷款余额前10名客户", llm_payload)

        self.assertIsNotNone(result.get("clarification_needed"))
        self.assertIn("集团合并", result.get("clarification_needed"))
        self.assertEqual(result.get("query_context", {}).get("clarify_reason"), "analysis:general")

    def test_handoff_new_query_hint_should_not_force_continuation(self):
        """handoff 明确 NEW_QUERY 时，不应把首轮识别成补充轮。"""
        llm_payload = {
            "intent": "metric_query",
            "metric_name": "贷款余额",
            "time_range": "2025-06-30",
            "filters": [],
            "dimensions": ["客户"],
            "chart_type": "",
            "clarification_needed": "",
        }

        result = self._invoke(
            "查询2025-06-30贷款余额前10名客户",
            llm_payload,
            pending_handoff={
                "target_agent": "data_expert",
                "task_description": "用户原始问题：查询2025-06-30贷款余额前10名客户",
                "turn_act_hint": "NEW_QUERY",
                "frame": {
                    "metric": "贷款余额",
                    "time_range": "2025-06-30",
                    "dimensions": ["客户"],
                },
            },
        )

        self.assertFalse(result.get("continuation_mode"))
        self.assertEqual(result.get("turn_act"), "NEW_QUERY")
        self.assertEqual(result.get("query_context", {}).get("continuation_reason"), "no_prior_context")

    def test_handoff_frame_should_override_task_description_noise(self):
        """handoff frame 存在时，应优先使用 frame，避免 task_description 噪声污染。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "",
            "time_range": "",
            "filters": [],
            "dimensions": [],
            "chart_type": "",
            "clarification_needed": "请补充指标和时间范围",
        }

        result = self._invoke(
            "图标",
            llm_payload,
            pending_handoff={
                "target_agent": "data_expert",
                "task_description": "总行→分行→支行；默认按支行展示。",
                "frame": {
                    "metric": "贷款余额",
                    "time_range": "2025-06-30",
                    "dimensions": ["机构"],
                    "org_level": "分行",
                    "chart_type": "图表",
                },
            },
            last_clarify_slot="display_mode",
            clarify_count=1,
        )

        self.assertIsNone(result.get("clarification_needed"))
        self.assertEqual(result.get("matched_metric"), "贷款余额")
        self.assertEqual(result.get("time_range"), "2025-06-30")
        self.assertEqual(result.get("query_context", {}).get("org_level"), "分行")


    def test_session_frame_should_backfill_context_after_parent_schema_trim(self):
        """父图裁剪 data 专有字段后，应从 session_frame 回收关键上下文。"""
        llm_payload = {
            "intent": "clarification",
            "metric_name": "",
            "time_range": "",
            "filters": [],
            "dimensions": [],
            "chart_type": "图表",
            "clarification_needed": "请补充指标和时间范围",
        }

        result = self._invoke(
            "生成图表",
            llm_payload,
            session_frame={
                "metric": "贷款余额",
                "time_range": "2025-06-30",
                "dimensions": ["客户"],
                "chart_type": "图表",
                "org_level": "分行",
            },
            pending_handoff={
                "target_agent": "data_expert",
                "task_description": "在上一轮查询结果基础上生成图表。",
                "turn_act_hint": "SUPPLEMENT",
            },
            last_clarify_slot="display_mode",
            clarify_count=1,
        )

        self.assertIsNone(result.get("clarification_needed"))
        self.assertEqual(result.get("matched_metric"), "贷款余额")
        self.assertEqual(result.get("time_range"), "2025-06-30")
        self.assertEqual(result.get("turn_act"), "SUPPLEMENT")
        self.assertEqual(result.get("frame_source_map", {}).get("metric"), "state")



if __name__ == "__main__":
    unittest.main()
