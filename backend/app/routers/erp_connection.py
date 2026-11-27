"""계정별 고객사 ERP 연결 — 내 ERP 주소 · 로그인 자격증명 저장 · 연결 테스트."""

import re

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ErpConnection, User
from ..schemas import ErpConnectionOut
from ..services import billing, crypto

router = APIRouter(prefix="/api/erp/connection", tags=["erp-connection"])

URL_RE = re.compile(r"^https?://[^\s]+$")


class ConnectionIn(BaseModel):
    name: str = Field(default="우리 회사 ERP", max_length=100)
    erp_url: str = Field(min_length=8, max_length=500)
    login_url: str | None = Field(default=None, max_length=500)
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)
    fields: dict | None = None


def _get(db: Session, user: User) -> ErpConnection | None:
    return db.scalar(select(ErpConnection).where(ErpConnection.user_id == user.id))


def to_public(conn: ErpConnection) -> dict:
    return {
        "id": conn.id, "name": conn.name, "erp_url": conn.erp_url, "login_url": conn.login_url,
        "username": conn.username, "has_password": bool(conn.password_enc),
        "fields": conn.fields_json, "updated_at": conn.updated_at,
    }


@router.get("", response_model=ErpConnectionOut | None)
def get_connection(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conn = _get(db, user)
    return to_public(conn) if conn else None


@router.put("", response_model=ErpConnectionOut)
def save_connection(body: ConnectionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    billing.require_erp_connection_feature(user)
    for url in (body.erp_url, body.login_url):
        if url and not URL_RE.match(url):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "http(s):// 로 시작하는 주소를 입력하세요.")
    conn = _get(db, user) or ErpConnection(user_id=user.id)
    conn.name, conn.erp_url, conn.login_url = body.name, body.erp_url.rstrip("/"), (body.login_url or "").rstrip("/") or None
    conn.username, conn.password_enc, conn.fields_json = body.username, crypto.encrypt(body.password), body.fields
    db.add(conn)
    db.commit()
    return to_public(conn)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conn = _get(db, user)
    if conn:
        db.delete(conn)
        db.commit()


@router.post("/test")
def test_connection(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """저장된 자격증명으로 고객사 ERP 로그인 폼 인증을 시험한다(폼 로그인 방식 ERP 기준)."""
    conn = _get(db, user)
    if not conn:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "저장된 ERP 연결 정보가 없습니다.")
    login_url = conn.login_url or conn.erp_url.rstrip("/") + "/login"
    try:
        session = requests.Session()
        res = session.post(
            login_url,
            data={"login_id": conn.username, "login_pw": crypto.decrypt(conn.password_enc)},
            allow_redirects=True, timeout=10,
        )
    except requests.RequestException as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"ERP 서버에 연결할 수 없습니다: {exc}") from exc
    if session.cookies:
        return {"ok": True, "detail": f"로그인 성공 — 세션이 발급되었습니다 ({login_url})"}
    if res.status_code == 401:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "로그인 실패 — 아이디·비밀번호를 확인하세요.")
    raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"로그인 응답을 확인할 수 없습니다 (HTTP {res.status_code}).")
