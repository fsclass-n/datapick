"""파싱된 정형 데이터를 엑셀 원장(ledger)에 누적 적재한다."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

LEDGER_COLUMNS = {
    "document_id": "문서ID",
    "document_type": "문서유형",
    "vendor": "거래처",
    "business_number": "사업자번호",
    "date": "거래일자",
    "total_amount": "합계금액",
    "vat": "부가세",
    "currency": "통화",
    "payment_method": "결제수단",
    "item_summary": "품목",
    "summary": "적요",
}


def to_row(document_id: int, parsed: dict) -> dict:
    items = parsed.get("items") or []
    item_summary = ", ".join(
        f"{item.get('name', '')} x{item.get('quantity') or 1}" for item in items if item.get("name")
    )
    row = {key: parsed.get(key) for key in LEDGER_COLUMNS}
    row.update(document_id=document_id, item_summary=item_summary)
    return row


def append_rows(path: Path, rows: list[dict]) -> int:
    """원장 파일에 행을 추가한다. 같은 문서ID 행은 최신 값으로 교체한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(rows, columns=list(LEDGER_COLUMNS)).rename(columns=LEDGER_COLUMNS)
    if path.exists():
        existing = pd.read_excel(path)
        existing = existing[~existing["문서ID"].isin(new["문서ID"])]
        new = pd.concat([existing, new], ignore_index=True)
    new = new.sort_values("문서ID").reset_index(drop=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        new.to_excel(writer, index=False, sheet_name="ledger")
        sheet = writer.sheets["ledger"]
        for column in sheet.columns:
            width = max(len(str(cell.value or "")) for cell in column)
            sheet.column_dimensions[column[0].column_letter].width = min(max(width + 4, 10), 50)
    return len(new)
