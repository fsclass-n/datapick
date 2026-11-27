"""요금제 조회 · 사용량 · 인앱 구독(결제 게이트웨이 연동 전 스텁)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import UsageOut
from ..services import billing

router = APIRouter(prefix="/api/billing", tags=["billing"])


class SubscribeIn(BaseModel):
    plan: str


@router.get("/plans")
def list_plans():
    return {"plans": [{"id": key, **plan} for key, plan in billing.PLANS.items()]}


@router.get("/usage", response_model=UsageOut)
def usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return billing.usage_info(db, user)


@router.post("/subscribe", response_model=UsageOut)
def subscribe(body: SubscribeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # TODO: 결제 게이트웨이(토스페이먼츠 등) 승인 후에만 플랜을 바꾸도록 교체
    if body.plan not in billing.PLANS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "알 수 없는 요금제입니다.")
    user.plan = body.plan
    db.commit()
    return billing.usage_info(db, user)


@router.post("/cancel", response_model=UsageOut)
def cancel(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.plan = billing.DEFAULT_PLAN
    db.commit()
    return billing.usage_info(db, user)
