"""笔记 CRUD 端点"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.db.session import get_db
from app.db.models import Note, Category, NoteLink
from app.schemas.note import NoteSummary, NoteDetail, RelatedNote

router = APIRouter()


@router.get("/notes", response_model=dict)
async def list_notes(
    category: Optional[str] = Query(None),
    status: str = Query("published"),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """公开端点：笔记列表"""
    conditions = ["n.status = :status"]
    params = {"status": status}

    if category:
        # 支持 name (01-地理与自然环境) 和 display_name (地理与自然环境) 两种传参
        conditions.append("(c.name = :cat OR c.display_name = :cat)")
        params["cat"] = category

    offset = (page - 1) * page_size

    query = text(f"""
        SELECT n.id, n.title, n.slug, c.display_name AS category, n.status,
               n.freshness, n.view_count, n.like_count, n.created_at, n.updated_at,
               n.plain_text,
               COUNT(*) OVER() AS total
        FROM notes n
        LEFT JOIN categories c ON n.category_id = c.id
        WHERE {' AND '.join(conditions)}
        ORDER BY n.updated_at DESC
        LIMIT :limit OFFSET :offset
    """)

    result = await db.execute(query, {**params, "limit": page_size, "offset": offset})
    rows = result.fetchall()

    total = rows[0][-1] if rows else 0
    notes = []
    for r in rows:
        notes.append({
            "id": str(r[0]), "title": r[1], "slug": r[2], "category": r[3],
            "status": r[4], "freshness": r[5], "view_count": r[6] or 0,
            "like_count": r[7] or 0, "excerpt": (r[10] or "")[:200],
            "created_at": r[8].isoformat() if r[8] else None,
            "updated_at": r[9].isoformat() if r[9] else None,
            "tags": [],
        })

    total_pages = max((total + page_size - 1) // page_size, 1)
    return {
        "notes": notes,
        "pagination": {"page": page, "page_size": page_size,
                       "total": total, "total_pages": total_pages},
    }


@router.get("/notes/{slug}", response_model=dict)
async def get_note(slug: str, db: AsyncSession = Depends(get_db)):
    """公开端点：笔记详情"""
    query = text("""
        SELECT n.id, n.title, n.slug, c.display_name AS category, n.status,
               n.freshness, n.content, n.frontmatter, n.plain_text,
               n.view_count, n.like_count, n.created_at, n.updated_at,
               n.source_path
        FROM notes n
        LEFT JOIN categories c ON n.category_id = c.id
        WHERE n.slug = :slug AND n.status = 'published'
    """)
    result = await db.execute(query, {"slug": slug})
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"笔记 '{slug}' 不存在")

    # 增加浏览量
    await db.execute(text("UPDATE notes SET view_count = view_count + 1 WHERE slug = :slug"), {"slug": slug})

    return {
        "id": str(row[0]), "title": row[1], "slug": row[2], "category": row[3],
        "status": row[4], "freshness": row[5], "content": row[6],
        "frontmatter": row[7] or {}, "excerpt": (row[8] or "")[:200],
        "view_count": row[9] or 0, "like_count": row[10] or 0,
        "created_at": row[11].isoformat() if row[11] else None,
        "updated_at": row[12].isoformat() if row[12] else None,
        "tags": [],
        "source_path": row[13] if row[13] else None,
    }


@router.get("/notes/{slug}/related")
async def get_related(slug: str, limit: int = Query(5, ge=1, le=20),
                      db: AsyncSession = Depends(get_db)):
    """公开端点：相关笔记"""
    query = text("""
        SELECT n2.id, n2.title, n2.slug, c.display_name AS category
        FROM notes n1
        JOIN note_links nl ON nl.source_note_id = n1.id OR nl.target_note_id = n1.id
        JOIN notes n2 ON (n2.id = nl.source_note_id OR n2.id = nl.target_note_id)
                       AND n2.id != n1.id AND n2.status = 'published'
        LEFT JOIN categories c ON n2.category_id = c.id
        WHERE n1.slug = :slug
        GROUP BY n2.id, n2.title, n2.slug, c.display_name
        LIMIT :limit
    """)
    result = await db.execute(query, {"slug": slug, "limit": limit})
    rows = result.fetchall()

    return {
        "notes": [{"id": str(r[0]), "title": r[1], "slug": r[2], "category": r[3]}
                  for r in rows],
        "relation_type": "wikilink",
    }
