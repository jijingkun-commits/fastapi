# 测试资产治理与单元测试收口 Review Report

> 日期：2026-03-14  
> 主题：`2026-03-13_test-asset-governance-and-right-sizing`

## 1. 结论

| 维度 | 结论 | 说明 |
| --- | --- | --- |
| 总体 review 结论 | PASS | 本轮 review 后未剩余 `P1/P2` 阻断项 |
| 需求对齐 | PASS | 正式回归 / 脚本验证 / 兼容入口三类角色已经收口到明确 owner |
| 设计对齐 | PASS | `tests/` 作为 canonical pytest 主入口、`scripts/verify/` 作为脚本型验证承载已经落地 |
| 精简收口 | PASS | `app/tests` 默认入口退出、重复兼容壳删除、旧脚本路径批量迁出 |
| review 衍生补修 | DONE | review 过程中发现并修复了旧 runner 路径残留与文档历史口径残留 |

## 2. 映射

- `task_ids`: `T-01`、`T-02`、`T-03`、`T-04`、`T-05`
- `requirement_ids`: `FR-01`、`FR-02`、`FR-03`、`FR-04`、`FR-05`、`FR-06`、`FR-07`
- `nfr_ids`: `NFR-01`、`NFR-02`、`NFR-03`、`NFR-04`、`NFR-05`、`NFR-06`
- `design_item_refs`: `D-01`、`D-02`、`D-03`、`D-04`、`D-05`
- `touched_scope`: `pyproject.toml`、`tests/**`、`scripts/verify/**`、`tests/run_master_test_suite.py`、测试治理文档与受影响产品文档

## 3. Findings

本轮最终状态下，**无剩余阻断 findings**。

review 过程中识别出的两处真实问题，已经在本轮关闭：

1. `tests/run_master_test_suite.py` 仍引用已迁走的 `tests/test_*.py` 脚本路径，属于旧入口未收干净。
2. `docs/开发文档/测试管理/测试用例库.md` 的 `3.1` 小节仍把 `app/tests + tests` 历史命令和旧统计写成当前口径，属于文档真理源未收口。

## 4. Review Checklist

```yaml
review_checklist:
  architecture_conformance: pass
  touched_scope_architecture: pass
  complexity_conformance: pass
  simplification_conformance: pass
  duplicate_cleanup_conformance: pass
```

## 5. Architecture Review

| 项 | 结论 | 说明 |
| --- | --- | --- |
| 模块边界 | PASS | 正式回归 owner 收敛到 `tests/`，脚本型验证 owner 收敛到 `scripts/verify/`，文档 owner 继续留在测试治理文档 |
| 依赖方向 | PASS | 当前是“角色规则 -> canonical 入口 -> 执行命令 -> 文档追溯 -> 文件承载”，没有再让旧路径反向决定口径 |
| 状态归属 | PASS | `pyproject.toml` 决定默认收集入口，治理 contract test 决定防回流门禁，脚本注册表决定脚本型验证真理源 |
| 错误处理责任 | PASS | pytest 资产继续靠断言失败；脚本型验证补上了可执行入口与退出语义，至少不再以“只打印日志也算过”冒充正式门禁 |

## 6. Slimming Review

### 正向收口

- `app/tests` 已退出默认 pytest 主入口，当前 worktree 中该目录已不存在。
- 重复兼容壳 `tests/unit/test_todo_graph_semantic_guard.py` 已删除。
- 脚本型 `test_*.py` 已迁到 `scripts/verify/`，不再占用 pytest 默认发现路径。
- `tests/run_master_test_suite.py` 已改为调度 `scripts/verify/*.py` canonical 路径，并摆脱 `cwd` 依赖。
- `tests/unit/test_test_asset_governance_contract.py` 已补一条 runner 路径防回流门禁。

### 非阻断遗留

- `docs/内部参考/**` 等历史归档材料仍会出现旧 `app/tests` 路径。这些属于归档/历史证据，不是当前真理源，不构成本轮阻断。
- `web/e2e` 统计仍缺一次带 `node_modules` 的 `pnpm test --list` 真正核对；当前文档已显式标成“待刷新”，没有继续伪装成最新实测值。

## 7. 证据摘要

- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_test_asset_governance_contract.py -q` -> `5 passed`
- `python -m py_compile tests/run_master_test_suite.py` -> `PASS`
- `python -m py_compile scripts/verify/todo_multiround.py` -> `PASS`
- `python scripts/verify/todo_multiround.py` -> `exit_code=0`
- `rg` 复核显示稳定文档已改用 `tests/` / `scripts/verify/` canonical 入口

## 8. Review Summary

这次改动没有把 touched scope 变复杂，反而把最容易误导执行者的几条旧路径真正收掉了。  
当前建议进入 `$jjk-verify`，可以按“当前实现已满足放行条件，但保留非阻断环境说明”的口径做最终验收。
