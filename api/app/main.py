"""FastAPI 主入口"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.api.v1.router import router as v1_router

# ── 日志 ──
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wenshan-kb")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info(f"🚀 WenShanKB API v{settings.VERSION} 启动中...")
    yield
    logger.info("WenShanKB API 已关闭")


app = FastAPI(
    title="WenShanKB API",
    description="文山州 AI 创作公共知识库系统 API",
    version=settings.VERSION,
    lifespan=lifespan,
)

# ── 中间件 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 静态文件：笔记中的 assets/ 图片 ──
_assets_paths = [
    Path("."),           # 本地运行
    Path("/data/markdown"),  # Docker 运行
]
for _p in _assets_paths:
    if _p.exists() and any(_p.glob("**/assets/*")):
        app.mount("/static", StaticFiles(directory=str(_p)), name="static")
        logger.info(f"  静态文件挂载: {_p.absolute()} → /static")
        break

# ── 路由 ──
app.include_router(v1_router)


@app.get("/api/v1/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": settings.VERSION,
        "database": "not_checked",
    }


# ── 异常处理 ──
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": str(exc)},
    )
