# 脚本目录说明

## 目录结构

```
scripts/                        # 项目脚本（根目录保留高频入口，实体按域归档）
├── db/                         # 数据库 schema、迁移、初始化
│   ├── create_dim_tables.py
│   ├── init_tables_ci.py
│   ├── migrate_access_admin_keys.py
│   ├── migrate_query_template.py
│   ├── schema_sync.py          # ★ 同步表元数据到向量库
│   └── sync_database.py        # ★ 自动同步工具（推荐）
├── data/                       # 数据导入、指标、技能
│   ├── expand_metrics.py       # ★ 扩展指标定义
│   ├── extract_metric_sql.py
│   ├── import_deposit_data.py
│   ├── import_dim_data.py
│   ├── import_metrics_from_didp.py
│   ├── import_skills.py        # 已退役：本地 Skill 导入链
│   ├── init_metric_definition.py
│   ├── setup_data.py           # 数据初始化入口
│   ├── skill_offline_evaluation.py  # Skill 检索离线评测
│   └── verify_data_db.py
├── docs_guard.py               # 文档同步守卫（hook 提醒 + 手动/CI 严格校验）
├── check_doc_sync.sh           # 文档同步检查（本地默认告警，--strict 阻断）
├── check_special_doc_sync.py   # 防屎山手册强制同步检查
├── config_doctor.py            # 配置契约健康检查
├── release_rollout_manager.py  # C-5 灰度发布/回滚管理（规则+命令）
├── jjk_deleteworktree.sh     # 输出当前 worktree 的可复制删除命令串
├── jjk_commit.sh             # 输出当前 worktree 的可复制提交/收口命令串
├── init_llm_config.py          # 初始化 LLM 模型配置
├── test_llm_config.py          # LLM 配置测试
├── sync-docs.sh                # 文档仓库同步
├── sync-repos.sh               # 代码仓库同步
├── *.py@ / *.sh@               # → symlink（入口别名，实体见下方说明）
└── README.md
```

### Symlink 说明

- 根目录 Python 入口（去重后的统一入口）：
  - `scripts/schema_sync.py@`、`scripts/sync_database.py@`、`scripts/create_dim_tables.py@` 等
  - `scripts/import_skills.py@`（已退役）、`scripts/expand_metrics.py@`、`scripts/setup_data.py@` 等
  - → 实体分别在 `scripts/db/` 或 `scripts/data/`（按领域归档）
- `.cursor/scripts/` 中保留部分工作流脚本副本（兼容旧流程），但执行入口以 `scripts/` 为准。

所有 symlink 保证现有引用（docs、commands、CI）无需修改；根目录不再保留与 `db/`、`data/` 的重复实体文件。

- `scripts/docs_guard.py`：提交 hook 默认使用 `--non-blocking` 输出提醒；手动校验与 CI 仍建议使用 `--strict` 保持阻断语义。
- `scripts/check_doc_sync.sh`：本地默认输出 warning 并允许继续提交；显式追加 `--strict` 时改回阻断模式，适合 CI / 人工收口。

### 重复脚本收敛清单（root -> 实体）

| 根目录入口 | 实体路径 |
|---|---|
| `scripts/create_dim_tables.py` | `scripts/db/create_dim_tables.py` |
| `scripts/init_tables_ci.py` | `scripts/db/init_tables_ci.py` |
| `scripts/migrate_access_admin_keys.py` | `scripts/db/migrate_access_admin_keys.py` |
| `scripts/migrate_query_template.py` | `scripts/db/migrate_query_template.py` |
| `scripts/schema_sync.py` | `scripts/db/schema_sync.py` |
| `scripts/sync_database.py` | `scripts/db/sync_database.py` |
| `scripts/expand_metrics.py` | `scripts/data/expand_metrics.py` |
| `scripts/extract_metric_sql.py` | `scripts/data/extract_metric_sql.py` |
| `scripts/import_deposit_data.py` | `scripts/data/import_deposit_data.py` |
| `scripts/import_dim_data.py` | `scripts/data/import_dim_data.py` |
| `scripts/import_metrics_from_didp.py` | `scripts/data/import_metrics_from_didp.py` |
| `scripts/import_skills.py` | `scripts/data/import_skills.py`（已退役） |
| `scripts/init_metric_definition.py` | `scripts/data/init_metric_definition.py` |
| `scripts/setup_data.py` | `scripts/data/setup_data.py` |
| `scripts/skill_offline_evaluation.py` | `scripts/data/skill_offline_evaluation.py` |
| `scripts/verify_data_db.py` | `scripts/data/verify_data_db.py` |

