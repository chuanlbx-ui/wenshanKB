"""向量嵌入服务 — 兼容多 API 提供商

DeepSeek chat API 不支持 embeddings 端点（返回 404）。
自动检测并禁用语义搜索，回退到 PostgreSQL 全文搜索。
"""

import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger("wenshan-kb.embedding")
settings = get_settings()

# 缓存检测结果：避免每 10 分钟重复尝试 404 的 API
_embedding_disabled = False


async def generate_embedding(text: str) -> Optional[list[float]]:
    """生成文本向量嵌入 (1536维)
    
    如果 LLM 提供商不支持 embeddings API，自动降级到全文搜索。
    """
    global _embedding_disabled

    if _embedding_disabled or not settings.LLM_API_KEY:
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=text[:20000],
        )

        return response.data[0].embedding

    except Exception as e:
        # 如果是 404（端点不存在），永久禁用
        if "404" in str(e) or "not found" in str(e).lower():
            _embedding_disabled = True
            logger.info("Embedding API 不可用，全局降级到全文搜索")
        return None
