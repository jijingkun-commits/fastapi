# 数据分析模块部署

本目录包含数据分析模块（问数功能）的部署脚本。

## 目录结构

```
install/data_import/
├── README.md                           # 本文件
├── 01_create_fdmdata_schema.sql        # 创建 fdmdata schema
├── 02_create_sdmdata_schema.sql        # 创建 sdmdata schema
├── 03_create_business_tables.sql       # 业务表建表语句（69张表）
├── 04_import_metrics.py                # 指标元数据导入脚本
├── 05_link_metric_sql.py               # 指标 SQL 关联脚本
├── 06_verify_coverage.py               # 覆盖率验证脚本
├── 07_import_table_metadata.py         # 表/字段元数据导入脚本
├── 08_generate_metric_embeddings.py    # 指标 embedding 生成脚本
├── 09_generate_training_embeddings.py  # 训练数据 embedding 生成脚本
└── generate_ddl.py                     # DDL 生成工具脚本
```

## 执行顺序

### 1. 创建 Schema

```bash
# 在 data_db 数据库中执行
psql -h localhost -U postgres -d data_db -f 01_create_fdmdata_schema.sql
psql -h localhost -U postgres -d data_db -f 02_create_sdmdata_schema.sql
```

### 2. 创建业务表

```bash
psql -h localhost -U postgres -d data_db -f 03_create_business_tables.sql
```

### 3. 导入指标定义

```bash
# 在项目根目录执行
python install/data_import/04_import_metrics.py
python install/data_import/05_link_metric_sql.py
```

### 4. 验证覆盖率

```bash
python install/data_import/06_verify_coverage.py
```

### 5. 导入表元数据（提升问数准确率）

```bash
# 导入表/字段元数据到 t_meta_tables 和 t_meta_columns
python install/data_import/07_import_table_metadata.py

# 生成表元数据的 embedding 向量
python install/data_import/07_import_table_metadata.py --generate-embeddings
```

### 6. 生成指标 Embedding（必选）

```bash
# 为指标定义生成 embedding 向量（启用指标语义匹配）
python install/data_import/08_generate_metric_embeddings.py
```

> **重要**：此步骤必须执行，否则指标语义匹配功能无法工作。

### 7. 训练数据 Embedding（批量导入时使用）

```bash
# 如果批量导入了历史训练数据，需要补充生成 embedding
python install/data_import/09_generate_training_embeddings.py
```

> 正常使用问数功能时，embedding 会在记录时自动生成，无需手动执行此脚本。

## 数据文件要求

指标导入脚本依赖以下数据文件（需放置在 `data/` 目录下）：

| 文件 | 说明 | 来源 |
|------|------|------|
| `dmp_show_ind_info_*.txt` | 指标元数据 | DIDP 导出 |
| `DIDP_PROJECT_WORKSPACE/` | SQL 模板和表结构 | DIDP 项目工作空间 |

## 业务表说明

DDL 脚本包含 **69 张业务表**，按覆盖度优先级排序。创建全部表后可达到 **90%+ 指标覆盖率**。

主要表分类：

**核心指标表（fdmdata schema）**：
- `f_mid_index_result` - 指标结果表（解锁最多指标）
- `f_mid_index_result_derive` - 派生指标结果表
- `f_mid_index_result_dim` - 维度指标结果表
- `f_mid_org_tree_k` - 机构树快照表
- `f_mid_loan_k_tb` / `f_mid_dep_k_tb` - 贷款/存款快照表

**业务基础表（sdmdata schema）**：
- `s_ods_g_b_cif_*` - 客户信息系列表
- `s_ods_g_b_ln_*` - 贷款业务系列表
- `s_ods_g_b_dep_*` - 存款业务系列表
- `s_rrs_rd_*` - 监管报表系列表

完整表清单见 `03_create_business_tables.sql` 文件注释。

## 注意事项

1. 执行前确保 data_db 数据库已创建
2. 指标 SQL 模板使用 `${data_dt}` 作为日期参数占位符
3. 业务表需要从生产环境同步数据才能查询指标
