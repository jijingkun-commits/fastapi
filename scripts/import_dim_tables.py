#!/usr/bin/env python
"""
创建维度表并导入数据
- f_mid_org_tree: 机构维度中间表
- t_ods_g_c_dim_date: 日期维度表
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(project_root / ".env")

# 数据库连接（使用 data_db）
ANALYTICS_DB_URL = os.getenv("ANALYTICS_DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/data_db")
# 转换为 psycopg 格式
DB_URL = ANALYTICS_DB_URL.replace("postgresql+psycopg://", "postgresql://")

# 数据文件路径
DATA_DIR = project_root / "docs/内部参考/数据资料"
ORG_TREE_FILE = DATA_DIR / "DMP_F_MID_ORG_TREE_20250630.txt"
DATE_DIM_FILE = DATA_DIR / "ods_g_c_dim_date_20250630.txt"

# 分隔符是 ESC 字符 (0x1b)
DELIMITER = "\x1b"

# 创建机构表 SQL
CREATE_ORG_TREE_SQL = """
DROP TABLE IF EXISTS f_mid_org_tree CASCADE;
CREATE TABLE f_mid_org_tree
(
    level7_cd VARCHAR(100),
    level7_val VARCHAR(100),
    org_no VARCHAR(100),
    org_val VARCHAR(100),
    org_lv VARCHAR(100)
);

COMMENT ON TABLE f_mid_org_tree IS '机构维度中间表';
COMMENT ON COLUMN f_mid_org_tree.level7_cd IS '7级机构代码';
COMMENT ON COLUMN f_mid_org_tree.level7_val IS '7级机构名称';
COMMENT ON COLUMN f_mid_org_tree.org_no IS '各级机构代码';
COMMENT ON COLUMN f_mid_org_tree.org_val IS '机构名称';
COMMENT ON COLUMN f_mid_org_tree.org_lv IS '机构层级';
"""

# 创建日期维度表 SQL
CREATE_DATE_DIM_SQL = """
DROP TABLE IF EXISTS t_ods_g_c_dim_date CASCADE;
CREATE TABLE t_ods_g_c_dim_date
(
    date_id DATE,
    ld_dt DATE,
    lte_dt DATE,
    lme_dt DATE,
    lqe_dt DATE,
    lye_dt DATE,
    lyse_dt DATE,
    lt_dt DATE,
    lm_dt DATE,
    lq_dt DATE,
    ly_dt DATE,
    lys_dt DATE,
    wd_id NUMERIC(10, 0),
    wd_cn_nm VARCHAR(100),
    t_id NUMERIC(10, 0),
    t_chn_nm VARCHAR(100),
    ts_dt DATE,
    te_dt DATE,
    te_ind VARCHAR(20),
    t_days NUMERIC(10, 0),
    t_t_days NUMERIC(10, 0),
    m_id NUMERIC(10, 0),
    m_cn_nm VARCHAR(100),
    ms_dt DATE,
    me_dt DATE,
    me_ind VARCHAR(20),
    m_days NUMERIC(10, 0),
    m_t_days NUMERIC(10, 0),
    q_id NUMERIC(10, 0),
    q_cn_nm VARCHAR(100),
    qs_dt DATE,
    qe_dt DATE,
    qe_ind VARCHAR(20),
    q_days NUMERIC(10, 0),
    q_t_days NUMERIC(10, 0),
    hy_id NUMERIC(10, 0),
    hy_cn_nm VARCHAR(100),
    hys_dt DATE,
    hye_dt DATE,
    hy_ind VARCHAR(20),
    hy_days NUMERIC(10, 0),
    hy_t_days NUMERIC(10, 0),
    y_id NUMERIC(10, 0),
    y_cn_nm VARCHAR(100),
    ys_dt DATE,
    ye_dt DATE,
    ye_ind VARCHAR(20),
    y_days NUMERIC(10, 0),
    y_t_days NUMERIC(10, 0),
    work_day_ind VARCHAR(20)
);

