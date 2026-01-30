"""聊天工具模块（中文注释）。

提供 Agent 可调用的各类工具：搜索、SQL 查询、Python 执行、绘图等。
"""
import os
import json
import logging
from pydantic import BaseModel, Field
from langchain.tools import tool

from app.ai import config as ai_config
from app.db.session import get_db_context
from app.models.chat_asset import AssetType

# 可选依赖导入
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import matplotlib
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    matplotlib = None
    plt = None
    sns = None

logger = logging.getLogger(__name__)

# 内置搜索工具 TavilySearch（可选）
search_tool = None
if ai_config.TAVILY_API_KEY:
    try:
        from langchain_tavily import TavilySearch
        search_tool = TavilySearch(max_results=5, tavily_api_key=ai_config.TAVILY_API_KEY)
        logger.info("TavilySearch 工具已加载")
    except ImportError:
        logger.warning("langchain-tavily 未安装，搜索工具不可用")

from sqlalchemy import text
from langgraph.types import interrupt
from app.db.session import analytics_engine  # 使用业务数据库连接

# 定义结构化参数模型
class SQLQuerySchema(BaseModel):
    sql_query: str = Field(description="用于从 PostgreSQL 提取数据的 SQL 查询语句。")

# 封装为 LangGraph 工具
@tool(args_schema=SQLQuerySchema)
def sql_inter(sql_query: str) -> str:
    """
    当用户需要进行数据库查询工作时，请调用该函数。
    该函数用于在指定PostgreSQL服务器上运行一段SQL代码，完成数据查询相关工作，
    并且当前函数是使用SQLAlchemy连接PostgreSQL数据库。
    本函数只负责运行SQL代码并进行数据查询，若要进行数据提取，则使用另一个extract_data函数。
    
    支持：
    - 模板 SQL：使用 {{metric_name}} 语法引用预定义指标
    - 数据访问控制：自动检查表权限
    
    :param sql_query: 字符串形式的SQL查询语句
    :return：sql_query在PostgreSQL中的运行结果。
    """
    # 模板 SQL 处理
    if "{{" in sql_query and "}}" in sql_query:
        sql_query = _expand_template_sql(sql_query)
    
    # 数据访问控制检查
    try:
        from app.ai.semantic.data_access_control import get_access_control
        dac = get_access_control()
        is_valid, error_msg = dac.validate_sql(sql_query)
        if not is_valid:
            logger.warning(f"SQL 访问被拒绝: {error_msg}")
            return json.dumps({"error": error_msg, "access_denied": True}, ensure_ascii=False)
    except ImportError:
        pass  # 忽略导入错误
    
    # 检查是否需要人工审核
    if ai_config.SQL_REQUIRE_APPROVAL:
        logger.info("SQL 查询需要人工审核，等待用户确认...")
        
        # 发送 interrupt 请求，暂停执行等待用户确认
        response = interrupt({
            "action_requests": [{
                "name": "sql_inter",
                "args": {"sql_query": sql_query},
                "description": f"即将执行 SQL 查询：{sql_query[:200]}{'...' if len(sql_query) > 200 else ''}"
            }],
            "review_configs": [{
                "action_name": "sql_inter",
                "allowed_decisions": ["approve", "edit", "reject"]
            }]
        })
        
        # 处理用户响应
        response_type = response.get("type", "accept")
        
        if response_type == "reject":
            logger.info("用户拒绝了 SQL 查询")
            return json.dumps({"error": "用户拒绝了该查询操作", "rejected": True}, ensure_ascii=False)
        elif response_type == "edit":
            # 使用用户编辑后的 SQL
            edited_args = response.get("args", {})
            sql_query = edited_args.get("sql_query", sql_query)
            logger.info("用户编辑了 SQL 查询: %s", sql_query[:100])
        else:
            logger.info("用户批准了 SQL 查询")
    
    # 执行 SQL 查询（在业务数据库 data_db 上执行）
    try:
        with analytics_engine.connect() as conn:
            result = conn.execute(text(sql_query))
            # 获取列名
            columns = result.keys()
            # 转换为字典列表
            result_list = [dict(zip(columns, row)) for row in result.fetchall()]
            return json.dumps(result_list, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error("SQL 查询执行失败: %s", e)
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _expand_template_sql(sql_query: str) -> str:
    """展开模板 SQL 中的指标引用。
    
    支持语法：{{metric_name}} 会被替换为指标的 SQL 片段
    """
    import re
    
    # 查找所有 {{...}} 模式
    pattern = r'\{\{(\w+)\}\}'
    
    def replace_metric(match):
        metric_name = match.group(1)
        # 从 data_intent_helpers 获取指标信息
        try:
            from app.ai.workflow.data_intent_helpers import get_metric_info
            metric = get_metric_info(metric_name)
            if metric and metric.get("formula"):
                return metric["formula"]
        except Exception:
            pass
        # 返回原始如果找不到
        return match.group(0)
    
    return re.sub(pattern, replace_metric, sql_query)

# 定义结构化参数
class ExtractQuerySchema(BaseModel):
    sql_query: str = Field(description="用于从 PostgreSQL 提取数据的 SQL 查询语句。")
    df_name: str = Field(description="指定用于保存结果的 pandas 变量名称（字符串形式）。")

from typing import Dict, Any
from langchain_core.runnables.config import RunnableConfig

# 用于存储提取的 DataFrame 的全局字典
# 结构: {thread_id: {df_name: DataFrame}}
extracted_dataframes: Dict[str, Dict[str, Any]] = {}


def cleanup_thread_dataframes(thread_id: str) -> bool:
    """清理指定对话的 DataFrame 缓存。
    
    当对话被删除时调用，释放内存中的数据对象。
    
    Args:
        thread_id: 对话线程 ID
        
    Returns:
        是否成功清理（True=存在并已删除，False=不存在）
    """
    if thread_id in extracted_dataframes:
        del extracted_dataframes[thread_id]
        logger.info("已清理对话 DataFrame 缓存: thread_id=%s", thread_id)
        return True
    return False

# 注册为 Agent 工具
@tool(args_schema=ExtractQuerySchema)
def extract_data(sql_query: str, df_name: str, config: RunnableConfig) -> str:
    """
    用于在PostgreSQL数据库中提取一张表到当前Python环境中，注意，本函数只负责数据表的提取，
    并不负责数据查询，若需要在PostgreSQL中进行数据查询，请使用sql_inter函数。
    同时需要注意，编写外部函数的参数消息时，必须是满足json格式的字符串，
    :param sql_query: 字符串形式的SQL查询语句，用于提取PostgreSQL中的某张表。
    :param df_name: 将PostgreSQL数据库中提取的表格进行本地保存时的变量名，以字符串形式表示。
    :return：表格读取和保存结果
    """
    if pd is None:
        return "错误: pandas 未安装，无法执行数据提取操作"
    
    # 获取 thread_id
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "错误: 无法获取对话 ID，无法保存数据"

    try:
        # 使用业务数据库连接读取数据
        df = pd.read_sql(sql_query, analytics_engine)
        
        # 初始化该 thread 的存储空间
        if thread_id not in extracted_dataframes:
            extracted_dataframes[thread_id] = {}
            
        # 将 DataFrame 保存到该 thread 的字典中
        extracted_dataframes[thread_id][df_name] = df
        
        shape_info = f"，数据形状: {df.shape}" if hasattr(df, 'shape') else ""
        return f"成功创建 pandas 对象 `{df_name}`，包含 {len(df)} 行数据{shape_info}。"
    except Exception as e:
        error_msg = str(e)
        # 截断过长的错误信息
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        return f" 执行失败：{error_msg}"
    

# Python代码执行工具
class PythonCodeInput(BaseModel):
    py_code: str = Field(description="一段合法的 Python 代码字符串，例如 '2 + 2' 或 'x = 3\\ny = x * 2'")


@tool(args_schema=PythonCodeInput)
def python_inter(py_code: str, config: RunnableConfig):
    """
    当用户需要编写Python程序并执行时，请调用该函数。
    该函数可以执行一段Python代码并返回最终结果，需要注意，本函数只能执行非绘图类的代码，若是绘图相关代码，则需要调用fig_inter函数运行。
    """    
    import traceback
    
    # 获取 thread_id
    thread_id = config.get("configurable", {}).get("thread_id")
    
    g = globals().copy()
    
    # 注入该 thread 之前提取的 DataFrame
    if thread_id and thread_id in extracted_dataframes:
        g.update(extracted_dataframes[thread_id])
    
    try:
        # 尝试如果是表达式，则返回表达式运行结果
        result = eval(py_code, g)
        # 确保返回值是可序列化的字符串
        if isinstance(result, (pd.DataFrame, pd.Series)):
            return f"执行成功，返回数据形状: {result.shape if hasattr(result, 'shape') else 'N/A'}"
        elif isinstance(result, (dict, list)):
            try:
                return json.dumps(result, ensure_ascii=False, default=str)
            except:
                return str(result)
        else:
            return str(result)
    except Exception as eval_error:
        # 若报错，则先测试是否是对相同变量重复赋值
        global_vars_before = set(g.keys())
        try:            
            exec(py_code, g)
        except Exception as exec_error:
            error_msg = str(exec_error)
            # 截断过长的错误信息
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."
            return f"代码执行时报错: {error_msg}"
        global_vars_after = set(g.keys())
        new_vars = global_vars_after - global_vars_before
        # 若存在新变量
        if new_vars:
            result = {}
            for var in new_vars:
                try:
                    val = g[var]
                    
                    # 如果生成了新的 DataFrame，也保存到当前 thread 的上下文
                    if isinstance(val, pd.DataFrame) and thread_id:
                        if thread_id not in extracted_dataframes:
                            extracted_dataframes[thread_id] = {}
                        extracted_dataframes[thread_id][var] = val
                    
                    # 对于复杂对象，只返回类型和基本信息
                    if isinstance(val, (pd.DataFrame, pd.Series)):
                        result[var] = f"<{type(val).__name__} shape={val.shape if hasattr(val, 'shape') else 'N/A'}>"
                    elif isinstance(val, (dict, list)):
                        try:
                            result[var] = json.dumps(val, ensure_ascii=False, default=str)[:200]
                        except:
                            result[var] = f"<{type(val).__name__} (无法序列化)>"
                    else:
                        result[var] = str(val)[:200]  # 限制长度
                except Exception:
                    result[var] = f"<{type(g[var]).__name__} (无法获取值)>"
            try:
                return json.dumps(result, ensure_ascii=False)
            except:
                return str(result)
        else:
            return "已经顺利执行代码"

class FigCodeInput(BaseModel):
    py_code: str = Field(description="要执行的 Python 绘图代码，必须使用 matplotlib/seaborn 创建图像并赋值给变量")
    fname: str = Field(description="图像对象的变量名，例如 'fig'，用于从代码中提取并保存为图片")

@tool(args_schema=FigCodeInput)
def fig_inter(py_code: str, fname: str, config: RunnableConfig) -> str:
    """
    **重要**：函数返回 JSON 格式结果，包含 'image_url' 字段。
    你 **必须** 在最终回复中，使用 Markdown 图片语法 `![生成的图表](image_url)` 将该图片展示出来。
    不要只说"图表已生成"，一定要把图片显示出来。

    注意：
    1. 所有绘图代码必须创建一个图像对象，并将其赋值为指定变量名（例如 `fig`）。
    2. 必须使用 `fig = plt.figure()` 或 `fig = plt.subplots()`。
    3. 不要使用 `plt.show()`。
    4. 请确保代码最后调用 `fig.tight_layout()`。
    5. 所有绘图代码中，坐标轴标签（xlabel、ylabel）、标题（title）、图例（legend）等文本内容，必须使用英文描述。
    """
    import io
    import time
    from uuid import uuid4
    
    # 获取 thread_id 和 user_id
    thread_id = config.get("configurable", {}).get("thread_id")
    user_id = config.get("configurable", {}).get("user_id")
    
    current_backend = matplotlib.get_backend()
    matplotlib.use('Agg')

    local_vars = {"plt": plt, "pd": pd, "sns": sns}

    try:
        g = globals().copy()
        
        # 注入该 thread 之前提取的 DataFrame
        if thread_id and thread_id in extracted_dataframes:
            g.update(extracted_dataframes[thread_id])
            
        exec(py_code, g, local_vars)
        g.update(local_vars)

        fig = local_vars.get(fname, None)
        if fig:
            # 生成唯一文件名
            timestamp = int(time.time() * 1000)
            image_filename = f"{fname}_{timestamp}_{uuid4().hex[:8]}.png"
            
            # 保存到内存
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
            img_buffer.seek(0)
            img_bytes = img_buffer.getvalue()
            
            # 尝试上传到 MinIO
            try:
                from app.services.asset_service import get_asset_service
                
                asset_service = get_asset_service()
                
                # 路径格式: {user_id}/{thread_id}/charts/{filename}
                user_prefix = str(user_id) if user_id else "anonymous"
                thread_prefix = thread_id if thread_id else "default"
                object_key = f"{user_prefix}/{thread_prefix}/charts/{image_filename}"
                
                asset_service.ensure_bucket()
                asset_service.client.put_object(
                    bucket_name=ai_config.MINIO_BUCKET_ASSETS,
                    object_name=object_key,
                    data=io.BytesIO(img_bytes),
                    length=len(img_bytes),
                    content_type="image/png"
                )
                
                logger.info("图片已上传到 MinIO: %s", object_key)
                
                # 保存资产元数据到数据库
                try:
                    with get_db_context() as db:
                        asset_service.register_existing_asset(
                            db=db,
                            object_key=object_key,
                            chat_id=thread_id or "unknown",
                            user_id=user_id,
                            asset_type=AssetType.CHART,
                            file_name=image_filename,
                        )
                    logger.info("图表资产元数据已保存到数据库: %s", object_key)
                except Exception as db_error:
                    logger.warning("保存资产元数据失败（不影响图表显示）: %s", db_error)
                
                # 使用代理 URL（权限校验 + 永不过期）
                # 统一使用相对路径，前端通过 Next.js rewrites 代理到后端
                proxy_url = asset_service.get_proxy_url(object_key)
                
                # 实时流式发送图片事件，让前端立即显示（不依赖 LLM 输出 Markdown）
                try:
                    from langgraph.config import get_stream_writer
                    from app.ai.events import emit_result
                    writer = get_stream_writer()
                    emit_result(writer, "image", {"url": proxy_url}, "图表已生成", "fig_inter")
                    logger.info("已通过 emit_result 发送图片事件: %s", proxy_url)
                except Exception as emit_error:
                    # 在非流式上下文中调用会失败，记录日志便于排查
                    logger.warning(
                        "emit_result 失败（图片已生成但无法实时推送）: url=%s, error=%s", 
                        proxy_url, 
                        emit_error
                    )
                
                return json.dumps({
                    "status": "success",
                    "image_url": proxy_url,
                    "message": "图表生成成功"
                }, ensure_ascii=False)

                
            except Exception as minio_error:
                # 如果 MinIO 上传失败，回退到本地保存
                logger.error(
                    "MinIO 上传失败，回退到本地保存: %s", 
                    minio_error, 
                    exc_info=True  # 记录完整堆栈便于排查
                )
                
                base_dir = ai_config.PUBLIC_DIR
                images_dir = os.path.join(base_dir, "images")
                os.makedirs(images_dir, exist_ok=True)
                
                abs_path = os.path.join(images_dir, image_filename)
                rel_path = os.path.join("images", image_filename)
                
                with open(abs_path, 'wb') as f:
                    f.write(img_bytes)
                
                # 使用相对路径，与 MinIO 资产保持一致
                return json.dumps({
                    "status": "success_local",
                    "image_url": f"/{rel_path}", 
                    "message": "图表保存在本地 Public 目录"
                }, ensure_ascii=False)

        else:
            return json.dumps({"status": "error", "message": "图像对象未找到"}, ensure_ascii=False)
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        return f" 执行失败：{error_msg}"
    finally:
        try:
            plt.close('all')
        except:
            pass
        matplotlib.use(current_backend)