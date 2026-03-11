# WS-00 C00 Codex 门禁状态目录规范

> 适用任务: `PP-20260301-USER-MEMORY-ADMIN`  
> 适用目录: `workdocs/任务拆解/2026-03-01_用户个性化永久记忆与管理能力`  
> 目标: 将门禁过程产物统一落在任务目录内，彻底去除历史全局 state 目录口径。

## 1. 结论先行

`check_integration_gate.py` 读取的 merge 证据不是 CC 专属插件产物，而是仓库脚本约定的“过程状态账本”。

当前默认路径为任务目录 `.artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力/<task_key>`；执行链路不再依赖历史全局 state 的回读/回写。

## 2. 门禁必要性评估

| 门禁项 | 必要性 | 作用 | 缺失风险 |
|---|---|---|---|
| `docs_guard --strict` | 必要 | 保证文档与链接一致性，防止拆解文档失真 | 验收文档断链、证据不可追溯 |
| `check_gate_contract_consistency` | 必要 | 保证 `vk_cards/parallel_plan/implementation_plan` 契约一致 | 执行顺序与 gate 关系漂移 |
| `check_integration_gate` | 必要 | 保证实现卡“已合并且主干可见” | 出现“本地 done、主干不可见”的假完成 |
| `coder4_scope_guard` | 建议 | 保证 active_task 作用域与当前任务一致 | 多任务并行时串卡污染 |

## 3. Codex 状态目录约定（本任务）

- 状态根目录（state_dir）:
  - `.artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力`
- 任务状态根（task state root）:
  - `.artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力/PP-20260301-USER-MEMORY-ADMIN`
- 关键产物:
  - `task-runner-state.json`
  - `task-runner-state.json.gate_results.<card_id>`
  - `task-runner-state.json.merge_results.<card_id>`

## 4. 标准执行命令（Codex）

### 4.1 Gate 结果聚合（G01）

```bash
python3 - <<'PY'
import json
import pathlib

required = ['C01', 'C02', 'C03', 'C04', 'C05', 'C06']
state_file = pathlib.Path('/Users/jijingkun/.codex/worktrees/978e/fastapi/.artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力/PP-20260301-USER-MEMORY-ADMIN/task-runner-state.json')
state = json.loads(state_file.read_text(encoding='utf-8'))
gate_results = state.get('gate_results', {})
missing = [card for card in required if card not in gate_results]
failed = [card for card in required if not gate_results.get(card, {}).get('passed', False)]
assert not missing and not failed, f'missing={missing},failed={failed}'
PY
```

### 4.2 主干可见性校验（IG01）

```bash
python3 scripts/coder4/check_integration_gate.py \
  --task-split-dir "2026-03-01_用户个性化永久记忆与管理能力" \
  --state-dir ".artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力" \
  --baseline master
```

### 4.3 `wt-flow` 写入同一状态目录

```bash
WT_FLOW_STATE_DIR="/Users/jijingkun/.codex/worktrees/978e/fastapi/.artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力" \
scripts/coder4/wt-flow.sh merge
```

## 5. 兼容策略

- 不支持历史全局 state 的回读/回写；发现旧目录时需先迁移再执行门禁。
- 若两套目录同时存在，以本任务 `parallel_plan.md` 中声明路径为验收准绳。
- 如需迁移旧证据，应合并到 `task-runner-state.json` 的 `gate_results/merge_results` 键后重跑门禁。

## 6. 验收标准

1. `G01` 与 `IG01` 的命令均显式指向任务目录 `.state`。
2. `check_integration_gate` 输出中的 `resolved_state_dir` 指向 `.artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力/PP-20260301-USER-MEMORY-ADMIN`。
3. 门禁失败信息能直接定位到本任务 `task-runner-state.json` 的具体 `gate_results/merge_results` 键。
