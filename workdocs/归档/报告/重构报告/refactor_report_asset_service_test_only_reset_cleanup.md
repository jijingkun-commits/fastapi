# Refactor Report: asset_service_test_only_reset_cleanup

- 日期：2026-03-12
- 主题：删除 `asset_service` 中仅供测试使用的 reset seam
- 范围：`app/services/asset_service.py`、`tests/unit/test_asset_service_runtime_registry.py`
- 结论：移除 `reset_asset_service()`，测试改为通过公共 `reset_cache_registry()` 控制共享实例生命周期
- 最佳实践依据：测试应尽量依赖公共状态管理接口，不为测试在生产模块中保留专用重置入口
- obsolete_paths：`app/services/asset_service.py::reset_asset_service`
- retained_paths：`app/services/asset_service.py::get_asset_service`、`app/core/cache_registry.py::reset_cache_registry`
- single_entry_owner：`app/core/cache_registry.py::reset_cache_registry`
- 变更摘要：删除 1 个 test-only helper；runtime registry 回归测试改用公共 cache registry
- 行数预算：代码与测试净删除；新增仅为审计报告
- 验证计划：`tests/unit/test_asset_service_runtime_registry.py`
- 风险：若仓外私有脚本直接 import `reset_asset_service`，会在运行时暴露 `AttributeError`
- 回滚点：如发现隐藏依赖，可短期恢复该 helper，随后统一迁移调用方到 `reset_cache_registry`
