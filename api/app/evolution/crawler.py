"""网络信息自动采集 — 回路 3（Celery 定时任务）

每小时抓取数据源。每次同时扫描最新页面和历史归档页面，
支持分页遍历，确保不限于最新5篇，历史数据也能被挖掘入库。

流程：抓取首页 → 提取文章列表 → 遍历分页归档 → 提取更多旧文章
     → 去重（已有则跳过） → AI摘要 → 保存待审核草稿
"""

import asyncio
import hashlib
import json
import logging
import random
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import httpx
from bs4 import BeautifulSoup
from celery import shared_task
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger("wenshan-kb.crawler")

# ── 数据源配置（仅限文山州本地相关源） ──
SOURCES = [
    {
        "name": "文山州政府",
        "url": "http://www.ynws.gov.cn/",
        "type": "gov",
        "allowed_domains": ["ynws.gov.cn"],
        "article_selector": ("a[href*='/content/'], a[href*='/info/'], "
                             "a[href*='/zwgk/']"),
        "content_selector": ("div.article-content, div.content, div.text, "
                             "div.TRS_Editor, div.Custom_UnionStyle, "
                             "div.main-content, .con_text, .art_con, .news-content"),
        "title_selector": "h1, .article-title, .title, .bt, .art_tit, .news-title",
        "pagination_selector": "a[href*='page'], a[href*='index_'], a.next, a:has(+ .next)",
    },
    {
        "name": "文山新闻网",
        "url": "https://www.wswxw.com/",
        "type": "news",
        "allowed_domains": ["wswxw.com"],
        "article_selector": ("a[href*='wswxw'], a[href*='/html/'], "
                             "a[href*='.html'], a[href*='/news/']"),
        "content_selector": ("div.article-content, div.content, div.text, "
                             "div.article, .detail, .main-content, .con_text"),
        "title_selector": "h1, .article-title, .title, .art_tit",
        "pagination_selector": "a[href*='page'], a[href*='index_'], a.next",
    },
    {
        "name": "新华网-文山",
        "url": "https://www.yn.xinhuanet.com/ws/index.htm",
        "type": "news",
        "allowed_domains": ["yn.xinhuanet.com", "xinhuanet.com"],
        "article_selector": ("a[href*='/ws/']"),
        "content_selector": ("div.content, div.article, div.text, "
                             ".detail, .main-content"),
        "title_selector": "h1, .title, .article-title",
        "pagination_selector": "a[href*='page'], a[href*='index_'], a.next",
    },
]

# 运行时参数
MAX_ARTICLES_PER_SOURCE = 15       # 每次每源最多抓取篇数
MAX_PAGINATION_PAGES = 3           # 每源最多遍历分页数
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


async def _fetch_page(client: httpx.AsyncClient, url: str) -> str:
    """抓取网页内容（随机UA，防封）"""
    ua = random.choice(USER_AGENTS)
    resp = await client.get(
        url,
        headers={"User-Agent": ua},
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

        # 提取标题（多个选择器依次尝试，需要覆盖不同站点结构）
        title = ""
        for sel in title_sel.split(", "):
            el = soup.select_one(sel)
            if el:
                t = el.text.strip()
                if 4 < len(t) < 300:
                    title = t
                    break

        # 如果上面的选择器都没命中，尝试从 <title> 标签提取
        if not title:
            title_tag = soup.find("title")
            if title_tag:
                t = title_tag.text.strip()
                # 去掉站点名后缀如 " -- 人民网" 等
                for sep in ["--", "-", "—", "|", "："]:
                    if sep in t:
                        t = t.split(sep)[0].strip()
                if 4 < len(t) < 300:
                    title = t

        # 最终 fallback：从 URL 中提取可读片段
        if not title:
            # /n2/2026/0616/c372453-41611870.html -> c372453-41611870
            path = urlparse(url).path
            last_part = path.rstrip(".html").rstrip("/").split("/")[-1]
            title = last_part.replace("-", " ").replace("_", " ").title()

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


async def _is_wenshan_related(article: dict) -> bool:
    """AI 判断文章内容是否与文山州相关（标题含关键词则快速通过）"""
    title = article.get("title", "")
    body = article.get("body", "")
    text_lower = (title + " " + body[:2000]).lower()

    # ── 前置质量检查：快速拒绝明显无效的内容 ──
    # 没有标题或标题是URL（爬取失败）
    if not title or title.startswith("http"):
        return False
    # 正文太短（少于300字很难是有效文章）
    if len(body) < 300:
        return False
    # 标题是省份/城市列表（索引页特征）
    for kw in ["北京\n天津\n", "上海\n江苏\n", "广东\n广西\n"]:
        if kw in title:
            return False
    # 标题包含"首页""列表""索引"等关键词（索引/列表页特征）
    index_keywords = ["首页", "列表", "索引", "index", "Index"]
    if any(kw in title for kw in index_keywords):
        return False

    # 快速关键词匹配：直接含文山地名的秒过
    wenshan_keywords = [
        "文山", "丘北", "砚山", "广南", "富宁", "麻栗坡", "马关", "西畴",
        "普者黑", "坝美", "老山", "者阴山", "八宝", "三七", "八角",
        "文山州", "文山市", "壮乡", "苗岭",
    ]
    if any(kw in text_lower for kw in wenshan_keywords):
        return True

    # 无关键词，调用 AI 判断标题+前500字是否涉及文山
    settings = get_settings()
    if not settings.LLM_API_KEY:
        return False  # 无 LLM Key 时保守跳过

    try:
        client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        prompt = f"""判断这篇文章是否与云南省文山壮族苗族自治州（简称文山州）相关。
只要提到文山州内的人、事、物、政策、经济、文化、旅游、基础设施等，都算相关。
只输出 JSON：{{"related": true}} 或 {{"related": false}}

标题：{title[:200]}
导语：{body[:800]}
"""
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)
        return result.get("related", False)
    except Exception as e:
        logger.warning(f"AI 文山相关性判断失败: {e}")
        return False  # 失败时保守处理，不收录


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
        "plain": body[:5000],
        "src": article["url"],
    })
    return True


