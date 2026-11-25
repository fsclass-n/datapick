"""datapick.onrender.com 시연 자동 녹화 (Playwright + Microsoft Edge, 1920x1080).

    .venv/Scripts/python docs/video/tools/record_demo.py [main|ext|compare|all]

- 화면은 Chrome DevTools 스크린캐스트(CDP)로 프레임마다 타임스탬프와 함께 저장 → 장면 표시와 같은 시계로 정확히 자름
- 일반 사용자 → 테스트 관리자(읽기 전용) 흐름을 한 페이지에서 앱 내부 이동으로 녹화 (전체 새로고침 없음)
- 외부 페이지(데모 ERP, 실제 API 응답, /docs, /api/health, GitHub Actions)는 따로 녹화하고 로딩이 끝난 뒤를 장면 시작으로 기록
- AI 해석·RPA 대기 시간은 marks 의 cuts 로 기록해 편집에서 잘라 냄
- 노란 원형 커서·클릭 링·시안 테두리 강조·주소 칩은 페이지 위에 덧씌운 요소 (화면 전체 딤 없음, 앱 코드 변경 없음)
- 운영 데이터 변경: 테스트 일반 사용자의 이전 시연 문서를 지우고 새로 2건(스캔 영수증 PDF, 청구 메일) 처리.
  테스트 관리자는 읽기 전용이라 쓰기 요청은 서버가 403 으로 거부
"""

import base64
import json
import shutil
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

from common import BUILD, ROOT, VIDEO, save_json
from video_scenes import SCENES

sys.path.insert(0, str(ROOT))
from rpa.erp_typer import FIELD_SELECTORS, RESULT_SELECTOR, SUBMIT_SELECTOR  # noqa: E402  같은 셀렉터 맵으로 재현

SITE = "https://datapick.onrender.com"
API = "https://datapick-api.onrender.com"
USER = {"email": "user@datapick.io", "password": "User1234!"}
TEST_ADMIN = {"email": "admin@datapick.io", "password": "Admin1234!"}
RECEIPT = VIDEO / "assets" / "sample_receipt_scan.pdf"
RECEIPT_NAME = "스캔영수증_브런치카페퀼_1117.pdf"
REVIEWED_SUMMARY = "역삼점 팀 점심 식대"
DUR = {s["id"]: s["dur"] for s in SCENES}
REC = BUILD / "rec"

OVERLAY_JS = r"""
(() => {
  const css = `
    #__cur{position:fixed;left:-100px;top:-100px;width:38px;height:38px;margin:-19px 0 0 -19px;border-radius:50%;
      background:rgba(245,197,24,.28);border:2px solid rgba(245,197,24,.95);box-shadow:0 0 10px rgba(245,197,24,.35);
      pointer-events:none;z-index:2147483647}
    .__ring{position:fixed;width:38px;height:38px;margin:-19px 0 0 -19px;border-radius:50%;border:3px solid #F5C518;
      pointer-events:none;z-index:2147483647;animation:__ring .6s ease-out forwards}
    @keyframes __ring{from{transform:scale(.6);opacity:1}to{transform:scale(2.3);opacity:0}}
    .__hl{position:fixed;border:3px solid #22d3ee;border-radius:14px;box-shadow:0 0 16px rgba(34,211,238,.45);
      pointer-events:none;z-index:2147483646;opacity:0;transition:opacity .3s ease}
    .__chip{position:fixed;left:50%;top:84px;transform:translateX(-50%);padding:10px 22px;border-radius:999px;
      background:rgba(15,23,42,.92);color:#fff;font:600 20px/1.2 Consolas,'Malgun Gothic',monospace;
      pointer-events:none;z-index:2147483646;opacity:0;transition:opacity .3s ease}
    main{min-height:100vh}
    ::-webkit-scrollbar{width:0;height:0}`;
  const boot = () => {
    if (document.getElementById('__cur')) return;
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    const cur = document.createElement('div'); cur.id = '__cur'; document.body.appendChild(cur);
    addEventListener('mousemove', e => { cur.style.left = e.clientX + 'px'; cur.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => {
      const r = document.createElement('div'); r.className = '__ring';
      r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
      document.body.appendChild(r); setTimeout(() => r.remove(), 700);
    }, true);
    window.__hl = (x, y, w, h, ms) => {
      const d = document.createElement('div'); d.className = '__hl';
      Object.assign(d.style, {left: x + 'px', top: y + 'px', width: w + 'px', height: h + 'px'});
      document.body.appendChild(d); requestAnimationFrame(() => d.style.opacity = 1);
      setTimeout(() => { d.style.opacity = 0; setTimeout(() => d.remove(), 350); }, ms);
    };
    window.__chip = (text, ms) => {
      const d = document.createElement('div'); d.className = '__chip'; d.textContent = text;
      document.body.appendChild(d); requestAnimationFrame(() => d.style.opacity = 1);
      setTimeout(() => { d.style.opacity = 0; setTimeout(() => d.remove(), 350); }, ms);
    };
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', boot); else boot();
})();
"""


