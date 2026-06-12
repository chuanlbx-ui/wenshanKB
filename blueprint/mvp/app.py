#!/usr/bin/env python3
"""
WenShanKB MVP — FastAPI 应用骨架
最小可运行后端，挂载核心 API 端点

运行:
    pip install fastapi uvicorn psycopg2-binary asyncpg sqlalchemy
    pip install pgvector openai pyyaml python-multipart
    python app.py

环境变量:
    DATABASE_URL=postgresql+asyncpg://kb_user:kb_pass@localhost:5432/wenshan_kb
    DATABASE_URL_SYNC=postgresql://kb_user:kb_pass@localhost:5432/wenshan_kb
    AGENT_API_KEY=wskb-dev-key
    SECRET_KEY=dev-secret-change-in-production
"""

import os
import re
import sys
import time
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from typing import Optional, Annotated

from fastapi import (
    FastAPI, HTTPException, Depends, Query, Path, Request, Security
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ── 日志 ────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wenshan-kb")

# ── 配置 ────────────────────────────────────────────
class Settings:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://kb_user:kb_pass@localhost:5432/wenshan_kb"
    )
    DATABASE_URL_SYNC = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://kb_user:kb_pass@localhost:5432/wenshan_kb"
    )
    AGENT_API_KEY = os.getenv("AGENT_API_KEY", "wskb-dev-key")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    VERSION = "0.1.0"
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 50

settings = Settings()

# ── 生命周期 ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的初始化与清理"""
    logger.info(f"WenShanKB API v{settings.VERSION} 启动中...")
    try:
        # 验证 sync 数据库连接
        import psycopg2
        conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
        conn.close()
        logger.info("  数据库连接正常")
    except Exception as e:
        logger.warning(f"  数据库连接失败: {e}。部分功能不可用。")
    yield
    logger.info("WenShanKB API 已关闭")

app = FastAPI(
    title="WenShanKB API",
    description="文山州 AI 创作公共知识库系统 API",
    version=settings.VERSION,
    lifespan=lifespan,
)

# ── 中间件 ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 安全 ────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)

def verify_api_key(api_key: str) -> bool:
    """验证 Agent API Key"""
    if not api_key:
        return False
    # 简单实现：比较哈希
    # 生产环境应查询 api_keys 表
    return api_key == settings.AGENT_API_KEY

async def get_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
):
    """
    统一认证中间件：支持 JWT Bearer Token 和 X-API-Key 两种方式。
    至少一种通过即放行。
    """
    # 方式 1：Bearer Token (JWT)
    if credentials and credentials.credentials.startswith("ey"):
        # TODO: 验证 JWT
        # payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        return {"auth_type": "user", "user_id": None}

    # 方式 2：X-API-Key
    api_key = request.headers.get("X-API-Key", "")
    if verify_api_key(api_key):
        return {"auth_type": "agent", "api_key": api_key[:8] + "..."}

    raise HTTPException(status_code=401, detail="未认证：请提供有效的 Bearer Token 或 X-API-Key")


# ── 数据模型 ────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询")
    category: Optional[str] = Field(None, description="按分类过滤")
    tags: Optional[list[str]] = Field(None, description="按标签过滤")
    status: str = Field("published", description="笔记状态")
    search_mode: str = Field("hybrid", description="搜索模式: semantic/fulltext/hybrid")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=50, description="每页条数")

class NoteSummary(BaseModel):
    id: str
    title: str
    slug: str
    category: Optional[str]
    status: str
    freshness: Optional[str] = None
    tags: list[str] = []
    excerpt: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class SearchResult(BaseModel):
    note: NoteSummary
    score: float
    snippet: Optional[str]
    match_type: str

class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int

class SearchResponse(BaseModel):
    results: list[SearchResult]
    pagination: Pagination
    search_time_ms: int

class MaterialCard(BaseModel):
    id: str
    title: str
    core_data: str
    category: Optional[str]
    applicable_scenarios: list[str] = []
    source_note: Optional[str]
    full_content: str

class PromptTemplate(BaseModel):
    id: int
    scenario: str
    sub_scenario: Optional[str]
    title: str
    template_content: str
    negative_prompts: list[str] = []
    suggested_cards: list[str] = []
    related_style: Optional[str]

class ComplianceRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    content_type: str = "通用"
    check_categories: list[str] = ["all"]

class ComplianceIssue(BaseModel):
    category: str
    severity: str
    location: str
    issue: str
    suggestion: str
    rule_ref: Optional[str]

class ComplianceResponse(BaseModel):
    passed: bool
    overall_score: int
    issues: list[ComplianceIssue] = []
    warnings: list[ComplianceIssue] = []
    passed_checks: list[str]
    check_time_ms: int

class FeedbackRequest(BaseModel):
    feedback_type: str = Field(..., description="content_suggestion/error_correction/knowledge_gap/quality_feedback")
    related_note_slug: Optional[str] = None
    content: str = Field(..., min_length=1, max_length=5000)
    source_conversation_id: Optional[str] = None


# ── 数据库辅助（同步，用于简单查询，生产环境改用 async） ──
def get_sync_db():
    """获取同步数据库连接（简单实现）"""
    import psycopg2
    import psycopg2.extras
    psycopg2.extras.register_uuid()
    try:
        conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
        return conn
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"数据库不可用: {str(e)}"
        )

def query_notes(params: dict) -> dict:
    """通用笔记查询"""
    conn = get_sync_db()
    try:
        cur = conn.cursor()

        conditions = ["n.status = 'published'"]
        vals = []

        if params.get("category"):
            conditions.append("c.name = %s")
            vals.append(params["category"])
        if params.get("tag"):
            conditions.append("EXISTS (SELECT 1 FROM note_tags nt JOIN tags t ON nt.tag_id=t.id WHERE nt.note_id=n.id AND t.name=%s)")
            vals.append(params["tag"])

        where = " AND ".join(conditions)
        page = params.get("page", 1)
        page_size = min(params.get("page_size", 20), 50)
        offset = (page - 1) * page_size

        cur.execute(f"""
            SELECT n.id, n.title, n.slug, c.display_name, n.status,
                   n.view_count, n.like_count, n.created_at, n.updated_at,
                   COUNT(*) OVER() AS total
            FROM notes n
            LEFT JOIN categories c ON n.category_id = c.id
            WHERE {where}
            ORDER BY n.updated_at DESC
            LIMIT %s OFFSET %s
        """, vals + [page_size, offset])

        rows = cur.fetchall()
        total = rows[0][-1] if rows else 0

        notes = []
        for r in rows:
            notes.append(NoteSummary(
                id=str(r[0]), title=r[1], slug=r[2], category=r[3],
                status=r[4], view_count=r[5], like_count=r[6],
                created_at=r[7], updated_at=r[8],
            ).model_dump())

        cur.close()
        return {
            "notes": notes,
            "pagination": {
                "page": page, "page_size": page_size,
                "total": total,
                "total_pages": max((total + page_size - 1) // page_size, 1),
            }
        }
    finally:
        conn.close()


# ── 模拟数据（当数据库不可用时） ──────────────────────
MOCK_NOTES = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "title": "普者黑旅游攻略",
        "slug": "普者黑旅游攻略",
        "category": "文化旅游",
        "status": "published",
        "freshness": "fresh",
        "tags": ["旅游", "普者黑", "5A景区"],
        "excerpt": "普者黑国家5A级景区，312座孤峰、54个湖泊...",
        "view_count": 1523,
        "like_count": 89,
        "created_at": datetime(2025, 5, 15, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 5, 15, tzinfo=timezone.utc),
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "title": "文山三七产业深度报告",
        "slug": "文山三七产业深度报告",
        "category": "特产与资源",
        "status": "published",
        "freshness": "fresh",
        "tags": ["三七", "经济", "产业"],
        "excerpt": "文山三七产量占全国90%以上，种植面积超60万亩...",
        "view_count": 980,
        "like_count": 56,
        "created_at": datetime(2025, 3, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 4, 20, tzinfo=timezone.utc),
    },
]

