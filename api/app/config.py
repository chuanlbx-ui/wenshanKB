"""应用配置 — 从环境变量读取"""

import os
from functools import lru_cache
from pathlib import Path

# 自动加载项目根目录的 .env 文件
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)


class Settings:
    VERSION = "0.2.0"

    # ── 数据库 ──
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://kb_user:kb_pass@localhost:5432/wenshan_kb",
    )
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://kb_user:kb_pass@localhost:5432/wenshan_kb",
    )

    # ── Redis ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── 安全 ──
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    AGENT_API_KEY: str = os.getenv("AGENT_API_KEY", "wskb-dev-key")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72

    # ── AI ──
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv(
        "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-max")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIM: int = 1536

    # ── CORS ──
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # ── 分页 ──
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 50

    # ── 采集 ──
    CRAWLER_USER_AGENT: str = "WenShanKB-Crawler/1.0"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
