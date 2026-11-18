"""HWPX(OWPML) 문서를 표준 보고서 디자인으로 직접 생성한다.

한글 HTML 가져오기는 CSS(글꼴 · 문단 간격 · 셀 여백 · 배경색)를 대부분 무시하므로,
글자 · 문단 · 테두리 모양을 header.xml 에 직접 정의하고 본문(section0.xml)을 작성한다.
생성한 파일은 한글(HWP COM)로 열어 다시 저장해 줄 배치 정보를 갱신한 뒤 PDF 로 내보낸다.

디자인 기준 (docs/산출물 공통)
- 글꼴: 맑은 고딕 (코드 블록의 영문만 Consolas)
- 제목 20pt · 대제목 15pt · 중제목 12.5pt · 소제목 11pt · 본문 10pt · 캡션 9pt, 본문 줄 간격 160%
- 대제목 위 14pt · 아래 9pt, 중제목 위 8pt · 아래 4pt, 본문 아래 4pt, 불릿 아래 2.5pt (빈 줄 대신 문단 여백 사용)
- 표: 짙은 녹색 제목 행 + 흰 글자, 셀 여백 상하 2mm · 좌우 2.5mm, 제목 행 반복, 셀 단위 쪽 나눔,
  표 아래 6pt + 다음 대제목 위 14pt → 표와 번호 제목 사이 20pt 확보
- 제목 문단은 '다음 문단과 함께' 로 페이지 하단에 제목만 남지 않게 함
"""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path

PAGE_WIDTH, MARGIN_LR = 59528, 4535
TEXT_WIDTH = PAGE_WIDTH - MARGIN_LR * 2          # 50458 HWPUNIT (= 약 178mm)
TABLE_WIDTH = TEXT_WIDTH - 120
CELL_MARGIN = {"left": 709, "right": 709, "top": 567, "bottom": 567}   # 2.5mm / 2mm

PRIMARY, INK, MUTED = "#1B5E3B", "#222222", "#6B7280"
HEAD_BG, LABEL_BG, ZEBRA_BG, LINE, CODE_BG = "#1F5C3A", "#E8F0EB", "#F6F8F7", "#9DB3A6", "#F3F5F4"

# ---------------------------------------------------------------- 글자 모양 (id: 크기pt, 색, 굵게, 기울임, 고정폭)
CHAR = {
    "body": (0, 10, INK, False, False, False),
    "body_b": (1, 10, INK, True, False, False),
    "title": (2, 20, PRIMARY, True, False, False),
    "h1": (3, 15, PRIMARY, True, False, False),
    "h2": (4, 12.5, INK, True, False, False),
    "h3": (5, 11, "#333333", True, False, False),
    "caption": (6, 9, MUTED, False, True, False),
    "th": (7, 9.5, "#FFFFFF", True, False, False),
    "td": (8, 9.5, INK, False, False, False),
    "td_b": (9, 9.5, INK, True, False, False),
    "code": (10, 9, "#1F2937", False, False, True),
    "running": (11, 8.5, MUTED, False, False, False),
    "subtitle": (12, 11, "#4B5563", False, False, False),
    "accent": (13, 10, PRIMARY, True, False, False),
    "td_accent": (14, 9.5, PRIMARY, True, False, False),
}
# ---------------------------------------------------------------- 테두리 · 배경 (id: 선 색, 배경, 테두리 위치)
BORDER = {
    "none": (1, None, None, ()),
    "char": (2, None, None, ()),
    "table": (3, LINE, None, ("l", "r", "t", "b")),
    "th": (4, HEAD_BG, HEAD_BG, ("l", "r", "t", "b")),
    "td": (5, LINE, None, ("l", "r", "t", "b")),
    "td_zebra": (6, LINE, ZEBRA_BG, ("l", "r", "t", "b")),
    "td_label": (7, LINE, LABEL_BG, ("l", "r", "t", "b")),
    "code": (8, "#D3DCD6", CODE_BG, ("l", "r", "t", "b")),
    "h1_rule": (9, PRIMARY, None, ("b",)),
    "running_rule": (10, "#C9D3CD", None, ("b",)),
}
# ---------------------------------------------------------------- 문단 모양 (id: 정렬, 위, 아래, 줄간격%, 왼쪽, 들여쓰기, 다음과함께, 줄보호, 테두리)
PARA = {
    "body": (0, "LEFT", 0, 400, 160, 0, 0, False, False, "none"),
    "bullet": (1, "LEFT", 0, 250, 160, 600, -1000, False, False, "none"),
    "title": (2, "CENTER", 0, 300, 130, 0, 0, True, True, "none"),
    "h1": (3, "LEFT", 1400, 800, 130, 0, 0, True, True, "none"),
    "h2": (4, "LEFT", 800, 400, 130, 0, 0, True, True, "none"),
    "h3": (5, "LEFT", 600, 300, 130, 0, 0, True, True, "none"),
    "caption": (6, "LEFT", 150, 600, 140, 0, 0, False, False, "none"),
    "cell_l": (7, "LEFT", 0, 0, 140, 0, 0, False, False, "none"),
    "cell_c": (8, "CENTER", 0, 0, 140, 0, 0, False, False, "none"),
    "cell_r": (9, "RIGHT", 0, 0, 140, 0, 0, False, False, "none"),
    "code": (10, "LEFT", 0, 0, 135, 0, 0, False, False, "none"),
    "table": (11, "LEFT", 200, 600, 100, 0, 0, False, False, "none"),
    "running": (12, "RIGHT", 0, 0, 120, 0, 0, False, False, "running_rule"),
    "subtitle": (13, "CENTER", 0, 700, 140, 0, 0, True, False, "none"),
    "first": (14, "LEFT", 0, 0, 100, 0, 0, False, False, "none"),
    "page_no": (15, "CENTER", 0, 0, 120, 0, 0, False, False, "none"),
    # 쪽 하단에 제목만 남는 경우(2차 배치 검사에서 발견) 제목 앞에서 쪽을 나눔
    "h1_pb": (16, "LEFT", 0, 800, 130, 0, 0, True, True, "none"),
    "h2_pb": (17, "LEFT", 0, 400, 130, 0, 0, True, True, "none"),
    "h3_pb": (18, "LEFT", 0, 300, 130, 0, 0, True, True, "none"),
    "table_inline": (19, "LEFT", 200, 700, 100, 0, 0, False, False, "none"),
}

