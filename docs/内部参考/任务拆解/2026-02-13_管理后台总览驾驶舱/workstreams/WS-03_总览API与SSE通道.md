# 工作包说明

> WS 编号: WS-03  
> 名称: 总览 API 与 SSE 通道  
> 类型: parallel

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260213-ADMIN-OVERVIEW-COCKPIT`
- 来源主计划：`docs/内部参考/迭代需求/implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/parallel_plan.md`

---

## 1. 目标

- 本包目标：提供总览 `summary/trends/stream` 接口并接入管理员鉴权。
- 完成定义（DoD）：
  1. 新增 `admin_overview_api.py` 并注册路由。
  2. `stream` 事件严格遵守 G0 契约。
  3. SSE 中断时返回可解释 `interrupt` 事件并支持轮询降级。

---

## 2. 文件边界

### 可修改（白名单）

- `app/api/v1/endpoints/admin_overview_api.py`
- `app/api/v1/router.py`
- `app/schemas/admin_overview.py`
- `tests/api/test_admin_overview_api.py`

### 禁止修改（黑名单）

- `app/models/**`
- `web/src/**`

---

## 3. 状态与契约

- 可写字段：接口入参/出参 schema，SSE 事件封装。
- 只读字段：`health_score` 算法和前端展示样式。
- 外部契约：`contracts/sse_events_v1.json`（只读消费）。

---

## 4. 实施步骤

1. 定义 summary/trends 响应 schema。
2. 实现 `GET /api/v1/admin-overview/summary`。
3. 实现 `GET /api/v1/admin-overview/trends`（1h/24h）。
4. 实现 `GET /api/v1/admin-overview/stream`（SSE）。
5. 注册到 `app/api/v1/router.py` 并挂管理员依赖。

---

## 5. 测试与验收

- 最小测试集：
  - `venv/bin/python -m pytest -q tests/api/test_admin_overview_api.py`
- 验收标准：
  1. 非管理员访问返回 403。
  2. 接口字段完整，SSE 事件具备 `done/result/interrupt`。

### 5.1 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：本 WS 仅 API 层，无前端交互。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：无页面改动。

---

## 6. 风险与回滚

- 主要风险：SSE 推送频率过高导致连接抖动。
- 回滚点：关闭 stream 路由，仅保留 summary + trends 轮询。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改了白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：

---

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-03
  card_key: PP-20260213-ADMIN-OVERVIEW-COCKPIT::WS-03
  title: 总览 API 与 SSE 通道
  type: parallel
  lane: lane-backend-api
  hard_depends_on:
    - WS-00
    - WS-02
  soft_depends_on:
    - WS-01
  depends_on:
    - WS-00
    - WS-02
  file_whitelist:
    - app/api/v1/endpoints/admin_overview_api.py
    - app/api/v1/router.py
    - app/schemas/admin_overview.py
    - tests/api/test_admin_overview_api.py
  readonly_scope:
    - app/models/
    - web/src/
  owner_fields:
    - api.summary
    - api.trends
    - sse.stream_event
  check_cmd:
    - venv/bin/python -m pytest -q tests/api/test_admin_overview_api.py
  handoff_artifacts:
    - app/api/v1/endpoints/admin_overview_api.py
    - app/schemas/admin_overview.py
  dod:
    - summary/trends/stream 接口可用并符合 G0 协议冻结
```
