from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("provider", "provider_id", name="uq_provider_identity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    plan: Mapped[str] = mapped_column(String(20), default="free")
    provider: Mapped[str] = mapped_column(String(20), default="local")
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    documents: Mapped[list["Document"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    analyses: Mapped[list["Analysis"]] = relationship(cascade="all, delete-orphan")
    erp_connection: Mapped["ErpConnection | None"] = relationship(cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(20))
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parser: Mapped[str | None] = mapped_column(String(30), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped[User] = relationship(back_populates="documents")
    jobs: Mapped[list["RpaJob"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class RpaJob(Base):
    __tablename__ = "rpa_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    target: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[Document] = relationship(back_populates="jobs")


class Analysis(Base):
    """AI 도구(견적 비교 · 계약서 빨간펜 · 검진 추이) 실행 결과. 원본 파일은 저장하지 않는다."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(255))
    filenames: Mapped[list] = mapped_column(JSON, default=list)
    engine: Mapped[str] = mapped_column(String(20))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ErpConnection(Base):
    """고객사 ERP 연결 정보. 계정별로 자기 ERP 의 주소·로그인 자격증명을 저장한다.

    비밀번호는 Fernet(서버 SECRET_KEY 기반)으로 암호화해 저장하고 API 응답에는 내보내지 않는다.
    fields_json 을 비우면 플랫폼 공용 셀렉터 맵(ERP_CONFIG)을 사용한다.
    """

    __tablename__ = "erp_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), default="우리 회사 ERP")
    erp_url: Mapped[str] = mapped_column(String(500))
    login_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    username: Mapped[str] = mapped_column(String(255))
    password_enc: Mapped[str] = mapped_column(Text)
    fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
