"""진행일지(양식 유지·빈 칸 채움) + 산출물(단계별 상세) 작성 → 한글(HWP COM)로 HWPX 재저장 · PDF 변환

    python docs/tools/build_docs.py

- 진행일지: 기존 표 양식·기간·조·보고자 등 메타데이터는 그대로 두고, 빈 셀에만 같은 문단/글자 스타일로 내용 삽입
- 산출물: 단계별 HTML 원고 → 한글로 열어 HWPX 로 저장(기존 빈 파일 교체)
- PDF: docs/pdf/ 에 같은 이름으로 저장 (한글 PDF 내보내기)
- 한글 자동화 보안 모듈(FilePathCheckerModule) 필요: pyhwpx 패키지에 포함된 DLL 을 레지스트리에 등록해 사용
"""

import html
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import win32com.client as win32

DOCS = Path(__file__).resolve().parents[1]
OUT_PDF = DOCS / "pdf"
TEAM = "홍기흥"
TOPIC = "DataQuill — 생성형 AI × RPA 기반 데이터 입력 자동화 플랫폼"
REPO = "https://github.com/fsclass-n/dataquill"
SERVICE = "https://dataquill.onrender.com (API 문서: https://dataquill-api.onrender.com/docs)"

# ============================================================================ 진행일지 내용 (행 번호 → 줄 목록)
# 근거: docs/md/*.md 작업 기록, 저장소 코드, 발표자료 구성안 (검증되지 않은 수치는 쓰지 않음)
COMMON = {1: [TOPIC], 2: [TEAM]}
JOURNAL = {
    "프로젝트_진행일지_1단계_기획분석.hwpx": {
        3: ["주제 선정 및 문제 정의, 요구사항 도출, 입력 문서·출력 대상 조사, 기술 스택 선정, 작업 기록 방식 결정"],
        4: ["- 핵심 가치 확정: 비정형 문서(영수증·세금계산서·거래 이메일)를 AI가 정형화하고 RPA가 ERP·엑셀에 대신 입력",
            "- MVP 범위(입력 형식, 추출 필드, 출력 대상, 권한) 확정 및 저장소·개발 환경 준비"],
        5: ["- 생성형 AI(LLM)와 RPA 자동화를 핵심 기술로 포함하고 클라우드 배포까지 수행",
            "- 반응형 UI, 소셜 로그인(OAuth), 관리자 페이지, 테스트 계정 요구사항 반영",
            "- 단계별 진행일지·산출물 작성"],
        6: ["- 문제 정의: 경리·총무 담당자가 같은 문서를 ERP에 한 번, 엑셀 원장에 또 한 번 수기 입력 / 문서 형식이 제각각이라 규칙(정규식)만으로는 자동화 한계 / 사내 ERP는 연동 API가 없는 경우가 많음",
            "- 해결 방향: 형식 문제는 생성형 AI 구조화 출력으로, API가 없는 문제는 화면에 입력하는 RPA로 해결하고, AI 오류에 대비해 사람 검수 단계를 둠",
            "- 입력 형식(PDF·이미지·EML·HTML·TXT·본문 붙여넣기)과 추출 필드(거래처·사업자번호·거래일자·합계·부가세·결제수단·품목·적요) 정의",
            "- 기술 스택 선정: FastAPI·SQLAlchemy·Gemini·Playwright·pandas·React·Tailwind·TiDB·Render",
            "- 저장소 origin 을 fsclass-n/dataquill 로 변경, 작업 내용을 docs/md 에 날짜별로 누적 기록하기로 결정"],
        7: ["- 실제 ERP 연동 대상 선정 — 범위 외로 두고 데모 ERP 화면으로 검증하기로 결정",
            "- 파싱 정확도 정량 평가셋 구축 — 향후 과제로 보류"],
        8: ["- 요구사항 정의서, 기능 목록, 입력·출력 조사표, 기술 스택 선정서 작성(산출물 01)",
            "- 결정 사항: 소셜 로그인은 실제 OAuth 연동(Google·Naver·Kakao)으로 구현"],
        9: ["- AI 결과를 그대로 입력하지 않고 '추출 → 사람 검수 → 입력' 순서로 처리한다는 원칙 합의",
            "- 외부 의존성(LLM 키·OCR 엔진)이 없어도 서비스가 멈추지 않도록 대체 경로를 기본 설계에 포함"],
        10: ["- 스캔 PDF·사진은 텍스트 레이어가 없어 일반 추출이 불가능",
             "- LLM 이 문서에 없는 값을 지어낼(환각) 위험 — 회계 데이터에서는 치명적",
             "- 연동 API 가 없는 ERP 는 화면 구조에 의존해야 하므로 변경에 취약"],
        11: ["- 추출 단계별 대체 순서(텍스트 → OCR → 멀티모달) 설계",
             "- LLM 출력 형식을 강제하는 방법과 RPA 성공 판정 기준 설계"],
        12: ["설계 단계 — 시스템 아키텍처, 데이터 모델·API, 문서 처리 파이프라인, 권한·보안, 화면, 배포 구조 설계"],
    },
    "프로젝트_진행일지_2단계_설계.hwpx": {
        3: ["시스템 아키텍처, 데이터 모델(ERD)·API 명세, 문서 처리 파이프라인, AI 스키마·프롬프트, RPA 설계, 권한·보안, 화면, 배포 구조 설계"],
        4: ["- 프런트엔드·백엔드 분리 배포와 웹 계층(backend.app)·자동화 계층(rpa) 분리 구조 확정",
            "- API 검증과 LLM 출력에 같은 Pydantic 스키마를 쓰는 설계 확정"],
        5: ["- 설계 근거와 트레이드오프를 함께 기록",
            "- 비밀 값은 .env 하나로 관리하고 저장소에 포함하지 않음"],
        6: ["- 아키텍처: React SPA(정적 호스팅) ↔ FastAPI(Docker) ↔ TiDB Cloud, 외부 연동 Gemini API·OAuth 제공자",
            "- 데이터 모델: users(역할·OAuth 식별자) 1:N documents(원문·추출 결과 JSON·상태·파서) 1:N rpa_jobs(대상·결과·메시지)",
            "- 파이프라인: 업로드 → extract(텍스트 레이어 → Tesseract OCR → Gemini 멀티모달) → parser(Gemini 구조화 출력, 키 없으면 규칙 파서) → 검수(PATCH) → 엑셀 upsert / ERP 타이핑",
            "- AI: ParsedDocument(Pydantic) 를 응답 스키마로 전달, temperature 0, '문서에 없는 값은 null' 규칙",
            "- RPA: 셀렉터 맵으로 화면 구조와 코드 분리, ERP 결과 요소의 상태값·전표번호로 성공 판정, 엑셀은 문서 ID 기준 교체",
            "- 배포: Render(백엔드 Docker·프런트 Static Site), 변경 영역만 검증·배포(paths-filter·Build Filter), 백엔드 없이도 동작하는 Mock 모드"],
        7: ["- RPA 작업 큐(별도 워커) 분리 — 범위 외로 보류, rpa 패키지를 분리해 이전 비용을 낮춤",
            "- DB 마이그레이션 도구(Alembic) — create_all 로 시작하고 향후 도입"],
        8: ["- 아키텍처 설계서, ERD·테이블 명세, API 명세서, 파이프라인·AI·RPA 설계서, 화면 설계서 작성(산출물 02)"],
        9: ["- 로컬·테스트는 SQLite, 운영은 TiDB 로 URL 만 바꿔 같은 코드를 실행하기로 결정",
            "- 헬스 체크 응답에 현재 파서 종류(gemini/rules)를 노출해 설정 상태를 확인할 수 있게 함"],
        10: ["- RPA 가 API 요청 안에서 동기로 실행되어 오래 걸리는 작업에 취약",
             "- 업로드 원본을 컨테이너 디스크에 두면 재배포 시 유실 가능"],
        11: ["- 실제 ERP 셀렉터 확보 전까지 데모 ERP 화면으로 RPA 검증",
             "- 원본 파일 저장소(오브젝트 스토리지) 이전은 고도화 단계에서 검토"],
        12: ["구현 단계 — 백엔드 API·인증·OAuth, 추출·AI 파서, RPA(엑셀·ERP), 프런트엔드 화면, 자동 테스트"],
    },
    "프로젝트_진행일지_3단계_구현.hwpx": {
        3: ["백엔드(FastAPI) API·인증·OAuth, 텍스트 추출·AI 파서, RPA(엑셀 적재·ERP 자동 타이핑), 프런트엔드(React) 화면, 관리자 기능, 자동 테스트"],
        4: ["- 업로드 → 추출 → AI 정형화 → 검수 → 엑셀 적재·ERP 타이핑 전 과정 동작",
            "- 회원/관리자 권한 분리, 테스트 계정 원클릭 로그인, pytest 로 핵심 규칙 회귀 방지"],
        5: ["- 설계서의 API·데이터 정책을 그대로 구현하고 변경 시 문서 갱신",
            "- 비밀번호 규칙(영문 대·소문자+숫자+특수문자 8자 이상)은 화면과 서버 양쪽에서 검증"],
        6: ["- 백엔드: SQLAlchemy 2.0(SQLite/TiDB), JWT(HS256)·PBKDF2-SHA256 해시, OAuth 3사(state 쿠키 CSRF 검증), 문서 업로드(10MB)·본문 입력·검수·재해석·삭제, 관리자 회원·통계 API",
            "- 추출·AI: pypdf·Tesseract(kor+eng)·EML/HTML 파싱, Gemini 구조화 출력(멀티모달 포함), 규칙 기반 파서(찾은 필드 수로 신뢰도 산출)",
            "- RPA: 엑셀 원장 upsert(pandas+openpyxl), Playwright ERP 타이핑 + 데모 ERP 화면(/erp-demo, 전표번호 발급), CLI 단독 실행",
            "- 프런트엔드: React 19·Vite·Tailwind v4, Split 로그인·OAuth 버튼·비밀번호 실시간 체크, 모바일 햄버거↔X 드로어, 대시보드·문서 처리·관리자(회원·모니터링), 페이지 코드 스플리팅, Mock 모드"],
        7: ["- Gemini API 키·OAuth 앱 등록 후 실연동 테스트 — 배포 단계로 이월",
            "- TiDB 클러스터 연결 테스트 — 배포 단계로 이월"],
        8: ["- pytest 19개 통과, 프런트 lint 오류 0·build 성공",
            "- 실서버 E2E: 로그인 → 영수증 업로드 → 규칙 파싱 → Playwright 가 데모 ERP 에 입력(전표번호 발급) → 엑셀 적재 확인",
            "- 구현 산출물(디렉터리 구조·모듈 설명·테스트·트러블슈팅) 작성(산출물 03)"],
        9: ["- 데스크톱(1440)·모바일(390) 화면을 Playwright 스크린샷으로 점검, 콘솔 오류 없음",
            "- Mock 모드 빌드로 로그인·권한 변경 동작 확인"],
        10: ["- .env 에서 빈 값 뒤 인라인 주석이 값으로 읽혀 키가 없는데도 Gemini·OAuth 가 '설정됨'으로 동작 → 주석을 별도 줄로 분리",
             "- Tailwind v4 에서 @layer components 클래스는 @apply 불가 → @utility 로 정의",
             "- 헤더 backdrop-filter 가 fixed 드로어의 기준 박스가 되는 문제 → 드로어를 헤더 밖으로 분리"],
        11: ["- Gemini 실제 영수증 파싱 품질 확인",
             "- OAuth Redirect URI 등록, TiDB 연결, Render/Netlify 배포"],
        12: ["배포 단계 — Docker 이미지, Render(API·프런트)·Netlify 배포, TiDB 연결, CI/CD, 운영 점검"],
    },
    "프로젝트_진행일지_4단계_배포.hwpx": {
        3: ["Docker 이미지 빌드, Render(백엔드 Web Service·프런트 Static Site)·Netlify 배포, TiDB Cloud 연결, GitHub Actions CI/CD, 운영 점검"],
        4: ["- 운영 서비스 dataquill.onrender.com · API dataquill-api.onrender.com 정상 동작",
            "- main 푸시 시 변경 영역만 검증·배포"],
        5: ["- 비밀 값은 Render 대시보드에만 등록, .env.example 에 [LOCAL]/[RENDER]/[RENDER-FE] 등록 위치 표기",
            "- 운영 DB 는 직접 건드리지 않고 임시 DB 로 검증"],
        6: ["- backend/Dockerfile(python:3.11-slim-bookworm + Tesseract 한국어 + Chromium), frontend/Dockerfile(nginx), docker-compose.yml",
            "- render.yaml(Build Filter: backend/**·rpa/**·requirements.txt / frontend/**), netlify.toml, deploy.yml(paths-filter 로 변경 영역 테스트·빌드)",
            "- TiDB Cloud Serverless 연결(DB_SSL=true + certifi CA), OAuth Redirect URI 등록, Gemini API 키 등록",
            "- 운영 점검: 로그인·CORS·OAuth Redirect·Gemini 파싱·엑셀 적재·ERP 타이핑"],
        7: ["- 업로드 원본 오브젝트 스토리지 이전 — 고도화 단계로 보류",
            "- RPA 작업 큐 분리 — 고도화 단계로 보류"],
        8: ["- 운영 Gemini 파싱 샘플: 영수증에서 거래처·사업자번호·금액·부가세·품목 정상 추출(신뢰도 0.98)",
            "- Gemini 재시도 테스트 3개 추가, pytest 22개 통과",
            "- 배포 구성·환경 변수·CI/CD·운영 점검 결과 작성(산출물 04)"],
        9: ["- 운영에서만 발생한 문제는 근거(로그·소스·헬스 체크)로 원인을 확정하고, 고친 뒤 같은 상황을 재현하는 테스트를 추가하기로 합의"],
        10: ["- 코드 변경 없이 Docker 빌드 실패: slim 태그가 Debian 13 으로 바뀌어 Playwright 1.52 의존성 설치 실패 → slim-bookworm 고정",
             "- TiDB '1105 insecure transport prohibited' → TLS 설정",
             "- Gemini 503(high demand) → 429/5xx 만 2s·5s·10s 백오프 재시도",
             "- 운영 ERP 타이핑 연결 거부: Render PORT=10000 → 기본 주소 127.0.0.1:$PORT",
             "- /login 새로고침 404 → SPA Rewrite(/* → /index.html)"],
        11: ["- 공개 테스트 계정의 권한 범위 점검",
             "- 무료 플랜 유휴 슬립으로 첫 요청 지연"],
        12: ["피드백 단계 — 점검 결과 반영(UI 표준화, 권한 모델 개편), 발표자료·문서 정리"],
    },
    "프로젝트_진행일지_5단계_피드백.hwpx": {
        3: ["플랫폼 표준 가이드 점검 결과 반영(전역 레이아웃·도메인 맞춤 메인·상용 푸터), 권한 모델 개편, 발표자료 제작, 문서 정리"],
        4: ["- 공개 테스트 관리자 계정의 보안 문제 해소(읽기 전용 전환)",
            "- 모든 페이지 공통 레이아웃과 디자인 토큰 표준화, 발표자료·README·진행일지·산출물 정리"],
        5: ["- 실제로 구현·검증되지 않은 수치(정확도, 고객사 로고 등)와 가짜 사업자 정보는 화면·문서에 넣지 않음",
            "- 권한은 화면이 아닌 서버에서 강제"],
        6: ["- 전역 레이아웃: SiteLayout(헤더·푸터·원형 Top 버튼), 첫 접속은 항상 메인, 로그인 상태별 헤더 메뉴, 테스트 관리자 '읽기 전용' 배너",
            "- 메인 페이지: Hero(원문 → AI 추출 → 엑셀/ERP 전표), 지원 형식, 작동 방식 4단계, 주요 기능, 활용 사례, 보안·권한, FAQ",
            "- 디자인 토큰(text-display/title/heading/body/caption, container-page, section-y) 표준화, 이용약관·개인정보처리방침 페이지 신설",
            "- 권한 모델: 운영 관리자는 ADMIN_TOKEN 로그인(compare_digest, 5회 실패 시 10분 차단), test_admin 은 deps.get_current_user 에서 쓰기 요청 403, 테스트 계정 권한은 기동 시 복원·변경 불가",
            "- 발표자료(16장, 발표자 노트) 제작, README 재작성, 진행일지·산출물 HWPX/PDF 정리"],
        7: ["- 발표자료 화면 캡처 재촬영(개편 전 기준) — 최종 발표 전 재생성 예정",
            "- RPA 작업 큐 분리·원본 스토리지 이전 — 향후 계획"],
        8: ["- 권한 테스트 8개 추가, pytest 30개 통과, 프런트 lint 오류 0·build 성공",
            "- 로컬 데모 인스턴스 Playwright 점검 16항목 통과(첫 접속 메인, 헤더/푸터, 읽기 전용 배너·버튼 비활성, 잘못된 토큰 거부 등)",
            "- 피드백 반영 내역·회고·향후 계획 작성(산출물 05)"],
        9: ["- 회고: 대체 경로 설계(텍스트 → OCR → Vision, Gemini → 규칙)와 화면·서버 양쪽 검증이 안정성에 효과적",
            "- 실패 원인 대부분이 외부 의존성(기본 이미지, LLM 가용성, 플랫폼 포트) → 처음부터 버전 고정·재시도 필요"],
        10: ["- 공개된 테스트 관리자 계정이 실제 관리자 권한을 가져 누구나 회원 권한 변경 가능(개편으로 해소)",
             "- Tailwind 기본 유틸리티 overline 과 이름이 겹쳐 텍스트에 줄이 그어짐 → eyebrow 로 변경"],
        11: ["- RPA 작업 큐 분리, 원본 오브젝트 스토리지 이전, Alembic 마이그레이션",
             "- 정답셋 기반 필드 단위 정확도 측정, 실제 ERP 커넥터"],
        12: ["고도화 — RPA 비동기 작업 큐, 원본 스토리지 이전, 정량 정확도 평가, 실제 ERP·조직 단위 권한"],
    },
}


