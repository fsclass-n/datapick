from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples"


def _files(*names):
    return [("files", (name, (SAMPLES / name).read_bytes(), "text/plain")) for name in names]


def test_quote_compare_flags_outliers_missing_items_and_cheapest(client, user_headers):
    res = client.post("/api/tools/quote-compare", headers=user_headers, files=_files("quote_a.txt", "quote_b.txt", "quote_c.txt"))
    assert res.status_code == 201, res.text
    body = res.json()
    c = body["result"]["comparison"]
    assert body["kind"] == "quote" and body["engine"] == "rules"
    assert c["vendors"] == ["한빛인테리어", "다온디자인", "우리공간"]
    assert c["totals"] == [2330000, 1755000, 2469000] and c["cheapest"] == 1 and c["savings"] == 714000
    assert len(c["rows"]) == 5, "어순이 다른 '도장(문틀)'·'문틀 도장'은 같은 품목으로 묶여야 한다"
    floor = next(r for r in c["rows"] if r["name"] == "바닥 데코타일")
    assert floor["cells"][2]["flag"] == "outlier" and floor["cells"][2]["diff_pct"] == 36.7
    assert c["missing"] == {"다온디자인": ["철거 및 폐기물 처리"]}
    assert "빠져 있어" in c["insights"][1]


def test_quote_compare_needs_at_least_two_files(client, user_headers):
    res = client.post("/api/tools/quote-compare", headers=user_headers, files=_files("quote_a.txt"))
    assert res.status_code == 422


def test_contract_review_marks_risky_clauses_in_original_text(client, user_headers):
    text = (SAMPLES / "contract.txt").read_text(encoding="utf-8")
    res = client.post("/api/tools/contract-review", headers=user_headers, data={"text": text})
    assert res.status_code == 201, res.text
    result = res.json()["result"]
    review = result["review"]
    assert review["overall"] == "high" and review["counts"] == {"high": 3, "medium": 3, "low": 2}
    assert {c["category"] for c in review["clauses"] if c["risk"] == "high"} == {"auto_renewal", "penalty", "termination"}
    for clause in review["clauses"]:
        assert clause["start"] is not None, clause["quote"]
        assert result["text"][clause["start"]:clause["end"]].split() == clause["quote"].split()


def test_contract_review_requires_file_or_text(client, user_headers):
    assert client.post("/api/tools/contract-review", headers=user_headers, data={"text": " "}).status_code == 422


def test_health_trend_sorts_by_date_and_flags_changes(client, user_headers):
    res = client.post("/api/tools/health-trend", headers=user_headers, files=_files("health_2026.txt", "health_2025.txt"))
    assert res.status_code == 201, res.text
    trend = res.json()["result"]["trend"]
    assert trend["dates"] == ["2025-11-12", "2026-11-18"]
    rows = {r["code"]: r for r in trend["rows"]}
    assert rows["fasting_glucose"]["statuses"] == ["normal", "caution"] and rows["fasting_glucose"]["flag"] == "worsened"
    assert rows["systolic_bp"]["values"] == [126, 138] and rows["systolic_bp"]["flag"] == "watch"
    assert rows["hdl"]["flag"] == "improved"
    assert rows["weight"]["statuses"] == [None, None]
    assert "진단이 아닙니다" in trend["disclaimer"]


@pytest.mark.parametrize("code, value, expected", [
    ("fasting_glucose", 99, "normal"), ("fasting_glucose", 100, "caution"), ("fasting_glucose", 126, "risk"),
    ("hdl", 40, "normal"), ("hdl", 39, "risk"), ("bmi", 18, "caution"), ("bmi", 22.9, "normal"), ("bmi", 25, "risk"),
    ("weight", 70, None),
])
def test_health_judgement_boundaries(code, value, expected):
    from backend.app.services.analyzers import judge

    assert judge(code, value) == expected


def test_analyses_are_private_and_deletable(client, user_headers, test_admin_headers):
    created = client.post("/api/tools/health-trend", headers=user_headers, files=_files("health_2025.txt")).json()
    listed = client.get("/api/tools/analyses?kind=health", headers=user_headers).json()
    assert created["id"] in [a["id"] for a in listed] and all(a["kind"] == "health" for a in listed)
    assert "result" not in listed[0]
    assert client.get(f"/api/tools/analyses/{created['id']}", headers=test_admin_headers).status_code == 404
    assert client.delete(f"/api/tools/analyses/{created['id']}", headers=user_headers).status_code == 204
    assert client.get(f"/api/tools/analyses/{created['id']}", headers=user_headers).status_code == 404


