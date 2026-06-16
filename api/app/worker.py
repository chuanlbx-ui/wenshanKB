"""Celery 应用定义 + 定时任务调度"""

from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

# 显式导入任务模块——确保 @shared_task 装饰器执行
from app.evolution import freshness  # noqa: F401
from app.evolution import crawler  # noqa: F401
from app.evolution import gap_analyzer  # noqa: F401

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
    "freshness-daily": {
        "task": "app.evolution.freshness.freshness_task",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "default"},
    },
    "crawler-morning": {
        "task": "app.evolution.crawler.crawler_task",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "default"},
    },
    "crawler-evening": {
        "task": "app.evolution.crawler.crawler_task",
        "schedule": crontab(hour=18, minute=0),
        "options": {"queue": "default"},
    },
    "gap-analyzer-daily": {
        "task": "app.evolution.gap_analyzer.gap_analyzer_task",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "default"},
    },
}
