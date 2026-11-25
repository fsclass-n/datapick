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
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Demo ERP - 전표 입력</title>
<style>
 *{box-sizing:border-box}
 body{font-family:system-ui,sans-serif;background:#f1f5f9;margin:0;color:#0f172a}
 header{background:#1e293b;color:#fff;padding:14px 28px;font-size:15px;font-weight:700;display:flex;justify-content:space-between;align-items:center}
 header span{font-size:12px;font-weight:400;color:#94a3b8}
 main{display:flex;gap:24px;padding:28px;max-width:1180px;margin:auto;align-items:flex-start;flex-wrap:wrap}
 form{width:420px;flex-shrink:0;background:#fff;padding:28px;border-radius:12px;box-shadow:0 4px 20px #0001}
 h1{font-size:18px;margin:0 0 20px} label{display:block;font-size:13px;margin:12px 0 4px;color:#475569}
 input{width:100%;padding:9px 11px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px}
 button{margin-top:20px;width:100%;padding:11px;border:0;border-radius:8px;background:#4f46e5;color:#fff;font-weight:600}
 #result{margin-top:16px;font-size:14px}
 section{flex:1;min-width:340px;background:#fff;padding:24px 28px;border-radius:12px;box-shadow:0 4px 20px #0001}
 h2{font-size:16px;margin:0 0 4px} .hint{font-size:12px;color:#64748b;margin:0 0 14px}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th{text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:12px;white-space:nowrap}
 td{padding:8px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top}
 td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
 td.dt{white-space:nowrap}
 td.no{font-family:ui-monospace,monospace;font-size:12px;white-space:nowrap}
 tr.new td{background:#eef2ff}
 .empty{padding:32px;text-align:center;color:#94a3b8;font-size:13px}
</style></head><body>
<header>Demo ERP <span>RPA 타이핑 시연용 가상 전표 시스템</span></header>
<main>
<form id="voucher">
 <h1>매입 전표 입력</h1>
 <label for="vendor">거래처</label><input id="vendor" required>
 <label for="business_number">사업자번호</label><input id="business_number">
 <label for="date">거래일자</label><input id="date" placeholder="YYYY-MM-DD" required>
 <label for="total_amount">합계금액</label><input id="total_amount" inputmode="numeric" required>
 <label for="vat">부가세</label><input id="vat" inputmode="numeric">
 <label for="summary">적요</label><input id="summary">
 <button id="submit" type="submit">전표 저장</button>
 <div id="result"></div>
</form>
<section>
 <h2>전표 목록</h2>
 <p class="hint">저장된 전표가 3초 간격으로 자동 갱신됩니다. DataPick 에서 'ERP 자동 타이핑'을 실행하면 여기에 새 전표가 나타납니다.</p>
 <table id="vlist"><thead><tr>
  <th>전표번호</th><th>거래일자</th><th>거래처</th><th>사업자번호</th>
  <th class="num">합계금액</th><th class="num">부가세</th><th>적요</th>
 </tr></thead><tbody><tr><td colspan="7" class="empty">입력된 전표가 없습니다</td></tr></tbody></table>
</section>
</main>
<script>
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const won = (n) => n == null ? '' : Number(n).toLocaleString('ko-KR');
let known = new Set();
async function loadList(highlight) {
  const rows = await (await fetch('/erp-demo/api/vouchers')).json();
  const tbody = document.querySelector('#vlist tbody');
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="7" class="empty">입력된 전표가 없습니다</td></tr>'; return; }
  tbody.innerHTML = [...rows].reverse().map((v) => {
    const fresh = highlight && !known.has(v.voucher_no);
    return `<tr class="${fresh ? 'new' : ''}"><td class="no">${esc(v.voucher_no)}</td><td class="dt">${esc(v.date)}</td>` +
      `<td>${esc(v.vendor)}</td><td>${esc(v.business_number)}</td>` +
      `<td class="num">${won(v.total_amount)}</td><td class="num">${won(v.vat)}</td><td>${esc(v.summary)}</td></tr>`;
  }).join('');
  known = new Set(rows.map((v) => v.voucher_no));
}
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
  if (res.ok) { out.dataset.voucher = data.voucher_no; out.textContent = '저장 완료: ' + data.voucher_no; loadList(true); }
  else { out.textContent = '저장 실패: ' + JSON.stringify(data.detail); }
});
loadList(false);
setInterval(() => loadList(true), 3000);
</script></body></html>"""


@router.get("", response_class=HTMLResponse)
def page():
    return PAGE
