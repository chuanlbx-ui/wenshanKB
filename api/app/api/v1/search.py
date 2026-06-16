"""搜索端点 — pgvector 语义搜索 + PostgreSQL 全文搜索"""

import time
import logging
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem, Pagination
from app.schemas.note import NoteSummary
from app.services.embedding import generate_embedding

logger = logging.getLogger("wenshan-kb.search")
router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_notes(body: SearchRequest, db: AsyncSession = Depends(get_db)):
    """混合搜索：语义搜索（pgvector 余弦相似度）+ 全文搜索（tsvector）"""
    t0 = time.perf_counter()

    try:
        if body.search_mode == "fulltext":
            results = await _fulltext_search(db, body.query, body.page_size, body.category)
        elif body.search_mode == "semantic":
            results = await _semantic_search(db, body.query, body.page_size, body.category)
        else:
            results = await _semantic_search(db, body.query, body.page_size, body.category)
            if len(results) < body.page_size:
                ft_results = await _fulltext_search(db, body.query, body.page_size, body.category)
                results.extend(ft_results[:body.page_size - len(results)])
    except Exception as e:
        logger.warning(f"搜索降级: {e}")
        results = []

    # 记录搜索日志
    try:
        await db.execute(text("""
            INSERT INTO search_logs (query, result_count, source, created_at)
            VALUES (:q, :cnt, 'api', NOW())
        """), {"q": body.query, "cnt": len(results)})
        await db.commit()
    except Exception:
        pass

    elapsed = int((time.perf_counter() - t0) * 1000)
    total = len(results)

    search_results = []
    for r in results:
        note = NoteSummary(
            id=r["id"], title=r["title"], slug=r["slug"],
            category=r.get("category"), status=r.get("status", "published"),
            view_count=r.get("view_count", 0), like_count=r.get("like_count", 0),
            created_at=r.get("created_at"), updated_at=r.get("updated_at"),
        )
        search_results.append(SearchResultItem(
            note=note,
            score=r.get("score", 0.0),
            snippet=r.get("snippet", ""),
            match_type=body.search_mode,
        ))

    return SearchResponse(
        results=search_results,
        pagination=Pagination(page=1, page_size=body.page_size,
                              total=total, total_pages=max(total // body.page_size, 1)),
        search_time_ms=elapsed,
    )


async def _semantic_search(db, query: str, limit: int, category: Optional[str] = None) -> list[dict]:
    """pgvector 语义搜索"""
    vec = await generate_embedding(query)
    if vec is None:
        return []

    vec_str = "[" + ",".join([f"{v:.8f}" for v in vec]) + "]"
    cat_cond = "AND (c.name = :cat OR c.display_name = :cat)" if category else ""
    sql = text(f"""
        SELECT n.id::text, n.title, n.slug, c.display_name AS category,
               n.status, n.view_count, n.like_count,
               n.created_at, n.updated_at,
               n.plain_text,
               1.0 - (n.embedding <=> :vec) AS score
        FROM notes n
        LEFT JOIN categories c ON n.category_id = c.id
        WHERE n.status = 'published' AND n.slug NOT IN ('00-MOC','index','log','purpose','changelog','README','-MOC','-索引,'文山KB总索引')
          AND n.embedding IS NOT NULL
          {cat_cond}
        ORDER BY n.embedding <=> :vec
        LIMIT :limit
    """)
    params = {"vec": vec_str, "limit": limit}
    if category:
        params["cat"] = category
    result = await db.execute(sql, params)
    rows = result.fetchall()

    return [
        {"id": str(r[0]), "title": r[1], "slug": r[2], "category": r[3],
         "status": r[4], "view_count": r[5] or 0, "like_count": r[6] or 0,
         "created_at": r[7], "updated_at": r[8],
         "snippet": (r[9] or "")[:200], "score": round(r[10], 4) if r[10] else 0.0}
        for r in rows
    ]


async def _fulltext_search(db, query: str, limit: int, category: Optional[str] = None) -> list[dict]:
    """PostgreSQL 全文搜索"""
    cat_cond = "AND (c.name = :cat OR c.display_name = :cat)" if category else ""
    sql = text(f"""
        SELECT n.id::text, n.title, n.slug, c.display_name AS category,
               n.status, n.view_count, n.like_count,
               n.created_at, n.updated_at,
               n.plain_text,
               ts_rank(n.search_vector, plainto_tsquery('simple', :q)) AS score
        FROM notes n
        LEFT JOIN categories c ON n.category_id = c.id
        WHERE n.status = 'published' AND n.slug NOT IN ('00-MOC','index','log','purpose','changelog','README','-MOC','-索引,'文山KB总索引')
          AND n.search_vector @@ plainto_tsquery('simple', :q)
          {cat_cond}
        ORDER BY score DESC
        LIMIT :limit
    """)
    params = {"q": query, "limit": limit}
    if category:
        params["cat"] = category
    result = await db.execute(sql, params)
    rows = result.fetchall()

    return [
        {"id": str(r[0]), "title": r[1], "slug": r[2], "category": r[3],
         "status": r[4], "view_count": r[5] or 0, "like_count": r[6] or 0,
         "created_at": r[7], "updated_at": r[8],
         "snippet": (r[9] or "")[:200], "score": round(r[10], 4) if r[10] else 0.0}
        for r in rows
    ]
