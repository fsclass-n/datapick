from urllib.parse import parse_qs, urlparse

import time

import pytest

from backend.app.security import is_valid_password

RECEIPT = """스타벅스 강남R점
사업자번호: 123-45-67890
2026.11.17 14:32
아메리카노 2 4,500 9,000
카페라떼 1 5,000 5,000
부가세: 1,273
합계: 14,000원
결제수단: 신용카드
"""


@pytest.mark.parametrize(
    "password, ok",
    [("Abcdef1!", True), ("abcdef1!", False), ("ABCDEF1!", False), ("Abcdefg!", False), ("Abcdefg1", False), ("Ab1!", False)],
)
def test_password_rule(password, ok):
    assert is_valid_password(password) is ok


def test_register_rejects_weak_password(client):
    res = client.post("/api/auth/register", json={"email": "weak@example.com", "name": "약함", "password": "password1"})
    assert res.status_code == 422


def test_register_and_me(client):
    res = client.post("/api/auth/register", json={"email": "New@Example.com", "name": "신규", "password": "Strong1!x"})
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == "new@example.com" and me["role"] == "user"
    assert client.post("/api/auth/register", json={"email": "new@example.com", "name": "x", "password": "Strong1!x"}).status_code == 409


def test_login_failure(client):
    assert client.post("/api/auth/login", json={"email": "user@datapick.io", "password": "Wrong123!"}).status_code == 401


def test_oauth_unconfigured_redirects_to_login(client):
    assert client.get("/api/auth/providers").json() == {"google": False, "naver": False, "kakao": False, "admin_login": True}
    res = client.get("/api/auth/oauth/google/start", follow_redirects=False)
    assert res.status_code == 307
    assert "oauth_error" in parse_qs(urlparse(res.headers["location"]).query)


def test_oauth_callback_rejects_bad_state(client):
    """쿠키가 있는데 state 가 다르면 거부, 쿠키가 없으면 프런트 sessionStorage 검증으로 넘긴다."""
    res = client.get("/api/auth/oauth/kakao/callback?code=abc&state=forged", headers={"Cookie": "dq_oauth_state=other"}, follow_redirects=False)
    assert "oauth_error" in res.headers["location"]
    res = client.get("/api/auth/oauth/kakao/callback?code=abc&state=forged", follow_redirects=False)
    loc = res.headers["location"]
    assert "/oauth/callback?" in loc and "provider=kakao" in loc and "state=forged" in loc


def test_oauth_exchange_rejects_forged_state(client):
    """서버가 발급하지 않은 state 로는 토큰 교환을 할 수 없다."""
    res = client.post("/api/auth/oauth/kakao/exchange", json={"code": "abc", "state": "forged"})
    assert res.status_code == 401


def test_upload_parse_and_excel_rpa(client, user_headers):
    res = client.post(
        "/api/documents/upload",
        headers=user_headers,
        files={"file": ("receipt.txt", RECEIPT.encode(), "text/plain")},
    )
    assert res.status_code == 201, res.text
    doc = res.json()
    assert doc["status"] == "parsed" and doc["parser"] == "rules"
    parsed = doc["parsed"]
    assert parsed["date"] == "2026-11-17"
    assert parsed["total_amount"] == 14000
    assert parsed["vat"] == 1273
    assert parsed["business_number"] == "123-45-67890"
    assert len(parsed["items"]) == 2

    job = client.post(f"/api/documents/{doc['id']}/rpa", headers=user_headers, json={"target": "excel"}).json()
    assert job["status"] == "success", job
    ledger = client.get("/api/documents/ledger.xlsx", headers=user_headers)
    assert ledger.status_code == 200 and ledger.content[:2] == b"PK"


def test_email_text_document_and_edit(client, user_headers):
    body = "From: billing@vendor.co.kr\nSubject: 11월 클라우드 사용료 청구\n\n청구금액: 330,000원\n부가세: 30,000\n청구일 2026-11-01"
    doc = client.post("/api/documents/text", headers=user_headers, json={"title": "청구 메일", "text": body}).json()
    assert doc["status"] == "parsed", doc
    assert doc["parsed"]["document_type"] == "email"
    assert doc["parsed"]["total_amount"] == 330000

    edited = client.patch(f"/api/documents/{doc['id']}", headers=user_headers, json={"vendor": "벤더클라우드"}).json()
    assert edited["parsed"]["vendor"] == "벤더클라우드"


