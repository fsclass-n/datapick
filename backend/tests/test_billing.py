"""요금제 · 사용량 한도 · 계정별 ERP 연결."""

from backend.app.services import crypto
from rpa import erp

DOC = {"title": "테스트 영수증", "text": "상호: 테스트상점\n합계: 1,000원\n2026-11-27"}


def _register(client, email):
    res = client.post("/api/auth/register", json={"email": email, "name": "테스터", "password": "Strong1!x"})
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_usage_default_free_and_subscribe(client):
    headers = _register(client, "plan@example.com")
    usage = client.get("/api/billing/usage", headers=headers).json()
    assert usage["plan"] == "free" and usage["docs_limit"] == 10

    plans = client.get("/api/billing/plans").json()["plans"]
    assert {p["id"] for p in plans} == {"free", "pro", "business"}

    res = client.post("/api/billing/subscribe", headers=headers, json={"plan": "pro"})
    assert res.json()["plan"] == "pro" and res.json()["docs_limit"] == 200
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["plan"] == "pro"

    res = client.post("/api/billing/cancel", headers=headers)
    assert res.json()["plan"] == "free"


def test_subscribe_rejects_unknown_plan(client):
    headers = _register(client, "badplan@example.com")
    assert client.post("/api/billing/subscribe", headers=headers, json={"plan": "gold"}).status_code == 400


def test_free_plan_monthly_quota(client):
    headers = _register(client, "quota@example.com")
    for _ in range(10):
        res = client.post("/api/documents/text", headers=headers, json=DOC)
        assert res.status_code == 201, res.text
    res = client.post("/api/documents/text", headers=headers, json=DOC)
    assert res.status_code == 402
    # 업그레이드하면 바로 다시 처리 가능
    client.post("/api/billing/subscribe", headers=headers, json={"plan": "pro"})
    assert client.post("/api/documents/text", headers=headers, json=DOC).status_code == 201


def test_erp_connection_requires_pro(client):
    headers = _register(client, "erpfree@example.com")
    body = {"erp_url": "https://erp.acme.co.kr/", "username": "acct01", "password": "erp-pw-1234"}
    assert client.put("/api/erp/connection", headers=headers, json=body).status_code == 403
    client.post("/api/billing/subscribe", headers=headers, json={"plan": "pro"})
    res = client.put("/api/erp/connection", headers=headers, json=body)
    assert res.status_code == 200, res.text
    saved = res.json()
    assert saved["erp_url"] == "https://erp.acme.co.kr" and saved["has_password"]
    assert "password" not in saved

    fetched = client.get("/api/erp/connection", headers=headers).json()
    assert fetched["username"] == "acct01"

    assert client.delete("/api/erp/connection", headers=headers).status_code == 204
    assert client.get("/api/erp/connection", headers=headers).json() is None


def test_rpa_uses_saved_erp_connection(client, monkeypatch):
    headers = _register(client, "rpaerp@example.com")
    client.post("/api/billing/subscribe", headers=headers, json={"plan": "pro"})
    client.put("/api/erp/connection", headers=headers, json={
        "erp_url": "https://erp.acme.co.kr/", "username": "acct01", "password": "erp-pw-1234",
    })
    doc = client.post("/api/documents/text", headers=headers, json=DOC).json()

    captured = {}

    def fake_submit(record, config=None):
        captured["config"] = config
        return "AC-TEST-0001"

    monkeypatch.setattr(erp, "submit_record", fake_submit)
    job = client.post(f"/api/documents/{doc['id']}/rpa", headers=headers, json={"target": "erp"})
    assert job.json()["status"] == "success" and "AC-TEST-0001" in job.json()["message"]
    cfg = captured["config"]
    assert cfg["url"] == "https://erp.acme.co.kr"
    assert cfg["login"]["username_value"] == "acct01"
    assert cfg["login"]["password_value"] == "erp-pw-1234"
    assert cfg["login"]["url"] == "https://erp.acme.co.kr/login"


def test_crypto_roundtrip_and_bad_key():
    token = crypto.encrypt("비밀비밀1234")
    assert token != "비밀비밀1234"
    assert crypto.decrypt(token) == "비밀비밀1234"
