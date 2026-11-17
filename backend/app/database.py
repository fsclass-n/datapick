from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import ROOT_DIR, settings


def _build_engine(url: str):
    parsed = make_url(url)
    connect_args = {}
    if parsed.get_backend_name() == "sqlite":
        connect_args["check_same_thread"] = False
        if parsed.database and parsed.database != ":memory:":
            db_path = (ROOT_DIR / parsed.database).resolve() if not parsed.database.startswith("/") else None
            if db_path:
                db_path.parent.mkdir(parents=True, exist_ok=True)
                parsed = parsed.set(database=str(db_path))
    elif settings.db_ssl:
        import certifi

        connect_args["ssl"] = {"ca": settings.db_ssl_ca or certifi.where()}
    return create_engine(parsed, connect_args=connect_args, pool_pre_ping=True)


engine = _build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
