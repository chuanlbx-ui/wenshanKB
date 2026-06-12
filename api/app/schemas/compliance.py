"""合规检查相关 Schema"""

from typing import Optional
from pydantic import BaseModel, Field


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
    rule_ref: Optional[str] = None


class ComplianceResponse(BaseModel):
    passed: bool
    overall_score: int
    issues: list[ComplianceIssue] = []
    warnings: list[ComplianceIssue] = []
    passed_checks: list[str] = []
    check_time_ms: int


class FeedbackRequest(BaseModel):
    feedback_type: str = Field(..., description="content_suggestion / error_correction / knowledge_gap / quality_feedback")
    related_note_slug: Optional[str] = None
    content: str = Field(..., min_length=1, max_length=5000)
    source_conversation_id: Optional[str] = None