## 常用脚本

### 数据库迁移

```bash
python scripts/db/sync_database.py              # ★ 自动同步（推荐）
python scripts/db/migrate_access_admin_keys.py --dry-run
```

### 部署初始化

```bash
./deploy.sh dev init                             # 一键部署
# 或手动：
python scripts/db/sync_database.py               # 先同步数据库
python scripts/init_llm_config.py                # LLM 模型配置
python scripts/data/init_metric_definition.py    # 指标定义
python scripts/data/expand_metrics.py            # 扩展指标
python scripts/data/import_skills.py             # 已退役：本地 Skill 导入链
python scripts/db/schema_sync.py                 # 元数据同步
```

### 记忆链路排查

```bash
# 删除单个 thread 的 LangGraph checkpoint（不删聊天消息表）
$(bash scripts/repo_python.sh) scripts/debug/delete_thread_checkpoint.py \
  --thread-id visual-evidence-1773109675

# 按用户名 + 槽位键诊断
$(bash scripts/repo_python.sh) scripts/debug/check_memory_flow.py \
  --username jjk \
  --slot-key user.profile.fact.favorite.color

# 按线程 + 关键字诊断
$(bash scripts/repo_python.sh) scripts/debug/check_memory_flow.py \
  --username jjk \
  --thread-id b7d622bf-350d-4dc6-bd3b-7f8b314ef58b \
  --thread-id 65829c70-0f9e-4d22-8cb9-8232a3a16660 \
  --keyword 蓝色
```

脚本会统一输出 `t_chat_message`、`t_user_memory_document`、`t_user_memory_chunk`、`t_user_memory_intent_job`、`t_user_memory` 的只读诊断结果，并给出“当前是否 active / 是否 archived / 可能走了哪条持久化路径”的推导结论。

### 日常维护

```bash
python scripts/db/schema_sync.py                 # 新增表后同步元数据
python scripts/data/import_skills.py             # 已退役：本地 SKILL.md 导入链不再可用
python scripts/data/skill_offline_evaluation.py  # Skill 检索离线评测
python scripts/config_doctor.py --strict         # 配置健康检查
python scripts/check_special_doc_sync.py --cached --strict  # 命中特殊处理文件时强制校验手册同步
python scripts/release_rollout_manager.py status             # C-5 灰度状态
python scripts/release_rollout_manager.py rollout --target all --percent 10 --sync
python scripts/release_rollout_manager.py rollback --target all --reason "production issue" --sync
```

### Codex App 监控

```bash
# 基础健康检查（/health, /health/db, /health/pool）
python scripts/codex_app_monitor.py --base-url http://127.0.0.1:8000/api/v1

# 开发环境加 Codex 轻探针（/dev-tools/codex/exec）
# 若接口受鉴权保护，传 Bearer Token（或设置 CODEX_APP_BEARER_TOKEN）
python scripts/codex_app_monitor.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --check-codex \
  --bearer-token "$CODEX_APP_BEARER_TOKEN" \
  --alert-threshold 2
```

脚本输出 JSON，`ok=false` 时返回退出码 `2`，可直接接入 `cron` / `systemd timer` / `launchd`。

示例（cron）：
```bash
*/3 * * * * cd /Users/jijingkun/bojxAI/fastapi && scripts/cron/codex_app_monitor.sh >> logs/codex-monitor.log 2>&1
```

### Codex 对话监督（长输出压缩 + 可续聊）

```bash
# 第 1 轮：返回 session_id + 精简结果，完整输出落盘
python scripts/codex_turn_supervisor.py \
  --workdir /Users/jijingkun/bojxAI/fastapi \
  --prompt "先分析项目里的 health 监控现状" \
  --sandbox read-only

# 第 2 轮：带上 session_id 继续
python scripts/codex_turn_supervisor.py \
  --workdir /Users/jijingkun/bojxAI/fastapi \
  --session-id <上一步返回的 session_id> \
  --prompt "基于你刚才的分析，给出下一步改造清单" \
  --sandbox read-only
```