async def _extract_pagination_links(html: str, source_url: str, selector: str) -> list[str]:
    """从分页器提取分页链接"""
    soup = BeautifulSoup(html, "html.parser")
    pages = set()
    for link in soup.select(selector):
        href = link.get("href", "")
        if href and href != "#" and not href.startswith("javascript:"):
            full_url = urljoin(source_url, href)
            # 避免死循环：只加入与首页不同但在同域下的URL
            if full_url != source_url.rstrip("/"):
                pages.add(full_url)
    return list(pages)


async def _run_crawler() -> dict:
    """执行一次完整的采集流程（支持分页遍历）"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)

    stats = {"sources_checked": 0, "articles_found": 0,
             "articles_new": 0, "errors": 0, "pages_scanned": 0}

    async with httpx.AsyncClient() as client, AsyncSession(engine) as db:
        for source in SOURCES:
            try:
                logger.info(f"[crawler] 🔍 采集: {source['name']}")
                stats["sources_checked"] += 1

                # 收集所有待扫描的 URL（首页 + 分页）
                urls_to_scan = [source["url"]]
                try:
                    html = await _fetch_page(client, source["url"])
                    pagination = await _extract_pagination_links(
                        html, source["url"], source["pagination_selector"]
                    )
                    # 最多取前 N 个分页
                    urls_to_scan.extend(pagination[:MAX_PAGINATION_PAGES])
                except Exception as e:
                    logger.warning(f"  分页提取失败: {e}")

                # 每页提取文章
                all_article_urls = []
                seen_url_hashes = set()
                for page_url in urls_to_scan:
                    try:
                        html = await _fetch_page(client, page_url)
                        articles = _extract_articles(html, page_url, source["article_selector"])
                        stats["pages_scanned"] += 1

                        for a in articles:
                            if a["url_hash"] not in seen_url_hashes:
                                seen_url_hashes.add(a["url_hash"])
                                all_article_urls.append(a)

                        logger.info(f"  页面 {page_url[:60]}... 找到 {len(articles)} 篇")
                    except Exception as e:
                        logger.warning(f"  扫描页失败 {page_url[:50]}: {e}")

                stats["articles_found"] += len(all_article_urls)
                logger.info(f"  合计 {len(all_article_urls)} 篇文章")

                # 过滤：只保留同域名下的 URL（域名白名单防跨站污染）
                source_domain = urlparse(source["url"]).hostname or ""
                allowed_domains = source.get("allowed_domains", [source_domain])
                real_articles = [
                    a for a in all_article_urls
                    if any(d in a["url"] for d in allowed_domains)
                ]
                logger.info(f"  其中 {len(real_articles)} 篇疑似真实文章")

                # 打乱顺序，避免每次都从头抓取（让旧文章也有机会）
                random.shuffle(real_articles)

                # 逐篇抓取 + AI 摘要 + 保存
                processed = 0
                for art in real_articles:
                    if processed >= MAX_ARTICLES_PER_SOURCE:
                        break

                    content = await _fetch_article_content(
                        client, art["url"],
                        source["content_selector"],
                        source["title_selector"],
                    )
                    if not content:
                        continue

                    ai = await _ai_summary(content)
                    # AI 过滤：判断是否与文山州相关
                    if not await _is_wenshan_related(content):
                        logger.info(f"  ⏭️ 非文山相关, 跳过: {content['title'][:50]}...")
                        processed += 1
                        continue
                    saved = await _save_draft(db, content, ai)
                    if saved:
                        stats["articles_new"] += 1
                        logger.info(f"  ✓ 新草稿: {content['title'][:50]}...")
                    processed += 1

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
