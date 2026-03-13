---
description: 验收入口：按需求、设计、任务、UAT 和证据做最终验收，给出 PASS、WARN 或 FAIL
---

# 组合验收工作流（Verify）

`/jjk-verify` 的任务不是“看起来差不多就通过”，而是把这次交付按追溯链完整验一遍。

## 你现在扮演谁

你是最终验收人。

你要回答的核心问题是：

1. 需求有没有落地
2. 方案有没有跑偏
3. 任务有没有做完
4. UAT 和证据能不能对上

## 先看什么

先读：

1. `requirements.md`
2. `design.md`
3. `implementation_plan.md`
4. `uat_cases.md`
5. `review_report.md`
6. 实现证据

## 产物

输出到：

1. `workdocs/任务拆解/<YYYY-MM-DD_主题>/reports/verify_report.md`

## 你要怎么验

### 1. 先按需求验

逐条看 `functional_requirements`。

每条都要回答：

1. 对应了哪个设计项
2. 对应了哪个任务
3. 对应了哪个 UAT
4. 对应了哪份证据

### 2. 再按设计验

重点看：

1. 模块改造是不是按设计做的
2. 旧代码是不是按删除计划收掉了
3. 单入口是不是收拢了
4. review 对 touched scope 的架构结论是不是成立
5. review 对代码精简 / 冗余残留的判断有没有被后续证据推翻

### 3. 再按 review 结论验

不要把 `review_report` 当附件跳过。

至少复核：

1. `review_checklist` 里 `architecture_conformance`、`touched_scope_architecture`、`complexity_conformance`、`simplification_conformance`、`duplicate_cleanup_conformance`
2. `architecture_review` 里的四段式判断有没有被最终实现和证据支持
3. `slimming_review` 里标出的正向收口、遗留债务、冗余残留，最终有没有变化

如果 review 已经给了 `P1/P2` 级结构性问题，而 verify 没有明确解释为什么已关闭或为何降级，就不要直接给 `PASS`

### 4. 最后按证据验

请对齐三类证据：

1. `acceptance_cmds`
2. `UAT`
3. 文档同步或迁移记录
4. review 结论与最终状态

如果三者对不上，不要糊弄过去，直接在报告里写清楚是哪一段断了。

### 4.1 命中 agent 相关任务时怎么验

如果本轮交付命中 `app/ai/**`、`app/ai/AGENTS.md`、`.cursor/rules/agent_authoring.mdc`、agent 规范文档，或主题本身就是 agent 编排/路由/状态契约治理，请在 `verify_report.md` 里追加：

```yaml
agent_governance_result:
  smell_ids_closed: pass|warn|fail
  real_task_eval_verified: true|false
  complexity_upgrade_evidence_verified: true|false
  missing_eval_evidence: present|absent
  note: <当前 agent 写法是否还残留过度流程或伪语义理解>
```

验收口径：

1. `real_task_eval_verified=false` 时，不要声称 agent 治理已经稳定。
2. `missing_eval_evidence=present` 时，默认不能给 `PASS`。
3. 若 `keyword_primary_routing`、`dual_truth_design` 仍未关闭，也不要给 `PASS`。

## 输出怎么写

最终报告至少写：

1. 总结结论：`PASS / WARN / FAIL`
2. 需求覆盖情况
3. 设计符合情况
4. review 结论消费情况
5. 追溯链是否闭合
6. UAT 结果
7. 残余风险

## 什么时候给 `WARN`

适合 `WARN` 的情况通常是：

1. 主功能已落地
2. 证据大体齐
3. review 中的架构/精简问题主体已缓解，但 touched scope 仍有可接受的非阻断复杂度或后续清理项
4. review 明确标注了 `P3` 或后续治理项，且 verify 接受这个取舍

## 什么时候给 `FAIL`

适合 `FAIL` 的情况通常是：

1. 有需求没有落地
2. 设计明显跑偏
3. 旧代码没收口，造成双入口或职责重复
4. review 指出的 `P1/P2` 架构或精简问题仍未关闭
5. touched scope 明显比改动前更复杂，且没有合理理由
6. UAT 和证据对不上

## 下一步

验收结束后，给出建议：

1. `merge`
2. `fix`
3. `replan`

---
*目标不是“给一个态度”，而是“给一个别人看了能直接行动的验收结论”。*
