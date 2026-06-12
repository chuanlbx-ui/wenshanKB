"""向量嵌入服务 — 兼容 DeepSeek / OpenAI / 通义千问"""

import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger("wenshan-kb.embedding")
settings = get_settings()


async def generate_embedding(text: str) -> Optional[list[float]]:
    """生成文本向量嵌入 (1536维)
    
    优先级：
    1. 如果 LLM_BASE_URL 提供 embedding 端点（OpenAI 兼容），直接调用
    2. DeepSeek 暂无 embedding API，返回 None 触发搜索降级到全文搜索
    """
    if not settings.LLM_API_KEY:
        logger.warning("LLM_API_KEY 未设置，语义搜索不可用")
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

        dim = len(response.data[0].embedding)
        logger.info(f"向量嵌入成功: dim={dim}, model={settings.EMBEDDING_MODEL}")
        return response.data[0].embedding

    except Exception as e:
        logger.warning(f"向量嵌入失败（将降级为全文搜索）: {e}")
        return None
