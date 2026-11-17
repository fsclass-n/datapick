"""비정형 문서(PDF·이미지·이메일·텍스트)에서 원문 텍스트를 추출한다.

스캔 PDF·이미지처럼 텍스트 레이어가 없는 경우 로컬 OCR(Tesseract)을 시도하고,
OCR 엔진이 없으면 `needs_vision=True` 를 돌려 LLM(Gemini) 멀티모달 해석으로 넘긴다.
"""

from __future__ import annotations

import email
import io
import shutil
from dataclasses import dataclass
from email import policy
from pathlib import Path

from bs4 import BeautifulSoup

PDF_TYPES = {".pdf"}
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
EMAIL_TYPES = {".eml"}
HTML_TYPES = {".html", ".htm"}
TEXT_TYPES = {".txt", ".csv", ".md"}
SUPPORTED_TYPES = PDF_TYPES | IMAGE_TYPES | EMAIL_TYPES | HTML_TYPES | TEXT_TYPES
MIN_TEXT_LENGTH = 20

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


@dataclass
class Extraction:
    text: str
    method: str
    needs_vision: bool = False
    mime_type: str | None = None


def source_type_of(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in PDF_TYPES:
        return "pdf"
    if suffix in IMAGE_TYPES:
        return "image"
    if suffix in EMAIL_TYPES | HTML_TYPES:
        return "email"
    return "text"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    lines = (line.strip() for line in soup.get_text("\n").splitlines())
    return "\n".join(line for line in lines if line)


def _decode(data: bytes) -> str:
    for encoding in ("utf-8", "cp949", "euc-kr", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _ocr_image(data: bytes) -> str:
    import pytesseract
    from PIL import Image

    return pytesseract.image_to_string(Image.open(io.BytesIO(data)), lang="kor+eng").strip()


def _email_text(data: bytes) -> str:
    message = email.message_from_bytes(data, policy=policy.default)
    header = "\n".join(f"{key}: {message[key]}" for key in ("From", "To", "Subject", "Date") if message[key])
    body = message.get_body(preferencelist=("plain", "html"))
    content = body.get_content() if body else ""
    if body and body.get_content_type() == "text/html":
        content = html_to_text(content)
    return f"{header}\n\n{content}".strip()


def extract(filename: str, data: bytes) -> Extraction:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_TYPES:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {suffix or '(확장자 없음)'}")

    if suffix in PDF_TYPES:
        text = _pdf_text(data)
        if len(text) >= MIN_TEXT_LENGTH:
            return Extraction(text, "pdf-text")
        return Extraction(text, "vision", needs_vision=True, mime_type=MIME_TYPES[suffix])

    if suffix in IMAGE_TYPES:
        if tesseract_available():
            text = _ocr_image(data)
            if len(text) >= MIN_TEXT_LENGTH:
                return Extraction(text, "tesseract")
        return Extraction("", "vision", needs_vision=True, mime_type=MIME_TYPES[suffix])

    if suffix in EMAIL_TYPES:
        return Extraction(_email_text(data), "email")
    if suffix in HTML_TYPES:
        return Extraction(html_to_text(_decode(data)), "html")
    return Extraction(_decode(data).strip(), "text")
