"""datapick RPA 연동 검증용 독립 미니 ERP — 가상 고객사 "(주)한빛물산"의 BizCube ERP.

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

app = FastAPI(title="BizCube ERP", docs_url=None, redoc_url=None)
_sequence = count(1)
VOUCHERS: list[dict] = []
SESSIONS: set[str] = set()
ERP_ID = os.getenv("EXT_ERP_ID", "erp")
ERP_PW = os.getenv("EXT_ERP_PW", "demo1234")
COMPANY = "(주)한빛물산"
PRODUCT = "BizCube ERP"


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
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__PRODUCT__ 로그인 - __COMPANY__</title>
<style>
*{box-sizing:border-box;margin:0}
body{font-family:'Malgun Gothic',system-ui,sans-serif;background:linear-gradient(160deg,#0d2240 0%,#163a63 55%,#1d4e89 100%);min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px}
.card{background:#fff;width:380px;border-radius:6px;box-shadow:0 20px 60px #0007;overflow:hidden}
.brand{padding:30px 34px 22px;border-bottom:1px solid #e5e9f0}
.brand .co{font-size:13px;color:#5a6b85;letter-spacing:.08em}
.brand h1{font-size:24px;color:#0d2240;margin-top:4px}
.brand h1 b{color:#1d5fbf}
.brand .ver{font-size:11px;color:#93a3bb;margin-top:6px}
form{padding:26px 34px 30px}
label{font-size:12px;color:#41506b;display:block;margin:14px 0 5px;font-weight:700}
input{width:100%;padding:10px 12px;border:1px solid #c3ccd9;border-radius:3px;font-size:14px}
input:focus{outline:2px solid #1d5fbf33;border-color:#1d5fbf}
button{margin-top:22px;width:100%;padding:12px;border:0;border-radius:3px;background:#1d5fbf;color:#fff;font-weight:700;font-size:14px;cursor:pointer}
button:hover{background:#164fa3}
.err{color:#c0292b;font-size:12px;margin-top:10px;background:#fdecec;border:1px solid #f3c1c1;padding:8px 10px;border-radius:3px}
footer{margin-top:22px;color:#9db4d4;font-size:11px;text-align:center;line-height:1.7}
.sso{margin-top:14px;text-align:center;font-size:11px;color:#93a3bb}
</style></head><body>
<div class="card">
 <div class="brand">
  <div class="co">__COMPANY__</div>
  <h1>__PRODUCT__ <b>Cloud</b></h1>
  <div class="ver">v5.2.1 · 통합회계관리시스템 · 회계기준 K-IFRS</div>
 </div>
 <form method="post" action="/login">
__ERR__
  <label for="login_id">사원 코드 / 아이디</label>
  <input id="login_id" name="login_id" autocomplete="username" required>
  <label for="login_pw">비밀번호</label>
  <input id="login_pw" name="login_pw" type="password" autocomplete="current-password" required>
  <button id="login_btn" type="submit">로그인</button>
  <p class="sso">SSO 로그인은 사내 인증서버(HANBIT-IDP)를 통해 제공됩니다.</p>
 </form>
</div>
<footer>__COMPANY__ · 경리팀 내선 0415 · 시스템 문의 it-help@hanbit.co.kr<br>© 2021-2026 Hanbit Trading Co., Ltd. All rights reserved.</footer>
</body></html>"""


@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    page = LOGIN_PAGE.replace("__COMPANY__", COMPANY).replace("__PRODUCT__", PRODUCT)
    return page.replace("__ERR__", f'<p class="err">{error}</p>' if error else "")


