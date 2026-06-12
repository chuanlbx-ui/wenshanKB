"""数据导入器 — Markdown → PostgreSQL（完整版）"""

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional


class DateEncoder(json.JSONEncoder):
    """处理 datetime.date / datetime.datetime 的 JSON 编码器"""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


def json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False, cls=DateEncoder)

from app.migration.parser import (
    parse_frontmatter, extract_tags, extract_all_wikilinks,
    slugify, extract_plain_text, parse_created_date,
)

# 目录名 → 分类名 映射
CATEGORY_MAP = {
    "00-总览": "00-总览",
    "01-地理与自然环境": "01-地理与自然环境",
    "02-历史沿革": "02-历史沿革",
    "03-行政区划": "03-行政区划",
    "04-人口与民族": "04-人口与民族",
    "05-经济发展": "05-经济发展",
    "06-文化旅游": "06-文化旅游",
    "07-特产与资源": "07-特产与资源",
    "08-交通与基础设施": "08-交通与基础设施",
    "09-政策与治理": "09-政策与治理",
    "10-社会民生": "10-社会民生",
    "synthesis": "synthesis",
    "ai-hub": "ai-hub",
    "wiki": "wiki",
}


async def _get_or_create_category(db, category_name: str) -> Optional[int]:
    """获取或创建分类，返回 category_id"""
    from sqlalchemy import text

    # 查找已有
    result = await db.execute(
        text("SELECT id FROM categories WHERE name = :name"),
        {"name": category_name},
    )
    row = result.fetchone()
    if row:
        return row[0]

    # 创建新分类
    display = category_name.replace("00-", "").replace("01-", "").replace("02-", "")
    display = display.replace("03-", "").replace("04-", "").replace("05-", "")
    display = display.replace("06-", "").replace("07-", "").replace("08-", "")
    display = display.replace("09-", "").replace("10-", "")

    result = await db.execute(
        text("INSERT INTO categories (name, display_name) VALUES (:name, :display) RETURNING id"),
        {"name": category_name, "display": display},
    )
    return result.fetchone()[0]


def _infer_category(filepath: Path, source_root: Path) -> str:
    """从文件路径推断分类"""
    try:
        rel = filepath.relative_to(source_root)
        top_dir = rel.parts[0] if len(rel.parts) > 1 else "未分类"
    except ValueError:
        top_dir = "未分类"

    return CATEGORY_MAP.get(top_dir, top_dir)


async def import_note(db, filepath: Path, source_root: Path) -> Optional[dict]:
    """导入单篇笔记，返回 {"id": str, "action": "created"|"updated"}"""
    from sqlalchemy import text

    metadata, body = parse_frontmatter(filepath)

    # 标题：优先用 frontmatter title，其次文件名
    title = metadata.get("title", filepath.stem)
    # slug
    slug = slugify(title)

    # 分类
    category_name = _infer_category(filepath, source_root)
    category_id = await _get_or_create_category(db, category_name)

    # 纯文本
    plain_text = extract_plain_text(body)

    # 创建时间 — 转为 Python date 对象
    created_str = parse_created_date(metadata)
    created_date_obj = None
    if created_str:
        try:
            created_date_obj = date.fromisoformat(created_str[:10])
        except (ValueError, TypeError):
            pass

    # 是否已存在
    result = await db.execute(
        text("SELECT id FROM notes WHERE slug = :slug"), {"slug": slug}
    )
    existing = result.fetchone()

    if existing:
        note_id = str(existing[0])
        # 更新已有笔记
        await db.execute(text("""
            UPDATE notes SET
                title = :title, content = :content, plain_text = :plain,
                frontmatter = :fm, category_id = :cid,
                updated_at = NOW()
            WHERE id = :id
        """), {
            "title": title, "content": body, "plain": plain_text,
            "fm": json_dumps(metadata), "cid": category_id, "id": existing[0],
        })
        action = "updated"
    else:
        # 新建笔记
        result = await db.execute(text("""
            INSERT INTO notes (title, slug, content, plain_text, frontmatter,
                               category_id, status, source_path, source_type,
                               created_at)
            VALUES (:title, :slug, :content, :plain, :fm,
                    :cid, 'published', :src, 'obsidian',
                    COALESCE(:created, NOW()))
            RETURNING id
        """), {
            "title": title, "slug": slug, "content": body,
            "plain": plain_text, "fm": json_dumps(metadata),
            "cid": category_id, "src": str(filepath),
            "created": created_date_obj,
        })
        note_id = str(result.fetchone()[0])
        action = "created"

    # 处理标签
    tags = extract_tags(metadata)
    for tag_name in tags:
        # 获取或创建标签
        tag_result = await db.execute(
            text("INSERT INTO tags (name) VALUES (:name) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id"),
            {"name": tag_name},
        )
        tag_id = tag_result.fetchone()[0]
        # 关联笔记与标签
        await db.execute(text("""
            INSERT INTO note_tags (note_id, tag_id) VALUES (:nid, :tid)
            ON CONFLICT DO NOTHING
        """), {"nid": note_id, "tid": tag_id})

    # 处理 wikilink 关系
    wikilinks = extract_all_wikilinks(metadata, body)
    for target, alias in wikilinks:
        target_slug = slugify(target)
        await db.execute(text("""
            INSERT INTO note_links (source_note_id, target_note_slug, link_text, link_type)
            VALUES (:src_id, :target, :text, 'wikilink')
            ON CONFLICT DO NOTHING
        """), {
            "src_id": note_id,
            "target": target_slug,
            "text": alias or target,
        })

    return {"id": note_id, "action": action, "title": title}


async def import_all(db, source_dir: Path, progress_callback=None) -> dict:
    """全量导入 Obsidian 知识库"""
    stats = {"created": 0, "updated": 0, "errors": 0, "total": 0}
    skipped_dirs = {"blueprint", "output", "site", ".obsidian", "_system",
                    "temp", "raw", "assets", ".reasonix", "ai-hub", "wiki"}

    md_files = sorted(source_dir.rglob("*.md"))

    for fp in md_files:
        try:
            rel = fp.relative_to(source_dir)
        except ValueError:
            continue

        # 跳过非笔记目录
        if rel.parts[0] in skipped_dirs or any(p.startswith(".") for p in rel.parts):
            continue

        try:
            result = await import_note(db, fp, source_dir)
            stats["total"] += 1
            if result["action"] == "created":
                stats["created"] += 1
            else:
                stats["updated"] += 1
            if progress_callback:
                progress_callback(f"{result['action']:7s}  {rel}")
        except Exception as e:
            stats["errors"] += 1
            if progress_callback:
                progress_callback(f"ERROR    {rel}  →  {e}")

    await db.commit()
    return stats