MOCK_CARDS = [
    MaterialCard(
        id="卡03", title='\u201c金不换\u201d——文山三七占全国 90% 产量',
        core_data="文山三七产量占全国90%以上，种植面积超60万亩...",
        category="特产卖点",
        applicable_scenarios=["农产品带货", "健康科普"],
        source_note="[[../07-特产与资源/三七]]",
        full_content="完整的卡片内容..."
    ).model_dump(),
    MaterialCard(
        id="卡07", title="普者黑——312座孤峰、54个湖泊的喀斯特奇迹",
        core_data="国家5A级景区，312座孤峰、83个溶洞、54个湖泊...",
        category="旅游亮点",
        applicable_scenarios=["旅游推荐", "短视频脚本"],
        source_note="[[../06-文化旅游/普者黑旅游攻略]]",
        full_content="完整的卡片内容..."
    ).model_dump(),
]

MOCK_PROMPTS = [
    PromptTemplate(
        id=1, scenario="农产品带货", sub_scenario="三七带货脚本",
        title="三七直播带货口播脚本",
        template_content="你是文山三七带货主播。文山三七产量占全国90%以上...",
        negative_prompts=["严禁宣称三七'治疗'疾病", "不使用绝对化用语"],
        suggested_cards=["卡03", "卡11"],
        related_style="带货风格"
    ).model_dump(),
]

COMPLIANCE_RULES = [
    (re.compile(r"治疗|治愈|药到病除|包治"), "advertising", "high",
     "不得使用医疗治疗效果表述", "改为'辅助调理''传统用于'等表述"),
    (re.compile(r"最好|第一|唯一|最.*的"), "advertising", "high",
     "不得使用绝对化用语", "移除或替换为'知名''优质'等"),
    (re.compile(r"争议领土|未定国界|争议地区"), "border", "high",
     "不得质疑已划定边界", "使用'中越边境'等官方表述"),
    (re.compile(r"落后.*(壮族|苗族|彝族|瑶族|民族)|原始.*民族"), "ethnic", "high",
     "不得使用歧视性描述", "改为'传统文化''独特习俗'"),
    (re.compile(r"部队番号|军事部署|兵力|驻军"), "military", "high",
     "不得泄露军事信息", "删除相关信息"),
    (re.compile(r"来源于网络|图片来自网络"), "copyright", "medium",
     "网络素材版权存疑", "使用自有或已授权素材"),
]


# ── API 端点 ────────────────────────────────────────

@app.get("/api/v1/health", tags=["系统"])
async def health_check():
    """健康检查"""
    db_status = "disconnected"
    try:
        import psycopg2
        conn = psycopg2.connect(settings.DATABASE_URL_SYNC, connect_timeout=3)
        conn.close()
        db_status = "connected"
    except Exception:
        pass

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": settings.VERSION,
        "database": db_status,
        "vector_index": "not_initialized",
    }


