"""datapick RPA 연동 검증용 독립 미니 ERP.

같은 서비스 안의 /erp-demo 와 달리 별도 프로세스·도메인으로 띄워
"서비스 경계를 넘는 실제 연동"(로그인 → 전표 입력 → 전표번호 확인)을 재현한다.
배포 시에는 별도 Render 서비스로 올리고, datapick 의 ERP_URL / ERP_CONFIG 가
이 서비스 주소를 가리키게 한다.

실행:
    uvicorn external_erp.main:app --port 8100
환경 변수:
    EXT_ERP_ID / EXT_ERP_PW  로그인 계정(기본 erp / demo1234)
    EXT_ERP_SECRET           세션 쿠키 서명용(선택)
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime
from itertools import count

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="ExtERP", docs_url=None, redoc_url=None)
_sequence = count(1)
VOUCHERS: list[dict] = []
SESSIONS: set[str] = set()
ERP_ID = os.getenv("EXT_ERP_ID", "erp")
ERP_PW = os.getenv("EXT_ERP_PW", "demo1234")


class VoucherIn(BaseModel):
    vendor: str
    business_number: str = ""
    date: str
    total_amount: int
    vat: int | None = None
    summary: str = ""


def _sid(request: Request) -> str | None:
    sid = request.cookies.get("ext_erp_sid")
    return sid if sid in SESSIONS else None


def _require(request: Request):
    if not _sid(request):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인이 필요합니다.")


@app.post("/api/vouchers")
def create_voucher(body: VoucherIn, request: Request):
    _require(request)
    voucher = {"voucher_no": f"AC-{datetime.now():%Y%m%d}-{next(_sequence):04d}", **body.model_dump()}
    VOUCHERS.append(voucher)
    return voucher


@app.get("/api/vouchers")
def list_vouchers(request: Request):
    _require(request)
    return VOUCHERS[-50:]


LOGIN_PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>AcmeERP 로그인</title>
<style>body{font-family:system-ui;background:#0b1f3a;display:grid;place-items:center;height:100vh;margin:0}
form{background:#fff;padding:36px;border-radius:14px;width:320px}
h1{margin:0 0 20px;font-size:20px;color:#0b1f3a}label{font-size:13px;color:#475569;display:block;margin:12px 0 4px}
input{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;box-sizing:border-box}
button{margin-top:20px;width:100%;padding:11px;border:0;border-radius:8px;background:#0ea5e9;color:#fff;font-weight:700}
.err{color:#dc2626;font-size:13px}</style></head><body>
<form method="post" action="/login"><h1>AcmeERP</h1>
__ERR__
<label>아이디</label><input id="login_id" name="login_id" required>
<label>비밀번호</label><input id="login_pw" name="login_pw" type="password" required>
<button id="login_btn" type="submit">로그인</button></form></body></html>"""


@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    return LOGIN_PAGE.replace("__ERR__", f'<p class="err">{error}</p>' if error else "")


@app.post("/login")
def do_login(login_id: str = Form(...), login_pw: str = Form(...)):
    if login_id != ERP_ID or login_pw != ERP_PW:
        return RedirectResponse("/login?error=아이디 또는 비밀번호가 올바르지 않습니다.", status_code=303)
    sid = secrets.token_urlsafe(24)
    SESSIONS.add(sid)
    res = RedirectResponse("/", status_code=303)
    res.set_cookie("ext_erp_sid", sid, httponly=True, samesite="lax")
    return res


@app.get("/logout")
def logout(request: Request):
    SESSIONS.discard(request.cookies.get("ext_erp_sid", ""))
    return RedirectResponse("/login", status_code=303)