class Recorder:
    def __init__(self, page, ctx, name):
        self.page, self.name = page, name
        self.dir = REC / name
        shutil.rmtree(self.dir, ignore_errors=True)
        (self.dir / "frames").mkdir(parents=True)
        self.frames = []
        self.t0 = time.time()
        self.marks, self.cur = {}, None
        self.mx, self.my = 960, 700
        self.cdp = ctx.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._on_frame)
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 88, "maxWidth": 1920, "maxHeight": 1080})

    def _on_frame(self, params) -> None:
        self.cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        name = f"frames/{len(self.frames):06d}.jpg"
        (self.dir / name).write_bytes(base64.b64decode(params["data"]))
        self.frames.append([round(params["metadata"]["timestamp"] - self.t0, 4), name])

    def stop(self) -> None:
        self.wait(0.5)
        self.cdp.send("Page.stopScreencast")

    def now(self) -> float:
        return time.time() - self.t0

    def wait(self, sec: float) -> None:
        self.page.wait_for_timeout(int(sec * 1000))

    # ---------------------------------------------------------- scene timing
    def begin(self, sid: str) -> None:
        self.cur = sid
        self.marks[sid] = {"start": round(self.now(), 3), "cuts": []}
        print(f"  ▶ {sid} @ {self.marks[sid]['start']:.1f}s")

    def effective(self) -> float:
        m = self.marks[self.cur]
        return self.now() - m["start"] - sum(b - a for a, b in m["cuts"])

    def end(self) -> None:
        used = self.effective()
        if used > DUR[self.cur]:
            print(f"    !! {self.cur}: 동작 {used:.1f}s 가 장면 {DUR[self.cur]}s 를 넘습니다 (끝부분이 잘림)")
        remain = DUR[self.cur] + 0.25 - used
        if remain > 0:
            self.wait(remain)
        self.marks[self.cur]["end"] = round(self.now(), 3)

    def cut_wait(self, fn, keep_before=0.8, keep_after=0.6):
        """fn 이 끝날 때까지 기다리고, 그 사이 대기 구간은 편집에서 잘라 내도록 기록."""
        a = self.now() + keep_before
        result = fn()
        b = self.now() - keep_after
        if b > a:
            self.marks[self.cur]["cuts"].append([round(a, 3), round(b, 3)])
        return result

    # ---------------------------------------------------------- cursor / emphasis
    def glide(self, x: float, y: float, ms: int = 700) -> None:
        """시간 기준 이동: 호출 오버헤드와 무관하게 항상 ms 동안 부드럽게 이동."""
        sx, sy, t0 = self.mx, self.my, time.monotonic()
        while True:
            t = min(1.0, (time.monotonic() - t0) * 1000 / ms)
            e = t * t * (3 - 2 * t)
            self.page.mouse.move(sx + (x - sx) * e, sy + (y - sy) * e)
            if t >= 1.0:
                break
        self.mx, self.my = x, y

    def center(self, loc):
        loc.scroll_into_view_if_needed()
        b = loc.bounding_box()
        return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

    def point(self, loc, pause: float = 0.8, rest_offset=None) -> None:
        x, y = self.center(loc)
        self.glide(x, y)
        self.wait(pause)
        if rest_offset:  # 말하는 동안 글자를 가리지 않도록 오른쪽 아래 여백으로 이동
            self.glide(x + rest_offset[0], y + rest_offset[1], 450)

    def click(self, loc, pause: float = 0.8) -> None:
        x, y = self.center(loc)
        self.glide(x, y)
        self.wait(pause)
        self.page.mouse.click(x, y)
        self.wait(0.5)

    def type(self, loc, text: str, delay: int = 110) -> None:
        self.click(loc, 0.4)
        loc.press_sequentially(text, delay=delay)

    def hl(self, loc, ms: int = 2600, pad: int = 8) -> None:
        loc.scroll_into_view_if_needed()
        b = loc.bounding_box()
        self.page.evaluate("([x,y,w,h,ms]) => window.__hl(x,y,w,h,ms)",
                           [b["x"] - pad, b["y"] - pad, b["width"] + pad * 2, b["height"] + pad * 2, ms])

    def chip(self, text: str, ms: int = 3000) -> None:
        self.page.evaluate("([t,ms]) => window.__chip(t,ms)", [text, ms])

    def soft(self, fn, *args, **kw) -> None:
        """보조 연출(토스트 강조 등)은 요소가 이미 사라졌으면 건너뛴다."""
        try:
            args[0].wait_for(state="visible", timeout=2500)
            fn(*args, **kw)
        except Exception:  # noqa: BLE001
            print("    (skip optional emphasis)")

    def scroll(self, dy: int) -> None:
        self.page.evaluate("dy => window.scrollBy({top: dy, behavior: 'smooth'})", dy)
        self.wait(0.9)

    def scroll_to(self, loc, offset: int = 110) -> None:
        """요소가 헤더 아래 보이도록 부드럽게 스크롤."""
        top = loc.evaluate("el => el.getBoundingClientRect().top + window.scrollY")
        self.page.evaluate("y => window.scrollTo({top: y, behavior: 'smooth'})", max(0, top - offset))
        self.wait(0.9)


