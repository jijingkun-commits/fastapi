# DIDP 指标数据提取指南


## 文档导航

- 全局架构入口：[系统总览](系统总览.md)
- AI 核心设计：[AI模块设计](AI模块设计.md)
- 后端分层设计：[后端架构](后端架构.md)
- 前端分层设计：[前端架构](前端架构.md)
- 数据模型与双库：[数据库设计](数据库设计.md)
- 对外接口定义：[接口文档](../../API文档/接口文档.md)
- 需求来源总览：[系统需求](../../产品文档/系统需求.md)

本文档说明如何从 `DIDP_PROJECT_WORKSPACE` 导出工程中提取指标定义和 SQL 模板，用于填充 `t_metric_definition` 表。

## 1. 数据源概览

DIDP 工程包含两类核心数据：

| 数据源 | 路径 | 用途 |
|-------|------|------|
| **指标元数据** | `dmp_show_ind_info_*.txt` | 指标 ID、名称、描述、单位、频率等 |
| **指标 SQL** | `DIDP_PROJECT_WORKSPACE/KJ2023_11/1.0/SCH_FDM_IND_*/` | 指标计算逻辑 SQL |

---

## 2. 指标元数据文件结构

### 2.1 文件格式

- **文件**: `dmp_show_ind_info_20260123.txt`
- **分隔符**: `\x1b` (ASCII 27, ESC 字符)
- **编码**: UTF-8
- **行数**: ~2659 条指标

### 2.2 字段映射

| 序号 | 源字段名 | 目标字段 | 说明 |
|-----|---------|---------|------|
| 0 | `IND_E_NAME` | `metric_id` | 指标编码，如 `A000047` |
| 1 | `IND_NAME` | `metric_name` | 指标名称 |
| 2 | `FIRST_THEME` | `category` | 一级主题分类 |
| 3 | `SECOND_THEME` | - | 二级主题（可选用） |
| 4 | `FREQUEN` | `frequency` | 频率：日/月/季/年 |
| 5 | `UNIT` | `unit` | 单位：%/元/万元/户 |
| 6 | `IND_DESC` | `description` | 指标描述（重要） |
| 7 | `MIX_CAL_RULE` | - | 混合计算规则 |
| 8 | `BUSINESS_CLIB` | - | 业务口径 |

### 2.3 解析示例

```python
DELIMITER = "\x1b"

def parse_line(line: str) -> dict:
    parts = line.strip().split(DELIMITER)
    return {
        "metric_id": parts[0],
        "metric_name": parts[1],
        "category": parts[2],
        "frequency": parts[4],
        "unit": parts[5],
        "description": parts[6],
    }
```

---

## 3. SQL 模板文件结构

### 3.1 目录组织

```
DIDP_PROJECT_WORKSPACE/
└── KJ2023_11/
    └── 1.0/
        ├── SCH_FDM_IND_CW_YW/          # 业务指标
        │   └── SCH_FDM_IND_CW_YW.F_MID_INDEX_RESULT/
        │       ├── 005_..._A000047.sql
        │       ├── 005_..._A000048.sql
        │       └── ...
        ├── SCH_FDM_IND_CW_CW/          # 财务指标
        ├── SCH_FDM_IND_CW_KH/          # 客户指标
        ├── SCH_FDM_IND_CW_FX/          # 风险指标
        ├── SCH_FDM_IND_YY_GY/          # 运营-柜员
        └── SCH_ADM_IND_*/              # 加载层(不含计算逻辑)
```

### 3.2 业务分类代码

| 代码 | 含义 | 目录示例 |
|-----|------|---------|
| `CW_YW` | 财务-业务 | `SCH_FDM_IND_CW_YW` |
| `CW_CW` | 财务-财务 | `SCH_FDM_IND_CW_CW` |
| `CW_KH` | 财务-客户 | `SCH_FDM_IND_CW_KH` |
| `CW_FX` | 财务-风险 | `SCH_FDM_IND_CW_FX` |
| `YY_GY` | 运营-柜员 | `SCH_FDM_IND_YY_GY` |
| `YY_SB` | 运营-设备 | `SCH_FDM_IND_YY_SB` |

