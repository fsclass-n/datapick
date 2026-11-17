"""RPA 시연용 가상 ERP 전표 입력 화면. 실제 ERP 대신 Playwright 타이핑 대상이 된다."""

from datetime import datetime
from itertools import count

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(prefix="/erp-demo", tags=["erp-demo"], include_in_schema=False)
_sequence = count(1)
VOUCHERS: list[dict] = []


class VoucherIn(BaseModel):
    vendor: str
    business_number: str = ""
    date: str
    total_amount: int
    vat: int | None = None
    summary: str = ""


@router.post("/api/vouchers")
def create_voucher(body: VoucherIn):
    voucher = {"voucher_no": f"JV-{datetime.now():%Y%m%d}-{next(_sequence):04d}", **body.model_dump()}
    VOUCHERS.append(voucher)
    return voucher


@router.get("/api/vouchers")
def list_vouchers():
    return VOUCHERS[-50:]


PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Demo ERP - 전표 입력</title>
<style>
 body{font-family:system-ui,sans-serif;background:#f1f5f9;margin:0;padding:40px;color:#0f172a}
 form{max-width:520px;margin:auto;background:#fff;padding:28px;border-radius:12px;box-shadow:0 4px 20px #0001}
 h1{font-size:18px;margin:0 0 20px} label{display:block;font-size:13px;margin:12px 0 4px;color:#475569}
 input{width:100%;box-sizing:border-box;padding:9px 11px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px}
 button{margin-top:20px;width:100%;padding:11px;border:0;border-radius:8px;background:#4f46e5;color:#fff;font-weight:600}
 #result{margin-top:16px;font-size:14px}
</style></head><body>
<form id="voucher">
 <h1>Demo ERP · 매입 전표 입력</h1>
 <label for="vendor">거래처</label><input id="vendor" required>
 <label for="business_number">사업자번호</label><input id="business_number">
 <label for="date">거래일자</label><input id="date" placeholder="YYYY-MM-DD" required>
 <label for="total_amount">합계금액</label><input id="total_amount" inputmode="numeric" required>
 <label for="vat">부가세</label><input id="vat" inputmode="numeric">
 <label for="summary">적요</label><input id="summary">
 <button id="submit" type="submit">전표 저장</button>
 <div id="result"></div>
</form>
<script>
document.getElementById('voucher').addEventListener('submit', async (e) => {
  e.preventDefault();
  const v = (id) => document.getElementById(id).value.trim();
  const out = document.getElementById('result');
  const res = await fetch('/erp-demo/api/vouchers', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({vendor: v('vendor'), business_number: v('business_number'), date: v('date'),
      total_amount: Number(v('total_amount').replace(/,/g, '')), vat: v('vat') ? Number(v('vat').replace(/,/g, '')) : null,
      summary: v('summary')})});
  const data = await res.json();
  out.dataset.status = res.ok ? 'ok' : 'error';
  if (res.ok) { out.dataset.voucher = data.voucher_no; out.textContent = '저장 완료: ' + data.voucher_no; }
  else { out.textContent = '저장 실패: ' + JSON.stringify(data.detail); }
});
</script></body></html>"""


@router.get("", response_class=HTMLResponse)
def page():
    return PAGE
