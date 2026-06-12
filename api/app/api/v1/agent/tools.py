"""Hermes Agent Tool 端点 — 7 个 Tool Schema

每个 Tool 端点都是独立的 HTTP 端点，Hermes Agent 通过 Function Calling 调用。
所有端点需要 X-API-Key 认证。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.api.deps import get_current_user

router = APIRouter(prefix="/agent/tools")


# ═══════════════════════════════════════════════════════
# Tool 1: search_kb — 知识库语义检索
# ═══════════════════════════════════════════════════════

class SearchKbRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = None
    max_results: int = Field(5, ge=1, le=10)
    include_full_content: bool = False


@router.post("/search_kb")
async def tool_search_kb(
    body: SearchKbRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(get_current_user),
):
    """Agent Tool: 知识库语义检索"""
    from app.api.v1.search import _semantic_search

    results = await _semantic_search(db, body.query, body.max_results)

    output = []
    for r in results:
        item = {
            "title": r["title"],
            "category": r.get("category"),
            "score": r.get("score"),
            "summary": r.get("snippet", ""),
            "source_note": f"[[{r.get('category', '')}/{r['title']}]]",
            "last_updated": str(r.get("updated_at", "")),
        }
        if body.include_full_content:
            # 获取完整内容
            note_result = await db.execute(
                text("SELECT content FROM notes WHERE slug = :slug"),
                {"slug": r["slug"]},
            )
            note_row = note_result.fetchone()
            if note_row:
                item["content"] = note_row[0]
        output.append(item)

    return {"results": output, "total_found": len(output)}


# ═══════════════════════════════════════════════════════
# Tool 2: get_material_card — 获取素材卡片
# ═══════════════════════════════════════════════════════

class MaterialCardRequest(BaseModel):
    card_ids: Optional[list[str]] = None
    query: Optional[str] = None
    category: Optional[str] = None
    max_cards: int = Field(3, ge=1, le=5)


@router.post("/material_card")
async def tool_material_card(
    body: MaterialCardRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(get_current_user),
):
    """Agent Tool: 获取素材卡片"""
    try:
        if body.card_ids:
            placeholders = ",".join([f":id_{i}" for i in range(len(body.card_ids))])
            params = {f"id_{i}": body.card_ids[i] for i in range(len(body.card_ids))}
            result = await db.execute(
                text(f"SELECT id, title, core_data, category, applicable_scenarios, source_note_id, full_content FROM material_cards WHERE id IN ({placeholders})"),
                params,
            )
        else:
            result = await db.execute(
                text("SELECT id, title, core_data, category, applicable_scenarios, source_note_id, full_content FROM material_cards ORDER BY id LIMIT :limit"),
                {"limit": body.max_cards},
            )

        rows = result.fetchall()
        cards = [{"card_id": r[0], "title": r[1], "core_data": r[2],
                  "category": r[3], "applicable_scenarios": r[4] or [],
                  "source_note": f"笔记 #{r[5]}" if r[5] else None,
                  "full_content": r[6]} for r in rows]
        return {"cards": cards, "total": len(cards)}
    except Exception:
        return {"cards": [], "total": 0}


# ═══════════════════════════════════════════════════════
# Tool 3: get_prompt_template — 获取创作 Prompt
# ═══════════════════════════════════════════════════════

class PromptTemplateRequest(BaseModel):
    scenario: str = Field(..., description="政务宣传/文旅推广/农产品带货/民族文化/新闻通讯/乡土故事")
    sub_scenario: Optional[str] = None
    custom_context: Optional[str] = None


@router.post("/prompt_template")
async def tool_prompt_template(
    body: PromptTemplateRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(get_current_user),
):
    """Agent Tool: 获取创作 Prompt 模板"""
    try:
        result = await db.execute(
            text("SELECT id, scenario, sub_scenario, title, template_content, negative_prompts, suggested_cards, related_style FROM prompt_templates WHERE scenario = :scenario"),
            {"scenario": body.scenario},
        )
        rows = result.fetchall()

        templates = []
        for r in rows:
            if body.sub_scenario and r[2] != body.sub_scenario:
                continue
            content = r[4]
            if body.custom_context:
                content = content.replace("[填写]", body.custom_context)
            templates.append({
                "id": r[0], "scenario": r[1], "sub_scenario": r[2],
                "title": r[3], "template_content": content,
                "negative_prompts": r[5] or [],
                "suggested_cards": r[6] or [],
                "related_style": r[7],
            })

        if templates:
            return {"scenario": body.scenario, "templates": templates}
    except Exception:
        pass

    return {"scenario": body.scenario, "templates": []}


# ═══════════════════════════════════════════════════════
# Tool 4: check_compliance — 合规检查
# ═══════════════════════════════════════════════════════

class ComplianceCheckRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    content_type: str = "通用"
    check_categories: list[str] = ["all"]


@router.post("/compliance")
async def tool_compliance(
    body: ComplianceCheckRequest,
    auth: dict = Depends(get_current_user),
):
    """Agent Tool: 合规检查"""
    from app.api.v1.compliance import check_compliance as _check
    from app.schemas.compliance import ComplianceRequest
    cr = ComplianceRequest(
        content=body.content, content_type=body.content_type,
        check_categories=body.check_categories,
    )
    return await _check(cr, auth)


# ═══════════════════════════════════════════════════════
# Tool 5: get_style_guide — 获取风格指南
# ═══════════════════════════════════════════════════════

class StyleGuideRequest(BaseModel):
    style: str = Field(..., description="政务/文旅/带货/新闻")
    format: str = Field("cheatsheet", description="full/cheatsheet")


STYLE_GUIDES = {
    "政务": "语调正式、数据准确、引用官方来源。避免口语化和情绪化表达。",
    "文旅": "生动形象、突出体验感、多用感官描述。适合小红书/抖音风格。",
    "带货": "突出卖点、数据支撑、紧迫感营造。遵守广告法，不用绝对化用语。",
    "新闻": "5W1H 结构、客观中立、事实优先。导语简洁，正文递进。",
}


@router.post("/style_guide")
async def tool_style_guide(
    body: StyleGuideRequest,
    auth: dict = Depends(get_current_user),
):
    """Agent Tool: 获取风格指南"""
    content = STYLE_GUIDES.get(body.style, "")
    if body.format == "cheatsheet":
        # 返回精简版
        return {"style": body.style, "format": "cheatsheet", "content": content}
    return {"style": body.style, "format": "full", "content": content}


# ═══════════════════════════════════════════════════════
# Tool 6: get_ip_story — 获取 IP 故事素材
# ═══════════════════════════════════════════════════════

class IPStoryRequest(BaseModel):
    ip_name: Optional[str] = None
    query: Optional[str] = None
    format: str = Field("card", description="card/narrative")


IP_STORIES = {
    "三七精灵": {
        "name": "三七精灵",
        "origin": "文山壮族民间传说",
        "adaptable_to": ["动画短片", "表情包", "IP 联名"],
        "narrative": "三七精灵是文山三七文化的拟人化形象，象征着健康与生命力…",
    },
    "句町女王": {
        "name": "句町女王",
        "origin": "句町古国历史",
        "adaptable_to": ["历史剧", "文创产品", "景区IP"],
        "narrative": "句町女王是古句町国的传奇统治者，文山古代文明的代表…",
    },
}


@router.post("/ip_story")
async def tool_ip_story(
    body: IPStoryRequest,
    auth: dict = Depends(get_current_user),
):
    """Agent Tool: 获取 IP 故事素材"""
    for name, story in IP_STORIES.items():
        if body.ip_name and body.ip_name in name:
            if body.format == "narrative":
                return {"ip_name": name, "format": "narrative", "content": story}
            return {"ip_name": name, "format": "card",
                    "origin": story["origin"],
                    "adaptable_to": story["adaptable_to"]}

    return {"ip_name": body.ip_name or "未找到", "content": {}}


# ═══════════════════════════════════════════════════════
# Tool 7: submit_feedback — 提交反馈回流
# ═══════════════════════════════════════════════════════

class AgentFeedbackRequest(BaseModel):
    feedback_type: str = Field(..., description="content_suggestion / error_correction / knowledge_gap / quality_feedback")
    related_note: Optional[str] = None
    content: str = Field(..., min_length=1, max_length=5000)
    source_conversation_id: Optional[str] = None


@router.post("/feedback", status_code=201)
async def tool_feedback(
    body: AgentFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(get_current_user),
):
    """Agent Tool: 提交反馈回流到知识库"""
    try:
        note_id = None
        if body.related_note:
            result = await db.execute(
                text("SELECT id FROM notes WHERE slug = :slug OR title = :title"),
                {"slug": body.related_note, "title": body.related_note},
            )
            row = result.fetchone()
            if row:
                note_id = row[0]

        result = await db.execute(text("""
            INSERT INTO feedback (id, type, related_note_id, content, source,
                                  source_conversation_id, status)
            VALUES (gen_random_uuid(), :type, :note_id, :content, 'agent',
                    :conv_id, 'pending')
            RETURNING id
        """), {
            "type": body.feedback_type,
            "note_id": note_id,
            "content": body.content,
            "conv_id": body.source_conversation_id,
        })
        feedback_id = result.fetchone()[0]
        return {"feedback_id": str(feedback_id), "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"反馈提交失败: {str(e)}")
