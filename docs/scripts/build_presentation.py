"""dataquill 발표자료(PPTX) 생성 스크립트.

실행: .venv/Scripts/python docs/scripts/build_presentation.py
출력: docs/프로젝트_발표자료.pptx (슬라이드 노트에 발표자 스크립트 포함)
원고: docs/md/2026-11-17_발표자료_구성안.md
화면 캡처: docs/assets/screenshots/ (로컬 데모 인스턴스에서 촬영)
"""

from __future__ import annotations

import re
from pathlib import Path

import qrcode
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

DOCS = Path(__file__).resolve().parents[1]
SHOTS = DOCS / "assets" / "screenshots"
QR_DIR = DOCS / "assets" / "qr"
OUTPUT = DOCS / "프로젝트_발표자료.pptx"

FONT, MONO = "맑은 고딕", "Consolas"
BRAND, BRAND_DARK, BRAND_LIGHT, BRAND_200 = "4F46E5", "1E1B4B", "EEF2FF", "C7D2FE"
INK, BODY, MUTED, LINE, PANEL, WHITE = "0F172A", "334155", "64748B", "E2E8F0", "F8FAFC", "FFFFFF"
GREEN, ROSE, AMBER, SKY = "059669", "E11D48", "D97706", "0284C7"
LINKS = {
    "GitHub": "https://github.com/fsclass-n/dataquill",
    "서비스": "https://dataquill.onrender.com",
    "API 문서": "https://dataquill-api.onrender.com/docs",
}
TOTAL_MAIN = 16
INLINE = re.compile(r"(\*\*|`[^`]+`)")
CODE = "4338CA"


# --------------------------------------------------------------------------- helpers
def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def style_run(run, size, color=BODY, bold=False, mono=False):
    font = run.font
    font.size = Pt(size)
    font.bold = bold
    font.color.rgb = rgb(color)
    font.name = MONO if mono else FONT
    rpr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set("typeface", FONT)


def write(tf, paragraphs, size=14, color=BODY, bold=False, align=None, space=4, mono=False, line=None):
    """paragraphs: str 또는 (str, {size,color,bold,bullet,level,align,space}). '**굵게**' 지원."""
    tf.word_wrap = True
    for i, para in enumerate(paragraphs):
        text, opt = (para, {}) if isinstance(para, str) else para
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = opt.get("align", align)
        p.space_after = Pt(opt.get("space", space))
        if line or opt.get("line"):
            p.line_spacing = opt.get("line", line)
        if opt.get("bullet"):
            level = opt.get("level", 0)
            ppr = p._p.get_or_add_pPr()
            margin = Inches(0.2 + 0.22 * level)
            ppr.set("marL", str(Emu(margin)))
            ppr.set("indent", str(-Emu(Inches(0.18))))
            clr = ppr.makeelement(qn("a:buClr"), {})
            srgb = clr.makeelement(qn("a:srgbClr"), {"val": opt.get("bullet_color", BRAND)})
            clr.append(srgb)
            ppr.append(clr)
            ppr.append(ppr.makeelement(qn("a:buChar"), {"char": "•" if level == 0 else "–"}))
        strong = False
        for token in INLINE.split(text):
            if not token:
                continue
            if token == "**":
                strong = not strong
                continue
            code = token.startswith("`") and token.endswith("`") and len(token) > 1
            run = p.add_run()
            run.text = token[1:-1] if code else token
            style_run(
                run,
                opt.get("size", size),
                CODE if code else (opt.get("bold_color", INK) if strong else opt.get("color", color)),
                bold=opt.get("bold", bold) or strong,
                mono=opt.get("mono", mono) or code,
            )
    return tf


def bullets(items, size=14, **extra):
    out = []
    for item in items:
        level = 1 if item.startswith("- ") else 0
        out.append((item[2:] if level else item, {"bullet": True, "level": level, "size": size - level, **extra}))
    return out


def textbox(slide, x, y, w, h, paragraphs, anchor=MSO_ANCHOR.TOP, margin=0.02, **kw):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    write(tf, paragraphs, **kw)
    return tb


def set_alpha(shape, alpha_pct):
    fill = shape.fill._xPr.find(qn("a:solidFill"))
    clr = fill[0]
    clr.append(clr.makeelement(qn("a:alpha"), {"val": str(int(alpha_pct * 1000))}))


def box(slide, x, y, w, h, fill=WHITE, line=LINE, radius=0.08, line_width=1.0, shape=None):
    kind = shape or (MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE)
    shp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = min(radius, 0.5)
    shp.shadow.inherit = False
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(line_width)
    else:
        shp.line.fill.background()
    return shp


def card(slide, x, y, w, h, paragraphs, fill=WHITE, line=LINE, anchor=MSO_ANCHOR.TOP, pad=0.18, radius=0.06, **kw):
    shp = box(slide, x, y, w, h, fill, line, radius)
    tf = shp.text_frame
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(pad)
    tf.margin_top = tf.margin_bottom = Inches(pad * 0.75)
    write(tf, paragraphs, **kw)
    return shp


def pill(slide, x, y, w, h, text, fill=BRAND_LIGHT, color=BRAND, size=11, line=None):
    return card(slide, x, y, w, h, [(text, {"bold": True, "color": color, "size": size, "align": PP_ALIGN.CENTER})],
                fill=fill, line=line, anchor=MSO_ANCHOR.MIDDLE, pad=0.06, radius=0.5)


def arrow(slide, x1, y1, x2, y2, color=MUTED, width=1.5):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    conn.line.color.rgb = rgb(color)
    conn.line.width = Pt(width)
    ln = conn.line._get_or_add_ln()
    ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return conn


def picture(slide, path, x, y, w, h, border=LINE, anchor="top"):
    """(w, h) 상자를 꽉 채우도록 이미지를 잘라서 배치한다."""
    with Image.open(path) as img:
        iw, ih = img.size
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    box_ratio, img_ratio = w / h, iw / ih
    if img_ratio > box_ratio:
        crop = 1 - box_ratio / img_ratio
        pic.crop_left = pic.crop_right = crop / 2
    elif img_ratio < box_ratio:
        crop = 1 - img_ratio / box_ratio
        if anchor == "top":
            pic.crop_bottom = crop
        else:
            pic.crop_top = pic.crop_bottom = crop / 2
    if border:
        pic.line.color.rgb = rgb(border)
        pic.line.width = Pt(0.75)
    return pic


def table(slide, x, y, w, rows, widths, size=11, header_fill=BRAND_DARK, row_h=0.4, first_col_bold=True):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tbl = shape.table
    tbl.first_row = True
    tbl.horz_banding = False
    for i, cw in enumerate(widths):
        tbl.columns[i].width = Inches(cw)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(header_fill if r == 0 else (PANEL if r % 2 == 0 else WHITE))
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.paragraphs[0].text = ""
            header = r == 0
            write(tf, [(value, {
                "size": size,
                "bold": header or (first_col_bold and c == 0),
                "color": WHITE if header else (INK if c == 0 else BODY),
            })], space=0)
    return tbl


def notes(slide, script):
    slide.notes_slide.notes_text_frame.text = script.strip()


def base(prs, num, section, title, subtitle=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box(slide, 0.6, 0.48, 0.07, 0.3, BRAND, None, 0)
    textbox(slide, 0.75, 0.42, 9, 0.4, [(section, {"size": 12, "bold": True, "color": BRAND})])
    textbox(slide, 0.6, 0.78, 12.1, 0.7, [(title, {"size": 26, "bold": True, "color": INK})])
    if subtitle:
        textbox(slide, 0.6, 1.33, 12.1, 0.4, [(subtitle, {"size": 13, "color": MUTED})])
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0.6), Inches(7.02), Inches(12.73), Inches(7.02))
    conn.line.color.rgb = rgb(LINE)
    conn.line.width = Pt(0.75)
    textbox(slide, 0.6, 7.07, 6, 0.3, [("dataquill  |  생성형 AI & RPA 데이터 입력 자동화  |  3조", {"size": 9, "color": MUTED})])
    page = f"{num} / {TOTAL_MAIN}" if isinstance(num, int) else num
    textbox(slide, 10.7, 7.07, 2.03, 0.3, [(page, {"size": 9, "color": MUTED, "align": PP_ALIGN.RIGHT})])
    return slide


