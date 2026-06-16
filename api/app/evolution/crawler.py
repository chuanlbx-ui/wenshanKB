"""网络信息自动采集 — 回路 3（Celery 定时任务）

从政府网站和新闻网站抓取最新文章，用 DeepSeek 做 AI 摘要，
生成草稿笔记入库，等待人工审核后发布。
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from celery import shared_task
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger("wenshan-kb.crawler")

# ── 数据源配置 ──
SOURCES = [
    {
        "name": "文山州政府",
        "url": "http://www.ynws.gov.cn/",
        "type": "gov",
        "article_selector": "a[href*='/content/'], a[href*='/info/'], a[href*='/zwgk/'], a[href*='.shtml'], a[href*='/news/']",
        "content_selector": "div.article-content, div.content, div.text, div.TRS_Editor, div.Custom_UnionStyle, div.main-content, .con_text, .art_con, .news-content",
        "title_selector": "h1, .article-title, .title, .bt, .art_tit, .news-title",
    },
    {
        "name": "新华网-文山",
        "url": "https://www.yn.xinhuanet.com/ws/index.htm",
        "type": "news",
        "article_selector": "a[href*='ws'], a[href*='xinhuanet'], a[target]",
        "content_selector": "div.content, div.article, div.text, .detail, .main-content",
        "title_selector": "h1, .title, .article-title",
    },
    {
        "name": "人民网-云南频道",
        "url": "http://yn.people.com.cn/",
        "type": "news",
        "article_selector": "a[href*='yn.people'], a[href*='n2'], a[href*='GB']",
        "content_selector": "div.rm_txt_con, div.content, div.text_con, .article, .main-content",
        "title_selector": "h1, .article-title, .title, .rm_title1",
    },
]


async def _fetch_page(client: httpx.AsyncClient, url: str) -> str:
    """抓取网页内容"""
    resp = await client.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        follow_redirects=True,
        timeout=30,
    )
    return resp.text


def _extract_articles(html: str, source_url: str, selector: str) -> list[dict]:
    """从 HTML 中提取文章链接"""
    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for link in soup.select(selector):
        href = link.get("href", "")
        title = link.get("title", "") or link.text.strip()
        if not href or not title or len(title) < 8:
            continue

        # 补全相对 URL
        full_url = urljoin(source_url, href)

        # 去重
        url_hash = hashlib.md5(full_url.encode()).hexdigest()

        articles.append({
            "url": full_url,
            "title": title.strip()[:120],
            "url_hash": url_hash,
        })

    return articles


async def _fetch_article_content(client: httpx.AsyncClient, url: str,
                                  content_sel: str, title_sel: str) -> dict | None:
    """获取文章详情页的正文和标题"""
    try:
        html = await _fetch_page(client, url)
        soup = BeautifulSoup(html, "html.parser")

        # 提取标题
        title_el = soup.select_one(title_sel)
        title = title_el.text.strip() if title_el else ""

        # 提取正文（逐个选择器尝试）
        body = ""
        for selector in content_sel.split(", "):
            el = soup.select_one(selector)
            if el:
                body = el.text.strip()
                if len(body) > 200:
                    break

        # 回退策略：去除脚本/样式/导航后取最大文本块
        if len(body) < 200:
            for tag_name in ["script", "style", "nav", "header", "footer", "noscript"]:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
            candidates = []
            for tag in ["article", "main", "div", "section", "p", "td"]:
                for el in soup.find_all(tag):
                    txt = el.get_text(strip=True)
                    if 200 < len(txt) < 10000:
                        candidates.append((len(txt), txt))
            if candidates:
                candidates.sort(reverse=True)
                body = candidates[0][1]

        # 清理空白
        body = "\n".join(line.strip() for line in body.split("\n") if line.strip())

        if len(body) < 100:
            return None

        return {"title": title or url, "body": body, "url": url}
    except Exception as e:
        logger.warning(f"  抓取失败 {url}: {e}")
        return None


async def _ai_summary(article: dict) -> dict:
    """用 DeepSeek 生成摘要、标签和建议分类"""
    settings = get_settings()
    if not settings.LLM_API_KEY:
        return {"summary": article["body"][:300], "tags": ["采集"], "category": "未分类"}

    try:
        client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        prompt = f"""你是一个文山州知识库编辑。请分析以下新闻/公告内容，输出 JSON：

