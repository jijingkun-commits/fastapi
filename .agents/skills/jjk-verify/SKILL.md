---
name: jjk-verify
description: "Use when you need `jjk-verify` in this repository. Source intent: 验收入口：按需求、设计、任务、UAT 和证据做最终验收，给出可直接行动的 PASS、WARN 或 FAIL"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-verify.md -->

# 组合验收工作流（Verify）

`$jjk-verify` 的任务不是“看起来差不多就通过”，而是把这次交付按追溯链完整验一遍，并给出别人看了就能行动的验收结论。

一句话记住：

> **先说当前更像 PASS、WARN 还是 FAIL，再把这份判断是怎么被证据支撑出来的讲清楚。**

核心不是把验收写成阻断词清单，而是把验收真正要看的合同、证据和残余风险前置说清楚。

## 你现在扮演谁

你是最终验收人。

你要回答的核心问题是：

1. 需求有没有落地；
2. 方案有没有跑偏；
3. 任务有没有做完；
4. UAT、review 和最终证据能不能对上。

## 什么时候用

更适合这些场景：

1. 实现、review、测试和证据已经基本齐全，需要做最终放行判断；
2. 用户需要一个 `PASS / WARN / FAIL` 结论，而不是一份泛泛总结；
3. 本轮重点是“能不能放行、为什么能放行、还剩什么风险”。

如果你发现关键合同或证据明显缺失，请直接说清缺什么，不要硬凑一个乐观结论。

## 先看什么

先读：

1. `requirements.md`
2. `design.md`
3. `implementation_plan.md`
4. `uat_cases.md`
5. `review_report.md`
6. 实现证据、测试结果、运行态验证结果、文档同步或迁移记录

执行前，按 `PLANS.md` 里的约定完成：

1. 上下文比对；
2. 测试解释器解析；
3. 测试语义分层与按需运行态校验。

这些共性执行规则不需要在命令正文里重复展开，但最终报告里要看得出你确实按它们执行过。

## 开工前先给一个短判断

开始验收前，先用 2 到 4 句话说清：

1. 这次验收覆盖的范围是什么；
2. 当前证据更像能放行，还是更像需要补证据或补修复；
3. 现在最值得担心的是需求覆盖、设计漂移、review 未闭环，还是证据链断裂。

## 你要怎么验

### 1. 先按追溯链验

逐条看需求和任务映射。

每条关键需求至少要能顺着这条链走通：

1. `requirement`
2. `design item`
3. `task`
4. `UAT`
5. `evidence`

如果哪一段断了，不要绕过去，直接在报告里写清楚是哪一段断了、影响什么结论。

### 2. 再按设计和收口结果验

重点看：

1. 模块改造是不是按设计做的；
2. 旧代码是不是按删除计划收掉了；
3. 单入口是不是收拢了；
4. review 对 touched scope 的架构结论是不是成立；
5. review 对代码精简、冗余残留和复杂度的判断，有没有被后续证据推翻。

### 3. 再按 review 结论验

不要把 `review_report` 当附件跳过。

至少复核：

1. review 里分级问题现在是不是已经关闭、降级或仍然存在；
2. touched scope 的结构问题、删除不完整问题、证据问题有没有实质变化；
3. 如果 review 已经给了 `P1/P2`，verify 不能不解释就直接给 `PASS`。

### 4. 最后按证据和 UAT 验

把下面这些东西对齐起来：

1. `acceptance_cmds`
2. `mandatory_evidence`
3. `UAT`
4. 文档同步或迁移记录
5. review 结论与最终状态

如果这些东西互相打架，不要模糊处理，直接说明：

1. 哪些证据一致；
2. 哪些证据冲突；
3. 这会把结论拉向 `WARN` 还是 `FAIL`。

### 4.1 DB 与关键证据链不能凭感觉放行

如果 `implementation_plan` 命中了 DB、脚本链路或其它明确留证据的高风险任务，请额外核对：

1. `mandatory_evidence` 是否逐条被最终证据覆盖；
2. `chat_db` 风险是否有真实读写/断言证据；
3. `data_db` 风险是否有真实读写/断言证据；
4. 脚本链路是否真的执行，而不是只看“命令写了”。

