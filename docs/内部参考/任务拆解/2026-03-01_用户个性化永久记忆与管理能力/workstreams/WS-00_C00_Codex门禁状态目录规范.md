# WS-00 C00 Codex 门禁状态目录规范

> 适用任务: `PP-20260301-USER-MEMORY-ADMIN`  
> 适用目录: `docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力`  
> 目标: 将门禁过程产物统一落在任务目录内，避免依赖默认 `.omc/state` 路径。

## 1. 结论先行

`check_integration_gate.py` 读取的 `merge_result.json` 不是 CC 专属插件产物，而是仓库脚本约定的“过程状态账本”。

当前默认路径写在脚本里是 `.omc/state`，但它可配置，且已支持通过参数覆盖到任务目录内。

## 2. 门禁必要性评估

| 门禁项 | 必要性 | 作用 | 缺失风险 |
|---|---|---|---|
| `docs_guard --strict` | 必要 | 保证文档与链接一致性，防止拆解文档失真 | 验收文档断链、证据不可追溯 |
| `check_gate_contract_consistency` | 必要 | 保证 `vk_cards/parallel_plan/implementation_plan` 契约一致 | 执行顺序与 gate 关系漂移 |
| `check_integration_gate` | 必要 | 保证实现卡“已合并且主干可见” | 出现“本地 done、主干不可见”的假完成 |
| `coder4_scope_guard` | 建议 | 保证 active_task 作用域与当前任务一致 | 多任务并行时串卡污染 |

## 3. Codex 状态目录约定（本任务）

- 状态根目录（state_dir）:
  - `docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/.state`
- 任务状态根（task state root）:
  - `docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/.state/PP-20260301-USER-MEMORY-ADMIN`
- 关键产物:
  - `task-runner-state.json`
  - `attempts/<card_id>/gate_result.json`
  - `attempts/<card_id>/merge_result.json`

## 4. 标准执行命令（Codex）

### 4.1 Gate 结果聚合（G01）

```bash
python3 -c "import json, pathlib; req=['C01','C02','C03','C04','C05','C06']; root=pathlib.Path('/Users/jijingkun/bojxAI/fastapi/docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/.state/PP-20260301-USER-MEMORY-ADMIN/attempts'); missing=[]; failed=[]; [((missing.append(c) if not (root/c/'gate_result.json').exists() else (failed.append(c) if not json.loads((root/c/'gate_result.json').read_text(encoding='utf-8')).get('passed', False) else None))) for c in req]; assert not missing and not failed, f'missing={missing},failed={failed}'"
```

### 4.2 主干可见性校验（IG01）

```bash
python3 scripts/check_integration_gate.py \
  --task-split-dir "2026-03-01_用户个性化永久记忆与管理能力" \
  --state-dir "docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/.state" \
  --baseline master
```

### 4.3 `wt-flow` 写入同一状态目录

```bash
WT_FLOW_STATE_DIR="/Users/jijingkun/bojxAI/fastapi/docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/.state" \
scripts/wt-flow.sh merge
```

## 5. 兼容策略

- 旧目录 `.omc/state` 继续可读，但本任务以任务目录 `.state` 为主。
- 若两套目录同时存在，以本任务 `parallel_plan.md` 中声明路径为验收准绳。
- 如需迁移旧证据，可按卡片维度将 `attempts/<card_id>/*.json` 迁入本任务 `.state` 对应目录后重跑门禁。

## 6. 验收标准

1. `G01` 与 `IG01` 的命令均显式指向任务目录 `.state`。
2. `check_integration_gate` 输出中的 `resolved_state_dir` 指向本任务 `.state/PP-20260301-USER-MEMORY-ADMIN`。
3. 门禁失败信息能直接定位到本任务目录下的具体 `attempts/<card_id>` 文件。
