"""迁移命令行入口"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import get_settings
from app.migration.importer import import_all

settings = get_settings()


async def run_migration(source_dir: str, mode: str = "full"):
    """执行数据迁移"""
    source = Path(source_dir)
    if not source.exists():
        print(f"[FATAL] 源目录不存在: {source_dir}")
        sys.exit(1)

    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as db:
        print(f"📂 扫描源目录: {source}")
        if mode == "dry-run":
            md_files = list(source.rglob("*.md"))
            print(f"   找到 {len(md_files)} 个 Markdown 文件")
            for f in sorted(md_files)[:10]:
                print(f"   - {f.relative_to(source)}")
            if len(md_files) > 10:
                print(f"   ... 及其他 {len(md_files) - 10} 个文件")
            return

        print("📥 开始导入...")
        stats = await import_all(db, source, progress_callback=lambda name: print(f"   ✓ {name}"))
        print(f"\n📊 导入完成: 总数={stats['total']}, 新建={stats['created']}, "
              f"更新={stats['updated']}, 错误={stats['errors']}")
        await db.commit()

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="WenShanKB 数据迁移工具")
    parser.add_argument("--source", "-s", default=os.getenv("KB_SOURCE_DIR", "."),
                        help="Obsidian 知识库根目录")
    parser.add_argument("--mode", "-m", choices=["full", "incremental", "dry-run"],
                        default="full", help="迁移模式")
    args = parser.parse_args()

    asyncio.run(run_migration(args.source, args.mode))


if __name__ == "__main__":
    main()
