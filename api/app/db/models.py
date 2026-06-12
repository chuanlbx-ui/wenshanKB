"""SQLAlchemy ORM 模型 — 对应 db_schema.sql 的 16 张表"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# ── 用户 ──

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(20), default="user")  # super_admin/editor/reviewer/member/user
    status: Mapped[str] = mapped_column(String(20), default="pending")  # active/disabled/pending
    level: Mapped[int] = mapped_column(Integer, default=1)
    contribution_score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ── 分类 ──

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))


# ── 标签 ──

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)


# ── 笔记（核心表） ──

class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    plain_text: Mapped[Optional[str]] = mapped_column(Text)
    frontmatter: Mapped[dict] = mapped_column(JSONB, default={})

    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/pending_review/published/archived
    freshness: Mapped[str] = mapped_column(String(20), default="fresh")  # fresh/aging/stale/expired
    freshness_score: Mapped[int] = mapped_column(Integer, default=100)

    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[float] = mapped_column(Float, default=0)

    source_path: Mapped[Optional[str]] = mapped_column(String(1024))
    source_type: Mapped[str] = mapped_column(String(32), default="manual")
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    embedding = mapped_column(Vector(1536))

    __table_args__ = (
        Index("idx_notes_status", "status"),
        Index("idx_notes_category", "category_id"),
        Index("idx_notes_slug", "slug"),
        Index("idx_notes_embedding", "embedding", postgresql_using="ivfflat",
              postgresql_with={"lists": 100}),
    )


# ── 笔记-标签关联 ──

class NoteTag(Base):
    __tablename__ = "note_tags"

    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


# ── Wikilink 关系 ──

class NoteLink(Base):
    __tablename__ = "note_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    target_note_slug: Mapped[Optional[str]] = mapped_column(String(512))
    target_note_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("notes.id", ondelete="SET NULL"))
    link_text: Mapped[Optional[str]] = mapped_column(String(512))
    link_type: Mapped[str] = mapped_column(String(32), default="wikilink")

    __table_args__ = (
        Index("idx_links_source", "source_note_id"),
        Index("idx_links_target", "target_note_id"),
    )


# ── 素材卡片 ──

class MaterialCard(Base):
    __tablename__ = "material_cards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    core_data: Mapped[str] = mapped_column(Text, nullable=False)
    full_content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(64))
    applicable_scenarios: Mapped[list] = mapped_column(JSONB, default=[])
    source_note_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("notes.id"))


# ── Prompt 模板 ──

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(String(64), nullable=False)
    sub_scenario: Mapped[Optional[str]] = mapped_column(String(256))
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompts: Mapped[Optional[list]] = mapped_column(ARRAY(Text))
    suggested_cards: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    related_style: Mapped[Optional[str]] = mapped_column(String(32))


# ── 反馈 ──

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    related_note_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("notes.id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="web")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ── 搜索日志 ──

class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(20), default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ── 笔记版本 ──

class NoteVersion(Base):
    __tablename__ = "note_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    frontmatter: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("note_id", "version_num"),
    )