### 3.3 文件命名规则

```
005_SCH_FDM_IND_CW_YW_F_MID_INDEX_RESULT_1_A000047.sql
 │              │              │           │
 │              │              │           └─ 指标代码
 │              │              └─ 目标表名
 │              └─ 业务分类
 └─ 执行顺序号
```

### 3.4 SQL 结构分析

典型的指标 SQL 包含以下部分：

```sql
-- 1. 清除旧数据
DELETE FROM FDMDATA.F_MID_INDEX_RESULT 
WHERE ZTETL_DT='[DATE]' AND INDEX_CODE='A000047';

-- 2. 插入新计算结果
INSERT INTO FDMDATA.F_MID_INDEX_RESULT(
    DATA_DT, ORG_NO, ORG_NO_MAP, CCY,
    INDEX_CODE, INDEX_NAME, INDEX_VALUE,
    MONTH_TO_DATE, QUARTER_TO_DATE, YEAR_TO_DATE, ZTETL_DT
)
SELECT
    '[DATE]' AS DATA_DT,
    ORG_NO,
    ORG_NO_MAP,
    CCY,
    'A000047' AS INDEX_CODE,
    '各项存款' AS INDEX_NAME,
    SUM(column_name) AS INDEX_VALUE,  -- 核心计算逻辑
    ...
FROM source_table
WHERE conditions
GROUP BY ...
```

### 3.5 变量占位符

| 占位符 | 含义 | 替换示例 |
|-------|------|---------|
| `[DATE]` | 业务日期 | `'2026-01-28'` |
| `ZTETL_DT` | ETL 时间戳 | 同 `[DATE]` |

---

## 4. 提取策略

### 4.1 核心逻辑提取

从 SQL 中提取 **SELECT 子句的计算表达式**，作为 `sql_template`：

**原始 SQL:**
```sql
SELECT SUM(DEP_BAL) AS INDEX_VALUE
FROM FDMDATA.F_MID_DEP_TB
WHERE DATA_DT = '[DATE]'
GROUP BY ORG_NO
```

**提取后的 sql_template:**
```sql
SELECT ORG_NO, SUM(DEP_BAL) AS value
FROM fdmdata.f_mid_dep_tb
WHERE data_dt = :date
GROUP BY ORG_NO
```

### 4.2 SQL 适配要点

| 原始 SQL 特征 | 适配处理 |
|--------------|---------|
| `'[DATE]'` 占位符 | 替换为 `:date` 参数 |
| `FDMDATA.` schema | 根据目标库调整 |
| Greenplum 语法 | 转换为 PostgreSQL 兼容语法 |
| INSERT 语句 | 只保留 SELECT 部分 |

### 4.3 复杂度分类

| 类型 | 特征 | 处理建议 |
|-----|------|---------|
| **简单聚合** | `SUM(col) FROM single_table` | 可自动提取 |
| **多表关联** | `JOIN` 多个基础表 | 需人工审核 |
| **派生计算** | 引用其他指标 `{{A00xxxx}}` | 需解析依赖 |
| **复杂逻辑** | CASE WHEN / 子查询嵌套 | 需重构简化 |

---

## 5. 自动提取脚本

### 5.1 脚本功能

`scripts/extract_metric_sql.py` 实现以下功能：

1. 扫描 `SCH_FDM_IND_*` 目录下的 SQL 文件
2. 从文件名提取指标代码
3. 解析 SQL 内容，提取 SELECT 核心逻辑
4. 更新 `t_metric_definition.sql_template` 字段

### 5.2 使用方法

```bash
# 提取并更新数据库
python scripts/extract_metric_sql.py

# 仅预览提取结果（不写库）
python scripts/extract_metric_sql.py --dry-run
```

---

## 6. 数据质量检查

### 6.1 覆盖率统计

