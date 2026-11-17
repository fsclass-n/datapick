"""Playwright 로 웹 ERP 전표 입력 화면에 파싱 결과를 자동 타이핑한다.

기본 대상은 백엔드가 제공하는 데모 ERP 화면(`/erp-demo`)이며, 실제 ERP 에 연동할 때는
`FIELD_SELECTORS` 와 `SUBMIT_SELECTOR`, `RESULT_SELECTOR` 를 해당 화면에 맞게 바꾼다.

단독 실행 예:
    python -m rpa.erp_typer --vendor "스타벅스 강남점" --date 2026-11-17 --amount 12500
"""

from __future__ import annotations

import argparse
import os

FIELD_SELECTORS = {
    "vendor": "#vendor",
    "business_number": "#business_number",
    "date": "#date",
    "total_amount": "#total_amount",
    "vat": "#vat",
    "summary": "#summary",
}
SUBMIT_SELECTOR = "#submit"
RESULT_SELECTOR = "#result[data-status]"


class ErpTypingError(RuntimeError):
    pass


def type_record(record: dict, url: str, headless: bool = True, delay_ms: int = 20) -> str:
    """레코드를 ERP 화면에 입력하고 ERP 가 발급한 전표 번호를 반환한다."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ErpTypingError("playwright 패키지가 설치되어 있지 않습니다.") from exc

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=15_000)
                for key, selector in FIELD_SELECTORS.items():
                    value = record.get(key)
                    if value in (None, ""):
                        continue
                    page.fill(selector, "")
                    page.type(selector, str(value), delay=delay_ms)
                page.click(SUBMIT_SELECTOR)
                result = page.wait_for_selector(RESULT_SELECTOR, timeout=10_000)
                if result.get_attribute("data-status") != "ok":
                    raise ErpTypingError(result.inner_text() or "ERP 가 입력을 거부했습니다.")
                return result.get_attribute("data-voucher") or result.inner_text()
            finally:
                browser.close()
    except PlaywrightError as exc:
        message = str(exc).splitlines()[0]
        if "Executable doesn't exist" in str(exc):
            message = "Chromium 이 설치되어 있지 않습니다. `playwright install chromium` 을 실행하세요."
        raise ErpTypingError(message) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="ERP 전표 자동 입력")
    parser.add_argument("--url", default=os.getenv("ERP_URL", "http://localhost:8000/erp-demo"))
    parser.add_argument("--vendor", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--amount", type=int, required=True)
    parser.add_argument("--vat", type=int)
    parser.add_argument("--summary", default="")
    parser.add_argument("--headed", action="store_true", help="브라우저 화면을 띄워서 실행")
    args = parser.parse_args()
    record = {
        "vendor": args.vendor,
        "date": args.date,
        "total_amount": args.amount,
        "vat": args.vat,
        "summary": args.summary,
    }
    print("전표 번호:", type_record(record, args.url, headless=not args.headed))


if __name__ == "__main__":
    main()
