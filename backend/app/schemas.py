from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

# DB(SQLite · TiDB)는 시간대 없는 UTC 시각을 돌려주므로, 응답에 UTC 표시를 붙여 브라우저가 현지 시각으로 바꾸게 한다
UtcDatetime = Annotated[datetime, AfterValidator(lambda v: v if v.tzinfo else v.replace(tzinfo=timezone.utc))]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str
    provider: str
    created_at: UtcDatetime
    last_login_at: UtcDatetime | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(LoginIn):
    name: str = Field(min_length=1, max_length=100)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RoleIn(BaseModel):
    role: Literal["user", "admin"]


class TextDocumentIn(BaseModel):
    title: str = Field(default="이메일 본문", max_length=255)
    text: str = Field(min_length=1)


class RpaJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    target: str
    status: str
    message: str | None
    created_at: UtcDatetime
    finished_at: UtcDatetime | None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    source_type: str
    status: str
    parser: str | None
    parsed: dict | None
    error: str | None
    created_at: UtcDatetime
    parsed_at: UtcDatetime | None
    jobs: list[RpaJobOut] = []


class DocumentDetailOut(DocumentOut):
    raw_text: str | None


class RpaIn(BaseModel):
    target: Literal["excel", "erp"] = "excel"


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    filenames: list[str]
    engine: str
    created_at: UtcDatetime


class AnalysisDetailOut(AnalysisOut):
    result: dict