```sql
-- 检查有 SQL 模板的指标数量
SELECT 
    COUNT(*) AS total,
    COUNT(sql_template) AS with_sql,
    COUNT(*) - COUNT(sql_template) AS without_sql
FROM t_metric_definition;
```

### 6.2 常见问题

| 问题 | 原因 | 解决方案 |
|-----|------|---------|
| 找不到匹配的 SQL 文件 | 指标可能是派生指标 | 检查 `MIX_CAL_RULE` 字段 |
| SQL 语法不兼容 | Greenplum/PostgreSQL 差异 | 手动调整语法 |
| 依赖表不存在 | 基础表未导入 | 先导入依赖的基础表 |

---

## 7. 附录

### 7.1 目录统计

| 目录 | SQL 文件数 |
|-----|-----------|
| `SCH_FDM_IND_CW_YW` | ~997 |
| `SCH_FDM_IND_CW_CW` | ~483 |
| `SCH_FDM_IND_CW_KH` | ~289 |
| `SCH_FDM_IND_CW_FX` | ~307 |
| `SCH_FDM_IND_YY_*` | ~150 |
| **合计** | ~2200+ |

### 7.2 相关脚本

| 脚本 | 用途 |
|-----|------|
| `scripts/import_metrics_from_didp.py` | 导入指标元数据 |
| `scripts/extract_metric_sql.py` | 提取 SQL 模板 |
| `app/ai/semantic/schema_sync.py` | 生成向量嵌入 |

---

## 8. 数据仓库分层架构

### 8.1 数据层级说明

DIDP 采用标准的数据仓库分层架构：

| 层级 | Schema | 英文全称 | 中文含义 | 用途 |
|-----|--------|---------|---------|------|
| **ODS** | `ODSFILE` | Operational Data Store | 操作数据存储 | 原始数据落地，保持源系统原貌 |
| **SDM** | `SDMDATA` | Source Data Mart / Standard Data Model | 源数据层/标准数据模型 | 清洗后的标准化数据 |
| **FDM** | `FDMDATA` | Foundation Data Model | 基础数据模型 | 加工汇总的宽表/主题表 |
| **ADM** | `ADMDATA` | Application Data Mart | 应用数据集市 | 面向应用的结果表 |

```
业务系统 → ODS(原始) → SDMDATA(标准化) → FDMDATA(汇总宽表) → ADMDATA(指标结果)
```

### 8.2 META_DATA 目录结构

`META_DATA/` 目录包含大量业务表的 JSON 定义：

| 目录 | 表数量 | 说明 |
|-----|--------|------|
| `META_DATA/SDMDATA/` | ~290个 | 源数据层表结构 |
| `META_DATA/INPUTFILE/` | ~318个 | 输入文件表结构 |
| `META_DATA/FDMDATA_INPUT/` | 7个 | FDM层输入表 |
| `META_DATA/STADATA/` | ~295个 | 统计数据表 |
| `META_DATA/ODSFILE/` | ~139个 | ODS层表 |

### 8.3 JSON 表定义格式

每个 JSON 文件定义表的字段结构，包含以下属性：

| 属性 | 说明 |
|-----|------|
| `column_name` | 字段名 |
| `column_desc` | 字段中文描述 |
| `col_type` | 数据类型 |
| `col_length` | 字段长度 |
| `pk_flag` | 主键标志 |
| `null_flag` | 是否可空 |

---

## 9. 指标数据来源分析

### 9.1 数据层引用统计

通过分析指标 SQL 文件，统计各数据层的引用频次：

| 数据层 | 引用次数 | 占比 |
|-------|---------|------|
| **FDMDATA** (基础模型层) | 3690 | 67.9% |
| **SDMDATA** (源数据层) | 1746 | 32.1% |
| ADMDATA (应用层) | 5 | <0.1% |

### 9.2 核心依赖表 TOP 15

