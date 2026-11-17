# dataquill

생성형 AI & RPA 기반 **데이터 입력 자동화 시스템**.
PDF 영수증·이메일 본문 같은 비정형 데이터를 AI(OCR + Gemini)가 해석해 정형화하고, RPA가 기업 ERP·엑셀에 자동으로 타이핑·적재하는 B2B 솔루션입니다.

| 구분 | URL |
| --- | --- |
| GitHub | https://github.com/fsclass-n/dataquill |
| Frontend (Netlify) | https://dataquill.netlify.app |
| Backend API (Render) | https://dataquill.onrender.com |

## 처리 흐름

```
업로드(PDF·이미지·EML·HTML·TXT / 이메일 본문)
  → rpa/extract.py      텍스트 추출 (pypdf, Tesseract OCR, 이메일 파싱)
  → services/parser.py  Gemini 구조화 추출 (키 없으면 규칙 기반 파서)
  → 사용자 검수/수정
  → rpa/excel_writer.py 엑셀 원장 적재  |  rpa/erp_typer.py Playwright ERP 자동 타이핑
```

## 디렉터리

```
backend/app/        FastAPI (routers: auth, documents, admin, erp_demo / services: parser, oauth, stats)
backend/tests/      pytest
rpa/                텍스트·OCR 추출, 엑셀 적재, Playwright ERP 타이핑
frontend/           React(Vite) + Tailwind CSS v4 + FontAwesome + Recharts
docs/               진행일지·산출물 (md/ 에 작업 기록 누적)
.github/workflows/  deploy.yml (변경 영역별 CI/CD)
```

## 로컬 실행

```bash
# 1) 환경 변수
cp .env.example .env            # SECRET_KEY 변경, 필요 시 GEMINI_API_KEY / OAuth 키 입력

# 2) 백엔드 (Python 3.11)
py -3.11 -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m playwright install chromium   # ERP 자동 타이핑용
.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000

# 3) 프런트엔드
cd frontend && npm install && npm run dev        # http://localhost:5173
```

- API 문서: http://localhost:8000/docs
- 데모 ERP 화면(RPA 타이핑 대상): http://localhost:8000/erp-demo
- Docker: `docker compose up --build`

### 테스트 계정 (SEED_TEST_ACCOUNTS=true 일 때 자동 생성)

| 구분 | 이메일 | 비밀번호 |
| --- | --- | --- |
| 일반 사용자 | user@dataquill.io | User1234! |
| 관리자 | admin@dataquill.io | Admin1234! |

### Mock 모드

`VITE_API_URL` 을 비워 빌드하면 프런트엔드가 브라우저 내 목업 API(localStorage)로 동작합니다. 1단계 Netlify 단독 배포에 사용합니다.

## 검증

```bash
.venv/Scripts/python -m pytest backend/tests -q
cd frontend && npm run lint && npm run build
```

## 배포

- **CI/CD**: `.github/workflows/deploy.yml` 이 변경된 영역만 검증 후 배포합니다.
  - `frontend/**` → lint·build → Netlify CLI 배포 (`NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`, `vars.VITE_API_URL`)
  - `backend/**`, `rpa/**`, `requirements.txt` → pytest → Render Deploy Hook (`RENDER_DEPLOY_HOOK_URL`)
- **Render**: `render.yaml` Blueprint (Docker, `autoDeploy: false`). 비밀 값은 대시보드에 직접 등록합니다.
- **Netlify**: `frontend/netlify.toml` (SPA 리다이렉트). Actions 로 배포하므로 Netlify 자체 Git 빌드는 중지(Stop builds)합니다.
- **OAuth Redirect URI**: `{BACKEND_URL}/api/auth/oauth/{google|naver|kakao}/callback`
