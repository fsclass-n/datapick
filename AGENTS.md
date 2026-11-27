# datapick - 에이전트 작업 메모

## 프로젝트
- PDF 영수증/이메일 등 비정형 데이터 → OCR + LLM(Gemini) 해석 → RPA로 ERP/엑셀 자동 입력하는 B2B 솔루션
- 2026-11-24: AI 도구 3종(견적서 비교 · 계약서 빨간펜 · 건강검진 추이) 추가, 브랜드 · 로고 · 프런트 전면 개편
- 3조 팀 프로젝트 — 팀원 4명: 박미금(조장) · 김모란 · 이오리(발표자) · 홍기흥
- Repo: https://github.com/fsclass-n/datapick (origin을 omnitask.git에서 변경함, 2026-11-16)
- Frontend: Netlify (https://datapick.netlify.app) / Backend: Render (https://datapick.onrender.com)

## 로컬 환경 (확인됨)
- Windows, Node v24.15.0, npm 11.12.1, Python 3.11.9 (`py -3.11`)
- Docker 미설치 (docker-compose 파일은 작성하되 로컬 실행 검증 불가)
- gh CLI 설치됨

## 명령어
- 백엔드 실행 (루트에서): `.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000`
- 백엔드 테스트: `.venv/Scripts/python -m pytest backend/tests -q` (50개)
- 프런트: `cd frontend && npm run dev` / `npm run lint` / `npm run build`
- Mock 모드 빌드 확인: `VITE_API_URL= npx vite build --outDir <임시폴더>`
- ERP 타이핑용 브라우저: `.venv/Scripts/python -m playwright install chromium`
- npm 의존성 추가 시 `--before=<7일 전 날짜>` 사용
- 발표자료 재생성: `.venv/Scripts/python docs/scripts/build_presentation.py` → `docs/프로젝트_발표자료.pptx` (노트에 발표 스크립트)
  - PDF: PowerPoint COM 으로 내보내기 (`docs/pdf/프로젝트_발표자료.pdf`), 화면 캡처는 `docs/assets/screenshots/`
  - 캡처는 별도 데모 인스턴스(백엔드 :8001 + 임시 SQLite, 프런트 :5180)에서 촬영. 5174 포트는 다른 프로젝트(fashionpick)가 사용 중

## 문서(진행일지 · 산출물) 생성
- `python docs/tools/build_docs.py` — **시스템 Python 3.11**(pywin32 · PyMuPDF, 한글 설치 필요)로 실행. .venv 에는 pywin32 가 없음
- 진행일지는 `docs/tools/templates/` 원본 빈 양식에서 다시 채움(메타데이터 보존), 산출물은 `docs/tools/hwpx_writer.py` 로 직접 생성
- 내용은 build_docs.py 의 JOURNAL · output_0N() 만 수정. 실행 후 자동 검수(본문 일치 · 글꼴 · 빈 쪽 · 하단 제목) 결과가 모두 OK 여야 함

## 구조 메모
- Python 패키지 루트는 저장소 루트 (`backend.app`, `rpa` 를 import). Docker 빌드 컨텍스트도 루트
- Vite 는 `envDir: '..'` 로 루트 `.env` 를 읽음 (VITE_ 접두사만 노출)
- `VITE_API_URL` 이 비어 있으면 프런트는 `src/api/mock.js` 목업 API 사용 → 백엔드 API 를 바꾸면 목업도 같이 수정
- Tailwind v4: 재사용 클래스(btn, card, input 등)는 `@utility` 로 정의 (`src/index.css`)

## 규칙
- **최종 결과 보고는 한국어로 작성**: 작업이 끝난 뒤 사용자에게 알리는 최종 결과만 한글로 작성 (작업 중간 안내는 언어 무관)
- 가상환경 `.venv`, 단일 `requirements.txt`
- 환경 변수는 `.env` 하나로 관리, `.env.example`에 Render 대시보드 등록 항목 구분 표시
- Netlify/Render는 각자 영역(frontend/, backend/) 변경 시에만 배포
- 진행 내용은 `docs/md/`에 마크다운으로 누적 기록
- `.env` 값 뒤에 인라인 주석 금지 (빈 값 뒤 주석이 값으로 읽힘)

## 권한 모델 (2026-11-17 개편)
- `admin`(운영 관리자): `/api/auth/admin-login` + `ADMIN_TOKEN` 으로만 진입, 전체 CRUD. 5회 실패/10분 차단(프로세스 메모리)
- `test_admin`(테스트 관리자, admin@datapick.io): 관리자 화면 조회만. `deps.get_current_user` 에서 GET/HEAD/OPTIONS 외 403
- 회원 삭제: `services/account.delete_account` 공용 — 탈퇴(`DELETE /api/auth/me`, 비밀번호 계정은 재확인, 체험 계정 차단) · 강퇴(`DELETE /api/admin/users/{id}`, 본인/테스트 계정/관리자 계정 차단 — 관리자는 강등 후 강퇴)
- 공개 테스트 계정 권한은 `backend/app/test_accounts.py` 기준으로 기동 시 복원, 권한 변경 API 로 변경 불가
- 프런트 Mock(`src/api/mock.js`)도 같은 규칙을 따라야 함 (DB 키 `dp_mock_db_v2`)

## UI 구조
- 모든 페이지 공통 `components/layout/SiteLayout` (Header · Footer · 원형 Top 버튼), `/` 는 항상 메인(랜딩) `pages/Home`
- 앱 · 정책 페이지는 `PageContainer` 안에서 렌더링 (container-page + page-y)
- 디자인 토큰: `index.css` 의 text-display/title/heading/body/caption, `container-page`, `section-y`, `page-y`, `eyebrow`
  (Tailwind 기본 유틸리티와 이름이 겹치지 않게 주의: `overline` 은 text-decoration 이라 사용 금지)
- 브랜드(2026-11-24 개편): 잉크 남색 `ink`/`brand-*`(#14213d 계열) · 금박 `gold-*`(#e9a23b) · 종이 배경 `paper`. 보조 유틸리티 `paper-lines`(괘선) · `dot-grid` · `red-pen`(물결 밑줄)
  - 도구별 강조색: 견적 sky · 계약서 rose · 검진 emerald · 문서 입력 ink — 클래스 문자열은 `utils/tools.js` ACCENTS 에 그대로 둔다(Tailwind 정적 분석)
  - recharts 색은 CSS 변수 대신 hex 로 적는다(SVG 속성)
- 로고: 깃펜의 한쪽 깃이 데이터 픽셀로 흩어지는 마크. `components/layout/Logo.jsx` 의 `LogoMark`(tone: tile · light · dark) + `Wordmark`(data=ink, quill=gold)
  - 같은 도형을 `frontend/public/favicon.svg`, 루트 `index.html`(GitHub Pages 로고 2곳 + 인라인 파비콘)에도 사용 → 로고를 바꾸면 세 곳 모두 수정
- 사진: `frontend/public/images/*.webp`(본문 1000~1600px, `-sm` 480px). 모두 Unsplash License, 출처는 `utils/tools.js` IMAGE_CREDITS 와 푸터에 표기. 새 사진도 공식 다운로드 링크로 받아 로컬 WebP 로 최적화(핫링크 금지)

## AI 도구 3종 (2026-11-24)
- 경로: `/tools/quotes`(견적서 비교기) · `/tools/contract`(계약서 빨간펜) · `/tools/health`(건강검진 추이), 메타데이터는 `frontend/src/utils/tools.js`
- 원칙: **AI는 읽기만, 판정은 규칙 코드** — `backend/app/services/analyzers.py` (Gemini 구조화 출력 → 결정적 비교 · 점수 · 판정). Gemini 호출은 `parser.generate_structured` 공용 함수(재시도 포함)
- API: `POST /api/tools/quote-compare`(files 2~5) · `/contract-review`(file 또는 text) · `/health-trend`(files 1~5), `GET/DELETE /api/tools/analyses[/{id}]`(본인만, 관리자도 타인 결과 조회 불가)
- 원본 파일은 저장하지 않고 `analyses` 테이블에 결과 JSON 만 저장
- 규칙을 바꾸면 **`frontend/src/api/mockTools.js` 도 같이 수정** (Mock 모드 동일성). 프런트 '샘플로 바로 체험'은 `frontend/public/samples/*.txt` 사용
- 샘플 재생성: `py -3.11 samples/make_samples.py` → `samples/견적비교|계약서|건강검진/*.pdf` + `frontend/public/samples/*.txt` (테스트 `backend/tests/test_tools.py` 가 TXT 사본을 읽음)
- 응답 시각은 `schemas.UtcDatetime` 으로 UTC 표시를 붙인다(DB 가 시간대 없는 값을 돌려줘 새로고침 후 9시간 이르게 보이던 문제 해결)
- 화면 점검: 데모 인스턴스(백엔드 :8001 임시 SQLite + `GEMINI_API_KEY=` 규칙 엔진, 프런트 :5180 `VITE_API_URL=http://localhost:8001`) + Mock 빌드(`vite preview` :5181)에서 Playwright 로 샘플 실행 · 콘솔 오류 · 가로 넘침 확인

## ERP 연동 구조 (2026-11-25)
- `rpa/erp.py`: `ErpAdapter` 인터페이스 + `WebFormAdapter`(Playwright, 셀렉터 맵·로그인을 `ERP_CONFIG` JSON으로 외부화) + `FileExportAdapter`(일괄등록 엑셀). `ERP_ADAPTER` env로 선택, 미설정 시 데모 ERP 동작
- `external_erp/main.py`: 로그인+전표 목록이 있는 독립 미니 ERP — `uvicorn external_erp.main:app --port 8100` + `ERP_CONFIG=rpa/erp_target.example.json` + `ERP_USERNAME=erp ERP_PASSWORD=demo1234` 로 로컬 실연동 검증 가능
- 데스크톱/사내망 ERP는 클라우드에서 접근 불가 → 로컬 에이전트가 필요하다는 한계를 문서로 남김(구현 안 함)

## 결정 사항
- 소셜 로그인(Google/Naver/Kakao): 실제 OAuth 연동 (백엔드 콜백 구현, Client ID/Secret 필요)
- 2026-11-17: 1단계 프런트엔드 완성 + 백엔드/RPA/AI 파이프라인 구현, 배포 설정 파일 작성 (실배포 전)
- 배포: 플랫폼 Git 연동 자동 배포 (Netlify: netlify.toml ignore 로 frontend/ 변경 시만, Render: render.yaml buildFilter). Actions(deploy.yml)는 테스트·빌드만, Secrets 미등록 시 배포 단계 skip
- 도메인: 프런트 https://datapick.onrender.com (Render Static Site), 백엔드 https://datapick-api.onrender.com (Render Web Service). Netlify 는 보조
- TiDB Cloud 는 DB_SSL=true 필수 (false 면 1105 insecure transport 오류로 기동 실패)

## 진행일지 · 산출물 (docs/*.hwpx → docs/pdf)
- 재생성: `python docs/tools/build_docs.py` (pywin32 가 있는 Python, 한컴오피스 2020 필요) → 진행일지 빈 칸 채움(양식·기간·조·보고자 유지), `docs/산출물/*.hwpx` 작성, `docs/pdf/` 에 PDF 저장
- 진행일지 팀원 칸은 `박미금(조장) · 김모란 · 이오리 · 홍기흥`(`TEAM` 상수), 보고자는 발표자 `이오리 (서명)`으로 교체
- 이미 채워진 셀은 건너뜀 → 문구를 바꾸려면 빈 양식으로 되돌린 뒤 실행 (`git checkout 608cdee -- docs/프로젝트_진행일지_*.hwpx`)
- 한글 자동화 보안 모듈: `HKCU\Software\HNC\HwpAutomation\Modules\FilePathCheckerModule` 에 pyhwpx 의 DLL 등록 필요, COM 이 멈추면 남은 `Hwp` 프로세스 종료
- 한글 HTML 가져오기는 CSS 대부분과 `&#x27;` 를 무시 → `html.escape(..., quote=False)`, 한글이 섞인 아스키 다이어그램 대신 표 사용
- 내용은 `docs/md` 작업 기록·코드에서 확인된 사실만 사용 (검증되지 않은 수치 금지)
- Windows 에서 `pip install -r requirements.txt` 가 cp949 디코딩 오류를 내면 `PYTHONUTF8=1` 로 실행 (requirements 에 한글 주석)

## 발표·시연 영상 (docs/video)
- 산출물: `3조_final.mp4`(10:00, 1080p30, ≤95MB, 저장소에 커밋) · `3조_final.srt` · `3조_highlight_3min.mp4`(3분) · `video-thumbnail.png` · `영상_대본_및_연출가이드.md`. `build/` 는 git 제외
- 대본·시간의 단일 기준: `docs/video/tools/video_scenes.py` (합계 정확히 600초, 영문 용어는 읽는 문장에 한글 발음)
- 순서: `tts.py` → `record_demo.py` → `docs/scripts/capture_screens.py` → `build_presentation.py` → `export_slides.ps1` → `compose.py --rebuild` → `check_final.py` → `gen_guide.py`
- 합성 음성 패키지는 `.venv` 에만 설치(`PYTHONUTF8=1 .venv/Scripts/pip install edge-tts==7.3.1`). `requirements.txt` 를 바꾸면 Render 백엔드가 재배포되므로 넣지 않음
- 녹화는 설치된 Edge(`channel="msedge"`) + CDP 스크린캐스트(프레임 타임스탬프). Playwright 기본 녹화는 실제 시간과 어긋나므로 쓰지 않음
- `record_demo.py` 는 공개 테스트 일반 사용자의 문서를 지우고 2건(가상 영수증 스캔 PDF, 샘플 청구 메일)을 새로 처리함 (Gemini 호출 발생). 스캔 PDF 는 Gemini 멀티모달 경로라 정확하고 빠름(이미지 업로드는 Tesseract 경로라 60초 이상 · 품목 오인식)
- 장면 동작이 장면 길이를 넘으면 녹화 로그에 `!!` 경고 → 끝부분이 잘리므로 동작을 줄이고 해당 클립(`build/clips/<id>.mp4`)만 지운 뒤 `compose.py` 재실행

## 상용화 구조 (2026-11-27)
- 요금제: `users.plan`(free/pro/business) + `services/billing.py`(월 문서 한도, 402 차단). 기존 DB 는 `database.migrate()` 가 기동 시 ALTER TABLE 로 컬럼 추가
- 결제: `POST /api/billing/subscribe` 는 게이트웨이 없는 인앱 스텁 — 실제 결제 연동 시 이 지점을 교체
- 고객사 ERP: `erp_connections` 테이블(계정별 ERP 주소·로그인 자격증명, 비밀번호는 Fernet 암호화 — `services/crypto.py`, SECRET_KEY 기반). Pro 이상만 저장 가능. 문서 소유자 연결이 있으면 `rpa/erp.config_for_connection()` → 인라인 자격증명(username_value/password_value)으로 입력
- external_erp 화면은 가상 고객사 "(주)한빛물산"의 "BizCube ERP" 컨셉(셀렉터·API 는 데모와 동일)
- 프런트 `/billing`: 요금제 카드 + 사용량 게이지 + ERP 연결 폼·연결 테스트
