"""AI 도구 3종: 견적서 비교기 · 계약서 빨간펜 · 건강검진 추이 비교기.

공통 원칙: AI(Gemini)는 문서에서 값을 '읽기'만 하고, 비교·판정은 이 모듈의 규칙 코드가 결정적으로 계산한다.
GEMINI_API_KEY 가 없으면 정규식 규칙 추출기로 동작한다(텍스트가 있는 문서만).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from statistics import median
from typing import Literal

from pydantic import BaseModel, Field

from rpa import extract

from ..config import settings
from .parser import ParseError, generate_structured

Engine = Literal["gemini", "rules"]
_DATE = re.compile(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})")
_NUM = r"(\d+(?:\.\d+)?)"


def _iso(match: re.Match | None) -> str | None:
    return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}" if match else None


def _int(value: str | None) -> int | None:
    return int(value.replace(",", "")) if value else None


def read_document(filename: str, data: bytes) -> tuple[str, bytes | None, str | None]:
    """원문 텍스트를 뽑고, 텍스트가 없으면 Gemini 멀티모달용 원본 바이트를 함께 돌려준다."""
    result = extract.extract(filename, data)
    if not result.needs_vision:
        return result.text, None, None
    if not settings.gemini_api_key:
        raise ParseError(f"'{filename}' 에서 글자를 읽지 못했습니다. 스캔본·사진은 GEMINI_API_KEY 가 설정된 서버에서만 해석할 수 있습니다.")
    return result.text, data, result.mime_type


def _engine() -> Engine:
    return "gemini" if settings.gemini_api_key else "rules"


# ─────────────────────────────── 견적서 비교기 ───────────────────────────────

class QuoteItem(BaseModel):
    name: str = Field(description="품목명(문서에 적힌 그대로)")
    quantity: float | None = None
    unit: str | None = Field(default=None, description="단위(식, 개, ㎡ 등)")
    unit_price: int | None = Field(default=None, description="단가(원 단위 정수)")
    amount: int | None = Field(default=None, description="금액(원 단위 정수)")


class QuoteDoc(BaseModel):
    vendor: str | None = Field(default=None, description="견적 업체명")
    date: str | None = Field(default=None, description="견적일 YYYY-MM-DD")
    items: list[QuoteItem] = []
    total_amount: int | None = Field(default=None, description="견적 총액(원 단위 정수)")
    notes: str | None = Field(default=None, description="유효기간·결제조건·하자보수 등 특이사항 한 줄")


QUOTE_PROMPT = """당신은 구매 담당자입니다. 아래 견적서에서 업체명, 견적일, 품목별 수량·단위·단가·금액, 총액, 특이사항을 JSON 으로 추출하세요.
- 금액은 쉼표와 통화 기호를 제거한 정수로 표기합니다. 날짜는 YYYY-MM-DD 로 변환합니다.
- 소계·부가세·합계 줄은 품목에 넣지 않습니다. 문서에 없는 값은 null 로 둡니다. 추측하지 마세요.
"""
OUTLIER_PCT = 20
_QUOTE_ITEM = re.compile(
    r"^(?P<name>.+?)\s+(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>[가-힣a-zA-Z㎡]{0,4})\s+(?P<price>[\d,]+)\s+(?P<amount>[\d,]+)\s*원?$"
)
_QUOTE_SKIP = re.compile(r"^(합\s*계|소\s*계|총\s*액|부가세|공급가액|품목|항목)")
_QUOTE_VENDOR = re.compile(r"(?:공급자|업체명|상호|견적처|회사명)\s*[:：]\s*(.+)")
_QUOTE_TOTAL = re.compile(r"(?:합\s*계|총\s*액|견적\s*금액|총\s*견적)[^\d\n]{0,15}([\d,]{3,})")
_QUOTE_NOTE = re.compile(r"(?:유효\s*기간|결제\s*조건|하자\s*보수|비고|특이\s*사항)\s*[:：]\s*(.+)")


def extract_quote_rules(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items = []
    for line in lines:
        if _QUOTE_SKIP.match(line):
            continue
        m = _QUOTE_ITEM.match(line)
        if m:
            items.append(QuoteItem(name=m["name"].strip(), quantity=float(m["qty"]), unit=m["unit"] or None,
                                   unit_price=_int(m["price"]), amount=_int(m["amount"])))
    if not items:
        raise ParseError("견적 품목(품목명 · 수량 · 단가 · 금액)을 찾지 못했습니다.")
    vendor = _QUOTE_VENDOR.search(text)
    total = _QUOTE_TOTAL.search(text)
    notes = [m.group(0) for m in _QUOTE_NOTE.finditer(text)]
    first = next((line for line in lines if "견적" not in line), lines[0])
    return QuoteDoc(
        vendor=(vendor.group(1).strip() if vendor else first)[:100],
        date=_iso(_DATE.search(text)),
        items=items,
        total_amount=_int(total.group(1)) if total else sum(i.amount or 0 for i in items),
        notes=" · ".join(notes)[:300] or None,
    ).model_dump()


def _norm(name: str) -> str:
    return re.sub(r"[\s()\[\]{}·,./\-_~]", "", name).lower()


def _similar(a: str, b: str) -> float:
    """문자 순서 유사도와 2글자 조각 겹침(dice) 중 큰 값. '도장(문틀)' ↔ '문틀 도장' 처럼 어순이 달라도 맞춘다."""
    grams_a, grams_b = ({x[i:i + 2] for i in range(len(x) - 1)} for x in (a, b))
    dice = 2 * len(grams_a & grams_b) / (len(grams_a) + len(grams_b)) if grams_a and grams_b else 0
    return max(SequenceMatcher(None, a, b).ratio(), dice)


def compare_quotes(quotes: list[dict]) -> dict:
    """품목을 이름으로 맞춰 단가를 나란히 놓고, 최저가 대비 이상 단가·누락 품목·총액 차이를 계산한다."""
    groups: list[dict] = []
    for qi, quote in enumerate(quotes):
        for item in quote["items"]:
            key = _norm(item["name"])
            candidates = [g for g in groups if qi not in g["cells"]]
            best = max(candidates, key=lambda g: _similar(key, g["key"]), default=None)
            if not best or _similar(key, best["key"]) < 0.6:
                best = {"key": key, "name": item["name"], "cells": {}}
                groups.append(best)
            price = item.get("unit_price")
            if price is None and item.get("amount") and item.get("quantity"):
                price = round(item["amount"] / item["quantity"])
            best["cells"][qi] = {"unit_price": price, "quantity": item.get("quantity"), "unit": item.get("unit"), "amount": item.get("amount")}

    vendors = [q.get("vendor") or f"견적 {i + 1}" for i, q in enumerate(quotes)]
    rows, insights, outliers = [], [], 0
    for g in groups:
        prices = {i: c["unit_price"] for i, c in g["cells"].items() if c["unit_price"]}
        low = min(prices.values()) if prices else None
        cells = []
        for qi in range(len(quotes)):
            cell = g["cells"].get(qi)
            if not cell:
                cells.append({"flag": "missing"})
                continue
            pct = round((cell["unit_price"] / low - 1) * 100, 1) if low and cell["unit_price"] else None
            flag = None
            if len(prices) >= 2 and cell["unit_price"] == low:
                flag = "lowest"
            elif pct is not None and pct >= OUTLIER_PCT:
                flag = "outlier"
                outliers += 1
                insights.append(f"'{g['name']}' 단가가 {vendors[qi]} 견적에서 최저가보다 {pct:g}% 높습니다.")
            cells.append({**cell, "diff_pct": pct, "flag": flag})
        rows.append({"name": g["name"], "cells": cells, "lowest": low, "median": median(prices.values()) if prices else None})

    totals = [q.get("total_amount") or sum(i.get("amount") or 0 for i in q["items"]) for q in quotes]
    common = [r for r in rows if all(c.get("flag") != "missing" for c in r["cells"])]
    common_totals = [sum(r["cells"][qi].get("amount") or 0 for r in common) for qi in range(len(quotes))]
    cheapest = min(range(len(quotes)), key=lambda i: totals[i]) if quotes else None
    savings = max(totals) - min(totals) if quotes else 0
    missing = {qi: [r["name"] for r in rows if r["cells"][qi].get("flag") == "missing"] for qi in range(len(quotes))}
    if cheapest is not None and len(quotes) >= 2:
        insights.insert(0, f"총액은 {vendors[cheapest]} 견적이 가장 낮습니다. 가장 비싼 견적보다 {savings:,}원 적습니다.")
        if missing[cheapest]:
            insights.insert(1, f"단, {vendors[cheapest]} 견적에는 {', '.join(missing[cheapest])} 항목이 빠져 있어 실제 비용은 더 들 수 있습니다.")
    for qi, names in missing.items():
        if qi != cheapest and names:
            insights.append(f"{vendors[qi]} 견적에는 {', '.join(names)} 항목이 없습니다.")
    return {
        "vendors": vendors,
        "rows": rows,
        "totals": totals,
        "common_totals": common_totals,
        "common_items": len(common),
        "cheapest": cheapest,
        "savings": savings,
        "outliers": outliers,
        "missing": {vendors[qi]: names for qi, names in missing.items() if names},
        "outlier_threshold_pct": OUTLIER_PCT,
        "insights": insights,
    }


def analyze_quotes(files: list[tuple[str, bytes]]) -> tuple[dict, Engine]:
    quotes = []
    for filename, data in files:
        text, file_bytes, mime = read_document(filename, data)
        try:
            doc = (generate_structured(QUOTE_PROMPT, QuoteDoc, text, file_bytes, mime).model_dump()
                   if settings.gemini_api_key else extract_quote_rules(text))
        except ParseError as exc:
            raise ParseError(f"'{filename}': {exc}") from exc
        if not doc["items"]:
            raise ParseError(f"'{filename}' 에서 견적 품목을 찾지 못했습니다.")
        quotes.append({**doc, "filename": filename})
    return {"quotes": quotes, "comparison": compare_quotes(quotes)}, _engine()


# ─────────────────────────────── 계약서 빨간펜 ───────────────────────────────

Category = Literal["auto_renewal", "penalty", "termination", "liability", "payment", "ip", "non_compete",
                   "confidentiality", "jurisdiction", "other"]
Risk = Literal["high", "medium", "low"]
CATEGORY_LABELS = {
    "auto_renewal": "자동 연장", "penalty": "위약금 · 손해배상", "termination": "일방 해지 · 변경", "liability": "책임 제한 · 면책",
    "payment": "대금 · 지연이자", "ip": "권리 귀속", "non_compete": "경업 금지", "confidentiality": "비밀 유지",
    "jurisdiction": "관할 · 분쟁", "other": "기타",
}


class RiskClause(BaseModel):
    title: str = Field(description="조항 제목 (예: 제5조(계약기간))")
    quote: str = Field(description="위험 문장 원문을 한 글자도 바꾸지 말고 그대로 발췌")
    category: Category
    risk: Risk
    explanation: str = Field(description="법률 지식이 없는 사람도 이해할 쉬운 설명 1~2문장")
    suggestion: str | None = Field(default=None, description="서명 전 확인하거나 협상할 점 1문장")


class ContractReview(BaseModel):
    title: str | None = Field(default=None, description="계약서 제목")
    parties: list[str] = Field(default=[], description="계약 당사자")
    summary: str | None = Field(default=None, description="계약 내용 2문장 요약")
    clauses: list[RiskClause] = []


CONTRACT_PROMPT = """당신은 계약서를 처음 보는 일반인을 돕는 검토 도우미입니다. 아래 계약서에서 서명 전에 주의해야 할 조항을 찾으세요.
- 자동 연장, 위약금·손해배상 예정, 일방적 해지·중단, 책임 제한·면책, 과도한 지연이자, 결과물 권리 귀속, 경업 금지, 비밀 유지, 관할 법원을 우선 확인합니다.
- quote 는 계약서 원문 문장을 한 글자도 바꾸지 말고 그대로 옮깁니다(화면에서 원문에 빨간 줄을 긋는 데 사용).
- risk 는 계약 당사자 중 불리한 쪽(보통 서명하는 개인·소상공인) 기준으로 high/medium/low 를 판단합니다.
- 법률 자문이 아니라 주의 표시입니다. 단정적 결론 대신 '확인하세요' 형태로 씁니다.
"""

CONTRACT_RULES: list[tuple[str, Risk, re.Pattern, str, str]] = [
    ("auto_renewal", "high", re.compile(r"자동\s*(?:으로\s*)?(?:연장|갱신)|동일한\s*조건으로\s*(?:연장|갱신)"),
     "만료 전에 해지 의사를 알리지 않으면 같은 조건으로 계약이 자동으로 이어집니다.",
     "해지 통보 기한을 달력에 적어 두고, '서면 합의 시에만 연장'으로 바꿀 수 있는지 확인하세요."),
    ("penalty", "high", re.compile(r"위약금|위약벌|손해배상\s*(?:액|의)?\s*예정|배액"),
     "계약을 중간에 끝내거나 약속을 어기면 정해진 돈을 물어야 합니다.",
     "위약금 산정 기준(남은 기간 전체인지, 실제 손해인지)과 상한이 합리적인지 확인하세요."),
    ("termination", "high", re.compile(r"(?:일방적으로|사전\s*통보\s*없이|통지\s*없이|즉시)[^.]{0,20}(?:해지|해제|중단|변경)"),
     "상대방이 미리 알리지 않고 계약을 끝내거나 내용을 바꿀 수 있습니다.",
     "해지 사유를 구체적으로 한정하고, 같은 권리가 양쪽 모두에게 있는지 확인하세요."),
    ("non_compete", "high", re.compile(r"경업|동종\s*업종[^.]{0,25}(?:금지|하지\s*않|할\s*수\s*없)"),
     "계약이 끝난 뒤에도 같은 업종의 일을 하지 못하게 제한합니다.",
     "제한 기간 · 지역 · 업종 범위가 지나치게 넓지 않은지 확인하세요."),
    ("liability", "medium", re.compile(r"책임[을도은]?\s*지지\s*않|면책|책임이\s*없"),
     "문제가 생겨도 상대방이 책임을 지지 않는다는 조항입니다.",
     "고의 · 중대한 과실까지 면책되는지, 배상 한도가 너무 낮지 않은지 확인하세요."),
    ("payment", "medium", re.compile(r"지연\s*(?:손해금|이자)|연체\s*(?:료|이자)|연\s*\d+(?:\.\d+)?\s*%"),
     "대금을 늦게 내면 추가 이자나 연체료가 붙습니다.",
     "지연 이율이 법정 이율(상사 연 6%)보다 과도하지 않은지 확인하세요."),
    ("ip", "medium", re.compile(r"(?:지식\s*재산권|저작권|소유권)[^.]{0,25}(?:귀속|양도|이전)"),
     "결과물에 대한 권리가 누구에게 가는지 정한 조항입니다.",
     "대금을 다 받기 전에 권리가 넘어가지 않는지, 기존에 가진 기술까지 넘어가지 않는지 확인하세요."),
    ("confidentiality", "low", re.compile(r"비밀\s*유지|기밀"),
     "업무 중 알게 된 정보를 외부에 알리면 안 됩니다.",
     "비밀 정보의 범위와 유지 기간이 명확한지 확인하세요."),
    ("jurisdiction", "low", re.compile(r"관할\s*법원|전속\s*관할|중재"),
     "분쟁이 생기면 어느 법원에서 다툴지 정한 조항입니다.",
     "상대방 소재지 법원으로만 정해져 있으면 소송 비용이 커질 수 있습니다."),
]
RISK_POINTS = {"high": 3, "medium": 2, "low": 1}
MAX_CONTRACT_CHARS = 30000
_CLAUSE_HEAD = re.compile(r"^\s*(제\s*\d+\s*조[^\n]*)", re.M)
_PARTY = re.compile(r"(\S+(?:\s\S+)?)\s*\(이하\s*[\"“']?(갑|을|병)[\"”']?\)")
_SENTENCE = re.compile(r"[^.。]+(?:[.。]|$)")
_HEADING_ONLY = re.compile(r"^\s*제\s*\d+\s*조\s*(?:\([^)]*\))?")


def _clauses(text: str) -> list[tuple[str, str, str]]:
    """(조항 제목, 제목 부분, 본문) 목록. '제N조(제목)' 이 없으면 빈 줄 단위 문단으로 나눈다."""
    heads = list(_CLAUSE_HEAD.finditer(text))
    if not heads:
        return [(part.strip()[:40], "", part) for part in text.split("\n\n") if part.strip()]
    result = []
    for i, m in enumerate(heads):
        body = text[m.start(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        head = _HEADING_ONLY.match(body)
        cut = head.end() if head else 0
        result.append(((head.group(0) if head else m.group(1)).strip()[:60], body[:cut], body[cut:]))
    return result


def _sentence_at(body: str, pos: int | None) -> str:
    sentences = list(_SENTENCE.finditer(body))
    chosen = next((m for m in sentences if pos is not None and m.start() <= pos < m.end()), sentences[0] if sentences else None)
    return " ".join((chosen.group(0) if chosen else body).split())


def review_contract_rules(text: str) -> dict:
    if len(text.strip()) < 30:
        raise ParseError("계약서 본문이 너무 짧습니다.")
    found = []
    for title, heading, body in _clauses(text):
        for category, risk, pattern, explanation, suggestion in CONTRACT_RULES:
            match = pattern.search(body)
            if not match and not pattern.search(heading):
                continue
            sentence = _sentence_at(body, match.start() if match else None)
            found.append(RiskClause(title=title, quote=sentence, category=category, risk=risk,
                                    explanation=explanation, suggestion=suggestion))
    first = next((line.strip() for line in text.splitlines() if line.strip()), None)
    parties = [f"{role}: {name}" for name, role in _PARTY.findall(text)]
    return ContractReview(title=first[:100] if first else None, parties=parties,
                          summary=None, clauses=found).model_dump()


def _flat(value: str) -> str:
    return "".join(value.split())


def _locate(text: str, quote: str) -> tuple[int, int] | None:
    start = text.find(quote)
    if start >= 0:
        return start, start + len(quote)
    words = [re.escape(w) for w in quote.split()]
    match = re.search(r"\s*".join(words), text) if words else None
    if match:
        return match.start(), match.end()
    # AI 가 한두 글자를 바꿔 옮긴 경우('필요한' → '필요할'): 공백을 무시하고 가장 비슷한 원문 문장(유사도 0.85 이상)에 표시
    target = _flat(quote)
    best, best_ratio = None, 0.85
    for sentence in _SENTENCE.finditer(text):
        raw = sentence.group(0)
        start = sentence.start() + len(raw) - len(raw.lstrip())
        head = _HEADING_ONLY.match(raw.lstrip())
        if head:
            rest = raw.lstrip()[head.end():]
            start += head.end() + len(rest) - len(rest.lstrip())
        body = text[start:sentence.end()].strip()
        ratio = SequenceMatcher(None, target, _flat(body)).ratio()
        if body and ratio >= best_ratio:
            best, best_ratio = (start, start + len(body)), ratio
    return best


def merge_with_rules(review: dict, text: str) -> dict:
    """AI 발췌 조항의 유형 · 위험도를 규칙으로 다시 정하고, AI 가 놓친 규칙 조항을 더한다(판정은 규칙 기준)."""
    clauses = []
    for clause in review["clauses"]:
        rule = next((r for r in CONTRACT_RULES if r[2].search(clause["quote"])), None)
        if rule:
            clause = {**clause, "category": rule[0], "risk": rule[1], "suggestion": clause.get("suggestion") or rule[4]}
        clauses.append(clause)
    for extra in review_contract_rules(text)["clauses"] if len(text.strip()) >= 30 else []:
        same = any(c["category"] == extra["category"] and SequenceMatcher(None, _flat(c["quote"]), _flat(extra["quote"])).ratio() > 0.6
                   for c in clauses)
        if not same:
            clauses.append(extra)
    return {**review, "clauses": clauses}


def score_contract(review: dict, text: str) -> dict:
    clauses = []
    for clause in review["clauses"]:
        span = _locate(text, clause["quote"])
        clauses.append({**clause, "label": CATEGORY_LABELS.get(clause["category"], "기타"),
                        "start": span[0] if span else None, "end": span[1] if span else None})
    order = {"high": 0, "medium": 1, "low": 2}
    clauses.sort(key=lambda c: (order[c["risk"]], c["start"] if c["start"] is not None else 10**9))
    counts = {level: sum(c["risk"] == level for c in clauses) for level in ("high", "medium", "low")}
    score = min(100, sum(RISK_POINTS[c["risk"]] for c in clauses) * 8)
    overall = "high" if counts["high"] >= 2 or score >= 60 else "medium" if counts["high"] or score >= 25 else "low"
    return {**review, "clauses": clauses, "counts": counts, "score": score, "overall": overall}


def analyze_contract(filename: str, data: bytes | None = None, text: str = "") -> tuple[dict, Engine]:
    file_bytes = mime = None
    if data is not None:
        text, file_bytes, mime = read_document(filename, data)
    if settings.gemini_api_key:
        review = merge_with_rules(generate_structured(CONTRACT_PROMPT, ContractReview, text, file_bytes, mime).model_dump(), text)
    else:
        review = review_contract_rules(text)
    shown = text[:MAX_CONTRACT_CHARS]
    return {"review": score_contract(review, shown), "text": shown}, _engine()


# ─────────────────────────────── 건강검진 추이 비교기 ───────────────────────────────

# code: (항목명, 단위, 별칭 정규식, 좋은 방향, 판정 기준)
#   ("lower", 주의 시작, 위험 시작) / ("higher", 주의 미만, 위험 미만) / ("range", 위험 하한, 주의 하한, 주의 상한, 위험 상한)
METRICS: dict[str, tuple] = {
    "systolic_bp": ("수축기 혈압", "mmHg", r"수축기\s*혈압|최고\s*혈압|수축기", "lower", ("lower", 120, 140)),
    "diastolic_bp": ("이완기 혈압", "mmHg", r"이완기\s*혈압|최저\s*혈압|이완기", "lower", ("lower", 80, 90)),
    "fasting_glucose": ("공복혈당", "mg/dL", r"공복\s*혈당|Glucose", "lower", ("lower", 100, 126)),
    "total_cholesterol": ("총콜레스테롤", "mg/dL", r"총\s*콜레스테롤|Total\s*Cholesterol", "lower", ("lower", 200, 240)),
    "ldl": ("LDL 콜레스테롤", "mg/dL", r"\bLDL\b|저밀도", "lower", ("lower", 130, 160)),
    "hdl": ("HDL 콜레스테롤", "mg/dL", r"\bHDL\b|고밀도", "higher", ("higher", 40, 40)),
    "triglyceride": ("중성지방", "mg/dL", r"중성\s*지방|Triglyceride", "lower", ("lower", 150, 200)),
    "ast": ("AST(SGOT)", "U/L", r"\bAST\b|SGOT", "lower", ("lower", 41, 51)),
    "alt": ("ALT(SGPT)", "U/L", r"\bALT\b|SGPT", "lower", ("lower", 36, 46)),
    "ggt": ("감마지티피", "U/L", r"감마\s*-?\s*지티피|감마\s*-?\s*GTP|γ\s*-?\s*GTP|\bGGT\b", "lower", ("lower", 64, 78)),
    "hemoglobin": ("혈색소", "g/dL", r"혈색소|헤모글로빈|Hemoglobin", None, ("range", 10, 12, 16.6, 18)),
    "creatinine": ("혈청 크레아티닌", "mg/dL", r"크레아티닌|Creatinine", "lower", ("lower", 1.6, 1.6)),
    "egfr": ("eGFR", "mL/min/1.73㎡", r"e\s*-?\s*GFR|신사구체\s*여과율", "higher", ("higher", 60, 45)),
    "bmi": ("체질량지수", "kg/㎡", r"체질량\s*지수|\bBMI\b", None, ("range", 0, 18.5, 23, 25)),
    "waist": ("허리둘레", "cm", r"허리\s*둘레", "lower", None),
    "weight": ("체중", "kg", r"체중|몸무게", None, None),
}
MetricCode = Literal[
    "systolic_bp", "diastolic_bp", "fasting_glucose", "total_cholesterol", "ldl", "hdl", "triglyceride", "ast", "alt",
    "ggt", "hemoglobin", "creatinine", "egfr", "bmi", "waist", "weight", "other",
]
STATUS_RANK = {"normal": 0, "caution": 1, "risk": 2}
STATUS_LABELS = {"normal": "정상", "caution": "주의", "risk": "위험"}
HEALTH_DISCLAIMER = "참고용 비교 결과이며 의학적 진단이 아닙니다. 판정 기준은 국민건강보험 일반검진 기준을 단순화했고(성별 구분 없음), 이상 소견은 의료진과 상담하세요."


class HealthMetric(BaseModel):
    name: str = Field(description="문서에 적힌 항목명")
    code: MetricCode = Field(description="표준 항목 코드, 해당 없으면 other")
    value: float | None = None
    unit: str | None = None


class HealthExam(BaseModel):
    exam_date: str | None = Field(default=None, description="검진일 YYYY-MM-DD")
    institution: str | None = Field(default=None, description="검진기관")
    metrics: list[HealthMetric] = []


HEALTH_PROMPT = """아래 건강검진 결과지에서 검진일, 검진기관, 검사 항목의 수치를 JSON 으로 추출하세요.
- 각 항목을 표준 코드(code)에 매핑합니다: systolic_bp, diastolic_bp, fasting_glucose, total_cholesterol, ldl, hdl,
  triglyceride, ast, alt, ggt, hemoglobin, creatinine, egfr, bmi, waist, weight. 해당 없으면 other.
