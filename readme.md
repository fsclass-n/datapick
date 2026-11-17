# dataquill

생성형 AI & RPA 기반 **데이터 입력 자동화 시스템**.
PDF 영수증·이메일 본문 같은 비정형 데이터를 AI(OCR + Gemini)가 해석해 정형화하고, RPA가 기업 ERP·엑셀에 자동으로 타이핑·적재하는 B2B 솔루션입니다.

| 구분 | URL |
| --- | --- |
| GitHub | https://github.com/fsclass-n/dataquill |
| Frontend (Render Static Site) | https://dataquill.onrender.com |
| Backend API (Render Web Service) | https://dataquill-api.onrender.com |
| Frontend (Netlify, 보조) | https://dataquill.netlify.app |

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

### 계정과 권한

| 구분 | 진입 방법 | 권한 |
| --- | --- | --- |
| 운영 관리자 | `/admin/login` 에서 서버 환경 변수 `ADMIN_TOKEN` 입력 | 모든 데이터 생성 · 수정 · 삭제, 회원 권한 변경 |
| 테스트 관리자 | 로그인 화면 버튼 (`admin@dataquill.io` / `Admin1234!`) | 관리자 화면 조회만 가능, 모든 쓰기 요청은 서버에서 403 |
| 일반 사용자 | 이메일 가입 · OAuth · 테스트 버튼 (`user@dataquill.io` / `User1234!`) | 본인 문서 업로드 · 검수 · RPA |

- 테스트 계정은 `SEED_TEST_ACCOUNTS=true` 일 때 자동 생성되며, 비밀번호가 공개되어 있으므로 서버 기동 시마다 권한이 고정값으로 되돌아가고 권한 변경 API 로도 바꿀 수 없습니다.
- 읽기 전용은 `deps.get_current_user` 한 곳에서 강제합니다 (`test_admin` 의 GET 외 요청 → 403).

### Mock 모드

`VITE_API_URL` 을 비워 빌드하면 프런트엔드가 브라우저 내 목업 API(localStorage)로 동작합니다. 1단계 Netlify 단독 배포에 사용합니다.

## 검증

```bash
.venv/Scripts/python -m pytest backend/tests -q
cd frontend && npm run lint && npm run build
```

## 배포 (Render, main 푸시 시 자동 배포)

`render.yaml` 이 두 서비스의 기준 설정입니다. 각 서비스는 자기 영역 파일이 바뀐 경우에만 배포됩니다(Build Filters).

| 서비스 | 유형 | 배포 트리거 경로 |
| --- | --- | --- |
| `dataquill-api` | Web Service (Docker `backend/Dockerfile`, 또는 Python 네이티브) | `backend/**`, `rpa/**`, `requirements.txt` |
| `dataquill` | Static Site (`frontend/dist`, `/*` → `/index.html` Rewrite) | `frontend/**` |

- GitHub Actions(`deploy.yml`)는 변경 영역 테스트·빌드를 수행합니다. 배포 Secrets 가 없으면 배포 단계는 건너뜁니다.
- OAuth Redirect URI: `https://dataquill-api.onrender.com/api/auth/oauth/{google|naver|kakao}/callback`
- 환경 변수 구분은 `.env.example` 의 `[RENDER]`(백엔드) / `[RENDER-FE]`(프런트) 표기를 따릅니다.
