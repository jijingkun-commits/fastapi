# 工作包说明

> WS 编号: WS-G2  
> 名称: 文档终稿门禁  
> 类型: gate

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260213-ADMIN-OVERVIEW-COCKPIT`
- 来源主计划：`docs/内部参考/迭代需求/implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/parallel_plan.md`

---

## 1. 目标

- 本包目标：完成代码改动后的文档同步与终稿收口。
- 完成定义（DoD）：
  1. 模块需求、架构文档、测试案例与实现保持一致。
  2. 文档映射符合 `doc_sync` 规则。
  3. 看板导出索引与最终 WS 状态一致。

---

## 2. 文件边界

### 可修改（白名单）

- `docs/产品文档/管理后台需求.md`
- `docs/开发文档/架构设计/前端架构.md`
- `docs/开发文档/架构设计/数据库设计.md`
- `docs/开发文档/测试管理/管理后台测试案例.md`
- `docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/workstreams/WS-G2_文档终稿门禁.md`

### 禁止修改（黑名单）

- `app/**`
- `web/src/**`

---

## 3. 状态与契约

- 可写字段：文档术语、章节映射、测试追溯表。
- 只读字段：业务代码与 API 实现细节（由前置 WS 提供）。

---

## 4. 实施步骤

1. 对照 WS-01~WS-04 改动回填文档映射。
2. 更新测试追溯编号（`ADMIN-OV-TC-*`）。
3. 执行 docs guard 并收口 parallel_plan 的 Gate 状态。

---

## 5. 测试与验收

- 最小测试集：
  - `venv/bin/python scripts/docs_guard.py --strict`
  - （当前环境等价执行）`python3 scripts/docs_guard.py --strict`
- 验收标准：
  1. 文档路径映射无遗漏。
  2. 文档内容与当前实现口径一致。

### 5.1 TC-ID 映射表（Gate WS 必填）

| TC-ID | 门禁命令/检查项 | 自动化脚本或 pytest nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| ADMIN-OV-DOC-001 | 管理后台需求同步 | `docs/产品文档/管理后台需求.md` 人工审阅 | 通过 | WS-G2 | |
| ADMIN-OV-DOC-002 | 前端架构文档同步 | `docs/开发文档/架构设计/前端架构.md` 人工审阅 | 通过 | WS-G2 | |
| ADMIN-OV-DOC-003 | DB 设计文档同步 | `docs/开发文档/架构设计/数据库设计.md` 人工审阅 | 通过 | WS-G2 | |
| ADMIN-OV-DOC-004 | 测试案例追溯同步 | `docs/开发文档/测试管理/管理后台测试案例.md` 人工审阅 | 通过 | WS-G2 | |

### 5.2 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：本 WS 仅文档终稿，不含 UI 修改。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因（如不触发则必填）：已由 WS-G1 覆盖浏览器门禁。

---

## 6. 风险与回滚

- 主要风险：文档口径与最终合并代码不一致。
- 回滚点：仅回退文档改动，不回退业务代码。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
  - `docs/产品文档/管理后台需求.md`
  - `docs/开发文档/架构设计/前端架构.md`
  - `docs/开发文档/测试管理/管理后台测试案例.md`
  - `docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/parallel_plan.md`
  - `docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/workstreams/WS-G2_文档终稿门禁.md`
- 是否修改了白名单外文件（是/否）：否
- 测试命令与结果：`python3 scripts/docs_guard.py --strict`（通过；errors=0, warnings=0）
- 已知风险点：后续若 WS-G1 追加接口字段，需再次执行文档对齐与追溯复核。
- 回滚建议：仅回滚本 WS 文档改动，并恢复 Gate 状态为“待执行”。

---

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-G2
  card_key: PP-20260213-ADMIN-OVERVIEW-COCKPIT::WS-G2
  title: 文档终稿门禁
  type: gate
  lane: lane-gate
  hard_depends_on:
    - WS-G1
  soft_depends_on: []
  depends_on:
    - WS-G1
  file_whitelist:
    - docs/产品文档/管理后台需求.md
    - docs/开发文档/架构设计/前端架构.md
    - docs/开发文档/架构设计/数据库设计.md
    - docs/开发文档/测试管理/管理后台测试案例.md
    - docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/workstreams/WS-G2_文档终稿门禁.md
  readonly_scope:
    - app/
    - web/src/
  owner_fields:
    - docs.admin_overview.requirements
    - docs.admin_overview.architecture
    - docs.admin_overview.test_traceability
  check_cmd:
    - venv/bin/python scripts/docs_guard.py --strict
  handoff_artifacts:
    - docs/产品文档/管理后台需求.md
    - docs/开发文档/架构设计/前端架构.md
    - docs/开发文档/架构设计/数据库设计.md
    - docs/开发文档/测试管理/管理后台测试案例.md
  dod:
    - 文档矩阵完成同步并通过 docs_guard
```
