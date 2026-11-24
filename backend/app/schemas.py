from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str
    provider: str
    created_at: datetime
    last_login_at: datetime | None = None


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
    created_at: datetime
    finished_at: datetime | None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    source_type: str
    status: str
    parser: str | None
    parsed: dict | None
    error: str | None
    created_at: datetime
    parsed_at: datetime | None
    jobs: list[RpaJobOut] = []


class DocumentDetailOut(DocumentOut):
    raw_text: str | None


class RpaIn(BaseModel):
    target: Literal["excel", "erp"] = "excel"
