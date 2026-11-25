from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import admin, auth, documents, erp_demo, tools
from .security import hash_password, verify_password
from .test_accounts import TEST_ACCOUNT_EMAILS, TEST_ACCOUNTS


def seed_test_accounts() -> None:
    with SessionLocal() as db:
        for account in TEST_ACCOUNTS:
            user = db.scalar(select(User).where(User.email == account["email"]))
            if not user:
                db.add(
                    User(
                        email=account["email"],
                        name=account["name"],
                        role=account["role"],
                        password_hash=hash_password(account["password"]),
                    )
                )
            elif user.role != account["role"]:
                # 공개 계정이 승격된 채로 남지 않도록 기동 시마다 권한을 되돌린다
                user.role = account["role"]
        db.commit()


def seed_admin_account() -> None:
    """환경 변수 ADMIN_EMAIL · ADMIN_PASSWORD 로 운영 관리자 계정을 준비한다.

    같은 이메일·비밀번호로 일반 로그인 화면에서도 바로 접속할 수 있다.
    """
    if not settings.admin_password or settings.admin_email in TEST_ACCOUNT_EMAILS:
        return
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == settings.admin_email))
        if not user:
            user = User(email=settings.admin_email, name="운영 관리자", provider="admin")
            db.add(user)
        user.role = "admin"
        if not user.password_hash or not verify_password(settings.admin_password, user.password_hash):
            user.password_hash = hash_password(settings.admin_password)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    if settings.seed_test_accounts:
        seed_test_accounts()
    seed_admin_account()
    yield


app = FastAPI(title="datapick API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for module in (auth, admin, documents, erp_demo, tools):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.app_env, "parser": "gemini" if settings.gemini_api_key else "rules"}
