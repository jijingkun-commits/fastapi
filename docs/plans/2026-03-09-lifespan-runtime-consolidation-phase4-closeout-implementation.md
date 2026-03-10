# 2026-03-09 lifespan runtime consolidation Phase 4 收尾重构实施计划

## 背景
这是 `Phase 4` 的收尾重构，不新增阶段编号。前面的 `Phase 4` 已经把 `_asset_service`、graph cache / provider 收口到 `runtime + registry`，但还残留三类旧 owner：
1. `app/services/permission_service.py` 里的类级 singleton（`__new__`）和模块级 `_permission_service`
2. `app/services/result_enrichment_rule_service.py` 里的模块级 `_service_singleton`
3. `app/api/v1/endpoints/data_admin_api.py` 里的导入期 `_rule_service = get_result_enrichment_rule_service()`

这三处会继续绕开 `lifespan -> AppRuntime -> CacheRegistry` 这条主干，让“应用级共享实例”同时存在两套 owner。

## 目标
- 明确本次仍属于 `Phase 4 收尾重构`，不是新阶段
- 删除剩余模块级 / 类级 singleton owner，避免双 owner
- 保留必要的薄 getter 入口，但 getter 本身不再持有状态
- 删除 endpoint 导入期实例化，让共享 service 回到 runtime registry 管理域
- 保持外部调用方式基本不变，避免无意义签名扩散

## 设计原则
1. **模块边界**：service 负责业务与实例内缓存，不负责应用级 owner
2. **依赖方向**：endpoint -> getter -> registry；禁止 endpoint/import 期反向持有共享实例
3. **状态归属**：共享实例只由 `CacheRegistry` 持有；service 内只保留实例级状态
4. **错误处理责任**：启动预热失败由 runtime 记录 degraded；业务调用失败由 service / endpoint 正常抛错

## 实施切片
### Slice 1: 收口 PermissionService owner
- 删除 `PermissionService.__new__`
- 删除类级 `_instance`、类级 `_cache`、类级 `_lock`
- 将缓存和锁下沉为实例字段 `self._cache`、`self._lock`
- 新增 registry-backed `get_permission_service()`
- 新增 `reset_permission_service()`，用于测试和 runtime cleanup 语义对齐

### Slice 2: 收口 ResultEnrichmentRuleService owner
- 删除模块级 `_service_singleton`
- 保留 service 内已有实例级 TTL cache / lock
- 将 `get_result_enrichment_rule_service()` 改为 registry-backed
- 新增 `reset_result_enrichment_rule_service()`

### Slice 3: 删除 data_admin_api 导入期实例化
- 删除 `_rule_service = get_result_enrichment_rule_service()`
- 在具体 handler 内按需调用 `get_result_enrichment_rule_service()`
- 保持路由签名不变，不新增无意义中间层

### Slice 4: 补回归与收口证据
- 新增 permission / result rule service 的 registry 级测试
- 保持已有业务测试继续通过
- 回填 `Phase 4` 总览与收尾报告，明确“删的是旧 owner，不是堆新壳”

## 非目标
- 本轮不创建 `Phase 5 / Phase 6` 新编号
- 本轮不调整 request 级依赖注入方式
- 本轮不拆分 permission / enrichment 的业务语义
- 本轮不引入新的依赖注入容器