COMMENT ON TABLE t_ods_g_c_dim_date IS '日期维度表';
"""

def create_tables(conn):
    """创建表"""
    print("正在创建表...")
    with conn.cursor() as cur:
        print("  - 创建 f_mid_org_tree 表...")
        cur.execute(CREATE_ORG_TREE_SQL)
        print("  - 创建 t_ods_g_c_dim_date 表...")
        cur.execute(CREATE_DATE_DIM_SQL)
    conn.commit()
    print("表创建完成！")

def import_org_tree(conn):
    """导入机构数据"""
    print(f"\n正在导入机构数据 ({ORG_TREE_FILE})...")
    
    if not ORG_TREE_FILE.exists():
        print(f"  错误：文件不存在 {ORG_TREE_FILE}")
        return 0
    
    insert_sql = """
        INSERT INTO f_mid_org_tree (level7_cd, level7_val, org_no, org_val, org_lv)
        VALUES (%s, %s, %s, %s, %s)
    """
    
    count = 0
    errors = 0
    with conn.cursor() as cur:
        with open(ORG_TREE_FILE, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                fields = line.split(DELIMITER)
                if len(fields) != 5:
                    print(f"  警告：第 {line_no} 行字段数不正确 (期望5，实际{len(fields)}): {fields}")
                    errors += 1
                    continue
                
                try:
                    cur.execute(insert_sql, fields)
                    count += 1
                except Exception as e:
                    print(f"  错误：第 {line_no} 行插入失败: {e}")
                    errors += 1
    
    conn.commit()
    print(f"  导入完成：成功 {count} 条，失败 {errors} 条")
    return count

def parse_date(val):
    """解析日期，空值返回None"""
    if not val or val.strip() == "":
        return None
    return val.strip()

def parse_numeric(val):
    """解析数字，空值返回None"""
    if not val or val.strip() == "":
        return None
    try:
        return int(val.strip())
    except ValueError:
        return None

def import_date_dim(conn):
    """导入日期维度数据"""
    print(f"\n正在导入日期维度数据 ({DATE_DIM_FILE})...")
    
    if not DATE_DIM_FILE.exists():
        print(f"  错误：文件不存在 {DATE_DIM_FILE}")
        return 0
    
    # 50个字段的插入语句
    insert_sql = """
        INSERT INTO t_ods_g_c_dim_date (
            date_id, ld_dt, lte_dt, lme_dt, lqe_dt, lye_dt, lyse_dt,
            lt_dt, lm_dt, lq_dt, ly_dt, lys_dt,
            wd_id, wd_cn_nm, t_id, t_chn_nm, ts_dt, te_dt, te_ind, t_days, t_t_days,
            m_id, m_cn_nm, ms_dt, me_dt, me_ind, m_days, m_t_days,
            q_id, q_cn_nm, qs_dt, qe_dt, qe_ind, q_days, q_t_days,
            hy_id, hy_cn_nm, hys_dt, hye_dt, hy_ind, hy_days, hy_t_days,
            y_id, y_cn_nm, ys_dt, ye_dt, ye_ind, y_days, y_t_days, work_day_ind
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    
    # 字段类型定义：D=日期, N=数字, S=字符串 (共50个字段)
    # 索引: 0-6(7个日期), 7(lt_dt空), 8-11(4个日期), 12(N), 13(S), 14(N), 15(S), 
    #       16-17(2D), 18(S), 19-20(2N), 21(N), 22(S), 23-24(2D), 25(S), 26-27(2N),
    #       28(N), 29(S), 30-31(2D), 32(S), 33-34(2N), 35(N), 36(S), 37-38(2D), 39(S), 40-41(2N),
    #       42(N), 43(S), 44-45(2D), 46(S), 47-48(2N), 49(S)
    field_types = [
        'D', 'D', 'D', 'D', 'D', 'D', 'D',  # 0-6: date_id to lyse_dt
        'D', 'D', 'D', 'D', 'D',            # 7-11: lt_dt to lys_dt
        'N', 'S',                            # 12-13: wd_id, wd_cn_nm
        'N', 'S', 'D', 'D', 'S', 'N', 'N',  # 14-20: t_id to t_t_days
        'N', 'S', 'D', 'D', 'S', 'N', 'N',  # 21-27: m_id to m_t_days
        'N', 'S', 'D', 'D', 'S', 'N', 'N',  # 28-34: q_id to q_t_days
        'N', 'S', 'D', 'D', 'S', 'N', 'N',  # 35-41: hy_id to hy_t_days
        'N', 'S', 'D', 'D', 'S', 'N', 'N',  # 42-48: y_id to y_t_days
        'S'                                  # 49: work_day_ind
    ]
    
    count = 0
    errors = 0
    with conn.cursor() as cur:
        with open(DATE_DIM_FILE, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                fields = line.split(DELIMITER)
                # 期望50个字段
                if len(fields) != 50:
                    print(f"  警告：第 {line_no} 行字段数不正确 (期望50，实际{len(fields)})")
                    errors += 1
                    continue
                
                try:
                    # 直接按顺序映射50个字段
                    params = []
                    for i, ft in enumerate(field_types):
                        val = fields[i]
                        
                        if ft == 'D':
                            params.append(parse_date(val))
                        elif ft == 'N':
                            params.append(parse_numeric(val))
                        else:
                            params.append(val.strip() if val else None)
                    
                    cur.execute(insert_sql, params)
                    count += 1
                    
                    if count % 5000 == 0:
                        print(f"  已处理 {count} 条...")
                        conn.commit()
                        
                except Exception as e:
                    print(f"  错误：第 {line_no} 行插入失败: {e}")
                    print(f"    字段数: {len(fields)}, 字段: {fields[:5]}...")
                    errors += 1
                    if errors > 10:
                        print("  错误过多，停止导入")
                        break
    
    conn.commit()
    print(f"  导入完成：成功 {count} 条，失败 {errors} 条")
    return count

def main():
    print("=" * 60)
    print("维度表创建与数据导入工具")
    print("=" * 60)
    print(f"\n数据库: {DB_URL}")
    print(f"数据目录: {DATA_DIR}")
    
    try:
        with psycopg.connect(DB_URL) as conn:
            # 1. 创建表
            create_tables(conn)
            
            # 2. 导入机构数据
            org_count = import_org_tree(conn)
            
            # 3. 导入日期数据
            date_count = import_date_dim(conn)
            
            print("\n" + "=" * 60)
            print("导入完成！")
            print(f"  - f_mid_org_tree: {org_count} 条")
            print(f"  - t_ods_g_c_dim_date: {date_count} 条")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