def test_unparseable_document_marked_failed(client, user_headers):
    doc = client.post("/api/documents/text", headers=user_headers, json={"text": "안녕하세요 회의 일정 공유드립니다"}).json()
    assert doc["status"] == "failed" and doc["error"]
    res = client.post(f"/api/documents/{doc['id']}/rpa", headers=user_headers, json={"target": "excel"})
    assert res.status_code == 409


def test_unsupported_upload(client, user_headers):
    res = client.post("/api/documents/upload", headers=user_headers, files={"file": ("a.exe", b"MZ", "application/octet-stream")})
    assert res.status_code == 415


def test_dashboard_scoped_to_user(client, user_headers):
    data = client.get("/api/dashboard", headers=user_headers).json()
    assert data["documents"]["parsed"] >= 2 and data["documents"]["failed"] >= 1
    assert "users" not in data
    assert len(data["daily"]) == 14


def test_admin_requires_admin(client, user_headers):
    assert client.get("/api/admin/users", headers=user_headers).status_code == 403
    assert client.get("/api/admin/users").status_code == 401


def test_admin_user_management_and_stats(client, admin_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    target = next(u for u in users if u["email"] == "new@example.com")
    res = client.patch(f"/api/admin/users/{target['id']}/role", headers=admin_headers, json={"role": "admin"})
    assert res.json()["role"] == "admin"
    admins = {u["email"] for u in client.get("/api/admin/users?role=admin", headers=admin_headers).json()}
    assert admins == {"new@example.com", "operator@datapick.io"}

    me = next(u for u in users if u["email"] == "operator@datapick.io")
    res = client.patch(f"/api/admin/users/{me['id']}/role", headers=admin_headers, json={"role": "user"})
    assert res.status_code == 400

    stats = client.get("/api/admin/stats", headers=admin_headers).json()
    assert stats["users"]["total"] >= 3
    assert 0 < stats["documents"]["success_rate"] < 100
    assert stats["rpa"]["success"] >= 1


def test_erp_demo_voucher(client):
    page = client.get("/erp-demo").text
    assert "전표 입력" in page and "전표 목록" in page
    res = client.post("/erp-demo/api/vouchers", json={"vendor": "A", "date": "2026-11-17", "total_amount": 1000})
    assert res.json()["voucher_no"].startswith("JV-")


class _FakeModels:
    def __init__(self, failures, code=503):
        self.failures, self.code, self.calls = failures, code, 0

    def generate_content(self, **_):
        from google.genai import errors

        self.calls += 1
        if self.calls <= self.failures:
            raise errors.APIError(self.code, {"error": {"code": self.code, "message": "high demand", "status": "UNAVAILABLE"}})
        return type("R", (), {"text": '{"document_type": "receipt", "vendor": "A", "total_amount": 1000}'})()


@pytest.mark.parametrize("failures, code, ok, calls", [(2, 503, True, 3), (9, 503, False, 4), (1, 400, False, 1)])
def test_gemini_retries_transient_errors(monkeypatch, failures, code, ok, calls):
    from google import genai

    from backend.app.services import parser

    fake = _FakeModels(failures, code)
    monkeypatch.setattr(genai, "Client", lambda **_: type("C", (), {"models": fake})())
    monkeypatch.setattr(parser, "RETRY_DELAYS", (0, 0, 0))
    monkeypatch.setattr(parser.settings, "gemini_api_key", "test")
    monkeypatch.setattr(parser.settings, "gemini_fallback_model", "")
    if ok:
        assert parser.parse_with_gemini("text")["total_amount"] == 1000
    else:
        with pytest.raises(parser.ParseError):
            parser.parse_with_gemini("text")
    assert fake.calls == calls


def test_gemini_fails_over_to_fallback_model(monkeypatch):
    """주 모델이 계속 실패하면 대체 모델로 호출한다."""
    from google import genai
    from google.genai import errors

    from backend.app.services import parser

    class Fake:
        def __init__(self):
            self.seen = []

        def generate_content(self, model=None, **_):
            self.seen.append(model)
            if model == "primary-model":
                raise errors.APIError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})
            return type("R", (), {"text": '{"document_type": "receipt", "vendor": "A", "total_amount": 1000}'})()

    fake = Fake()
    monkeypatch.setattr(genai, "Client", lambda **_: type("C", (), {"models": fake})())
    monkeypatch.setattr(parser, "RETRY_DELAYS", (0, 0, 0))
    monkeypatch.setattr(parser.settings, "gemini_api_key", "test")
    monkeypatch.setattr(parser.settings, "gemini_model", "primary-model")
    monkeypatch.setattr(parser.settings, "gemini_fallback_model", "backup-model")
    assert parser.parse_with_gemini("text")["total_amount"] == 1000
    assert fake.seen == ["primary-model"] * 4 + ["backup-model"]


