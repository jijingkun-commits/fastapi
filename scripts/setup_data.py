"""
数据仓库与元数据管理工具。

整合了由于历史原因分散的各类初始化脚本，提供统一的 CLI 入口。
用于：
1. 初始化数仓 Schema (FDM/SDM)
2. 导入基础数据 (机构、日期、事实表)
3. 初始化元数据 Schema (Chat DB)
4. 从 DIDP 导入指标定义与提取 SQL
5. 同步向量数据库
"""
import click
import subprocess
import sys
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

def run_script(script_name, description):
    """运行 scripts 目录下的 python 脚本。"""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        click.secho(f"[错误] 脚本未找到: {script_name}", fg="red")
        return False
        
    click.secho(f"\n[执行中] {description} ({script_name})...", fg="cyan", bold=True)
    
    try:
        # 传递当前环境变量
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            [sys.executable, str(script_path)],
            env=env,
            cwd=PROJECT_ROOT, # 在项目根目录运行
            check=True
        )
        click.secho(f"[成功] {description} 完成。", fg="green")
        return True
    except subprocess.CalledProcessError as e:
        click.secho(f"[失败] {description} 失败，退出码 {e.returncode}。", fg="red")
        return False

@click.group()
def cli():
    """数据仓库与元数据管理工具 (Data Warehouse Manager)"""
    pass

@cli.command()
def init_schema():
    """初始化分析库 Schema (维度表结构)"""
    run_script("create_dim_tables.py", "正在创建维度表")

@cli.command()
def import_dims():
    """导入维度数据 (机构、日期)"""
    run_script("import_dim_data.py", "正在导入维度数据")

@cli.command()
def import_facts():
    """导入事实/样本数据 (存款)"""
    run_script("import_deposit_data.py", "正在导入存款数据")

@cli.command()
def init_metrics():
    """初始化指标元数据表结构"""
    run_script("init_metric_definition.py", "正在初始化指标定义表")

@cli.command()
def import_metadata():
    """从 DIDP 文件导入指标元数据"""
    run_script("import_metrics_from_didp.py", "正在导入 DIDP 指标定义")

@cli.command()
def extract_sql():
    """从 DIDP 工程提取 SQL 模板"""
    run_script("extract_metric_sql.py", "正在提取 SQL 模板")

@cli.command()
def sync_vectors():
    """同步 Schema 和指标到向量数据库"""
    run_script("schema_sync.py", "正在同步向量数据库")

@cli.command()
def full_setup():
    """运行完整初始化流程 (建表 -> 导数 -> 元数据 -> 向量化)"""
    steps = [
        ("create_dim_tables.py", "创建维度表"),
        ("init_metric_definition.py", "初始化指标定义表"),
        ("import_dim_data.py", "导入维度数据"),
        ("import_deposit_data.py", "导入存款数据"),
        ("import_metrics_from_didp.py", "导入 DIDP 指标定义"),
        ("extract_metric_sql.py", "提取 SQL 模板"),
        ("schema_sync.py", "同步向量数据库")
    ]
    
    click.secho("\n=== 开始全量数据初始化流程 ===", fg="yellow", bold=True)
    
    for script, desc in steps:
        if not run_script(script, desc):
            click.secho("\n[终止] 流程因错误终止。", fg="red", bold=True)
            sys.exit(1)
            
    click.secho("\n[完成] 全量初始化成功完成！", fg="green", bold=True)

if __name__ == "__main__":
    cli()
