# 全面代码审查整改（非安全范围）— 需求基线（2026-02-27）

> 触发命令：`/jjk-plan`（重跑）
> 基线报告：`output/全面代码审查报告_合并版_20260225.md`（#1-#68）
> 代码现状快照：`git rev-parse --short HEAD = 5fe3f55`（2026-02-27）

> **范围冻结声明（强制）**
> 本轮整改**暂不考虑安全方面问题**。凡属于认证、鉴权、注入、RCE、密钥、CORS、安全护栏、健康检查鉴权等安全议题，均已从本计划移除。
> 本文件仅覆盖：架构收敛、工程质量、前端一致性、集成测试基线。后续若启动安全专项，必须单独立项并使用独立计划文档。

---

## 1. 重写目标

1. 基于当前代码现状重建“非安全范围”整改计划，避免沿用历史漂移结论。
2. 将纳入项统一映射为 `Issue -> Feature Packet -> Card -> 验收命令 -> 回滚锚点`。
3. 明确写入“安全项已剔除”的范围边界，防止后续 `/jjk-vkplan` 与执行阶段误并入。
4. 输出可机读执行契约供后续落卡消费。

---

## 2. 范围定义（本轮）

### 2.1 纳入范围（40 项）

- 架构：Graph/State 体量、分层依赖、运行态一致性。
- 后端工程质量：模型、Schema、异常处理、性能/复杂度问题。
- 前端工程质量：类型治理、交互一致性、缓存与事件生命周期。
- 测试：建立 `tests/integration/` 并形成回归基线。

### 2.2 明确剔除（安全相关 28 项）

剔除问题编号：
`#1 #2 #3 #4 #5 #6 #7 #10 #11 #12 #13 #14 #15 #34 #36 #37 #39 #47 #49 #60 #61 #62 #63 #64 #65 #66 #67 #68`

---

## 3. 当前代码现状（2026-02-27 静态复核）

### 3.1 快照事实

- 当前提交：`5fe3f55`
- 本轮问题池：40 项（P0=2，P1=13，P2=25）
- 状态判定（本轮静态复核）：
  - 未完成：37
  - 部分完成：3（#28 #31 #38）
  - 已完成：0

### 3.2 关键量化证据

- `app/ai/workflow/data_graph.py`：4489 行
- `app/ai/workflow/multi_agent_graph.py`：2900 行
- `app/services/skill_service.py`：2319 行
- `app/services/chat_service.py`：1183 行
- `web/src` 中 `as any`：19 处
- `web/src` 中 `catch (err: any)`：1 处
- `app/**` 裸 `except:`：4 处
- `app/**` `except Exception`：259 处
- `tests/integration/`：目录缺失

---

## 4. Feature Packet 定义（6 个）

| Feature Packet | 目标 | 覆盖问题 | 风险等级 | 当前状态 |
|---|---|---|---|---|
| FP-ARC-01 | Graph/State 体量与状态字段收敛 | #16, #23, #59 | P1/P2 | 未开始 |
| FP-ARC-02 | Service / Controller / Repo 边界解耦 | #17, #18, #19, #20, #40, #41, #42, #45, #46, #56, #57 | P1/P2 | 未开始 |
| FP-ARC-03 | 运行态一致性与异步可靠性 | #21, #22, #38, #43, #58 | P1/P2 | 部分完成 |
| FP-BE-01 | 后端模型/Schema/异常治理 | #8, #24, #29, #30, #31, #32, #33, #44, #48, #50, #51 | P0/P1/P2 | 部分完成 |
| FP-FE-01 | 前端类型与交互一致性 | #9, #26, #27, #28, #35, #52, #53, #54, #55 | P0/P1/P2 | 部分完成 |
| FP-QA-01 | 集成测试与可追溯矩阵 | #25 | P1 | 未开始 |

---

## 5. 40 项问题逐项映射（Issue -> FP）