def test_parse_falls_back_to_rules_when_gemini_fails(monkeypatch):
    """Gemini 두 모델이 모두 실패해도 규칙 파서 결과를 반환한다."""
    from backend.app.services import parser

    def boom(*_a, **_kw):
        raise parser.ParseError("Gemini 호출 실패 (503)")

    monkeypatch.setattr(parser, "generate_structured", boom)
    monkeypatch.setattr(parser.settings, "gemini_api_key", "test")
    text = "브런치카페\n2026-11-17\n합계 10,000원"
    parsed, engine = parser.parse(text)
    assert engine == "rules" and parsed["total_amount"] == 10000


def test_withdraw_blocks_public_test_account(client, user_headers):
    res = client.request("DELETE", "/api/auth/me", headers=user_headers, json={})
    assert res.status_code == 403


def test_withdraw_deletes_account_and_data(client):
    email = f"withdraw-{time.time_ns()}@example.com"
    headers = {"Authorization": f"Bearer {client.post('/api/auth/register', json={'name': '탈퇴', 'email': email, 'password': 'Withdraw123!'}).json()['access_token']}"}
    client.post("/api/documents/upload", headers=headers, files={"file": ("memo.txt", b"hello", "text/plain")})
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    # 비밀번호가 틀리면 탈퇴되지 않는다
    assert client.request("DELETE", "/api/auth/me", headers=headers, json={"password": "Wrong123!"}).status_code == 401
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    # 올바른 비밀번호로 탈퇴하면 계정이 사라진다
    assert client.request("DELETE", "/api/auth/me", headers=headers, json={"password": "Withdraw123!"}).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_admin_login_issues_full_admin(client, admin_headers):
    me = client.get("/api/auth/me", headers=admin_headers).json()
    assert me["role"] == "admin" and me["provider"] == "admin"


def test_admin_credentials_also_work_on_normal_login(client):
    res = client.post("/api/auth/login", json={"email": "operator@datapick.io", "password": "test-admin-pw-0123!"})
    assert res.status_code == 200 and res.json()["user"]["role"] == "admin"


def test_admin_login_rejects_wrong_credentials_and_rate_limits(client):
    from backend.app.routers import auth

    auth.ADMIN_LOGIN_FAILURES.clear()
    for body in ({"email": "operator@datapick.io", "password": "wrong"},
                 {"email": "nobody@datapick.io", "password": "test-admin-pw-0123!"},
                 {"email": "operator@datapick.io", "password": "wrong"},
                 {"email": "operator@datapick.io", "password": "wrong"},
                 {"email": "operator@datapick.io", "password": "wrong"}):
        assert client.post("/api/auth/admin-login", json=body).status_code == 401
    res = client.post("/api/auth/admin-login", json={"email": "operator@datapick.io", "password": "test-admin-pw-0123!"})
    assert res.status_code == 429
    auth.ADMIN_LOGIN_FAILURES.clear()


def test_admin_login_disabled_when_not_configured(client, monkeypatch):
    from backend.app.config import settings

    monkeypatch.setattr(settings, "admin_password", "")
    assert client.post("/api/auth/admin-login", json={"email": "a@b.co", "password": "x"}).status_code == 503


def test_seeded_test_admin_is_read_only_role(client, test_admin_headers):
    me = client.get("/api/auth/me", headers=test_admin_headers).json()
    assert me["role"] == "test_admin"


def test_test_admin_can_view_admin_pages(client, test_admin_headers):
    assert client.get("/api/admin/users", headers=test_admin_headers).status_code == 200
    assert client.get("/api/admin/stats", headers=test_admin_headers).status_code == 200
    assert client.get("/api/documents", headers=test_admin_headers).status_code == 200


