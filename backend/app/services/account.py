"""계정 삭제 공통 처리 — 회원 탈퇴(본인)와 관리자 강퇴가 같은 정리 절차를 쓴다."""

from pathlib import Path

from sqlalchemy.orm import Session

from ..config import settings
from ..models import User


def delete_account(db: Session, user: User) -> None:
    """계정과 함께 문서 · RPA 작업 · AI 분석 · 업로드 파일 · 엑셀 원장을 삭제한다."""
    paths = [Path(d.storage_path) for d in user.documents if d.storage_path]
    ledger = settings.storage_dir.parent / "exports" / f"ledger_user_{user.id}.xlsx"
    db.delete(user)  # documents → rpa_jobs, analyses 는 관계 cascade 로 함께 삭제
    db.commit()
    for path in paths + [ledger]:
        path.unlink(missing_ok=True)
