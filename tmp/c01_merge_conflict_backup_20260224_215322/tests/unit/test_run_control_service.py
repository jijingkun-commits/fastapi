"""运行时取消控制服务测试骨架（中文注释）。

本文件用于 C01 红灯阶段，锁定以下契约：
1. 存在 ChatRun 状态模型；
2. 存在 RunControlService 控制面；
3. 支持 run_id 级别取消能力。
"""

from __future__ import annotations

import importlib
import importlib.util


def _import_required_module(module_name: str):
    """导入必须存在的模块；缺失时直接触发失败。"""

    spec = importlib.util.find_spec(module_name)
    assert spec is not None, f"缺少模块: {module_name}"
    return importlib.import_module(module_name)


def test_chat_run_model_should_exist_with_core_fields() -> None:
    """ChatRun 模型应存在并包含核心状态字段。"""

    module = _import_required_module("app.models.chat_run")
    assert hasattr(module, "ChatRun"), "缺少 ChatRun 模型定义"

    model = module.ChatRun
    required_fields = {
        "run_id",
        "session_id",
        "user_id",
        "status",
        "cancel_reason",
        "created_at",
    }
    missing = [field for field in required_fields if not hasattr(model, field)]
    assert not missing, f"ChatRun 缺少字段: {missing}"


def test_run_control_service_should_expose_cancel_contract() -> None:
    """RunControlService 应暴露 run 级控制契约。"""

    module = _import_required_module("app.services.run_control_service")
    assert hasattr(module, "RunControlService"), "缺少 RunControlService"

    service = module.RunControlService
    required_methods = {"create_run", "cancel_run", "get_run_status"}
    missing = [method for method in required_methods if not hasattr(service, method)]
    assert not missing, f"RunControlService 缺少方法: {missing}"
