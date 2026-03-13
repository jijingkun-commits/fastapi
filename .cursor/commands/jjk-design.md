---
description: 技术方案入口：基于 requirements 和现有代码写出能落地的 design 文档，包含最佳实践判断、技术图、模块改造清单、删除清单和实现种子
---

# 技术方案工作流（Technical Design）

`/jjk-design` 的任务是回答四个问题：

1. 系统到底改哪里
2. 为什么这样改
3. 旧代码哪些该删、哪些保留
4. `/jjk-plan` 接下来该怎么拆

## 你现在扮演谁

你是技术负责人 + 架构师 + 文档作者。

你的工作不是直接写代码，而是先把方案写到“别人照着就能拆任务”的程度。

## 开工前先做两件事

### 1. 读输入

先读：

1. `requirements.md`
2. 相关代码
3. 相关架构/接口文档
4. 已有同主题设计文档

默认检索范围：

1. 先看 `workdocs/需求/`、`workdocs/设计/`、`docs/开发文档/`、相关代码
2. 默认排除 `.artifacts/**` 与 `workdocs/归档/**`
3. 只有当前主题在活跃层没有对应材料，或用户明确要求“参考历史方案”时，才读取 `workdocs/归档/**`

### 2. 查最佳实践

先查官方或权威资料，再定方案。

你不用长篇摘抄资料，只需要在设计文档里回答：

1. 参考了什么
2. 采用了什么
3. 没采用什么
4. 为什么这个仓库不完全照搬

## 产物

输出到：

1. `workdocs/设计/<topic>/design.md`

同时回填：

2. `workdocs/需求/<topic>/requirements.md`

至少回填这些字段：

1. `requirements_contract.design_source`
2. `requirements_contract.design_approved`
3. `requirements_contract.design_approval_evidence`
4. `requirements_contract.design_freeze_summary`
5. `requirements_contract.clarify_handoff_source`
6. `requirements_contract.clarify_handoff_version`

## 你要怎么写

### 1. 开头先给设计结论

不要先堆背景。

开头先用短段落回答：

1. 这次主方案是什么
2. 这次不选什么方案
3. 最大收益是什么
4. 最大代价是什么

### 2. 写最佳实践判断

请在文档里放一个 `best_practice_review`。

写法要像这样：

1. 来源
2. 采用点
3. 不采用点
4. 适配原因

不要只写“已参考最佳实践”，那没有任何信息量。

### 3. 给出四段式架构结论

按这个顺序写：

1. `module_boundaries`
2. `dependency_direction`
3. `state_ownership`
4. `error_handling`

每一段都回答三件事：

1. 现状哪里别扭
2. 这次怎么改
3. 明确不再怎么做

### 4. 一定要画技术图

至少放一张 Mermaid 图。

建议：

1. 模块关系用 `flowchart`
2. 请求/事件交互用 `sequenceDiagram`
3. 状态变化用 `stateDiagram-v2`

图后补一句解释：

1. 这张图在帮助谁理解什么

### 5. 把“改什么模块、为什么改”写具体

请显式写 `module_change_plan`。

每行至少包含：

1. `module`
2. `current_problem`
3. `target_change`
4. `why_this_way`
5. `affected_paths`
6. `owner`

这部分不要写成抽象口号。要让人一眼看出：

1. 哪个模块是主改
2. 哪个模块只是配合
3. 为什么不选别的改法

### 6. 把“删什么”写具体

请显式写：

1. `change_map`
2. `deletion_plan`
3. `shrink_contract`

其中：

1. `change_map` 说新增、修改、替代关系
2. `deletion_plan` 说哪些旧路径或旧职责要删，为什么删，谁接手
3. `shrink_contract` 说哪些废弃、哪些保留、单入口归谁

删除清单不要只写路径名，要补上下文。可以照这个思路写：

```yaml
- path_or_symbol: app/services/legacy_xxx.py
  current_responsibility: 旧查询聚合入口
  remove_reason: 新方案已经把入口收敛到统一 query service
  replaced_by: app/services/query_service.py
  cleanup_timing: implementation
```

### 7. 给计划阶段留“实现种子”

设计文档里请直接放：

1. `implementation_seeds`
2. `execution_chain_seed`
3. `clarify_handoff_contract`

这些不是走形式，它们是给 `/jjk-plan` 用的。

写的时候要保证：

1. 每个 `design_item` 都能落到后续任务
2. 每个 `implementation_seed` 都说清文件、符号、改动类型
3. `clarify_handoff_contract` 里能看出每条设计项对应哪条 FR

### 8. 命中数据库时，把数据库说清楚

如果这次会动数据库，就补一个 `db_migration_contract`。

请回答：

1. 动不动表结构
2. 范围多大
3. 开发态怎么迁移
4. 发布态怎么迁移
5. 回滚怎么做

## 写作风格

请按这个风格来：

1. 先说结论，再给理由
2. 少写“提升灵活性/增强扩展性”，多写真实取舍
3. 多写“现状 -> 决策 -> 影响”
4. 多写“改哪里、删哪里、保留哪里”
5. 如果有假设，写明假设，不要装作已经确定

## 不要写成什么样

不要把设计文档写成：

1. 一堆标题，没有内容
2. 一堆原则，没有模块
3. 一堆抽象词，没有路径
4. 只说新增，不说删除
5. 只说怎么改，不说为什么

## 完成后顺手检查

写完后快速问自己：

1. 别人看完，能不能知道先改哪个模块
2. 为什么这么改，是否说服人
3. 该删的旧代码有没有写出来
4. `/jjk-plan` 能不能直接从这里拆任务

## 下一步

完成后，下一步建议进入：

1. `/jjk-plan`
2. 命中 API 变化时，再接 `/jjk-api-doc-sync`

---
*目标不是“写一份看起来专业的设计文档”，而是“写一份别人真能照着做的设计文档”。*
