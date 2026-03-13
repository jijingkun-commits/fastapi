# Current Worktree Snapshot

本目录保存了 `2026-03-14` 当次清理结束后 `master` 工作区的本地快照。

## 内容

- `current-worktree-tracked.patch`
  - 来源：当时所有已跟踪文件的未提交改动
  - 数量：13 个已跟踪文件
  - 文件清单：`current-worktree-tracked-files.txt`
- `current-worktree-untracked.patch`
  - 来源：当时所有未跟踪文本文件
  - 数量：14 个未跟踪文件
  - 文件清单：`current-worktree-untracked-files.txt`

## 校验

两份 patch 都已在干净 worktree
`/Users/jijingkun/.codex/worktrees/6438/fastapi`
上通过：

```bash
git apply --check current-worktree-tracked.patch
git apply --check current-worktree-untracked.patch
```

## 恢复方式

如果后续要恢复到某个干净分支：

```bash
git apply --index workdocs/stash-archive/2026-03-14/current-worktree/current-worktree-tracked.patch
git apply --index workdocs/stash-archive/2026-03-14/current-worktree/current-worktree-untracked.patch
```

如果只想先检查：

```bash
git apply --stat workdocs/stash-archive/2026-03-14/current-worktree/current-worktree-tracked.patch
git apply --check workdocs/stash-archive/2026-03-14/current-worktree/current-worktree-tracked.patch
git apply --stat workdocs/stash-archive/2026-03-14/current-worktree/current-worktree-untracked.patch
git apply --check workdocs/stash-archive/2026-03-14/current-worktree/current-worktree-untracked.patch
```
