"""API 依赖注入：认证 + 权限"""

from typing import Optional
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


# ── 角色权限等级 ──
ROLE_LEVEL = {
    "super_admin": 100,
    "editor": 70,
    "reviewer": 50,
    "member": 30,
    "user": 10,
}


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> dict:
    """统一认证：支持 JWT Bearer Token 和 X-API-Key 两种方式"""

    # 方式 1：Bearer JWT
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return {"auth_type": "user", "user_id": payload.get("sub"),
                    "role": payload.get("role", "user")}
        except JWTError:
            pass

    # 方式 2：X-API-Key（给 Agent 用）
    api_key = request.headers.get("X-API-Key", "")
    if api_key == settings.AGENT_API_KEY:
        return {"auth_type": "agent", "role": "agent"}

    raise HTTPException(status_code=401, detail="未认证：请提供有效的 Bearer Token 或 X-API-Key")


def require_role(min_role: str):
    """权限守卫工厂"""

    async def checker(auth: dict = Depends(get_current_user)) -> dict:
        role = auth.get("role", "user")
        if ROLE_LEVEL.get(role, 0) < ROLE_LEVEL.get(min_role, 0):
            raise HTTPException(status_code=403, detail=f"权限不足，需要 {min_role} 及以上角色")
        return auth

    return checker
