"""知识缺口发现 — 回路 4（Celery 定时任务）"""

import asyncio
from celery import shared_task
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import get_settings


async def _analyze_gaps() -> dict:
    """分析搜索日志，发现知识缺口"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as db:
        result = await db.execute(text("""
            SELECT query, COUNT(*) as freq
            FROM search_logs
            WHERE result_count = 0
              AND created_at > NOW() - INTERVAL '7 days'
            GROUP BY query
            ORDER BY freq DESC
            LIMIT 20
        """))
        gaps = [{"query": r[0], "frequency": r[1]} for r in result.fetchall()]

        for gap in gaps:
            await db.execute(text("""
                INSERT INTO knowledge_gaps (query, frequency, priority, status)
                VALUES (:q, :f, 'medium', 'open')
            """), {"q": gap["query"], "f": gap["frequency"]})

        await db.commit()

    await engine.dispose()
    return {"gaps_found": len(gaps)}


@shared_task(name="app.evolution.gap_analyzer.gap_analyzer_task")
def gap_analyzer_task():
    """Celery 任务入口"""
    result = asyncio.run(_analyze_gaps())
    print(f"[gap_analyzer] {result}")
    return result
