# 知识库检索P2交付工作流强管控设计说明

## 1. 需求澄清结论
- 目标:
  - 将“代码完成但验证结论不稳定”的现状，升级为可重复、可审计、可回放的交付工作流。
  - 对 `PP-20260301-KB-RETRIEVAL-P2` 建立统一门禁：本地验证、证据落盘、集成校验、CI 复核四段闭环。
- 范围:
  - 仅覆盖知识库检索 P2 的交付流程与验证流程，不改业务能力目标。
  - 覆盖对象包含：本地命令入口、门禁脚本编排、卡片 merge 证据链、CI 触发链路、文档化运行手册。
- 边界:
  - 不重构 `ragflow_tool`、`multi_agent_graph` 等业务逻辑实现。
  - 不改变 `vk_cards` 的业务任务拆解顺序（仍以 C01~C07 + G01 为主）。
  - 不引入新的任务系统，仅在现有 `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>` 与 `scripts/*` 体系上收敛。
- 成功标准:
  - 同一分支、同一输入下，本地与 CI 的验证结论一致。
  - `check_integration_gate` 在进入集成验收前即可自动识别缺失证据并阻断。
  - 所有实现卡（C01~C07）有可追溯 `merge_result.json`，且与基线可见性一致。
  - 开发者不需要记忆隐性参数（如 `PYTHONPATH`），统一入口即可完成完整验证。

## 2. 最终方案
- 方案描述:
  - 采用“强管控分层门禁”方案，形成 **L0 本地预检 -> L1 证据完整性 -> L2 集成门禁 -> L3 CI 复核** 的串行流程。
  - 每层均定义明确输入、输出和人工闸门；任一层失败立即停止，不允许跳层验收。
- 关键决策:
  - 决策 1：统一验证入口，新增单一脚本作为唯一推荐入口，内置 `PYTHONPATH`、测试命令、文档门禁、合同一致性校验。
  - 决策 2：将 `merge_result.json` 作为“实现已合并”的唯一证据，不再接受口头或临时截图作为替代。
  - 决策 3：将 `check_integration_gate.py` 前移到日常流程，避免只在最终阶段才暴露证据链缺失。
  - 决策 4：CI 新增专用 Workflow，对 P2 关键门禁进行独立复核并产出结构化总结。
  - 决策 5：保留人工 Stop/Go 节点，要求每阶段通过后再进入下一阶段，符合“分步执行 + 人工检测/测试/评估”。

## 3. 决策权衡
- 放弃路径:
  - 仅补几条命令说明，不改流程。
  - 只做本地门禁，不接入 CI。
  - 等全部开发完成后一次性补证据与门禁。
- 放弃原因:
  - 命令说明无法约束执行顺序，仍会出现“本地绿、集成红”的反复返工。
  - 无 CI 复核无法保证团队一致性，易产生环境差异误判。
  - 证据后补会破坏时序可追溯性，无法可靠定位责任边界与回归来源。

## 4. 设计概要
- 架构:
  - 工作流控制面：`scripts/` 下的门禁脚本 + 统一验证入口脚本。
  - 证据数据面：`docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json::merge_results.<card_id>`、`task-runner-state.json`。
  - 审计与展示面：`docs/内部参考/任务拆解/*` 与 CI Summary。
- 组件:
  - `scripts/coder4/check_integration_gate.py`：校验 merge 证据存在性、提交可见性、状态一致性。
  - `scripts/check_gate_contract_consistency.py`：校验 `vk_cards / parallel_plan / implementation_plan` 契约一致。
  - `scripts/docs_guard.py`：文档合规与链接完整性门禁。
  - `wt-flow` / 卡片执行链：负责在实施卡完成时落盘 `merge_result.json`。
  - 新增统一入口脚本（设计项）：封装 `PYTHONPATH` 与标准验证链。
  - 新增 CI Workflow（设计项）：执行同一套标准命令并输出汇总。
- 数据流:
  - Step 1（开发者本地）：统一入口脚本启动，执行 unit tests + docs guard + contract consistency。
  - Step 2（证据检查）：读取 `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>`，确认 C01~C07 的 `merge_result.json` 完整且格式正确。
  - Step 3（集成门禁）：`check_integration_gate.py` 验证每个 merge commit 对基线可见。
  - Step 4（CI 复核）：PR/手动触发 CI 复跑同链路并输出结论，结论回写 PR summary。
  - Step 5（人工闸门）：负责人审阅阶段报告，确认“结论+证据+剩余风险”后再推进。
- 异常与测试考虑:
  - 环境异常：若直接 `pytest` 报 `ModuleNotFoundError: app`，统一入口脚本必须屏蔽该类误用。
  - 证据缺失：若缺任一卡 `merge_result.json`，流程在 L1 阶段硬阻断。
  - 基线漂移：若 merge commit 非 baseline 可见祖先，L2 阶段硬阻断并输出卡片 ID。
  - 契约漂移：三份契约任一不一致，L0 直接失败，禁止进入实施验收。
  - 回归策略：先跑失败点最小回归，再跑 `tests/unit` 全量，最后跑流程门禁。

## 5. 分阶段执行与人工闸门
- 阶段 S1（统一入口落地）:
  - 交付：统一验证入口脚本与使用说明。
  - 人工闸门：验证“同命令同结果”（至少两次独立运行）。
- 阶段 S2（证据链自动化）:
  - 交付：实现卡完成后自动生成 `merge_result.json`，并在缺失时给出可操作报错。
  - 人工闸门：抽检至少 2 张卡，确认证据文件字段与路径正确。
- 阶段 S3（集成门禁前移）:
  - 交付：开发阶段默认执行 `check_integration_gate`，不再仅终态执行。
  - 人工闸门：确认 C01~C07 的状态与基线可见性一致。
- 阶段 S4（CI 强制复核）:
  - 交付：新增 Workflow，固定执行门禁链并产出 Summary。
  - 人工闸门：PR 审核必须包含 CI 通过记录与风险备注。

## 6. 落地约束与验收口径
- 约束:
  - 统一入口是默认执行入口，临时散命令不作为验收依据。
  - `merge_result.json` 缺失或无效即视为“未完成合并证据”。
  - 任何阶段失败必须先修复再推进，不允许跨阶段“先过后补”。
- 验收口径:
  - 本地：`unit + docs + contract + integration_gate` 全部通过。
  - CI：复跑同链路且结论一致。
  - 文档：流程说明与门禁入口在项目文档可检索、可执行。

## 7. 未决问题（如有）
- [ ] CI 触发策略采用 `pull_request` 还是 `workflow_dispatch + pull_request` 双模式。
- [ ] `merge_result.json` 是否需要补充签名字段（如执行人/会话号）用于审计增强。
- [ ] 是否引入“仅验证变化卡片”的增量模式以缩短等待时间。

## 8. 审批记录
- design_approved: true
- approved_at: 2026-03-04 10:44
- approved_round: round-4（用户明确指定“按方案C”）