- 혈압이 '128/84' 처럼 한 칸에 있으면 systolic_bp 와 diastolic_bp 두 항목으로 나눕니다.
- value 는 숫자만, 단위는 unit 에 적습니다. 문서에 없는 값은 넣지 않습니다. 추측하지 마세요.
"""


def judge(code: str, value: float | None) -> str | None:
    rule = METRICS.get(code, (None,) * 5)[4]
    if value is None or not rule:
        return None
    kind, *t = rule
    if kind == "lower":
        return "risk" if value >= t[1] else "caution" if value >= t[0] else "normal"
    if kind == "higher":
        return "risk" if value < t[1] else "caution" if value < t[0] else "normal"
    low_risk, low_caution, high_caution, high_risk = t
    if value < low_risk or value >= high_risk:
        return "risk"
    return "caution" if value < low_caution or value >= high_caution else "normal"


def extract_health_rules(text: str) -> dict:
    metrics: dict[str, HealthMetric] = {}
    bp = re.search(r"혈압[^\d\n]{0,15}(\d{2,3})\s*/\s*(\d{2,3})", text)
    if bp:
        metrics["systolic_bp"] = HealthMetric(name="수축기 혈압", code="systolic_bp", value=float(bp.group(1)), unit="mmHg")
        metrics["diastolic_bp"] = HealthMetric(name="이완기 혈압", code="diastolic_bp", value=float(bp.group(2)), unit="mmHg")
    for line in text.splitlines():
        for code, (label, unit, alias, *_rest) in METRICS.items():
            if code in metrics or not re.search(alias, line, re.I):
                continue
            tail = line.rsplit(":", 1)[-1] if ":" in line else re.split(alias, line, maxsplit=1, flags=re.I)[-1]
            number = re.search(_NUM, tail)
            if number:
                metrics[code] = HealthMetric(name=label, code=code, value=float(number.group(1)), unit=unit)
            break
    if len(metrics) < 2:
        raise ParseError("검사 항목 수치를 찾지 못했습니다. 혈압 · 공복혈당 · 콜레스테롤 등 항목명과 수치가 있는 결과지인지 확인하세요.")
    date = re.search(r"(?:검진일|검사일|수검일|검진\s*일자)[^\d\n]{0,10}" + _DATE.pattern, text) or _DATE.search(text)
    institution = re.search(r"(?:검진\s*기관|기관명|병원명)\s*[:：]\s*(.+)", text)
    return HealthExam(
        exam_date=_iso(date),
        institution=institution.group(1).strip()[:100] if institution else None,
        metrics=list(metrics.values()),
    ).model_dump()


def _fmt(value: float) -> str:
    return f"{value:g}"


def compare_health(exams: list[dict]) -> dict:
    exams = sorted(exams, key=lambda e: e.get("exam_date") or "9999")
    rows, insights = [], []
    for code, (label, unit, _alias, better, _rule) in METRICS.items():
        values = [next((m["value"] for m in e["metrics"] if m["code"] == code and m["value"] is not None), None) for e in exams]
        if all(v is None for v in values):
            continue
        statuses = [judge(code, v) for v in values]
        present = [i for i, v in enumerate(values) if v is not None]
        last = present[-1]
        prev = present[-2] if len(present) >= 2 else None
        delta = round(values[last] - values[prev], 2) if prev is not None else None
        flag = None
        if prev is not None and statuses[last] and statuses[prev]:
            r_now, r_before = STATUS_RANK[statuses[last]], STATUS_RANK[statuses[prev]]
            worse_dir = (better == "lower" and delta > 0) or (better == "higher" and delta < 0)
            if r_now > r_before:
                flag = "worsened"
            elif r_now < r_before:
                flag = "improved"
            elif worse_dir and r_now > 0:
                flag = "watch"
        if flag:
            change = f"{_fmt(values[prev])} → {_fmt(values[last])} {unit}"
            now_label, before_label = STATUS_LABELS[statuses[last]], STATUS_LABELS[statuses[prev]]
            message = {
                "worsened": f"{label}: {change}, '{before_label}'에서 '{now_label}' 범위로 나빠졌습니다.",
                "watch": f"{label}: 이미 '{now_label}' 범위인데 {change}로 더 나빠졌습니다.",
                "improved": f"{label}: {change}, '{now_label}' 범위로 좋아졌습니다.",
            }[flag]
            insights.append((flag, message))
        rows.append({"code": code, "label": label, "unit": unit, "better": better, "values": values, "statuses": statuses,
                     "delta": delta, "flag": flag, "reference": _reference(code), "limits": _limits(code)})
    latest = [r["statuses"][max(i for i, v in enumerate(r["values"]) if v is not None)] for r in rows]
    order = {"worsened": 0, "watch": 1, "improved": 2, None: 3}
    return {
        "dates": [e.get("exam_date") for e in exams],
        "institutions": [e.get("institution") for e in exams],
        "rows": sorted(rows, key=lambda r: order[r["flag"]]),
        "counts": {s: latest.count(s) for s in ("normal", "caution", "risk")},
        "worsened": sum(r["flag"] in ("worsened", "watch") for r in rows),
        "improved": sum(r["flag"] == "improved" for r in rows),
        "insights": [message for _, message in sorted(insights, key=lambda x: order[x[0]])],
        "disclaimer": HEALTH_DISCLAIMER,
    }


def _limits(code: str) -> list[float]:
    """차트 기준선: 정상 범위 경계값."""
    rule = METRICS[code][4]
    if not rule:
        return []
    kind, *t = rule
    return [t[0]] if kind in ("lower", "higher") else [v for v in (t[1], t[2]) if v]


def _reference(code: str) -> str | None:
    rule = METRICS[code][4]
    if not rule:
        return None
    kind, *t = rule
    if kind == "lower":
        return f"{_fmt(t[0])} 미만"
    if kind == "higher":
        return f"{_fmt(t[0])} 이상"
    return f"{_fmt(t[1])} ~ {_fmt(t[2])} 미만"


def analyze_health(files: list[tuple[str, bytes]]) -> tuple[dict, Engine]:
    exams = []
    for filename, data in files:
        text, file_bytes, mime = read_document(filename, data)
        try:
            exam = (generate_structured(HEALTH_PROMPT, HealthExam, text, file_bytes, mime).model_dump()
                    if settings.gemini_api_key else extract_health_rules(text))
        except ParseError as exc:
            raise ParseError(f"'{filename}': {exc}") from exc
        exams.append({**exam, "filename": filename})
    return {"exams": exams, "trend": compare_health(exams)}, _engine()
