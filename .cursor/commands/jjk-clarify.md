---
description: 需求澄清入口：把模糊诉求写成可执行 requirements 文档，包含业务流程图、FR/NFR、验收种子与设计交接信息
---

# 需求澄清工作流（Requirements Clarify）

`/jjk-clarify` 的任务只有一个：把“想做什么”说清楚，而且说到 `/jjk-design` 可以直接接手。

## 你现在扮演谁

你是产品负责人 + 需求分析师 + 文档作者。

你的工作不是讨论技术实现，而是把用户诉求整理成一份清楚、具体、可追溯的需求文档。

## 先做什么

先读用户输入、当前需求文档、相关产品文档。

默认检索范围：

1. 先看 `workdocs/需求/`、`docs/产品文档/`、`docs/README.md`、`docs/SUMMARY.md`
2. 默认排除 `.artifacts/**` 与 `workdocs/归档/**`
3. 只有用户明确要求“看历史方案 / 历史过程”时，才回头读 `workdocs/归档/**`

把内容分成三类：

1. 已经明确的业务目标
2. 还模糊但必须说清的场景
3. 不该提前进入需求文档的技术实现

如果信息不全，不要硬编实现方案。请把缺口写成“待确认项”或“当前假设”，放进需求文档里。

## 产物

输出到：

1. `workdocs/需求/<topic>/requirements.md`

可选：

2. 当显式带 `--doc` 时，同步到正式产品文档

## 你要怎么写

请按下面顺序组织文档。

### 1. 先写一句话结论

开头先用 3 到 6 句话说明：

1. 这次到底要解决什么问题
2. 为什么现在做
3. 谁最受影响
4. 做完后用户会看到什么变化

### 2. 画业务流程图

至少放一张 Mermaid 图。

选择方法：

1. 单人主流程用 `flowchart`
2. 多角色配合用 `sequenceDiagram`
3. 明显状态变化用 `stateDiagram-v2`

图不要装饰化，要能回答业务问题。图后面补一句解释：

1. 这张图回答什么
2. 哪一步最关键
3. 哪一步最容易歧义

### 3. 把需求写成结构化合同

需求文档至少包含这些部分：

1. `requirements_contract`
2. `product_contract_matrix`
3. `fr_contract_matrix`
4. `nfr_contract_matrix`
5. `acceptance_seed_matrix`
6. `traceability_seed_matrix`
7. `out_of_scope`
8. `constraints_and_assumptions`
9. `approval`

### 4. FR 要写到“真的能做”

每条 `fr_contract_matrix` 不要只写标题。

请至少写清：

1. `fr_id`
2. `scenario_id`
3. 用户得到什么价值
4. 什么情况下触发
5. 输入是什么
6. 输出是什么
7. 失败时用户看到什么
8. 验收时应该看什么现象

可以照这个思路写：

```yaml
- fr_id: FR-01
  scenario_id: S-01
  user_value: 用户可以快速完成一次标准查询
  trigger: 用户在首页输入问题并点击发送
  input_contract:
    required_fields: [question]
    optional_fields: [filters]
  output_contract:
    required_fields: [answer, status]
  failure_semantics: 查询失败时页面保留输入，并明确提示失败原因
  acceptance_story: 用户输入有效问题后，能在一次交互内拿到清晰结果
  linked_business_goals: [BG-01]
```

### 5. NFR 不要写空话

像“体验更好”“性能更强”这种话不要单独成条。

请改写成可以观察的表述，例如：

1. 首屏判断时间 <= 3 秒
2. 占位信息数量 = 0
3. 输出字段漂移事件数 = 0

### 6. 给下游留好交接信息

`traceability_seed_matrix` 不是走形式，它是给 `/jjk-design` 和 `/jjk-plan` 用的。

每行至少写：

1. `bg_id`
2. `fr_id`
3. `scenario_id`
4. `acceptance_seed_ids`
5. `design_focus`

其中 `design_focus` 要回答一句话：

1. 设计阶段最该优先想清楚什么

## 写作风格

请按下面的风格写：

1. 先说结论，再展开
2. 少写大词，多写场景
3. 少写“优化/升级/增强”，多写“用户看到什么变化”
4. 每一节都尽量让非技术同学看得懂
5. 如果有假设，就明确写出来，不要偷偷带过去

## 不要写什么

不要在需求文档里写这些：

1. 文件路径
2. 类名、函数名
3. 表结构改法
4. 技术分层
5. 任务拆解
6. 实现步骤

这些内容留给 `/jjk-design`。

## 完成后顺手检查

写完后自己快速检查一遍：

1. 用户为什么要这个能力，是否说清了
2. 有没有流程图
3. 每条 FR 是否能被验收
4. `out_of_scope` 是否明确
5. 下游看到这份文档，能不能开始做设计

## 下一步

完成后，下一步建议进入：

1. `/jjk-design`

---
*目标不是“把需求写长”，而是“把事情写具体，让设计阶段不用重新猜”。*