FONT_FACES = ["맑은 고딕", "Consolas"]
LANGS = ["HANGUL", "LATIN", "HANJA", "JAPANESE", "OTHER", "SYMBOL", "USER"]


def _fontfaces() -> str:
    out = []
    for lang in LANGS:
        fonts = "".join(
            f'<hh:font id="{i}" face="{face}" type="TTF" isEmbedded="0"><hh:typeInfo familyType="{"FCAT_GOTHIC" if i == 0 else "FCAT_UNKNOWN"}" '
            f'weight="5" proportion="{3 if i == 0 else 9}" contrast="2" strokeVariation="0" armStyle="0" letterform="2" midline="0" xHeight="4"/></hh:font>'
            for i, face in enumerate(FONT_FACES))
        out.append(f'<hh:fontface lang="{lang}" fontCnt="{len(FONT_FACES)}">{fonts}</hh:fontface>')
    return f'<hh:fontfaces itemCnt="{len(LANGS)}">{"".join(out)}</hh:fontfaces>'


def _border_fills() -> str:
    items = []
    for _, (bid, color, fill, sides) in sorted(BORDER.items(), key=lambda kv: kv[1][0]):
        def side(tag, key):
            on = key in sides
            width = "0.4 mm" if bid == BORDER["h1_rule"][0] else "0.12 mm"
            return f'<hh:{tag} type="{"SOLID" if on else "NONE"}" width="{width}" color="{color or "#000000"}"/>'
        brush = f'<hc:fillBrush><hc:winBrush faceColor="{fill}" hatchColor="#999999" alpha="0"/></hc:fillBrush>' if fill else ""
        items.append(
            f'<hh:borderFill id="{bid}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            f'{side("leftBorder", "l")}{side("rightBorder", "r")}{side("topBorder", "t")}{side("bottomBorder", "b")}'
            f'<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>{brush}</hh:borderFill>')
    return f'<hh:borderFills itemCnt="{len(items)}">{"".join(items)}</hh:borderFills>'


