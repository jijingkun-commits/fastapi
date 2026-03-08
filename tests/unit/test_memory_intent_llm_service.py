"""用户记忆意图 LLM 合同判定测试。"""

from __future__ import annotations

from dataclasses import dataclass

import app.services.memory_intent_llm_service as llm_service


@dataclass
class _Message:
    content: object


class _ModelDumpMessage:
    def __init__(self, content: object):
        self.content = content

    def model_dump(self) -> dict[str, object]:
        return {
            "content": self.content,
            "type": "ai",
        }


class _FakeLLM:
    def __init__(self, response: object, *, should_raise: bool = False):
        self._response = response
        self._should_raise = should_raise
        self.calls: list[str] = []

    def invoke(self, prompt: str):
        self.calls.append(prompt)
        if self._should_raise:
            raise RuntimeError("mock-llm-error")
        return self._response


def _build_accept_item(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "memory_kind": "response_preference",
        "operation": "upsert",
        "slot_key": "user.preference.response_style",
        "normalized_value": "conclusion_first",
        "canonical_text": "用户偏好先结论后分析",
        "evidence_span": "先给结论再分析",
        "durability": 0.9,
    }
    payload.update(overrides)
    return payload


def test_decide_should_accept_decision_contract_with_memories_array() -> None:
    """合法合同应输出 accepted DecisionContract。"""

    llm = _FakeLLM(
        {
            "decision": "accept",
            "reason_code": "accepted",
            "confidence": 0.93,
            "memories": [_build_accept_item()],
            "audit": {"detector": "llm_primary"},
        }
    )

    decision = llm_service.decide(llm=llm, user_text="以后都先给结论再分析")

    assert decision["decision"] == "accept"
    assert decision["reason_code"] == "accepted"
    assert decision["confidence"] == 0.93
    assert len(decision["memories"]) == 1
    assert decision["memories"][0]["slot_key"] == "user.preference.response_style"


def test_decide_should_parse_markdown_json_block() -> None:
    """模型输出 markdown json 代码块时也应能解析。"""

    llm = _FakeLLM(
        _Message(
            content=(
                "```json\n"
                "{"
                '"decision":"accept",'
                '"reason_code":"accepted",'
                '"confidence":0.91,'
                '"memories":[{'
                '"memory_kind":"assistant_persona",'
                '"operation":"upsert",'
                '"slot_key":"assistant.persona.style",'
                '"normalized_value":"friendly",'
                '"canonical_text":"助手人设为友好亲切",'
                '"evidence_span":"你就叫小哈",'
                '"durability":0.8'
                "}]"
                "}\n"
                "```"
            )
        )
    )

    decision = llm_service.decide(llm=llm, user_text="以后你叫小哈")

    assert decision["decision"] == "accept"
    assert decision["memories"][0]["memory_kind"] == "assistant_persona"


def test_decide_should_parse_content_when_message_has_model_dump() -> None:
    """AIMessage 风格对象应优先解析 content，不得误判缺字段。"""

    llm = _FakeLLM(
        _ModelDumpMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        '{"decision":"accept","reason_code":"accepted",'
                        '"confidence":0.9,"memories":[{"memory_kind":"response_preference",'
                        '"operation":"upsert","slot_key":"user.preference.response_style",'
                        '"normalized_value":"detailed","canonical_text":"用户偏好表述详细",'
                        '"evidence_span":"更详细地交流"}]}'
                    ),
                }
            ]
        )
    )

    decision = llm_service.decide(llm=llm, user_text="以后用更详细的表述方式交流")

    assert decision["decision"] == "accept"
    assert decision["reason_code"] == "accepted"
    assert decision["memories"][0]["slot_key"] == "user.preference.response_style"


def test_decide_should_reject_when_required_field_missing() -> None:
    """顶层字段缺失时应拒绝并返回 reason_code。"""

    llm = _FakeLLM(
        {
            "decision": "accept",
            "confidence": 0.93,
            "memories": [_build_accept_item()],
        }
    )

    decision = llm_service.decide(llm=llm, user_text="以后都先给结论")

    assert decision["decision"] == "reject"
    assert decision["reason_code"] == "contract_missing_required"


