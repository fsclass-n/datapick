"""samples/ 폴더의 시연용 샘플 문서를 생성한다.

실행: py -3.11 samples/make_samples.py  (PyMuPDF · Pillow 필요, 시스템 Python 기준)
모든 내용은 가상의 업체·금액이다.
"""

import io
import textwrap
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent
FONT = "C:/Windows/Fonts/malgun.ttf"
FONT_B = "C:/Windows/Fonts/malgunbd.ttf"
KST = timezone(timedelta(hours=9))

RECEIPT = {
    "vendor": "브런치카페 퀼 역삼점",
    "biz": "123-45-67890",
    "addr": "서울 강남구 테헤란로 123",
    "owner": "김퀼",
    "date": "2026.11.20 14:32",
    "items": [("아메리카노", 2, 4500), ("카페라떼", 1, 5500), ("크로플", 1, 6500)],
    "vat": 1909,
    "total": 21000,
    "pay": "신용카드",
}


def receipt_lines():
    lines = [
        RECEIPT["vendor"], f"사업자번호: {RECEIPT['biz']}", RECEIPT["addr"], f"대표: {RECEIPT['owner']}",
        f"{RECEIPT['date']}  영수증 No.0042", "-" * 34, "상품명          수량    단가     금액",
    ]
    for name, qty, price in RECEIPT["items"]:
        lines.append(f"{name:<10}{qty:>5}{price:>9,}{qty * price:>9,}")
    lines += [
        "-" * 34, f"과세금액: {RECEIPT['total'] - RECEIPT['vat']:,}원", f"부가세: {RECEIPT['vat']:,}원",
        f"합계: {RECEIPT['total']:,}원", f"결제수단: {RECEIPT['pay']}", "승인번호: 12345678",
    ]
    return lines


def make_text_pdf():
    doc = fitz.open()
    page = doc.new_page(width=300, height=430)
    page.insert_font(fontname="malgun", fontfile=FONT)
    page.insert_font(fontname="malgunb", fontfile=FONT_B)
    y = 24
    for i, line in enumerate(receipt_lines()):
        size, fontname = (11, "malgunb") if i == 0 else (8, "malgun")
        page.insert_text((24, y), line, fontsize=size, fontname=fontname)
        y += size + 12 if i == 0 else 16
    doc.subset_fonts()
    doc.save(OUT / "01_카페영수증_텍스트PDF.pdf", deflate=True)
    doc.close()