MAIN_PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AcmeERP - 매입 전표</title>
<style>
 *{box-sizing:border-box}
 body{font-family:system-ui,sans-serif;background:#eef4fb;margin:0;color:#132a4f}
 header{background:#0b3d91;color:#fff;padding:14px 28px;font-size:15px;font-weight:700;display:flex;justify-content:space-between;align-items:center}
 header a{color:#bfdbfe;font-size:12px;text-decoration:none}
 main{display:flex;gap:24px;padding:28px;max-width:1180px;margin:auto;align-items:flex-start;flex-wrap:wrap}
 form{width:420px;flex-shrink:0;background:#fff;padding:28px;border-radius:12px;box-shadow:0 4px 20px #0001}
 h1{font-size:18px;margin:0 0 20px} label{display:block;font-size:13px;margin:12px 0 4px;color:#475569}
 input{width:100%;padding:9px 11px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px}
 button{margin-top:20px;width:100%;padding:11px;border:0;border-radius:8px;background:#0b3d91;color:#fff;font-weight:600}
 #result{margin-top:16px;font-size:14px}
 section{flex:1;min-width:340px;background:#fff;padding:24px 28px;border-radius:12px;box-shadow:0 4px 20px #0001}
 h2{font-size:16px;margin:0 0 4px} .hint{font-size:12px;color:#64748b;margin:0 0 14px}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th{text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:12px;white-space:nowrap}
 td{padding:8px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top}
 td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
 td.no{font-family:ui-monospace,monospace;font-size:12px;white-space:nowrap}
 tr.new td{background:#e0f2fe}
 .empty{padding:32px;text-align:center;color:#94a3b8;font-size:13px}
</style></head><body>
<header>AcmeERP 회계 시스템 <a href="/logout">로그아웃</a></header>
<main>
<form id="voucher">
 <h1>매입 전표 등록</h1>
 <label for="vendor">거래처명</label><input id="vendor" required>
 <label for="business_number">사업자등록번호</label><input id="business_number">
 <label for="date">거래일자</label><input id="date" placeholder="YYYY-MM-DD" required>
 <label for="total_amount">공급가액+세액</label><input id="total_amount" inputmode="numeric" required>
 <label for="vat">세액</label><input id="vat" inputmode="numeric">
 <label for="summary">적요</label><input id="summary">
 <button id="submit" type="submit">전표 등록</button>
 <div id="result"></div>
</form>
<section>
 <h2>전표 조회</h2>
 <p class="hint">DataPick 의 'ERP 자동 타이핑'이 이 화면에 로그인해 전표를 등록합니다. 목록은 3초 간격으로 갱신됩니다.</p>
 <table id="vlist"><thead><tr>
  <th>전표번호</th><th>거래일자</th><th>거래처</th><th>사업자번호</th>
  <th class="num">금액</th><th class="num">세액</th><th>적요</th>
 </tr></thead><tbody><tr><td colspan="7" class="empty">등록된 전표가 없습니다</td></tr></tbody></table>
</section>
</main>
<script>
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const won = (n) => n == null ? '' : Number(n).toLocaleString('ko-KR');
let known = new Set();
async function loadList(highlight) {
  const res = await fetch('/api/vouchers');
  if (res.status === 401) { location.href = '/login'; return; }
  const rows = await res.json();
  const tbody = document.querySelector('#vlist tbody');
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="7" class="empty">등록된 전표가 없습니다</td></tr>'; return; }
  tbody.innerHTML = [...rows].reverse().map((v) => {
    const fresh = highlight && !known.has(v.voucher_no);
    return `<tr class="${fresh ? 'new' : ''}"><td class="no">${esc(v.voucher_no)}</td><td>${esc(v.date)}</td>` +
      `<td>${esc(v.vendor)}</td><td>${esc(v.business_number)}</td>` +
      `<td class="num">${won(v.total_amount)}</td><td class="num">${won(v.vat)}</td><td>${esc(v.summary)}</td></tr>`;
  }).join('');
  known = new Set(rows.map((v) => v.voucher_no));
}
document.getElementById('voucher').addEventListener('submit', async (e) => {
  e.preventDefault();
  const v = (id) => document.getElementById(id).value.trim();
  const out = document.getElementById('result');
  const res = await fetch('/api/vouchers', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({vendor: v('vendor'), business_number: v('business_number'), date: v('date'),
      total_amount: Number(v('total_amount').replace(/,/g, '')), vat: v('vat') ? Number(v('vat').replace(/,/g, '')) : null,
      summary: v('summary')})});
  if (res.status === 401) { location.href = '/login'; return; }
  const data = await res.json();
  out.dataset.status = res.ok ? 'ok' : 'error';
  if (res.ok) { out.dataset.voucher = data.voucher_no; out.textContent = '등록 완료: ' + data.voucher_no; loadList(true); }
  else { out.textContent = '등록 실패: ' + JSON.stringify(data.detail); }
});
loadList(false);
setInterval(() => loadList(true), 3000);
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not _sid(request):
        return RedirectResponse("/login", status_code=303)
    return MAIN_PAGE


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "external_erp"}


# favicon 등 잡다한 요청의 404 JSON 응답 정리용
@app.exception_handler(404)
def not_found(request, exc):
    return JSONResponse({"detail": "Not Found"}, status_code=404)
