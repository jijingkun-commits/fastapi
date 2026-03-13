# Stash Archive 2026-03-14

本目录保存了 2026-03-14 从 `fastapi` 仓库导出的 5 份 stash patch 备份。

## 归档项

| 原 stash 主题 | Patch 文件 | 原 stash 对象 |
| --- | --- | --- |
| `codex/服务中台` | `codex-fuwu-zhongtai.patch` | `3c4eaa9f567b8826fe20358c2dc859baac3c5554` |
| `codex/supervisor-state-ownership` | `codex-supervisor-state-ownership.patch` | `190ecb7f89f71a138a834a63e905444093d17517` |
| `codex/回复内容展示bug` | `codex-reply-content-display-bug.patch` | `302214ff9a75dfaf2e18a0fd91b12092a390267b` |
| `autostash` | `autostash.patch` | `fd47d0d35f975c87e60d9b15a4da1857f0704a58` |
| `codex/ai-hotspot-module-refactor-docs safe switch` | `codex-ai-hotspot-module-refactor-docs-safe-switch.patch` | `2bf8eb079cedd80580100ea0fa070a8da51cd267` |

## 原始消息

- `On codex/服务中台: codex cleanup backup 2026-03-13 22:20:43 | codex_服务中台 | /Users/jijingkun/.codex/worktrees/服务中台`
- `On codex/supervisor-state-ownership: codex cleanup backup 2026-03-13 22:20:51 | codex_supervisor-state-ownership | /Users/jijingkun/bojxAI/fastapi/.worktrees/supervisor-state-ownership`
- `On codex/回复内容展示bug: codex cleanup backup 2026-03-13 22:20:38 | codex_回复内容展示bug | /Users/jijingkun/.codex/worktrees/ece2/fastapi`
- `autostash`
- `On codex/ai-hotspot-module-refactor-docs: safe switch to master from codex/ai-hotspot-module-refactor-docs`

## 恢复方式

如果后续需要恢复某一份归档，可在目标分支上执行：

```bash
git apply --index workdocs/stash-archive/2026-03-14/<patch-file>
```

如果只想先看内容，不直接应用：

```bash
git apply --stat workdocs/stash-archive/2026-03-14/<patch-file>
git apply --check workdocs/stash-archive/2026-03-14/<patch-file>
```
