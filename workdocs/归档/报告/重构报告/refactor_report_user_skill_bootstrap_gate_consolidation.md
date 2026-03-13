# Refactor Report: user_skill_bootstrap_gate_consolidation

- 日期：2026-03-12
- 主题：移除 `user_service` 的重复 Skill bootstrap gate，收口到 `skill_bootstrap_service`
- 范围：`app/services/user_service.py`、`app/services/skill_bootstrap_service.py`、`tests/unit/test_user_service_skill_bootstrap.py`、相关实施文档
- 结论：`bootstrap_user_skills` 成为唯一开关判定 owner，`create_user` 只负责在用户创建后调用该服务
- 最佳实践依据：feature gate 评估应收口成单一知识源，避免上层和下层重复判断导致状态归属分裂
- obsolete_paths：`app/services/user_service.py::_is_user_skill_bootstrap_enabled`、对应测试 monkeypatch 耦合
- retained_paths：`app/services/skill_bootstrap_service.py::_is_bootstrap_enabled`、`bootstrap_user_skills`、`app/services/user_service.py::create_user`
- single_entry_owner：`app/services/skill_bootstrap_service.py::_is_bootstrap_enabled`
- 变更摘要：删除 1 处重复 gate；把“配置解析失败视为关闭”的保护迁到 service owner；测试改为锚定 canonical service
- 行数预算：代码与测试净删除；新增仅为审计报告
- 验证计划：`tests/unit/test_user_service_skill_bootstrap.py`、`tests/unit/test_user_service_memory_bootstrap.py`
- 风险：若未来有人在 `create_user` 外再复制一层 Skill bootstrap gate，会重新引入双重判定
- 回滚点：恢复 `user_service` 内部 helper，或在 `bootstrap_user_skills` 明确透出 enablement contract 后再调整调用方
