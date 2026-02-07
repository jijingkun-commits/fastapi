# DIDP 数据架构与指标提取指南

本文档详细说明了系统的数仓架构、数据来源以及如何初始化和维护数据环境。

## 1. 数仓架构 (Data Warehouse Architecture)

本系统采用简化的数仓分层架构，主要包含以下层级：

| 层级 | Schema | 说明 | 主要表 |
| :--- | :--- | :--- | :--- |
| **ODS/SDM** | `sdmdata` | 源数据层/标准数据层 | `s_ods_g_c_dim_date` (日期维度) |
| **FDM** | `fdmdata` | 基础数据层 (3NF) | `f_mid_org_tree` (机构树), `f_mid_loan_tb` (贷款), `f_mid_dep_tb` (存款) |
| **ADM** | `admdata` | 应用数据层 (宽表/集市) | (暂未启用，直接基于 FDM 计算) |

## 2. 数据来源与初始化

系统数据分为**业务数据** (Analytics DB) 和**元数据** (Chat DB)。

### 2.1 自动化初始化工具

我们把所有初始化脚本整合到了统一的 CLI 工具中：`scripts/setup_data.py`。

**一键完整初始化**:
```bash
python scripts/setup_data.py full-setup
```

该命令会按顺序执行以下步骤：
1.  **init-schema**: 创建维度表结构 (`f_mid_org_tree`, `s_ods_g_c_dim_date`)。
2.  **init-metrics**: 初始化元数据表 (`t_metric_definition`)。
3.  **import-dims**: 导入维度数据 (从 `.txt` 文件)。
    *   *自动处理主键冲突与去重*。
4.  **import-facts**: 导入事实/样本数据 (如 `f_mid_dep_tb`)。
5.  **import-metadata**: 从 DIDP 导出文件 (`dmp_show_ind_info_*.txt`) 导入指标元数据。
6.  **extract-sql**: 从 DIDP 工程目录扫描 SQL 文件，提取计算逻辑并更新到 `sql_template`。
7.  **sync-vectors**: 将最新的 Schema 和指标定义同步到向量数据库 (Vanna)。

### 2.2 常用命令速查

| 任务 | 命令 | 备注 |
| :--- | :--- | :--- |
| **仅更新指标定义** | `python scripts/setup_data.py import-metadata` | 当指标文档更新时执行 |
| **仅更新 SQL 逻辑** | `python scripts/setup_data.py extract-sql` | 当 SQL 模板变动时执行 |
| **同步向量库** | `python scripts/setup_data.py sync-vectors` | 任何元数据变动后都应执行 |

## 3. 指标提取机制

系统采用 "Text + SQL" 双轨制提取指标：

1.  **元数据 (Metadata)**:
    *   来源: `dmp_show_ind_info_*.txt`
    *   包含: 指标ID, 名称, 描述, 业务口径
    *   脚本: `import_metrics_from_didp.py`

2.  **计算逻辑 (SQL)**:
    *   来源: DIDP 工程目录 (`*_F_MID_INDEX_RESULT_*.sql`)
    *   逻辑: 解析 SQL 文件中的 `SELECT` 部分，替换 `[DATE]` 占位符为 `:data_dt`，适配 PostgreSQL 语法。
    *   脚本: `extract_metric_sql.py`

## 4. 常见问题排查

### 4.1 数据导入失败 ("duplicate key")
原因：源文件可能包含重复数据。
解决：`import_dim_data.py` 已内置 `ON CONFLICT DO NOTHING` 逻辑，通常会自动忽略重复项。如果报错，请检查脚本版本。

### 4.2 向量库检索不到新指标
原因：元数据更新后未同步。
解决：执行 `python scripts/setup_data.py sync-vectors`。

## 5. 手动查找指南 (Manual Lookup Guide)

如果你不想运行脚本，也可以通过以下步骤手动找到需要的指标定义和 SQL。

### 步骤 1：查找指标 ID

1. 打开数据文件：`data/dmp_show_ind_info_*.txt`
2. 搜索指标名称（如 "各项存款"）
3. 第一列即为 **指标 ID** (如 `A000047`)

### 步骤 2：定位 SQL 文件

SQL 核心逻辑位于 `data/DIDP_PROJECT_WORKSPACE/KJ2023_11/1.0/` 目录下。根据指标类型进入不同子目录：

- **业务指标**: `SCH_FDM_IND_CW_YW/SCH_FDM_IND_CW_YW.F_MID_INDEX_RESULT/` (最常用)
- **财务指标**: `SCH_FDM_IND_CW_CW/...`
- **客户指标**: `SCH_FDM_IND_CW_KH/...`

在目录下搜索文件名包含 **指标 ID** 的 `.sql` 文件。
例如：`*_A000047.sql`

### 步骤 3：提取计算逻辑

1. 打开找到的 SQL 文件。
2. 找到 `INSERT INTO ... SELECT ...` 语句。
3. 复制 `SELECT` 部分（不包含 `INSERT`）。
4. 将 `Sum(column)` 等聚合函数作为提取目标。
5. 将 `[DATE]` 替换为参数 `:date`。

> **更多详情**：请参阅 [DIDP 数据架构与指标提取](../../开发文档/架构设计/DIDP数据架构与指标提取.md) 获取完整的字段映射和目录结构说明。