| 排名 | 表名 | 引用次数 | 说明 |
|-----|------|---------|------|
| 1 | `FDMDATA.F_MID_INDEX_RESULT` | 1784 | 指标结果表（派生计算） |
| 2 | `FDMDATA.F_MID_ORG_TREE` | 1024 | 机构维度表 |
| 3 | `SDMDATA.S_ODS_G_C_DIM_DATE` | 672 | 日期维度表 |
| 4 | `FDMDATA.F_MID_INDEX_RESULT_DIM` | 517 | 多维度指标结果 |
| 5 | `FDMDATA.F_MID_INDEX_RESULT_DERIVE` | 452 | 派生指标结果 |
| 6 | `FDMDATA.F_MID_ORG_TREE_K` | 370 | 机构扩展维度 |
| 7 | **`FDMDATA.F_MID_LOAN_TB`** | 350 | **贷款宽表** ⭐ |
| 8 | `FDMDATA.F_MID_SXQJ_A` | 254 | 授信区间维度 |
| 9 | **`FDMDATA.F_MID_DEP_TB`** | 142 | **存款宽表** ⭐ |
| 10 | `FDMDATA.F_MID_DKCP_A` | 122 | 贷款产品维度 |
| 11 | `FDMDATA.F_MID_KHFL_A` | 116 | 客户分类维度 |
| 12 | `SDMDATA.S_ODS_G_B_CIF_BASIC_INFO` | 110 | 客户基本信息 |
| 13 | `SDMDATA.S_MMS_DMP_PUB_CUST_TAG_ALL` | 110 | 客户标签 |

### 9.3 核心结论

指标计算主要依赖 FDMDATA 层（占 68%），核心表包括：
- `F_MID_DEP_TB` - 存款宽表
- `F_MID_LOAN_TB` - 贷款宽表  
- `F_MID_ORG_TREE` - 机构维度表
- `F_MID_INDEX_RESULT` - 指标结果表（用于派生指标）

---

## 10. 数据导入策略

### 10.1 不建议全量导入的原因

| 问题 | 说明 |
|-----|------|
| **表数量巨大** | SDMDATA 290+ 表，总共 600+ 表 |
| **向量化压力** | 每张表的每个字段都要生成向量嵌入，成本高 |
| **语义匹配混乱** | 表太多，用户问"存款"可能匹配到几十张表 |
| **数据同步成本** | 这些表的数据需要持续同步，维护成本高 |

### 10.2 推荐方案：两层漏斗模型

```
┌─────────────────────────────────────────────────────┐
│  用户问题: "查询本月各网点存款余额"                    │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  第一层：指标定义表 (t_metric_definition)             │
│  ├── 存款余额 → sql_template (基于 F_MID_DEP_TB)     │
│  └── 向量匹配：找到最相关的指标                       │
└─────────────────────────────────────────────────────┘
                         │ 匹配成功 → 直接用 sql_template
                         │ 匹配失败 → 降级到表级查询
                         ▼
┌─────────────────────────────────────────────────────┐
│  第二层：核心宽表 (仅 3-5 张)                         │
│  ├── F_MID_DEP_TB   (存款)                          │
│  ├── F_MID_LOAN_TB  (贷款)                          │
│  └── F_MID_ORG_TREE (机构)                          │
└─────────────────────────────────────────────────────┘
```

### 10.3 具体实施建议

**第一层 - 指标级匹配** (优先)
- 2659 个指标定义 + 向量嵌入
- 匹配成功直接执行 `sql_template`

**第二层 - 宽表级匹配** (兜底)
- 只导入 3-5 张核心宽表的结构和数据
- `F_MID_DEP_TB`, `F_MID_LOAN_TB`, `F_MID_ORG_TREE`
- 当指标匹配不到时，AI 基于这几张表自由生成 SQL

### 10.4 方案优势

| 优势 | 说明 |
|-----|------|
| **向量化成本低** | 只有指标 + 核心表字段需要嵌入 |
| **语义匹配精准** | 先匹配指标，再匹配表 |
| **数据维护简单** | 只需维护核心宽表 |
| **查询性能优** | 核心宽表已预聚合，查询效率高 |
