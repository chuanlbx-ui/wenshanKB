"""向量嵌入服务 — 支持独立 embedding API

如果配置了 EMBEDDING_API_KEY/EMBEDDING_BASE_URL，使用专用服务。
否则回退到 LLM 配置。两者都不可用时降级全文搜索。
"""

import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger("wenshan-kb.embedding")
settings = get_settings()

_embedding_disabled = False


async def generate_embedding(text: str) -> Optional[list[float]]:
    """生成文本向量嵌入"""
    global _embedding_disabled

    if _embedding_disabled:
        return None

    api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
    base_url = settings.EMBEDDING_BASE_URL

    if not api_key:
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=text[:500],  # SiliconFlow 限制 512 tokens
            encoding_format="float",
        )

        dim = len(response.data[0].embedding)
        logger.info(f"嵌入成功: dim={dim}, provider={base_url}")

        # 如果维度不匹配，截断或填充到 1536
        if dim < 1536:
            return response.data[0].embedding + [0.0] * (1536 - dim)
        return response.data[0].embedding[:1536]

    except Exception as e:
        msg = str(e).lower()
        if "404" in msg or "not found" in msg or "does not exist" in msg:
            _embedding_disabled = True
            logger.info(f"Embedding API 不可用({base_url})，全局降级全文搜索")
        return None