def new_context(browser):
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="ko-KR", color_scheme="light")
    ctx.add_init_script(OVERLAY_JS)
    return ctx


def finish(ctx, page, rec, name):
    rec.stop()
    ctx.close()
    save_json(REC / f"{name}.json", {"dir": str(rec.dir), "frames": rec.frames, "scenes": rec.marks})
    print(f"  saved {name}: {len(rec.frames)} frames")


# ====================================================================== API helpers
def api(path, method="GET", body=None, token=None, timeout=180):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read()
            return res.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def login(account) -> str:
    status, data = api("/api/auth/login", "POST", account)
    assert status == 200, (status, data)
    return data["access_token"]


def clear_user_documents():
    """공개 테스트 일반 사용자의 이전 시연 문서를 정리 (녹화를 다시 해도 같은 화면이 나오도록)."""
    token = login(USER)
    _, docs = api("/api/documents", token=token)
    for d in docs:
        api(f"/api/documents/{d['id']}", "DELETE", token=token)
    print(f"  cleared {len(docs)} demo document(s)")


def warm_up():
    for url in (f"{API}/api/health", f"{SITE}/", f"{API}/erp-demo", f"{API}/docs"):
        for _ in range(4):
            try:
                urllib.request.urlopen(url, timeout=120).read()
                break
            except Exception:  # noqa: BLE001
                time.sleep(5)


def toast(page, text):
    return page.locator("[aria-live=polite] .card", has_text=text).last


