import os
import sys
import tempfile
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp(prefix="datapick-test-"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{(_tmp / 'test.db').as_posix()}",
    STORAGE_DIR=str(_tmp / "uploads"),
    GEMINI_API_KEY="",
    SEED_TEST_ACCOUNTS="true",
    SECRET_KEY="test-secret",
    ADMIN_PASSWORD="test-admin-pw-0123!",
    ADMIN_EMAIL="operator@datapick.io",
    **{f"{p}_CLIENT_{k}": "" for p in ("GOOGLE", "NAVER", "KAKAO") for k in ("ID", "SECRET")},
)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="session")
def user_headers(client):
    return _login(client, "user@datapick.io", "User1234!")


@pytest.fixture(scope="session")
def admin_headers(client):
    res = client.post("/api/auth/admin-login", json={"email": "operator@datapick.io", "password": "test-admin-pw-0123!"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="session")
def test_admin_headers(client):
    return _login(client, "admin@datapick.io", "Admin1234!")
