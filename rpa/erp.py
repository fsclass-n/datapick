"""ERP 입력 어댑터 계층.

`ErpAdapter.submit(record) -> str` 인터페이스로 통일하고, 대상 ERP별 차이는
설정(JSON)으로 흡수한다. 어떤 어댑터를 쓸지는 환경 변수로 결정한다.

- ERP_ADAPTER  : `web_form`(기본) | `file_export`
- ERP_CONFIG   : web_form 대상 설정 JSON 파일 경로 또는 JSON 문자열.
                 비우면 같은 서버의 데모 ERP(/erp-demo) 대상으로 자동 설정된다.
- ERP_URL      : 대상 화면 URL — 설정의 url 을 덮어쓰고, login.url 이 없으면
                 `{ERP_URL}/login` 으로 자동 유도된다(파일 설정 + URL 만으로 연결 가능)
- ERP_EXPORT_PATH : file_export 출력 파일(기본 storage/erp_upload.xlsx)

web_form 설정 예시는 rpa/erp_target.example.json 참조.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:  # dotenv 없이 단독 실행되는 환경
    pass

DEMO_FIELD_SELECTORS = {
    "vendor": "#vendor",
    "business_number": "#business_number",
    "date": "#date",
    "total_amount": "#total_amount",
    "vat": "#vat",
    "summary": "#summary",
}


class ErpTypingError(RuntimeError):
    pass


class ErpAdapter:
    """파싱 결과 한 건을 대상 ERP에 입력하고 영수 번호/식별자를 반환한다."""

    name = "base"

    def submit(self, record: dict, headless: bool = True) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class WebFormAdapter(ErpAdapter):
    """브라우저 자동화로 웹 ERP 전표 화면에 타이핑한다.

    config 키:
      url            입력 화면 URL
      fields         {record 키: CSS 셀렉터}
      submit         저장 버튼 셀렉터
      result         결과 확인 요소 셀렉터(기본 "#result")
      result_ok_attr / result_ok_value  성공 판정(기본 data-status=ok)
      voucher_attr   전표번호가 들어있는 속성(기본 data-voucher, 없으면 요소 텍스트)
      voucher_regex  텍스트에서 전표번호를 뽑는 정규식(선택)
      login          선택. {"url", "username", "password", "submit", "username_env",
                     "password_env"} — 값은 env 이름으로 지정하고 비밀 값은 .env 에 둔다.
                     계정별 연결에서는 "username_value" / "password_value" 로 값을 직접 넘길 수 있다.
      delay_ms       키 입력 간 지연(기본 20)
    """

    name = "web_form"

    def __init__(self, config: dict):
        self.cfg = dict(config)
        self.cfg.setdefault("fields", DEMO_FIELD_SELECTORS)
        self.cfg.setdefault("submit", "#submit")
        self.cfg.setdefault("result", "#result")
        self.cfg.setdefault("result_ok_attr", "data-status")
        self.cfg.setdefault("result_ok_value", "ok")
        self.cfg.setdefault("voucher_attr", "data-voucher")
        if not self.cfg.get("url"):
            raise ErpTypingError("web_form 어댑터에 대상 url 이 없습니다.")

    def submit(self, record: dict, headless: bool = True) -> str:
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ErpTypingError("playwright 패키지가 설치되어 있지 않습니다.") from exc

        cfg = self.cfg
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                try:
                    page = browser.new_page()
                    self._login(page)
                    page.goto(cfg["url"], wait_until="domcontentloaded", timeout=15_000)
                    for key, selector in cfg["fields"].items():
                        value = record.get(key)
                        if value in (None, ""):
                            continue
                        page.fill(selector, "")
                        page.type(selector, str(value), delay=cfg.get("delay_ms", 20))
                    page.click(cfg["submit"])
                    return self._read_voucher(page)
                finally:
                    browser.close()
        except PlaywrightError as exc:
            message = str(exc).splitlines()[0]
            if "Executable doesn't exist" in str(exc):
                message = "Chromium 이 설치되어 있지 않습니다. `playwright install chromium` 을 실행하세요."
            raise ErpTypingError(message) from exc

    def _login(self, page) -> None:
        login = self.cfg.get("login")
        if not login:
            return
        username = login.get("username_value") or os.getenv(login.get("username_env", "ERP_USERNAME"), "")
        password = login.get("password_value") or os.getenv(login.get("password_env", "ERP_PASSWORD"), "")
        if not username or not password:
            raise ErpTypingError(
                f"ERP 로그인 자격증명이 없습니다({login.get('username_env')}, {login.get('password_env')})."
            )
        page.goto(login["url"], wait_until="domcontentloaded", timeout=15_000)
        page.fill(login["username"], username)
        page.fill(login["password"], password)
        page.click(login["submit"])
        page.wait_for_load_state("domcontentloaded")

    def _read_voucher(self, page) -> str:
        cfg = self.cfg
        result = page.wait_for_selector(cfg["result"], timeout=10_000)
        if cfg.get("result_ok_attr"):
            if result.get_attribute(cfg["result_ok_attr"]) != cfg["result_ok_value"]:
                raise ErpTypingError(result.inner_text() or "ERP 가 입력을 거부했습니다.")
        voucher_attr = cfg.get("voucher_attr")
        if voucher_attr and result.get_attribute(voucher_attr):
            return result.get_attribute(voucher_attr)
        text = (result.inner_text() or "").strip()
        pattern = cfg.get("voucher_regex")
        if pattern:
            m = re.search(pattern, text)
            if m:
                return m.group(1) if m.groups() else m.group(0)
        return text or "(전표번호 없음)"


class FileExportAdapter(ErpAdapter):
    """ERP 전표 일괄등록용 엑셀 파일에 행을 쌓는다(사람이 ERP에서 업로드)."""

    name = "file_export"

    DEFAULT_COLUMNS = {
        "date": "거래일자",
        "vendor": "거래처",
        "business_number": "사업자번호",
        "total_amount": "합계금액",
        "vat": "부가세",
        "summary": "적요",
    }

    def __init__(self, path: Path, columns: dict | None = None):
        self.path = Path(path)
        self.columns = columns or self.DEFAULT_COLUMNS

    def submit(self, record: dict, headless: bool = True) -> str:
        import pandas as pd

        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {header: record.get(key) for key, header in self.columns.items()}
        new = pd.DataFrame([row])
        if self.path.exists():
            new = pd.concat([pd.read_excel(self.path), new], ignore_index=True)
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            new.to_excel(writer, index=False, sheet_name="vouchers")
        return f"{self.path.name} {len(new)}행"


def _resolve_url(config_url: str = "") -> str:
    """대상 URL 결정: ERP_URL env > 설정 파일 url > 같은 컨테이너의 데모 ERP.

    Render 에서 localhost 계열은 자기 컨테이너일 수밖에 없으므로 데모로 되돌린다.
    """
    url = os.getenv("ERP_URL") or config_url
    if not url or (os.getenv("RENDER") and ("localhost" in url or "127.0.0.1" in url)):
        return f"http://127.0.0.1:{os.getenv('PORT', '8000')}/erp-demo"
    return url


def load_target_config() -> dict:
    """ERP_CONFIG(JSON 파일 경로 또는 JSON 문자열)를 읽는다. 없으면 데모 ERP 대상."""
    raw = (os.getenv("ERP_CONFIG") or "").strip()
    if raw:
        try:
            cfg = json.loads(Path(raw).read_text(encoding="utf-8") if Path(raw).exists() else raw)
        except json.JSONDecodeError as exc:
            raise ErpTypingError(f"ERP_CONFIG JSON 해석 실패: {exc}. 파일 경로 또는 완전한 JSON 인지 확인하세요.") from exc
        if not isinstance(cfg, dict):
            raise ErpTypingError("ERP_CONFIG 은 JSON 객체여야 합니다.")
        cfg["url"] = _resolve_url(cfg.get("url", ""))
    else:
        cfg = {"url": _resolve_url(), "fields": dict(DEMO_FIELD_SELECTORS)}
    login = cfg.get("login")
    if isinstance(login, dict) and not login.get("url"):
        login["url"] = cfg["url"].rstrip("/") + "/login"
    return cfg


def get_adapter() -> ErpAdapter:
    kind = (os.getenv("ERP_ADAPTER") or "web_form").strip().lower()
    if kind == "file_export":
        return FileExportAdapter(os.getenv("ERP_EXPORT_PATH", "storage/erp_upload.xlsx"))
    if kind == "web_form":
        return WebFormAdapter(load_target_config())
    raise ErpTypingError(f"알 수 없는 ERP_ADAPTER: {kind}")


def config_for_connection(
    *, url: str, username: str, password: str, login_url: str | None = None, fields: dict | None = None
) -> dict:
    """고객사 ERP 연결 정보로 web_form 설정을 만든다.

    셀렉터 맵은 플랫폼 공용 설정(ERP_CONFIG / 데모)을 기본으로 쓰고,
    고객이 fields 를 지정하면 그 맵으로 교체한다.
    """
    cfg = load_target_config()
    cfg["url"] = url
    if fields:
        cfg["fields"] = fields
    base_login = cfg.get("login") if isinstance(cfg.get("login"), dict) else {}
    cfg["login"] = {
        "url": login_url or url.rstrip("/") + "/login",
        "username": base_login.get("username", "#login_id"),
        "password": base_login.get("password", "#login_pw"),
        "submit": base_login.get("submit", "#login_btn"),
        "username_value": username,
        "password_value": password,
    }
    return cfg


def submit_record(record: dict, config: dict | None = None) -> str:
    """환경 변수로 선택된 어댑터(또는 주어진 계정별 설정)로 파싱 결과를 입력한다."""
    headless = os.getenv("RPA_HEADLESS", "true").lower() != "false"
    adapter = WebFormAdapter(config) if config else get_adapter()
    return adapter.submit(record, headless=headless)
