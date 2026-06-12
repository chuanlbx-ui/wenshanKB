"""反馈提交端点"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.compliance import FeedbackRequest

router = APIRouter()


@router.post("/feedback", status_code=201)
async def submit_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(get_current_user),
):
    """提交反馈（纠错/建议/缺口/质量）"""
    try:
        note_id = None
        if body.related_note_slug:
            result = await db.execute(
                text("SELECT id FROM notes WHERE slug = :slug"),
                {"slug": body.related_note_slug},
            )
            row = result.fetchone()
            if row:
                note_id = row[0]

        query = text("""
            INSERT INTO feedback (id, type, related_note_id, content, source,
                                  source_conversation_id, status)
            VALUES (gen_random_uuid(), :type, :note_id, :content, :source,
                    :conv_id, 'pending')
            RETURNING id
        """)
        result = await db.execute(query, {
            "type": body.feedback_type,
            "note_id": note_id,
            "content": body.content,
            "source": auth.get("auth_type", "web"),
            "conv_id": body.source_conversation_id,
        })
        feedback_id = result.fetchone()[0]
        return {"feedback_id": str(feedback_id), "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"反馈提交失败: {str(e)}")
