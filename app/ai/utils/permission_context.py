"""问数权限上下文（中文注释）。

定义用户权限上下文数据结构，用于 SQL 重写和权限判断。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class UserPermissionContext:
    """用户权限上下文。
    
    包含用户的角色、机构、部门信息，以及解析后的权限规则。
    
    Attributes:
        user_id: 用户 ID
        role: 用户角色 (admin / analyst / user)
        org_code: 机构代码
        org_name: 机构名称
        dept_code: 部门代码
        dept_name: 部门名称
        allowed_schemas: 允许访问的 Schema 列表
        allowed_tables: 允许访问的表规则列表（支持通配符）
        denied_tables: 禁止访问的表列表
        row_filters: 行级过滤规则 {schema.table: [(column, operator, value), ...]}
        masked_columns: 列脱敏规则 {schema.table.column: mask_type}
    """
    user_id: int
    role: str = "user"
    org_code: Optional[str] = None
    org_name: Optional[str] = None
    dept_code: Optional[str] = None
    dept_name: Optional[str] = None
    
    # 表级权限
    allowed_schemas: List[str] = field(default_factory=list)
    allowed_tables: List[str] = field(default_factory=list)  # 格式: schema.table 或 schema.*
    denied_tables: Set[str] = field(default_factory=set)
    
    # 行级权限（RLS）
    # 格式: {"fdmdata.f_mid_deposit": [("org_code", "=", "001")]}
    row_filters: Dict[str, List[tuple]] = field(default_factory=dict)
    
    # 列级权限（脱敏）
    # 格式: {"fdmdata.f_mid_deposit.mobile": "partial"}
    masked_columns: Dict[str, str] = field(default_factory=dict)
    
    def is_admin(self) -> bool:
        """是否为管理员（无权限限制）。"""
        return self.role == "admin"
    
    def get_row_filter_value(self, source: str) -> Optional[str]:
        """根据 filter_source 获取实际过滤值。
        
        Args:
            source: 过滤值来源，如 user.org_code / user.dept_code
            
        Returns:
            实际的过滤值
        """
        if source == "user.org_code":
            return self.org_code
        elif source == "user.dept_code":
            return self.dept_code
        else:
            # fixed 类型直接返回 None，由调用方使用配置的 filter_value
            return None


@dataclass
class PermissionCheckResult:
    """权限检查结果。
    
    Attributes:
        allowed: 是否允许访问
        reason: 拒绝原因（如果 allowed=False）
        rewritten_sql: 重写后的 SQL（如果需要注入过滤条件）
    """
    allowed: bool
    reason: Optional[str] = None
    rewritten_sql: Optional[str] = None