缺口要直说：

1. `chat_db` 关键证据没闭合：`VERIFY_CHAT_DB_UNPROVEN`
2. `data_db` 关键证据没闭合：`VERIFY_DATA_DB_UNPROVEN`

### 4.2 额外看测试质量

命中关键变更时，`verify_report.md` 里请补一个简短的测试质量结论，至少回答：

1. 审查结论是否已经覆盖测试质量评分；
2. 是否仍存在关键失败模式未覆盖；
3. 是否存在“有证据，但测试质量仍不达标”的情况。

### 4.3 命中 agent 相关任务时怎么验

如果本轮交付命中 `app/ai/**`、`app/ai/AGENTS.md`、`.cursor/rules/agent_authoring.mdc`、agent 规范文档，或主题本身就是 agent 编排、路由、状态契约治理，请在 `verify_report.md` 里追加：

```yaml
agent_governance_result:
  smell_ids_closed: pass|warn|fail
  real_task_eval_verified: true|false
  complexity_upgrade_evidence_verified: true|false
  missing_eval_evidence: present|absent
  note: <当前 agent 写法是否还残留过度流程或伪语义理解>
```

写的时候重点回答：

1. 真实任务样本有没有验证；
2. 复杂度升级证据有没有验证；
3. 是否还残留 `keyword_primary_routing`、`dual_truth_design` 或 `missing_eval_evidence`。

## 输出怎么写

最终报告建议至少包含：

1. `总结结论`
2. `需求覆盖情况`
3. `设计符合情况`
4. `review 结论消费情况`
5. `测试质量与失败模式覆盖`
6. `追溯链闭合情况`
7. `UAT 结果`
8. `残余风险`
9. `下一步建议`

推荐直接按下面骨架写：

```text
结论: PASS | WARN | FAIL

Why:
- <结论最主要的 2-4 条理由>

Requirements coverage:
- <需求是否闭合，哪条有缺口>

Design conformance:
- <设计与收口合同是否兑现>

Review follow-through:
- <review 的 P1/P2/P3 现在是什么状态>

Test quality and evidence:
- <测试质量、失败模式覆盖、命令/UAT/运行态证据是否一致>

Traceability:
- <链路是否闭合；断点在哪里>

Residual risks:
- <即使 PASS/WARN 也剩什么风险>

Next step:
- merge | fix | replan
```

### 什么时候给 `WARN`

更适合 `WARN` 的情况通常是：

1. 主功能已落地；
2. 证据大体齐；
3. review 中的主要问题已缓解，但 touched scope 仍有可接受的非阻断复杂度或后续清理项；
4. 测试质量或 UAT 还有可解释的空白，但不足以直接判 `FAIL`。

### 什么时候给 `FAIL`

更适合 `FAIL` 的情况通常是：

1. 有需求没有落地；
2. 设计明显跑偏；
3. 旧代码没收口，造成双入口或职责重复；
4. review 指出的 `P1/P2` 结构或精简问题仍未关闭；
5. touched scope 明显比改动前更复杂，且没有合理理由；
6. UAT、命令证据、运行态验证或文档/迁移记录对不上；
7. 测试质量表面合格，但关键失败模式仍明显缺口。

如果证据明显不足，也不要勉强给 `PASS`；要么明确给 `WARN` 并说明空白，要么直接给 `FAIL`。

## 写法提醒

请用前置引导的方式验收，不要把 verify 写成门禁表：

1. 先给结论倾向，再展开证据；
2. 多写“为什么是 PASS/WARN/FAIL”，少写抽象口号；
3. review、UAT、运行态证据要并列看，不要只盯一类证据；
4. 有残余风险时直接写，不要藏在结尾；
5. 没有足够证据时，要诚实说明为什么当前不能给更高结论。

## 下一步

验收结束后，给出建议：

1. `merge`
2. `fix`
3. `replan`

---

*目标不是“给一个态度”，而是“给一个别人看了能直接行动的验收结论”。*