def dark(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(BRAND_DARK)
    for x, y, d, color, a in [(-1.6, -1.8, 5.2, "4F46E5", 45), (9.6, 4.2, 5.4, "C026D3", 22)]:
        circle = box(slide, x, y, d, d, color, None, 0, shape=MSO_SHAPE.OVAL)
        set_alpha(circle, a)
    return slide


def make_qr_codes():
    QR_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for label, url in LINKS.items():
        path = QR_DIR / f"qr_{['github', 'service', 'api'][list(LINKS).index(label)]}.png"
        img = qrcode.make(url, box_size=10, border=2)
        img.save(path)
        paths[label] = path
    return paths


def qr_block(slide, qrs, x, y, size=1.25, gap=0.3):
    for i, (label, path) in enumerate(qrs.items()):
        cx = x + i * (size + gap)
        box(slide, cx - 0.06, y - 0.06, size + 0.12, size + 0.12, WHITE, None, 0.06)
        slide.shapes.add_picture(str(path), Inches(cx), Inches(y), Inches(size), Inches(size))
        textbox(slide, cx - 0.2, y + size + 0.1, size + 0.4, 0.3,
                [(label, {"size": 11, "bold": True, "color": WHITE, "align": PP_ALIGN.CENTER})])


# --------------------------------------------------------------------------- slides
def s01_cover(prs, qrs):
    s = dark(prs)
    logo = box(s, 0.9, 1.05, 0.75, 0.75, BRAND, None, 0.22)
    write(logo.text_frame, [("dq", {"size": 22, "bold": True, "color": WHITE, "align": PP_ALIGN.CENTER})])
    logo.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    textbox(s, 0.85, 1.95, 8, 1.1, [("dataquill", {"size": 60, "bold": True, "color": WHITE})])
    textbox(s, 0.9, 3.1, 8.5, 0.6, [("서류는 AI가 읽고, 입력은 로봇이 합니다.", {"size": 26, "bold": True, "color": BRAND_200})])
    textbox(s, 0.9, 3.75, 8.5, 0.5, [("생성형 AI & RPA 기반 데이터 입력 자동화 시스템 — 프로젝트 결과 발표", {"size": 16, "color": "E0E7FF"})])
    for i, label in enumerate(["비정형 문서", "OCR + Gemini 해석", "RPA → ERP · Excel"]):
        pill(s, 0.9 + i * 2.55, 4.6, 2.15, 0.45, label, fill="312E81", color="E0E7FF", size=12)
        if i < 2:
            arrow(s, 0.9 + i * 2.55 + 2.18, 4.825, 0.9 + (i + 1) * 2.55 - 0.05, 4.825, BRAND_200)
    textbox(s, 0.9, 5.85, 7, 0.9, [
        ("발표  이오리", {"size": 16, "bold": True, "color": WHITE}),
        ("3조 · 조장 박미금 / 김모란 · 이오리 · 홍기흥", {"size": 12, "color": "C7D2FE"}),
    ])
    qr_block(s, qrs, 8.35, 4.55)
    notes(s, """
안녕하세요, 3조 발표를 맡은 이오리입니다.
dataquill은 영수증 PDF나 거래 이메일처럼 형식이 제각각인 문서를 AI가 읽어서 정형 데이터로 바꾸고,
RPA 로봇이 그 값을 ERP와 엑셀에 직접 입력해 주는 B2B 자동화 서비스입니다.
오늘은 기능 소개보다는 왜 이렇게 설계했는지, 배포하면서 무엇이 터졌고 어떻게 해결했는지를 중심으로 말씀드리겠습니다.
""")


def s02_problem(prs):
    s = base(prs, 2, "01 · 배경 및 문제 정의", "같은 값을 두 번, 손으로 입력하는 업무")
    steps = ["메일함 · 스캔 파일\n영수증 · 청구 메일", "사람이 읽고 해석", "ERP 화면에 수기 입력", "엑셀 원장에 다시 입력"]
    pains = [None, "형식 제각각", "오타 · 누락", "이중 입력"]
    for i, (step, pain) in enumerate(zip(steps, pains)):
        x = 0.6 + i * 3.15
        card(s, x, 1.85, 2.75, 0.95, [(step, {"size": 13, "bold": True, "color": INK, "align": PP_ALIGN.CENTER})],
             fill=PANEL, anchor=MSO_ANCHOR.MIDDLE)
        if i < 3:
            arrow(s, x + 2.78, 2.325, x + 3.12, 2.325)
        if pain:
            pill(s, x + 0.62, 2.92, 1.5, 0.34, pain, fill="FFE4E6", color=ROSE, size=10)
    problems = [
        ("문제 1. 비정형 입력", "영수증 · 세금계산서 · 청구 메일마다 형식이 달라 규칙 기반 자동화가 쉽게 깨짐"),
        ("문제 2. 반복 · 이중 입력", "같은 거래를 ERP와 엑셀에 각각 수작업 → 시간 낭비 + 불일치"),
        ("문제 3. API 없는 레거시 ERP", "연동 API가 없으면 결국 사람이 화면에 타이핑해야 함"),
    ]
    for i, (title, body) in enumerate(problems):
        card(s, 0.6 + i * 4.1, 3.6, 3.85, 1.6, [
            (title, {"size": 15, "bold": True, "color": INK, "space": 8}),
            (body, {"size": 12.5, "color": BODY}),
        ])
    card(s, 0.6, 5.5, 12.1, 1.25, [
        ("기획 의도", {"size": 12, "bold": True, "color": BRAND, "space": 4}),
        ("해석은 **생성형 AI (OCR + LLM)**, 입력은 **RPA**, 그리고 그 사이에 **사람의 검수 단계(Human-in-the-loop)**를 둔다",
         {"size": 16, "color": BODY}),
    ], fill=BRAND_LIGHT, line=BRAND_200, anchor=MSO_ANCHOR.MIDDLE, pad=0.25)
    notes(s, """
경리나 총무 업무를 보면, 영수증과 청구 메일을 보고 ERP에 한 번, 엑셀 원장에 또 한 번 입력하는 일이 계속 반복됩니다.
기존 자동화가 잘 안 됐던 이유는 두 가지라고 봤습니다.
첫째, 문서 형식이 제각각이라 정규식 같은 규칙으로는 한계가 있다는 점. 둘째, 회사가 쓰는 ERP에 연동 API가 없는 경우가 많다는 점입니다.
그래서 형식 문제는 생성형 AI로, API가 없는 문제는 사람처럼 화면에 입력하는 RPA로 풀기로 했습니다.
다만 AI가 틀릴 수 있기 때문에 둘 사이에 사람이 확인하고 고치는 검수 단계를 일부러 넣었습니다. 이 결정이 이후 설계 전체에 영향을 줬습니다.
""")


def s03_solution(prs):
    s = base(prs, 3, "02 · 핵심 가치 및 솔루션", "수집 → 해석 → 입력, 세 단계로 끝나는 자동화")
    cards = [
        ("01", "비정형 문서 수집", ["파일 업로드: PDF · 이미지 · EML · HTML · TXT", "이메일 본문 붙여넣기 (텍스트/HTML)", "최대 10MB, 확장자 화이트리스트"]),
        ("02", "OCR + Gemini 해석", ["거래처 · 사업자번호 · 일자 · 합계 · 부가세", "결제수단 · 품목 · 적요 + 신뢰도", "Pydantic 스키마로 출력 형식 강제"]),
        ("03", "RPA 자동 입력", ["엑셀 원장 적재 (문서 ID 기준 교체)", "Playwright 가 ERP 전표 화면에 타이핑", "ERP 가 발급한 전표번호까지 확인"]),
    ]
    for i, (num, title, items) in enumerate(cards):
        x = 0.6 + i * 4.1
        box(s, x, 1.85, 3.85, 3.75, WHITE, LINE, 0.05)
        textbox(s, x + 0.3, 2.05, 2, 0.8, [(num, {"size": 36, "bold": True, "color": BRAND_200})])
        textbox(s, x + 0.3, 2.85, 3.3, 0.5, [(title, {"size": 18, "bold": True, "color": INK})])
        textbox(s, x + 0.3, 3.5, 3.35, 2, bullets(items, size=13), space=6)
        if i < 2:
            arrow(s, x + 3.88, 3.72, x + 4.07, 3.72, BRAND)
    card(s, 0.6, 5.85, 12.1, 0.9, [
        ("+ 운영   관리자 모니터링으로 **AI 파싱 성공률**과 **RPA 성공률**, 일별 추이, 최근 실패 원인을 추적", {"size": 15}),
    ], fill=PANEL, anchor=MSO_ANCHOR.MIDDLE, pad=0.25)
    notes(s, """
서비스는 세 단계입니다. 문서를 넣으면, AI가 회계 전표에 필요한 항목을 뽑아내고,
사용자가 확인한 뒤 버튼 하나로 엑셀 원장에 쌓거나 로봇이 ERP 화면에 직접 입력합니다.
여기에 운영 관점에서 "AI가 얼마나 잘 읽고 있는지, 로봇이 얼마나 성공하고 있는지"를 볼 수 있는 관리자 모니터링을 붙였습니다.
""")


def s04_architecture(prs):
    s = base(prs, 4, "03 · 전체 시스템 아키텍처", "정적 프런트 · 무상태 API 컨테이너 · 관리형 클라우드 DB")
    card(s, 0.6, 1.8, 7.7, 0.5, [("사용자 브라우저   ·   HTTPS   ·   Bearer JWT", {"size": 12, "bold": True, "color": MUTED, "align": PP_ALIGN.CENTER})],
         fill=PANEL, anchor=MSO_ANCHOR.MIDDLE, pad=0.05)
    arrow(s, 4.45, 2.32, 4.45, 2.55)
    card(s, 0.6, 2.58, 7.7, 0.72, [
        ("Frontend   React 19 · Vite 8 · Tailwind CSS v4 · Recharts", {"size": 13, "bold": True, "color": INK, "space": 1}),
        ("Render Static Site  —  dataquill.onrender.com  (Mock 모드 지원)", {"size": 11, "color": MUTED}),
    ], anchor=MSO_ANCHOR.MIDDLE, pad=0.15)
    arrow(s, 4.45, 3.32, 4.45, 3.58)
    textbox(s, 4.6, 3.3, 3.6, 0.3, [("REST · CORS 허용 도메인 제한", {"size": 10, "color": MUTED})])
    box(s, 0.6, 3.6, 7.7, 2.05, BRAND_LIGHT, BRAND_200, 0.04)
    textbox(s, 0.8, 3.68, 7.4, 0.6, [
        ("Backend   FastAPI · SQLAlchemy 2.0 · Pydantic", {"size": 13, "bold": True, "color": INK, "space": 1}),
        ("Render Web Service (Docker: Python 3.11 + Tesseract + Chromium)  —  dataquill-api.onrender.com", {"size": 10.5, "color": MUTED}),
    ])
    modules = [("routers", "auth · documents\nadmin · erp_demo"), ("services", "parser (Gemini / 규칙)\noauth · stats"),
               ("rpa/", "extract (OCR)\nexcel_writer · erp_typer")]
    for i, (title, body) in enumerate(modules):
        card(s, 0.8 + i * 2.48, 4.4, 2.32, 1.05, [
            (title, {"size": 12, "bold": True, "color": BRAND, "space": 2}),
            (body, {"size": 10.5, "color": BODY}),
        ], pad=0.12)
    externals = [("TiDB Cloud Serverless", "MySQL 호환 · TLS 필수"), ("Google Gemini API", "구조화 출력 · 멀티모달"),
                 ("OAuth 제공자", "Google · Naver · Kakao")]
    for i, (title, body) in enumerate(externals):
        x = 0.6 + i * 2.6
        arrow(s, x + 1.25, 5.67, x + 1.25, 5.92)
        card(s, x, 5.95, 2.5, 0.85, [
            (title, {"size": 12, "bold": True, "color": INK, "space": 1, "align": PP_ALIGN.CENTER}),
            (body, {"size": 10.5, "color": MUTED, "align": PP_ALIGN.CENTER}),
        ], fill=PANEL, anchor=MSO_ANCHOR.MIDDLE, pad=0.08)
    textbox(s, 8.75, 1.8, 3.95, 0.4, [("설계 결정", {"size": 15, "bold": True, "color": INK})])
    textbox(s, 8.75, 2.3, 3.95, 3.6, bullets([
        "**분리 배포** — 화면 수정이 RPA가 들어 있는 무거운 백엔드 이미지 재빌드를 유발하지 않게",
        "**rpa 패키지 분리** — API에서 호출 + CLI 단독 실행 (`python -m rpa.erp_typer`) → 워커 분리가 쉬움",
        "**무상태 컨테이너** — 데이터는 TiDB에 두어 재배포 · 인스턴스 교체에도 유지",
        "**DB 추상화** — `DATABASE_URL` 하나로 SQLite(테스트) ↔ TiDB(운영)",
    ], size=12.5), space=8)
    card(s, 8.75, 5.95, 3.95, 0.85, [
        ("한계: RPA · LLM 호출이 API 요청 안에서 동기 실행 → 15장 '작업 큐 분리'", {"size": 11, "color": AMBER, "bold": True}),
    ], fill="FFFBEB", line="FDE68A", anchor=MSO_ANCHOR.MIDDLE, pad=0.14)
    notes(s, """
구조는 크게 세 덩어리입니다. 정적 프런트, FastAPI 백엔드, 그리고 외부 서비스인 TiDB, Gemini, OAuth 제공자입니다.
프런트와 백엔드를 분리한 이유는 배포 주기가 다르기 때문입니다. 화면만 고쳤는데 RPA가 들어 있는 무거운 백엔드 이미지를 다시 빌드할 필요는 없으니까요.
RPA 코드는 rpa라는 별도 패키지로 뺐습니다. 웹 서버에서 호출할 수도 있고, 명령줄에서 단독 실행할 수도 있게 해서, 나중에 별도 워커로 떼어 내기 쉽게 했습니다.
컨테이너는 상태를 갖지 않게 하고 데이터는 TiDB에 두었기 때문에, 재배포하거나 인스턴스가 바뀌어도 데이터가 유지됩니다.
지금 구조의 한계는 RPA와 LLM 호출이 요청 안에서 동기로 돈다는 점인데, 이건 마지막 회고에서 개선 계획으로 말씀드리겠습니다.
""")


def s05_stack(prs):
    s = base(prs, 5, "04 · 기술 스택 선정 이유", "기능보다 '작은 팀이 끝까지 운영할 수 있는가'로 골랐다")
    for i, text in enumerate(["① 작은 팀이 유지보수 가능한가", "② 로컬과 운영이 같은 코드로 도는가", "③ 실패해도 대체 경로가 있는가"]):
        pill(s, 0.6 + i * 4.1, 1.78, 3.85, 0.42, text, size=12)
    rows = [
        ["영역", "선택", "고려한 대안", "선택 이유"],
        ["API", "FastAPI", "Flask, Django", "Pydantic 으로 요청 검증 + 응답 모델 정의, OpenAPI /docs 자동 생성"],
        ["LLM", "Gemini 구조화 출력", "프롬프트로 JSON 요청", "response_schema 에 Pydantic 모델 전달 → 스키마 강제, 이미지·PDF 멀티모달"],
        ["RPA", "Playwright", "Selenium", "요소 준비까지 자동 대기, --with-deps 로 Docker 설치 단순, 헤드리스 기본"],
        ["OCR", "pypdf → Tesseract → Gemini", "상용 OCR API", "텍스트 레이어 → 로컬 OCR → LLM 멀티모달 순서로 단계적 대체"],
        ["DB", "TiDB Cloud Serverless", "SQLite, 자체 MySQL", "MySQL 호환(PyMySQL 그대로), 무료 관리형 → 컨테이너 무상태화"],
        ["ORM", "SQLAlchemy 2.0", "Raw SQL", "URL 만 바꿔 SQLite(테스트) ↔ TiDB(운영) 전환"],
        ["Front", "React 19 · Vite 8 · Tailwind v4", "CRA, styled-components", "빠른 빌드, @theme 디자인 토큰 + @utility 공통 클래스"],
        ["차트", "Recharts", "Plotly, Chart.js", "React 컴포넌트 방식, 게이지 · 누적 막대 · 도넛을 같은 API 로 구성"],
    ]
    table(s, 0.6, 2.4, 12.1, rows, [1.0, 2.75, 2.25, 6.1], size=11.5, row_h=0.47)
    notes(s, """
기술은 세 가지 기준으로 골랐습니다. 작은 팀으로 유지보수할 수 있는지, 로컬과 운영이 같은 코드로 도는지, 실패했을 때 대체 경로가 있는지입니다.
대표적인 예가 LLM 부분입니다. 처음에는 프롬프트로 JSON으로 답해 달라고 요청하고 결과를 파싱하는 방식도 생각했는데,
그러면 필드가 빠지거나 형식이 깨지는 경우를 일일이 처리해야 합니다.
그래서 Gemini의 구조화 출력에 Pydantic 모델을 그대로 스키마로 넘겼습니다. 서버의 검증 모델과 LLM 출력 스키마가 같은 클래스라서 한쪽만 고치면 됩니다.
또 API 키가 없거나 장애가 나도 서비스가 멈추지 않도록 규칙 기반 파서를 대체 경로로 두었습니다.
DB는 SQLAlchemy를 써서 테스트는 SQLite, 운영은 TiDB로 URL만 바꿔 돌립니다.
""")


def s06_pipeline(prs):
    s = base(prs, 6, "05 · 핵심 기술 ① 문서 수집 · RPA 자동화 파이프라인", "가장 싸고 정확한 방법부터, 실패하면 다음 방법으로")
    stages = [
        ("① 업로드", ["PDF · 이미지 · EML", "HTML · TXT · 메일 본문", "10MB · 확장자 검사"]),
        ("② 텍스트 추출", ["PDF 텍스트 레이어 (pypdf)", "20자 미만 → 스캔본 판정", "이미지 → Tesseract kor+eng"]),
        ("③ AI 정형화", ["Gemini 구조화 출력", "스캔본 · 이미지는 멀티모달", "키 없음 → 규칙 파서"]),
        ("④ 사람 검수", ["추출 값 수정 · 저장", "서버 스키마 재검증 (422)", "신뢰도 표시"]),
        ("⑤ RPA 입력", ["엑셀: 문서 ID 기준 교체", "ERP: Playwright 타이핑", "전표번호 확인 후 성공"]),
    ]
    for i, (title, items) in enumerate(stages):
        x = 0.6 + i * 2.47
        pill(s, x, 1.8, 2.22, 0.48, title, fill=BRAND if i in (2, 4) else BRAND_LIGHT,
             color=WHITE if i in (2, 4) else BRAND, size=13)
        if i < 4:
            arrow(s, x + 2.24, 2.04, x + 2.45, 2.04, BRAND)
        card(s, x, 2.38, 2.22, 1.3, bullets(items, size=11), fill=PANEL, pad=0.1, space=2)
    textbox(s, 0.6, 3.95, 8.6, 0.4, [("RPA 설계 포인트", {"size": 15, "bold": True, "color": INK})])
    textbox(s, 0.6, 4.4, 8.6, 2.5, bullets([
        "**결과 검증으로 성공 판정** — 버튼 클릭이 아니라 ERP 응답 요소의 `data-status=\"ok\"` + 전표번호를 확인해야 성공 기록",
        "**화면 구조와 코드 분리** — `FIELD_SELECTORS` 맵만 바꾸면 실제 ERP 화면에 적용",
        "**멱등 적재** — 같은 문서를 다시 엑셀에 적재하면 문서 ID 기준으로 교체 → 중복 행 없음",
        "**실패도 기록** — Chromium 미설치 등 환경 오류를 읽을 수 있는 문장으로 바꿔 작업 이력에 저장",
        "**운영 확인** — Render 컨테이너 안에서 Chromium 실행, Gemini 파싱 → 엑셀 적재 성공",
    ], size=12.5), space=6)
    picture(s, SHOTS / "erp_demo.png", 9.55, 3.95, 3.15, 2.6, anchor="center")
    textbox(s, 9.55, 6.6, 3.15, 0.35, [("데모 ERP: 로봇 입력 후 전표번호 발급", {"size": 10, "color": MUTED, "align": PP_ALIGN.CENTER})])
    notes(s, """
파이프라인의 핵심은 "가장 싸고 정확한 방법부터 시도하고, 안 되면 다음 방법으로 넘어간다"입니다.
PDF에 텍스트 레이어가 있으면 그냥 읽습니다. 스캔본이라 글자가 20자도 안 나오면 OCR로, OCR 엔진이 없으면 파일 자체를 Gemini에 넘깁니다.
RPA 쪽에서 신경 쓴 건 두 가지입니다. 첫째, 엑셀 적재를 여러 번 눌러도 행이 중복되지 않도록 문서 ID 기준으로 교체하게 했습니다.
둘째, ERP 입력은 버튼을 눌렀다고 성공이 아니라, ERP가 돌려준 결과 요소의 상태값과 전표번호를 확인한 뒤에야 성공으로 기록합니다.
화면의 셀렉터는 코드와 분리해 두었기 때문에, 실제 회사 ERP에 붙일 때는 셀렉터 맵만 바꾸면 됩니다.
오른쪽 화면은 로봇이 데모 ERP에 값을 입력하고 전표번호를 받은 결과입니다.
""")


def s07_ai(prs):
    s = base(prs, 7, "06 · 핵심 기술 ② AI 정형화 로직 및 지표 시각화", "환각은 프롬프트 · 스키마 · 사람 검수 3단계로 통제")
    code = """{
  "document_type": "receipt",
  "vendor": "스타벅스 강남R점",
  "business_number": "123-45-67890",
  "date": "2026-11-17",
  "total_amount": 9000,  "vat": 818,
  "payment_method": "신용카드",
  "items": [{"name": "아메리카노", "quantity": 2,
             "unit_price": 4500, "amount": 9000}],
  "confidence": 0.98
}"""
    shp = box(s, 0.6, 1.8, 5.9, 3.0, "0F172A", None, 0.04)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Inches(0.25)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    write(tf, [(line, {"size": 11.5, "color": "E2E8F0", "mono": True, "space": 0}) for line in code.splitlines()])
    textbox(s, 0.6, 4.85, 5.9, 0.3, [("운영 환경(Render + Gemini) 실제 추출 결과, 2026-11-17", {"size": 10, "color": MUTED})])
    textbox(s, 0.6, 5.25, 5.9, 1.7, [
        ("운영 지표 정의", {"size": 13, "bold": True, "color": INK, "space": 4}),
        *bullets([
            "AI 파싱 성공률 = parsed ÷ (parsed + failed)  · 대기 문서는 분모 제외",
            "RPA 성공률 = success ÷ (success + failed)",
            "일별 집계는 UTC 저장 → KST 로 변환 후 날짜 묶음",
        ], size=11.5),
    ], space=3)
    textbox(s, 6.85, 1.8, 5.85, 2.6, bullets([
        "**스키마** — `ParsedDocument`(Pydantic): 금액은 정수(원), 날짜 YYYY-MM-DD, 없는 값은 null",
        "**프롬프트** — \"문서에 없는 값은 추측하지 말 것\" + temperature 0",
        "**대체 경로** — 정규식 규칙 파서, 찾은 필드 수로 신뢰도 계산",
        "- confidence = 0.2 + 0.15 × 핵심 필드 수 + 0.1(품목)",
        "**검수 UI** — 신뢰도를 보여 주고 사람이 확인한 값만 RPA 로",
    ], size=12.5), space=5)
    picture(s, SHOTS / "monitoring_top.png", 6.85, 4.45, 5.85, 2.45)
    notes(s, """
회계 데이터에서 가장 위험한 건 AI가 그럴듯하게 지어낸 값입니다.
그래서 프롬프트에 "없는 값은 추측하지 말고 null"을 명시하고 temperature는 0으로 고정했습니다.
왼쪽은 운영 환경에서 실제로 뽑힌 결과인데, 품목 단가까지 계산해서 나눠 줍니다.
신뢰도 값은 검수 화면에 보여 줘서, 사용자가 어떤 문서를 더 꼼꼼히 봐야 하는지 판단하게 했습니다.
운영 측면에서는 성공률을 정의하는 게 중요했는데요, 아직 처리 중인 문서는 분모에서 빼고 성공 대 실패만으로 계산했습니다.
날짜는 서버가 UTC로 저장하기 때문에 통계를 낼 때 한국 시간으로 바꿔서 날짜를 묶었습니다.
""")


def s08_auth(prs):
    s = base(prs, 8, "07 · 주요 기능 ① 사용자 인증 및 보안", "화면은 단순하게, 보안 결정은 서버에서")
    picture(s, SHOTS / "login.png", 0.6, 1.8, 6.3, 3.94)
    textbox(s, 0.6, 5.78, 6.3, 0.3, [("Split 레이아웃 · 테스트 계정 원클릭 · 비밀번호 규칙 실시간 체크", {"size": 10, "color": MUTED})])
    textbox(s, 7.2, 1.8, 5.5, 4.2, bullets([
        "**비밀번호 규칙** — 대·소문자 + 숫자 + 특수문자 8자 이상, 프런트 실시간 + **서버 재검증**",
        "**저장** — PBKDF2-SHA256 26만 회 + 솔트, `hmac.compare_digest` 비교",
        "**OAuth 3종** — Google · Naver · Kakao 인가 코드 방식, state 쿠키로 CSRF 방지",
        "**계정 탈취 방지** — 같은 이메일이 다른 방식으로 가입돼 있으면 자동 연결 거부, 제공자의 이메일 인증 여부 확인",
        "**토큰 전달** — URL 해시(#token)로 전달 → 서버 접근 로그에 남지 않음",
        "**테스트 계정** — 일반 / 테스트 관리자(조회 전용) 버튼 → 자동 입력 후 로그인 (면접관 즉시 체험)",
    ], size=12.5), space=6)
    flow = ["/oauth/{p}/login\nstate 생성 · HttpOnly 쿠키", "제공자 로그인", "/callback\nstate 비교", "토큰 교환\n프로필 조회", "계정 연결 · 생성\n→ #token=JWT"]
    for i, step in enumerate(flow):
        x = 0.6 + i * 2.47
        card(s, x, 6.15, 2.22, 0.75, [(step, {"size": 10.5, "bold": i in (2, 4), "color": INK, "align": PP_ALIGN.CENTER})],
             fill=BRAND_LIGHT if i in (2, 4) else PANEL, anchor=MSO_ANCHOR.MIDDLE, pad=0.06)
        if i < 4:
            arrow(s, x + 2.24, 6.525, x + 2.45, 6.525, BRAND)
    notes(s, """
로그인은 화면은 단순하지만 보안 결정이 가장 많이 들어간 부분입니다.
비밀번호 규칙은 프런트에서 실시간으로 보여 주지만, 프런트 검사는 우회할 수 있으니 서버에서 같은 규칙으로 다시 검사합니다.
소셜 로그인에서 특히 신경 쓴 건 계정 탈취입니다. 누군가 제 이메일로 카카오 계정을 만들었을 때,
이메일이 같다고 기존 계정에 자동으로 연결해 버리면 그 사람이 제 계정에 들어올 수 있습니다.
그래서 이메일이 겹치면 연결하지 않고 막았고, 제공자가 이메일 인증 여부를 주는 경우에는 인증된 이메일만 믿습니다.
로그인이 끝나면 토큰을 쿼리 문자열이 아니라 URL 해시로 넘겨서 서버 접근 로그에 토큰이 남지 않게 했습니다.
테스트 계정 버튼은 오늘 같은 자리를 위해 만들었습니다. 가입 없이 일반 사용자와 관리자 화면을 바로 비교해 보실 수 있고, 공개된 테스트 관리자는 조회만 가능합니다.
""")


def s09_flow(prs):
    s = base(prs, 9, "08 · 주요 기능 ② 핵심 유저 플로우", "업로드부터 ERP 입력까지 한 화면에서")
    picture(s, SHOTS / "documents.png", 0.6, 1.8, 6.9, 5.05)
    steps = [
        ("업로드", "파일 드래그 & 드롭 또는 '이메일 본문' 탭에 붙여넣기"),
        ("해석", "완료 알림과 함께 우측 검수 패널에 추출 결과 표시"),
        ("검수", "값 수정 → '검수 저장' (서버 스키마 재검증, 잘못된 값은 422)"),
        ("입력", "'엑셀 원장 적재' / 'ERP 자동 타이핑' → 작업 이력에 결과 · 전표번호"),
        ("제약", "파싱 완료 문서만 RPA 가능: 버튼 비활성 + 서버 409 (화면 · 서버 이중 제약)"),
    ]
    for i, (title, body) in enumerate(steps):
        y = 1.8 + i * 1.0
        num = box(s, 7.85, y + 0.08, 0.5, 0.5, BRAND, None, 0.5, shape=MSO_SHAPE.OVAL)
        write(num.text_frame, [(str(i + 1), {"size": 14, "bold": True, "color": WHITE, "align": PP_ALIGN.CENTER})])
        num.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        textbox(s, 8.55, y, 4.15, 0.95, [
            (title, {"size": 14, "bold": True, "color": INK, "space": 2}),
            (body, {"size": 11.5, "color": BODY}),
        ])
    notes(s, """
실제 사용 흐름입니다. 대시보드에서 문서 업로드로 들어가 영수증을 끌어다 놓으면, 해석 결과가 오른쪽 검수 패널에 바로 뜹니다.
값을 고치고 저장한 다음 엑셀 적재나 ERP 타이핑을 누르면, 아래 작업 이력에 결과와 전표번호가 쌓입니다.
파싱이 실패한 문서는 RPA 버튼이 비활성화되고, 누군가 API를 직접 호출해도 서버가 409로 막습니다.
화면 제약과 서버 제약을 항상 같이 걸어 두는 게 원칙이었습니다.
""")


def s10_ui(prs):
    s = base(prs, 10, "09 · 주요 기능 ③ 반응형 UI/UX 및 디자인 시스템", "B2B SaaS 수준의 디테일을 4인 팀으로")
    for i, (name, caption) in enumerate([("mobile_login.png", "모바일 로그인"), ("mobile_closed.png", "메뉴 닫힘 (햄버거)"),
                                          ("mobile_drawer.png", "메뉴 열림 (X + 드로어)")]):
        x = 0.6 + i * 2.35
        picture(s, SHOTS / name, x, 1.8, 2.15, 4.65)
        textbox(s, x, 6.5, 2.15, 0.3, [(caption, {"size": 10, "color": MUTED, "align": PP_ALIGN.CENTER})])
    textbox(s, 7.85, 1.8, 4.85, 5.1, bullets([
        "**햄버거 ↔ X** — 막대 3개 위치 · 회전 · 투명도 전환(300ms), `aria-expanded` 노출",
        "**우측 드로어** — 오른쪽 → 왼쪽 슬라이드, 배경 블러, ESC 닫기, 스크롤 잠금, 닫힘 시 `inert` 로 포커스 차단",
        "**서체 이원화** — 제목 IBM Plex Sans KR / 본문 Pretendard",
        "**디자인 시스템** — Tailwind v4 `@theme` 토큰 + `@utility` 공통 클래스, FontAwesome 아이콘 통일",
        "**편의** — To the Top (푸터 + 플로팅, smooth scroll), 토스트 알림",
        "**성능** — 페이지 단위 코드 스플리팅: 단일 번들 885KB → 메인 416KB, 차트는 사용하는 페이지에서만 로드",
    ], size=12.5), space=7)
    notes(s, """
UI는 "상용 B2B SaaS처럼 보이는가"를 기준으로 만들었습니다.
모바일 메뉴는 아이콘 전환과 드로어 슬라이드를 직접 구현했고, 키보드 사용자를 위해 ESC로 닫기,
닫혀 있을 때 포커스가 메뉴로 들어가지 않게 하는 처리까지 넣었습니다.
서체는 제목과 본문을 나눠 위계를 만들었고, 버튼 · 카드 · 입력창 같은 공통 스타일은 디자인 토큰으로 묶어서 화면마다 흩어지지 않게 했습니다.
차트 라이브러리가 무거워서 첫 화면 번들이 885KB였는데, 페이지 단위로 쪼개서 로그인 화면에서는 차트 코드를 받지 않게 했습니다.
""")


def s11_admin(prs):
    s = base(prs, 11, "10 · 주요 기능 ④ 관리자(Admin) 백오피스", "접근 제어는 세 겹, 보안 경계는 서버 하나")
    picture(s, SHOTS / "admin_users.png", 0.6, 1.8, 7.2, 4.5)
    textbox(s, 0.6, 6.35, 7.2, 0.5, [("검색(250ms 디바운스) · 권한 필터 · 가입 방식 · 처리 문서 수 · 권한 토글 (운영 화면 · 테스트 관리자)", {"size": 10, "color": MUTED})])
    layers = [
        ("① 메뉴 노출", "관리자만 '회원 관리' · '모니터링' 메뉴 표시", PANEL, LINE, INK),
        ("② 라우트 가드", "<RequireAuth admin> → 일반 사용자는 대시보드로", PANEL, LINE, INK),
        ("③ API 의존성  ← 실제 보안 경계", "Depends(require_admin): 토큰 없음 401 · 권한 없음 403", BRAND_LIGHT, BRAND, BRAND),
    ]
    for i, (title, body, fill, line, color) in enumerate(layers):
        card(s, 8.15, 1.8 + i * 1.0, 4.55, 0.88, [
            (title, {"size": 13, "bold": True, "color": color, "space": 2}),
            (body, {"size": 11, "color": BODY}),
        ], fill=fill, line=line, anchor=MSO_ANCHOR.MIDDLE, pad=0.15)
    textbox(s, 8.15, 4.95, 4.55, 1.9, bullets([
        "**권한 변경** — 토글 + 확인창 → PATCH /api/admin/users/{id}/role",
        "**안전장치** — 본인 관리자 권한 해제 금지 (UI 비활성 + 서버 400) → 관리자 0명 방지",
        "**테스트 관리자** — 화면은 조회만, 쓰기 요청은 `get_current_user` 에서 403 · 운영 관리자는 ADMIN_TOKEN 로그인",
    ], size=12), space=6)
    notes(s, """
관리자 기능의 핵심은 접근 제어를 세 겹으로 둔 것입니다. 메뉴를 숨기고, 라우트에서 막고, API에서 다시 막습니다.
그런데 앞의 두 개는 사용자 편의를 위한 것이고, 진짜 보안 경계는 서버의 require_admin 의존성 하나라고 생각합니다.
테스트에서도 일반 사용자 토큰으로 관리자 API를 호출하면 403, 토큰 없이 호출하면 401이 나오는지 확인합니다.
또 관리자가 실수로 자기 권한을 지우면 관리자가 아무도 없는 상태가 될 수 있어서, 그건 서버에서 400으로 막았습니다.
로그인 화면에 공개한 테스트 관리자는 조회만 할 수 있고, 데이터를 바꾸는 요청은 인증 단계에서 모두 403으로 거부합니다.
""")


def s12_devops(prs):
    s = base(prs, 12, "11 · DevOps 및 CI/CD 배포 자동화", "main 푸시 한 번, 바뀐 영역만 검증하고 배포")
    card(s, 0.6, 3.0, 1.9, 1.1, [("git push\nmain", {"size": 15, "bold": True, "color": WHITE, "align": PP_ALIGN.CENTER})],
         fill=BRAND_DARK, line=None, anchor=MSO_ANCHOR.MIDDLE)
    lanes = [
        (1.8, 1.55, "GitHub Actions  ·  deploy.yml", ["paths-filter 로 바뀐 영역 판별", "`frontend/**` → npm ci · lint · build", "`backend/**` · `rpa/**` · requirements → pytest (30개)"], BRAND_LIGHT, BRAND_200),
        (3.55, 1.05, "Render Static Site  ·  dataquill", ["Root Directory = frontend → frontend 변경 시에만 빌드", "SPA Rewrite: /* → /index.html"], PANEL, LINE),
        (4.8, 1.05, "Render Web Service (Docker)  ·  dataquill-api", ["Build Filter: `backend/**` · `rpa/**` · requirements.txt", "헬스 체크 /api/health · PORT 환경 변수로 기동"], PANEL, LINE),
    ]
    for y, h, title, items, fill, line in lanes:
        arrow(s, 2.52, 3.55, 3.08, y + h / 2, BRAND)
        card(s, 3.1, y, 4.75, h, [(title, {"size": 12.5, "bold": True, "color": INK, "space": 3}), *bullets(items, size=11)],
             fill=fill, line=line, pad=0.14, space=1)
    textbox(s, 8.25, 1.8, 4.45, 0.4, [("환경 변수 · 비밀 값 관리", {"size": 15, "bold": True, "color": INK})])
    textbox(s, 8.25, 2.25, 4.45, 2.2, bullets([
        "**루트 .env 하나** — Vite 도 `envDir: '..'` 로 같은 파일 사용 (VITE_ 접두사만 노출)",
        "**.env 는 Git 제외**, 운영 값은 Render 대시보드에 직접 등록",
        "**Mock 모드** — VITE_API_URL 이 비면 브라우저 목업 API → 1단계 프런트 단독 배포",
    ], size=12), space=6)
    table(s, 8.25, 4.55, 4.45, [
        ["표기", "등록 위치"],
        ["[LOCAL]", "로컬 .env 전용"],
        ["[RENDER]", "백엔드 Web Service"],
        ["[RENDER-FE]", "프런트 Static Site"],
    ], [1.5, 2.95], size=11, row_h=0.36)
    card(s, 0.6, 6.05, 7.25, 0.8, [
        ("문서만 고친 커밋 → 어떤 서비스도 재빌드하지 않음", {"size": 12.5, "bold": True, "color": GREEN}),
    ], fill="ECFDF5", line="A7F3D0", anchor=MSO_ANCHOR.MIDDLE, pad=0.18)
    notes(s, """
배포는 main에 푸시하면 자동으로 됩니다. 다만 매번 다 배포하지 않고, 바뀐 영역만 검증하고 배포합니다.
백엔드 이미지에는 Chromium이 들어 있어서 빌드가 몇 분씩 걸리는데, 화면 문구 하나 고쳤다고 그걸 다시 빌드하는 건 낭비니까요.
GitHub Actions에서는 바뀐 쪽의 테스트와 빌드를 돌리고, Render는 Build Filter로 자기 영역이 바뀐 경우에만 배포합니다.
환경 변수는 루트의 .env 하나로 통일했습니다. 프런트 빌드 도구도 같은 파일을 읽게 해서 설정이 두 군데로 갈라지지 않게 했고,
예시 파일에는 각 값이 어디에 등록돼야 하는지 표시해 뒀습니다.
1단계에서는 백엔드 없이 프런트만 먼저 배포해야 했기 때문에, API 주소가 없으면 브라우저 안에서 돌아가는 목업 API로 전환되게 만들었습니다.
""")


def s13_trouble(prs):
    s = base(prs, 13, "12 · 트러블슈팅", "추측이 아니라 근거(로그 · 소스 · 헬스 체크)로 원인을 확정한다")
    cases = [
        ("① 어제까지 되던 Docker 빌드 실패", ROSE, [
            ("증상", "playwright install --with-deps 단계에서 'ttf-ubuntu-font-family' 설치 실패"),
            ("원인", "python:3.11-slim 이 Debian 13 으로 변경. Playwright 1.52 소스(nativeDeps.ts) 확인 → Debian 11/12 · Ubuntu 만 지원"),
            ("해결", "python:3.11-slim-bookworm 으로 고정 (Debian 12 의 fonts-unifont 사용 확인)"),
            ("교훈", "움직이는 태그는 재현성을 깬다 → 기본 이미지 OS 고정"),
        ]),
        ("② 키가 없는데 AI · OAuth 가 '설정됨'", AMBER, [
            ("증상", "헬스 체크가 parser: gemini, OAuth 3종도 활성으로 표시"),
            ("원인", "빈 값 뒤 인라인 주석(KEY=   # 설명)을 python-dotenv 가 값으로 읽음"),
            ("해결", "주석을 별도 줄로 이동, 규칙 문서화, 테스트는 외부 키를 비워 로컬 설정과 독립 실행"),
            ("교훈", "설정은 '넣었는지'가 아니라 '어떤 값으로 읽혔는지' 확인 → 헬스 체크에 파서 종류 노출"),
        ]),
        ("③ 운영에서만 실패하는 문제들", SKY, [
            ("TiDB", "1105 insecure transport → TLS 필수, DB_SSL=true + certifi CA. 운영 DB 대신 임시 DB 로 전체 흐름 검증 후 삭제"),
            ("Gemini", "503 high demand → 429/5xx 만 2·5·10초 백오프 재시도, 400 은 즉시 실패. 가짜 클라이언트 테스트 3개"),
            ("ERP", "컨테이너는 PORT=10000 → 기본값을 127.0.0.1:$PORT 로. 오류 메시지의 URL 로 원인 확정"),
        ]),
    ]
    for i, (title, color, rows) in enumerate(cases):
        x = 0.6 + i * 4.1
        box(s, x, 1.85, 3.85, 5.0, WHITE, LINE, 0.04)
        box(s, x, 1.85, 3.85, 0.08, color, None, 0)
        textbox(s, x + 0.2, 2.05, 3.5, 0.5, [(title, {"size": 13.5, "bold": True, "color": INK})])
        paras = []
        for label, body in rows:
            paras.append((label, {"size": 11.5, "bold": True, "color": color, "space": 2}))
            paras.append((body, {"size": 12.5, "color": BODY, "space": 12}))
        textbox(s, x + 0.2, 2.6, 3.5, 4.2, paras)
    notes(s, """
가장 기억에 남는 건 첫 번째 사례입니다. 코드를 하나도 안 바꿨는데 Docker 빌드가 실패했습니다.
로그를 보니 Ubuntu 폰트 패키지를 찾고 있었는데, 저는 Debian 기반 이미지를 쓰고 있었거든요.
추측으로 고치지 않고 Playwright 소스에서 OS별 의존성 목록을 직접 확인했더니, 그 버전은 Debian 12까지만 지원했고,
그 사이에 slim 태그가 Debian 13으로 바뀌어 있었습니다. 이미지를 Debian 12로 고정해서 해결했고, 그 뒤로는 기본 이미지 버전을 고정하고 있습니다.
두 번째는 설정 파일 문제입니다. 키를 비워 뒀는데 AI 파서가 Gemini로 잡혀 있었습니다.
원인은 빈 값 뒤에 붙인 주석이 값으로 읽힌 것이었습니다. 헬스 체크 응답에 현재 파서 종류를 일부러 노출해 뒀기 때문에 바로 발견할 수 있었습니다.
세 번째는 운영에서만 나는 문제들입니다. TiDB는 TLS가 필수였고, Gemini는 사용량이 몰리면 503을 돌려줬고,
컨테이너 안의 로봇은 포트가 달라 자기 자신을 찾지 못했습니다.
공통적으로 운영 DB를 직접 건드리지 않고 임시 DB로 검증했고, 고친 뒤에는 같은 상황을 재현하는 테스트를 추가했습니다.
""")


def s14_docs(prs):
    s = base(prs, 14, "13 · 프로젝트 산출물 및 문서화 관리", "여럿이 개발할수록 '왜 그렇게 했는지'를 남긴다")
    tree = """docs/
├── md/
│   ├── 2026-11-16_착수.md
│   ├── 2026-11-17_1차_구현.md
│   └── 2026-11-17_발표자료_구성안.md
├── 산출물/  (01 기획분석 ~ 05 피드백)
├── 프로젝트_진행일지_1~5단계.hwpx
├── scripts/  (발표자료 · 화면 캡처)
├── video/  (10분 발표·시연 영상)
├── assets/screenshots/
├── pdf/프로젝트_발표자료.pdf
└── 프로젝트_발표자료.pptx

AGENTS.md
readme.md"""
    shp = box(s, 0.6, 1.8, 6.6, 4.9, "0F172A", None, 0.03)
    tf = shp.text_frame
    tf.margin_left = Inches(0.3)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    write(tf, [(line, {"size": 12, "color": "E2E8F0", "mono": True, "space": 1}) for line in tree.splitlines()])
    textbox(s, 7.55, 1.8, 5.15, 4.9, bullets([
        "**5단계 관리** — 기획분석 → 설계 → 구현 → 배포 → 피드백별 진행일지 · 산출물",
        "**작업일 기록** — 결정 사항 · 검증 결과 · 이슈와 해결 · 다음 작업",
        "**재현 가능한 발표자료** — 이 슬라이드도 스크립트로 생성 (화면 캡처는 로컬 데모 인스턴스)",
        "**운영 메모** — .env 주석 규칙, TiDB SSL 필수 등 재발 방지 사항을 AGENTS.md 에 기록",
        "**커밋 메시지** — '무엇'보다 '왜' 중심",
    ], size=13), space=9)
    notes(s, """
여럿이 나눠 개발하면 결정한 이유가 더 쉽게 흩어집니다.
그래서 작업한 날마다 무엇을 결정했고, 어떻게 검증했고, 무엇이 터졌는지를 마크다운으로 남겼고, 단계별 진행일지와 산출물을 따로 관리했습니다.
오늘 보여 드린 트러블슈팅 내용도 이 기록에서 그대로 가져왔고, 이 발표자료 자체도 스크립트로 다시 만들 수 있게 해 두었습니다.
""")


def s15_retro(prs):
    s = base(prs, 15, "14 · 회고 및 향후 고도화 계획", "한계를 먼저 말하고, 개선 순서를 제시한다")
    card(s, 0.6, 1.8, 5.9, 1.25, [
        ("Keep", {"size": 13, "bold": True, "color": GREEN, "space": 3}),
        ("대체 경로 설계(텍스트 → OCR → Vision, Gemini → 규칙), 화면 · 서버 이중 검증, 재발 방지 테스트", {"size": 11.5}),
    ], fill="ECFDF5", line="A7F3D0", pad=0.18)
    card(s, 0.6, 3.15, 5.9, 1.25, [
        ("Problem", {"size": 13, "bold": True, "color": ROSE, "space": 3}),
        ("실패 원인 대부분이 외부 의존성(이미지 태그 · LLM 가용성 · 플랫폼 포트) → 처음부터 버전 고정 · 재시도 설계 필요", {"size": 11.5}),
    ], fill="FFF1F2", line="FECDD3", pad=0.18)
    textbox(s, 0.6, 4.55, 5.9, 2.4, [
        ("현재 한계", {"size": 13, "bold": True, "color": INK, "space": 4}),
        *bullets([
            "RPA · LLM 이 API 요청 안에서 동기 실행",
            "업로드 원본이 컨테이너 디스크에 저장 (재배포 시 유실 가능)",
            "스키마 변경을 create_all 로 처리 (마이그레이션 없음)",
            "파싱 품질은 샘플 단위 검증 (정량 평가셋 없음) · 데모 ERP 대상",
        ], size=11.5),
    ], space=3)
    textbox(s, 6.9, 1.8, 5.8, 0.4, [("고도화 로드맵", {"size": 15, "bold": True, "color": INK})])
    roadmap = [
        ("RPA 작업 큐 분리", "워커 프로세스 + 진행 상태 조회, rpa 패키지 분리로 이전 비용 낮음"),
        ("오브젝트 스토리지", "원본 문서를 S3 등으로 이전, 보존 기간 정책"),
        ("마이그레이션", "Alembic 도입"),
        ("정량 평가", "문서 유형별 정답셋 → 필드 단위 정확도, 프롬프트 · 모델 비교"),
        ("실제 ERP 커넥터", "API 우선, 없으면 RPA · 조직(테넌트) 단위 권한"),
    ]
    for i, (title, body) in enumerate(roadmap):
        y = 2.35 + i * 0.9
        num = box(s, 6.9, y + 0.05, 0.42, 0.42, BRAND, None, 0.5, shape=MSO_SHAPE.OVAL)
        write(num.text_frame, [(str(i + 1), {"size": 12, "bold": True, "color": WHITE, "align": PP_ALIGN.CENTER})])
        num.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        if i < 4:
            arrow(s, 7.11, y + 0.5, 7.11, y + 0.92, BRAND_200, 1.25)
        textbox(s, 7.5, y, 5.2, 0.85, [
            (title, {"size": 13, "bold": True, "color": INK, "space": 1}),
            (body, {"size": 11, "color": BODY}),
        ])
    notes(s, """
돌아보면 저희 코드 자체보다 외부 요인에서 더 많이 실패했습니다. 이미지 태그, LLM 서버 상태, 플랫폼 포트 같은 것들이요.
그래서 다음 프로젝트에서는 처음부터 버전을 고정하고 재시도 정책을 먼저 설계할 생각입니다.
현재 한계도 분명히 알고 있습니다. 가장 큰 건 RPA가 API 요청 안에서 동기로 돈다는 점이라, 첫 번째 과제로 작업 큐 분리를 잡았습니다.
RPA 코드를 처음부터 별도 패키지로 분리해 둔 덕분에 이전 비용은 크지 않을 거라고 봅니다.
그리고 지금은 정확도를 샘플로만 확인했기 때문에, 정답셋을 만들어 필드 단위로 측정하는 것도 다음 단계에 넣었습니다.
""")


def s16_qna(prs, qrs):
    s = dark(prs)
    textbox(s, 0.9, 0.9, 8, 1.0, [("Q & A", {"size": 54, "bold": True, "color": WHITE})])
    textbox(s, 0.9, 2.0, 11.5, 0.6, [("형식이 제각각인 문서 → 검수 가능한 정형 데이터 → 로봇이 ERP · 엑셀에 입력",
                                      {"size": 20, "bold": True, "color": BRAND_200})])
    rows = [("서비스", "https://dataquill.onrender.com"), ("API 문서", "https://dataquill-api.onrender.com/docs"),
            ("GitHub", "https://github.com/fsclass-n/dataquill"), ("일반 사용자", "user@dataquill.io  /  User1234!"),
            ("테스트 관리자", "admin@dataquill.io  /  Admin1234!  (조회 전용)")]
    for i, (label, value) in enumerate(rows):
        y = 3.0 + i * 0.52
        textbox(s, 0.9, y, 1.6, 0.45, [(label, {"size": 13, "bold": True, "color": "A5B4FC"})], anchor=MSO_ANCHOR.MIDDLE)
        textbox(s, 2.5, y, 5.6, 0.45, [(value, {"size": 13, "color": WHITE, "mono": True})], anchor=MSO_ANCHOR.MIDDLE)
    textbox(s, 0.9, 5.85, 7.2, 0.8, [
        ("검증: pytest 30개 · 운영 점검(로그인 · CORS · OAuth Redirect · Gemini 파싱 · 엑셀 적재)", {"size": 12, "color": "C7D2FE"}),
        ("로그인 화면의 테스트 계정 버튼으로 가입 없이 바로 체험할 수 있습니다.", {"size": 12, "color": "C7D2FE"}),
    ])
    qr_block(s, qrs, 8.35, 3.05)
    notes(s, """
화면의 테스트 계정 버튼으로 바로 들어가 보실 수 있습니다. 테스트 관리자 계정으로 들어가시면 모니터링과 회원 관리 화면을 조회하실 수 있습니다.
질문 받겠습니다.
""")


def s17_appendix(prs):
    s = base(prs, "부록", "부록 · 예상 질문과 답변", "Q&A 대비 핵심 답변")
    rows = [
        ["예상 질문", "핵심 답변"],
        ["AI 가 틀린 값을 넣으면?", "추측 금지 프롬프트 + Pydantic 스키마 강제 + 신뢰도 표시, 사람 검수 후에만 RPA (파싱 완료 상태만, 그 외 409)"],
        ["RPA 가 화면 변경에 약하지 않나?", "셀렉터 맵 분리, 결과 요소(data-status · 전표번호)로 성공 판정. API 가 있는 ERP 는 API 우선"],
        ["동시 요청이 많아지면?", "RPA · LLM 동기 실행이 병목 → 작업 큐 + 워커 분리 계획. 웹 계층은 무상태라 수평 확장 가능"],
        ["JWT 를 localStorage 에 두면?", "XSS 에 취약함을 인지. 개선안: HttpOnly 쿠키 + 짧은 만료 + 리프레시 토큰 (도메인 분리로 SameSite · CSRF 설계 필요)"],
        ["왜 TiDB 인가?", "MySQL 호환이라 코드 변경 없음, 무료 관리형 Serverless. URL 만 바꿔 MySQL 로 이전 가능"],
        ["파싱 정확도는?", "샘플 단위 검증까지 완료(운영 샘플 신뢰도 0.98). 정답셋 구축 후 측정 예정이라 수치로 주장하지 않음"],
        ["개인정보 보안은?", "업로드 크기 · 확장자 제한, 본인 문서만 조회, 비밀 값 저장소 외부 관리. 암호화 저장 · 보존 정책은 개선 과제"],
        ["테스트 전략은?", "API 통합 테스트 30개(인증 · OAuth state · 업로드→파싱→엑셀 · 권한 · 읽기 전용 관리자 · 통계 · Gemini 재시도), 외부 키 격리"],
        ["무료 플랜 콜드 스타트는?", "유휴 시 잠듦 → 데모 전 /api/health 로 깨움. 운영 전환 시 유료 플랜 또는 헬스 체크 핑"],
    ]
    table(s, 0.6, 1.8, 12.1, rows, [3.1, 9.0], size=11, row_h=0.5)
    notes(s, "예상 질문 대비용 백업 슬라이드입니다. 발표 시간에는 넘기고, 질문이 나오면 해당 행을 근거로 답합니다.")


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    prs.core_properties.title = "dataquill 프로젝트 결과 발표"
    prs.core_properties.author = "3조 (박미금 · 김모란 · 이오리 · 홍기흥)"
    qrs = make_qr_codes()
    s01_cover(prs, qrs)
    for build in (s02_problem, s03_solution, s04_architecture, s05_stack, s06_pipeline, s07_ai, s08_auth,
                  s09_flow, s10_ui, s11_admin, s12_devops, s13_trouble, s14_docs, s15_retro):
        build(prs)
    s16_qna(prs, qrs)
    s17_appendix(prs)
    prs.save(OUTPUT)
    print(f"saved {OUTPUT} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