脚本会把完整内容写入 `tmp/codex-supervisor/<session_id>/`，并在终端仅输出摘要 JSON，适合做“看结果 + 人工回复推进下一步”。

### Vibe Kanban 多 worktree

```bash
bash scripts/vk_setup.sh       # 初始化 worktree 配置
bash scripts/vk_dev.sh up      # 启动 backend + web
bash scripts/vk_dev.sh status  # 查看状态
bash scripts/vk_cleanup.sh     # 清理进程
```

> 主分支默认 8000/3000；子任务分支按 worktree 自动分配端口。

### Worktree 生命周期清理

```bash
bash scripts/jjk_deleteworktree.sh
# 输出一条可复制执行的删除命令；默认只生成，不直接删除
```

脚本会基于当前 worktree 自动解析：

- 当前 worktree 根路径
- 当前分支名
- 当前 HEAD 是否已并入 `master`
- 当前 worktree 是否干净

若门禁通过，输出一条可在**任意目录**执行的命令串，例如：

```bash
git -C /path/to/repo worktree remove /path/to/worktree && git -C /path/to/repo branch -d branch-name
```

适合“先在当前 worktree 里生成，再复制到任意终端执行”，避免脚本在被删除目录内自删。

### Commit 并收口到 `master`

```bash
bash scripts/jjk_commit.sh
# 直接输出一条可复制执行的提交 + merge 命令；默认 verify 为 `:`，dirty 时自动生成 commit message

# 也可以显式给验证命令和提交说明
bash scripts/jjk_commit.sh --verify-cmd 'bash scripts/pytest_targeted.sh tests/...' --message 'feat: xxx'
```

脚本会基于当前 worktree 自动解析：

- 当前 worktree 根路径
- 当前分支名与当前 HEAD
- 当前脏改动快照 hash（防止生成后内容漂移）
- shared delivery engine 与 `master` 基线可达性

若门禁通过，输出一条可在**任意目录**执行的命令串。该命令会先：

1. 切到当前 worktree 绝对路径；
2. 校验分支、HEAD 与脏改动快照未漂移；
3. 执行 `--verify-cmd`（默认 `:`，即不额外执行验证）；
4. 若存在未提交改动，则 `git add -A && git commit -m ...`（默认 `chore: deliver <branch>`）；
5. 最后调用 shared delivery engine 收口到 `master`。

这样你可以“先在当前 worktree 里生成，再复制到任意终端执行”，同时保留 `jjk-commit` 的上下文门禁与可追溯验证语义。

## 注意事项

1. 所有脚本依赖 `.env` 配置，确保环境变量正确
2. 大部分脚本支持幂等执行（`ON CONFLICT DO UPDATE`）
3. 个人工作流脚本实体在 `.cursor/scripts/`，勿直接编辑 `scripts/` 下的 symlink

## 新增脚本流程

| 场景 | 操作 |
|------|------|
| 新增个人工作流脚本 | 文件放 `.cursor/scripts/xxx`，然后 `ln -s ../.cursor/scripts/xxx scripts/xxx` |
| 新增项目脚本 | 直接放 `scripts/` 根目录或对应子目录（`db/`、`data/`） |
| 新增 Cursor 规则/命令 | 在 `.cursor/rules/` 或 `.cursor/commands/` 新增文件，然后 `python3 scripts/sync_rules_to_cc.py`（同时镜像 `AGENTS.md -> CLAUDE.md`，同步到 `.claude/*`，并将命令同步到 `~/.codex/prompts/`） |
| 生成 JJK Skills 镜像 | 执行 `python3 scripts/sync_rules_to_cc.py --only commands`，将 `.cursor/commands/jjk-*.md` 生成到 `.agents/skills/jjk-*/SKILL.md`（仅同步 SKILL.md，不注入 prompt 注册） |
| Clarify 命令体检 | 执行 `python3 scripts/check_clarify_contract_consistency.py`，校验 `.cursor/commands/jjk-clarify.md`、模板、Skill 镜像与 `~/.codex/prompts/jjk-clarify.md` 是否一致 |
| 新增 CC 手工规则 | 创建 `.claude/rules/xxx.md`，在 sync 脚本 `MANUAL_FILES` 中注册文件名 |
