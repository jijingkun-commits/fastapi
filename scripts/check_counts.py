import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import ANALYTICS_DATABASE_URL, DATABASE_URL

def check_counts():
    print(f"Checking Analytics DB: {ANALYTICS_DATABASE_URL}")
    engine = create_engine(ANALYTICS_DATABASE_URL)
    with engine.connect() as conn:
        try:
            res = conn.execute(text("SELECT count(*) FROM t_dmp_ind_info")).scalar()
            print(f"t_dmp_ind_info count: {res}")
        except Exception as e:
            print(f"t_dmp_ind_info check failed: {e}")

        try:
            res = conn.execute(text("SELECT count(*) FROM fdmdata.f_mid_dep_tb")).scalar()
            print(f"fdmdata.f_mid_dep_tb count: {res}")
        except Exception as e:
            print(f"fdmdata.f_mid_dep_tb check failed: {e}")

        try:
            res = conn.execute(text("SELECT count(*) FROM fdmdata.f_mid_loan_tb")).scalar()
            print(f"fdmdata.f_mid_loan_tb count: {res}")
        except Exception as e:
            print(f"fdmdata.f_mid_loan_tb check failed: {e}")

if __name__ == "__main__":
    check_counts()