| # | 严重级别 | 问题 | Feature Packet | 当前状态（2026-02-27） |
|---|---|---|---|---|
| 8 | P0 | todo_api.py:338 空指针风险 | FP-BE-01 | 未完成 |
| 9 | P0 | 前端 handleConfirm 传递错误的 DecisionType | FP-FE-01 | 未完成 |
| 16 | P1 | LangGraph Workflow 文件严重膨胀 | FP-ARC-01 | 未完成 |
| 17 | P1 | chat_service.py God Object | FP-ARC-02 | 未完成 |
| 18 | P1 | skill_service.py God Object | FP-ARC-02 | 未完成 |
| 19 | P1 | data_admin_api.py Fat Controller | FP-ARC-02 | 未完成 |
| 20 | P1 | chat_repo.py Repository 反向依赖 Service | FP-ARC-02 | 未完成 |
| 21 | P1 | postgres_checkpoint.py 异步单例竞态 | FP-ARC-03 | 未完成 |
| 22 | P1 | 同步 ORM 阻塞异步 LangGraph 事件循环 | FP-ARC-03 | 未完成 |
| 23 | P1 | BaseAgentState 字段膨胀 | FP-ARC-01 | 未完成 |
| 24 | P1 | 全局 extracted_dataframes 字典内存泄漏 | FP-BE-01 | 未完成 |
| 25 | P1 | 零集成测试 | FP-QA-01 | 未完成 |
| 26 | P1 | 大量 as any 断言（19 处） | FP-FE-01 | 未完成 |
| 27 | P1 | SSE 流异常结束时线程列表不刷新 | FP-FE-01 | 未完成 |
| 28 | P1 | catch (err: any) 模式遗留 | FP-FE-01 | 部分完成 |
| 29 | P2 | datetime 时间戳 default=func.now() | FP-BE-01 | 未完成 |
| 30 | P2 | ORM 风格不一致 | FP-BE-01 | 未完成 |
| 31 | P2 | 模型导出不完整 | FP-BE-01 | 部分完成 |
| 32 | P2 | t_chat_feedback 无 ORM 模型 | FP-BE-01 | 未完成 |
| 33 | P2 | Schema 定义散落在 endpoint 文件内 | FP-BE-01 | 未完成 |
| 35 | P2 | lang="cn" 应为 lang="zh-CN" | FP-FE-01 | 未完成 |
| 38 | P2 | RunControlService 内存态与数据库态一致性风险 | FP-ARC-03 | 部分完成 |
| 40 | P2 | deps.py 中认证逻辑大量重复代码 | FP-ARC-02 | 未完成 |
| 41 | P2 | router.py import 风格不一致 | FP-ARC-02 | 未完成 |
| 42 | P2 | chat_api.py 函数内 import | FP-ARC-02 | 未完成 |
| 43 | P2 | _log_disliked_sql_query 阻塞请求线程 | FP-ARC-03 | 未完成 |
| 44 | P2 | todo_api.py validator 返回类型不匹配 | FP-BE-01 | 未完成 |
| 45 | P2 | llm_admin_api.py 使用 getattr/setattr | FP-ARC-02 | 未完成 |
| 46 | P2 | global_exception_handler 重复检查 | FP-ARC-02 | 未完成 |
| 48 | P2 | list_skills O(n^2) 查找 | FP-BE-01 | 未完成 |
| 50 | P2 | 裸 except 与宽泛异常捕获过多 | FP-BE-01 | 未完成 |
| 51 | P2 | 注释中包含 emoji | FP-BE-01 | 未完成 |
| 52 | P2 | 模块级可变缓存无失效机制 | FP-FE-01 | 未完成 |
| 53 | P2 | useFileUpload 事件监听器频繁重建 | FP-FE-01 | 未完成 |
| 54 | P2 | handleSubmitEdit 传递不支持的参数 | FP-FE-01 | 未完成 |
| 55 | P2 | 根路由与 /chat 路由渲染相同组件 | FP-FE-01 | 未完成 |
| 56 | P2 | 全局单例三种实现共存 | FP-ARC-02 | 未完成 |
| 57 | P2 | f-string 日志模式 | FP-ARC-02 | 未完成 |
| 58 | P2 | datetime.fromtimestamp() 使用本地时区 | FP-ARC-03 | 未完成 |
| 59 | P2 | 参考实现 chat_graph.py 源文件已删除 | FP-ARC-01 | 未完成 |

