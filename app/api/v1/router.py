"""v1 总路由注册（中文注释）。

统一在此处组合各功能模块的路由，并可按模块配置统一的依赖（如登录校验）。

约定：
- `health_router` 与 `auth_router` 对外公开，无需登录。
- 需要登录保护的模块（如 `chat_router`、`user_router`）建议通过 `dependencies=[Depends(get_current_user)]` 统一配置，避免在每个接口里重复写依赖。

如需更细粒度控制（例如某模块部分接口开放、部分受保护），可在对应的 endpoint 文件内为具体接口单独添加 `Depends(get_current_user)`，二者可并存。
"""
from fastapi import APIRouter, Depends

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.user import router as user_router
from app.api.v1.endpoints.user_skill_api import router as user_skill_router
from app.api.v1.endpoints.chat_api import router as chat_router
from app.api.v1.endpoints.assets_api import router as assets_router
from app.api.deps import get_current_user, get_admin_user


api_router = APIRouter(prefix="/api/v1")

# 注册各业务路由（按是否需要登录进行分组）
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(user_skill_router, dependencies=[Depends(get_current_user)])
api_router.include_router(chat_router, dependencies=[Depends(get_current_user)])
# 资产路由：权限校验在 API 内部处理（支持可选登录）
api_router.include_router(assets_router)
# LLM 路由：只读接口也建议要求登录
from app.api.v1.endpoints.llm_api import router as llm_router
api_router.include_router(llm_router, prefix="/llm", tags=["LLM"], dependencies=[Depends(get_current_user)])
# 系统配置路由
from app.api.v1.endpoints.config_api import router as config_router
api_router.include_router(config_router, prefix="/config", tags=["Config"], dependencies=[Depends(get_current_user)])
# 上传路由：必须登录
from app.api.v1.endpoints.upload_api import router as upload_router
api_router.include_router(upload_router, dependencies=[Depends(get_current_user)])
# 待办看板路由：需要登录
from app.api.v1.endpoints.todo_api import router as todo_router
api_router.include_router(todo_router, prefix="/todo", tags=["Todo"], dependencies=[Depends(get_current_user)])

# ==================== 后台管理路由（仅管理员可访问） ====================
# 问数管理路由：仅管理员
from app.api.v1.endpoints.data_admin_api import router as data_admin_router
api_router.include_router(data_admin_router, dependencies=[Depends(get_admin_user)])
# 数据访问控制管理路由：仅管理员
from app.api.v1.endpoints.access_admin_api import router as access_admin_router
api_router.include_router(access_admin_router, dependencies=[Depends(get_admin_user)])
# LLM 配置管理路由：仅管理员
from app.api.v1.endpoints.llm_admin_api import router as llm_admin_router
api_router.include_router(llm_admin_router, dependencies=[Depends(get_admin_user)])
# 技能管理路由：仅管理员
from app.api.v1.endpoints.skill_admin_api import router as skill_admin_router
api_router.include_router(skill_admin_router, dependencies=[Depends(get_admin_user)])
# 系统配置管理路由：仅管理员
from app.api.v1.endpoints.system_admin_api import router as system_admin_router
api_router.include_router(system_admin_router, dependencies=[Depends(get_admin_user)])
# 总览驾驶舱路由：仅管理员
from app.api.v1.endpoints.admin_overview_api import router as admin_overview_router
api_router.include_router(admin_overview_router, dependencies=[Depends(get_admin_user)])
# 开发工具路由：仅管理员
from app.api.v1.endpoints.dev_codex_api import router as dev_codex_router
api_router.include_router(dev_codex_router, dependencies=[Depends(get_admin_user)])
# 文档记忆运维路由：仅管理员
from app.api.v1.endpoints.memory_admin_api import router as memory_admin_router
api_router.include_router(memory_admin_router, dependencies=[Depends(get_admin_user)])