@app.post("/api/v1/search", response_model=SearchResponse, tags=["搜索"])
async def search_notes(
    body: SearchRequest,
    auth: dict = Depends(get_auth),
):
    """语义搜索"""
    t0 = time.perf_counter()
    with open("/tmp/debug_search.log", "a") as f:
        f.write(f"SEARCH_CALLED query={body.query!r} mode={body.search_mode!r}\n")

    # 尝试真实数据库查询
    try:
        conn = get_sync_db()
        cur = conn.cursor()
        query_text = body.query

        if body.search_mode in ("semantic", "hybrid"):
            # 语义搜索：通过 pgvector 余弦相似度
            # 注意：需要先生成 query embedding
            cur.execute("""
                SELECT n.id, n.title, n.slug, c.display_name, n.status,
                       n.view_count, n.like_count, n.created_at, n.updated_at,
                       n.plain_text,
                       1.0 - (n.embedding <=> '[0.0]'::vector) AS score
                FROM notes n
                LEFT JOIN categories c ON n.category_id = c.id
                WHERE n.status = 'published'
                ORDER BY score DESC
                LIMIT %s
            """, (body.page_size,))
            rows = cur.fetchall()
        else:
            # 全文搜索
            logger.info(f"[DEBUG] fulltext search query_text={query_text!r}, page_size={body.page_size}")
            print(f"[DEBUG-PRINT] fulltext search query_text={query_text!r}, page_size={body.page_size}", flush=True)
            cur.execute("""
                SELECT n.id, n.title, n.slug, c.display_name, n.status,
                       n.view_count, n.like_count, n.created_at, n.updated_at,
                       n.plain_text,
                       ts_rank(n.search_vector, plainto_tsquery('simple', %s)) AS score
                FROM notes n
                LEFT JOIN categories c ON n.category_id = c.id
                WHERE n.status = 'published'
                  AND n.search_vector @@ plainto_tsquery('simple', %s)
                ORDER BY score DESC
                LIMIT %s
            """, (body.query, body.query, body.page_size))
            rows = cur.fetchall()
        cur.close()
        conn.close()
        with open("/tmp/debug_search.log", "a") as f:
            f.write(f"ROWS={len(rows)}\n")
        logger.info(f"[DEBUG] search rows={len(rows)}, status_ok={len(rows) > 0}")
        print(f"[DEBUG-PRINT] search rows={len(rows)}", flush=True)

        if rows:
            with open("/tmp/debug_search.log", "a") as f:
                f.write(f"ENTERED_IF_ROWS row0={rows[0][1]!r}\n")
            results = []
            for r in rows:
                note = NoteSummary(
                    id=str(r[0]), title=r[1], slug=r[2], category=r[3],
                    status=r[4], view_count=r[5] or 0, like_count=r[6] or 0,
                    created_at=r[7], updated_at=r[8],
                )
                snippet = (r[9] or "")[:200]
                results.append(SearchResult(
                    note=note, score=round(r[10], 4) if r[10] else 0.0,
                    snippet=snippet, match_type=body.search_mode
                ).model_dump())

            elapsed = int((time.perf_counter() - t0) * 1000)
            return SearchResponse(
                results=results,
                pagination=Pagination(page=1, page_size=body.page_size,
                                      total=len(results), total_pages=1),
                search_time_ms=elapsed,
            )

    except Exception as e:
        with open("/tmp/debug_search.log", "a") as f:
            f.write(f"EXCEPTION_CAUGHT: {e}\n")
        logger.error(f"数据库搜索异常: {e}", exc_info=True)

    # 数据库无结果或异常时返回空结果
    with open("/tmp/debug_search.log", "a") as f:
        f.write("FALLBACK_EMPTY\n")
    elapsed = int((time.perf_counter() - t0) * 1000)
    return SearchResponse(
        results=[],
        pagination=Pagination(page=1, page_size=body.page_size,
                              total=0, total_pages=0),
        search_time_ms=elapsed,
    )


