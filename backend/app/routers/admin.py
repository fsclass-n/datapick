from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import ADMIN_ROLES, require_admin
from ..models import Document, User
from ..schemas import RoleIn, UserOut
from ..services import stats
from ..test_accounts import TEST_ACCOUNT_EMAILS

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users")
def list_users(q: str = "", role: str = "", db: Session = Depends(get_db)):
    query = select(User, func.count(Document.id)).outerjoin(Document).group_by(User.id).order_by(User.id)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(or_(func.lower(User.email).like(like), func.lower(User.name).like(like)))
    if role in ("user", *ADMIN_ROLES):
        query = query.where(User.role == role)
    return [
        {**UserOut.model_validate(user).model_dump(mode="json"), "document_count": count}
        for user, count in db.execute(query).all()
    ]


@router.patch("/users/{user_id}/role", response_model=UserOut)
def change_role(user_id: int, body: RoleIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "사용자를 찾을 수 없습니다.")
    if user.id == admin.id and body.role != "admin":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "본인의 관리자 권한은 해제할 수 없습니다.")
    if user.email in TEST_ACCOUNT_EMAILS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "공개된 테스트 계정의 권한은 변경할 수 없습니다.")
    user.role = body.role
    db.commit()
    return user


@router.get("/stats")
def admin_stats(days: int = 14, db: Session = Depends(get_db)):
    return stats.compute(db, days=max(1, min(days, 90)))
