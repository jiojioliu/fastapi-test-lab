from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import database
from .security import TokenError, decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: int
    username: str
    display_name: str
    role: str
    created_at: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def can_use_lab(self) -> bool:
        return self.role == "admin"

    @property
    def can_create_orders(self) -> bool:
        return self.role in {"customer", "admin"}


def _unauthorized(detail: str = "Authentication is required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    token = credentials.credentials if credentials else request.cookies.get(
        "lab_access_token"
    )
    if not token:
        raise _unauthorized()
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise _unauthorized(str(exc)) from exc
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise _unauthorized("Invalid token subject")
    row = database.get_user_by_id(user_id)
    if row is None:
        raise _unauthorized("This account no longer exists")
    return CurrentUser(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        role=row["role"],
        created_at=row["created_at"],
    )


async def require_admin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role is required",
        )
    return user


async def require_test_access(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not user.can_use_lab:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The administrator account is required for lab endpoints",
        )
    return user


async def require_order_user(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not user.can_create_orders:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest accounts have read-only access",
        )
    return user

