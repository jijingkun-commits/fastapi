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
        role: 兼容字段，等价于 data_role
        data_role: 数据角色（问数权限主体）
        sys_role: 系统角色（仅用于兼容与观测，不参与数据权限判定）
        org_code: 机构代码
        org_name: 机构名称
        dept_code: 部门代码
        dept_name: 部门名称
        default_dept_scope: 是否启用默认部门隔离
        allowed_schemas: 允许访问的 Schema 列表
        allowed_tables: 允许访问的表规则列表（支持通配符）
        denied_tables: 禁止访问的表列表
        row_filters: 行级过滤规则 {schema.table: [(column, operator, value), ...]}
        masked_columns: 列脱敏规则 {schema.table.column: mask_type}
    """
    user_id: int
    role: Optional[str] = None
    data_role: Optional[str] = None
    sys_role: Optional[str] = None
    org_code: Optional[str] = None
    org_name: Optional[str] = None
    dept_code: Optional[str] = None
    dept_name: Optional[str] = None
    default_dept_scope: bool = True
    
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

    def __post_init__(self) -> None:
        """标准化角色字段，确保 data_role 为唯一权限角色来源。"""

        normalized_data_role = (self.data_role or "").strip()
        normalized_role = (self.role or "").strip()

        if normalized_data_role:
            resolved_data_role = normalized_data_role
        elif normalized_role:
            resolved_data_role = normalized_role
        else:
            resolved_data_role = "staff"

        self.data_role = resolved_data_role
        # role 保留兼容语义，始终与 data_role 对齐
        self.role = resolved_data_role

        if self.sys_role:
            self.sys_role = self.sys_role.strip()

    def is_admin(self) -> bool:
        """是否为数据管理员角色（仅基于 data_role 判定）。"""
        return self.data_role == "admin"

    def has_dept_code(self) -> bool:
        """是否具备有效 dept_code。"""

        return bool((self.dept_code or "").strip())
    
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