def para_xml(text: str, para_pr: str, char_pr: str) -> str:
    return (f'<hp:p id="0" paraPrIDRef="{para_pr}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{char_pr}"><hp:t>{html.escape(text, quote=False)}</hp:t></hp:run></hp:p>')


def fill_journal(path: Path, rows: dict) -> None:
    rows = {**COMMON, **rows}
    with zipfile.ZipFile(path) as z:
        items = {n: z.read(n) for n in z.namelist()}
        infos = {i.filename: i for i in z.infolist()}
    xml = items["Contents/section0.xml"].decode("utf-8")

    def repl(m):
        tc = m.group(0)
        a = re.search(r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"', tc)
        col, row = int(a.group(1)), int(a.group(2))
        target = (row in (1, 2) and col == 2) or (3 <= row <= 12 and col == 1)
        if not target or row not in rows:
            return tc
        if re.search(r"<hp:t>[^<]+</hp:t>", tc):  # 이미 내용이 있으면 보존
            return tc
        p = re.search(r'<hp:p id="0" paraPrIDRef="(\d+)"[^>]*><hp:run charPrIDRef="(\d+)"', tc)
        body = "".join(para_xml(t, p.group(1), p.group(2)) for t in rows[row])
        return re.sub(r"(<hp:subList[^>]*>).*?(</hp:subList>)", lambda s: s.group(1) + body + s.group(2), tc, count=1, flags=re.S)

    xml = re.sub(r"<hp:tc .*?</hp:tc>", repl, xml, flags=re.S)
    items["Contents/section0.xml"] = xml.encode("utf-8")
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w") as z:
        for name, data in items.items():  # mimetype 은 첫 항목·무압축 유지
            z.writestr(infos[name], data, compress_type=zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED)
    tmp.replace(path)


# ============================================================================ 산출물 원고 (HTML)
CSS = """<style>
body{font-family:'맑은 고딕';font-size:10pt;line-height:160%}
h1{font-size:20pt;text-align:center} h2{font-size:14pt;color:#1f3a5f;border-bottom:1px solid #1f3a5f} h3{font-size:11.5pt}
table{border-collapse:collapse;width:100%} th,td{border:1px solid #666;padding:3px 5px;font-size:9.5pt;vertical-align:top}
th{background:#dfe6f0}
</style>"""

CELL = "font-family:'맑은 고딕';font-size:9.5pt;text-align:left"


def table(head, rows):
    # 한글 HTML 가져오기는 CSS 를 대부분 무시하므로 열 너비·배경·정렬을 속성으로 지정 (너비는 내용 길이 비례)
    cols = len(head)
    avg = [sum(len(re.sub("<[^>]+>", "", str(r[i]))) for r in [head, *rows]) / (len(rows) + 1) for i in range(cols)]
    weight = [min(max(a, 9), 55) for a in avg]
    widths = [round(w * 100 / sum(weight)) for w in weight]
    h = "".join(f'<th bgcolor="#DCE4EF" align="left" width="{w}%" style="{CELL};font-weight:bold">{c}</th>' for c, w in zip(head, widths))
    b = "".join("<tr>" + "".join(f'<td align="left" valign="top" width="{w}%" style="{CELL}">{c}</td>' for c, w in zip(r, widths)) + "</tr>" for r in rows)
    return f'<table border="1" cellspacing="0" cellpadding="4" width="100%">{"<tr>" + h + "</tr>"}{b}</table><p></p>'


def ul(items):
    return "".join(f'<p align="left" style="{CELL};font-size:10pt">· {i}</p>' for i in items) + "<p></p>"


def pre(text):
    lines = html.escape(text.strip("\n"), quote=False).split("\n")
    return "".join(f'<p align="left" style="font-family:\'D2Coding\',\'Consolas\';font-size:9pt">{l.replace(" ", "&nbsp;") or "&nbsp;"}</p>' for l in lines) + "<p></p>"


def doc(title, stage, period, sections):
    meta = table(["항목", "내용"], [["프로젝트", TOPIC], ["과정", "[K-Digital] 심화_생성형 AI와 AWS 클라우드를 활용한 풀스택 & 자동화 실무 개발 Final-Project"],
                                   ["단계", stage], ["기간", period], ["작성", "3조 · " + TEAM], ["서비스", SERVICE], ["저장소", REPO]])
    body = "".join(f'<h2><font face="맑은 고딕" color="#1F3A5F">{h}</font></h2>{c}' for h, c in sections)
    body = body.replace("<p>", f'<p align="left" style="{CELL};font-size:10pt">')
    return (f"<html><head><meta charset='utf-8'>{CSS}</head><body><h1 align='center'><font face='맑은 고딕'>{title}</font></h1>"
            f"{meta}{body}</body></html>")


P1 = doc("01. 기획·분석 산출물", "1단계 기획·분석", "2026년 11월 23일(월) ~ 11월 24일(화)", [
    ("1. 프로젝트 개요", "<p>영수증·세금계산서·거래 이메일 같은 비정형 문서를 생성형 AI(Gemini)가 읽어 정형 데이터로 바꾸고, "
     "사람이 검수한 뒤 RPA(Playwright)가 웹 ERP 전표 화면과 엑셀 원장에 대신 입력하는 B2B 데이터 입력 자동화 플랫폼이다.</p>"
     + table(["구분", "내용"], [["핵심 가치", "같은 문서를 ERP·엑셀에 반복 입력하는 일을 'AI 추출 → 사람 검수 → 로봇 입력'으로 대체"],
                               ["대상 사용자", "경리·회계, 구매·총무, 영업지원 담당자 / 서비스 운영 관리자"],
                               ["입력", "PDF, 이미지(JPG·PNG·WEBP·BMP·TIFF), EML, HTML, TXT 업로드(최대 10MB), 이메일 본문 붙여넣기"],
                               ["출력", "엑셀 원장(xlsx) 적재, 웹 ERP 전표 자동 입력(전표번호 발급)"]])),
    ("2. 배경 및 문제 정의", table(["문제", "현상", "해결 방향"], [
        ["이중 수기 입력", "같은 영수증·청구 메일을 ERP 에 한 번, 엑셀 원장에 또 한 번 입력", "한 번 추출한 결과를 엑셀·ERP 에 자동 입력"],
        ["문서 형식의 다양성", "거래처마다 양식이 달라 정규식 규칙으로는 한계", "생성형 AI 구조화 출력으로 필드 추출"],
        ["스캔본·사진", "텍스트 레이어가 없어 일반 추출 불가", "OCR → LLM 멀티모달 순서로 대체"],
        ["API 없는 ERP", "사내 ERP 에 연동 API 가 없는 경우가 많음", "사람처럼 화면에 입력하는 RPA"],
        ["AI 오류(환각)", "문서에 없는 값을 그럴듯하게 생성할 위험", "'없는 값은 null' 규칙 + 사람 검수 단계"]])),
    ("3. 목표", ul(["6가지 입력 형식에서 회계 전표 필드를 JSON 으로 추출하고 신뢰도를 함께 제공",
                   "AI 키·OCR 엔진이 없어도 동작하는 대체 경로(규칙 기반 파서) 제공",
                   "검수 후 엑셀 원장 적재(중복 없음)와 ERP 자동 입력(전표번호 확인)",
                   "이메일 가입·OAuth 3사 로그인, 운영 관리자·테스트 관리자·일반 사용자 권한 분리",
                   "반응형 UI, 관리자 모니터링(파싱·RPA 성공률), 클라우드 자동 배포"])),
    ("4. 추출 필드 정의", table(["필드", "설명", "형식"], [
        ["document_type", "문서 유형", "receipt / invoice / email / other"], ["vendor", "거래처(상호명)", "문자열"],
        ["business_number", "사업자등록번호", "000-00-00000"], ["date", "거래일자", "YYYY-MM-DD"],
        ["total_amount · vat", "합계 금액 · 부가세", "원 단위 정수"], ["payment_method", "결제수단", "신용카드·현금·계좌이체 등"],
        ["items", "품목 목록", "품명·수량·단가·금액"], ["summary", "한 줄 적요", "문자열"], ["confidence", "추출 신뢰도", "0 ~ 1"]])),
    ("5. 기능 요구사항", table(["ID", "구분", "요구사항", "우선순위"], [
        ["FR-01", "회원", "이메일 가입·로그인(JWT), 비밀번호 규칙(영문 대·소문자+숫자+특수문자 8자 이상) 화면·서버 검증", "상"],
        ["FR-02", "회원", "Google·Naver·Kakao OAuth 로그인, 이메일 중복 가입 차단", "중"],
        ["FR-03", "회원", "일반 사용자·테스트 관리자 원클릭 로그인", "상"],
        ["FR-04", "문서", "파일 업로드(10MB)·이메일 본문 입력, 지원하지 않는 형식 거부", "상"],
        ["FR-05", "AI", "Gemini 구조화 추출(이미지·스캔본 멀티모달), 키가 없으면 규칙 기반 파서", "상"],
        ["FR-06", "검수", "추출 결과 화면 수정·저장(서버 재검증), 재해석, 삭제", "상"],
        ["FR-07", "RPA", "엑셀 원장 적재(문서 ID 기준 교체)·다운로드", "상"],
        ["FR-08", "RPA", "웹 ERP 전표 자동 입력, 전표번호 확인 후 성공 기록, 작업 이력", "상"],
        ["FR-09", "대시보드", "사용자 KPI, 최근 14일 처리 추이, 입력 소스 분포, 최근 문서", "중"],
        ["FR-10", "관리자", "회원 목록·검색·권한 변경, 파싱·RPA 성공률 모니터링, 최근 실패", "상"],
        ["FR-11", "공통", "반응형 GNB(햄버거↔X, 우측 드로어), To the Top 버튼, 토스트 알림", "중"]])),
    ("6. 비기능 요구사항", table(["ID", "항목", "요구사항"], [
        ["NFR-01", "신뢰성", "LLM 응답은 스키마로 강제하고 문서에 없는 값은 null, 사람 검수 후 입력"],
        ["NFR-02", "가용성", "LLM 키 없음·일시 장애·OCR 미설치 시에도 대체 경로로 서비스 지속"],
        ["NFR-03", "정합성", "엑셀 재적재 시 중복 행 없음, RPA 는 결과 확인 후에만 성공 처리"],
        ["NFR-04", "보안", "JWT 인증, PBKDF2 해시, OAuth state 검증, CORS 제한, 비밀 값 .env 관리, 권한은 서버에서 강제"],
        ["NFR-05", "배포", "프런트·백엔드 독립 배포, 변경 영역만 검증·배포"],
        ["NFR-06", "투명성", "검증되지 않은 수치·가짜 사업자 정보는 화면·문서에 넣지 않음"]])),
    ("7. 기술 스택 선정", table(["영역", "선택", "근거"], [
        ["Backend", "Python 3.11 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · PyJWT", "Pydantic 으로 요청 검증·응답 모델·LLM 스키마 공유, /docs 자동 생성"],
        ["AI", "Google Gemini(google-genai)", "구조화 출력(response_schema), 이미지·PDF 멀티모달"],
        ["RPA·데이터", "Playwright · pandas · openpyxl · pypdf · pytesseract · BeautifulSoup4", "API 없는 ERP 화면 입력, 엑셀 원장, PDF·OCR·HTML 추출"],
        ["Frontend", "React 19 · Vite · Tailwind CSS v4 · React Router · Recharts · FontAwesome", "컴포넌트화, 디자인 토큰, 차트"],
        ["DB", "TiDB Cloud Serverless(MySQL 호환) / SQLite", "운영은 관리형 DB, 로컬·테스트는 URL 만 바꿔 같은 코드"],
        ["Infra", "Docker · Render · Netlify · GitHub Actions", "Chromium·Tesseract 포함 이미지, 조건부 배포"]])),
    ("8. 일정 계획", table(["단계", "기간", "주요 산출물"], [
        ["1단계 기획·분석", "11/23 ~ 11/24", "요구사항 정의서, 추출 필드 정의, 기술 스택 선정서"],
        ["2단계 설계", "11/25 ~ 11/27", "아키텍처·ERD·API·파이프라인·권한·화면 설계서"],
        ["3단계 구현", "11/30 ~ 12/09", "백엔드·RPA·AI 파서·프런트엔드, 테스트 결과"],
        ["4단계 배포", "12/10 ~ 12/17", "Render·Netlify 배포, CI/CD, 운영 점검 결과"],
        ["5단계 피드백", "12/18 ~ 12/21", "UI·권한 개편, 발표자료, 회고·향후 계획"]])),
    ("9. 위험 요소 및 대응", table(["위험", "영향", "대응"], [
        ["LLM 환각·형식 오류", "잘못된 회계 데이터 입력", "스키마 강제, temperature 0, null 규칙, 사람 검수"],
        ["LLM 일시 장애·키 없음", "파싱 실패", "일시 오류만 재시도, 규칙 기반 파서 대체"],
        ["ERP 화면 변경", "RPA 실패", "셀렉터 맵 분리, 결과 확인 후 성공 처리, 실패 사유 기록"],
        ["공개 테스트 계정 악용", "데이터·권한 변조", "서버 측 권한 강제(5단계에서 읽기 전용으로 강화)"]])),
])

P2 = doc("02. 설계 산출물", "2단계 설계", "2026년 11월 25일(수) ~ 11월 27일(금)", [
    ("1. 시스템 아키텍처", "<p>구성: React SPA(Render Static Site) ↔ FastAPI(Render Web Service, Docker) ↔ TiDB Cloud Serverless, 외부 연동 Google Gemini API · OAuth 제공자(Google·Naver·Kakao)</p>"
     + table(["구성 요소", "역할", "설계 근거"], [
        ["frontend", "랜딩·로그인·대시보드·문서 처리·관리자 화면", "정적 배포로 백엔드와 배포 주기·장애 범위 분리"],
        ["backend.app", "routers(auth·documents·admin·erp_demo), services(parser·oauth·stats)", "웹 계층과 자동화 계층 분리"],
        ["rpa", "extract(텍스트·OCR) · excel_writer · erp_typer(Playwright)", "CLI 단독 실행 가능 → 향후 별도 워커로 이전 용이"],
        ["TiDB Cloud", "회원·문서·RPA 작업 이력 저장", "무상태 컨테이너 + 외부 DB → 재배포해도 데이터 유지"],
        ["Gemini API", "문서 구조화 추출", "구조화 출력·멀티모달"],
        ["데모 ERP(/erp-demo)", "RPA 입력 대상 화면, 전표번호 발급", "실제 ERP 없이 RPA 전 과정 검증"]])),
    ("2. 문서 처리 파이프라인", table(["단계", "모듈", "처리", "실패 시"], [
        ["① 추출", "rpa/extract.py", "PDF 텍스트 레이어 → 이미지 Tesseract(kor+eng) → 20자 미만이면 원본을 Gemini 멀티모달로 전달, EML 헤더+본문, HTML 정리", "미지원 형식 415"],
        ["② 정형화", "services/parser.py", "Gemini 구조화 출력(ParsedDocument), 키가 없으면 규칙 파서", "429·5xx 재시도, 최종 실패 시 문서 상태 failed + 사유"],
        ["③ 검수", "routers/documents.py", "화면 수정값을 같은 스키마로 재검증 후 저장", "형식 오류 422"],
        ["④ 입력", "rpa/excel_writer.py · erp_typer.py", "엑셀 원장 upsert / ERP 화면 입력 후 결과 확인", "rpa_jobs 에 실패 사유 기록"]])),
    ("3. ERD · 테이블 명세", table(["테이블", "주요 컬럼", "제약 / 관계"], [
        ["users", "id, email, name, password_hash, role(user·test_admin·admin), provider, provider_id, created_at, last_login_at", "email UNIQUE, (provider, provider_id) UNIQUE"],
        ["documents", "id, user_id, filename, source_type, storage_path, status(uploaded·parsed·failed), raw_text, parsed(JSON), parser(gemini·rules), error, created_at, parsed_at", "users 1:N, user_id 인덱스"],
        ["rpa_jobs", "id, document_id, target(excel·erp), status(pending·success·failed), message, created_at, finished_at", "documents 1:N"]])),
    ("4. API 명세", table(["Method", "Endpoint", "설명", "권한"], [
        ["POST", "/api/auth/register · /login", "이메일 가입·로그인(JWT)", "-"],
        ["POST", "/api/auth/admin-login", "ADMIN_TOKEN 운영 관리자 로그인", "-"],
        ["GET", "/api/auth/oauth/{provider}/login · /callback", "OAuth Authorization Code 흐름", "-"],
        ["GET", "/api/auth/me · /providers", "내 정보, 활성 OAuth 제공자", "로그인"],
        ["GET", "/api/dashboard", "사용자 KPI·일별 추이", "로그인"],
        ["GET · POST", "/api/documents · /upload · /text", "목록, 업로드, 본문 입력", "로그인"],
        ["GET · PATCH · DELETE", "/api/documents/{id}", "상세, 검수 수정, 삭제", "본인"],
        ["POST", "/api/documents/{id}/reparse · /rpa", "재해석, 엑셀·ERP 입력", "본인"],
        ["GET", "/api/documents/ledger.xlsx", "엑셀 원장 다운로드", "로그인"],
        ["GET · PATCH", "/api/admin/users · /users/{id}/role · /stats", "회원 관리, 통계", "관리자"],
        ["GET", "/api/health", "상태, 현재 파서 종류", "-"]])),
    ("5. AI 정형화 설계", ul(["ParsedDocument(Pydantic) 를 Gemini response_schema 와 API 검증 모델로 함께 사용 — 한쪽만 고치면 됨",
                            "프롬프트: 회계 전표 입력 담당자 역할, 금액은 정수, 날짜는 YYYY-MM-DD, '문서에 없는 값은 null, 추측 금지', confidence(0~1)",
                            "temperature 0, 문서 텍스트는 최대 30,000자, 이미지·스캔 PDF 는 원본 바이트를 함께 전달",
                            "재시도 정책: 429·500·503·504 만 2s → 5s → 10s 백오프(최대 4회 시도), 400 등 요청 오류는 즉시 실패",
                            "규칙 기반 파서: 날짜·사업자번호·합계·부가세·결제수단·품목 줄 정규식, confidence = 0.2 + 0.15 × 찾은 핵심 필드 수 + 0.1(품목 있음)"])),
    ("6. RPA 설계", table(["항목", "설계"], [
        ["화면 분리", "FIELD_SELECTORS 맵(vendor·business_number·date·total_amount·vat·summary), SUBMIT·RESULT 셀렉터"],
        ["성공 판정", "결과 요소의 data-status=\"ok\" 와 data-voucher(전표번호)를 확인해야 성공"],
        ["대상 주소", "ERP_URL 미설정 시 같은 서버의 데모 ERP(127.0.0.1:$PORT/erp-demo)"],
        ["실행 모드", "RPA_HEADLESS(기본 true), CLI: python -m rpa.erp_typer"],
        ["엑셀 적재", "문서ID 기준 기존 행 교체 후 정렬, 열 너비 자동 조정, 사용자별 원장 파일"],
        ["오류 처리", "Chromium 미설치 등 환경 오류를 안내 문구로 변환해 작업 이력에 기록"]])),
    ("7. 권한 · 보안 설계", table(["항목", "설계"], [
        ["인증", "JWT(HS256, 만료 시간), PBKDF2-SHA256 26만 회 반복 해시"],
        ["OAuth", "state 쿠키로 CSRF 검증, (provider, provider_id) 식별, 이메일 중복 가입 차단"],
        ["권한", "역할 user / admin, 관리자 라우터는 require_admin 의존성, 문서는 본인 소유만 접근"],
        ["입력 검증", "업로드 확장자·10MB 제한, Pydantic 스키마 검증"],
        ["비밀 값", "루트 .env 하나로 관리(Vite 는 VITE_ 접두사만 노출), 저장소 미포함"]])),
    ("8. 화면 설계", table(["화면", "구성 요소"], [
        ["로그인", "Split 레이아웃(좌측 브랜드 그래픽), 테스트 계정 버튼, OAuth 3사 버튼, 비밀번호 규칙 실시간 체크, 회원가입 전환"],
        ["대시보드", "KPI 카드, 최근 14일 처리 추이, 입력 소스 분포, 최근 문서"],
        ["문서 처리", "드래그&드롭 업로드 / 이메일 본문 탭, 추출 결과 검수 폼, 엑셀 적재·ERP 입력 버튼, 작업 이력"],
        ["관리자", "회원 관리(검색·필터·권한 토글), 모니터링(성공률 게이지, 일별 차트, 분포 도넛, 최근 실패)"],
        ["공통", "반응형 GNB(햄버거↔X, 우측 드로어·백드롭·ESC·스크롤 잠금), To the Top, 토스트"]])),
    ("9. 배포 설계", ul(["백엔드: Docker(Tesseract 한국어 + Chromium), Render Web Service, 헬스 체크 /api/health",
                       "프런트엔드: Render Static Site(/* → /index.html), Netlify 보조",
                       "CI/CD: GitHub Actions paths-filter 로 변경 영역만 테스트·빌드, Render Build Filter 로 변경 영역만 배포",
                       "Mock 모드: VITE_API_URL 미설정 시 localStorage 목업 API → 백엔드 없이 프런트 단독 배포"])),
])

P3 = doc("03. 구현 산출물", "3단계 구현", "2026년 11월 30일(월) ~ 12월 09일(수)", [
    ("1. 디렉터리 구조", table(["경로", "설명"], [
        ["backend/app/main.py", "앱 생성, CORS, 테이블 생성, 테스트 계정 시드"],
        ["backend/app/config.py · database.py", "루트 .env 설정, SQLAlchemy 엔진(SQLite / TiDB + TLS)"],
        ["backend/app/deps.py · security.py", "인증·권한 의존성, PBKDF2 해시·JWT"],
        ["backend/app/routers/", "auth · documents · admin · erp_demo"],
        ["backend/app/services/", "parser(Gemini/규칙) · oauth · stats"],
        ["backend/tests/", "pytest (외부 키를 비워 로컬 설정과 무관하게 실행, 임시 DB)"],
        ["rpa/", "extract.py · excel_writer.py · erp_typer.py"],
        ["frontend/src/", "pages · components · api(client·mock) · context(Auth·Toast) · utils"],
        ["docs/md/", "작업일별 결정·검증·이슈 기록"]])),
    ("2. 모듈별 구현 내용", table(["모듈", "구현 내용"], [
        ["routers/auth.py", "가입·로그인, OAuth 로그인/콜백(state 쿠키 검증), 내 정보, 활성 제공자 목록"],
        ["routers/documents.py", "업로드(확장자·10MB 검사, UUID 파일명 저장), 본문 입력(HTML 정리), 검수 PATCH(스키마 재검증), 재해석, 삭제, RPA 실행, 원장 다운로드"],
        ["routers/admin.py", "회원 목록·검색, 권한 변경(본인 강등 차단), 통계"],
        ["routers/erp_demo.py", "데모 ERP 전표 입력 화면, 전표번호(JV-YYYYMMDD-NNNN) 발급 API"],
        ["services/parser.py", "Gemini 구조화 출력·멀티모달, 규칙 기반 파서, ParseError 로 실패 사유 전달"],
        ["services/stats.py", "파싱 성공률 parsed/(parsed+failed), RPA 성공률 success/(success+failed), 최근 14일 KST 일별 추이, 분포"],
        ["rpa/extract.py", "pypdf, Tesseract(kor+eng), EML(plain/html), HTML(BeautifulSoup), 인코딩 자동 판별(utf-8·cp949·euc-kr)"],
        ["rpa/excel_writer.py", "문서ID 기준 upsert, 열 너비 자동 조정"],
        ["rpa/erp_typer.py", "Playwright 셀렉터 입력 → 저장 → 결과 확인, CLI 실행"],
        ["frontend", "Login·Dashboard·Documents·AdminUsers·AdminMonitoring 페이지, Recharts 차트, 페이지 단위 코드 스플리팅, Mock API"]])),
    ("3. 핵심 구현 — Gemini 구조화 출력과 재시도", pre("""
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=ParsedDocument,
    temperature=0,
)
for attempt, delay in enumerate((*RETRY_DELAYS, None)):   # 2s, 5s, 10s
    try:
        response = client.models.generate_content(
            model=settings.gemini_model, contents=contents, config=config)
        break
    except genai_errors.APIError as exc:
        if exc.code in RETRYABLE_STATUS and delay is not None:
            time.sleep(delay)
            continue
        raise ParseError(...)
return ParsedDocument.model_validate_json(response.text).model_dump()
""")),
    ("4. 핵심 구현 — 단계적 텍스트 추출", pre("""
if suffix in PDF_TYPES:
    text = _pdf_text(data)
    if len(text) >= MIN_TEXT_LENGTH:          # 20
        return Extraction(text, "pdf-text")
    return Extraction(text, "vision", needs_vision=True, mime_type=...)
if suffix in IMAGE_TYPES:
    if tesseract_available():
        text = _ocr_image(data)                # lang="kor+eng"
        if len(text) >= MIN_TEXT_LENGTH:
            return Extraction(text, "tesseract")
    return Extraction("", "vision", needs_vision=True, mime_type=...)
""")),
    ("5. 핵심 구현 — RPA 결과 확인", pre("""
page.goto(url, wait_until="domcontentloaded", timeout=15_000)
for key, selector in FIELD_SELECTORS.items():
    page.fill(selector, "")
    page.type(selector, str(value), delay=delay_ms)
page.click(SUBMIT_SELECTOR)
result = page.wait_for_selector("#result[data-status]", timeout=10_000)
if result.get_attribute("data-status") != "ok":
    raise ErpTypingError(result.inner_text())
return result.get_attribute("data-voucher")
""")),
    ("6. 테스트", table(["구분", "대상", "검증 내용"], [
        ["단위", "비밀번호 규칙", "대·소문자·숫자·특수문자·길이 조합별 허용/거부"],
        ["통합", "회원", "약한 비밀번호 거부, 가입·내 정보, 로그인 실패"],
        ["통합", "OAuth", "미설정 제공자는 로그인 화면으로 이동, 잘못된 state 거부"],
        ["통합", "문서·RPA", "업로드 → 파싱 → 엑셀 적재, 본문 입력·검수 수정, 해석 불가 문서 failed, 미지원 형식 415"],
        ["통합", "대시보드·관리자", "사용자별 통계 범위, 관리자 권한 검사, 회원 관리·통계"],
        ["통합", "데모 ERP", "전표 입력 시 전표번호 발급"]])
     + "<p>결과: pytest 19개 통과, 프런트 lint 오류 0·build 성공. 실서버 E2E(로그인 → 영수증 업로드 → 규칙 파싱 → Playwright 데모 ERP 입력·전표번호 발급 → 엑셀 적재)와 "
       "데스크톱(1440)·모바일(390) 화면을 Playwright 로 점검하였다.</p>"),
    ("7. 트러블슈팅", table(["문제", "원인", "해결"], [
        ["키를 넣지 않았는데 Gemini·OAuth 가 '설정됨'", ".env 에서 빈 값 뒤 인라인 주석이 값으로 읽힘", "주석을 별도 줄로 분리, 규칙 문서화, 테스트는 외부 키를 빈 값으로 고정"],
        ["Tailwind 사용자 클래스 @apply 오류", "v4 는 @layer components 클래스에 @apply 불가", "@utility 로 정의"],
        ["모바일 드로어 위치 오류", "헤더 backdrop-filter 가 fixed 요소의 기준 박스가 됨", "드로어를 헤더 밖으로 분리"],
        ["초기 번들 크기", "단일 번들 885KB", "페이지 단위 코드 스플리팅(메인 416KB, 차트는 사용 페이지에서만 로드)"]])),
])

P4 = doc("04. 배포 산출물", "4단계 배포", "2026년 12월 10일(목) ~ 12월 17일(목)", [
    ("1. 배포 구성", table(["구분", "주소", "플랫폼"], [
        ["프런트엔드", "https://dataquill.onrender.com", "Render Static Site (/* → /index.html Rewrite)"],
        ["백엔드 API", "https://dataquill-api.onrender.com (/docs, /api/health)", "Render Web Service (Docker)"],
        ["프런트엔드(보조)", "https://dataquill.netlify.app", "Netlify"],
        ["데이터베이스", "TiDB Cloud Serverless", "MySQL 호환 · TLS 필수"],
        ["저장소", REPO, "GitHub"]])),
    ("2. 컨테이너 · 인프라", ul([
        "backend/Dockerfile: python:3.11-slim-bookworm 고정, Tesseract OCR(한국어), playwright install --with-deps chromium, PORT 환경 변수로 uvicorn 실행",
        "frontend/Dockerfile: 빌드 후 nginx 로 정적 파일 제공",
        "docker-compose.yml: backend(8000) · frontend(5173), 업로드 저장소 볼륨",
        "render.yaml: 두 서비스 정의, Build Filter(backend/**·rpa/**·requirements.txt / frontend/**), 헬스 체크 /api/health",
        "netlify.toml: frontend/ 변경 시에만 빌드, SPA 리다이렉트"])),
    ("3. CI/CD", table(["Job", "조건", "내용"], [
        ["changes", "항상", "dorny/paths-filter 로 frontend / backend 변경 판별"],
        ["frontend", "frontend/** 변경", "npm ci · lint · build, Netlify 시크릿이 있으면 배포"],
        ["backend", "backend/**·rpa/**·requirements.txt 변경", "pip install · pytest, Render 배포 훅이 있으면 배포"]])
     + "<p>기본 배포는 Render·Netlify 의 Git 연동 자동 배포이며, Actions 는 테스트·빌드를 담당한다(시크릿 미등록 시 배포 단계 생략). 문서만 고친 커밋은 어떤 서비스도 다시 빌드하지 않는다.</p>"),
    ("4. 환경 변수 명세 (값은 저장소에 포함하지 않음)", table(["그룹", "키", "설명"], [
        ["앱", "APP_ENV, SECRET_KEY, JWT_EXPIRE_MINUTES", "JWT 서명 키 등"],
        ["관리자", "ADMIN_TOKEN, ADMIN_EMAIL", "운영 관리자 토큰 로그인"],
        ["DB", "DATABASE_URL, DB_SSL, DB_SSL_CA", "TiDB 는 DB_SSL=true 필수"],
        ["주소", "FRONTEND_URL, BACKEND_URL, CORS_ORIGINS", "OAuth 복귀·콜백, CORS"],
        ["계정", "SEED_TEST_ACCOUNTS", "테스트 계정 자동 생성"],
        ["AI", "GEMINI_API_KEY, GEMINI_MODEL", "비우면 규칙 기반 파서"],
        ["OAuth", "GOOGLE/NAVER/KAKAO_CLIENT_ID · _CLIENT_SECRET", "Redirect URI: {BACKEND_URL}/api/auth/oauth/{provider}/callback"],
        ["RPA", "ERP_URL, RPA_HEADLESS", "비우면 같은 서버의 데모 ERP"],
        ["프런트", "VITE_API_URL", "비우면 Mock 모드"]])),
    ("5. 운영 점검 결과", table(["항목", "결과"], [
        ["/api/health", "status ok, env production, parser gemini"],
        ["로그인 · CORS", "프런트 도메인에서 로그인·API 호출 정상"],
        ["OAuth Redirect", "운영 콜백 주소로 이동 확인"],
        ["Gemini 파싱", "영수증 샘플에서 거래처·사업자번호·금액·부가세·품목 정상 추출(신뢰도 0.98)"],
        ["RPA", "운영 컨테이너에서 데모 ERP 입력·전표번호 발급, 엑셀 적재 확인"],
        ["SPA 라우팅", "Rewrite 적용 후 /login 등 딥링크 새로고침 정상"]])),
    ("6. 운영 이슈 및 조치", table(["이슈", "원인", "조치"], [
        ["코드 변경 없이 Docker 빌드 실패", "slim 태그가 Debian 13 으로 바뀌어 Playwright 1.52 의존성(Debian 11/12 만 지원) 설치 실패", "python:3.11-slim-bookworm 고정"],
        ["TiDB 1105 insecure transport", "TiDB Serverless 는 TLS 필수", "DB_SSL=true + certifi CA, 임시 DB 로 전체 흐름 검증 후 삭제"],
        ["Gemini 503(high demand)", "사용량 폭주 시 일시 오류", "429·5xx 만 백오프 재시도, 재시도 테스트 3개 추가(pytest 22개)"],
        ["운영 ERP 타이핑 연결 거부", "Render 컨테이너는 PORT=10000", "기본 대상 127.0.0.1:$PORT"],
        ["/login 새로고침 404", "정적 호스팅 SPA 규칙 없음", "/* → /index.html Rewrite"]])),
    ("7. 결과물", table(["결과물", "위치"], [
        ["소스 코드 · README", REPO],
        ["운영 서비스", "https://dataquill.onrender.com"],
        ["API 문서", "https://dataquill-api.onrender.com/docs"],
        ["작업 기록", "docs/md/"]])),
])

P5 = doc("05. 피드백 산출물", "5단계 피드백", "2026년 12월 18일(금) ~ 12월 21일(월)", [
    ("1. 점검 개요", "<p>배포 후 플랫폼 표준 가이드(전역 레이아웃 · 도메인 맞춤 UI · 상용 푸터 · 관리자/테스트 관리자 권한) 기준으로 서비스를 점검하고, 발견된 문제를 반영하였다.</p>"),
    ("2. 피드백 내용 및 반영 결과", table(["No", "피드백 / 발견 사항", "조치", "상태"], [
        ["1", "공개된 테스트 관리자 계정이 실제 관리자 권한을 가져 누구나 회원 권한 변경 가능(보안)", "test_admin 역할 신설, 서버에서 쓰기 요청 403", "반영"],
        ["2", "운영 관리자 진입 경로가 공개 계정과 분리되어 있지 않음", "/admin/login + ADMIN_TOKEN, compare_digest, 5회 실패 시 10분 차단", "반영"],
        ["3", "페이지마다 헤더·푸터 구성이 다름", "SiteLayout 으로 전 페이지 공통화, 원형 Top 버튼", "반영"],
        ["4", "첫 화면에서 서비스 성격이 드러나지 않음", "도메인 맞춤 메인(Hero·지원 형식·작동 방식·기능·활용 사례·보안·FAQ)", "반영"],
        ["5", "상용 서비스 수준의 푸터·정책 페이지 부재", "4열 푸터, 이용약관·개인정보처리방침 신설(가짜 사업자 정보 미기재)", "반영"],
        ["6", "글자 크기·여백이 화면마다 다름", "디자인 토큰(text-display~caption, container-page, section-y, page-y)", "반영"],
        ["7", "발표자료 화면 캡처가 개편 전 기준", "최종 발표 전 재촬영·재생성", "예정"]])),
    ("3. 권한 모델", table(["역할", "진입", "권한"], [
        ["admin 운영 관리자", "/admin/login 에서 ADMIN_TOKEN 입력", "전체 CRUD, 회원 권한 변경"],
        ["test_admin 테스트 관리자", "로그인 화면 버튼", "관리자 화면 조회만, 쓰기 요청 403"],
        ["user 일반 사용자", "가입 · OAuth · 테스트 버튼", "본인 문서"]])
     + ul(["deps.get_current_user 단일 진입점에서 test_admin 의 GET/HEAD/OPTIONS 외 요청 차단 → 새 API 에도 자동 적용",
           "테스트 계정 권한은 test_accounts.py 기준으로 서버 기동 시 복원, 권한 변경 API 로 변경 불가(400)",
           "프런트 Mock 모드도 같은 규칙 적용"])),
    ("4. 최종 검증 결과", table(["구분", "항목", "결과"], [
        ["자동 테스트", "pytest(권한 테스트 8개 추가)", "30개 통과"],
        ["프런트", "lint · build", "오류 0 · 성공"],
        ["화면 점검", "로컬 데모 인스턴스 Playwright 16항목", "통과(첫 접속 메인, 헤더/푸터, 해시 이동, Top 버튼, 읽기 전용 배너·버튼 비활성, 잘못된 토큰 거부, 운영 관리자 권한, 테스트 계정 토글 고정 등)"],
        ["Mock 빌드", "테스트 관리자 제한", "권한 토글·업로드 영역 비활성 확인"],
        ["반응형", "데스크톱(1440) · 모바일(390)", "정상"]])),
    ("5. 회고 (KPT)", table(["구분", "내용"], [
        ["Keep", "대체 경로 설계(텍스트 → OCR → Vision, Gemini → 규칙)로 외부 의존성 장애에도 서비스 유지<br/>화면과 서버 양쪽 검증, 고친 문제는 테스트로 재발 방지<br/>작업일마다 결정·검증·이슈를 docs/md 에 기록"],
        ["Problem", "실패 원인 대부분이 외부 의존성(기본 이미지 태그, LLM 가용성, 플랫폼 포트)이었음<br/>공개 테스트 계정의 권한 범위를 배포 후에야 점검함<br/>파싱 품질을 샘플 단위로만 확인함"],
        ["Try", "기본 이미지·의존성 버전 고정과 재시도 정책을 초기 설계에 포함<br/>공개 계정은 처음부터 최소 권한으로 설계<br/>정답셋 기반 필드 단위 정확도 측정"]])),
    ("6. 현재 한계", ul(["RPA 가 API 요청 안에서 동기로 실행 → 오래 걸리는 작업에 취약",
                       "업로드 원본이 컨테이너 디스크에 저장 → 재배포 시 원본 유실 가능(메타데이터·결과는 TiDB 에 유지)",
                       "스키마 변경을 create_all 로 처리(마이그레이션 도구 없음)",
                       "데모 ERP 대상 검증(실제 ERP 연동 전), 무료 플랜 유휴 슬립으로 첫 요청 지연"])),
    ("7. 향후 계획", table(["우선순위", "과제", "내용"], [
        ["1", "RPA 작업 큐 분리", "워커 프로세스 + 진행 상태 조회 (rpa 패키지가 분리되어 있어 이전 비용 낮음)"],
        ["2", "원본 스토리지 이전", "S3 등 오브젝트 스토리지"],
        ["3", "마이그레이션", "Alembic 도입"],
        ["4", "정확도 평가", "문서 유형별 정답셋, 필드 단위 정확도, 프롬프트·모델 비교"],
        ["5", "실제 ERP 연동", "ERP 커넥터(API 우선, 없으면 RPA), 조직(테넌트) 단위 권한"]])),
])

OUTPUTS = {"01_기획분석_산출물.hwpx": P1, "02_설계_산출물.hwpx": P2, "03_구현_산출물.hwpx": P3,
           "04_배포_산출물.hwpx": P4, "05_피드백_산출물.hwpx": P5}



# ============================================================================ 한글 자동화
def hwp_app():
    h = win32.Dispatch("HWPFrame.HwpObject")
    if not h.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule"):
        raise SystemExit("한글 보안 모듈 등록 실패 (HKCU\\Software\\HNC\\HwpAutomation\\Modules 확인)")
    h.XHwpWindows.Item(0).Visible = False
    return h


def main() -> None:
    OUT_PDF.mkdir(exist_ok=True)
    for name, rows in JOURNAL.items():
        fill_journal(DOCS / name, rows)
        print("filled", name)
    h = hwp_app()
    try:
        tmp = Path(tempfile.mkdtemp())
        for name, html_doc in OUTPUTS.items():
            src = tmp / (Path(name).stem + ".html")
            src.write_text(html_doc, encoding="utf-8")
            assert h.Open(str(src), "HTML", "forceopen:true;code:utf8")
            assert h.SaveAs(str(DOCS / "산출물" / name), "HWPX", "")
            assert h.SaveAs(str(OUT_PDF / (Path(name).stem + ".pdf")), "PDF", "")
            print("output", name, "pages", h.PageCount)
            h.Clear(1)
        for name in JOURNAL:
            assert h.Open(str(DOCS / name), "HWPX", "forceopen:true")
            assert h.SaveAs(str(DOCS / name), "HWPX", "")  # 한글로 다시 저장해 줄 배치 정보 갱신
            assert h.SaveAs(str(OUT_PDF / (Path(name).stem + ".pdf")), "PDF", "")
            print("journal", name, "pages", h.PageCount)
            h.Clear(1)
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        h.Quit()


if __name__ == "__main__":
    main()
