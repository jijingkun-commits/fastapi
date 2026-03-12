# Lean 瘦身门禁规范

## 目标

把“精简优先、主动瘦身、热点文件禁止继续长胖”从口头要求收敛为可执行门禁，避免继续通过在超大文件中追加 `_helper`、嵌套函数、包装层或局部 fallback 掩盖结构问题。

## 适用范围

- 所有 Pull Request / 本地变更集。
- 尤其适用于以下热点目录：
  - `app/ai/workflow/**/*.py`
  - `app/services/**/*.py`
  - `scripts/**/*.py`

## 核心原则（强制）

1. **热点文件 shrink-only**：当文件已超过目录阈值时，继续修改该文件必须以净删除为主，禁止净增长。
2. **禁止继续堆内部函数**：热点文件超过阈值后，禁止继续新增私有 helper（`def _*` / `async def _*`）与嵌套函数。
3. **优先拆职责，不优先拆函数**：若文件已是热点文件，新增逻辑应外移到新模块/新职责边界，而不是继续在原文件里切更多内部函数。
4. **删除合同前置**：`bugfix/refactor` 编码前必须声明 `obsolete_paths`、`retained_paths` 与 `line_budget`；其中 `line_budget` 按整个变更集统计，新增文件、外移模块、helper 文件同样计入 added。
5. **新增实现必须收旧口**：若新实现已覆盖旧职责，旧函数、旧分支、旧文件必须删除；确需保留时，必须写明唯一理由与失效条件。
6. **私有 helper / fallback 要克制**：禁止为一次性包装、命名中转或假设性容错继续堆 `_helper`、嵌套函数或 fallback 分支；只有在消除重复逻辑或隔离明确外部边界时才允许新增。
7. **未上线阶段默认治理优先**：本项目未上线，命中结构热点时优先重构，不以“先兼容后治理”作为默认口径。

## 默认阈值

| 范围 | 阈值（结果文件行数） | 默认动作 |
| --- | --- | --- |
| `app/ai/workflow/**/*.py` | 1500 | 超阈值文件进入 shrink-only |
| `app/services/**/*.py` | 800 | 超阈值文件进入 shrink-only |
| `scripts/**/*.py` | 1000 | 超阈值文件进入 shrink-only |

## 失败码

| 失败码 | 触发条件 |
| --- | --- |
| `LEAN_GUARD_HOTSPOT_GROWTH` | 热点文件超过阈值且本次变更对该文件净增长 |
| `LEAN_GUARD_PRIVATE_HELPER_ADDED` | 超阈值热点文件新增私有 helper |
| `LEAN_GUARD_NESTED_FUNCTION_ADDED` | 超阈值热点文件新增嵌套函数 |
| `LEAN_GUARD_OBSOLETE_PATH_RETAINED` | 新实现已覆盖旧职责，但旧路径仍保留且无唯一理由 |
| `LEAN_GUARD_WHOLESET_GROWTH_UNPROVEN` | 只用单文件删行主张“已瘦身”，但整个变更集仍净增长且未说明原因 |

## 证据化要求

命中 Lean Guard 的任务，交付必须包含：

- 瘦身合同执行结果（`obsolete_paths` 命中结果、`retained_paths` 保留理由）
- 变更集统计口径（新增文件、删除文件、净增减）
- 删除清单（删了什么冗余）
- 重复收敛（消除了哪些重复逻辑）
- 复杂度变化（至少给出文件/函数层摘要）
- 验证结果（确保重构或外移后行为可验证）

## 与 Bugfix 预算的关系

- `bugfix-minimal-change` 解决“缺陷修复别越修越胖”。
- `lean-guard` 解决“热点文件别继续长胖”。
- 两者并行生效，互不替代。
- `lean-guard` 不依赖 PR 模板或 PR 时机，默认在执行链内部收口。

## 本地与执行指令门禁

- 本地建议执行：
  - `python3 scripts/ci/check_lean_budget.py --cached --strict`
- 执行指令强制挂载：
  - `/jjk-imp` 命中热点文件时，完成实现前必须执行 Lean Guard
  - `/jjk-debug` 命中热点文件时，完成修复前必须执行 Lean Guard
  - `/jjk-refactor` 命中热点文件时，完成重构前必须执行 Lean Guard
