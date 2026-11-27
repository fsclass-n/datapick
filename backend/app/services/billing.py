"""요금제 · 사용량 정산(결제 게이트웨이 연동 전 인앱 구독 스텁)."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Document, User

PLANS = {
    "free": {"label": "Free", "price": 0, "docs_per_month": 10, "erp_connection": False,
             "features": ["월 문서 10건", "AI 도구 3종", "엑셀 원장"]},
    "pro": {"label": "Pro", "price": 29000, "docs_per_month": 200, "erp_connection": True,
            "features": ["월 문서 200건", "내 ERP 연동", "AI 도구 3종", "엑셀 원장"]},
    "business": {"label": "Business", "price": 99000, "docs_per_month": 2000, "erp_connection": True,
                 "features": ["월 문서 2,000건", "내 ERP 연동", "우선 지원"]},
}
DEFAULT_PLAN = "free"


def plan_of(user: User) -> dict:
    return PLANS.get(user.plan or DEFAULT_PLAN, PLANS[DEFAULT_PLAN])


def monthly_usage(db: Session, user_id: int) -> int:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(
        select(func.count(Document.id)).where(Document.user_id == user_id, Document.created_at >= start)
    ) or 0


def usage_info(db: Session, user: User) -> dict:
    plan = plan_of(user)
    used = monthly_usage(db, user.id)
    limit = plan["docs_per_month"]
    return {
        "plan": user.plan or DEFAULT_PLAN,
        "plan_label": plan["label"],
        "price": plan["price"],
        "docs_used": used,
        "docs_limit": limit,
        "docs_remaining": max(limit - used, 0),
        "erp_connection": plan["erp_connection"],
    }


def check_quota(db: Session, user: User) -> None:
    info = usage_info(db, user)
    if info["docs_used"] >= info["docs_limit"]:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"이번 달 문서 처리 한도({info['docs_limit']}건)를 모두 사용했습니다. 상위 요금제로 업그레이드하세요.",
        )


def require_erp_connection_feature(user: User) -> None:
    if not plan_of(user)["erp_connection"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "고객사 ERP 연동은 Pro 이상 요금제에서 사용할 수 있습니다.",
        )