{{
  "summary": "150字以内的摘要，罗列核心数据点",
  "tags": ["3-5个相关标签，如文山、绿色铝、经济"],
  "category": "最适合的分类（经济发展/文化旅游/特产与资源/交通与基础设施/政策与治理/社会民生/地理与自然环境/历史沿革/行政区划/人口与民族）"
}}

文章标题：{article["title"]}
文章内容：{article["body"][:3000]}
"""

        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        import json
        result = json.loads(resp.choices[0].message.content)
        return {
            "summary": result.get("summary", article["body"][:300]),
            "tags": result.get("tags", ["采集"]),
            "category": result.get("category", "未分类"),
        }
    except Exception as e:
        logger.warning(f"AI 摘要失败: {e}")
        return {"summary": article["body"][:300], "tags": ["采集"], "category": "未分类"}


async def _save_draft(db: AsyncSession, article: dict, ai: dict) -> bool:
    """将采集到的文章以草稿形式写入 notes 表"""
    title = article["title"]
    body = article["body"]

    # 检查是否已存在
    result = await db.execute(
        text("SELECT id FROM notes WHERE source_path = :src AND source_type = 'crawler'"),
        {"src": article["url"]},
    )
    if result.fetchone():
        return False  # 已采集过，跳过

    content = f"""# {title}

> 来源：[{article["url"]}]({article["url"]})
> 采集时间：{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}
> 状态：待审核 AI 摘要

---

{body[:5000]}

---

## AI 摘要

{ai["summary"]}
"""

    url_hash = hashlib.md5(article["url"].encode()).hexdigest()[:8]
    await db.execute(text("""
        INSERT INTO notes (title, slug, content, plain_text, status,
                           source_path, source_type, created_at)
        VALUES (:title, :slug, :content, :plain, 'pending_review',
                :src, 'crawler', NOW())
    """), {
        "title": title,
        "slug": f"crawler-{url_hash}",
        "content": content,
        "plain": f"{title}\n\n{ai['summary']}",
        "src": article["url"],
    })
    return True


async def _run_crawler() -> dict:
    """执行一次完整的采集流程"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)

    stats = {"sources_checked": 0, "articles_found": 0, "articles_new": 0, "errors": 0}

    async with httpx.AsyncClient() as client, AsyncSession(engine) as db:
        for source in SOURCES:
            try:
                logger.info(f"[crawler] 采集: {source['name']}")
                stats["sources_checked"] += 1

                # 1. 抓取首页
                html = await _fetch_page(client, source["url"])
                if not html:
                    stats["errors"] += 1
                    continue

                # 2. 提取文章列表
                articles = _extract_articles(html, source["url"], source["article_selector"])
                stats["articles_found"] += len(articles)
                logger.info(f"  找到 {len(articles)} 篇文章")

                # 过滤：只保留看起来像真实文章的 URL（含日期或 /content/ 等模式）
                real_articles = [
                    a for a in articles
                    if any(p in a["url"] for p in ["/content/", "/info/", "/news/", ".shtml", "/article/", "202"])
                ]
                logger.info(f"  其中 {len(real_articles)} 篇疑似真实文章")

                # 3. 逐篇抓取详情 + AI 摘要
                for art in real_articles[:5]:  # 每次最多 5 篇
                    content = await _fetch_article_content(
                        client, art["url"],
                        source["content_selector"],
                        source["title_selector"],
                    )
                    if not content:
                        continue

                    # 4. AI 摘要
                    ai = await _ai_summary(content)

                    # 5. 保存草稿
                    saved = await _save_draft(db, content, ai)
                    if saved:
                        stats["articles_new"] += 1
                        logger.info(f"  ✓ 新草稿: {content['title'][:50]}...")

                await db.commit()

            except Exception as e:
                logger.error(f"[crawler] {source['name']} 失败: {e}")
                stats["errors"] += 1

    await engine.dispose()
    return stats


@shared_task(name="app.evolution.crawler.crawler_task")
def crawler_task():
    """Celery 任务入口"""
    result = asyncio.run(_run_crawler())
    logger.info(f"[crawler] 完成: {result}")
    return result
