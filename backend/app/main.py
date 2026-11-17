from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import admin, auth, documents, erp_demo
from .security import hash_password

TEST_ACCOUNTS = [
    {"email": "user@dataquill.io", "name": "테스트 사용자", "password": "User1234!", "role": "user"},
    {"email": "admin@dataquill.io", "name": "테스트 관리자", "password": "Admin1234!", "role": "admin"},
]


def seed_test_accounts() -> None:
    with SessionLocal() as db:
        for account in TEST_ACCOUNTS:
            if not db.scalar(select(User).where(User.email == account["email"])):
                db.add(
                    User(
                        email=account["email"],
                        name=account["name"],
                        role=account["role"],
                        password_hash=hash_password(account["password"]),
                    )
                )
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    if settings.seed_test_accounts:
        seed_test_accounts()
    yield


app = FastAPI(title="dataquill API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for module in (auth, admin, documents, erp_demo):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.app_env, "parser": "gemini" if settings.gemini_api_key else "rules"}
