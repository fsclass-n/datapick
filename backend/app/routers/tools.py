"""AI 도구 3종 API. 업로드 원본은 저장하지 않고 분석 결과(JSON)만 사용자별로 보관한다."""

import os
from functools import partial
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from rpa import extract

from ..database import get_db
from ..deps import get_current_user
from ..models import Analysis, User
from ..schemas import AnalysisDetailOut, AnalysisOut
from ..services import analyzers
from ..services.parser import ParseError

router = APIRouter(prefix="/api/tools", tags=["tools"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_FILES = 5
KINDS = {"quote", "contract", "health"}


async def _read_files(files: list[UploadFile], minimum: int, maximum: int = MAX_FILES) -> list[tuple[str, bytes]]:
    if not minimum <= len(files) <= maximum:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"파일은 {minimum}~{maximum}개를 올려 주세요.")
    result = []
    for file in files:
        name = os.path.basename(file.filename or "upload")
        if Path(name).suffix.lower() not in extract.SUPPORTED_TYPES:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"'{name}': PDF, 이미지, EML, HTML, TXT 파일만 올릴 수 있습니다.")
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"'{name}': 파일은 10MB 이하만 올릴 수 있습니다.")
        result.append((name, data))
    return result


def _save(db: Session, user: User, kind: str, title: str, filenames: list[str], run) -> Analysis:
    try:
        result, engine = run()
    except (ParseError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    analysis = Analysis(user_id=user.id, kind=kind, title=title(result)[:255], filenames=filenames, engine=engine, result=result)
    db.add(analysis)
    db.commit()
    return analysis


@router.post("/quote-compare", response_model=AnalysisDetailOut, status_code=status.HTTP_201_CREATED)
async def quote_compare(files: list[UploadFile] = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = await _read_files(files, minimum=2)
    return _save(db, user, "quote", lambda r: "견적 비교 · " + " vs ".join(r["comparison"]["vendors"]),
                 [n for n, _ in data], partial(analyzers.analyze_quotes, data))


@router.post("/contract-review", response_model=AnalysisDetailOut, status_code=status.HTTP_201_CREATED)
async def contract_review(
    file: UploadFile | None = File(None),
    text: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file is not None:
        (name, data), = await _read_files([file], minimum=1, maximum=1)
        run = partial(analyzers.analyze_contract, name, data)
    elif text.strip():
        name = "붙여넣은 계약서"
        run = partial(analyzers.analyze_contract, name, text=text)
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "계약서 파일을 올리거나 본문을 붙여 넣어 주세요.")
    return _save(db, user, "contract", lambda r: "계약서 검토 · " + (r["review"].get("title") or name), [name], run)


@router.post("/health-trend", response_model=AnalysisDetailOut, status_code=status.HTTP_201_CREATED)
async def health_trend(files: list[UploadFile] = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = await _read_files(files, minimum=1)

    def title(result: dict) -> str:
        dates = [d for d in result["trend"]["dates"] if d]
        return "건강검진 추이 · " + (" → ".join(dates) if dates else f"{len(data)}회")

    return _save(db, user, "health", title, [n for n, _ in data], partial(analyzers.analyze_health, data))


def _get(db: Session, analysis_id: int, user: User) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    if not analysis or analysis.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "분석 결과를 찾을 수 없습니다.")
    return analysis


@router.get("/analyses", response_model=list[AnalysisOut])
def list_analyses(kind: str = "", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Analysis).where(Analysis.user_id == user.id).order_by(Analysis.id.desc())
    if kind in KINDS:
        query = query.where(Analysis.kind == kind)
    return db.scalars(query.limit(50)).all()


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetailOut)
def get_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get(db, analysis_id, user)


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_get(db, analysis_id, user))
    db.commit()
