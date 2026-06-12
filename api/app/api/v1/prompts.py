"""Prompt 模板端点"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.deps import get_current_user

router = APIRouter()

VALID_SCENARIOS = {"政务宣传", "文旅推广", "农产品带货", "民族文化", "新闻通讯", "乡土故事"}


@router.get("/prompts")
async def get_prompt_templates(
    scenario: str = Query(..., description="场景类型"),
    sub_scenario: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(get_current_user),
):
    """提示词模板查询"""
    if scenario not in VALID_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"无效场景。可选: {VALID_SCENARIOS}")

    try:
        query = text("""
            SELECT id, scenario, sub_scenario, title, template_content,
                   negative_prompts, suggested_cards, related_style
            FROM prompt_templates
            WHERE scenario = :scenario
        """)
        result = await db.execute(query, {"scenario": scenario})
        rows = result.fetchall()

        if rows:
            templates = []
            for r in rows:
                if sub_scenario and r[2] != sub_scenario:
                    continue
                templates.append({
                    "id": r[0], "scenario": r[1], "sub_scenario": r[2],
                    "title": r[3], "template_content": r[4],
                    "negative_prompts": r[5] or [],
                    "suggested_cards": r[6] or [],
                    "related_style": r[7],
                })
            if templates:
                return {"scenario": scenario, "templates": templates}
    except Exception:
        pass

    raise HTTPException(status_code=404, detail=f"场景 '{scenario}' 下无模板")


@router.get("/prompts/scenarios")
async def list_scenarios():
    """获取所有可用 Prompt 场景"""
    return {"scenarios": [{"name": s, "template_count": 0} for s in VALID_SCENARIOS]}
