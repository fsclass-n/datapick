"""발표자료 · README 화면 캡처 (운영 서비스 datapick.onrender.com, 공개 테스트 계정).

    .venv/Scripts/python docs/scripts/capture_screens.py

- 출력: docs/assets/screenshots/*.png (데스크톱 1440 기준 1.5배, 모바일 390 기준 2배)
- 일반 사용자 문서가 있어야 문서 처리 · 모니터링 화면이 채워진다 (docs/video/tools/record_demo.py 녹화 후 실행)
- 데모 ERP 캡처는 rpa/erp_typer.py 와 같은 셀렉터로 값을 입력하고 저장한다 (서버 메모리의 데모 전표 1건 추가)
- 브라우저: 설치된 Microsoft Edge (channel="msedge")
"""

import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rpa.erp_typer import FIELD_SELECTORS, RESULT_SELECTOR, SUBMIT_SELECTOR  # noqa: E402

SITE = "https://datapick.onrender.com"
API = "https://datapick-api.onrender.com"
OUT = ROOT / "docs" / "assets" / "screenshots"
HIDE = "::-webkit-scrollbar{width:0;height:0}"


def receipt_doc():
    req = urllib.request.Request(f"{API}/api/auth/login", method="POST", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"email": "user@datapick.io", "password": "User1234!"}).encode())
    token = json.load(urllib.request.urlopen(req, timeout=120))["access_token"]
    req = urllib.request.Request(f"{API}/api/documents", headers={"Authorization": f"Bearer {token}"})
    docs = json.load(urllib.request.urlopen(req, timeout=120))
    return next((d for d in docs if d["source_type"] == "pdf"), docs[0] if docs else None)


def login(page, kind):
    page.goto(f"{SITE}/login", wait_until="networkidle", timeout=120000)
    page.locator("button", has_text=kind).first.click()
    page.wait_for_url("**/dashboard", timeout=60000)
    page.wait_for_timeout(1000)
    page.locator("[aria-live=polite] .card").first.wait_for(state="detached", timeout=15000)  # 환영 토스트가 사라진 뒤 촬영
    page.wait_for_timeout(500)


def go(page, path, wait_text, delay=1800):
    page.evaluate("p => { history.pushState({}, '', p); dispatchEvent(new PopStateEvent('popstate')); }", path)
    page.get_by_text(wait_text).first.wait_for(timeout=60000)
    page.wait_for_timeout(delay)


def desktop(browser, height=900):
    ctx = browser.new_context(viewport={"width": 1440, "height": height}, device_scale_factor=1.5, locale="ko-KR")
    ctx.add_init_script(f"addEventListener('DOMContentLoaded', () => {{ const s = document.createElement('style'); s.textContent = `{HIDE}`; document.head.appendChild(s); }})")
    return ctx, ctx.new_page()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = receipt_doc()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")

        ctx, page = desktop(b)
        page.goto(f"{SITE}/login", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(1200)
        page.screenshot(path=OUT / "login.png")
        login(page, "일반 사용자")
        page.screenshot(path=OUT / "dashboard.png")
        ctx.close()

        ctx, page = desktop(b, 1080)
        login(page, "일반 사용자")
        go(page, f"/documents?id={doc['id']}" if doc else "/documents", "추출 결과 검수" if doc else "처리 내역")
        page.screenshot(path=OUT / "documents.png")
        ctx.close()

        ctx, page = desktop(b, 1000)
        login(page, "테스트 관리자")
        go(page, "/admin/monitoring", "AI 파싱 성공률", 2600)
        page.screenshot(path=OUT / "monitoring_top.png")
        page.evaluate("window.scrollTo(0, 820)")
        page.wait_for_timeout(1200)
        page.screenshot(path=OUT / "monitoring_charts.png")
        ctx.close()

        ctx, page = desktop(b)
        login(page, "테스트 관리자")
        go(page, "/admin/users", "회원 관리")
        page.screenshot(path=OUT / "admin_users.png")
        ctx.close()

        ctx = b.new_context(viewport={"width": 570, "height": 540}, device_scale_factor=2, locale="ko-KR")
        page = ctx.new_page()
        page.goto(f"{API}/erp-demo", wait_until="networkidle", timeout=120000)
        values = (doc or {}).get("parsed") or {}
        for key, selector in FIELD_SELECTORS.items():
            if values.get(key) not in (None, ""):
                page.fill(selector, str(values[key]))
        page.click(SUBMIT_SELECTOR)
        page.locator(RESULT_SELECTOR).wait_for(timeout=30000)
        page.wait_for_timeout(500)
        page.screenshot(path=OUT / "erp_demo.png")
        ctx.close()

        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="ko-KR",
                            is_mobile=True, has_touch=True)
        page = ctx.new_page()
        page.goto(f"{SITE}/login", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(1200)
        page.screenshot(path=OUT / "mobile_login.png")
        page.locator("button", has_text="일반 사용자").first.click()
        page.wait_for_url("**/dashboard", timeout=60000)
        page.locator("[aria-live=polite] .card").first.wait_for(state="detached", timeout=15000)
        page.wait_for_timeout(500)
        page.screenshot(path=OUT / "mobile_closed.png")
        page.get_by_role("button", name="메뉴 열기").click()
        page.wait_for_timeout(900)
        page.screenshot(path=OUT / "mobile_drawer.png")
        ctx.close()
        b.close()
    print("saved:", ", ".join(sorted(f.name for f in OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
