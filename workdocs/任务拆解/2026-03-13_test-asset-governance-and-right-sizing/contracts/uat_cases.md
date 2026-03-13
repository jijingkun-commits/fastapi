# 测试资产治理与单元测试收口 UAT 用例

> 适用范围：验证测试资产是否已经按“正式回归 / 脚本型链路验证 / 历史兼容入口”三类角色完成收口。
> 对应实施计划：`workdocs/任务拆解/2026-03-13_test-asset-governance-and-right-sizing/contracts/implementation_plan.md`

## UAT 总体说明

- 验收角色：后端开发者、测试执行者、评审者、仓库维护者
- 验收方式：文档核对 + 默认 pytest 收集验证 + 轻量治理门禁 + 脚本型验证入口核对
- 非目标：本轮不验证前端 E2E 目录重构，不验证业务逻辑新增能力

## UAT Cases

### TC-01 三类资产角色对人可见

- 关联需求：`FR-01`、`FR-05`
- 关联任务：`T-01`
- 验收角色：评审者
- 前置条件：
  - `T-01` 已完成
- 用户操作：
  1. 阅读 `测试用例库.md`、`测试指南与环境配置.md`、`脚本链路证据注册表.md`
  2. 查看是否能直接找到 `formal_regression`、`scripted_flow`、`compatibility_entry` 三类角色
  3. 再查看受影响产品文档，确认不再把问题文件直接当唯一入口
- 期望结果：
  - 三类角色定义清楚，且各自有 canonical owner
  - 产品文档的测试入口引用与治理文档口径一致
- 证据：
  - `rg -n "formal_regression|scripted_flow|compatibility_entry|canonical" docs/开发文档/测试管理/测试用例库.md docs/开发文档/测试管理/测试指南与环境配置.md docs/开发文档/测试管理/脚本链路证据注册表.md`
  - `rg -n "TODO-TC-004|QS-TC-001|脚本型链路验证|正式回归" docs/产品文档/待办助手需求.md docs/产品文档/问数助手需求.md`
- acceptance_cmd_ref:
  - `T-01.acceptance_cmds[0]`
  - `T-01.acceptance_cmds[1]`

### TC-02 脚本型资产退出默认 pytest 发现路径

- 关联需求：`FR-03`
- 关联任务：`T-02`
- 验收角色：测试执行者
- 前置条件：
  - `T-01`、`T-02` 已完成
- 用户操作：
  1. 查看 `scripts/verify/` 下的脚本型资产
  2. 查阅脚本链路证据注册表，确认每条脚本都有前置条件、命令、期望产物和失败判定
  3. 对照原问题文件，确认它们已不再作为默认 pytest 正式回归入口
- 期望结果：
  - 真实依赖探针仍然可执行，但角色明确为脚本型链路验证
  - 默认 pytest 入口不再把这些脚本当正式回归收集
- 证据：
  - `rg -n "scripts/verify/|前置条件|期望产物|失败判定" docs/开发文档/测试管理/脚本链路证据注册表.md docs/开发文档/测试管理/测试指南与环境配置.md`
  - `rg -n "^if __name__ == \"__main__\":|def test_" scripts/verify/*.py`
- acceptance_cmd_ref:
  - `T-02.acceptance_cmds[0]`
  - `T-02.acceptance_cmds[1]`

### TC-03 正式回归默认只认 canonical suite

- 关联需求：`FR-01`、`FR-06`
- 关联任务：`T-03`、`T-05`
- 验收角色：仓库维护者
- 前置条件：
  - `T-03`、`T-05` 已完成
- 用户操作：
  1. 先执行 `bash scripts/repo_python.sh`
  2. 再执行默认 canonical suite 的 collect-only
  3. 查看 `pyproject.toml` 和测试指南里的默认命令
- 期望结果：
  - 默认 pytest 入口收敛到 `tests`
  - 迁移后的正式回归均在 `tests/unit|api|integration` 下可被收集
  - `app/tests` 不再作为正式回归主入口出现在默认命令中
- 证据：
  - `bash scripts/repo_python.sh`
  - `bash scripts/pytest_targeted.sh --collect-only -q tests`
  - `rg -n 'testpaths = \\["tests"\\]' pyproject.toml`
- acceptance_cmd_ref:
  - `T-03.acceptance_cmds[0]`
  - `T-03.acceptance_cmds[1]`
  - `T-05.acceptance_cmds[1]`

### TC-04 重复壳和弱测试已被收口

- 关联需求：`FR-02`、`FR-04`
- 关联任务：`T-04`
- 验收角色：评审者
- 前置条件：
  - `T-04` 已完成
- 用户操作：
  1. 查看待办语义相关 canonical owner 是否只剩一个
  2. 检查原兼容壳是否已退役
  3. 检查原打印式/返回布尔值 pytest 资产是否已重写或降级到脚本验证
- 期望结果：
  - 重复兼容壳不再被收集
  - 正式回归里不再保留明显弱断言入口
- 证据：
  - `bash scripts/pytest_targeted.sh --collect-only -q tests/unit/test_todo_nodes.py`
  - `bash scripts/pytest_targeted.sh tests/unit/test_todo_nodes.py -q`
  - `rg -n "return all\\(|print\\(|if __name__ == \"__main__\":" tests/unit/test_todo_multiround_contract.py scripts/verify/todo_multiround.py`
- acceptance_cmd_ref:
  - `T-04.acceptance_cmds[0]`
  - `T-04.acceptance_cmds[1]`
  - `T-04.acceptance_cmds[2]`

### TC-05 治理门禁能阻止坏模式回流

- 关联需求：`FR-02`、`FR-07`
- 关联任务：`T-05`
- 验收角色：仓库维护者
- 前置条件：
  - `T-05` 已完成
- 用户操作：
  1. 运行测试资产治理 contract test
  2. 查看 `pyproject.toml` 默认入口是否已经切换
  3. 确认测试指南中的默认命令与实际入口一致
- 期望结果：
  - 轻量治理门禁能检查默认入口、重复壳和弱测试回流
  - 默认执行命令和 canonical suite 口径一致
- 证据：
  - `bash scripts/pytest_targeted.sh tests/unit/test_test_asset_governance_contract.py -q`
  - `bash scripts/pytest_targeted.sh --collect-only -q tests`
  - `rg -n 'testpaths = \\["tests"\\]' pyproject.toml`
- acceptance_cmd_ref:
  - `T-05.acceptance_cmds[0]`
  - `T-05.acceptance_cmds[2]`
  - `T-05.acceptance_cmds[1]`

## UAT 通过标准

1. 五条 UAT 用例全部通过。
2. 任意验收者都能明确回答：哪些资产属于正式回归，哪些属于脚本型链路验证，哪些只是兼容入口。
3. 默认 pytest 执行口径与文档口径一致，不再需要口头补充“这个文件虽然叫 test 但别算它”。
4. 至少一条治理门禁能自动发现脚本回流、重复 owner 或弱断言回流。
