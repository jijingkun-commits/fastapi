"""扩展指标定义脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL

METRICS = [
    # 存款类
    ("DEP_003", "活期存款余额", "活期余额,活期存款", "统计期末全行活期类存款的账面余额合计。",
     "SELECT SUM(acct_bal) as 活期存款余额 FROM fdmdata.f_mid_dep_tb WHERE fix_cur_ind = '0' AND data_dt = '${data_dt}'",
     "存款", "元"),
    ("DEP_004", "存款户数", "存款账户数,储蓄户数", "统计期末存款账户总数（按账号去重）。",
     "SELECT COUNT(DISTINCT dep_acct_no) as 存款户数 FROM fdmdata.f_mid_dep_tb WHERE data_dt = '${data_dt}'",
     "存款", "户"),
    ("DEP_005", "日均存款余额", "日均存款,平均存款", "统计期末全行存款的日均余额。",
     "SELECT SUM(std_y_avg_bal) as 日均存款余额 FROM fdmdata.f_mid_dep_tb WHERE data_dt = '${data_dt}'",
     "存款", "元"),
    ("DEP_006", "分机构存款余额", "各机构存款,分行存款", "按机构统计存款余额分布。",
     "SELECT org_no as 机构代码, level7_val as 机构名称, SUM(acct_bal) as 存款余额 FROM fdmdata.f_mid_dep_tb WHERE data_dt = '${data_dt}' GROUP BY org_no, level7_val ORDER BY 存款余额 DESC",
     "存款", "元"),
    ("DEP_007", "对公存款余额", "公司存款,企业存款", "统计期末对公客户存款余额。",
     "SELECT SUM(acct_bal) as 对公存款余额 FROM fdmdata.f_mid_dep_tb WHERE cust_type_cd = '2' AND data_dt = '${data_dt}'",
     "存款", "元"),
    ("DEP_008", "个人存款余额", "零售存款,私人存款", "统计期末个人客户存款余额。",
     "SELECT SUM(acct_bal) as 个人存款余额 FROM fdmdata.f_mid_dep_tb WHERE cust_type_cd = '1' AND data_dt = '${data_dt}'",
     "存款", "元"),
    # 贷款类
    ("LOAN_003", "正常贷款余额", "正常类贷款,一类贷款", "统计期末五级分类为正常的贷款本金余额。",
     "SELECT SUM(prin_bal) as 正常贷款余额 FROM fdmdata.f_mid_loan_tb WHERE five_class_cd = '1' AND data_dt = '${data_dt}'",
     "贷款", "元"),
    ("LOAN_004", "关注类贷款余额", "关注贷款,二类贷款", "统计期末五级分类为关注的贷款本金余额。",
     "SELECT SUM(prin_bal) as 关注类贷款余额 FROM fdmdata.f_mid_loan_tb WHERE five_class_cd = '2' AND data_dt = '${data_dt}'",
     "贷款", "元"),
    ("LOAN_005", "逾期贷款余额", "逾期贷款,过期贷款", "统计期末本金逾期天数大于0的贷款余额。",
     "SELECT SUM(prin_bal) as 逾期贷款余额 FROM fdmdata.f_mid_loan_tb WHERE prin_ovrd_days > 0 AND data_dt = '${data_dt}'",
     "贷款", "元"),
    ("LOAN_006", "贷款户数", "贷款账户数,信贷户数", "统计期末贷款账户总数。",
     "SELECT COUNT(DISTINCT duebill_no) as 贷款户数 FROM fdmdata.f_mid_loan_tb WHERE data_dt = '${data_dt}'",
     "贷款", "户"),
    ("LOAN_007", "分机构贷款余额", "各机构贷款,分行贷款", "按机构统计贷款余额分布。",
     "SELECT org_cd as 机构代码, level7_val as 机构名称, SUM(prin_bal) as 贷款余额 FROM fdmdata.f_mid_loan_tb WHERE data_dt = '${data_dt}' GROUP BY org_cd, level7_val ORDER BY 贷款余额 DESC",
     "贷款", "元"),
    ("LOAN_008", "分行业贷款余额", "行业贷款,行业分布", "按行业统计贷款余额分布。",
     "SELECT indu_type_cd as 行业代码, SUM(prin_bal) as 贷款余额 FROM fdmdata.f_mid_loan_tb WHERE data_dt = '${data_dt}' AND indu_type_cd IS NOT NULL GROUP BY indu_type_cd ORDER BY 贷款余额 DESC",
     "贷款", "元"),
    ("LOAN_009", "不良贷款率", "不良率,NPL比率", "不良贷款余额占贷款总额的比例。",
     "SELECT ROUND(SUM(CASE WHEN five_class_cd IN ('3', '4', '5') THEN prin_bal ELSE 0 END) * 100.0 / NULLIF(SUM(prin_bal), 0), 2) as 不良贷款率 FROM fdmdata.f_mid_loan_tb WHERE data_dt = '${data_dt}'",
     "贷款", "%"),
    ("LOAN_010", "利息收入", "贷款利息,利息", "统计期末应收利息总额。",
     "SELECT SUM(int_amt2) as 利息收入 FROM fdmdata.f_mid_loan_tb WHERE data_dt = '${data_dt}'",
     "贷款", "元"),
    # 综合类
    ("COMP_001", "存贷比", "贷存比", "贷款余额与存款余额的比例。",
     "SELECT ROUND((SELECT SUM(prin_bal) FROM fdmdata.f_mid_loan_tb WHERE data_dt = '${data_dt}') * 100.0 / NULLIF((SELECT SUM(acct_bal) FROM fdmdata.f_mid_dep_tb WHERE data_dt = '${data_dt}'), 0), 2) as 存贷比",
     "综合", "%"),
]

def main():
    print("扩展指标定义...")
    engine = create_engine(str(DATABASE_URL))
    
    insert_sql = text("""
        INSERT INTO t_metric_definition 
            (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
        VALUES 
            (:metric_id, :metric_name, :aliases, :description, :sql_template, :category, :unit, true)
        ON CONFLICT (metric_id) DO UPDATE SET 
            metric_name = EXCLUDED.metric_name,
            aliases = EXCLUDED.aliases,
            description = EXCLUDED.description,
            sql_template = EXCLUDED.sql_template,
            category = EXCLUDED.category,
            unit = EXCLUDED.unit,
            updated_at = NOW()
    """)
    
    with engine.begin() as conn:
        for m in METRICS:
            params = {
                "metric_id": m[0],
                "metric_name": m[1],
                "aliases": m[2],
                "description": m[3],
                "sql_template": m[4],
                "category": m[5],
                "unit": m[6],
            }
            conn.execute(insert_sql, params)
            print(f"  + {m[0]}: {m[1]}")
    
    # 统计
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM t_metric_definition")).scalar()
        print(f"\n共 {result} 个指标定义")

if __name__ == "__main__":
    main()
