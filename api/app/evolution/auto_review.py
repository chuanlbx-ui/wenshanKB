"""自动审核 — AI 评分自动发布（回路 5）

对 pending_review 的爬虫草稿进行 AI 质量评分，
≥75 分自动发布并生成摘要/tags/category，
<75 分保持在待审核状态并记录原因到 frontmatter。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from celery import shared_task
from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import get_settings

logger = logging.getLogger("wenshan-kb.auto_review")

SCORE_THRESHOLD = 75  # 自动发布阈值


async def _ai_score(article: dict) -> dict:
    """用 DeepSeek 对文章进行质量评分"""
    settings = get_settings()
    if not settings.LLM_API_KEY:
        return {"score": 50, "summary": article.get("plain_text", "")[:300],
                "tags": ["采集"], "reason": "无 LLM Key，保守处理（默认不通过）"}

    try:
        client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        prompt = f"""你是一个知识库编辑审核助手。请评估以下文章的质量，输出 JSON：

{{
  "score": 0-100的整数评分（内容充实≥80，有数据支撑≥85，过于简短文不对题<60），
  "summary": "150字以内的专业摘要",
  "tags": ["3-5个相关标签"],
  "category": "最适合的分类（经济发展/文化旅游/特产与资源/交通与基础设施/政策与治理/社会民生/地理与自然环境/历史沿革/行政区划/人口与民族）",
  "reason": "评分理由（一句话说明为什么给这个分数）"
}}

文章标题：{article["title"]}
文章内容：{article["plain_text"][:3000]}
"""

        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        result = json.loads(resp.choices[0].message.content)
        return {
            "score": max(0, min(100, result.get("score", 75))),
            "summary": result.get("summary", article["plain_text"][:300]),
            "tags": result.get("tags", ["采集"]),
            "category": result.get("category", "未分类"),
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        logger.warning(f"AI 评分失败: {e}")
        return {"score": 40, "summary": article["plain_text"][:300],
                "tags": ["采集"], "reason": f"AI 评分异常，保守处理: {str(e)[:50]}"}


async def _ensure_tags(db: AsyncSession, tag_names: list[str]) -> dict[str, int]:
    """确保 tags 表中存在这些标签，返回 {名称: id} 映射"""
    result = {}
    for name in tag_names:
        if not name or not name.strip():
            continue
        name = name.strip()
        row = await db.execute(text("SELECT id FROM tags WHERE name = :n"), {"n": name})
        tag = row.fetchone()
        if tag:
            result[name] = tag[0]
        else:
            row = await db.execute(
                text("INSERT INTO tags (name, usage_count) VALUES (:n, 0) RETURNING id"),
                {"n": name}
            )
            new_id = row.fetchone()[0]
            result[name] = new_id
    return result


async def _publish_note(db: AsyncSession, slug: str, review: dict) -> bool:
    """将草稿发布为正式笔记"""
    try:
        summary_json = json.dumps(review["summary"], ensure_ascii=False)

        # 1. 更新笔记状态和分类（使用 || 拼接 jsonb 来避免 : 在 jsonb_set 中的歧义）
        update_sql = text("""
            UPDATE notes
            SET status = 'published',
                category_id = (SELECT id FROM categories WHERE display_name = :cat LIMIT 1),
                frontmatter = frontmatter || :summary_jsonb,
                updated_at = NOW(),
                published_at = COALESCE(published_at, NOW())
            WHERE slug = :slug AND status = 'pending_review'
            RETURNING id
        """)
        result = await db.execute(update_sql, {
            "slug": slug,
            "summary_jsonb": json.dumps({"summary": review["summary"]}, ensure_ascii=False),
            "cat": review["category"],
        })
        note = result.fetchone()
        if not note:
            logger.warning(f"  笔记不存在或状态不对: {slug}")
            return False

        note_id = note[0]

        # 2. 确保标签存在并建立关联
        tag_map = await _ensure_tags(db, review["tags"])
        for tag_name, tag_id in tag_map.items():
            await db.execute(text("""
                INSERT INTO note_tags (note_id, tag_id, created_at)
                VALUES (:nid, :tid, NOW())
                ON CONFLICT DO NOTHING
            """), {"nid": note_id, "tid": tag_id})
            await db.execute(text("""
                UPDATE tags SET usage_count = usage_count + 1 WHERE id = :tid
            """), {"tid": tag_id})

        logger.info(f"  ✅ 自动发布: {slug} (评分 {review['score']}, 标签 {review['tags']})")
        return True

    except Exception as e:
        logger.warning(f"  发布失败 {slug}: {e}")
        return False


async def _run_auto_review() -> dict:
    """自动审核所有待处理草稿"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)

    stats = {"checked": 0, "published": 0, "skipped": 0, "errors": 0}

    async with AsyncSession(engine) as db:
        result = await db.execute(text("""
            SELECT slug, title, plain_text, content, created_at
            FROM notes
            WHERE source_type = 'crawler' AND status = 'pending_review'
            ORDER BY created_at ASC
            LIMIT 20
        """))
        drafts = result.fetchall()

        if not drafts:
            logger.info("[auto_review] 没有待审核的草稿")
            await engine.dispose()
            return stats

        stats["checked"] = len(drafts)
        logger.info(f"[auto_review] 发现 {len(drafts)} 篇待审核草稿")

        for r in drafts:
            slug, title, plain_text, content, created_at = r
            try:
                article = {
                    "title": title or slug,
                    "plain_text": plain_text or content or "",
                }
                review = await _ai_score(article)

                if review["score"] >= SCORE_THRESHOLD:
                    ok = await _publish_note(db, slug, review)
                    if ok:
                        stats["published"] += 1
                    else:
                        stats["errors"] += 1
                else:
                    # 分数不够，记录原因到 frontmatter
                    reject_info = json.dumps({
                        "auto_review": {
                            "score": review["score"],
                            "reason": review["reason"],
                            "time": datetime.now(timezone.utc).isoformat(),
                        }
                    }, ensure_ascii=False)
                    await db.execute(text("""
                        UPDATE notes
                        SET frontmatter = frontmatter || :reject_jsonb
                        WHERE slug = :slug AND status = 'pending_review'
                    """), {
                        "slug": slug,
                        "reject_jsonb": reject_info,
                    })
                    stats["skipped"] += 1
                    logger.info(f"  ⏭️ 跳过: {slug} (评分 {review['score']} < {SCORE_THRESHOLD}, 原因: {review['reason']})")

            except Exception as e:
                logger.error(f"  审核异常 {slug}: {e}")
                stats["errors"] += 1

        await db.commit()

    await engine.dispose()
    return stats


@shared_task(name="app.evolution.auto_review.auto_review_task")
def auto_review_task():
    """Celery 任务入口 — 自动审核所有待处理草稿"""
    result = asyncio.run(_run_auto_review())
    logger.info(f"[auto_review] 完成: {result}")
    return result
