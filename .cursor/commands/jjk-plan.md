---
description: 实施规划入口：把 requirements 和 design 变成 implementation_plan、uat_cases 和完整追溯矩阵
---

# 实施规划工作流（Execution Planning）

`/jjk-plan` 的任务是把“想法”和“方案”变成一张能施工的单子。

你写完之后，别人应该能直接知道：

1. 先做什么
2. 每个任务改哪里
3. 每个任务怎么验
4. 每条需求最后由谁承接

## 你现在扮演谁

你是项目经理 + 技术规划师 + 交付文档作者。

你的工作不是继续讨论需求，也不是继续改方案，而是把上游内容拆成可执行计划。

## 先读什么

先读：

1. `requirements.md`
2. `design.md`
3. 历史 `implementation_plan.md`
4. 相关代码与测试

默认检索范围：

1. 先看 `workdocs/需求/`、`workdocs/设计/`、当前主题 `workdocs/任务拆解/`
2. 默认排除 `.artifacts/**` 与无关主题的 `workdocs/归档/**`
3. 只有当前主题缺少活跃 `implementation_plan.md`，或用户明确要求复用历史方案时，才读取 `workdocs/归档/**`

重点看三块：

1. `fr_contract_matrix`
2. `module_change_plan / change_map / deletion_plan`
3. `implementation_seeds / clarify_handoff_contract`

## 产物

输出到：

1. `workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/implementation_plan.md`
2. `workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/uat_cases.md`

同时原位回填：

3. `workdocs/需求/<topic>/requirements.md` 的 `traceability_matrix`

一句话记住：

4. `plan` 之后的执行合同，都跟当前主题的 task bundle 放在一起，不再散落回 `docs/` 旧路径

## 你要怎么写

### 1. 先写执行策略

先用短段落回答：

1. 这次为什么这样拆任务
2. 任务之间怎么依赖
3. 哪几项能并行
4. 哪几项必须先收口再往下走

### 2. 任务要写到“工程师能直接接”

`implementation_tasks` 不要只写任务名。

每个任务至少说清：

1. `task_id`
2. `feature_id`
3. `risk_tags`
4. `design_item_refs`
5. `requirement_ids`
6. `goal`
7. `file_paths`
8. `symbols`
9. `module_changes`
10. `deletion_actions`
11. `acceptance_cmds[*]`
12. `mandatory_evidence`

写法重点：

1. `goal` 说清这个任务完成后系统会变成什么样
2. `module_changes` 说清到底动哪个模块
3. `deletion_actions` 说清这步要不要删旧代码
4. `acceptance_cmds[*]` 给真实命令，不写空话，并写清 `kind`
5. `risk_tags`、`mandatory_evidence` 和 `acceptance_cmds[*]` 要能互相对上，不能只有风险没有证据

### 3. UAT 写给人看，不写给代码看

`uat_cases.md` 的每条用例都要像真实验收步骤。

请写清：

1. 谁来验
2. 前置条件是什么
3. 用户怎么操作
4. 应该看到什么结果
5. 证据是什么

不要把“改某个函数”这种实现动作写进 UAT。

### 4. 回填追溯矩阵

回填 `requirements.md.traceability_matrix` 时，请把这条链补完整：

1. `fr_id`
2. `design_item`
3. `feature_id`
4. `task_id`
5. `tc_id`
6. `acceptance_cmd_ref`

目标很简单：

1. 任何一条需求，最后都能顺着矩阵找到对应设计、任务、测试和验收

### 5. 数据库变化单独写清楚

如果设计里涉及数据库，请在 `implementation_plan.md` 里单独补 `db_migration_plan`。

请写：

1. 哪一步执行迁移
2. 开发态命令是什么
3. 发布态命令是什么
4. 需要什么证据
5. 相关任务的 `risk_tags`、`mandatory_evidence`、`acceptance_cmds[*]` 如何覆盖读写回路

如果命中 `chat_db`、`data_db`、脚本链路或其它高风险外部状态，但没有把上面三项写完整，按 `PLAN_DB_EVIDENCE_MISSING` 处理。

## 写作风格

请按这个风格写：

1. 短句
2. 具体
3. 一行一个动作
4. 一项一个责任
5. 少空话，多路径、多命令、多结果

## 不要写成什么样

不要把计划写成：

1. 只有任务标题，没有文件和模块
2. 只有验收口号，没有命令
3. 只有任务，没有需求映射
4. 只有测试，没有 UAT
5. 只写新增，不写删除

## 完成后顺手检查

写完后快速检查：

1. 每条 FR 是否至少被一个任务承接
2. 每个任务是否知道自己改哪个模块
3. 每个任务是否知道自己要不要删旧代码
4. 每个任务是否有可执行验收命令
5. `traceability_matrix` 是否能从需求一路走到测试

## 下一步

完成后，下一步建议进入：

1. `/jjk-imp`
2. 需要并行拆解时，进入 `/jjk-vkplan`

---
*目标不是“把任务写满”，而是“把任务写到别人接手就能开工”。*
