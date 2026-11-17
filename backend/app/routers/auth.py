import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User, utcnow
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import PASSWORD_RULE, create_token, hash_password, is_valid_password, verify_password
from ..services import oauth

router = APIRouter(prefix="/api/auth", tags=["auth"])
STATE_COOKIE = "dq_oauth_state"


def issue_token(db: Session, user: User) -> TokenOut:
    user.last_login_at = utcnow()
    db.commit()
    return TokenOut(access_token=create_token(user.id, role=user.role), user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if not is_valid_password(body.password):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, PASSWORD_RULE)
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 가입된 이메일입니다.")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    return issue_token(db, user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.")
    return issue_token(db, user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/providers")
def providers():
    return {name: oauth.is_configured(name) for name in oauth.PROVIDERS}


def _frontend_error(message: str) -> RedirectResponse:
    response = RedirectResponse(f"{settings.frontend_url}/login?{urlencode({'oauth_error': message})}")
    response.delete_cookie(STATE_COOKIE)
    return response


@router.get("/oauth/{provider}/login")
def oauth_login(provider: str):
    if provider not in oauth.PROVIDERS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "지원하지 않는 로그인 방식입니다.")
    if not oauth.is_configured(provider):
        return _frontend_error(f"{provider} 로그인이 아직 설정되지 않았습니다. 관리자에게 문의하세요.")
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(oauth.authorize_url(provider, state))
    response.set_cookie(
        STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.backend_url.startswith("https"),
    )
    return response


@router.get("/oauth/{provider}/callback")
def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if provider not in oauth.PROVIDERS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "지원하지 않는 로그인 방식입니다.")
    if error or not code:
        return _frontend_error("소셜 로그인이 취소되었습니다.")
    expected = request.cookies.get(STATE_COOKIE)
    if not state or not expected or not secrets.compare_digest(state, expected):
        return _frontend_error("로그인 요청이 만료되었거나 올바르지 않습니다. 다시 시도해 주세요.")

    try:
        profile = oauth.fetch_profile(provider, code, state)
    except oauth.OAuthError as exc:
        return _frontend_error(str(exc))

    user = db.scalar(select(User).where(User.provider == provider, User.provider_id == profile.provider_id))
    if not user:
        if db.scalar(select(User).where(User.email == profile.email.lower())):
            return _frontend_error("이미 다른 로그인 방식으로 가입된 이메일입니다.")
        user = User(email=profile.email.lower(), name=profile.name, provider=provider, provider_id=profile.provider_id)
        db.add(user)
        db.flush()

    token = issue_token(db, user).access_token
    response = RedirectResponse(f"{settings.frontend_url}/oauth/callback#{urlencode({'token': token})}")
    response.delete_cookie(STATE_COOKIE)
    return response
