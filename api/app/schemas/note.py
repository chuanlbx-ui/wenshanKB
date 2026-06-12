"""笔记相关 Pydantic 模型"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NoteSummary(BaseModel):
    """笔记摘要（列表用）"""
    id: str
    title: str
    slug: str
    category: Optional[str] = None
    status: str
    freshness: Optional[str] = None
    tags: list[str] = []
    excerpt: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NoteDetail(BaseModel):
    """笔记详情"""
    id: str
    title: str
    slug: str
    category: Optional[str] = None
    status: str
    freshness: Optional[str] = None
    content: str
    frontmatter: Optional[dict] = {}
    tags: list[str] = []
    view_count: int = 0
    like_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RelatedNote(BaseModel):
    """相关笔记"""
    id: str
    title: str
    slug: str
    category: Optional[str] = None
