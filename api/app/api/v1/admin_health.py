"""知识库健康检查 — 检测失效 wikilink、frontmatter 缺失等"""

import re
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter(prefix="/admin", tags=["管理"])


@router.get("/link-check")
async def check_broken_links(db: AsyncSession = Depends(get_db)):
    """扫描所有笔记的 wikilink，找出指向不存在 slug 的失效链接"""
    # 获取所有已存在的 slug
    result = await db.execute(text("SELECT slug FROM notes WHERE status = 'published'"))
    existing_slugs = {r[0] for r in result.fetchall()}

    # 获取所有笔记的 wikilink 引用
    result = await db.execute(text("""
        SELECT nl.id, nl.source_note_id, nl.target_note_slug, nl.link_text,
               n.title AS source_title, n.slug AS source_slug
        FROM note_links nl
        JOIN notes n ON nl.source_note_id = n.id
        WHERE nl.link_type = 'wikilink'
    """))
    rows = result.fetchall()

    broken = []
    stats = {"total_links": len(rows), "broken": 0, "valid": 0}

    for r in rows:
        target = r[2]
        if target and target not in existing_slugs:
            broken.append({
                "link_id": r[0],
                "source_title": r[4],
                "source_slug": r[5],
                "target_slug": target,
                "link_text": r[3] or target,
            })
            stats["broken"] += 1
        else:
            stats["valid"] += 1

    return {"stats": stats, "broken_links": broken[:50]}


@router.get("/quality-report")
async def quality_report(db: AsyncSession = Depends(get_db)):
    """知识库质量概览"""
    result = await db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE fresh IS NOT NULL AND fresh != '') - COUNT(*) FILTER (WHERE freshness = 'fresh') AS stale_notes,
            COUNT(*) FILTER (WHERE frontmatter->>'confidence' IS NULL) AS missing_confidence,
            COUNT(*) FILTER (WHERE frontmatter->>'sources' IS NULL OR frontmatter->>'sources' = '[]') AS missing_sources,
            COUNT(*) FILTER (WHERE plain_text IS NULL OR length(plain_text) < 200) AS short_notes
        FROM notes
        WHERE status = 'published'
    """))
    row = result.fetchone()

    return {
        "total_notes": row[0],
        "stale_notes": row[1],
        "missing_confidence": row[2],
        "missing_sources": row[3],
        "short_notes": row[4],
    }
