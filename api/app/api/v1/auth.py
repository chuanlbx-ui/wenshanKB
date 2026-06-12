"""认证端点 — JWT 登录"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.config import get_settings

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


@router.post("/auth/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    result = await db.execute(
        text("SELECT id FROM users WHERE username = :un"), {"un": body.username}
    )
    if result.fetchone():
        raise HTTPException(status_code=409, detail="用户名已存在")

    hashed = pwd_context.hash(body.password)
    query = text("""
        INSERT INTO users (username, password_hash, display_name, role, status)
        VALUES (:un, :pw, :dn, 'user', 'active')
        RETURNING id
    """)
    result = await db.execute(query, {"un": body.username, "pw": hashed,
                                       "dn": body.display_name or body.username})
    user_id = result.fetchone()[0]
    return {"id": str(user_id), "username": body.username}


@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录，返回 JWT"""
    result = await db.execute(
        text("SELECT id, password_hash, role FROM users WHERE username = :un AND status = 'active'"),
        {"un": body.username},
    )
    row = result.fetchone()
    if not row or not pwd_context.verify(body.password, row[1]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(row[0]),
        "role": row[2],
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expire.isoformat(),
        "user": {"id": str(row[0]), "username": body.username, "role": row[2]},
    }
