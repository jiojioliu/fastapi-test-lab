from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from .. import database
from ..config import TOKEN_TTL_SECONDS
from ..dependencies import CurrentUser, get_current_user
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..security import create_access_token, verify_password


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _token_response(user, response: Response | None = None) -> TokenResponse:
    token, ttl = create_access_token(user["id"], user["username"], user["role"])
    if response is not None:
        response.set_cookie(
            "lab_access_token",
            token,
            max_age=ttl,
            httponly=True,
            samesite="lax",
            secure=False,
        )
    return TokenResponse(
        access_token=token,
        expires_in=ttl,
        user=UserOut(
            id=user["id"],
            username=user["username"],
            display_name=user["display_name"],
            role=user["role"],
            created_at=user["created_at"],
        ),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with a JSON request",
)
async def login(payload: LoginRequest, response: Response) -> TokenResponse:
    user = database.get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(user, response)


@router.post(
    "/guest",
    response_model=TokenResponse,
    summary="Start a read-only guest session",
)
async def guest_session(response: Response) -> TokenResponse:
    user = database.get_user_by_username("guest")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Guest access is not configured",
        )
    return _token_response(user, response)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 form login for Swagger UI",
)
async def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    user = database.get_user_by_username(form.username)
    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(user)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a standard user account",
)
async def register(payload: RegisterRequest, response: Response) -> TokenResponse:
    try:
        user = database.create_user(
            payload.username, payload.password, payload.display_name
        )
    except database.OrderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _token_response(user, response)


@router.get("/me", response_model=UserOut, summary="Read the current account")
async def me(user: CurrentUser = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        created_at=user.created_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    response.delete_cookie("lab_access_token")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/config", summary="Inspect token configuration")
async def auth_config() -> dict[str, object]:
    return {
        "token_type": "Bearer",
        "algorithm": "HS256",
        "expires_in": TOKEN_TTL_SECONDS,
        "demo_accounts": {
            "customer": "customer / customer123",
            "admin": "admin / admin123 (administrator + test account)",
            "guest": "POST /api/auth/guest",
        },
    }

