#!/usr/bin/env python3
"""
文山州知识库 Obsidian 热同步工具

用法:
    python kb.py watch     — 启动文件监听，自动同步修改
    python kb.py sync      — 执行一次全量同步
    python kb.py status    — 显示同步状态

在你的 Obsidian 里编辑保存后，2 秒内自动更新到线上数据库。
"""

import os
import sys
import time
import hashlib
import asyncio
from pathlib import Path

sys.path.insert(0, "api")

# 自动加载 .env，确保数据库连接可用
from dotenv import load_dotenv
load_dotenv()

# 本地运行时，覆盖 Docker 内部地址为 localhost 映射端口
if "DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("db:5432", "localhost:5435")
    os.environ["DATABASE_URL_SYNC"] = os.environ.get("DATABASE_URL_SYNC", "").replace("db:5432", "localhost:5435")

# 看门狗目录
WATCH_DIRS = [
    "00-总览", "01-地理与自然环境", "02-历史沿革", "03-行政区划",
    "04-人口与民族", "05-经济发展", "06-文化旅游", "07-特产与资源",
    "08-交通与基础设施", "09-政策与治理", "10-社会民生",
    "synthesis", "ai-hub", "wiki",
]


def get_md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


async def sync_file(filepath: Path):
    """同步单个文件到数据库"""
    from app.migration.importer import import_note
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from app.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as db:
        result = await import_note(db, filepath, Path("."))
        await db.commit()

    await engine.dispose()
    return result


async def watch():
    """启动文件监听循环"""
    print("👁️ 文山KB 热同步已启动 — 编辑 Obsidian 笔记后自动更新")
    print(f"   监听目录: {', '.join(WATCH_DIRS[:5])}... (共 {len(WATCH_DIRS)} 个)")
    print("   按 Ctrl+C 退出\n")

    # 初始扫描
    file_states: dict[str, str] = {}
    skipped = {"blueprint", "output", "site", "raw", "temp", "api", "web", "nginx", ".git", ".reasonix"}

    for wd in WATCH_DIRS:
        for fp in Path(wd).rglob("*.md"):
            try:
                file_states[str(fp)] = get_md5(fp)
            except Exception:
                pass

    print(f"   已跟踪 {len(file_states)} 个文件\n")

    synced_count = 0

    while True:
        time.sleep(2)
        changed = []

        for wd in WATCH_DIRS:
            wd_path = Path(wd)
            if not wd_path.exists():
                continue
            for fp in Path(wd).rglob("*.md"):
                key = str(fp)
                try:
                    new_md5 = get_md5(fp)
                    if key not in file_states:
                        # 新文件
                        file_states[key] = new_md5
                        changed.append(fp)
                    elif file_states[key] != new_md5:
                        # 文件已修改
                        file_states[key] = new_md5
                        changed.append(fp)
                except Exception:
                    pass

        for fp in changed:
            try:
                result = await sync_file(fp)
                rel = fp.relative_to(Path("."))
                synced_count += 1
                action = result["action"] if result else "skip"
                print(f"  [{synced_count}] {action:7s}  {rel}")
            except Exception as e:
                print(f"  [ERROR] {fp}: {e}")


async def full_sync():
    """执行一次全量同步"""
    from app.migration.runner import run_migration

    print("📥 全量同步中...")
    stats = await run_migration(".", "incremental")
    print(f"   完成: 新建 {stats.get('created', '?')}, 更新 {stats.get('updated', '?')}")


async def show_status():
    """显示同步状态"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text
    from app.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as db:
        result = await db.execute(text("""
            SELECT status, COUNT(*) FROM notes GROUP BY status
        """))
        print("📊 数据库状态:")
        for r in result.fetchall():
            print(f"   {r[0]:20s}: {r[1]} 篇")

    await engine.dispose()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "watch"

    if cmd == "watch":
        try:
            asyncio.run(watch())
        except KeyboardInterrupt:
            print("\n👋 热同步已停止")
    elif cmd == "sync":
        asyncio.run(full_sync())
    elif cmd == "status":
        asyncio.run(show_status())
    else:
        print(f"用法: python kb.py [watch|sync|status]")


if __name__ == "__main__":
    main()
