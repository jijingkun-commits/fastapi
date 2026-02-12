# 脚本目录说明

本目录包含项目维护和数据初始化相关的脚本。

## 目录结构

```
scripts/                    # 运维和数据脚本
├── README.md              # 本文件
│
├── # === 数据初始化（部署时使用）===
├── init_llm_config.py     # 初始化 LLM 模型配置
├── init_metric_definition.py  # 初始化指标定义（基础 4 个）
├── init_skill_config.py   # 初始化技能配置
├── init_tables_ci.py      # CI 环境表初始化
├── init_business_tables.py    # 业务表初始化
├── init_feedback_table.py     # 反馈表初始化
├── init_metrics_table.py  # [废弃] 创建 t_dmp_ind_info 表
│
├── # === 数据导入 ===
├── import_skills.py       # ★ 导入 AI 技能到向量库
├── import_metrics_from_didp.py  # 从 DIDP 导入指标
├── import_deposit_data.py # 导入存款测试数据
├── import_dim_data.py     # 导入维度数据
├── import_dim_tables.py   # 导入维度表结构
│
├── # === 元数据同步 ===
├── schema_sync.py         # ★ 同步表元数据到向量库
├── expand_metrics.py      # ★ 扩展指标定义（19 个）
├── create_dim_tables.py   # 创建维度表
├── create_meta_tables.py  # 创建元数据表
│
├── # === 数据库迁移 ===
├── sync_database.py       # ★ 自动同步工具（推荐）
├── migrate_user_management.py  # 用户管理模块迁移
├── migrate_todo_tables.py # 待办表迁移
├── migrate_vector_dim.py  # 向量维度迁移
│
├── # === 数据维护 ===
├── cleanup_chat_db.py     # 清理聊天历史
├── force_import_skills.py # 强制重新导入技能
├── archive_restore_skills.py  # 归档/恢复技能
├── merge_skills_from_cursorrules.py  # 合并 Cursor 规则技能
│
├── # === 验证和检查 ===
├── check_counts.py        # 检查各表记录数
├── verify_data_db.py      # 验证数据库状态
├── validate_metric_coverage.py  # 验证指标覆盖率
├── inspect_data_files.py  # 检查数据文件
│
├── # === 工具脚本 ===
├── extract_metric_sql.py  # 提取指标 SQL
├── setup_data.py          # 数据初始化入口
├── sync-repos.sh          # 仓库同步脚本
│
├── # === Vibe Kanban 多 worktree 本机开发 ===
├── vk_ports.sh            # 计算当前 worktree 端口
├── vk_setup.sh            # 初始化 worktree 本地配置
├── vk_dev.sh              # 启动 backend/web（本机命令）
└── vk_cleanup.sh          # 清理当前 worktree 启动进程

install/                   # 部署安装相关
├── scripts/
│   ├── init_postgres.sql/ # ★ 数据库迁移 SQL（按序号执行）
│   │   ├── 006_add_vision_models.sql
│   │   ├── 007_upgrade_todo_tables.sql
│   │   ├── ...
│   │   └── 016_expand_metrics.sql
│   ├── init_llm_config.py     # LLM 配置初始化
│   ├── init_minio_buckets.py  # MinIO Bucket 初始化
│   └── init_system_config.py  # 系统配置初始化
└── sql/                   # 基础 SQL 脚本
    └── init_postgres.sql  # ★ 全量建表（用户、会话、待办、LLM配置等）
```

## 常用脚本

### 数据库迁移（重要）

```bash
# ★ 推荐：自动同步数据库（检测并修复模型与数据库差异）
python scripts/sync_database.py

# 或手动执行特定迁移
python scripts/migrate_user_management.py
python scripts/migrate_todo_tables.py
```

> **说明**：`sync_database.py` 会自动创建缺失的表、列和索引，无需手动写 SQL。索引定义在模型的 `__table_args__` 中。

### 部署初始化

```bash
# 推荐使用一键部署脚本
./deploy.sh dev init

# 或手动执行关键脚本
python scripts/sync_database.py          # 先同步数据库
python scripts/init_llm_config.py        # LLM 模型配置
python install/scripts/init_system_config.py  # 系统配置项
python scripts/init_metric_definition.py # 指标定义
python scripts/expand_metrics.py         # 扩展指标
python scripts/import_skills.py          # AI 技能
python scripts/schema_sync.py            # 元数据同步
```

### 日常维护

```bash
# 同步表元数据（新增表后执行）
python scripts/schema_sync.py

# 更新 AI 技能（修改 SKILL.md 后执行）
python scripts/import_skills.py

# 检查数据状态
python scripts/check_counts.py
python scripts/validate_metric_coverage.py
```

### Vibe Kanban 多 worktree（本机命令）

```bash
# 初始化当前 worktree（复制配置 + 生成本地端口文件）
bash scripts/vk_setup.sh

# 启动 backend + web
bash scripts/vk_dev.sh up

# 查看状态
bash scripts/vk_dev.sh status

# 清理当前 worktree 进程
bash scripts/vk_cleanup.sh
```

> 主分支默认 8000/3000；子任务分支按 worktree 自动分配端口。
>
> 共享 venv 建议：`VK_SHARED_VENV_MODE=auto`（默认）。当本地 `venv` 不可用时，`vk_setup.sh` 会通过 `.vibe/venv` 复用主 worktree 的 `venv`。

### 数据清理

```bash
# 清理聊天历史（保留 30 天）
python scripts/cleanup_chat_db.py --days 30

# 强制重新导入技能
python scripts/force_import_skills.py
```

## 脚本分类

| 分类 | 说明 | 执行频率 |
|------|------|----------|
| **初始化** | 部署时执行一次 | 部署时 |
| **导入** | 数据变更后执行 | 按需 |
| **同步** | 元数据变更后执行 | 按需 |
| **维护** | 定期清理 | 定期 |
| **验证** | 排查问题时使用 | 按需 |

## 注意事项

1. **执行顺序**：初始化脚本有依赖关系，建议使用 `./deploy.sh init`
2. **环境变量**：所有脚本依赖 `.env` 配置，确保配置正确
3. **幂等性**：大部分脚本支持重复执行，使用 `ON CONFLICT DO UPDATE`
4. **废弃脚本**：`init_metrics_table.py` 已废弃，勿使用
