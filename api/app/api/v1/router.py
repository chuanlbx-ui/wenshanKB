"""v1 路由聚合器"""

from fastapi import APIRouter
from app.api.v1.notes import router as notes_router
from app.api.v1.search import router as search_router
from app.api.v1.materials import router as materials_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.auth import router as auth_router
from app.api.v1.agent.tools import router as agent_tools_router

router = APIRouter(prefix="/api/v1")

router.include_router(notes_router, tags=["笔记"])
router.include_router(search_router, tags=["搜索"])
router.include_router(materials_router, tags=["素材卡片"])
router.include_router(prompts_router, tags=["提示词"])
router.include_router(compliance_router, tags=["合规"])
router.include_router(feedback_router, tags=["反馈"])
router.include_router(auth_router, tags=["认证"])
router.include_router(agent_tools_router, tags=["Agent Tools"])
