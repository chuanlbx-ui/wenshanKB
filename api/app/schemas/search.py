"""搜索相关 Pydantic 模型"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.note import NoteSummary


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询")
    category: Optional[str] = Field(None, description="按分类过滤")
    search_mode: str = Field("hybrid", description="semantic / fulltext / hybrid")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=50)

    @field_validator("search_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("semantic", "fulltext", "hybrid"):
            raise ValueError("search_mode 必须是 semantic / fulltext / hybrid 之一")
        return v


class SearchResultItem(BaseModel):
    note: NoteSummary
    score: float
    snippet: Optional[str] = None
    match_type: str


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    pagination: Pagination
    search_time_ms: int
