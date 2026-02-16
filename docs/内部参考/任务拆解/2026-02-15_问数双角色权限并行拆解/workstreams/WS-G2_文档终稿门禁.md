# 工作包说明

> WS 编号: WS-G2
> 名称: 文档终稿门禁
> 类型: gate

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION`
- 来源主计划：`docs/内部参考/迭代需求/askdata_dual_role_permission_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md`

---

## 1. 目标

- 本包目标：完成产品/架构/测试文档终稿同步并通过文档门禁。
- 完成定义（DoD）：
  1. 文档映射更新完整。
  2. `SUMMARY` 索引可达。
  3. `docs_guard` 严格模式通过。

---

## 2. 文件边界

### 可修改（白名单）

- `docs/产品文档/问数助手需求.md`
- `docs/产品文档/用户管理需求.md`
- `docs/开发文档/架构设计/问数引擎设计.md`
- `docs/开发文档/架构设计/数据库设计.md`
- `docs/开发文档/测试管理/问数引擎测试案例.md`
- `docs/开发文档/测试管理/用户管理测试案例.md`
- `docs/SUMMARY.md`
- `docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/workstreams/WS-G2_文档终稿门禁.md`

### 禁止修改（黑名单）

- `app/**`
- `web/**`

---

## 3. 状态与契约

- 可写字段：`gate.g2.docs_sync`、`gate.g2.summary_index`。
- 只读字段：业务实现逻辑。

---

## 4. 实施步骤

1. 按代码变更映射同步产品/架构/测试文档。
2. 更新 `docs/SUMMARY.md` 新增入口。
3. 执行 `docs_guard` 并回填 Gate 结论。

---

## 5. 测试与验收

- 最小测试集：
  - `python3 scripts/docs_guard.py --strict`
- 验收标准：
  1. 文档无断链，覆盖率不下降。
  2. 索引入口可达。

### 5.1 TC-ID 映射表（Gate WS 必填）

| TC-ID | 门禁命令/检查项 | 自动化脚本或 nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| DP-DOC-001 | 文档严格门禁 | `python3 scripts/docs_guard.py --strict` | PASS | WS-G2 | - |
| DP-DOC-002 | 索引可达性 | `docs/SUMMARY.md` 人工审阅 | PASS | WS-G2 | - |

### 5.2 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：文档终稿门禁，不涉及 UI。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：非浏览器场景。

---

## 6. 风险与回滚

- 主要风险：文档与实现脱节，影响后续维护。
- 回滚点：按文档文件粒度回退并重跑门禁。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
  - `docs/SUMMARY.md`
  - `docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md`
  - `docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/workstreams/WS-G2_文档终稿门禁.md`
- 是否修改了白名单外文件（是/否）：否
- 测试命令与结果：
  - `python3 scripts/docs_guard.py --strict`（PASS）
- 已知风险点：本次仅修正索引断链并完成 Gate 回填，未新增文档专题内容。
- 回滚建议：如需回退，按文档文件粒度回滚并重跑 `docs_guard`。

---

## 8. card_export（/vk 机读，必填）

```yaml
card_export:
  id: WS-G2
  card_key: PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION::WS-G2
  title: 文档终稿门禁
  type: gate
  lane: lane-gate
  hard_depends_on:
    - WS-G1
  soft_depends_on: []
  depends_on:
    - WS-G1
  file_whitelist:
    - docs/产品文档/问数助手需求.md
    - docs/产品文档/用户管理需求.md
    - docs/开发文档/架构设计/问数引擎设计.md
    - docs/开发文档/架构设计/数据库设计.md
    - docs/开发文档/测试管理/问数引擎测试案例.md
    - docs/开发文档/测试管理/用户管理测试案例.md
    - docs/SUMMARY.md
    - docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/workstreams/WS-G2_文档终稿门禁.md
  readonly_scope:
    - app/
    - web/
  owner_fields:
    - gate.g2.docs_sync
    - gate.g2.summary_index
  check_cmd:
    - python3 scripts/docs_guard.py --strict
  handoff_artifacts:
    - docs/SUMMARY.md
  dod:
    - 文档矩阵与索引同步完成并通过 docs_guard
```
