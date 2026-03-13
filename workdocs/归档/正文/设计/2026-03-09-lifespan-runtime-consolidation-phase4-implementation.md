# 2026-03-09 lifespan runtime consolidation Phase 4 实施计划

## 背景
Phase 1~3 已将 `lifespan` 主流程、DB 生命周期和部分进程级缓存收口到 `app.state.runtime`。当前仍有两类应用级共享资源停留在模块级全局状态：
1. `app/ai/workflow/multi_agent_graph.py` 中的 `_MULTI_AGENT_GRAPH_CACHE`
2. `app/services/asset_service.py` 中的 `_asset_service`

这两者都符合 FastAPI/Starlette 官方对 lifespan 资源的适用场景：
- 启动前准备、请求间共享、关闭时应有明确 owner 的资源
- 共享对象建议通过 lifespan state / app state 暴露，而不是散落在模块全局中

## 口径说明
本任务线正式分期只到 `Phase 4`。此前误写为“Phase 5”的 graph provider 外移，现统一并回 **Phase 4 收尾重构**，不再新增阶段编号。

## 目标
- 保持对外调用方式尽量稳定
- 将 graph / asset 的 owner 收口到 runtime 管理域
- 避免把 `app.state` 直接扩散到业务模块
- 继续以轻量 getter + registry 方式演进，而不是引入新的 DI 容器

## 实施切片
### Slice 1: graph runtime registry 化
- 为多智能体图缓存增加 registry-backed 存储与 reset 入口
- 保持 `get_multi_agent_graph()` API 不变
- runtime 预热默认图时复用同一缓存 owner

### Slice 2: asset service runtime registry 化
- 移除模块级 `_asset_service` owner
- `get_asset_service()` 改为从 registry 获取/创建实例
- runtime 启动阶段记录 warmup 状态，不在模块导入期创建实例

### Slice 3: 回归与证据
- 新增 graph/asset runtime owner 测试
- 回归 runtime/bootstrap/chat-assets/health 相关用例
- 输出 refactor report 补充 Phase 4 证据；若继续做 graph provider 外移，归入 `Phase 4 收尾重构`

## 非目标
- 本轮不做全量 `request.app.state.runtime` 注入改签名
- 本轮不继续拆 `data_graph.py` 的业务语义逻辑
- 本轮不引入额外容器/服务定位器抽象