# ====================================================================== main flow (일반 사용자 → 테스트 관리자)
def record_main(browser):
    clear_user_documents()
    ctx = new_context(browser)
    page = ctx.new_page()
    r = Recorder(page, ctx, "main")
    page.goto(f"{SITE}/", wait_until="load", timeout=120000)
    page.locator("div[role='tablist']").wait_for(timeout=90000)
    r.wait(1.5)
    header = page.locator("header").first
    nav = page.locator("nav[aria-label='주 메뉴']")

    # d00 메인(비로그인)
    r.begin("d00")
    r.glide(520, 330, 600)
    r.hl(page.locator("h1").first, 3000)
    r.wait(3.2)
    mock = page.locator("div[role='tablist']").locator("xpath=..")
    r.hl(mock, 4600)
    r.point(mock, 1.2, rest_offset=(330, 240))
    r.end()

    # d01 로그인 화면 → 회원가입 비밀번호 규칙
    r.begin("d01")
    r.click(header.get_by_role("link", name="로그인"))
    r.cut_wait(lambda: page.get_by_text("다시 오신 것을 환영합니다").wait_for(timeout=60000))
    r.wait(0.6)
    quick = page.locator("div.grid", has=page.locator("button", has_text="일반 사용자")).first
    r.hl(quick, 3800)
    r.point(quick, 3.0, rest_offset=(0, 140))
    r.click(page.locator("main p button", has_text="회원가입"), 0.6)
    pw = page.get_by_placeholder("영문 대·소문자, 숫자, 특수문자 8자 이상")
    pw.wait_for(timeout=10000)
    r.type(pw, "data", 160)
    r.hl(page.locator("#password-rules"), 5600)
    r.wait(0.5)
    pw.press_sequentially("Pick2026!", delay=230)
    r.wait(2.0)
    r.click(page.locator("main p button", has_text="로그인"), 0.5)
    r.end()

    # d02 일반 사용자 테스트 로그인
    r.begin("d02")
    r.click(page.locator("button", has_text="일반 사용자").first, 1.0)
    page.wait_for_url("**/dashboard", timeout=60000)
    r.cut_wait(lambda: page.get_by_text("안녕하세요", exact=False).first.wait_for(timeout=60000))
    r.wait(0.8)
    r.hl(nav, 3400)
    r.point(nav, 2.0, rest_offset=(0, 120))
    r.end()

    # d03 스캔 영수증 PDF 업로드 → Gemini 멀티모달 해석
    r.begin("d03")
    r.click(nav.get_by_role("link", name="문서 자동 입력"))
    drop = page.get_by_text("파일을 끌어다 놓거나 클릭해서 선택").locator("xpath=ancestor::div[contains(@class,'border-dashed')][1]")
    drop.wait_for(timeout=60000)
    r.wait(0.5)
    r.hl(drop, 3200)
    r.point(drop, 2.6)
    payload = {"name": RECEIPT_NAME, "mimeType": "application/pdf", "buffer": RECEIPT.read_bytes()}
    chosen = []
    page.once("filechooser", lambda chooser: (chooser.set_files(payload), chosen.append(True)))
    r.click(drop, 0.6)
    r.wait(0.8)
    if not chosen:  # 파일 선택 창 이벤트가 오지 않으면 같은 입력 요소에 직접 지정 (앱의 onChange 그대로 실행)
        page.locator("input[type=file]").set_input_files(payload)
    r.wait(1.6)  # 'AI가 문서를 해석하고 있습니다…' 표시 구간
    r.cut_wait(lambda: toast(page, "해석 완료").wait_for(timeout=240000), 1.4, 0.4)
    detail = page.locator("section.card", has_text="추출 결과 검수")
    detail.wait_for(timeout=30000)
    r.wait(0.6)
    r.soft(r.hl, toast(page, "해석 완료"), 2400)
    r.wait(1.0)
    r.hl(detail, 3200)
    r.end()

    # d04 추출 결과: 필드 · 파서/신뢰도 · 품목
    r.begin("d04")
    fields = detail.locator("div.grid").first
    r.hl(fields, 5600)
    r.point(fields, 4.6, rest_offset=(260, 210))
    meta = detail.locator("p", has_text="신뢰도").first
    r.hl(meta, 3600)
    r.point(meta, 2.8, rest_offset=(120, 70))
    items = detail.locator("table").first
    r.scroll_to(items, 260)
    r.hl(items, 4400)
    r.point(items, 3.6, rest_offset=(220, 110))
    r.end()

    # d05 사람 검수: 적요 수정 → 검수 저장 (서버 재검증)
    r.begin("d05")
    summary = detail.locator("label", has_text="적요").locator("input")
    r.scroll_to(summary, 300)
    r.click(summary, 0.4)
    page.keyboard.press("Control+A")
    summary.press_sequentially(REVIEWED_SUMMARY, delay=120)
    r.wait(0.6)
    r.click(detail.get_by_role("button", name="검수 저장"), 0.6)
    toast(page, "검수 내용을 저장했습니다").wait_for(timeout=60000)
    r.wait(0.3)
    r.soft(r.hl, toast(page, "검수 내용을 저장했습니다"), 2800)
    r.end()

    # d06 RPA: 엑셀 원장 적재 → ERP 자동 타이핑(전표번호)
    r.begin("d06")
    rpa_box = detail.locator("div.rounded-xl", has_text="RPA 자동 입력").last
    r.scroll_to(rpa_box, 260)
    r.hl(rpa_box, 2600)
    r.click(rpa_box.get_by_role("button", name="엑셀 원장 적재"), 0.7)
    r.cut_wait(lambda: toast(page, "엑셀 원장에 적재").wait_for(timeout=120000), 0.8, 0.3)
    r.wait(2.6)
    r.click(rpa_box.get_by_role("button", name="ERP 자동 타이핑"), 0.7)
    r.wait(1.2)
    r.cut_wait(lambda: toast(page, "전표번호").wait_for(timeout=180000), 0.8, 0.3)
    r.wait(0.4)
    jobs = rpa_box.locator("ul").first
    jobs.wait_for(timeout=30000)
    r.soft(r.hl, toast(page, "전표번호"), 3000)
    r.wait(0.8)
    r.hl(jobs, 4400)
    r.point(jobs.locator("li").first, 2.4, rest_offset=(160, 90))
    r.end()

    # d08 이메일 본문 → AI 해석
    r.begin("d08")
    r.scroll(-2000)
    r.click(page.get_by_role("button", name="이메일 본문"), 0.5)
    r.click(page.get_by_role("button", name="샘플 채우기"), 0.5)
    r.hl(page.locator("textarea"), 2800)
    r.wait(1.6)
    r.click(page.get_by_role("button", name="AI 해석 실행"), 0.6)
    r.wait(1.4)
    r.cut_wait(lambda: toast(page, "청구 메일' 해석 완료").wait_for(timeout=180000), 0.8, 0.4)
    page.locator("section.card", has_text="추출 결과 검수").get_by_text("11월 클라우드 청구 메일").first.wait_for(timeout=30000)
    r.wait(0.6)
    detail2 = page.locator("section.card", has_text="추출 결과 검수")
    r.hl(detail2.locator("div.grid").first, 3600)
    r.point(detail2.locator("div.grid").first, 2.6, rest_offset=(240, 200))
    r.end()

    # d09 대시보드 집계
    r.begin("d09")
    r.click(nav.get_by_role("link", name="대시보드"))
    kpis = page.locator("main div.grid").first
    r.cut_wait(lambda: kpis.wait_for(timeout=60000))
    r.wait(1.0)
    r.hl(kpis, 3800)
    r.point(kpis, 3.0, rest_offset=(260, 200))
    r.end()

    # d10 일반 사용자 → /admin/users 직접 접근 → 대시보드로 되돌림
    r.begin("d10")
    r.hl(nav, 2600)
    r.point(nav, 2.0)
    r.chip("주소 입력  →  /admin/users", 3600)
    r.wait(1.2)
    page.evaluate("() => { history.pushState({}, '', '/admin/users'); dispatchEvent(new PopStateEvent('popstate')); }")
    page.wait_for_url("**/dashboard", timeout=15000)
    r.wait(1.0)
    r.chip("관리자 전용  →  /dashboard 로 이동", 4200)
    r.hl(nav, 3600)
    r.glide(1300, 640, 600)
    r.end()

    # d11 로그아웃
    r.begin("d11")
    r.click(header.get_by_role("button", name="로그아웃"), 0.6)
    page.wait_for_timeout(800)
    if "/login" not in page.url:
        page.evaluate("() => { history.pushState({}, '', '/login'); dispatchEvent(new PopStateEvent('popstate')); }")
    r.cut_wait(lambda: page.get_by_text("다시 오신 것을 환영합니다").wait_for(timeout=60000))
    r.end()

    # a00 테스트 관리자 로그인 → 읽기 전용 배너 · 관리자 메뉴
    r.begin("a00")
    r.click(page.locator("button", has_text="테스트 관리자").first, 0.8)
    page.wait_for_url("**/dashboard", timeout=60000)
    banner = page.get_by_text("테스트 관리자 모드 · 읽기 전용").first
    r.cut_wait(lambda: banner.wait_for(timeout=60000))
    r.wait(0.6)
    r.hl(nav, 3000)
    r.point(nav.get_by_role("link", name="모니터링"), 2.2)
    r.hl(banner.locator("xpath=.."), 3400)
    r.point(banner, 1.8, rest_offset=(260, 80))
    r.end()

    # a01 모니터링 대시보드
    r.begin("a01")
    r.click(nav.get_by_role("link", name="모니터링"))
    r.cut_wait(lambda: page.get_by_text("AI 파싱 성공률").first.wait_for(timeout=60000))
    r.wait(1.2)
    cards = page.locator("main div.grid").first
    r.hl(cards, 3600)
    r.point(cards, 3.0, rest_offset=(260, 160))
    gauges = page.locator(".card", has_text="AI 파싱 성공률").first.locator("xpath=..")
    r.scroll_to(gauges, 120)
    r.hl(gauges, 4200)
    r.point(gauges, 3.4, rest_offset=(300, 200))
    daily = page.locator("section.card", has_text="일별 AI 파싱 결과").first.locator("xpath=..")
    r.scroll_to(daily, 120)
    r.hl(daily, 3800)
    r.wait(3.4)
    dist = page.locator("section.card", has_text="파서 엔진").first.locator("xpath=..")
    r.scroll_to(dist, 160)
    r.hl(dist, 3600)
    r.end()

    # a02 회원 관리: 검색 · 권한 필터 · 잠긴 권한 스위치
    r.begin("a02")
    r.scroll(-3000)
    r.click(nav.get_by_role("link", name="회원 관리"))
    search = page.get_by_placeholder("이름 또는 이메일 검색")
    r.cut_wait(lambda: search.wait_for(timeout=60000))
    r.wait(0.5)
    r.type(search, "datapick", 130)
    r.wait(1.2)
    role = page.get_by_label("권한 필터")
    r.click(role, 0.5)
    options = role.locator("option").all_inner_texts()
    role.select_option(index=min(2, len(options) - 1))
    r.wait(1.6)
    role.select_option(index=0)
    r.wait(1.0)
    toggles = page.locator("button[aria-label$='관리자 권한']")
    r.hl(toggles.first.locator("xpath=ancestor::table[1]"), 4200)
    r.point(toggles.first, 2.4, rest_offset=(-200, 90))
    r.end()

    # a03 문서 처리: 업로드 · 해석 비활성
    r.begin("a03")
    r.click(nav.get_by_role("link", name="문서 자동 입력"))
    drop = page.get_by_text("파일을 끌어다 놓거나 클릭해서 선택").locator("xpath=ancestor::div[contains(@class,'border-dashed')][1]")
    r.cut_wait(lambda: drop.wait_for(timeout=60000))
    r.wait(0.4)
    r.hl(drop, 3200)
    r.point(drop, 2.6)
    r.click(page.get_by_role("button", name="이메일 본문"), 0.5)
    run_btn = page.get_by_role("button", name="AI 해석 실행")
    r.hl(run_btn, 3000)
    r.point(run_btn, 2.0, rest_offset=(-160, 80))
    r.end()

    # a05 운영 관리자 로그인 화면 (토큰 입력, 제출하지 않음)
    r.begin("a05")
    r.chip("주소 입력  →  /admin/login", 2600)
    r.wait(0.8)
    page.evaluate("() => { window.scrollTo(0, 0); history.pushState({}, '', '/admin/login'); dispatchEvent(new PopStateEvent('popstate')); }")
    token_input = page.locator("main input").first
    r.cut_wait(lambda: token_input.wait_for(timeout=30000))
    r.wait(0.8)
    form = token_input.locator("xpath=ancestor::form[1]")
    r.hl(form, 4600)
    r.point(token_input, 3.0, rest_offset=(220, 120))
    r.end()
    finish(ctx, page, r, "main")


