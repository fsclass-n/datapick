from urllib.parse import parse_qs, urlparse

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
    assert client.post("/api/auth/login", json={"email": "user@dataquill.io", "password": "Wrong123!"}).status_code == 401


def test_oauth_unconfigured_redirects_to_login(client):
    assert client.get("/api/auth/providers").json() == {"google": False, "naver": False, "kakao": False}
    res = client.get("/api/auth/oauth/google/login", follow_redirects=False)
    assert res.status_code == 307
    assert "oauth_error" in parse_qs(urlparse(res.headers["location"]).query)


def test_oauth_callback_rejects_bad_state(client):
    res = client.get("/api/auth/oauth/kakao/callback?code=abc&state=forged", follow_redirects=False)
    assert "oauth_error" in res.headers["location"]


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
    assert client.get("/api/admin/users?role=admin", headers=admin_headers).json()[-1]["email"] == "new@example.com"

    me = next(u for u in users if u["email"] == "admin@dataquill.io")
    res = client.patch(f"/api/admin/users/{me['id']}/role", headers=admin_headers, json={"role": "user"})
    assert res.status_code == 400

    stats = client.get("/api/admin/stats", headers=admin_headers).json()
    assert stats["users"]["total"] >= 3
    assert 0 < stats["documents"]["success_rate"] < 100
    assert stats["rpa"]["success"] >= 1


def test_erp_demo_voucher(client):
    assert "전표 입력" in client.get("/erp-demo").text
    res = client.post("/erp-demo/api/vouchers", json={"vendor": "A", "date": "2026-11-17", "total_amount": 1000})
    assert res.json()["voucher_no"].startswith("JV-")
