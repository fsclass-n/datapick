import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from rpa import erp, excel_writer, extract

from ..config import settings
from ..database import get_db
from ..deps import ADMIN_ROLES, get_current_user
from ..models import Document, ErpConnection, RpaJob, User, utcnow
from ..schemas import DocumentDetailOut, DocumentOut, RpaIn, RpaJobOut, TextDocumentIn
from ..services import billing, crypto, parser, stats

router = APIRouter(prefix="/api", tags=["documents"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _ledger_path(user_id: int) -> Path:
    return settings.storage_dir.parent / "exports" / f"ledger_user_{user_id}.xlsx"


def _get_document(db: Session, doc_id: int, user: User) -> Document:
    doc = db.get(Document, doc_id)
    if not doc or (doc.user_id != user.id and user.role not in ADMIN_ROLES):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "문서를 찾을 수 없습니다.")
    return doc


def _run_parse(doc: Document, data: bytes | None) -> None:
    try:
        file_bytes = mime_type = None
        if data is None:
            text = doc.raw_text or ""
        else:
            result = extract.extract(doc.filename, data)
            text = result.text
            if result.needs_vision:
                file_bytes, mime_type = data, result.mime_type
        doc.raw_text = text
        doc.parsed, doc.parser = parser.parse(text, file_bytes, mime_type)
        doc.status, doc.error = "parsed", None
    except (parser.ParseError, ValueError) as exc:
        doc.status, doc.error, doc.parsed = "failed", str(exc), None
    except Exception as exc:
        doc.status, doc.error, doc.parsed = "failed", f"문서 처리 중 오류: {exc}", None
    doc.parsed_at = utcnow()


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return stats.compute(db, user_id=user.id)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(status_filter: str = "", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Document).where(Document.user_id == user.id).order_by(Document.id.desc())
    if status_filter:
        query = query.where(Document.status == status_filter)
    return db.scalars(query).all()


@router.post("/documents/upload", response_model=DocumentDetailOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    billing.check_quota(db, user)
    filename = os.path.basename(file.filename or "upload")
    if Path(filename).suffix.lower() not in extract.SUPPORTED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "PDF, 이미지, EML, HTML, TXT 파일만 업로드할 수 있습니다.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "파일은 10MB 이하만 업로드할 수 있습니다.")

    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    stored = settings.storage_dir / f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
    stored.write_bytes(data)

    doc = Document(user_id=user.id, filename=filename, source_type=extract.source_type_of(filename), storage_path=str(stored))
    _run_parse(doc, data)
    db.add(doc)
    db.commit()
    return doc


@router.post("/documents/text", response_model=DocumentDetailOut, status_code=status.HTTP_201_CREATED)
def create_text_document(body: TextDocumentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    billing.check_quota(db, user)
    text = extract.html_to_text(body.text) if "<" in body.text and ">" in body.text else body.text
    doc = Document(user_id=user.id, filename=body.title, source_type="email", raw_text=text)
    _run_parse(doc, None)
    db.add(doc)
    db.commit()
    return doc


@router.get("/documents/ledger.xlsx")
def download_ledger(user: User = Depends(get_current_user)):
    path = _ledger_path(user.id)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "아직 엑셀에 적재된 데이터가 없습니다.")
    return FileResponse(path, filename="datapick_ledger.xlsx")


@router.get("/documents/{doc_id}", response_model=DocumentDetailOut)
def get_document(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_document(db, doc_id, user)


@router.patch("/documents/{doc_id}", response_model=DocumentDetailOut)
def update_parsed(doc_id: int, body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """사용자가 검수 화면에서 수정한 값을 반영한다."""
    doc = _get_document(db, doc_id, user)
    try:
        doc.parsed = parser.ParsedDocument.model_validate({**(doc.parsed or {}), **body}).model_dump()
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    doc.status, doc.error = "parsed", None
    db.commit()
    return doc


@router.post("/documents/{doc_id}/reparse", response_model=DocumentDetailOut)
def reparse(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = _get_document(db, doc_id, user)
    data = Path(doc.storage_path).read_bytes() if doc.storage_path and Path(doc.storage_path).exists() else None
    _run_parse(doc, data)
    db.commit()
    return doc


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = _get_document(db, doc_id, user)
    if doc.storage_path:
        Path(doc.storage_path).unlink(missing_ok=True)
    db.delete(doc)
    db.commit()


@router.post("/documents/{doc_id}/rpa", response_model=RpaJobOut)
def run_rpa(doc_id: int, body: RpaIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = _get_document(db, doc_id, user)
    if doc.status != "parsed" or not doc.parsed:
        raise HTTPException(status.HTTP_409_CONFLICT, "파싱이 완료된 문서만 RPA 입력을 실행할 수 있습니다.")

    job = RpaJob(document_id=doc.id, target=body.target, created_at=utcnow())
    try:
        if body.target == "excel":
            rows = excel_writer.append_rows(_ledger_path(doc.user_id), [excel_writer.to_row(doc.id, doc.parsed)])
            job.message = f"엑셀 원장에 적재했습니다. (총 {rows}행)"
        else:
            # 문서 소유자가 고객사 ERP 연결을 저장해 두면 그 계정으로 입력한다.
            # 없으면 ERP_ADAPTER/ERP_CONFIG 로 정한 플랫폼 기본 대상(데모 ERP)을 쓴다.
            conn = db.scalar(select(ErpConnection).where(ErpConnection.user_id == doc.user_id))
            config = None
            if conn:
                config = erp.config_for_connection(
                    url=conn.erp_url, login_url=conn.login_url, username=conn.username,
                    password=crypto.decrypt(conn.password_enc), fields=conn.fields_json,
                )
            voucher = erp.submit_record(doc.parsed, config=config)
            job.message = f"ERP 입력 완료 ({voucher})"
        job.status = "success"
    except Exception as exc:
        job.status, job.message = "failed", str(exc)
    job.finished_at = utcnow()
    db.add(job)
    db.commit()
    return job
