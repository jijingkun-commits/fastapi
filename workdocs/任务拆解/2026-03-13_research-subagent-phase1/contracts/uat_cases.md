# 统一 `research_subagent` 一期 UAT 用例

> 适用范围：验证 `knowledge + web` 多来源研究任务已经通过统一 `research_subagent` 执行，且主会话 owner、附件 planning、知识库图文展示都满足一期合同。
> 对应实施计划：`workdocs/任务拆解/2026-03-13_research-subagent-phase1/contracts/implementation_plan.md`

## UAT 总体说明

- 验收角色：产品/设计、后端开发、前端验收人员
- 验收方式：真实对话操作 + 历史回放核对 + 轻量命令证据
- 非目标：本轮不验证 `todo` 和核心 `data` 是否已改造成 subagent；它们应该保持 workflow

## UAT Cases

### TC-RS-01 单次知识库直查保持简单路径

- 关联需求：`FR-02`
- 关联任务：`T-01`、`T-03`
- 验收角色：产品/设计
- 前置条件：
  - 已配置可用知识库
  - `T-01`、`T-03` 已完成
- 用户操作：
  1. 在聊天中输入“公司请假流程是什么？”
  2. 观察流式状态和最终回复
  3. 刷新历史后再看同一条消息
- 应看到的结果：
  - 请求按单次查询处理，不升级成复杂 research 链路
  - 回复简洁，能直接给出知识库答案
  - 历史回放与当轮展示一致
- 证据：
  - 前端录屏
  - `bash scripts/pytest_targeted.sh tests/unit/test_research_goal_resolver.py tests/unit/test_research_dispatch_contract.py -q`
- acceptance_cmd_ref:
  - `T-01.acceptance_cmds[0]`
  - `T-03.acceptance_cmds[0]`

### TC-RS-02 多来源研究进入统一 research_subagent

- 关联需求：`FR-03`、`FR-07`
- 关联任务：`T-01`、`T-02`、`T-03`
- 验收角色：后端开发
- 前置条件：
  - 知识库与联网搜索都可用
  - `T-01`、`T-02`、`T-03` 已完成
- 用户操作：
  1. 输入“综合知识库和网页资料，帮我对比两种报销口径的差异”
  2. 观察事件流与最终回复
  3. 检查回复是否仍由主助手统一收口
- 应看到的结果：
  - 进入统一 `research_subagent` 执行
  - 主会话拿到的是结论、证据和不足项，而不是原始搜索过程
  - 最终答复 owner 仍然是主会话，不出现“换了个助手接管”的体验
- 证据：
  - 对话截图
  - `bash scripts/pytest_targeted.sh tests/unit/test_research_subagent.py tests/unit/test_research_dispatch_contract.py -q`
- acceptance_cmd_ref:
  - `T-02.acceptance_cmds[0]`
  - `T-03.acceptance_cmds[0]`

### TC-RS-03 附件不因存在而自动进入 research

- 关联需求：`FR-01`、`FR-06`
- 关联任务：`T-01`、`T-04`
- 验收角色：产品/设计
- 前置条件：
  - 可上传 Excel 或 CSV 附件
  - `T-01`、`T-04` 已完成
- 用户操作：
  1. 上传一个 Excel 文件
  2. 输入“把这个 Excel 里的贷款余额按分行统计一下”
  3. 观察最终路由行为
- 应看到的结果：
  - 附件进入 data 路由，而不是因为“带附件”误入 research
  - 回复表现为数据分析结果，而不是研究总结
- 证据：
  - 对话截图
  - `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_chat_service_human_attachment_persistence.py -q`
- acceptance_cmd_ref:
  - `T-04.acceptance_cmds[0]`

### TC-RS-04 知识库研究图文展示不退化

- 关联需求：`FR-05`
- 关联任务：`T-02`、`T-05`
- 验收角色：前端验收人员
- 前置条件：
  - 知识库中存在带图片的资料
  - `T-02`、`T-05` 已完成
- 用户操作：
  1. 发起一个会命中带图知识库资料的研究请求
  2. 观察当轮 live 展示
  3. 刷新历史后再查看同一条消息
- 应看到的结果：
  - live 与 history 都能看到文图结合结果
  - 不出现“当轮有图、刷新后没图”或“只剩文字不见图”
  - 图片失败时也至少保留文本和证据，不是整条结果消失
- 证据：
  - 前端录屏
  - `bash scripts/pytest_targeted.sh tests/unit/test_message_display_blocks.py tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_repo_serialization.py tests/api/test_chat_api.py -q`
- acceptance_cmd_ref:
  - `T-05.acceptance_cmds[0]`

### TC-RS-05 证据不足时主会话正确降级

- 关联需求：`FR-04`、`FR-07`
- 关联任务：`T-02`、`T-05`
- 验收角色：产品/设计
- 前置条件：
  - 知识库或网页源存在证据不足场景
  - `T-02`、`T-05` 已完成
- 用户操作：
  1. 输入一个知识库和网页都缺证据的研究问题
  2. 观察最终答复
- 应看到的结果：
  - 能明确看到不足说明
  - 不会把原始网页噪声或工具报错直接甩给用户
  - 主会话仍能给出结果性降级提示
- 证据：
  - 对话截图
  - `bash scripts/pytest_targeted.sh tests/unit/test_research_subagent.py tests/unit/test_research_dispatch_contract.py tests/unit/test_chat_service_done_payload.py -q`
- acceptance_cmd_ref:
  - `T-02.acceptance_cmds[0]`
  - `T-05.acceptance_cmds[0]`

### TC-RS-06 稳定文档与过程合同一致

- 关联需求：`FR-01`、`FR-03`、`FR-05`、`FR-06`、`FR-07`
- 关联任务：`T-06`
- 验收角色：架构评审者
- 前置条件：
  - `T-06` 已完成
- 用户操作：
  1. 阅读 `AI模块设计.md`
  2. 阅读 `聊天系统需求.md`
  3. 对照 `requirements.md` 与 `implementation_plan.md`
- 应看到的结果：
  - 稳定文档和过程文档对 `research_subagent` 的范围、owner 和附件边界口径一致
  - 能顺着追溯矩阵找到设计、任务和验收命令
- 证据：
  - 文档截图
  - `rg -n "research_subagent|knowledge_search|web_research|附件|图文展示" docs/开发文档/架构设计/AI模块设计.md docs/产品文档/聊天系统需求.md workdocs/需求/2026-03-13_research-subagent-phase1/requirements.md`
- acceptance_cmd_ref:
  - `T-06.acceptance_cmds[0]`

## UAT 通过标准

1. 六条 UAT 用例全部通过。
2. 简单知识/联网查询没有被误升级为 research。
3. 多来源研究任务已经稳定走统一 `research_subagent`，且主会话 owner 不变。
4. 带附件的数据类请求不会被误送入 research。
5. 知识库图文展示在 research 场景下 live 与 history 不退化。

