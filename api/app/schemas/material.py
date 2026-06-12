"""素材卡片 + Prompt 模板相关 Schema"""

from typing import Optional
from pydantic import BaseModel, Field


class MaterialCardOut(BaseModel):
    id: str
    title: str
    core_data: str
    category: Optional[str] = None
    applicable_scenarios: list[str] = []
    source_note: Optional[str] = None
    full_content: str


class MaterialCardsResponse(BaseModel):
    cards: list[MaterialCardOut]
    total: int


class PromptTemplateOut(BaseModel):
    id: int
    scenario: str
    sub_scenario: Optional[str] = None
    title: str
    template_content: str
    negative_prompts: list[str] = []
    suggested_cards: list[str] = []
    related_style: Optional[str] = None


class PromptTemplatesResponse(BaseModel):
    scenario: str
    templates: list[PromptTemplateOut]