@app.post("/login")
def do_login(login_id: str = Form(...), login_pw: str = Form(...)):
    if login_id != ERP_ID or login_pw != ERP_PW:
        return RedirectResponse("/login?error=사용자 정보가 일치하지 않습니다. 관리자에게 문의하세요.", status_code=303)
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
<title>__PRODUCT__ - 매입전표등록</title>
<style>
*{box-sizing:border-box}
body{font-family:'Malgun Gothic',system-ui,sans-serif;background:#e8ecf3;margin:0;color:#1c2b45;font-size:13px}
.topbar{background:#0d2240;color:#fff;height:46px;display:flex;align-items:center;padding:0 18px;gap:16px}
.topbar .logo{font-weight:800;font-size:15px;letter-spacing:.02em}
.topbar .logo b{color:#7db2ff}
.topbar nav{display:flex;gap:2px;font-size:12px}
.topbar nav span{padding:6px 10px;border-radius:3px;color:#b9c8e0}
.topbar nav span.on{background:#1d5fbf;color:#fff}
.topbar .who{margin-left:auto;font-size:12px;color:#b9c8e0}
.topbar .who b{color:#fff}
.topbar a{color:#9db4d4;font-size:11px;text-decoration:none;margin-left:10px}
.wrap{display:flex;min-height:calc(100vh - 46px)}
aside{width:190px;background:#152c4e;color:#c4d2ea;padding:16px 0;flex-shrink:0}
aside h3{font-size:11px;color:#6f86ad;padding:0 16px;margin:14px 0 6px;font-weight:600;letter-spacing:.05em}
aside a{display:block;padding:8px 16px 8px 20px;color:#c4d2ea;text-decoration:none;font-size:12.5px;border-left:3px solid transparent}
aside a.on{background:#1d5fbf;color:#fff;border-left-color:#7db2ff}
aside a:hover:not(.on){background:#1b3560}
main{flex:1;padding:18px 22px;min-width:0}
.crumb{font-size:11.5px;color:#6b7d99;margin-bottom:10px}
.panel{background:#fff;border:1px solid #d4dbe8;border-radius:3px;margin-bottom:16px}
.panel>.hd{padding:10px 14px;border-bottom:1px solid #e4e9f2;font-weight:700;font-size:13px;display:flex;align-items:center;gap:8px}
.panel>.hd .tag{font-size:10.5px;font-weight:600;color:#1d5fbf;background:#e8f0fd;border:1px solid #b9d0f5;padding:1px 7px;border-radius:10px}
.toolbar{display:flex;gap:6px;padding:8px 14px;border-bottom:1px solid #e4e9f2;background:#f7f9fc}
.toolbar button{padding:6px 14px;border:1px solid #c3ccd9;background:#fff;border-radius:3px;font-size:12px;cursor:pointer;color:#33445f}
.toolbar button:hover{background:#eef3fa}
.toolbar .sp{flex:1}
.toolbar .meta{font-size:11.5px;color:#6b7d99;align-self:center}
.grid{display:grid;grid-template-columns:1fr 380px;gap:16px;align-items:start}
@media (max-width:1000px){.grid{grid-template-columns:1fr}aside{display:none}}
table.data{width:100%;border-collapse:collapse;font-size:12.5px}
table.data th{background:#eef2f8;border:1px solid #d4dbe8;padding:7px 9px;text-align:left;color:#41506b;font-weight:600;white-space:nowrap}
table.data td{border:1px solid #e2e7f0;padding:7px 9px;background:#fff;vertical-align:top}
table.data td.num,table.data th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.data td.no{font-family:Consolas,ui-monospace,monospace;font-size:11.5px;white-space:nowrap}
table.data tr.new td{background:#fff8e1}
table.data tfoot td{background:#f2f5fa;font-weight:700;border:1px solid #d4dbe8}
.empty{padding:36px;text-align:center;color:#93a3bb}
form.reg{padding:14px}
form.reg label{display:block;font-size:11.5px;color:#41506b;font-weight:700;margin:10px 0 4px}
form.reg label .req{color:#c0292b}
form.reg input,form.reg select{width:100%;padding:7px 9px;border:1px solid #c3ccd9;border-radius:3px;font-size:13px}
form.reg input:focus{outline:2px solid #1d5fbf33;border-color:#1d5fbf}
form.reg .row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
form.reg button#submit{margin-top:14px;width:100%;padding:10px;border:0;border-radius:3px;background:#0d2240;color:#fff;font-weight:700;font-size:13px;cursor:pointer}
form.reg button#submit:hover{background:#1d5fbf}
#result{margin-top:10px;font-size:12px}
.statusbar{background:#0d2240;color:#8fa8cc;font-size:11px;padding:5px 18px;display:flex;gap:18px}
</style></head><body>
<div class="topbar">
 <span class="logo">__PRODUCT__ <b>Cloud</b></span>
 <nav><span>시스템</span><span class="on">회계</span><span>인사</span><span>구매·자재</span><span>영업</span></nav>
 <span class="who">__COMPANY__ · <b>경리팀 김한빛</b> (__UID__) <a href="/logout">로그아웃</a></span>
</div>
<div class="wrap">
 <aside>
  <h3>회계관리</h3>
  <a href="#">전표처리현황</a>
  <a href="#" class="on">매입전표등록</a>
  <a href="#">매출전표등록</a>
  <a href="#">전표승인/결재</a>
  <h3>기초정보</h3>
  <a href="#">거래처등록</a>
  <a href="#">계정과목관리</a>
  <a href="#">부서/프로젝트</a>
  <h3>결산·보고</h3>
  <a href="#">월별매입집계</a>
  <a href="#">부가세신고자료</a>
  <a href="#">시산표</a>
 </aside>
 <main>
  <div class="crumb">회계 &gt; 전표관리 &gt; <b>매입전표등록</b> · 화면ID FI-AP-110</div>

  <div class="panel">
   <div class="hd">매입전표등록 <span class="tag">전자입력 · RPA 연동</span></div>
   <div class="toolbar">
    <button type="button">조회</button><button type="button">신규</button>
    <button type="button">인쇄</button><button type="button">엑셀다운</button>
    <span class="sp"></span><span class="meta">기준회계기간: 2026 회계연도 · 통화 KRW</span>
   </div>
   <div class="grid">
    <div style="overflow:auto">
     <table class="data" id="vlist">
      <thead><tr>
       <th>전표번호</th><th>전표일자</th><th>거래처</th><th>사업자번호</th>
       <th class="num">공급가+세액</th><th class="num">세액</th><th>적요</th>
      </tr></thead>
      <tbody><tr><td colspan="7" class="empty">조회된 전표가 없습니다</td></tr></tbody>
      <tfoot><tr><td colspan="4">합계</td><td class="num" id="tot">0</td><td class="num" id="totv">0</td><td></td></tr></tfoot>
     </table>
    </div>
    <form class="reg" id="voucher">
     <label>전표유형</label>
     <select><option>51 매입(세금계산서)</option><option>52 매입(계산서)</option><option>53 매입(카드/현금영수증)</option></select>
     <label for="vendor">거래처명 <span class="req">*</span></label><input id="vendor" required>
     <div class="row">
      <div><label for="business_number">사업자등록번호</label><input id="business_number" placeholder="000-00-00000"></div>
      <div><label for="date">전표일자 <span class="req">*</span></label><input id="date" placeholder="YYYY-MM-DD" required></div>
     </div>
     <div class="row">
      <div><label for="total_amount">공급가액+세액 <span class="req">*</span></label><input id="total_amount" inputmode="numeric" required></div>
      <div><label for="vat">세액</label><input id="vat" inputmode="numeric"></div>
     </div>
     <label for="summary">적요</label><input id="summary">
     <button id="submit" type="submit">전표저장 (F8)</button>
     <div id="result"></div>
    </form>
   </div>
  </div>
 </main>
</div>
<div class="statusbar"><span>서버: HB-ERP-PRD01</span><span>회사: __COMPANY__ (법인 110111-HB267)</span><span>사용자: __UID__</span><span id="clock"></span></div>
<script>
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const won = (n) => n == null ? '' : Number(n).toLocaleString('ko-KR');
let known = new Set();
async function loadList(highlight) {
  const res = await fetch('/api/vouchers');
  if (res.status === 401) { location.href = '/login'; return; }
  const rows = await res.json();
  const tbody = document.querySelector('#vlist tbody');
  document.getElementById('tot').textContent = won(rows.reduce((a, v) => a + (v.total_amount || 0), 0));
  document.getElementById('totv').textContent = won(rows.reduce((a, v) => a + (v.vat || 0), 0));
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="7" class="empty">조회된 전표가 없습니다</td></tr>'; return; }
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
  if (res.ok) { out.dataset.voucher = data.voucher_no; out.textContent = '저장 완료 · 전표번호 ' + data.voucher_no; loadList(true); }
  else { out.textContent = '저장 실패: ' + JSON.stringify(data.detail); }
});
setInterval(() => { document.getElementById('clock').textContent = new Date().toLocaleString('ko-KR'); }, 1000);
loadList(false);
setInterval(() => loadList(true), 3000);
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not _sid(request):
        return RedirectResponse("/login", status_code=303)
    return MAIN_PAGE.replace("__COMPANY__", COMPANY).replace("__PRODUCT__", PRODUCT).replace("__UID__", ERP_ID)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "external_erp"}


# favicon 등 잡다한 요청의 404 JSON 응답 정리용
@app.exception_handler(404)
def not_found(request, exc):
    return JSONResponse({"detail": "Not Found"}, status_code=404)
