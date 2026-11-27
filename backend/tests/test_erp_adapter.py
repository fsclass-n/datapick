"""ERP 어댑터 선택 · 설정 로딩 · file_export 출력."""

import json
from pathlib import Path

import pandas as pd
import pytest

from rpa import erp
from rpa.erp import ErpTypingError, FileExportAdapter, WebFormAdapter

RECEIPT = """스타벅스 강남R점
사업자번호: 123-45-67890
2026.11.17 14:32
아메리카노 2 4,500 9,000
부가세: 1,273
합계: 14,000원
결제수단: 신용카드
"""


def test_default_adapter_is_demo_web_form(monkeypatch):
    for key in ("ERP_ADAPTER", "ERP_CONFIG", "ERP_URL"):
        monkeypatch.delenv(key, raising=False)
    adapter = erp.get_adapter()
    assert isinstance(adapter, WebFormAdapter)
    assert adapter.cfg["url"].endswith("/erp-demo")
    assert adapter.cfg["fields"]["vendor"] == "#vendor"


def test_erp_config_inline_json(monkeypatch):
    cfg = {"url": "https://erp.example.com/new", "fields": {"vendor": "#v"}, "voucher_regex": "JV-[0-9-]+"}
    monkeypatch.delenv("ERP_URL", raising=False)
    monkeypatch.setenv("ERP_CONFIG", json.dumps(cfg))
    adapter = erp.get_adapter()
    assert adapter.cfg["url"] == "https://erp.example.com/new"
    assert adapter.cfg["fields"] == {"vendor": "#v"}
    assert adapter.cfg["submit"] == "#submit"  # 기본값 채움


def test_erp_config_file(monkeypatch, tmp_path):
    path = tmp_path / "target.json"
    path.write_text(json.dumps({"url": "https://a.b/c", "fields": {"vendor": "#v"}}), encoding="utf-8")
    monkeypatch.delenv("ERP_URL", raising=False)
    monkeypatch.setenv("ERP_CONFIG", str(path))
    assert erp.load_target_config()["url"] == "https://a.b/c"


def test_erp_url_overrides_config_and_derives_login(monkeypatch, tmp_path):
    """ERP_URL 을 두면 파일 설정의 url 을 덮어쓰고 로그인 주소도 유도된다."""
    path = tmp_path / "target.json"
    cfg = {"url": "http://localhost:8100/", "login": {"username": "#u", "password": "#p", "submit": "#b"}, "fields": {"vendor": "#v"}}
    path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setenv("ERP_CONFIG", str(path))
    monkeypatch.setenv("ERP_URL", "https://erp.example.com/")
    loaded = erp.load_target_config()
    assert loaded["url"] == "https://erp.example.com/"
    assert loaded["login"]["url"] == "https://erp.example.com/login"


def test_erp_config_bad_json_fails_clearly(monkeypatch):
    monkeypatch.setenv("ERP_CONFIG", '{"url": "https://a.b/')
    with pytest.raises(ErpTypingError, match="JSON"):
        erp.load_target_config()


def test_example_target_file_derives_login_url(monkeypatch):
    """저장소에 포함된 예시 파일은 login.url 없이 ERP_URL/파일 url 에서 유도된다."""
    path = Path("rpa/erp_target.example.json")
    monkeypatch.delenv("ERP_URL", raising=False)
    monkeypatch.setenv("ERP_CONFIG", str(path))
    loaded = erp.load_target_config()
    assert loaded["login"]["url"] == "http://localhost:8100/login"


def test_web_form_requires_url():
    with pytest.raises(ErpTypingError):
        WebFormAdapter({"url": ""})


def test_file_export_appends_rows(tmp_path):
    out = tmp_path / "erp_upload.xlsx"
    adapter = FileExportAdapter(out)
    first = adapter.submit({"vendor": "A상사", "date": "2026-11-17", "total_amount": 14000, "vat": 1273})
    second = adapter.submit({"vendor": "B상사", "date": "2026-11-18", "total_amount": 5000})
    assert "1행" in first and "2행" in second
    rows = pd.read_excel(out)
    assert list(rows["거래처"]) == ["A상사", "B상사"]


def test_rpa_api_uses_selected_adapter(client, user_headers, monkeypatch, tmp_path):
    """ERP_ADAPTER=file_export 이면 API 의 erp 타겟도 파일에 누적한다."""
    out = tmp_path / "erp_upload.xlsx"
    monkeypatch.setenv("ERP_ADAPTER", "file_export")
    monkeypatch.setenv("ERP_EXPORT_PATH", str(out))
    doc = client.post(
        "/api/documents/upload", headers=user_headers,
        files={"file": ("receipt.txt", RECEIPT.encode(), "text/plain")},
    ).json()
    job = client.post(f"/api/documents/{doc['id']}/rpa", headers=user_headers, json={"target": "erp"}).json()
    assert job["status"] == "success", job
    assert "erp_upload.xlsx" in job["message"]
    rows = pd.read_excel(out)
    assert rows.iloc[0]["거래처"] == "스타벅스 강남R점"
