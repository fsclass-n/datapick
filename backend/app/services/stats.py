from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document, RpaJob, User


def _rate(ok: int, total: int) -> float:
    return round(ok / total * 100, 1) if total else 0.0


def _day(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone(timedelta(hours=9))).strftime("%m-%d")


def compute(db: Session, user_id: int | None = None, days: int = 14) -> dict:
    doc_query = select(Document)
    job_query = select(RpaJob).join(Document)
    if user_id is not None:
        doc_query = doc_query.where(Document.user_id == user_id)
        job_query = job_query.where(Document.user_id == user_id)
    docs = db.scalars(doc_query).all()
    jobs = db.scalars(job_query).all()

    doc_status = Counter(d.status for d in docs)
    job_status = Counter(j.status for j in jobs)
    parsed, failed = doc_status["parsed"], doc_status["failed"]
    rpa_ok, rpa_fail = job_status["success"], job_status["failed"]

    today = datetime.now(timezone(timedelta(hours=9))).date()
    labels = [(today - timedelta(days=i)).strftime("%m-%d") for i in range(days - 1, -1, -1)]
    daily = {label: {"date": label, "parsed": 0, "failed": 0, "rpa_success": 0, "rpa_failed": 0} for label in labels}
    for d in docs:
        bucket = daily.get(_day(d.created_at))
        if bucket and d.status in ("parsed", "failed"):
            bucket[d.status] += 1
    for j in jobs:
        bucket = daily.get(_day(j.created_at))
        if bucket and j.status in ("success", "failed"):
            bucket[f"rpa_{j.status}"] += 1

    amount_total = sum((d.parsed or {}).get("total_amount") or 0 for d in docs if d.status == "parsed")
    confidences = [(d.parsed or {}).get("confidence") for d in docs if d.status == "parsed"]
    confidences = [c for c in confidences if isinstance(c, (int, float))]

    result = {
        "documents": {
            "total": len(docs),
            "parsed": parsed,
            "failed": failed,
            "pending": doc_status["uploaded"],
            "success_rate": _rate(parsed, parsed + failed),
            "by_source": dict(Counter(d.source_type for d in docs)),
            "by_parser": dict(Counter(d.parser for d in docs if d.parser)),
            "amount_total": amount_total,
            "avg_confidence": round(sum(confidences) / len(confidences), 2) if confidences else None,
        },
        "rpa": {
            "total": len(jobs),
            "success": rpa_ok,
            "failed": rpa_fail,
            "success_rate": _rate(rpa_ok, rpa_ok + rpa_fail),
            "by_target": dict(Counter(j.target for j in jobs)),
        },
        "daily": list(daily.values()),
        "recent_failures": [
            {"id": d.id, "filename": d.filename, "error": d.error, "created_at": d.created_at.isoformat()}
            for d in sorted((d for d in docs if d.status == "failed"), key=lambda d: d.created_at, reverse=True)[:5]
        ],
    }
    if user_id is None:
        users = db.scalars(select(User)).all()
        result["users"] = {
            "total": len(users),
            "admins": sum(u.role == "admin" for u in users),
            "test_admins": sum(u.role == "test_admin" for u in users),
            "by_provider": dict(Counter(u.provider for u in users)),
        }
    return result