> 覆盖校验：本轮纳入项 `40/40` 完整映射，未出现未归档问题。

---

## 6. 用户故事（Who / Scenario / Goal / Why）

| 角色 | 场景 | 目标 | 价值 |
|---|---|---|---|
| 平台负责人 | 安全专项暂缓，但架构与质量问题已影响迭代效率 | 先完成非安全范围收敛计划 | 控制改造范围，保持交付连续性 |
| 后端工程师 | 多处 God Object 与状态不一致导致改动高耦合 | 先按架构与工程质量问题分批治理 | 降低回归风险与维护成本 |
| 前端工程师 | 类型与交互问题导致线上行为不稳定 | 获取明确 FE 整改边界与验收命令 | 提升交互稳定性与协作一致性 |
| QA/运维 | 缺少集成回归基线 | 建立最小可运行的 integration 门禁 | 提升发布可预测性 |

---

## 7. 验收标准（功能 / 边界 / 性能稳定性）

### 7.1 功能性

1. 纳入的 40 项问题全部映射到 FP 与卡片，且卡片可执行。
2. 所有卡片均具备 `done_gate` 与 `acceptance_checks`。
3. 执行顺序固定为：架构 -> 工程质量 -> 集成测试 -> Gate。

### 7.2 异常与边界

1. 状态流转异常（run-control/checkpoint）必须可回放并具备一致性证据。
2. 前端 SSE 异常结束后线程列表必须刷新，不允许“消息到达但列表不更新”。
3. Schema 校验失败必须返回一致错误语义，不允许静默吞错。

### 7.3 性能与稳定性

1. `list_skills` 的复杂度问题需从 O(n^2) 收敛到线性或可缓存策略。
2. 宽泛异常捕获数量趋势必须下降并建立门禁。
3. 集成测试基线建立后，应可在标准 CI 周期内执行。

---

## 8. 非功能需求（NFR）

1. **一致性**：状态字段定义单一来源，跨模块无语义漂移。
2. **可维护性**：分层边界清晰，不再存在 Repo 反向依赖 Service。
3. **可观测性**：关键状态转移可追踪，错误分类可审计。
4. **可回滚性**：高风险改动具备特性开关或兼容回退路径。
5. **可测试性**：每个 FP 至少绑定 1 条可执行命令。

---

## 9. 关联测试用例预留（追溯矩阵入口）

| TC ID | 目标问题域 | 对应 FP | 验证类型 |
|---|---|---|---|
| TC-ARC-01 | Graph/State 拆分兼容 | FP-ARC-01 | unit |
| TC-ARC-02 | 分层依赖收敛 | FP-ARC-02 | unit |
| TC-ARC-03 | run-control 一致性 | FP-ARC-03 | unit |
| TC-BE-01 | 模型与 Schema 治理 | FP-BE-01 | unit |
| TC-FE-01 | 类型与交互一致性 | FP-FE-01 | unit + web |
| TC-QA-01 | 全链路回归基线 | FP-QA-01 | integration |

---

## 10. 场景约束（平台/架构迁移）

1. 本任务属于平台治理与架构整改，不引入新业务功能。
2. 本轮严格排除安全范围，不接受执行期“顺手修安全”并入。
3. 门禁顺序固定：架构 -> 工程质量 -> 集成测试 -> 全局 Gate。
4. 规划必须支持串行单卡推进，满足自动执行场景收敛。

---

## 11. 交付物

1. `workdocs/归档/正文/需求/全面代码审查整改_requirements.md`（本文件）
2. `workdocs/归档/正文/实施计划/全面代码审查整改_implementation_plan.md`（实施方案）
3. `docs/SUMMARY.md`（索引同步）
4. 后续执行输入：`planning_contract`（见 implementation_plan）

---

## 12. 需求状态声明

```yaml
plan_status:
  mode: core
  security_scope: excluded
  included_issue_count: 40
  excluded_security_issue_count: 28
  ready_for_vkplan: true
  notes:
    - "本轮禁止并入安全整改"
    - "docs_guard --strict 当前存在历史断链，非本次规划新增"
```