def test_tools_reject_test_admin_writes_and_bad_files(client, user_headers, test_admin_headers):
    assert client.post("/api/tools/quote-compare", headers=test_admin_headers, files=_files("quote_a.txt", "quote_b.txt")).status_code == 403
    bad = [("files", ("a.exe", b"MZ", "application/octet-stream")), ("files", ("b.exe", b"MZ", "application/octet-stream"))]
    assert client.post("/api/tools/quote-compare", headers=user_headers, files=bad).status_code == 415
    unreadable = [("files", ("a.txt", "안녕하세요".encode(), "text/plain")), ("files", ("b.txt", "반갑습니다".encode(), "text/plain"))]
    res = client.post("/api/tools/quote-compare", headers=user_headers, files=unreadable)
    assert res.status_code == 422 and "a.txt" in res.json()["detail"]


def test_quote_compare_uses_gemini_extraction_when_configured(client, user_headers, monkeypatch):
    from backend.app.services import analyzers

    def fake(prompt, schema, text, *_):
        vendor = "가" if "A" in text else "나"
        price = 1000 if vendor == "가" else 1500
        return schema(vendor=vendor, items=[{"name": "볼펜", "quantity": 10, "unit_price": price, "amount": price * 10}])

    monkeypatch.setattr(analyzers.settings, "gemini_api_key", "test")
    monkeypatch.setattr(analyzers, "generate_structured", fake)
    files = [("files", ("a.txt", b"A quote", "text/plain")), ("files", ("b.txt", b"B quote", "text/plain"))]
    body = client.post("/api/tools/quote-compare", headers=user_headers, files=files).json()
    assert body["engine"] == "gemini"
    assert body["result"]["comparison"]["rows"][0]["cells"][1] == {
        "unit_price": 1500, "quantity": 10, "unit": None, "amount": 15000, "diff_pct": 50.0, "flag": "outlier"}


def test_timestamps_are_returned_with_utc_offset(client, user_headers):
    """새로고침 후 시각이 9시간 이르게 보이던 문제: DB 의 시간대 없는 값에 UTC 표시를 붙여야 한다."""
    listed = client.get("/api/tools/analyses", headers=user_headers).json()
    me = client.get("/api/auth/me", headers=user_headers).json()
    docs = client.get("/api/documents", headers=user_headers).json()
    for value in [a["created_at"] for a in listed] + [me["created_at"]] + [d["created_at"] for d in docs]:
        assert value.endswith(("Z", "+00:00")), value


def test_contract_gemini_output_is_relocated_and_rejudged_by_rules(client, user_headers, monkeypatch):
    """운영에서 실제로 받은 Gemini 응답 재현: 한 글자 바뀐 발췌문, 규칙과 다른 유형 · 위험도, 누락된 비밀유지 조항."""
    from backend.app.services import analyzers

    def fake(prompt, schema, text, *_):
        clause = lambda q, cat, risk: {"title": "-", "quote": q, "category": cat, "risk": risk, "explanation": "AI 설명"}  # noqa: E731
        return schema(title="마케팅 대행 서비스 계약서", summary="AI 요약", clauses=[
            clause("을이 계약기간 중 계약을 해지하는 경우 잔여 기간 이용료 총액의 50%를 위약금으로 갑에게 지급한다.", "termination", "high"),
            clause("갑은 운영상 필요할 경우 을에게 사전 통보 없이 서비스 내용을 변경할 수 있다.", "termination", "high"),
            clause("계약 만료 1개월 전까지 서면 해지 통보가 없으면 동일한 조건으로 1년씩 자동 연장된다.", "auto_renewal", "medium"),
        ])

    monkeypatch.setattr(analyzers.settings, "gemini_api_key", "test")
    monkeypatch.setattr(analyzers, "generate_structured", fake)
    text = (SAMPLES / "contract.txt").read_text(encoding="utf-8")
    body = client.post("/api/tools/contract-review", headers=user_headers, data={"text": text}).json()
    review = body["result"]["review"]
    by_category = {c["category"]: c for c in review["clauses"]}
    assert body["engine"] == "gemini" and review["summary"] == "AI 요약"
    assert by_category["penalty"]["risk"] == "high", "위약금 문장은 규칙으로 penalty 판정"
    assert by_category["auto_renewal"]["risk"] == "high", "AI 가 medium 으로 줘도 규칙 위험도(high) 적용"
    assert by_category["termination"]["start"] is not None, "'필요할'로 바뀐 발췌문도 원문 문장에 표시"
    assert {"confidentiality", "jurisdiction", "payment", "liability", "ip"} <= set(by_category), "AI 가 놓친 규칙 조항 추가"
    assert len(review["clauses"]) == 8 and all(c["start"] is not None for c in review["clauses"])
