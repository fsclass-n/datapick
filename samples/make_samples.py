"""samples/ 폴더의 시연용 샘플 문서를 생성한다.

실행: py -3.11 samples/make_samples.py  (PyMuPDF · Pillow 필요, 시스템 Python 기준)
모든 내용은 가상의 업체·금액이다.
"""

import io
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


if __name__ == "__main__":
    make_text_pdf()
    make_scanned_pdf()
    make_eml()
    make_html()
    make_txt()
    for f in sorted(OUT.iterdir()):
        if f.name != "make_samples.py":
            print(f"{f.name:40s} {f.stat().st_size:>8,} B")
