"""Playwright 로 웹 ERP 전표 입력 화면에 파싱 결과를 자동 타이핑한다.

실제 구현은 rpa/erp.py 의 WebFormAdapter. 이 모듈은 데모 ERP 대상의
CLI · 호환 API 를 유지한다. 실제 ERP 연동 시에는 ERP_CONFIG(JSON)로
셀렉터 맵과 로그인 설정을 지정한다(rpa/erp_target.example.json 참조).

단독 실행 예:
    python -m rpa.erp_typer --vendor "스타벅스 강남점" --date 2026-11-17 --amount 12500
"""

from __future__ import annotations

import argparse
import os

from rpa.erp import DEMO_FIELD_SELECTORS, ErpTypingError, WebFormAdapter

FIELD_SELECTORS = DEMO_FIELD_SELECTORS
SUBMIT_SELECTOR = "#submit"
RESULT_SELECTOR = "#result[data-status]"


def type_record(record: dict, url: str, headless: bool = True, delay_ms: int = 20) -> str:
    """레코드를 ERP 화면에 입력하고 ERP 가 발급한 전표 번호를 반환한다."""
    adapter = WebFormAdapter({
        "url": url,
        "fields": dict(FIELD_SELECTORS),
        "submit": SUBMIT_SELECTOR,
        "result": "#result",
        "voucher_attr": "data-voucher",
        "delay_ms": delay_ms,
    })
    return adapter.submit(record, headless=headless)


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
