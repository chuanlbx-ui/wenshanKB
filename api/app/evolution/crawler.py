"""网络信息自动采集 — 回路 3（Celery 定时任务）"""

import asyncio
import httpx
from celery import shared_task

SOURCES = [
    {"name": "文山州政府", "url": "http://www.ynws.gov.cn/", "type": "gov"},
    {"name": "文山新闻网", "url": "http://www.wsnews.com.cn/", "type": "news"},
]


async def _fetch_source(client: httpx.AsyncClient, source: dict) -> list[dict]:
    """抓取单个数据源"""
    try:
        resp = await client.get(
            source["url"],
            headers={"User-Agent": "WenShanKB-Crawler/1.0"},
            follow_redirects=True,
            timeout=30,
        )
        if resp.status_code == 200:
            # TODO: 解析 HTML 提取文章标题和链接
            return []
        return []
    except Exception:
        return []


async def _run_crawler() -> dict:
    """执行采集"""
    async with httpx.AsyncClient() as client:
        tasks = [_fetch_source(client, src) for src in SOURCES]
        results = await asyncio.gather(*tasks)

    total = sum(len(r) for r in results)
    return {"sources_checked": len(SOURCES), "articles_found": total}


@shared_task(name="app.evolution.crawler.crawler_task")
def crawler_task():
    """Celery 任务入口"""
    result = asyncio.run(_run_crawler())
    print(f"[crawler] {result}")
    return result
