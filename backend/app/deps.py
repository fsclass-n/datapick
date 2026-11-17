import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)
ADMIN_ROLES = {"admin", "test_admin"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
READ_ONLY_MESSAGE = "테스트 관리자 계정은 읽기 전용입니다. 데이터 생성·수정·삭제는 운영 관리자만 할 수 있습니다."


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인이 필요합니다.")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "인증 토큰이 유효하지 않습니다.")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "사용자를 찾을 수 없습니다.")
    # 테스트 관리자는 모든 인증 API 에서 조회만 허용 (단일 진입점에서 강제)
    if user.role == "test_admin" and request.method not in SAFE_METHODS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, READ_ONLY_MESSAGE)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """관리자 화면 접근: 운영 관리자(admin) + 테스트 관리자(test_admin, 조회만)."""
    if user.role not in ADMIN_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "관리자 권한이 필요합니다.")
    return user
