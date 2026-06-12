"""语义搜索服务"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.embedding import generate_embedding


async def semantic_search(
    db: AsyncSession,
    query: str,
    category: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """基于 pgvector 的语义搜索"""
    # 生成查询向量
    vec = await generate_embedding(query)
    if vec is None:
        return []

    vec_str = "[" + ",".join([f"{v:.8f}" for v in vec]) + "]"
    sql = text("""
        SELECT n.id, n.title, n.slug, c.display_name, n.status,
               n.view_count, n.like_count, n.created_at, n.updated_at,
               n.plain_text,
               1.0 - (n.embedding <=> :vec) AS score
        FROM notes n
        LEFT JOIN categories c ON n.category_id = c.id
        WHERE n.status = 'published'
        ORDER BY n.embedding <=> :vec
        LIMIT :limit
    """)
    result = await db.execute(sql, {"vec": vec_str, "limit": limit})
    rows = result.fetchall()

    results = []
    for r in rows:
        results.append({
            "id": str(r[0]), "title": r[1], "slug": r[2],
            "category": r[3], "status": r[4],
            "view_count": r[5], "like_count": r[6],
            "created_at": r[7], "updated_at": r[8],
            "snippet": (r[9] or "")[:200],
            "score": round(r[10], 4) if r[10] else 0.0,
        })
    return results


async def fulltext_search(
    db: AsyncSession,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """PostgreSQL 全文搜索"""
    sql = text("""
        SELECT n.id, n.title, n.slug, c.display_name, n.status,
               n.view_count, n.like_count, n.created_at, n.updated_at,
               n.plain_text,
               ts_rank(n.search_vector, plainto_tsquery('simple', :q)) AS score
        FROM notes n
        LEFT JOIN categories c ON n.category_id = c.id
        WHERE n.status = 'published'
          AND n.search_vector @@ plainto_tsquery('simple', :q)
        ORDER BY score DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, {"q": query, "limit": limit})
    rows = result.fetchall()

    return [
        {
            "id": str(r[0]), "title": r[1], "slug": r[2],
            "category": r[3], "status": r[4],
            "view_count": r[5], "like_count": r[6],
            "created_at": r[7], "updated_at": r[8],
            "snippet": (r[9] or "")[:200],
            "score": round(r[10], 4) if r[10] else 0.0,
        }
        for r in rows
    ]
