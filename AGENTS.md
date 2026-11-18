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
- `test_admin`(테스트 관리자, admin@dataquill.io): 관리자 화면 조회만. `deps.get_current_user` 에서 GET/HEAD/OPTIONS 외 403
- 공개 테스트 계정 권한은 `backend/app/test_accounts.py` 기준으로 기동 시 복원, 권한 변경 API 로 변경 불가
- 프런트 Mock(`src/api/mock.js`)도 같은 규칙을 따라야 함 (DB 키 `dq_mock_db_v2`)

## UI 구조
- 모든 페이지 공통 `components/layout/SiteLayout` (Header · Footer · 원형 Top 버튼), `/` 는 항상 메인(랜딩) `pages/Home`
- 앱 · 정책 페이지는 `PageContainer` 안에서 렌더링 (container-page + page-y)
- 디자인 토큰: `index.css` 의 text-display/title/heading/body/caption, `container-page`, `section-y`, `page-y`, `eyebrow`
  (Tailwind 기본 유틸리티와 이름이 겹치지 않게 주의: `overline` 은 text-decoration 이라 사용 금지)

## 결정 사항
- 소셜 로그인(Google/Naver/Kakao): 실제 OAuth 연동 (백엔드 콜백 구현, Client ID/Secret 필요)
- 2026-11-17: 1단계 프런트엔드 완성 + 백엔드/RPA/AI 파이프라인 구현, 배포 설정 파일 작성 (실배포 전)
- 배포: 플랫폼 Git 연동 자동 배포 (Netlify: netlify.toml ignore 로 frontend/ 변경 시만, Render: render.yaml buildFilter). Actions(deploy.yml)는 테스트·빌드만, Secrets 미등록 시 배포 단계 skip
- 도메인: 프런트 https://dataquill.onrender.com (Render Static Site), 백엔드 https://dataquill-api.onrender.com (Render Web Service). Netlify 는 보조
- TiDB Cloud 는 DB_SSL=true 필수 (false 면 1105 insecure transport 오류로 기동 실패)

## 진행일지 · 산출물 (docs/*.hwpx → docs/pdf)
- 재생성: `python docs/tools/build_docs.py` (pywin32 가 있는 Python, 한컴오피스 2020 필요) → 진행일지 빈 칸 채움(양식·기간·조·보고자 유지), `docs/산출물/*.hwpx` 작성, `docs/pdf/` 에 PDF 저장
- 진행일지 팀원 칸은 `홍기흥`, 보고자는 양식의 `조휘일 (서명)` 유지 (`TEAM` 상수)
- 이미 채워진 셀은 건너뜀 → 문구를 바꾸려면 빈 양식으로 되돌린 뒤 실행 (`git checkout 608cdee -- docs/프로젝트_진행일지_*.hwpx`)
- 한글 자동화 보안 모듈: `HKCU\Software\HNC\HwpAutomation\Modules\FilePathCheckerModule` 에 pyhwpx 의 DLL 등록 필요, COM 이 멈추면 남은 `Hwp` 프로세스 종료
- 한글 HTML 가져오기는 CSS 대부분과 `&#x27;` 를 무시 → `html.escape(..., quote=False)`, 한글이 섞인 아스키 다이어그램 대신 표 사용
- 내용은 `docs/md` 작업 기록·코드에서 확인된 사실만 사용 (검증되지 않은 수치 금지)
- Windows 에서 `pip install -r requirements.txt` 가 cp949 디코딩 오류를 내면 `PYTHONUTF8=1` 로 실행 (requirements 에 한글 주석)

## 발표·시연 영상 (docs/video)
- 산출물: `3조_final.mp4`(10:00, 1080p30, ≤95MB, 저장소에 커밋) · `3조_final.srt` · `3조_highlight.mp4`(60초) · `video-thumbnail.png` · `영상_대본_및_연출가이드.md`. `build/` 는 git 제외
- 대본·시간의 단일 기준: `docs/video/tools/video_scenes.py` (합계 정확히 600초, 영문 용어는 읽는 문장에 한글 발음)
- 순서: `tts.py` → `record_demo.py` → `docs/scripts/capture_screens.py` → `build_presentation.py` → `export_slides.ps1` → `compose.py --rebuild` → `check_final.py` → `gen_guide.py`
- 합성 음성 패키지는 `.venv` 에만 설치(`PYTHONUTF8=1 .venv/Scripts/pip install edge-tts==7.3.1`). `requirements.txt` 를 바꾸면 Render 백엔드가 재배포되므로 넣지 않음
- 녹화는 설치된 Edge(`channel="msedge"`) + CDP 스크린캐스트(프레임 타임스탬프). Playwright 기본 녹화는 실제 시간과 어긋나므로 쓰지 않음
- `record_demo.py` 는 공개 테스트 일반 사용자의 문서를 지우고 2건(가상 영수증 스캔 PDF, 샘플 청구 메일)을 새로 처리함 (Gemini 호출 발생). 스캔 PDF 는 Gemini 멀티모달 경로라 정확하고 빠름(이미지 업로드는 Tesseract 경로라 60초 이상 · 품목 오인식)
- 장면 동작이 장면 길이를 넘으면 녹화 로그에 `!!` 경고 → 끝부분이 잘리므로 동작을 줄이고 해당 클립(`build/clips/<id>.mp4`)만 지운 뒤 `compose.py` 재실행