def _char_props() -> str:
    items = []
    seven = lambda v: " ".join(f'{k}="{v}"' for k in ("hangul", "latin", "hanja", "japanese", "other", "symbol", "user"))
    for _, (cid, size, color, bold, italic, mono) in sorted(CHAR.items(), key=lambda kv: kv[1][0]):
        latin = 1 if mono else 0
        font_ref = f'hangul="0" latin="{latin}" hanja="0" japanese="0" other="{latin}" symbol="0" user="0"'
        items.append(
            f'<hh:charPr id="{cid}" height="{round(size * 100)}" textColor="{color}" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">'
            f'<hh:fontRef {font_ref}/><hh:ratio {seven(100)}/><hh:spacing {seven(0)}/><hh:relSz {seven(100)}/><hh:offset {seven(0)}/>'
            f'{"<hh:italic/>" if italic else ""}{"<hh:bold/>" if bold else ""}<hh:strikeout shape="3D" color="#000000"/></hh:charPr>')
    return f'<hh:charProperties itemCnt="{len(items)}">{"".join(items)}</hh:charProperties>'


def _para_props() -> str:
    items = []
    for _, (pid, align, prev, nxt, line, left, indent, keep_next, keep_lines, border) in sorted(PARA.items(), key=lambda kv: kv[1][0]):
        off_bottom = 150 if border in ("h1_rule", "running_rule") else 0
        items.append(
            f'<hh:paraPr id="{pid}" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="0" suppressLineNumbers="0" checked="0">'
            f'<hh:align horizontal="{align}" vertical="BASELINE"/><hh:heading type="NONE" idRef="0" level="0"/>'
            f'<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" widowOrphan="1" keepWithNext="{int(keep_next)}" '
            f'keepLines="{int(keep_lines)}" pageBreakBefore="{int(_.endswith("_pb"))}" lineWrap="BREAK"/><hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
            f'<hh:margin><hc:intent value="{indent}" unit="HWPUNIT"/><hc:left value="{left}" unit="HWPUNIT"/><hc:right value="0" unit="HWPUNIT"/>'
            f'<hc:prev value="{prev}" unit="HWPUNIT"/><hc:next value="{nxt}" unit="HWPUNIT"/></hh:margin>'
            f'<hh:lineSpacing type="PERCENT" value="{line}" unit="HWPUNIT"/>'
            f'<hh:border borderFillIDRef="{BORDER[border][0]}" offsetLeft="0" offsetRight="0" offsetTop="0" offsetBottom="{off_bottom}" connect="0" ignoreMargin="0"/></hh:paraPr>')
    return f'<hh:paraProperties itemCnt="{len(items)}">{"".join(items)}</hh:paraProperties>'


def build_header(template_header: str) -> str:
    ref = (f"<hh:refList>{_fontfaces()}{_border_fills()}{_char_props()}"
           '<hh:tabProperties itemCnt="1"><hh:tabPr id="0" autoTabLeft="0" autoTabRight="0"/></hh:tabProperties>'
           f"{_para_props()}"
           '<hh:styles itemCnt="1"><hh:style id="0" type="PARA" name="바탕글" engName="Normal" paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0" langID="1042" lockForm="0"/></hh:styles>'
           "</hh:refList>")
    return re.sub(r"<hh:refList>.*</hh:refList>", lambda _: ref, template_header, count=1, flags=re.S)


# ---------------------------------------------------------------- 본문
INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")


def _runs(text: str, base: str, strong: str) -> str:
    out = []
    for tok in INLINE.split(text):
        if not tok:
            continue
        style = base
        if tok.startswith("**") and tok.endswith("**"):
            tok, style = tok[2:-2], strong
        elif tok.startswith("`") and tok.endswith("`"):
            tok, style = tok[1:-1], strong
        out.append(f'<hp:run charPrIDRef="{CHAR[style][0]}"><hp:t>{html.escape(tok, quote=False)}</hp:t></hp:run>')
    return "".join(out) or f'<hp:run charPrIDRef="{CHAR[base][0]}"/>'


