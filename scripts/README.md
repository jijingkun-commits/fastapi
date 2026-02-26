# 脚本目录说明

## 目录结构

```
scripts/                        # 项目脚本（根目录保留高频/CI 脚本）
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
│   ├── import_skills.py        # ★ 导入 AI 技能到向量库
│   ├── init_metric_definition.py
│   ├── setup_data.py           # 数据初始化入口
│   ├── skill_offline_evaluation.py  # Skill 检索离线评测
│   └── verify_data_db.py
├── docs_guard.py               # 文档同步守卫（pre-commit）
├── check_doc_sync.sh           # 文档同步检查
├── config_doctor.py            # 配置契约健康检查
├── init_llm_config.py          # 初始化 LLM 模型配置
├── test_llm_config.py          # LLM 配置测试
├── sync-docs.sh                # 文档仓库同步
├── sync-repos.sh               # 代码仓库同步
├── *.py@ / *.sh@               # → symlink，实体见下方说明
└── README.md
```

### Symlink 说明

- `scripts/vk_*.sh@`, `scripts/wt-flow.sh@`, `scripts/sync_rules_to_cc.py@` 等
  → 实体在 `.cursor/scripts/`（个人工作流脚本）
- `scripts/schema_sync.py@`, `scripts/import_skills.py@` 等
  → 实体在 `scripts/db/` 或 `scripts/data/`（子目录归类）

所有 symlink 保证现有引用（docs、commands、CI）无需修改。

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
python scripts/data/import_skills.py             # AI 技能
python scripts/db/schema_sync.py                 # 元数据同步
```

### 日常维护

```bash
python scripts/db/schema_sync.py                 # 新增表后同步元数据
python scripts/data/import_skills.py             # 修改 SKILL.md 后更新技能
python scripts/data/skill_offline_evaluation.py  # Skill 检索离线评测
python scripts/config_doctor.py --strict         # 配置健康检查
```

### Vibe Kanban 多 worktree

```bash
bash scripts/vk_setup.sh       # 初始化 worktree 配置
bash scripts/vk_dev.sh up      # 启动 backend + web
bash scripts/vk_dev.sh status  # 查看状态
bash scripts/vk_cleanup.sh     # 清理进程
```

> 主分支默认 8000/3000；子任务分支按 worktree 自动分配端口。

## 注意事项

1. 所有脚本依赖 `.env` 配置，确保环境变量正确
2. 大部分脚本支持幂等执行（`ON CONFLICT DO UPDATE`）
3. 个人工作流脚本实体在 `.cursor/scripts/`，勿直接编辑 `scripts/` 下的 symlink

## 新增脚本流程

| 场景 | 操作 |
|------|------|
| 新增个人工作流脚本 | 文件放 `.cursor/scripts/xxx`，然后 `ln -s ../.cursor/scripts/xxx scripts/xxx` |
| 新增项目脚本 | 直接放 `scripts/` 根目录或对应子目录（`db/`、`data/`） |
| 新增 Cursor 规则 | 在 `.cursor/rules/` 创建 `.mdc` 文件，然后 `python3 scripts/sync_rules_to_cc.py` |
| 新增 CC 手工规则 | 创建 `.claude/rules/xxx.md`，在 sync 脚本 `MANUAL_FILES` 中注册文件名 |