# ====================================================================== 외부 페이지
def latest_receipt_values() -> dict:
    token = login(USER)
    _, docs = api("/api/documents", token=token)
    receipt = next((d for d in docs if d["filename"] == RECEIPT_NAME and d.get("parsed")), None)
    if receipt:
        return receipt["parsed"]
    return {"vendor": "브런치카페 퀼 역삼점", "business_number": "214-86-12345", "date": "2026-11-17",
            "total_amount": 31000, "vat": 2818, "summary": REVIEWED_SUMMARY}


PROOF_CSS = """body{margin:0;background:#f8fafc;color:#0f172a;font-family:'Malgun Gothic',sans-serif;padding:70px 140px}
.k{color:#4f46e5;font-weight:700;letter-spacing:.25em;font-size:18px}
h1{font-size:42px;margin:10px 0 34px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:20px;padding:26px 32px;margin-bottom:26px;box-shadow:0 8px 24px rgba(15,23,42,.06)}
.who{font-size:20px;color:#64748b;margin-bottom:10px}
.req{font:600 26px/1.4 Consolas,monospace;color:#1e1b4b}
.res{font:24px/1.5 Consolas,'Malgun Gothic',monospace;margin-top:14px;padding:14px 18px;border-radius:12px;background:#fff1f2;color:#be123c}
.code{display:inline-block;background:#e11d48;color:#fff;border-radius:8px;padding:2px 12px;margin-right:12px;font-weight:700}
.note{color:#64748b;font-size:19px;margin-top:6px}"""