def _p(text: str, para: str, char: str, strong: str | None = None) -> str:
    return (f'<hp:p id="0" paraPrIDRef="{PARA[para][0]}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f"{_runs(text, char, strong or char)}</hp:p>")


class Document:
    def __init__(self, running_title: str, break_before: frozenset = frozenset()):
        self.running_title = running_title
        self.break_before = break_before
        self.body: list[tuple[str, str]] = []   # (종류, xml)
        self._tbl = 0

    # 텍스트
    def title(self, text, subtitle=None):
        self.body.append(("title", _p(text, "title", "title")))
        if subtitle:
            self.body.append(("subtitle", _p(subtitle, "subtitle", "subtitle")))

    def _heading(self, level, text):
        para = f"{level}_pb" if text in self.break_before else level
        self.body.append((level, _p(text, para, level)))

    def h1(self, text):
        self._heading("h1", text)

    def h2(self, text):
        self._heading("h2", text)

    def h3(self, text):
        self._heading("h3", text)

    def headings(self) -> list[str]:
        return [html.unescape("".join(re.findall(r"<hp:t>([^<]*)</hp:t>", x))) for k, x in self.body if k in ("h1", "h2", "h3")]

    def p(self, text):
        self.body.append(("body", _p(text, "body", "body", "body_b")))

    def bullets(self, items):
        for item in items:
            self.body.append(("bullet", _p(f"•  {item}", "bullet", "body", "body_b")))

    def caption(self, text):
        self.body.append(("caption", _p(text, "caption", "caption")))

    # 표
    def table(self, head, rows, widths=None, align=None, label_col=False, zebra=True):
        cols = len(head)
        align = align or ["L"] * cols
        if widths is None:
            avg = [sum(len(re.sub(r"\*\*|`", "", str(r[i]))) for r in [head, *rows]) / (len(rows) + 1) for i in range(cols)]
            widths = [min(max(a, 5), 48) for a in avg]
        total = sum(widths)
        px = [int(TABLE_WIDTH * w / total) for w in widths]
        px[-1] += TABLE_WIDTH - sum(px)

        def cell(r, c, value, header):
            if header:
                bf, para, char, strong = "th", "cell_c", "th", "th"
            else:
                bf = "td_label" if (label_col and c == 0) else ("td_zebra" if zebra and r % 2 == 0 else "td")
                para = {"L": "cell_l", "C": "cell_c", "R": "cell_r"}[align[c]]
                char, strong = ("td_b", "td_b") if (label_col and c == 0) else ("td", "td_accent")
            lines = str(value).split("\n")
            paras = "".join(_p(line, para, char, strong) for line in lines)
            return (f'<hp:tc name="" header="{int(header)}" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="{BORDER[bf][0]}">'
                    '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" '
                    f'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">{paras}</hp:subList>'
                    f'<hp:cellAddr colAddr="{c}" rowAddr="{r}"/><hp:cellSpan colSpan="1" rowSpan="1"/>'
                    f'<hp:cellSz width="{px[c]}" height="1400"/>'
                    f'<hp:cellMargin left="{CELL_MARGIN["left"]}" right="{CELL_MARGIN["right"]}" top="{CELL_MARGIN["top"]}" bottom="{CELL_MARGIN["bottom"]}"/></hp:tc>')

        all_rows = [head, *rows]
        trs = "".join("<hp:tr>" + "".join(cell(r, c, v, r == 0) for c, v in enumerate(row)) + "</hp:tr>" for r, row in enumerate(all_rows))
        self._append_table(trs, len(all_rows), cols, 1400 * len(all_rows))

    def meta(self, rows):
        self.table(["항목", "내용"], rows, widths=[18, 82], label_col=True, zebra=False)

    def code(self, text, caption=None):
        lines = text.strip("\n").split("\n")
        paras = "".join(_p(line if line.strip() else " ", "code", "code") for line in lines)
        tc = (f'<hp:tc name="" header="0" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="{BORDER["code"][0]}">'
              '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" '
              f'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">{paras}</hp:subList>'
              '<hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/>'
              f'<hp:cellSz width="{TABLE_WIDTH}" height="1400"/><hp:cellMargin left="850" right="850" top="567" bottom="567"/></hp:tc>')
        self._append_table(f"<hp:tr>{tc}</hp:tr>", 1, 1, 1400, repeat=False)
        if caption:
            self.caption(caption)

    def _append_table(self, trs, rows, cols, height, repeat=True):
        # 짧은 표는 '글자처럼 취급'(문단의 일부)으로 두어 제목의 '다음 문단과 함께' 가 표까지 적용되게 하고,
        # 긴 표는 떠 있는 개체로 두어 행 단위로 쪽을 나눈다(제목 행 반복).
        inline = rows <= self.SPLIT_ROWS
        self._tbl += 1
        tid = 1000 + self._tbl
        tbl = (f'<hp:tbl id="{tid}" zOrder="{self._tbl}" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
               f'dropcapstyle="None" pageBreak="{"NONE" if inline else "CELL"}" repeatHeader="{int(repeat)}" rowCnt="{rows}" colCnt="{cols}" cellSpacing="0" '
               f'borderFillIDRef="{BORDER["table"][0]}" noAdjust="0">'
               f'<hp:sz width="{TABLE_WIDTH}" widthRelTo="ABSOLUTE" height="{height}" heightRelTo="ABSOLUTE" protect="0"/>'
               f'<hp:pos treatAsChar="{int(inline)}" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
               'horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
               f'<hp:outMargin left="0" right="0" top="0" bottom="{"0" if inline else "@@OUT_BOTTOM@@"}"/>'
               f'<hp:inMargin left="{CELL_MARGIN["left"]}" right="{CELL_MARGIN["right"]}" top="{CELL_MARGIN["top"]}" bottom="{CELL_MARGIN["bottom"]}"/>'
               f"{trs}</hp:tbl>")
        self.body.append(("table", f'<hp:p id="0" paraPrIDRef="{PARA["table_inline" if inline else "table"][0]}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                                   f'<hp:run charPrIDRef="{CHAR["body"][0]}">{tbl}<hp:t/></hp:run></hp:p>'))

    # 표는 본문 위에 떠 있는 개체라 다음 문단의 '위 여백' 이 적용되지 않는다 → 표 바깥 아래 여백으로 간격 확보
    # 15행 이하 표는 쪽을 나누지 않음 → 제목 + 제목 행만 페이지 하단에 남는 현상 방지
    SPLIT_ROWS = 15
    GAP_AFTER_TABLE = {"h1": 1400, "h2": 1000, "h3": 900, "table": 700, "caption": 150, None: 0}

    def _body_xml(self) -> str:
        out = []
        for i, (kind, xml) in enumerate(self.body):
            if kind == "table":
                nxt = self.body[i + 1][0] if i + 1 < len(self.body) else None
                xml = xml.replace("@@OUT_BOTTOM@@", str(self.GAP_AFTER_TABLE.get(nxt, 700)))
            out.append(xml)
        return "".join(out)

    # 저장
    def _section(self, template_section: str) -> str:
        root = re.match(r"(<\?xml[^>]*\?>\s*<hs:sec [^>]*>)", template_section).group(1)
        sec_pr = re.search(r"<hp:secPr .*?</hp:secPr>", template_section, re.S).group(0)
        col_pr = re.search(r"<hp:ctrl><hp:colPr [^>]*/></hp:ctrl>", template_section).group(0)
        sec_pr = re.sub(r'<hp:margin header="\d+" footer="\d+"', '<hp:margin header="2268" footer="1700"', sec_pr)
        sub = ('<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" '
               f'textWidth="{TEXT_WIDTH}" textHeight="{{h}}" hasTextRef="0" hasNumRef="0">')
        page_no = (f'<hp:p id="0" paraPrIDRef="{PARA["page_no"][0]}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                   f'<hp:run charPrIDRef="{CHAR["running"][0]}"><hp:t>- </hp:t></hp:run>'
                   f'<hp:run charPrIDRef="{CHAR["running"][0]}"><hp:ctrl><hp:autoNum num="1" numType="PAGE">'
                   '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar="" supscript="0"/></hp:autoNum></hp:ctrl></hp:run>'
                   f'<hp:run charPrIDRef="{CHAR["running"][0]}"><hp:t> -</hp:t></hp:run></hp:p>')
        running = (f'<hp:ctrl><hp:header id="1" applyPageType="BOTH">{sub.format(h=2268)}'
                   f'{_p(self.running_title, "running", "running")}</hp:subList></hp:header></hp:ctrl>'
                   f'<hp:ctrl><hp:footer id="2" applyPageType="BOTH">{sub.format(h=1700)}{page_no}</hp:subList></hp:footer></hp:ctrl>')
        first = (f'<hp:p id="0" paraPrIDRef="{PARA["first"][0]}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                 f'<hp:run charPrIDRef="{CHAR["body"][0]}">{sec_pr}{col_pr}{running}</hp:run></hp:p>')
        return f"{root}{first}{self._body_xml()}</hs:sec>"

    def save(self, template_hwpx: Path, out: Path) -> None:
        with zipfile.ZipFile(template_hwpx) as z:
            items = {n: z.read(n) for n in z.namelist()}
            infos = {i.filename: i for i in z.infolist()}
        items["Contents/header.xml"] = build_header(items["Contents/header.xml"].decode("utf-8")).encode("utf-8")
        items["Contents/section0.xml"] = self._section(items["Contents/section0.xml"].decode("utf-8")).encode("utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w") as z:
            for name, data in items.items():
                info = infos[name]
                z.writestr(info, data, compress_type=zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED)

    def plain_text(self) -> str:
        """PDF 와 내용 비교용 본문 텍스트"""
        return " ".join(html.unescape(t) for t in re.findall(r"<hp:t>([^<]*)</hp:t>", self._body_xml()))