def test_decide_identity_semantic_should_accept_without_trigger() -> None:
    """无触发词身份表达也应由模型直判接受。"""

    llm = _FakeLLM(
        {
            "decision": "accept",
            "reason_code": "accepted",
            "confidence": 0.95,
            "memories": [
                _build_accept_item(
                    memory_kind="user_identity",
                    slot_key="user.identity.display_name",
                    normalized_value="jjk",
                    canonical_text="用户名字是jjk",
                    evidence_span="我叫jjk",
                )
            ],
        }
    )

    decision = llm_service.decide(llm=llm, user_text="我叫jjk")

    assert decision["decision"] == "accept"
    assert decision["memories"][0]["memory_kind"] == "user_identity"
    assert decision["memories"][0]["slot_key"] == "user.identity.display_name"


def test_decide_multi_memory_items_should_return_array() -> None:
    """多记忆句应返回 memories[] 数组，不得压缩成单项。"""

    llm = _FakeLLM(
        {
            "decision": "accept",
            "reason_code": "accepted",
            "confidence": 0.96,
            "memories": [
                _build_accept_item(
                    slot_key="user.preference.response_structure",
                    normalized_value="conclusion_first",
                    canonical_text="用户偏好先结论后分析",
                    evidence_span="先给结论",
                ),
                _build_accept_item(
                    slot_key="user.preference.response_length",
                    normalized_value="short",
                    canonical_text="用户偏好回答简短",
                    evidence_span="回答简短一点",
                ),
            ],
        }
    )

    decision = llm_service.decide(llm=llm, user_text="以后先给结论，回答简短一点")

    assert decision["decision"] == "accept"
    assert isinstance(decision["memories"], list)
    assert len(decision["memories"]) == 2


def test_decide_style_semantic_should_normalize() -> None:
    """风格偏好应输出稳定 slot 与 normalized_value。"""

    llm = _FakeLLM(
        {
            "decision": "accept",
            "reason_code": "accepted",
            "confidence": 0.92,
            "memories": [
                _build_accept_item(
                    slot_key="user.preference.response_style",
                    normalized_value="less_official",
                    canonical_text="用户希望语气少一些官方感",
                    evidence_span="别太官方",
                )
            ],
        }
    )

    decision = llm_service.decide(llm=llm, user_text="以后回答狠一点，别太官方")

    assert decision["decision"] == "accept"
    assert decision["memories"][0]["slot_key"] == "user.preference.response_style"
    assert decision["memories"][0]["normalized_value"] == "less_official"


def test_decide_multi_preference_sentence_should_emit_two_memories() -> None:
    """同一句多偏好应拆成两个 memory item。"""

    llm = _FakeLLM(
        {
            "decision": "accept",
            "reason_code": "accepted",
            "confidence": 0.94,
            "memories": [
                _build_accept_item(
                    slot_key="user.preference.response_structure",
                    normalized_value="conclusion_first",
                    canonical_text="用户偏好先给结论",
                    evidence_span="先给结论",
                ),
                _build_accept_item(
                    slot_key="user.preference.response_length",
                    normalized_value="short",
                    canonical_text="用户偏好回答简短",
                    evidence_span="简短一点",
                ),
            ],
        }
    )

    decision = llm_service.decide(llm=llm, user_text="以后先给结论，回答简短一点")

    assert decision["decision"] == "accept"
    assert {item["slot_key"] for item in decision["memories"]} == {
        "user.preference.response_structure",
        "user.preference.response_length",
    }


def test_decide_translation_should_not_persist() -> None:
    """翻译/引用任务应拒绝入库。"""

    llm = _FakeLLM(
        {
            "decision": "reject",
            "reason_code": "task_intent_translation_or_quote",
            "confidence": 0.97,
            "memories": [],
        }
    )

    decision = llm_service.decide(llm=llm, user_text="翻译一下：我叫jjk")

    assert decision["decision"] == "reject"
    assert decision["reason_code"] == "task_intent_translation_or_quote"


def test_decide_should_reject_when_confidence_below_threshold() -> None:
    """低于阈值时应拒绝。"""

    llm = _FakeLLM(
        {
            "decision": "accept",
            "reason_code": "accepted",
            "confidence": 0.64,
            "memories": [_build_accept_item()],
        }
    )

    decision = llm_service.decide(llm=llm, user_text="以后都先给结论")

    assert decision["decision"] == "reject"
    assert decision["reason_code"] == "low_confidence"


def test_decide_should_reject_when_llm_invoke_failed() -> None:
    """模型调用异常应容错拒绝。"""

    llm = _FakeLLM(response={}, should_raise=True)

    decision = llm_service.decide(llm=llm, user_text="以后都先给结论")

    assert decision["decision"] == "reject"
    assert decision["reason_code"] == "llm_invoke_failed"