def proof_html() -> str:
    """실제 운영 API 를 호출한 응답을 그대로 보여 주는 페이지 (값을 가공하지 않음)."""
    user_token, admin_token = login(USER), login(TEST_ADMIN)
    _, users = api("/api/admin/users", token=admin_token)
    target = next(u for u in users if u["email"] == USER["email"])
    s1, b1 = api("/api/admin/users", token=user_token)
    s2, b2 = api(f"/api/admin/users/{target['id']}/role", "PATCH", {"role": "admin"}, token=admin_token)
    assert s1 == 403 and s2 == 403, (s1, b1, s2, b2)
    esc = lambda o: json.dumps(o, ensure_ascii=False).replace("&", "&amp;").replace("<", "&lt;")
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>{PROOF_CSS}</style></head><body>
<div class="k">SERVER-SIDE AUTHORIZATION</div><h1>화면이 아니라 서버가 거부합니다</h1>
<div class="card" id="c1"><div class="who">일반 사용자 토큰 (user@datapick.io)</div>
<div class="req">GET {API}/api/admin/users</div>
<div class="res"><span class="code">{s1}</span>{esc(b1)}</div></div>
<div class="card" id="c2"><div class="who">테스트 관리자 토큰 (admin@datapick.io)</div>
<div class="req">PATCH {API}/api/admin/users/{target['id']}/role  {{"role": "admin"}}</div>
<div class="res"><span class="code">{s2}</span>{esc(b2)}</div></div>
<div class="note">녹화 시점에 운영 서버를 실제로 호출한 응답입니다. (backend/app/deps.py · require_admin / get_current_user)</div>
</body></html>"""


def record_external(browser):
    # d07 데모 ERP 화면에서 RPA 입력 재현 (rpa/erp_typer.py 와 같은 셀렉터 맵 · 같은 대상 화면)
    values = latest_receipt_values()
    ctx = new_context(browser)
    page = ctx.new_page()
    r = Recorder(page, ctx, "erp")
    page.goto(f"{API}/erp-demo", wait_until="load", timeout=120000)
    page.locator(SUBMIT_SELECTOR).wait_for(timeout=60000)
    page.add_style_tag(content="body{zoom:1.35}")
    r.wait(1.2)
    r.begin("d07")
    r.hl(page.locator("form").first, 2400)
    r.wait(0.8)
    for key, selector in FIELD_SELECTORS.items():  # erp_typer.type_record 와 같은 순서 · 같은 셀렉터
        value = values.get(key)
        if value in (None, ""):
            continue
        x, y = r.center(page.locator(selector))
        r.glide(x, y, 350)
        page.mouse.click(x, y)
        page.locator(selector).press_sequentially(str(value), delay=32)
        r.wait(0.15)
    r.click(page.locator(SUBMIT_SELECTOR), 0.5)
    result = page.locator(RESULT_SELECTOR)
    result.wait_for(timeout=30000)
    r.wait(0.4)
    r.hl(result, 4200)
    r.point(result, 2.4, rest_offset=(260, 60))
    r.end()
    finish(ctx, page, r, "erp")

    # a04 실제 API 응답(403) 페이지
    ctx = new_context(browser)
    page = ctx.new_page()
    r = Recorder(page, ctx, "proof")
    page.set_content(proof_html(), wait_until="load")
    page.evaluate(OVERLAY_JS)
    r.wait(1.0)
    r.begin("a04")
    r.glide(900, 300, 600)
    r.hl(page.locator("#c1"), 4600)
    r.point(page.locator("#c1 .res"), 3.4, rest_offset=(420, 60))
    r.hl(page.locator("#c2"), 4800)
    r.point(page.locator("#c2 .res"), 3.4, rest_offset=(420, 60))
    r.end()
    finish(ctx, page, r, "proof")

    # s01 API 문서
    ctx = new_context(browser)
    page = ctx.new_page()
    r = Recorder(page, ctx, "docs")
    page.goto(f"{API}/docs", wait_until="load", timeout=120000)
    page.locator(".opblock-tag").first.wait_for(timeout=60000)
    r.wait(1.5)
    r.begin("s01")
    r.hl(page.locator(".info"), 2400)
    r.glide(900, 300, 600)
    r.wait(1.2)
    for tag in ("auth", "documents", "admin"):
        loc = page.locator(f".opblock-tag[data-tag='{tag}']")
        page.evaluate("el => el.scrollIntoView({behavior:'smooth', block:'start'})", loc.element_handle())
        r.wait(1.0)
        r.hl(loc.locator("xpath=.."), 2600)
        r.point(loc, 1.4)
    r.end()
    finish(ctx, page, r, "docs")

    # s02 /api/health (JSON 을 읽기 좋게 들여쓰기만 적용, 값은 그대로)
    ctx = new_context(browser)
    page = ctx.new_page()
    r = Recorder(page, ctx, "health")
    page.goto(f"{API}/api/health", wait_until="load", timeout=120000)
    page.evaluate("""(api) => {
      const data = JSON.parse(document.body.innerText);
      document.body.innerHTML = '';
      Object.assign(document.body.style, {margin: 0, background: '#0f172a', color: '#e2e8f0',
        font: '38px/1.5 Consolas, monospace', padding: '150px 180px'});
      const h = document.createElement('div'); h.textContent = 'GET ' + api + '/api/health';
      Object.assign(h.style, {color: '#94a3b8', fontSize: '28px', marginBottom: '30px'});
      const pre = document.createElement('pre'); pre.id = 'json'; pre.textContent = JSON.stringify(data, null, 2);
      pre.style.margin = 0; document.body.append(h, pre);
    }""", API)
    page.evaluate(OVERLAY_JS)
    r.wait(1.0)
    r.begin("s02")
    r.glide(760, 360, 600)
    r.hl(page.locator("#json"), 4200)
    r.wait(4.4)
    r.end()
    finish(ctx, page, r, "health")

    record_actions(browser)


def record_actions(browser):
    # s03 GitHub Actions
    ctx = new_context(browser)
    page = ctx.new_page()
    r = Recorder(page, ctx, "actions")
    page.goto("https://github.com/fsclass-n/datapick/actions", wait_until="load", timeout=120000)
    page.locator("a[href*='/actions/runs/']").first.wait_for(timeout=60000)
    r.wait(1.5)
    r.begin("s03")
    runs = page.locator("[id^='check_suite_']")
    target = runs.first if runs.count() else page.locator("a[href*='/actions/runs/']").first
    r.hl(target, 4000)
    r.point(target, 3.0, rest_offset=(360, 60))
    if runs.count() > 1:
        r.hl(runs.nth(1), 2600)
    r.end()
    finish(ctx, page, r, "actions")


# ====================================================================== 계정 비교 카드 (정지 이미지)
COMPARE_HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
body{margin:0;width:1920px;height:1080px;background:radial-gradient(1100px 560px at 8% -10%,#4f46e526,transparent 60%),#f8fafc;
 color:#0f172a;font-family:'Malgun Gothic',sans-serif;display:flex;flex-direction:column;justify-content:center;padding:0 150px;box-sizing:border-box}
.k{color:#4f46e5;font-weight:700;letter-spacing:.3em;font-size:22px}
h1{font-size:58px;margin:14px 0 44px}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:29px;border:1px solid #e2e8f0;border-radius:22px;overflow:hidden;background:#fff;
 box-shadow:0 12px 32px rgba(15,23,42,.08)}
th,td{padding:24px 30px;text-align:left;border-bottom:1px solid #e2e8f0}
th{background:#eef2ff;color:#3730a3;font-size:26px}
tr:last-child td{border-bottom:0} td:first-child{font-weight:700;width:330px}
.y{color:#059669;font-weight:700}.n{color:#e11d48;font-weight:700}.m{color:#64748b;font-size:24px}
</style></head><body>
<div class="k">ACCOUNT COMPARISON</div><h1>하나의 로그인, 역할에 따른 화면 · API 분리</h1>
<table><tr><th>기능</th><th>일반 사용자</th><th>테스트 관리자</th><th>운영 관리자</th></tr>
<tr><td>문서 업로드 · AI 해석 · 검수</td><td class="y">본인 문서</td><td class="n">비활성 · 서버 403</td><td class="y">가능</td></tr>
<tr><td>엑셀 적재 · ERP 자동 타이핑</td><td class="y">본인 문서</td><td class="n">비활성 · 서버 403</td><td class="y">가능</td></tr>
<tr><td>회원 관리 · 모니터링 화면</td><td class="n">대시보드로 이동 · API 403</td><td class="y">조회만</td><td class="y">가능</td></tr>
<tr><td>회원 권한 변경</td><td class="n">—</td><td class="n">서버 403 거부</td><td class="y">가능 (본인 강등 · 공개 계정 보호)</td></tr>
<tr><td>로그인 방식</td><td class="m">가입 · OAuth · 테스트 버튼</td><td class="m">테스트 버튼 (공개 계정)</td><td class="m">ADMIN_TOKEN · 5회 실패 시 10분 차단</td></tr>
</table></body></html>"""


def render_compare(browser):
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.set_content(COMPARE_HTML)
    page.wait_for_timeout(500)
    page.screenshot(path=str(BUILD / "overlays" / "compare.png"))
    page.close()
    print("  saved compare.png")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    warm_up()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        if what in ("compare", "all"):
            render_compare(b)
        if what in ("main", "all"):
            record_main(b)
        if what in ("ext", "all"):
            record_external(b)
        if what == "actions":
            record_actions(b)
        b.close()
