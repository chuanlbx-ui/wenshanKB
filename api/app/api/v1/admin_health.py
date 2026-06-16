"""知识库健康检查 — 检测失效 wikilink、frontmatter 缺失等"""

import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter(prefix="/admin", tags=["管理"])


class ReviewAction(BaseModel):
    action: str  # "approve" or "reject"
    slug: str


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


# ── 采集草稿审核 ──

@router.get("/drafts")
async def list_drafts(db: AsyncSession = Depends(get_db)):
    """列出所有待审核的采集草稿"""
    result = await db.execute(text("""
        SELECT slug, title, plain_text, source_path, created_at, content
        FROM notes
        WHERE source_type = 'crawler' AND status = 'pending_review'
        ORDER BY created_at DESC
        LIMIT 50
    """))
    drafts = []
    for r in result.fetchall():
        drafts.append({
            "slug": r[0],
            "title": r[1],
            "summary": (r[2] or "")[:300],
            "source_url": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
            "content_preview": (r[5] or "")[:500],
        })
    return {"total": len(drafts), "drafts": drafts}


@router.post("/review")
async def review_draft(body: ReviewAction, db: AsyncSession = Depends(get_db)):
    """审核草稿：approve 发布 / reject 归档"""
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action 必须为 approve 或 reject")

    new_status = "published" if body.action == "approve" else "archived"

    result = await db.execute(
        text("UPDATE notes SET status = :status WHERE slug = :slug AND status = 'pending_review' RETURNING id"),
        {"status": new_status, "slug": body.slug},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="草稿不存在或已处理")

    await db.commit()
    return {"slug": body.slug, "action": body.action, "new_status": new_status}


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    """首页仪表盘：核心统计 + 最近更新"""
    # 基本统计
    stats = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'published') AS total,
            COUNT(*) FILTER (WHERE status = 'pending_review') AS drafts,
            COUNT(*) FILTER (WHERE freshness IS NOT NULL AND freshness != 'fresh') AS stale,
            COUNT(DISTINCT category_id) FILTER (WHERE status = 'published') AS categories
        FROM notes
    """))
    row = stats.fetchone()

    # 失效链接数
    result = await db.execute(text("SELECT slug FROM notes WHERE status = 'published'"))
    existing_slugs = {r[0] for r in result.fetchall()}
    result = await db.execute(text(
        """SELECT COUNT(*) FROM note_links
           WHERE link_type = 'wikilink'
             AND target_note_slug NOT IN (SELECT slug FROM notes WHERE status = 'published')
             AND target_note_slug NOT LIKE '%MOC%'
             AND target_note_slug NOT LIKE '%索引%'
             AND target_note_slug NOT LIKE 'wiki-%'
             AND target_note_slug NOT LIKE 'ai-hub-%'
             AND target_note_slug NOT LIKE 'synthesis-%'
             AND target_note_slug NOT LIKE 'p%-%报告%'
             AND target_note_slug NOT LIKE '..-%'
             AND target_note_slug NOT LIKE 'blueprint-%'"""
    ))
    broken = result.fetchone()[0]

    # 最近更新 5 篇
    recent = await db.execute(text("""
        SELECT title, slug, updated_at, view_count FROM notes
        WHERE status = 'published' AND slug NOT LIKE 'crawler-%' AND slug NOT IN ('00-MOC','index','log','purpose','changelog','README','-MOC','-索引','文山KB总索引')
        ORDER BY updated_at DESC LIMIT 5
    """))
    recent_notes = [{"title": r[0], "slug": r[1],
                      "updated_at": r[2].isoformat() if r[2] else None,
                      "view_count": r[3] or 0} for r in recent.fetchall()]

    return {
        "total": row[0] or 0,
        "drafts": row[1] or 0,
        "stale": row[2] or 0,
        "categories": row[3] or 0,
        "broken_links": broken,
        "recent_updates": recent_notes,
    }
