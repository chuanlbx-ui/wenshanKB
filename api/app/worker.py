"""Celery 应用定义 + 定时任务调度

调度说明（所有时间 Asia/Shanghai）：
  - 自动审核 + 爬虫：每小时运行一次（第0分钟审稿，第5分钟抓取）
  - 新鲜度检查：每日 2:00
  - 缺口分析：每日 4:00
"""

from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

# 显式导入任务模块——确保 @shared_task 装饰器执行
from app.evolution import freshness  # noqa: F401
from app.evolution import crawler  # noqa: F401
from app.evolution import gap_analyzer  # noqa: F401
from app.evolution import auto_review  # noqa: F401

settings = get_settings()

app = Celery(
    "wenshan_kb",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_redirect_stdouts=False,
)

# ── 定时任务调度 ──
app.conf.beat_schedule = {
    # 自动审核：每小时第 0 分钟运行
    "auto-review-hourly": {
        "task": "app.evolution.auto_review.auto_review_task",
        "schedule": crontab(minute=0),  # 每小时整点
        "options": {"queue": "default"},
    },
    # 爬虫抓取：每小时第 5 分钟运行（等审核先跑完）
    "crawler-hourly": {
        "task": "app.evolution.crawler.crawler_task",
        "schedule": crontab(minute=5),  # 每小时过5分钟
        "options": {"queue": "default"},
    },
    # 新鲜度：每日 2:00
    "freshness-daily": {
        "task": "app.evolution.freshness.freshness_task",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "default"},
    },
    # 缺口分析：每日 4:00
    "gap-analyzer-daily": {
        "task": "app.evolution.gap_analyzer.gap_analyzer_task",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "default"},
    },
}
