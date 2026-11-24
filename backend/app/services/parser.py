"""비정형 텍스트 → 정형 JSON 변환.

GEMINI_API_KEY 가 있으면 Gemini 로 해석하고(이미지·스캔 PDF는 멀티모달로 OCR 겸용),
없으면 정규식 기반 규칙 파서로 동작한다.
"""

from __future__ import annotations

import re
import time
from typing import Literal

from pydantic import BaseModel, Field

from ..config import settings


class LineItem(BaseModel):
    name: str
    quantity: float | None = None
    unit_price: int | None = None
    amount: int | None = None


class ParsedDocument(BaseModel):
    document_type: Literal["receipt", "invoice", "email", "other"] = "other"
    vendor: str | None = Field(default=None, description="거래처(상호명)")
    business_number: str | None = Field(default=None, description="사업자등록번호 000-00-00000")
    date: str | None = Field(default=None, description="거래일자 YYYY-MM-DD")
    total_amount: int | None = Field(default=None, description="합계 금액(원 단위 정수)")
    vat: int | None = Field(default=None, description="부가세(원 단위 정수)")
    currency: str = "KRW"
    payment_method: str | None = None
    items: list[LineItem] = []
    summary: str | None = Field(default=None, description="한 줄 적요")
    confidence: float = Field(default=0.5, ge=0, le=1)


class ParseError(RuntimeError):
    pass


RETRYABLE_STATUS = {429, 500, 503, 504}
RETRY_DELAYS = (2, 5, 10)
MAX_PROMPT_CHARS = 30000


PROMPT = """당신은 회계 전표 입력 담당자입니다. 아래 문서(영수증, 세금계산서, 거래 이메일 등)를 읽고
ERP 전표 입력에 필요한 값을 JSON 으로 추출하세요.
- 금액은 쉼표와 통화 기호를 제거한 정수로 표기합니다.
- 날짜는 YYYY-MM-DD 형식으로 변환합니다.
- 문서에 없는 값은 null 로 둡니다. 추측하지 마세요.
- confidence 는 추출 결과 전체에 대한 확신도(0~1)입니다.
"""


def generate_structured(
    prompt: str,
    schema: type[BaseModel],
    text: str = "",
    file_bytes: bytes | None = None,
    mime_type: str | None = None,
) -> BaseModel:
    """Gemini 구조화 출력 공용 호출. 일시 오류(429/5xx)만 백오프 재시도한다."""
    from google import genai
    from google.genai import errors as genai_errors
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    contents: list = [prompt]
    if file_bytes and mime_type:
        contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
    if text:
        contents.append(f"[문서 텍스트]\n{text[:MAX_PROMPT_CHARS]}")
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0,
    )
    for attempt, delay in enumerate((*RETRY_DELAYS, None)):
        try:
            response = client.models.generate_content(model=settings.gemini_model, contents=contents, config=config)
            break
        except genai_errors.APIError as exc:
            if exc.code in RETRYABLE_STATUS and delay is not None:
                time.sleep(delay)
                continue
            hint = " (일시적인 과부하입니다. 잠시 후 다시 시도해 주세요.)" if exc.code in RETRYABLE_STATUS else ""
            raise ParseError(f"Gemini 호출 실패 ({exc.code}, {attempt + 1}회 시도): {exc.message or exc.status}{hint}") from exc
        except Exception as exc:
            raise ParseError(f"Gemini 호출 실패: {exc}") from exc
    if not response.text:
        raise ParseError("Gemini 가 빈 응답을 반환했습니다.")
    return schema.model_validate_json(response.text)


def parse_with_gemini(text: str, file_bytes: bytes | None = None, mime_type: str | None = None) -> dict:
    return generate_structured(PROMPT, ParsedDocument, text, file_bytes, mime_type).model_dump()


_AMOUNT = r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)\s*원?"
_DATE = re.compile(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})")
_BIZ = re.compile(r"\b(\d{3})-?(\d{2})-?(\d{5})\b")
_TOTAL = re.compile(r"(?:합\s*계|총\s*액|결제\s*금액|청구\s*금액|받을\s*금액|total)\s*[:：]?\s*(?:₩|\\)?\s*" + _AMOUNT, re.I)
_VAT = re.compile(r"(?:부가세|부가가치세|VAT)\s*[:：]?\s*(?:₩|\\)?\s*" + _AMOUNT, re.I)
_VENDOR = re.compile(r"(?:상호|가맹점|업체명|공급자|거래처)\s*(?:명)?\s*[:：]\s*(.+)")
_PAYMENT = re.compile(r"(신용카드|체크카드|현금|계좌이체|카드)")
_ITEM = re.compile(r"^(?P<name>[^\d:：]{2,30}?)\s+(?P<qty>\d{1,3})\s+(?P<price>[\d,]+)\s+(?P<amount>[\d,]+)\s*$")


def _int(value: str | None) -> int | None:
    return int(value.replace(",", "")) if value else None


def parse_with_rules(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ParseError("추출된 텍스트가 없습니다. GEMINI_API_KEY 를 설정하면 이미지/스캔 문서도 해석할 수 있습니다.")

    date = _DATE.search(text)
    biz = _BIZ.search(text)
    totals = [_int(m.group(1)) for m in _TOTAL.finditer(text)]
    vat = _VAT.search(text)
    vendor = _VENDOR.search(text)
    payment = _PAYMENT.search(text)
    items = [
        LineItem(
            name=m["name"].strip(),
            quantity=float(m["qty"]),
            unit_price=_int(m["price"]),
            amount=_int(m["amount"]),
        )
        for m in (_ITEM.match(line) for line in lines)
        if m
    ]
    is_email = bool(re.search(r"^(From|Subject|보낸\s*사람|제목)\s*:", text, re.M))
    doc_type = "email" if is_email else "invoice" if "세금계산서" in text or "청구" in text else "receipt"
    subject = re.search(r"^(?:Subject|제목)\s*:\s*(.+)$", text, re.M)

    parsed = ParsedDocument(
        document_type=doc_type if (totals or date) else "other",
        vendor=(vendor.group(1).strip() if vendor else lines[0])[:100],
        business_number="-".join(biz.groups()) if biz else None,
        date=f"{date.group(1)}-{int(date.group(2)):02d}-{int(date.group(3)):02d}" if date else None,
        total_amount=max(totals) if totals else None,
        vat=_int(vat.group(1)) if vat else None,
        payment_method=payment.group(1) if payment else None,
        items=items,
        summary=(subject.group(1).strip() if subject else lines[0])[:200],
    )
    found = sum(v is not None for v in (parsed.date, parsed.total_amount, parsed.business_number, parsed.vat))
    parsed.confidence = round(0.2 + 0.15 * found + (0.1 if items else 0), 2)
    if parsed.total_amount is None and parsed.date is None:
        raise ParseError("금액·날짜를 찾지 못했습니다. 문서 형식을 확인하거나 Gemini 파서를 사용하세요.")
    return parsed.model_dump()


def parse(text: str, file_bytes: bytes | None = None, mime_type: str | None = None) -> tuple[dict, str]:
    if settings.gemini_api_key:
        return parse_with_gemini(text, file_bytes, mime_type), "gemini"
    return parse_with_rules(text), "rules"
