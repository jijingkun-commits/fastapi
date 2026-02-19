"""文件读取工具（中文注释）。

提供两类读取能力：
1. 读取 MinIO 已上传文件（read_uploaded_file）
2. 读取仓库内本地文本文件（read，仅 admin）
"""
import io
import json
import logging
import mimetypes
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables.config import RunnableConfig

from app.core import config as ai_config
from app.services.asset_service import get_asset_service

logger = logging.getLogger(__name__)

# 可选依赖导入
try:
    import pandas as pd
except ImportError:
    pd = None


LOCAL_READ_MAX_LINES = 2000
LOCAL_READ_MAX_BYTES = 50 * 1024
LOCAL_READ_SAMPLE_BYTES = 4096
LOCAL_READ_TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "gbk", "gb2312")
LOCAL_READ_TEXT_MIME_ALLOWLIST = {
    "application/json",
    "application/ld+json",
    "application/xml",
    "application/javascript",
    "application/x-javascript",
    "application/x-sh",
    "application/x-yaml",
    "application/yaml",
}


def _discover_project_root() -> Path:
    """推断仓库根目录（以 .git 为首选锚点）。"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent.resolve()
    return current.parents[3].resolve()


PROJECT_ROOT = _discover_project_root()


def _json_response(status: str, **payload: object) -> str:
    """统一构造 JSON 字符串返回值。"""
    data = {"status": status, **payload}
    return json.dumps(data, ensure_ascii=False)


def _extract_user_id(config: Optional[RunnableConfig]) -> Optional[int]:
    """从 RunnableConfig 中提取 user_id。"""
    if not config:
        return None
    configurable = config.get("configurable") if isinstance(config, dict) else None
    if not isinstance(configurable, dict):
        return None
    user_id = configurable.get("user_id")
    try:
        if user_id is None:
            return None
        return int(user_id)
    except (TypeError, ValueError):
        return None


def _get_user_role(user_id: int) -> tuple[Optional[str], Optional[str]]:
    """根据 user_id 查询系统角色（t_user.role）。"""
    try:
        from app.db.session import get_db_context
        from app.models.user import User

        with get_db_context() as db:
            user = db.get(User, user_id)
        if not user:
            return None, "权限校验失败：用户不存在"

        role = str(getattr(user, "role", "") or "").strip().lower()
        if not role:
            return None, "权限校验失败：用户角色缺失"

        return role, None
    except Exception as exc:
        logger.exception("查询用户角色失败: user_id=%s, error=%s", user_id, exc)
        return None, "权限校验失败：无法读取用户角色"


def _resolve_local_path(path_value: str) -> tuple[Optional[Path], Optional[str]]:
    """解析并校验本地路径，确保访问范围在仓库根目录内。"""
    raw = str(path_value or "").strip()
    if not raw:
        return None, "path/file_path 不能为空"

    input_path = Path(raw).expanduser()
    if input_path.is_absolute():
        resolved = input_path.resolve(strict=False)
    else:
        resolved = (PROJECT_ROOT / input_path).resolve(strict=False)

    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        return None, f"路径越界：仅允许读取项目目录内文件（根目录: {PROJECT_ROOT}）"

    if not resolved.exists():
        return None, f"文件不存在: {resolved}"

    if resolved.is_dir():
        return None, f"目标路径是目录，暂不支持读取目录: {resolved}"

    return resolved, None


def _is_supported_text_mime(mime_type: Optional[str]) -> bool:
    """判断 MIME 类型是否属于可读文本。"""
    if not mime_type:
        return True
    return mime_type.startswith("text/") or mime_type in LOCAL_READ_TEXT_MIME_ALLOWLIST


def _detect_text_encoding(sample: bytes) -> Optional[str]:
    """基于采样内容推断文本编码。"""
    if not sample:
        return "utf-8"
    for encoding in LOCAL_READ_TEXT_ENCODINGS:
        try:
            sample.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return None


def _read_text_with_limits(
    file_path: Path,
    encoding: str,
    offset: int,
    line_limit: int,
) -> dict[str, object]:
    """按行读取文本并施加行数/字节上限。"""
    collected_lines: list[str] = []
    collected_bytes = 0
    truncated = False
    first_line_exceeds_limit = False
    next_offset: Optional[int] = None

    with file_path.open("r", encoding=encoding) as handle:
        for line_no, line in enumerate(handle, start=1):
            if line_no < offset:
                continue

            if len(collected_lines) >= line_limit:
                truncated = True
                next_offset = line_no
                break

            encoded_line = line.encode("utf-8")
            remaining_bytes = LOCAL_READ_MAX_BYTES - collected_bytes
            if remaining_bytes <= 0:
                truncated = True
                next_offset = line_no
                break

            if len(encoded_line) > remaining_bytes:
                if not collected_lines:
                    clipped = encoded_line[:remaining_bytes].decode("utf-8", errors="ignore")
                    if clipped:
                        collected_lines.append(clipped)
                        collected_bytes += len(clipped.encode("utf-8"))
                    first_line_exceeds_limit = True
                    next_offset = line_no + 1
                else:
                    next_offset = line_no

                truncated = True
                break

            collected_lines.append(line)
            collected_bytes += len(encoded_line)

    content = "".join(collected_lines)
    line_count = len(collected_lines)
    line_start = offset if line_count > 0 else None
    line_end = offset + line_count - 1 if line_count > 0 else None

    return {
        "content": content,
        "line_count": line_count,
        "line_start": line_start,
        "line_end": line_end,
        "bytes": collected_bytes,
        "truncated": truncated,
        "next_offset": next_offset,
        "first_line_exceeds_limit": first_line_exceeds_limit,
    }


class ReadFileInput(BaseModel):
    """读取文件工具的输入参数。"""
    file_path: str = Field(
        description="文件的 URL 路径，通常是用户上传文件时返回的 URL，如 /api/v1/assets/xxx/yyy/file.xlsx"
    )


class ReadLocalFileInput(BaseModel):
    """读取本地文件工具输入。"""

    path: Optional[str] = Field(
        default=None,
        description="本地文件路径（推荐），支持相对仓库根目录或绝对路径",
    )
    file_path: Optional[str] = Field(
        default=None,
        description="path 的兼容别名",
    )
    offset: Optional[int] = Field(
        default=1,
        description="起始行号（1-based）",
    )
    limit: Optional[int] = Field(
        default=None,
        description="返回行数上限，可选；最大 2000 行",
    )


@tool("read", args_schema=ReadLocalFileInput)
def read(
    path: Optional[str] = None,
    file_path: Optional[str] = None,
    offset: Optional[int] = 1,
    limit: Optional[int] = None,
    config: Optional[RunnableConfig] = None,
) -> str:
    """读取仓库内文本文件（仅 admin 可调用）。"""
    user_id = _extract_user_id(config)
    if user_id is None:
        return _json_response(
            "error",
            error="permission_denied",
            message="权限不足：read 工具仅支持 admin 用户调用（缺少 user_id）",
        )

    role, role_error = _get_user_role(user_id)
    if role_error:
        return _json_response(
            "error",
            error="permission_denied",
            message=role_error,
            user_id=user_id,
        )

    if role != "admin":
        return _json_response(
            "error",
            error="permission_denied",
            message=f"权限不足：read 工具仅支持 admin 用户调用（当前角色: {role}）",
            user_id=user_id,
        )

    target_input = str(path or file_path or "").strip()
    if not target_input:
        return _json_response(
            "error",
            error="invalid_arguments",
            message="缺少必填参数 path（支持 file_path 作为别名）",
        )

    if offset is None:
        offset = 1
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 1:
        return _json_response(
            "error",
            error="invalid_arguments",
            message="offset 必须是大于等于 1 的整数",
        )

    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
        return _json_response(
            "error",
            error="invalid_arguments",
            message="limit 必须是大于等于 1 的整数",
        )

    target_path, path_error = _resolve_local_path(target_input)
    if path_error:
        return _json_response(
            "error",
            error="path_not_allowed",
            message=path_error,
            path=target_input,
        )

    assert target_path is not None

    mime_type, _ = mimetypes.guess_type(str(target_path))
    if not _is_supported_text_mime(mime_type):
        return _json_response(
            "error",
            error="unsupported_file_type",
            message=(
                f"暂不支持读取该文件类型（mime={mime_type}）。"
                "请提供文本文件（如 .py/.md/.json/.txt/.yaml）。"
            ),
            path=str(target_path.relative_to(PROJECT_ROOT)),
        )

    try:
        with target_path.open("rb") as handle:
            sample = handle.read(LOCAL_READ_SAMPLE_BYTES)
    except OSError as exc:
        logger.exception("读取本地文件采样失败: %s", exc)
        return _json_response(
            "error",
            error="read_failed",
            message=f"读取文件失败: {exc}",
            path=str(target_path.relative_to(PROJECT_ROOT)),
        )

    if b"\x00" in sample:
        return _json_response(
            "error",
            error="binary_not_supported",
            message="检测到二进制文件，暂不支持 read 工具直接读取。",
            path=str(target_path.relative_to(PROJECT_ROOT)),
        )

    detected_encoding = _detect_text_encoding(sample)
    encodings = [detected_encoding] if detected_encoding else []
    for encoding in LOCAL_READ_TEXT_ENCODINGS:
        if encoding not in encodings:
            encodings.append(encoding)

    line_limit = min(limit if limit is not None else LOCAL_READ_MAX_LINES, LOCAL_READ_MAX_LINES)

    page_result: Optional[dict[str, object]] = None
    selected_encoding: Optional[str] = None
    for encoding in encodings:
        try:
            page_result = _read_text_with_limits(
                file_path=target_path,
                encoding=encoding,
                offset=offset,
                line_limit=line_limit,
            )
            selected_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            logger.exception("读取本地文件失败: %s", exc)
            return _json_response(
                "error",
                error="read_failed",
                message=f"读取文件失败: {exc}",
                path=str(target_path.relative_to(PROJECT_ROOT)),
            )

    if page_result is None:
        return _json_response(
            "error",
            error="unsupported_encoding",
            message="无法按文本方式解码该文件，请确认编码格式是否受支持（utf-8/gbk）。",
            path=str(target_path.relative_to(PROJECT_ROOT)),
        )

    message_parts = []
    if page_result["line_count"] == 0:
        message_parts.append("未读取到内容，可能是 offset 超出文件行数。")
    if page_result["truncated"] and page_result["next_offset"]:
        message_parts.append(f"输出已截断，可使用 offset={page_result['next_offset']} 继续读取。")
    if page_result["first_line_exceeds_limit"]:
        message_parts.append("首行超过 50KB 限制，仅返回可展示片段。")

    return _json_response(
        "success",
        tool="read",
        path=str(target_path.relative_to(PROJECT_ROOT)),
        full_path=str(target_path),
        encoding=selected_encoding,
        offset=offset,
        limit=line_limit,
        line_count=page_result["line_count"],
        line_start=page_result["line_start"],
        line_end=page_result["line_end"],
        bytes=page_result["bytes"],
        truncated=page_result["truncated"],
        next_offset=page_result["next_offset"],
        content=page_result["content"],
        message=" ".join(message_parts) if message_parts else None,
    )


@tool(args_schema=ReadFileInput)
def read_uploaded_file(file_path: str, config: RunnableConfig) -> str:
    """
    读取用户上传的文件内容。

    支持的文件类型：
    - Excel (.xlsx, .xls): 返回数据预览和统计信息
    - CSV (.csv): 返回数据预览和统计信息
    - 文本文件 (.txt, .json): 返回文件内容
    - PDF: 返回提取的文本内容

    Args:
        file_path: 文件的 URL 路径，如 /api/v1/assets/user/thread/file.xlsx

    Returns:
        文件内容或数据预览的 JSON 格式字符串
    """
    try:
        # 从 URL 提取 object_key
        # URL 格式: /api/v1/assets/{object_key}
        if file_path.startswith("/api/v1/assets/"):
            object_key = file_path[len("/api/v1/assets/"):]
        elif file_path.startswith("http"):
            # 完整 URL，提取路径部分
            from urllib.parse import urlparse
            parsed = urlparse(file_path)
            path = parsed.path
            if "/api/v1/assets/" in path:
                object_key = path.split("/api/v1/assets/")[1]
            else:
                return json.dumps({"error": f"无法解析 URL: {file_path}"}, ensure_ascii=False)
        else:
            object_key = file_path
        
        logger.info("读取文件: object_key=%s", object_key)
        
        # 从 MinIO 获取文件
        asset_service = get_asset_service()
        response = asset_service.client.get_object(
            bucket_name=ai_config.MINIO_BUCKET_ASSETS,
            object_name=object_key
        )
        
        file_content = response.read()
        response.close()
        response.release_conn()
        
        # 获取文件信息
        stat = asset_service.client.stat_object(
            bucket_name=ai_config.MINIO_BUCKET_ASSETS,
            object_name=object_key
        )
        content_type = stat.content_type or ""
        file_size = stat.size
        
        # 根据文件类型处理
        file_ext = object_key.lower().split(".")[-1] if "." in object_key else ""
        
        # Excel 文件
        if file_ext in ["xlsx", "xls"] or "spreadsheet" in content_type or "excel" in content_type:
            return _read_excel(file_content, object_key)
        
        # CSV 文件
        elif file_ext == "csv" or "csv" in content_type:
            return _read_csv(file_content, object_key)
        
        # JSON 文件
        elif file_ext == "json" or "json" in content_type:
            return _read_json(file_content, object_key)
        
        # 文本文件
        elif file_ext == "txt" or "text/plain" in content_type:
            return _read_text(file_content, object_key)
        
        # PDF 文件
        elif file_ext == "pdf" or "pdf" in content_type:
            return _read_pdf(file_content, object_key)
        
        else:
            return json.dumps({
                "status": "unsupported",
                "message": f"暂不支持直接读取此文件类型: {file_ext} ({content_type})",
                "file_size": file_size,
                "object_key": object_key
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.exception("读取文件失败: %s", e)
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _read_excel(content: bytes, object_key: str) -> str:
    """读取 Excel 文件。"""
    if pd is None:
        return json.dumps({"error": "pandas 未安装，无法读取 Excel 文件"}, ensure_ascii=False)
    
    try:
        # 读取 Excel
        df = pd.read_excel(io.BytesIO(content))
        
        # 构建响应
        result = {
            "status": "success",
            "file_type": "excel",
            "file_name": object_key.split("/")[-1],
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "preview": df.head(20).to_dict(orient="records"),  # 前20行预览
            "statistics": {}
        }
        
        # 添加数值列的统计信息
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            result["statistics"] = df[numeric_cols].describe().to_dict()
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": f"读取 Excel 失败: {str(e)}"}, ensure_ascii=False)


def _read_csv(content: bytes, object_key: str) -> str:
    """读取 CSV 文件。"""
    if pd is None:
        return json.dumps({"error": "pandas 未安装，无法读取 CSV 文件"}, ensure_ascii=False)
    
    try:
        # 尝试不同编码
        for encoding in ["utf-8", "gbk", "gb2312", "latin1"]:
            try:
                df = pd.read_csv(io.BytesIO(content), encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            return json.dumps({"error": "无法解析 CSV 文件编码"}, ensure_ascii=False)
        
        result = {
            "status": "success",
            "file_type": "csv",
            "file_name": object_key.split("/")[-1],
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "preview": df.head(20).to_dict(orient="records"),
            "statistics": {}
        }
        
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            result["statistics"] = df[numeric_cols].describe().to_dict()
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": f"读取 CSV 失败: {str(e)}"}, ensure_ascii=False)


def _read_json(content: bytes, object_key: str) -> str:
    """读取 JSON 文件。"""
    try:
        data = json.loads(content.decode("utf-8"))
        
        result = {
            "status": "success",
            "file_type": "json",
            "file_name": object_key.split("/")[-1],
            "content": data
        }
        
        # 如果是列表，添加长度信息
        if isinstance(data, list):
            result["length"] = len(data)
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": f"读取 JSON 失败: {str(e)}"}, ensure_ascii=False)


def _read_text(content: bytes, object_key: str) -> str:
    """读取文本文件。"""
    try:
        # 尝试不同编码
        for encoding in ["utf-8", "gbk", "gb2312", "latin1"]:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = content.decode("utf-8", errors="ignore")
        
        # 限制返回长度
        max_length = 10000
        if len(text) > max_length:
            text = text[:max_length] + f"\n\n... (截断，原文件共 {len(content)} 字节)"
        
        return json.dumps({
            "status": "success",
            "file_type": "text",
            "file_name": object_key.split("/")[-1],
            "content": text,
            "length": len(content)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"读取文本文件失败: {str(e)}"}, ensure_ascii=False)


def _read_pdf(content: bytes, object_key: str) -> str:
    """读取 PDF 文件。"""
    try:
        # 尝试使用 PyPDF2
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            text_parts = []
            for page in reader.pages[:20]:  # 最多读取前20页
                text_parts.append(page.extract_text() or "")
            text = "\n\n".join(text_parts)
            
            return json.dumps({
                "status": "success",
                "file_type": "pdf",
                "file_name": object_key.split("/")[-1],
                "total_pages": len(reader.pages),
                "extracted_pages": min(20, len(reader.pages)),
                "content": text[:10000] if len(text) > 10000 else text
            }, ensure_ascii=False)
            
        except ImportError:
            return json.dumps({
                "status": "error",
                "message": "PyPDF2 未安装，无法读取 PDF 文件。请使用 pip install PyPDF2 安装。",
                "file_name": object_key.split("/")[-1]
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({"error": f"读取 PDF 失败: {str(e)}"}, ensure_ascii=False)


# 导出工具列表
file_tools = [read_uploaded_file, read]