def receipt_image():
    img = Image.new("RGB", (620, 980), "white")
    d = ImageDraw.Draw(img)
    f_title, f_body, f_small = ImageFont.truetype(FONT_B, 34), ImageFont.truetype(FONT, 24), ImageFont.truetype(FONT, 20)
    y = 40
    for i, line in enumerate(receipt_lines()):
        f = f_title if i == 0 else (f_small if "승인번호" in line else f_body)
        w = d.textlength(line, font=f)
        d.text(((620 - w) / 2 if i == 0 else 40, y), line, fill="black", font=f)
        y += 48 if i == 0 else 40
    d.rectangle([14, 14, 606, 966], outline="gray", width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_scanned_pdf():
    img_bytes = receipt_image()
    doc = fitz.open()
    page = doc.new_page(width=620, height=980)
    page.insert_image(page.rect, stream=img_bytes)
    doc.save(OUT / "05_스캔영수증_이미지PDF.pdf", deflate=True)
    doc.close()
    (OUT / "06_영수증사진.png").write_bytes(img_bytes)


def make_eml():
    msg = EmailMessage()
    msg["From"] = "billing@cloudvendor.co.kr"
    msg["To"] = "account@acme.co.kr"
    msg["Subject"] = "[청구서] 11월 클라우드 워크스페이스 이용료 안내"
    msg["Date"] = datetime(2026, 11, 21, 9, 0, tzinfo=KST).strftime("%a, %d %b %Y %H:%M:%S %z")
    msg.set_content(
        "안녕하세요, (주)에이씨미 담당자님.\n\n"
        "11월분 클라우드 서비스 이용료를 아래와 같이 청구드립니다.\n\n"
        "거래처: 클라우드벤더(주)\n"
        "사업자번호: 220-81-99031\n"
        "청구일: 2026-11-21\n"
        "품목: 클라우드 워크스페이스 Standard 월 구독 x1\n"
        "공급가액: 300,000원\n"
        "부가세: 30,000원\n"
        "청구금액(합계): 330,000원\n"
        "결제수단: 계좌이체 (입금계좌: 국민은행 123-45-678901)\n"
        "입금기한: 2026-11-30\n\n"
        "감사합니다.\n클라우드벤더(주) 빌링팀\n"
    )
    (OUT / "02_클라우드청구메일.eml").write_bytes(bytes(msg))


def make_html():
    (OUT / "03_거래명세서.html").write_text(
        """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>거래명세서</title>
<style>body{font-family:'Malgun Gothic',sans-serif}table{border-collapse:collapse;width:100%}
th,td{border:1px solid #333;padding:6px 10px;text-align:center}th{background:#eee}.r{text-align:right}</style></head>
<body><h2>거래명세서</h2>
<table><tr><th>공급자</th><td>오피스디포 역삼점</td><th>사업자번호</th><td>214-86-11223</td></tr>
<tr><th>공급받는자</th><td>(주)에이씨미</td><th>거래일자</th><td>2026-11-22</td></tr></table>
<br><table><tr><th>품목</th><th>수량</th><th>단가</th><th>금액</th></tr>
<tr><td>A4 복사용지(80g)</td><td>3</td><td class="r">21,000</td><td class="r">63,000</td></tr>
<tr><td>레이저 토너 카트리지</td><td>1</td><td class="r">89,000</td><td class="r">89,000</td></tr>
<tr><th colspan="3">합계(부가세 포함)</th><td class="r">152,000</td></tr>
<tr><th colspan="3">부가세</th><td class="r">13,818</td></tr></table>
<p>결제수단: 법인카드 &nbsp;|&nbsp; 적요: 사무용품 11월 정기 구매</p></body></html>
""",
        encoding="utf-8",
    )


def make_txt():
    (OUT / "04_간이영수증.txt").write_text(
        "GS25 선릉점\n사업자번호: 105-81-33456\n2026.11.23 09:15\n"
        "생수 2L 6 1,200 7,200\n커피믹스 1박스 2 8,900 17,800\n"
        "부가세: 2,272\n합계: 25,000원\n결제수단: 현금영수증\n",
        encoding="utf-8",
    )


QUOTES = {
    "견적서_A_한빛인테리어": """견 적 서
공급자: 한빛인테리어
사업자번호: 214-81-55120
견적일: 2026-11-10
수신: 브런치카페 퀼 (사무공간 리모델링)
품목 수량 단위 단가 금액
벽지 시공(실크) 30 롤 18,000 540,000
바닥 데코타일 25 ㎡ 32,000 800,000
LED 조명 교체 8 개 55,000 440,000
철거 및 폐기물 처리 1 식 400,000 400,000
도장(문틀) 6 개 25,000 150,000
합계: 2,330,000원 (부가세 별도)
유효기간: 견적일로부터 30일
결제조건: 착수 50%, 완료 후 50%""",
    "견적서_B_다온디자인": """견 적 서
공급자: 다온디자인
사업자번호: 105-87-33014
견적일: 2026-11-12
수신: 브런치카페 퀼 (사무공간 리모델링)
품목 수량 단위 단가 금액
벽지 시공 실크 30 롤 17,500 525,000
바닥 데코타일 시공 25 ㎡ 30,000 750,000
LED 조명 8 개 42,000 336,000
문틀 도장 6 개 24,000 144,000
합계: 1,755,000원 (부가세 별도)
유효기간: 견적일로부터 14일
결제조건: 계약 시 전액""",
    "견적서_C_우리공간": """견 적 서
공급자: 우리공간
사업자번호: 120-86-90412
견적일: 2026-11-13
수신: 브런치카페 퀼 (사무공간 리모델링)
품목 수량 단위 단가 금액
벽지 시공(실크) 30 롤 19,000 570,000
바닥 데코타일 25 ㎡ 41,000 1,025,000
LED 조명 교체 8 개 46,000 368,000
철거 및 폐기물 처리 1 식 350,000 350,000
도장(문틀) 6 개 26,000 156,000
합계: 2,469,000원 (부가세 별도)
유효기간: 견적일로부터 30일
하자보수: 시공 후 1년 무상""",
}

CONTRACT = """마케팅 대행 서비스 계약서

주식회사 퀵그로스 (이하 "갑")와 브런치카페 퀼 (이하 "을")은 다음과 같이 계약을 체결한다.

제1조(목적) 본 계약은 갑이 을의 온라인 마케팅(SNS 운영, 검색 광고 대행)을 수행하는 데 필요한 사항을 정한다.

제2조(계약기간) 계약기간은 2026년 12월 1일부터 2027년 11월 30일까지로 한다. 계약 만료 1개월 전까지 서면 해지 통보가 없으면 동일한 조건으로 1년씩 자동 연장된다.

제3조(대금 지급) 을은 매월 5일까지 월 이용료 1,100,000원(부가세 포함)을 지급한다. 지급이 지연될 경우 연 24%의 지연이자를 가산한다.

제4조(중도 해지) 을이 계약기간 중 계약을 해지하는 경우 잔여 기간 이용료 총액의 50%를 위약금으로 갑에게 지급한다.

제5조(서비스 변경) 갑은 운영상 필요한 경우 을에게 사전 통보 없이 서비스 내용을 변경할 수 있다.

제6조(책임의 제한) 광고 성과(방문자 수, 매출 등)에 대하여 갑은 어떠한 책임도 지지 않는다.

제7조(결과물의 권리) 계약기간 중 제작된 콘텐츠의 저작권은 갑에게 귀속된다.

제8조(비밀유지) 양 당사자는 본 계약과 관련하여 알게 된 상대방의 영업 정보를 제3자에게 누설하지 아니한다.

제9조(관할) 본 계약과 관련한 분쟁은 갑의 본점 소재지 관할 법원을 전속 관할로 한다.

2026년 11월 20일"""

HEALTH = {
    "건강검진_2025": """건강검진 결과 통보서
수검자: 홍길동 (가상 인물)
검진기관: 퀼내과의원
검진일: 2025-11-12
체중: 71.2 kg
체질량지수(BMI): 24.1
허리둘레: 84 cm
혈압: 126/82 mmHg
공복혈당: 98 mg/dL
총콜레스테롤: 205 mg/dL
HDL 콜레스테롤: 38 mg/dL
LDL 콜레스테롤: 128 mg/dL
중성지방: 142 mg/dL
AST(SGOT): 28 U/L
ALT(SGPT): 33 U/L
감마지티피(γ-GTP): 45 U/L
혈색소: 14.8 g/dL
혈청 크레아티닌: 0.9 mg/dL
eGFR: 95 mL/min/1.73㎡""",
    "건강검진_2026": """건강검진 결과 통보서
수검자: 홍길동 (가상 인물)
검진기관: 퀼내과의원
검진일: 2026-11-18
체중: 75.8 kg
체질량지수(BMI): 25.6
허리둘레: 89 cm
혈압: 138/88 mmHg
공복혈당: 112 mg/dL
총콜레스테롤: 236 mg/dL
HDL 콜레스테롤: 44 mg/dL
LDL 콜레스테롤: 162 mg/dL
중성지방: 210 mg/dL
AST(SGOT): 31 U/L
ALT(SGPT): 48 U/L
감마지티피(γ-GTP): 71 U/L
혈색소: 15.1 g/dL
혈청 크레아티닌: 0.95 mg/dL
eGFR: 91 mL/min/1.73㎡""",
}

# 프런트엔드 '샘플로 체험' 버튼이 내려받는 텍스트 사본 (URL 에 안전한 영문 파일명)
WEB_NAMES = {
    "견적서_A_한빛인테리어": "quote_a.txt", "견적서_B_다온디자인": "quote_b.txt", "견적서_C_우리공간": "quote_c.txt",
    "마케팅대행_계약서": "contract.txt", "건강검진_2025": "health_2025.txt", "건강검진_2026": "health_2026.txt",
}
WEB_DIR = OUT.parent / "frontend" / "public" / "samples"


def text_pdf(path, text, title_size=13, size=9):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="malgun", fontfile=FONT)
    page.insert_font(fontname="malgunb", fontfile=FONT_B)
    y = 56
    for i, line in enumerate(text.splitlines()):
        if not line.strip():
            y += 6
            continue
        title = i == 0
        for chunk in textwrap.wrap(line, 48) if not title else [line]:
            page.insert_text((50, y), chunk, fontsize=title_size if title else size, fontname="malgunb" if title else "malgun")
            y += 24 if title else size + 7
    doc.subset_fonts()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path, deflate=True)
    doc.close()


def make_tool_samples():
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    groups = [("견적비교", QUOTES), ("계약서", {"마케팅대행_계약서": CONTRACT}), ("건강검진", HEALTH)]
    for folder, docs in groups:
        for name, text in docs.items():
            text_pdf(OUT / folder / f"{name}.pdf", text)
            (WEB_DIR / WEB_NAMES[name]).write_text(text + chr(10), encoding="utf-8")


if __name__ == "__main__":
    make_tool_samples()
    make_text_pdf()
    make_scanned_pdf()
    make_eml()
    make_html()
    make_txt()
    for f in sorted(OUT.rglob("*")):
        if f.is_file() and f.suffix not in (".py", ".md"):
            print(f"{str(f.relative_to(OUT)):44s} {f.stat().st_size:>8,} B")
