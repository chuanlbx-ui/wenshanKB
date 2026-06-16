"""新鲜度监控 — 回路 1（Celery 定时任务）"""

import asyncio
from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import get_settings


async def _calculate_freshness() -> dict:
    """计算所有已发布笔记的新鲜度评分"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as db:
        now = datetime.now(timezone.utc)

        result = await db.execute(text("""
            SELECT id, title, updated_at
            FROM notes WHERE status = 'published'
        """))
        rows = result.fetchall()

        alerts = []
        for r in rows:
            note_id, title, updated_at = r
            days_since = (now - updated_at).days if updated_at else 365
            score = max(0, int(100 - days_since * 0.27))
            freshness = "fresh"
            if score < 30:
                freshness = "expired"
            elif score < 50:
                freshness = "stale"
            elif score < 80:
                freshness = "aging"

            await db.execute(text("""
                UPDATE notes SET freshness_score = :score, freshness = :freshness
                WHERE id = :id
            """), {"score": score, "freshness": freshness, "id": note_id})

            if freshness != "fresh":
                alerts.append({"title": title, "freshness": freshness, "score": score})

        await db.commit()

    await engine.dispose()
    return {"checked": len(rows), "alerts": len(alerts)}


@shared_task(name="app.evolution.freshness.freshness_task")
def freshness_task():
    """Celery 任务入口"""
    result = asyncio.run(_calculate_freshness())
    print(f"[freshness] {result}")
    return result