@app.get("/api/v1/notes", tags=["笔记"])
async def list_notes(
    category: Optional[str] = Query(None),
    status: str = Query("published"),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    """笔记列表（公开端点，无需认证）"""
    try:
        return query_notes({
            "category": category,
            "tag": tag,
            "page": page,
            "page_size": page_size,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"笔记列表查询异常: {e}", exc_info=True)
        return {
            "notes": [],
            "pagination": {"page": 1, "page_size": 20, "total": 0, "total_pages": 0},
        }


@app.get("/api/v1/notes/{slug}", tags=["笔记"])
async def get_note(slug: str):
    """笔记详情"""
    conn = get_sync_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT n.id, n.title, n.slug, c.display_name, n.status,
                   n.freshness, n.content, n.frontmatter, n.plain_text,
                   n.view_count, n.like_count, n.created_at, n.updated_at
            FROM notes n
            LEFT JOIN categories c ON n.category_id = c.id
            WHERE n.slug = %s AND n.status = 'published'
        """, (slug,))
        row = cur.fetchone()
        cur.close()

        if row:
            # 增加浏览量
            cur2 = conn.cursor()
            cur2.execute("UPDATE notes SET view_count = view_count + 1 WHERE slug = %s", (slug,))
            conn.commit()
            cur2.close()

            return {
                "id": str(row[0]), "title": row[1], "slug": row[2],
                "category": row[3], "status": row[4], "freshness": row[5],
                "content": row[6], "frontmatter": row[7],
                "excerpt": (row[8] or "")[:200],
                "view_count": row[9], "like_count": row[10],
                "created_at": row[11].isoformat(), "updated_at": row[12].isoformat(),
            }
    except Exception as e:
        logger.error(f"数据库查询笔记失败: {e}", exc_info=True)
    finally:
        conn.close()

    # DB 无结果或异常时返回 404
    raise HTTPException(status_code=404, detail=f"笔记 '{slug}' 不存在")


@app.get("/api/v1/notes/{slug}/related", tags=["笔记"])
async def get_related_notes(slug: str, limit: int = Query(5, ge=1, le=20)):
    """相关笔记推荐"""
    conn = get_sync_db()
    try:
        cur = conn.cursor()
        # 通过 wikilink 关系找关联笔记
        cur.execute("""
            SELECT n2.id, n2.title, n2.slug, c.display_name
            FROM notes n1
            JOIN note_links nl ON nl.source_note_id = n1.id OR nl.target_note_id = n1.id
            JOIN notes n2 ON (n2.id = nl.source_note_id OR n2.id = nl.target_note_id) AND n2.id != n1.id
            LEFT JOIN categories c ON n2.category_id = c.id
            WHERE n1.slug = %s AND n2.status = 'published'
            GROUP BY n2.id, n2.title, n2.slug, c.display_name
            LIMIT %s
        """, (slug, limit))
        rows = cur.fetchall()
        cur.close()

        return {
            "notes": [
                {"id": str(r[0]), "title": r[1], "slug": r[2], "category": r[3]}
                for r in rows
            ],
            "relation_type": "wikilink",
        }
    except Exception as e:
        logger.warning(f"关联查询失败: {e}")
        return {"notes": [], "relation_type": "wikilink"}
    finally:
        conn.close()


@app.get("/api/v1/materials", tags=["素材卡片"])
async def get_material_cards(
    card_ids: Optional[str] = Query(None, description="逗号分隔卡片ID"),
    query: Optional[str] = Query(None, description="语义匹配查询"),
    category: Optional[str] = Query(None),
    limit: int = Query(3, ge=1, le=10),
    auth: dict = Depends(get_auth),
):
    """素材卡片查询"""
    try:
        conn = get_sync_db()
        cur = conn.cursor()

        if card_ids:
            ids = [c.strip() for c in card_ids.split(",")]
            placeholders = ",".join(["%s"] * len(ids))
            cur.execute(f"""
                SELECT id, title, core_data, category, applicable_scenarios,
                       source_note_id, full_content
                FROM material_cards
                WHERE id IN ({placeholders})
            """, ids)
        else:
            # 全量返回（MVP 阶段 30 张卡片，无需复杂语义匹配）
            cur.execute("""
                SELECT id, title, core_data, category, applicable_scenarios,
                       source_note_id, full_content
                FROM material_cards
                ORDER BY id
                LIMIT %s
            """, (limit,))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        if rows:
            cards = []
            for r in rows:
                cards.append(MaterialCard(
                    id=r[0], title=r[1], core_data=r[2], category=r[3],
                    applicable_scenarios=r[4] or [],
                    source_note=f"笔记 #{r[5]}" if r[5] else None,
                    full_content=r[6]
                ).model_dump())
            return {"cards": cards, "total": len(cards)}
    except Exception as e:
        logger.warning(f"素材卡片查询失败: {e}")

    # 回退到模拟数据
    if card_ids:
        ids = set(card_ids.split(","))
        cards = [c for c in MOCK_CARDS if c["id"] in ids]
    else:
        cards = MOCK_CARDS[:limit]

    return {"cards": cards, "total": len(cards)}


@app.get("/api/v1/prompts", tags=["提示词"])
async def get_prompt_templates(
    scenario: str = Query(..., description="场景类型"),
    sub_scenario: Optional[str] = Query(None),
    custom_context: Optional[str] = Query(None),
    auth: dict = Depends(get_auth),
):
    """提示词模板查询"""
    valid_scenarios = {"政务宣传", "文旅推广", "农产品带货", "民族文化", "新闻通讯", "乡土故事"}
    if scenario not in valid_scenarios:
        raise HTTPException(status_code=400, detail=f"无效场景。可选: {valid_scenarios}")

    try:
        conn = get_sync_db()
        cur = conn.cursor()

        conditions = ["scenario = %s"]
        vals = [scenario]
        if sub_scenario:
            conditions.append("sub_scenario = %s")
            vals.append(sub_scenario)

        cur.execute(f"""
            SELECT id, scenario, sub_scenario, title, template_content,
                   negative_prompts, suggested_cards, related_style
            FROM prompt_templates
            WHERE {' AND '.join(conditions)}
        """, vals)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if rows:
            templates = []
            for r in rows:
                content = r[4]
                if custom_context:
                    content = content.replace("[填写]", custom_context)
                templates.append(PromptTemplate(
                    id=r[0], scenario=r[1], sub_scenario=r[2], title=r[3],
                    template_content=content,
                    negative_prompts=r[5] or [],
                    suggested_cards=r[6] or [],
                    related_style=r[7]
                ).model_dump())
            return {"scenario": scenario, "templates": templates}
    except Exception as e:
        logger.warning(f"Prompt 查询失败: {e}")

    # 回退到模拟数据
    matched = [p for p in MOCK_PROMPTS if p["scenario"] == scenario]
    if sub_scenario:
        matched = [p for p in matched if p.get("sub_scenario") == sub_scenario]

    if not matched:
        raise HTTPException(status_code=404, detail=f"场景 '{scenario}' 下无模板")

    return {"scenario": scenario, "templates": matched}


@app.get("/api/v1/prompts/scenarios", tags=["提示词"])
async def list_scenarios():
    """获取所有可用 Prompt 场景"""
    return {
        "scenarios": [
            {"name": s, "template_count": 3 + i}
            for i, s in enumerate(["政务宣传", "文旅推广", "农产品带货", "民族文化", "新闻通讯", "乡土故事"])
        ]
    }


@app.post("/api/v1/compliance/check", response_model=ComplianceResponse, tags=["合规"])
async def check_compliance(
    body: ComplianceRequest,
    auth: dict = Depends(get_auth),
):
    """合规检查"""
    t0 = time.perf_counter()
    issues = []
    warnings = []
    checked = set()

    for pattern, category, severity, description, suggestion in COMPLIANCE_RULES:
        if body.check_categories != ["all"] and category not in body.check_categories:
            continue
        checked.add(category)

        for match in pattern.finditer(body.content):
            issue = ComplianceIssue(
                category=category,
                severity=severity,
                location=f"位置 {match.start()}-{match.end()}: ...{body.content[max(0,match.start()-20):match.end()+20]}...",
                issue=description,
                suggestion=suggestion,
                rule_ref="[[合规指南]]"
            )
            if severity == "high":
                issues.append(issue)
            else:
                warnings.append(issue)

    score = max(0, 100 - len(issues) * 15 - len(warnings) * 5)
    elapsed = int((time.perf_counter() - t0) * 1000)

    return ComplianceResponse(
        passed=len(issues) == 0,
        overall_score=score,
        issues=issues,
        warnings=warnings,
        passed_checks=list(checked),
        check_time_ms=elapsed,
    )


@app.post("/api/v1/feedback", status_code=201, tags=["反馈"])
async def submit_feedback(
    body: FeedbackRequest,
    auth: dict = Depends(get_auth),
):
    """提交反馈"""
    # 写入数据库
    try:
        conn = get_sync_db()
        cur = conn.cursor()
        note_id = None
        if body.related_note_slug:
            cur.execute("SELECT id FROM notes WHERE slug = %s", (body.related_note_slug,))
            row = cur.fetchone()
            if row:
                note_id = row[0]

        cur.execute("""
            INSERT INTO feedback (type, related_note_id, content, source,
                source_conversation_id, submitter_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            body.feedback_type, note_id, body.content,
            auth.get("auth_type", "web"),
            body.source_conversation_id,
            auth.get("user_id"),
        ))
        feedback_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return {"feedback_id": str(feedback_id), "status": "pending"}
    except Exception as e:
        logger.error(f"反馈提交失败: {e}")
        raise HTTPException(status_code=500, detail=f"反馈提交失败: {str(e)}")


# ── 异常处理 ────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": f"HTTP_{exc.status_code}", "message": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "服务器内部错误"},
    )


# ── 启动入口 ────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print(f"""
╔══════════════════════════════════════════════════════╗
║         WenShanKB API v{settings.VERSION}                       ║
║         文山州 AI 创作公共知识库系统                    ║
╠══════════════════════════════════════════════════════╣
║  文档: http://localhost:8000/docs                    ║
║  健康: http://localhost:8000/api/v1/health           ║
║  搜索: POST http://localhost:8000/api/v1/search      ║
║  笔记: GET  http://localhost:8000/api/v1/notes       ║
║  素材: GET  http://localhost:8000/api/v1/materials   ║
║  Prompt: GET http://localhost:8000/api/v1/prompts    ║
║  合规: POST http://localhost:8000/api/v1/compliance/check ║
╚══════════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
