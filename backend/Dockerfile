# 빌드 컨텍스트: 저장소 루트 (backend/ + rpa/ + requirements.txt)
# Debian 12(bookworm) 고정: Playwright 1.52 의 --with-deps 는 Debian 11/12 만 지원 (trixie 에서 설치 실패)
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# OCR 엔진(Tesseract, 한국어 포함)
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-kor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ERP 자동 타이핑용 Chromium (끄려면 --build-arg INSTALL_PLAYWRIGHT=false)
ARG INSTALL_PLAYWRIGHT=true
RUN if [ "$INSTALL_PLAYWRIGHT" = "true" ]; then python -m playwright install --with-deps chromium; fi

COPY backend ./backend
COPY rpa ./rpa

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
