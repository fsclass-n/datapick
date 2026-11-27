"""ERP 자격증명 대칭 암호화 — SECRET_KEY 에서 유도한 Fernet 키 사용."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(f"erp-credentials:{settings.secret_key}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("저장된 자격증명을 복호화할 수 없습니다. SECRET_KEY 가 바뀌었는지 확인하세요.") from exc
