import secrets
import time
from collections import defaultdict, deque
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
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
OAUTH_STATE_TTL_SECONDS = 600
OAUTH_STATES: dict[str, float] = {}  # 서버가 발급한 state → 발급 시각 (쿠키 없는 시작 경로의 exchange 검증용)
ADMIN_LOGIN_MAX_FAILURES = 5
ADMIN_LOGIN_WINDOW_SECONDS = 600
ADMIN_LOGIN_FAILURES: dict[str, deque] = defaultdict(deque)


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


def _recent_failures(client_ip: str) -> deque:
    failures = ADMIN_LOGIN_FAILURES[client_ip]
    while failures and failures[0] < time.monotonic() - ADMIN_LOGIN_WINDOW_SECONDS:
        failures.popleft()
    return failures


@router.post("/admin-login", response_model=TokenOut)
def admin_login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    """운영 관리자 로그인: 서버 환경 변수 ADMIN_EMAIL · ADMIN_PASSWORD 와 일치해야 전체 CRUD 권한을 받는다."""
    if not settings.admin_password:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "운영 관리자 로그인이 설정되지 않았습니다. (ADMIN_EMAIL · ADMIN_PASSWORD)",
        )
    client_ip = request.client.host if request.client else "unknown"
    failures = _recent_failures(client_ip)
    if len(failures) >= ADMIN_LOGIN_MAX_FAILURES:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "인증 실패가 많아 잠시 차단되었습니다. 10분 후 다시 시도해 주세요.")
    email_ok = secrets.compare_digest(body.email.lower().encode(), settings.admin_email.encode())
    password_ok = secrets.compare_digest(body.password.encode(), settings.admin_password.encode())
    if not (email_ok and password_ok):
        failures.append(time.monotonic())
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.")
    failures.clear()

    user = db.scalar(select(User).where(User.email == settings.admin_email))
    if not user:
        user = User(email=settings.admin_email, name="운영 관리자", provider="admin")
        db.add(user)
    user.role = "admin"
    # 같은 이메일·비밀번호로 일반 로그인도 되도록 환경 변수 비밀번호를 계정에 반영한다
    user.password_hash = hash_password(settings.admin_password)
    db.flush()
    return issue_token(db, user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/providers")
def providers():
    return {**{name: oauth.is_configured(name) for name in oauth.PROVIDERS}, "admin_login": bool(settings.admin_password)}


def _frontend_error(message: str) -> RedirectResponse:
    response = RedirectResponse(f"{settings.frontend_url}/login?{urlencode({'oauth_error': message})}")
    response.delete_cookie(STATE_COOKIE)
    return response


@router.get("/oauth/{provider}/start")
def oauth_login(provider: str, format: str | None = None):
    if provider not in oauth.PROVIDERS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "지원하지 않는 로그인 방식입니다.")
    if not oauth.is_configured(provider):
        return _frontend_error(f"{provider} 로그인이 아직 설정되지 않았습니다. 관리자에게 문의하세요.")
    state = secrets.token_urlsafe(24)
    now = time.time()
    for issued_state, issued_at in [item for item in OAUTH_STATES.items() if now - item[1] > OAUTH_STATE_TTL_SECONDS]:
        del OAUTH_STATES[issued_state]
    OAUTH_STATES[state] = now
    url = oauth.authorize_url(provider, state)
    response = JSONResponse({"url": url, "state": state}) if format == "json" else RedirectResponse(url)
    response.set_cookie(
        STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.backend_url.startswith("https"),
    )
    return response


def _oauth_token_for_profile(db: Session, provider: str, profile: oauth.OAuthProfile) -> tuple[str | None, str | None]:
    """소셜 프로필로 사용자를 찾거나 만들고 (토큰, 오류 메시지)를 반환한다."""
    user = db.scalar(select(User).where(User.provider == provider, User.provider_id == profile.provider_id))
    if not user:
        if db.scalar(select(User).where(User.email == profile.email.lower())):
            return None, "이미 다른 로그인 방식으로 가입된 이메일입니다."
        user = User(email=profile.email.lower(), name=profile.name, provider=provider, provider_id=profile.provider_id)
        db.add(user)
        db.flush()
    return issue_token(db, user).access_token, None


class OAuthExchangeIn(BaseModel):
    code: str
    state: str


@router.post("/oauth/{provider}/exchange")
def oauth_exchange(provider: str, body: OAuthExchangeIn, db: Session = Depends(get_db)):
    """쿠키 없이 시작한 OAuth 흐름의 마무리. state 는 서버 발급 레지스트리로 검증한다(1회용)."""
    if provider not in oauth.PROVIDERS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "지원하지 않는 로그인 방식입니다.")
    issued_at = OAUTH_STATES.pop(body.state, None)
    if not issued_at or time.time() - issued_at > OAUTH_STATE_TTL_SECONDS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인 요청이 만료되었거나 올바르지 않습니다. 다시 시도해 주세요.")
    try:
        profile = oauth.fetch_profile(provider, body.code, body.state)
    except oauth.OAuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    token, err = _oauth_token_for_profile(db, provider, profile)
    if err:
        raise HTTPException(status.HTTP_409_CONFLICT, err)
    return {"access_token": token}


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
    if not state:
        return _frontend_error("로그인 요청이 만료되었거나 올바르지 않습니다. 다시 시도해 주세요.")
    if expected is None:
        # 쿠키가 저장되지 않는 사이트 간 시작 경로: state 와의 바인딩은 프런트가 sessionStorage 로 검증하고
        # /exchange 에서 서버 발급 여부를 한 번 더 확인한다
        return RedirectResponse(f"{settings.frontend_url}/oauth/callback?{urlencode({'provider': provider, 'code': code, 'state': state})}")
    if not secrets.compare_digest(state, expected):
        return _frontend_error("로그인 요청이 만료되었거나 올바르지 않습니다. 다시 시도해 주세요.")

    try:
        profile = oauth.fetch_profile(provider, code, state)
    except oauth.OAuthError as exc:
        return _frontend_error(str(exc))

    token, err = _oauth_token_for_profile(db, provider, profile)
    if err:
        return _frontend_error(err)

    response = RedirectResponse(f"{settings.frontend_url}/oauth/callback#{urlencode({'token': token})}")
    response.delete_cookie(STATE_COOKIE)
    return response
