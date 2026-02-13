# 评估报告

## 背景
本文件用于承接当前迭代需求的评估结论，并作为 `docs/SUMMARY.md` 中“评估报告”入口的目标文档。

## 当前状态
- 状态：已更新（2026-02-13）
- 关联需求：`docs/内部参考/迭代需求/requirements.md`
- 关联实施方案：`docs/内部参考/迭代需求/implementation_plan.md`
- 关联工作包：`PP-20260213-SKILL-RETRIEVAL-MVP::WS-04`

## 目标达成度评估

### WS-04 DoD 对齐
1. **检索日志字段可追溯**：Skill 检索新增结构化 `retrieval_log`，覆盖 `thread_id/trace_id/query_hash/selected_skill_ids` 与候选统计，可从 query -> candidates -> final 串联追踪。
2. **离线评测可执行**：新增离线评测脚本与样例集，支持 mock 回放与 baseline 差值计算。
3. **回归报告可复用**：输出评测 JSON 产物，包含单 case 结果、汇总指标与 baseline 对比，可直接复用于后续调参回归。

### 样例覆盖说明
- 银行业务场景：
  - `SK-OFFLINE-001` 对公贷款余额按分行统计
  - `SK-OFFLINE-002` 分行巡检待办与存款日报提醒
- 合规边界场景：
  - `SK-OFFLINE-003` 客户手机号/证件号明细请求触发“无权限时脱敏”边界

## 质量基线与回归结果

### 回归命令（本次执行）
1. `python3 scripts/skill_offline_evaluation.py --dataset tests/fixtures/skill_retrieval_offline_eval_cases.json --baseline tests/fixtures/skill_retrieval_offline_eval_baseline.json --output tests/artifacts/skill_retrieval_offline_eval_result.json`
2. `python3 -m pytest -q -o addopts='' tests/unit/test_skill_service.py`
3. `python3 -m pytest -q -o addopts='' tests/unit/test_multi_agent_skill_workflow.py`
4. `python3 -m pytest -q -o addopts='' tests/unit/test_skill_offline_evaluation.py`
5. `python3 -m pytest -q -o addopts='' tests -k "skill"`

> 说明：工作树中的 `venv` 为 Windows 结构（`venv/Scripts`），未提供 `venv/bin/python`，因此实际执行时使用 `python3` + `-o addopts=''` 覆盖项目默认 `pytest-cov` 参数。

### 结果摘要
| 指标 | 本次结果 | 基线 | 差值 |
|---|---:|---:|---:|
| total_cases | 3 | 3 | 0 |
| passed_cases | 3 | 3 | 0 |
| pass_rate | 1.0000 | 1.0000 | +0.0000 |
| avg_precision | 1.0000 | 1.0000 | +0.0000 |
| avg_recall | 1.0000 | 1.0000 | +0.0000 |

### 证据文件
- 离线评测样例：`tests/fixtures/skill_retrieval_offline_eval_cases.json`
- 评测基线：`tests/fixtures/skill_retrieval_offline_eval_baseline.json`
- 评测输出：`tests/artifacts/skill_retrieval_offline_eval_result.json`

## 风险与遗留问题
1. 当前离线评测以 mock 回放为主，能验证“观测字段完整性 + 规则裁决稳定性”，但不能完全覆盖线上 embedding/数据库波动。
2. live 模式依赖本地数据库 schema 与技能元数据完整（特别是 `is_enabled/auto_enabled` 列），环境不齐时可能降级为全空召回。
3. 评测样例数仍偏少，后续需扩展不同 scope 与冲突技能组合，降低误判风险。

## 下一阶段行动项
1. 在 WS-G1 门禁中接入 `python3 scripts/skill_offline_evaluation.py`，将 pass_rate/precision/recall 纳入统一门禁指标。
2. 增补 live 数据集（不少于 10 条），覆盖向量降级、scope 冲突与 top_k 溢出等边界。
3. 若后续出现回归，优先对比 `tests/artifacts/skill_retrieval_offline_eval_result.json` 与 baseline 差值定位退化维度。
