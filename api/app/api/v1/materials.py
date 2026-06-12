"""素材卡片端点"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/materials")
async def get_material_cards(
    card_ids: Optional[str] = Query(None, description="逗号分隔卡片ID"),
    category: Optional[str] = Query(None),
    limit: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(get_current_user),
):
    """素材卡片查询"""
    try:
        if card_ids:
            ids = [c.strip() for c in card_ids.split(",")]
            placeholders = ",".join([f":id_{i}" for i in range(len(ids))])
            params = {f"id_{i}": ids[i] for i in range(len(ids))}
            query = text(f"""
                SELECT id, title, core_data, category, applicable_scenarios,
                       source_note_id, full_content
                FROM material_cards
                WHERE id IN ({placeholders})
            """)
            result = await db.execute(query, params)
        else:
            result = await db.execute(
                text("""
                    SELECT id, title, core_data, category, applicable_scenarios,
                           source_note_id, full_content
                    FROM material_cards
                    ORDER BY id LIMIT :limit
                """),
                {"limit": limit},
            )

        rows = result.fetchall()
        if rows:
            cards = []
            for r in rows:
                cards.append({
                    "id": r[0], "title": r[1], "core_data": r[2],
                    "category": r[3], "applicable_scenarios": r[4] or [],
                    "source_note": f"笔记 #{r[5]}" if r[5] else None,
                    "full_content": r[6],
                })
            return {"cards": cards, "total": len(cards)}
    except Exception:
        pass  # 回退到空结果

    return {"cards": [], "total": 0}
