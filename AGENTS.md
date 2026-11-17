# dataquill - 에이전트 작업 메모

## 프로젝트
- PDF 영수증/이메일 등 비정형 데이터 → OCR + LLM(Gemini) 해석 → RPA로 ERP/엑셀 자동 입력하는 B2B 솔루션
- 1인 프로젝트 (홍기흥)
- Repo: https://github.com/fsclass-n/dataquill (origin을 omnitask.git에서 변경함, 2026-11-16)
- Frontend: Netlify (https://dataquill.netlify.app) / Backend: Render (https://dataquill.onrender.com)

## 로컬 환경 (확인됨)
- Windows, Node v24.15.0, npm 11.12.1, Python 3.11.9 (`py -3.11`)
- Docker 미설치 (docker-compose 파일은 작성하되 로컬 실행 검증 불가)
- gh CLI 설치됨

## 명령어
- 백엔드 실행 (루트에서): `.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000`
- 백엔드 테스트: `.venv/Scripts/python -m pytest backend/tests -q`
- 프런트: `cd frontend && npm run dev` / `npm run lint` / `npm run build`
- Mock 모드 빌드 확인: `VITE_API_URL= npx vite build --outDir <임시폴더>`
- ERP 타이핑용 브라우저: `.venv/Scripts/python -m playwright install chromium`
- npm 의존성 추가 시 `--before=<7일 전 날짜>` 사용
- 발표자료 재생성: `.venv/Scripts/python docs/scripts/build_presentation.py` → `docs/프로젝트_발표자료.pptx` (노트에 발표 스크립트)
  - PDF: PowerPoint COM 으로 내보내기 (`docs/pdf/프로젝트_발표자료.pdf`), 화면 캡처는 `docs/assets/screenshots/`
  - 캡처는 별도 데모 인스턴스(백엔드 :8001 + 임시 SQLite, 프런트 :5180)에서 촬영. 5174 포트는 다른 프로젝트(fashionpick)가 사용 중

## 구조 메모
- Python 패키지 루트는 저장소 루트 (`backend.app`, `rpa` 를 import). Docker 빌드 컨텍스트도 루트
- Vite 는 `envDir: '..'` 로 루트 `.env` 를 읽음 (VITE_ 접두사만 노출)
- `VITE_API_URL` 이 비어 있으면 프런트는 `src/api/mock.js` 목업 API 사용 → 백엔드 API 를 바꾸면 목업도 같이 수정
- Tailwind v4: 재사용 클래스(btn, card, input 등)는 `@utility` 로 정의 (`src/index.css`)

## 규칙
- 가상환경 `.venv`, 단일 `requirements.txt`
- 환경 변수는 `.env` 하나로 관리, `.env.example`에 Render 대시보드 등록 항목 구분 표시
- Netlify/Render는 각자 영역(frontend/, backend/) 변경 시에만 배포
- 진행 내용은 `docs/md/`에 마크다운으로 누적 기록
- `.env` 값 뒤에 인라인 주석 금지 (빈 값 뒤 주석이 값으로 읽힘)

## 결정 사항
- 소셜 로그인(Google/Naver/Kakao): 실제 OAuth 연동 (백엔드 콜백 구현, Client ID/Secret 필요)
- 2026-11-17: 1단계 프런트엔드 완성 + 백엔드/RPA/AI 파이프라인 구현, 배포 설정 파일 작성 (실배포 전)
- 배포: 플랫폼 Git 연동 자동 배포 (Netlify: netlify.toml ignore 로 frontend/ 변경 시만, Render: render.yaml buildFilter). Actions(deploy.yml)는 테스트·빌드만, Secrets 미등록 시 배포 단계 skip
- 도메인: 프런트 https://dataquill.onrender.com (Render Static Site), 백엔드 https://dataquill-api.onrender.com (Render Web Service). Netlify 는 보조
- TiDB Cloud 는 DB_SSL=true 필수 (false 면 1105 insecure transport 오류로 기동 실패)