def test_test_admin_writes_are_blocked(client, test_admin_headers, admin_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    target = next(u for u in users if u["email"] == "user@datapick.io")
    blocked = [
        client.patch(f"/api/admin/users/{target['id']}/role", headers=test_admin_headers, json={"role": "admin"}),
        client.post("/api/documents/text", headers=test_admin_headers, json={"text": "합계: 1,000원 2026-11-17"}),
        client.post("/api/documents/upload", headers=test_admin_headers, files={"file": ("a.txt", b"x", "text/plain")}),
        client.delete("/api/documents/1", headers=test_admin_headers),
        client.post("/api/documents/1/rpa", headers=test_admin_headers, json={"target": "excel"}),
    ]
    assert [r.status_code for r in blocked] == [403] * 5
    assert "읽기 전용" in blocked[0].json()["detail"]
    assert client.get("/api/admin/users", headers=admin_headers).json()[0]["role"] == "user"


def test_test_accounts_roles_cannot_be_changed(client, admin_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    for email in ("admin@datapick.io", "user@datapick.io"):
        target = next(u for u in users if u["email"] == email)
        res = client.patch(f"/api/admin/users/{target['id']}/role", headers=admin_headers, json={"role": "admin"})
        assert res.status_code == 400, email


def test_seed_restores_test_account_roles(client):
    from sqlalchemy import select

    from backend.app.database import SessionLocal
    from backend.app.main import seed_test_accounts
    from backend.app.models import User

    with SessionLocal() as db:
        db.scalar(select(User).where(User.email == "admin@datapick.io")).role = "admin"
        db.commit()
    seed_test_accounts()
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == "admin@datapick.io")).role == "test_admin"


def test_admin_expel_user(client, admin_headers):
    """운영 관리자는 일반 회원을 강퇴할 수 있고, 보호 규칙이 적용된다."""
    email = f"expel-{time.time_ns()}@example.com"
    reg = client.post("/api/auth/register", json={"name": "강퇴대상", "email": email, "password": "Expel123!"})
    target_id = reg.json()["id"] if "id" in reg.json() else None
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    if target_id is None:
        target_id = client.get("/api/auth/me", headers=headers).json()["id"]
    client.post("/api/documents/upload", headers=headers, files={"file": ("memo.txt", b"bye", "text/plain")})

    # 본인 · 테스트 계정 · 관리자 계정은 강퇴 불가
    me_id = client.get("/api/auth/me", headers=admin_headers).json()["id"]
    assert client.delete(f"/api/admin/users/{me_id}", headers=admin_headers).status_code == 400
    users = client.get("/api/admin/users", headers=admin_headers).json()
    test_user_id = next(u["id"] for u in users if u["email"] == "user@datapick.io")
    assert client.delete(f"/api/admin/users/{test_user_id}", headers=admin_headers).status_code == 400

    # 강퇴 성공 → 목록에서 사라지고 대상 토큰도 무효
    res = client.delete(f"/api/admin/users/{target_id}", headers=admin_headers)
    assert res.status_code == 204, res.text
    assert all(u["id"] != target_id for u in client.get("/api/admin/users", headers=admin_headers).json())
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_admin_cannot_expel_admin_role(client, admin_headers):
    """관리자 권한 계정은 먼저 강등해야 강퇴할 수 있다."""
    email = f"expel-admin-{time.time_ns()}@example.com"
    reg = client.post("/api/auth/register", json={"name": "관리자후보", "email": email, "password": "Expel123!"})
    uid = client.get("/api/auth/me", headers={"Authorization": f"Bearer {reg.json()['access_token']}"}).json()["id"]
    assert client.patch(f"/api/admin/users/{uid}/role", headers=admin_headers, json={"role": "admin"}).status_code == 200
    assert client.delete(f"/api/admin/users/{uid}", headers=admin_headers).status_code == 400
    # 강등 후에는 강퇴 가능
    assert client.patch(f"/api/admin/users/{uid}/role", headers=admin_headers, json={"role": "user"}).status_code == 200
    assert client.delete(f"/api/admin/users/{uid}", headers=admin_headers).status_code == 204
