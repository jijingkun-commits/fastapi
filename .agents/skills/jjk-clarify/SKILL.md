---
name: jjk-clarify
description: "Use when you need `jjk-clarify` in this repository. Source intent: 需求澄清入口：只产出 requirements contract；可选 --doc 发布正式产品/需求文档"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-clarify.md -->

# 需求澄清工作流（Requirements Clarify）

`$jjk-clarify` 只负责把用户意图冻结为**纯需求**，不负责技术方案、任务拆解或实现细节。

> **中文主导**：思考与输出统一中文。
>
> **唯一目标**：回答“做什么、为什么做、做到什么算完成”。

## 产物与边界

必须产出：

1. `docs/内部参考/迭代需求/<topic>_requirements.md`

可选发布（仅显式 `--doc` 时）：

2. 对应正式产品/需求文档章节

本命令不做：

1. 不写技术方案；
2. 不写模块边界/依赖方向/状态归属；
3. 不写文件路径、函数名、任务拆解；
4. 不写 UAT 步骤；
5. 不写 `obsolete_paths` / `retained_paths` / `single_entry_owner`。

## 参数

1. `--doc`：在生成内部 `requirements.md` 的同时，发布到正式产品/需求文档；
2. `--hydrate`：对历史需求做归一化收口，但仍只输出需求层内容。

约束：

1. 不带 `--doc` 时，内部 `requirements.md` 仍必须生成；
2. `--doc` 只控制“是否发布正式文档”，不控制“是否生成需求产物”。

## 输入前置（强制）

至少提供以下信息中的最小组合：

1. 业务目标或问题陈述；
2. 目标用户或核心场景；
3. 成功标准、限制条件、显式非目标中的任意一类。

失败时：

1. 缺少业务目标：`CLARIFY_GOAL_MISSING`
2. 缺少核心场景：`CLARIFY_SCENARIO_MISSING`
3. 成功标准不可验证：`CLARIFY_SUCCESS_CRITERIA_MISSING`
4. 混入技术实现内容且无法抽离：`CLARIFY_SCOPE_POLLUTED_BY_DESIGN`

## 执行流程（强制顺序）

### 0) 上下文检查

至少检查：

1. 当前主题是否已有同名 `requirements.md`；
2. 是否存在已审批但待更新的旧需求；
3. 用户输入里哪些是需求，哪些其实是技术方案。

### 1) 冻结需求合同

`<topic>_requirements.md` 至少包含：

1. `problem_statement`
2. `target_users`
3. `core_scenarios`
4. `in_scope`
5. `out_of_scope`
6. `functional_requirements`
7. `non_functional_requirements`
8. `business_acceptance_criteria`
9. `constraints_and_assumptions`
10. `publish_product_doc`

强约束：

1. 每条 `functional_requirements` 必须可被后续 UAT 覆盖；
2. `non_functional_requirements` 不能只有“性能更好/体验更好”这类空话；
3. `out_of_scope` 不能为空；
4. 若出现文件路径、类名、表字段级改法，必须下沉到 `$jjk-design`。

### 2) 审批门禁

必须明确：

1. `requirements_approved=true|false`
2. `approved_at`
3. `approval_evidence`

若用户未确认，允许停留在 `draft`，但不得进入 `$jjk-design`。

### 3) 正式文档发布（仅 `--doc`）

1. `publish_product_doc=true` 时，按主题把需求收敛到正式产品/需求文档对应章节；
2. 不带 `--doc` 时，`publish_product_doc=false`；
3. 禁止在没有 `--doc` 的情况下修改正式产品文档；
4. 禁止用 `--doc` 替代内部 `requirements.md`。

## 输出要求（强制）

至少输出：

1. 需求结论摘要；
2. `requirements.md` 路径；
3. `requirements_approved` 状态；
4. `publish_product_doc` 状态；
5. 下一步建议（仅限 `$jjk-design`）。

## 禁止项（强制）

1. 禁止把技术方案写进需求文档；
2. 禁止把任务拆解写进需求文档；
3. 禁止把 UAT 细节写进需求文档；
4. 禁止未审批就进入 `$jjk-design`；
5. 禁止用“内部没写，但正式文档补了”替代需求真理源。

## 推荐链路

`$jjk-clarify -> $jjk-design -> $jjk-plan -> $jjk-imp -> $jjk-verify`

## 使用示例

```text
$jjk-clarify
```

```text
$jjk-clarify --doc
```

---
*使用 `$jjk-clarify` 触发。目标是“冻结纯需求”，不是“顺手把方案也写了”。*
