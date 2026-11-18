"""프로젝트 진행일지 5종 + 산출물 5종 작성 → 한글(HWP COM)로 HWPX 저장 · PDF 변환 · 검수

    python docs/tools/build_docs.py            # 작성 + 저장 + PDF + 검수
    python docs/tools/build_docs.py --verify   # 검수만

- 실행: pywin32 · PyMuPDF 가 설치된 시스템 Python 3.11 (한글 2020 이상 필요)
- 진행일지: docs/tools/templates/ 의 원본 빈 양식에서 출발해 빈 셀만 채움 → 기간 · 조 · 보고자 등 메타데이터와 표 양식은 원본 그대로
- 산출물: hwpx_writer 로 표준 디자인(맑은 고딕, 짙은 녹색 표 제목 행, 셀 여백, 표-제목 간격)을 적용해 직접 생성
- PDF: docs/pdf/ 에 원본과 같은 파일 이름으로 저장
- 근거: 저장소 코드 · 설정 파일 · pytest 결과 · docs/md 작업 기록 (확인되지 않은 수치 · 결과는 쓰지 않음)
"""

from __future__ import annotations

import html
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwpx_writer import Document  # noqa: E402

DOCS = Path(__file__).resolve().parents[1]
TEMPLATES = DOCS / "tools" / "templates"
OUT_DIR = DOCS / "산출물"
PDF_DIR = DOCS / "pdf"

TEAM = "홍기흥"
TOPIC = "DataQuill — 생성형 AI × RPA 기반 데이터 입력 자동화 플랫폼"
COURSE = "[K-Digital] 심화_생성형 AI와 AWS 클라우드를 활용한 풀스택 & 자동화 실무 개발 Final-Project"
REPO = "https://github.com/fsclass-n/dataquill"
SERVICE = "https://dataquill.onrender.com (API 문서: https://dataquill-api.onrender.com/docs)"
PORTFOLIO = "https://fsclass-n.github.io/dataquill/"

# ============================================================================ 1. 진행일지 (행 번호 → 줄 목록)
# 행: 1 주제 · 2 팀원 · 3 수행과제 · 4 도달목표 · 5 지시사항 · 6 수행사항 · 7 미수행사항 · 8 수행결과
#     9 마감회의 · 10 문제점 · 11 미해결 사항 및 과제 · 12 차기 주제   (0 기간 · 13 보고자 는 원본 유지)
# 상태 표기: [완료] [이월] [보류] [향후 과제] [해결: n단계] [미해결]
COMMON = {1: [TOPIC], 2: [TEAM]}
JOURNAL = {
    "프로젝트_진행일지_1단계_기획분석.hwpx": {
        3: ["주제 선정 및 문제 정의, 요구사항(기능 11 · 비기능 6) 도출, 입력 문서 · 출력 대상 조사, 추출 필드 정의, 기술 스택 선정, 작업 기록 방식 결정"],
        4: ["- 핵심 가치 확정: 비정형 문서(영수증 · 세금계산서 · 거래 이메일)를 AI가 정형화하고 RPA가 ERP · 엑셀에 대신 입력",
            "- MVP 범위(입력 6종, 추출 필드 9종, 출력 2종, 권한) 확정 및 저장소 · 개발 환경 준비"],
        5: ["- 생성형 AI(LLM)와 RPA 자동화를 핵심 기술로 포함하고 클라우드 배포까지 수행",
            "- 반응형 UI, 소셜 로그인(OAuth), 관리자 페이지, 테스트 계정 요구사항 반영",
            "- 단계별 진행일지 · 산출물 작성"],
        6: ["[완료] 문제 정의: 같은 문서를 ERP에 한 번, 엑셀 원장에 또 한 번 수기 입력 / 문서 형식이 제각각이라 정규식만으로는 한계 / 사내 ERP는 연동 API가 없는 경우가 많음",
            "[완료] 해결 방향: 형식 문제는 생성형 AI 구조화 출력, API가 없는 문제는 화면에 입력하는 RPA, AI 오류에 대비해 사람 검수 단계를 둠",
            "[완료] 입력 형식(PDF · 이미지 · EML · HTML · TXT · 본문 붙여넣기)과 추출 필드(거래처 · 사업자번호 · 거래일자 · 합계 · 부가세 · 결제수단 · 품목 · 적요 · 신뢰도) 정의",
            "[완료] 기술 스택 선정: FastAPI · SQLAlchemy · Gemini · Playwright · pandas · React · Tailwind · TiDB · Render",
            "[완료] 저장소 origin 을 fsclass-n/dataquill 로 변경, 작업 내용을 docs/md 에 날짜별로 누적 기록하기로 결정"],
        7: ["[보류] 실제 ERP 연동 대상 선정 — 범위 외로 두고 데모 ERP 화면(/erp-demo)으로 검증하기로 결정",
            "[향후 과제] 파싱 정확도 정량 평가셋 구축"],
        8: ["[완료] 요구사항 정의(FR-01~11, NFR-01~06), 추출 필드 정의, 기술 스택 선정, 일정 · 위험 요소 정리(산출물 01)",
            "[완료] 결정 사항: 소셜 로그인은 실제 OAuth 연동(Google · Naver · Kakao)으로 구현"],
        9: ["- AI 결과를 그대로 입력하지 않고 '추출 → 사람 검수 → 입력' 순서로 처리한다는 원칙 합의",
            "- 외부 의존성(LLM 키 · OCR 엔진)이 없어도 서비스가 멈추지 않도록 대체 경로를 기본 설계에 포함"],
        10: ["- 스캔 PDF · 사진은 텍스트 레이어가 없어 일반 추출이 불가능",
             "- LLM 이 문서에 없는 값을 지어낼(환각) 위험 — 회계 데이터에서는 치명적",
             "- 연동 API 가 없는 ERP 는 화면 구조에 의존해야 하므로 변경에 취약"],
        11: ["[해결: 2단계] 추출 단계별 대체 순서(텍스트 → OCR → 멀티모달) 설계",
             "[해결: 2단계] LLM 출력 형식을 강제하는 방법과 RPA 성공 판정 기준 설계"],
        12: ["설계 단계 — 시스템 아키텍처, 데이터 모델 · API, 문서 처리 파이프라인, 권한 · 보안, 화면, 배포 구조 설계"],
    },
    "프로젝트_진행일지_2단계_설계.hwpx": {
        3: ["시스템 아키텍처, 데이터 모델(ERD) · API 명세, 문서 처리 파이프라인, AI 스키마 · 프롬프트, RPA 설계, 권한 · 보안, 화면, 배포 구조 설계"],
        4: ["- 프런트엔드 · 백엔드 분리 배포와 웹 계층(backend.app) · 자동화 계층(rpa) 분리 구조 확정",
            "- API 검증과 LLM 출력에 같은 Pydantic 스키마를 쓰는 설계 확정"],
        5: ["- 설계 근거와 트레이드오프를 함께 기록",
            "- 비밀 값은 .env 하나로 관리하고 저장소에 포함하지 않음"],
        6: ["[완료] 아키텍처: React SPA(정적 호스팅) ↔ FastAPI(Docker) ↔ TiDB Cloud, 외부 연동 Gemini API · OAuth 제공자",
            "[완료] 데이터 모델: users(역할 · OAuth 식별자) 1:N documents(원문 · 추출 결과 JSON · 상태 · 파서) 1:N rpa_jobs(대상 · 결과 · 메시지)",
            "[완료] 파이프라인: 업로드 → extract(텍스트 레이어 → Tesseract OCR → Gemini 멀티모달) → parser(Gemini 구조화 출력, 키 없으면 규칙 파서) → 검수(PATCH) → 엑셀 upsert / ERP 타이핑",
            "[완료] AI: ParsedDocument(Pydantic) 를 응답 스키마로 전달, temperature 0, '문서에 없는 값은 null' 규칙",
            "[완료] RPA: 셀렉터 맵으로 화면 구조와 코드 분리, ERP 결과 요소의 상태값 · 전표번호로 성공 판정, 엑셀은 문서 ID 기준 교체",
            "[완료] 배포: Render(백엔드 Docker · 프런트 Static Site), 변경 영역만 검증 · 배포(paths-filter · Build Filter), 백엔드 없이도 동작하는 Mock 모드"],
        7: ["[보류] RPA 작업 큐(별도 워커) 분리 — 범위 외, rpa 패키지를 분리해 이전 비용을 낮춤",
            "[향후 과제] DB 마이그레이션 도구(Alembic) — create_all 로 시작"],
        8: ["[완료] 아키텍처 · 데이터 흐름, 테이블 명세, API 명세 · 오류 코드, 처리 흐름(파이프라인 · AI · RPA · OAuth), 화면, 권한, 외부 연동, 배포 설계(산출물 02)"],
        9: ["- 로컬 · 테스트는 SQLite, 운영은 TiDB 로 URL 만 바꿔 같은 코드를 실행하기로 결정",
            "- 헬스 체크 응답에 현재 파서 종류(gemini/rules)를 노출해 설정 상태를 확인할 수 있게 함"],
        10: ["- RPA 가 API 요청 안에서 동기로 실행되어 오래 걸리는 작업에 취약",
             "- 업로드 원본을 컨테이너 디스크에 두면 재배포 시 유실 가능"],
        11: ["[미해결 · 향후 과제] RPA 비동기 작업 큐, 원본 파일 오브젝트 스토리지 이전",
             "[해결: 3단계] 실제 ERP 셀렉터 확보 전까지 데모 ERP 화면으로 RPA 검증"],
        12: ["구현 단계 — 백엔드 API · 인증 · OAuth, 추출 · AI 파서, RPA(엑셀 · ERP), 프런트엔드 화면, 자동 테스트"],
    },
    "프로젝트_진행일지_3단계_구현.hwpx": {
        3: ["백엔드(FastAPI) API · 인증 · OAuth, 텍스트 추출 · AI 파서, RPA(엑셀 적재 · ERP 자동 타이핑), 프런트엔드(React) 화면, 관리자 기능, 자동 테스트"],
        4: ["- 업로드 → 추출 → AI 정형화 → 검수 → 엑셀 적재 · ERP 타이핑 전 과정 동작",
            "- 회원 / 관리자 권한 분리, 테스트 계정 원클릭 로그인, pytest 로 핵심 규칙 회귀 방지"],
        5: ["- 설계서의 API · 데이터 정책을 그대로 구현하고 변경 시 문서 갱신",
            "- 비밀번호 규칙(영문 대 · 소문자 + 숫자 + 특수문자 8자 이상)은 화면과 서버 양쪽에서 검증"],
        6: ["[완료] 백엔드: SQLAlchemy 2.0(SQLite/TiDB), JWT(HS256) · PBKDF2-SHA256 해시, OAuth 3사(state 쿠키 CSRF 검증), 문서 업로드(10MB) · 본문 입력 · 검수 · 재해석 · 삭제, 관리자 회원 · 통계 API",
            "[완료] 추출 · AI: pypdf · Tesseract(kor+eng) · EML/HTML 파싱, Gemini 구조화 출력(멀티모달 포함), 규칙 기반 파서(찾은 필드 수로 신뢰도 산출)",
            "[완료] RPA: 엑셀 원장 upsert(pandas + openpyxl), Playwright ERP 타이핑 + 데모 ERP 화면(/erp-demo, 전표번호 발급), CLI 단독 실행",
            "[완료] 프런트엔드: React 19 · Vite · Tailwind v4, Split 로그인 · OAuth 버튼 · 비밀번호 실시간 체크, 모바일 햄버거↔X 드로어, 대시보드 · 문서 처리 · 관리자(회원 · 모니터링), 코드 스플리팅, Mock 모드"],
        7: ["[이월: 4단계] Gemini API 키 · OAuth 앱 등록 후 실연동 테스트",
            "[이월: 4단계] TiDB 클러스터 연결 테스트"],
        8: ["[완료] pytest 19개 통과, 프런트 lint 오류 0 · build 성공",
            "[완료] 실서버 E2E: 로그인 → 영수증 업로드 → 규칙 파싱 → Playwright 가 데모 ERP 에 입력(전표번호 발급) → 엑셀 적재 확인",
            "[완료] 구현 산출물(개발 환경 · 디렉터리 · 모듈 · 기능별 구현 · 테스트 · 트러블슈팅) 작성(산출물 03)"],
        9: ["- 데스크톱(1440) · 모바일(390) 화면을 Playwright 스크린샷으로 점검, 콘솔 오류 없음",
            "- Mock 모드 빌드로 로그인 · 권한 변경 동작 확인"],
        10: ["- .env 에서 빈 값 뒤 인라인 주석이 값으로 읽혀 키가 없는데도 Gemini · OAuth 가 '설정됨'으로 동작 → 주석을 별도 줄로 분리",
             "- Tailwind v4 에서 @layer components 클래스는 @apply 불가 → @utility 로 정의",
             "- 헤더 backdrop-filter 가 fixed 드로어의 기준 박스가 되는 문제 → 드로어를 헤더 밖으로 분리"],
        11: ["[해결: 4단계] Gemini 실제 영수증 파싱 품질 확인",
             "[해결: 4단계] OAuth Redirect URI 등록, TiDB 연결, Render 배포"],
        12: ["배포 단계 — Docker 이미지, Render(API · 프런트) · Netlify 배포, TiDB 연결, CI/CD, 운영 점검"],
    },
    "프로젝트_진행일지_4단계_배포.hwpx": {
        3: ["Docker 이미지 빌드, Render(백엔드 Web Service · 프런트 Static Site) · Netlify 배포, TiDB Cloud 연결, GitHub Actions CI/CD, 운영 점검"],
        4: ["- 운영 서비스 dataquill.onrender.com · API dataquill-api.onrender.com 정상 동작",
            "- main 푸시 시 변경 영역만 검증 · 배포"],
        5: ["- 비밀 값은 Render 대시보드에만 등록, .env.example 에 [LOCAL]/[RENDER]/[RENDER-FE] 등록 위치 표기",
            "- 운영 DB 는 직접 건드리지 않고 임시 DB 로 검증"],
        6: ["[완료] backend/Dockerfile(python:3.11-slim-bookworm + Tesseract 한국어 + Chromium), frontend/Dockerfile(nginx), docker-compose.yml",
            "[완료] render.yaml(Build Filter: backend/** · rpa/** · requirements.txt / frontend/**), netlify.toml, deploy.yml(paths-filter 로 변경 영역 테스트 · 빌드)",
            "[완료] TiDB Cloud Serverless 연결(DB_SSL=true + certifi CA), OAuth Redirect URI 등록, Gemini API 키 등록",
            "[완료] 운영 점검: 헬스 체크 · 로그인 · CORS · OAuth Redirect · Gemini 파싱 · 엑셀 적재 · SPA 딥링크"],
        7: ["[보류] 업로드 원본 오브젝트 스토리지 이전 — 고도화 단계",
            "[보류] RPA 작업 큐 분리 — 고도화 단계"],
        8: ["[완료] 운영 Gemini 파싱 샘플: 영수증에서 거래처 · 사업자번호 · 금액 · 부가세 · 품목 정상 추출(신뢰도 0.98)",
            "[완료] Gemini 재시도 테스트 3개 추가, pytest 22개 통과",
            "[완료] 배포 구성 · 환경 변수 · CI/CD · 실행 방법 · 테스트 결과 · 운영 점검 작성(산출물 04)"],
        9: ["- 운영에서만 발생한 문제는 근거(로그 · 소스 · 헬스 체크)로 원인을 확정하고, 고친 뒤 같은 상황을 재현하는 테스트를 추가하기로 합의"],
        10: ["- 코드 변경 없이 Docker 빌드 실패: slim 태그가 Debian 13 으로 바뀌어 Playwright 1.52 의존성 설치 실패 → slim-bookworm 고정",
             "- TiDB '1105 insecure transport prohibited' → TLS 설정",
             "- Gemini 503(high demand) → 429/5xx 만 2s · 5s · 10s 백오프 재시도",
             "- 운영 ERP 타이핑 연결 거부: Render PORT=10000 → 기본 주소 127.0.0.1:$PORT",
             "- /login 새로고침 404 → SPA Rewrite(/* → /index.html)"],
        11: ["[해결: 5단계] 공개 테스트 계정의 권한 범위 점검",
             "[미해결] 무료 플랜 유휴 슬립으로 첫 요청 지연(약 1분) — 시연 전 헬스 체크로 서버를 깨워 운영"],
        12: ["피드백 단계 — 점검 결과 반영(UI 표준화, 권한 모델 개편), 발표자료 · 발표 영상 · 문서 정리"],
    },
    "프로젝트_진행일지_5단계_피드백.hwpx": {
        3: ["플랫폼 표준 가이드 점검 결과 반영(전역 레이아웃 · 도메인 맞춤 메인 · 상용 푸터), 권한 모델 개편, 발표자료 · 발표 영상 · 포트폴리오 제작, 문서 정리"],
        4: ["- 공개 테스트 관리자 계정의 보안 문제 해소(읽기 전용 전환)",
            "- 모든 페이지 공통 레이아웃과 디자인 토큰 표준화, 발표자료 · 10분 발표 영상 · README · 진행일지 · 산출물 완성"],
        5: ["- 실제로 구현 · 검증되지 않은 수치(정확도, 고객사 로고 등)와 가짜 사업자 정보는 화면 · 문서에 넣지 않음",
            "- 권한은 화면이 아닌 서버에서 강제"],
        6: ["[완료] 전역 레이아웃 SiteLayout(헤더 · 푸터 · 원형 Top), 첫 접속 메인, 상태별 헤더 메뉴, 읽기 전용 배너",
            "[완료] 도메인 맞춤 메인 페이지, 디자인 토큰 표준화, 이용약관 · 개인정보처리방침 신설",
            "[완료] 권한 모델: 운영 관리자는 ADMIN_TOKEN 로그인(5회 실패 시 10분 차단), test_admin 은 쓰기 요청 403, 테스트 계정 권한은 기동 시 복원 · 변경 불가",
            "[완료] 발표자료(16장 + 부록, 발표자 노트) · 10분 발표 · 시연 영상(자막 포함) · 60초 하이라이트 제작, GitHub Pages 포트폴리오 공개",
            "[완료] README 재작성, 진행일지 · 산출물 표준 디자인으로 재작성 및 PDF 변환"],
        7: ["[완료] 발표자료 화면 캡처를 운영 서비스에서 재촬영해 개편 후 기준으로 갱신",
            "[향후 과제] RPA 작업 큐 분리 · 원본 스토리지 이전 · 정량 정확도 평가"],
        8: ["[완료] 권한 테스트 8개 추가, pytest 30개 통과, 프런트 lint 오류 0 · build 성공",
            "[완료] 화면 점검 16항목 · 포트폴리오 페이지 22항목(제자리 영상 재생 · 모바일) 통과",
            "[완료] 피드백 반영 내역 · 요구사항 충족 여부 · 운영 방법 · 회고 · 향후 계획 작성(산출물 05)"],
        9: ["- 회고: 대체 경로 설계(텍스트 → OCR → Vision, Gemini → 규칙)와 화면 · 서버 양쪽 검증이 안정성에 효과적",
            "- 실패 원인 대부분이 외부 의존성 → 처음부터 버전 고정 · 재시도 설계 필요"],
        10: ["- 공개된 테스트 관리자 계정이 실제 관리자 권한을 가져 누구나 회원 권한 변경 가능(개편으로 해소)",
             "- 새로고침 후 문서 시각이 9시간 이르게 표시(시간대 정보 누락) — 미수정"],
        11: ["[미해결] 문서 목록 · 상세의 시각 표시 오류(응답 직렬화 시 UTC 시간대 부여 예정)",
             "[미해결] 운영 서버 ADMIN_TOKEN 미등록 → 운영 관리자 로그인 비활성",
             "[향후 과제] RPA 작업 큐, 원본 스토리지 이전, Alembic, 정답셋 기반 정확도 측정, 실제 ERP 커넥터"],
        12: ["고도화 — RPA 비동기 작업 큐, 원본 스토리지 이전, 정량 정확도 평가, 실제 ERP · 조직 단위 권한"],
    },
}


JOURNAL_CONTENT_PARA = "2"   # 원본 양식에서 내용 셀(왼쪽 정렬)이 쓰는 문단 모양


def _para_xml(text: str, para_pr: str, char_pr: str) -> str:
    return (f'<hp:p id="0" paraPrIDRef="{para_pr}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{char_pr}"><hp:t>{html.escape(text, quote=False)}</hp:t></hp:run></hp:p>')


def fill_journal(template: Path, out: Path, rows: dict) -> None:
    """원본 빈 양식의 빈 셀에만, 그 셀의 문단 · 글자 모양 그대로 내용을 넣는다."""
    rows = {**COMMON, **rows}
    with zipfile.ZipFile(template) as z:
        items = {n: z.read(n) for n in z.namelist()}
        infos = {i.filename: i for i in z.infolist()}
    xml = items["Contents/section0.xml"].decode("utf-8")

    def repl(m):
        tc = m.group(0)
        col, row = map(int, re.search(r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"', tc).groups())
        target = (row in (1, 2) and col == 2) or (3 <= row <= 12 and col == 1)
        if not target or row not in rows or re.search(r"<hp:t>[^<]+</hp:t>", tc):
            return tc
        p = re.search(r'<hp:p id="0" paraPrIDRef="(\d+)"[^>]*><hp:run charPrIDRef="(\d+)"', tc)
        body = "".join(_para_xml(t, p.group(1), p.group(2)) for t in rows[row])
        return re.sub(r"(<hp:subList[^>]*>).*?(</hp:subList>)", lambda s: s.group(1) + body + s.group(2), tc, count=1, flags=re.S)

    xml = re.sub(r"<hp:tc .*?</hp:tc>", repl, xml, flags=re.S)
    # 표준 스타일: 셀 내부 여백 상하 2mm · 좌우 2.5mm (표 틀 · 행 · 열은 그대로)
    xml = re.sub(r'<hp:(cellMargin|inMargin) left="\d+" right="\d+" top="\d+" bottom="\d+"/>',
                 lambda m: f'<hp:{m.group(1)} left="709" right="709" top="567" bottom="567"/>', xml)
    xml = xml.replace('hasMargin="0"', 'hasMargin="1"')
    items["Contents/section0.xml"] = xml.encode("utf-8")
    # 표준 스타일: 셀 본문 문단(왼쪽 정렬) 줄 간격 130%(원본 양식 값) · 항목 아래 1pt → 1쪽 양식 유지
    header = items["Contents/header.xml"].decode("utf-8")
    content_pp = re.search(r'<hp:cellAddr colAddr="1" rowAddr="6"', xml) and JOURNAL_CONTENT_PARA
    def tune(m):
        pp = m.group(0)
        if f'id="{content_pp}"' not in pp:
            return pp
        pp = re.sub(r'<hh:lineSpacing type="PERCENT" value="\d+"', '<hh:lineSpacing type="PERCENT" value="130"', pp)
        return re.sub(r'<hc:next value="\d+"', '<hc:next value="100"', pp)
    items["Contents/header.xml"] = re.sub(r"<hh:paraPr id=.*?</hh:paraPr>", tune, header, flags=re.S).encode("utf-8")
    with zipfile.ZipFile(out, "w") as z:
        for name, data in items.items():
            z.writestr(infos[name], data, compress_type=zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED)


# ============================================================================ 2. 산출물
BREAKS: dict[str, set] = {}   # 산출물별로 쪽 나눔이 필요한 제목 (2차 배치 검사 결과)


def new_doc(no: str, title: str, stage: str, period: str) -> Document:
    d = Document(f"DataQuill  ·  {no}. {title}", frozenset(BREAKS.get(no, ())))
    d.title(f"{no}. {title}", TOPIC)
    d.meta([["프로젝트", TOPIC], ["과정", COURSE], ["단계", stage], ["기간", period],
            ["작성", f"3조 · {TEAM}"], ["서비스", SERVICE], ["저장소", REPO]])
    return d


def output_01() -> Document:
    d = new_doc("01", "기획·분석 산출물", "1단계 기획·분석", "2026년 11월 23일(월) ~ 11월 24일(화)")
    d.h1("1. 프로젝트 개요 및 추진 목적")
    d.p("DataQuill 은 영수증 · 세금계산서 · 거래 이메일 같은 비정형 문서를 생성형 AI(Google Gemini)가 읽어 정형 데이터로 바꾸고, "
        "사람이 검수한 값을 RPA(Playwright) 로봇이 웹 ERP 전표 화면과 엑셀 원장에 대신 입력하는 B2B 데이터 입력 자동화 플랫폼이다.")
    d.table(["구분", "내용"], [
        ["핵심 가치", "같은 문서를 ERP · 엑셀에 반복 입력하던 일을 'AI 추출 → 사람 검수 → 로봇 입력' 흐름으로 대체"],
        ["추진 목적", "생성형 AI(LLM) · RPA · 클라우드 배포를 한 서비스로 통합해 실무형 자동화 파이프라인을 1인 풀스택으로 구현"],
        ["대상 사용자", "경리 · 회계, 구매 · 총무, 영업지원 담당자 / 서비스 운영 관리자"],
        ["입력", "PDF, 이미지(JPG · PNG · WEBP · BMP · TIFF), EML, HTML, TXT 업로드(최대 10MB), 이메일 본문 붙여넣기"],
        ["출력", "엑셀 원장(xlsx) 적재, 웹 ERP 전표 자동 입력(전표번호 발급)"],
        ["결과물", "운영 서비스 · API 문서 · 소스 코드 · 발표자료 · 10분 발표 영상 · 포트폴리오 페이지"]], widths=[18, 82], label_col=True, zebra=False)

    d.h1("2. 배경 및 문제 정의")
    d.table(["문제", "현상", "해결 방향"], [
        ["이중 수기 입력", "같은 영수증 · 청구 메일을 ERP 에 한 번, 엑셀 원장에 또 한 번 입력", "한 번 추출한 결과를 엑셀 · ERP 에 자동 입력"],
        ["문서 형식의 다양성", "거래처마다 양식이 달라 정규식 규칙으로는 한계", "생성형 AI 구조화 출력으로 필드 추출"],
        ["스캔본 · 사진", "텍스트 레이어가 없어 일반 추출 불가", "OCR → LLM 멀티모달 순서로 대체"],
        ["API 없는 ERP", "사내 ERP 에 연동 API 가 없는 경우가 많음", "사람처럼 화면에 입력하는 RPA"],
        ["AI 오류(환각)", "문서에 없는 값을 그럴듯하게 생성할 위험", "'없는 값은 null' 규칙 + 사람 검수 단계"]], widths=[20, 42, 38], label_col=True)

    d.h1("3. 목표 및 핵심 기능")
    d.h2("3.1 프로젝트 목표")
    d.bullets(["6가지 입력 형식에서 회계 전표 필드를 JSON 으로 추출하고 신뢰도를 함께 제공",
               "AI 키 · OCR 엔진이 없어도 동작하는 대체 경로(규칙 기반 파서) 제공",
               "검수 후 엑셀 원장 적재(중복 없음)와 ERP 자동 입력(전표번호 확인)",
               "이메일 가입 · OAuth 3사 로그인, 운영 관리자 · 테스트 관리자 · 일반 사용자 권한 분리",
               "반응형 UI, 관리자 모니터링(파싱 · RPA 성공률), 클라우드 자동 배포"])
    d.h2("3.2 핵심 기능")
    d.table(["기능", "설명", "구현 위치"], [
        ["문서 수집", "파일 드래그&드롭 업로드, 거래 이메일 본문(텍스트 · HTML) 붙여넣기", "routers/documents.py"],
        ["텍스트 추출", "PDF 텍스트 레이어 → 이미지 OCR → 원본 멀티모달 순서의 단계적 추출", "rpa/extract.py"],
        ["AI 정형화", "Gemini 구조화 출력으로 전표 필드 추출, 키가 없으면 규칙 기반 파서", "services/parser.py"],
        ["사람 검수", "추출 결과 화면 수정 · 저장(서버 재검증), 재해석, 삭제", "pages/Documents.jsx"],
        ["엑셀 원장 적재", "문서 ID 기준 행 교체(중복 없음), 원장 다운로드", "rpa/excel_writer.py"],
        ["ERP 자동 타이핑", "Playwright 가 전표 화면에 입력하고 전표번호를 확인해야 성공 기록", "rpa/erp_typer.py"],
        ["대시보드 · 모니터링", "KPI, 최근 14일 처리 추이, 파싱 · RPA 성공률, 최근 실패", "services/stats.py"],
        ["회원 · 권한", "이메일 · OAuth 로그인, 테스트 계정, 운영/테스트 관리자 권한 분리", "routers/auth.py · deps.py"]], widths=[18, 54, 28], label_col=True)

    d.h1("4. 대상 사용자 및 사용자 요구사항")
    d.table(["사용자", "주요 업무", "요구사항", "반영 기능"], [
        ["경리 · 회계 담당자", "법인카드 영수증 · 세금계산서로 매입 전표 입력", "스캔본도 읽을 것, 틀린 값은 바로 고칠 것", "단계적 추출, 검수 화면, ERP 타이핑"],
        ["구매 · 총무 담당자", "거래처 청구 메일을 월별 원장에 기록", "메일 본문을 그대로 붙여 넣어 처리", "이메일 본문 입력, 엑셀 원장"],
        ["영업지원 담당자", "거래명세서 · 주문 확인 메일 입력", "ERP 와 엑셀에 같은 값을 한 번에", "엑셀 적재 + ERP 입력, 작업 이력"],
        ["운영 관리자", "회원 · 권한 관리, 처리 품질 점검", "성공률 · 실패 원인을 한눈에, 권한 오남용 방지", "모니터링, 회원 관리, 서버 권한 검사"],
        ["체험 사용자(면접관)", "가입 없이 기능 확인", "버튼 한 번으로 로그인, 데이터 변경 없이 관리자 화면 열람", "테스트 계정, 읽기 전용 테스트 관리자"]], widths=[19, 27, 30, 24], label_col=True)

    d.h1("5. 추출 필드 정의")
    d.table(["필드", "설명", "형식"], [
        ["document_type", "문서 유형", "receipt / invoice / email / other"], ["vendor", "거래처(상호명)", "문자열"],
        ["business_number", "사업자등록번호", "000-00-00000"], ["date", "거래일자", "YYYY-MM-DD"],
        ["total_amount · vat", "합계 금액 · 부가세", "원 단위 정수"], ["payment_method", "결제수단", "신용카드 · 현금 · 계좌이체 등"],
        ["items", "품목 목록", "품명 · 수량 · 단가 · 금액"], ["summary", "한 줄 적요", "문자열"], ["confidence", "추출 신뢰도", "0 ~ 1"]],
        widths=[26, 34, 40], align=["L", "L", "C"], label_col=True)

    d.h1("6. 기능 요구사항")
    d.table(["ID", "구분", "요구사항", "우선순위", "상태"], [
        ["FR-01", "회원", "이메일 가입 · 로그인(JWT), 비밀번호 규칙(영문 대 · 소문자 + 숫자 + 특수문자 8자 이상) 화면 · 서버 검증", "상", "완료"],
        ["FR-02", "회원", "Google · Naver · Kakao OAuth 로그인, 이메일 중복 가입 차단", "중", "완료"],
        ["FR-03", "회원", "일반 사용자 · 테스트 관리자 원클릭 로그인", "상", "완료"],
        ["FR-04", "문서", "파일 업로드(10MB) · 이메일 본문 입력, 지원하지 않는 형식 거부", "상", "완료"],
        ["FR-05", "AI", "Gemini 구조화 추출(이미지 · 스캔본 멀티모달), 키가 없으면 규칙 기반 파서", "상", "완료"],
        ["FR-06", "검수", "추출 결과 화면 수정 · 저장(서버 재검증), 재해석, 삭제", "상", "완료"],
        ["FR-07", "RPA", "엑셀 원장 적재(문서 ID 기준 교체) · 다운로드", "상", "완료"],
        ["FR-08", "RPA", "웹 ERP 전표 자동 입력, 전표번호 확인 후 성공 기록, 작업 이력", "상", "완료"],
        ["FR-09", "대시보드", "사용자 KPI, 최근 14일 처리 추이, 입력 소스 분포, 최근 문서", "중", "완료"],
        ["FR-10", "관리자", "회원 목록 · 검색 · 권한 변경, 파싱 · RPA 성공률 모니터링, 최근 실패", "상", "완료"],
        ["FR-11", "공통", "반응형 GNB(햄버거↔X, 우측 드로어), To the Top 버튼, 토스트 알림", "중", "완료"],
        ["FR-12", "권한", "운영 관리자(ADMIN_TOKEN) · 테스트 관리자(읽기 전용) · 일반 사용자 분리(5단계 추가)", "상", "완료"]],
        widths=[9, 10, 61, 10, 10], align=["C", "C", "L", "C", "C"])
    d.caption("※ 상태는 최종 점검(5단계) 기준이며, 근거는 산출물 05 의 '요구사항 충족 여부' 에 정리하였다.")

    d.h1("7. 비기능 요구사항")
    d.table(["ID", "항목", "요구사항", "상태"], [
        ["NFR-01", "신뢰성", "LLM 응답은 스키마로 강제하고 문서에 없는 값은 null, 사람 검수 후 입력", "완료"],
        ["NFR-02", "가용성", "LLM 키 없음 · 일시 장애 · OCR 미설치 시에도 대체 경로로 서비스 지속", "완료"],
        ["NFR-03", "정합성", "엑셀 재적재 시 중복 행 없음, RPA 는 결과 확인 후에만 성공 처리", "완료"],
        ["NFR-04", "보안", "JWT 인증, PBKDF2 해시, OAuth state 검증, CORS 제한, 비밀 값 .env 관리, 권한은 서버에서 강제", "완료"],
        ["NFR-05", "배포", "프런트 · 백엔드 독립 배포, 변경 영역만 검증 · 배포", "완료"],
        ["NFR-06", "투명성", "검증되지 않은 수치 · 가짜 사업자 정보는 화면 · 문서에 넣지 않음", "완료"]],
        widths=[10, 12, 66, 12], align=["C", "C", "L", "C"])

    d.h1("8. 서비스 운영 및 활용 시나리오")
    d.table(["시나리오", "사용자", "처리 절차", "결과"], [
        ["S1. 법인카드 영수증", "경리 · 회계", "스캔 영수증 PDF 업로드 → Gemini 멀티모달 해석 → 적요 수정 · 검수 저장 → ERP 자동 타이핑", "ERP 매입 전표(전표번호 발급)"],
        ["S2. 청구 메일", "구매 · 총무", "이메일 본문 붙여넣기 → AI 해석 → 검수 → 엑셀 원장 적재", "월별 엑셀 원장(중복 없음)"],
        ["S3. 처리 품질 점검", "운영 관리자", "모니터링에서 파싱 · RPA 성공률과 최근 실패 확인 → 문서 재해석", "실패 원인 파악 · 재처리"],
        ["S4. 권한 관리", "운영 관리자", "ADMIN_TOKEN 으로 로그인 → 회원 검색 → 권한 변경", "운영 관리자 지정 · 해제"],
        ["S5. 기능 체험", "면접관", "테스트 관리자 버튼 로그인 → 관리자 화면 열람(쓰기 요청은 서버 403)", "데이터 변경 없는 체험"]],
        widths=[19, 13, 46, 22], label_col=True)

    d.h1("9. 프로젝트 범위 및 제외 범위")
    d.table(["구분", "항목", "비고"], [
        ["포함", "6종 입력 · 단계적 추출 · AI 정형화 · 규칙 파서", "Gemini 키가 없어도 동작"],
        ["포함", "검수 화면 · 엑셀 원장 · 데모 ERP 자동 타이핑", "데모 ERP(/erp-demo)로 RPA 전 과정 검증"],
        ["포함", "회원 · OAuth 3사 · 3단계 권한 · 관리자 모니터링", "권한은 서버에서 강제"],
        ["포함", "Render 배포 · CI/CD · 발표자료 · 발표 영상 · 문서", "변경 영역만 배포"],
        ["제외", "실제 사내 ERP 연동", "셀렉터 맵만 교체하면 적용 가능하도록 설계"],
        ["제외", "파싱 정확도 정량 평가셋", "샘플 단위 검증까지 수행, 향후 과제"],
        ["제외", "RPA 비동기 작업 큐 · 원본 오브젝트 스토리지", "고도화 단계 과제"],
        ["제외", "다중 조직(테넌트) · 결제 · 요금제", "범위 외"]], widths=[10, 52, 38], align=["C", "L", "L"])

    d.h1("10. 기술 스택 선정")
    d.table(["영역", "선택", "근거"], [
        ["Backend", "Python 3.11 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · PyJWT", "Pydantic 으로 요청 검증 · 응답 모델 · LLM 스키마 공유, /docs 자동 생성"],
        ["AI", "Google Gemini(google-genai)", "구조화 출력(response_schema), 이미지 · PDF 멀티모달"],
        ["RPA · 데이터", "Playwright · pandas · openpyxl · pypdf · pytesseract · BeautifulSoup4", "API 없는 ERP 화면 입력, 엑셀 원장, PDF · OCR · HTML 추출"],
        ["Frontend", "React 19 · Vite · Tailwind CSS v4 · React Router · Recharts · FontAwesome", "컴포넌트화, 디자인 토큰, 차트"],
        ["DB", "TiDB Cloud Serverless(MySQL 호환) / SQLite", "운영은 관리형 DB, 로컬 · 테스트는 URL 만 바꿔 같은 코드"],
        ["Infra", "Docker · Render · Netlify · GitHub Actions", "Chromium · Tesseract 포함 이미지, 조건부 배포"]], widths=[14, 43, 43], label_col=True)

    d.h1("11. 개발 일정 및 단계별 계획")
    d.table(["단계", "기간", "주요 산출물", "상태"], [
        ["1단계 기획 · 분석", "11/23 ~ 11/24", "요구사항 정의, 추출 필드 정의, 기술 스택 선정", "완료"],
        ["2단계 설계", "11/25 ~ 11/27", "아키텍처 · 테이블 · API · 처리 흐름 · 권한 · 화면 설계", "완료"],
        ["3단계 구현", "11/30 ~ 12/09", "백엔드 · RPA · AI 파서 · 프런트엔드, 테스트", "완료"],
        ["4단계 배포", "12/10 ~ 12/17", "Render · Netlify 배포, CI/CD, 테스트 · 운영 점검", "완료"],
        ["5단계 피드백", "12/18 ~ 12/21", "UI · 권한 개편, 발표자료 · 영상, 회고 · 향후 계획", "완료"]],
        widths=[20, 16, 52, 12], align=["L", "C", "L", "C"], label_col=True)

    d.h1("12. 위험 요소 및 대응")
    d.table(["위험", "영향", "대응"], [
        ["LLM 환각 · 형식 오류", "잘못된 회계 데이터 입력", "스키마 강제, temperature 0, null 규칙, 사람 검수"],
        ["LLM 일시 장애 · 키 없음", "파싱 실패", "일시 오류만 재시도, 규칙 기반 파서 대체"],
        ["ERP 화면 변경", "RPA 실패", "셀렉터 맵 분리, 결과 확인 후 성공 처리, 실패 사유 기록"],
        ["공개 테스트 계정 악용", "데이터 · 권한 변조", "서버 측 권한 강제(5단계에서 읽기 전용으로 강화)"]], widths=[26, 24, 50], label_col=True)
    return d


def output_02() -> Document:
    d = new_doc("02", "설계 산출물", "2단계 설계", "2026년 11월 25일(수) ~ 11월 27일(금)")
    d.h1("1. 전체 시스템 아키텍처")
    d.p("React SPA(Render Static Site) 가 FastAPI 백엔드(Render Web Service, Docker)를 REST 로 호출하고, 백엔드는 TiDB Cloud Serverless 에 데이터를 저장하며 "
        "Google Gemini API 와 OAuth 제공자(Google · Naver · Kakao)에 연동한다. RPA 코드는 웹 계층과 분리된 rpa 패키지로 두었다.")
    d.code("""
Browser   --HTTPS / Bearer JWT-->  Frontend  React SPA        (Render Static Site)
Frontend  --REST / CORS-------->  Backend   FastAPI          (Render Web Service, Docker)
                                  ├─ routers  : auth · documents · admin · erp_demo
                                  ├─ services : parser (Gemini / rules) · oauth · stats
                                  └─ rpa      : extract (OCR) · excel_writer · erp_typer (Playwright)
Backend   --SQL / TLS---------->  TiDB Cloud Serverless      (MySQL compatible)
Backend   --HTTPS-------------->  Google Gemini API          (structured output · multimodal)
Backend   --OAuth 2.0---------->  Google · Naver · Kakao     (Authorization Code + state)""", "그림 1. 시스템 구성도")
    d.table(["구성 요소", "역할", "설계 근거"], [
        ["frontend", "메인 · 로그인 · 대시보드 · 문서 처리 · 관리자 · 정책 화면", "정적 배포로 백엔드와 배포 주기 · 장애 범위 분리"],
        ["backend.app", "routers(auth · documents · admin · erp_demo), services(parser · oauth · stats)", "웹 계층과 자동화 계층 분리"],
        ["rpa", "extract(텍스트 · OCR) · excel_writer · erp_typer(Playwright)", "CLI 단독 실행 가능 → 향후 별도 워커로 이전 용이"],
        ["TiDB Cloud", "회원 · 문서 · RPA 작업 이력 저장", "무상태 컨테이너 + 외부 DB → 재배포해도 데이터 유지"],
        ["Gemini API", "문서 구조화 추출", "구조화 출력 · 멀티모달"],
        ["데모 ERP(/erp-demo)", "RPA 입력 대상 화면, 전표번호 발급", "실제 ERP 없이 RPA 전 과정 검증"]], widths=[18, 44, 38], label_col=True)

    d.h1("2. 서비스 구성 및 데이터 흐름")
    d.table(["순서", "주체", "입력 데이터", "처리", "저장 · 출력"], [
        ["1", "사용자", "파일 · 메일 본문", "업로드(확장자 · 10MB 검사)", "storage/uploads (UUID 파일명)"],
        ["2", "rpa/extract", "원본 바이트", "텍스트 레이어 → OCR → 멀티모달 대상 판정", "raw_text"],
        ["3", "services/parser", "텍스트 · 원본", "Gemini 구조화 출력 / 규칙 파서", "documents.parsed(JSON) · parser · status"],
        ["4", "사용자", "수정한 필드", "같은 스키마로 서버 재검증(PATCH)", "documents.parsed"],
        ["5", "rpa/excel_writer", "parsed", "문서 ID 기준 upsert", "사용자별 엑셀 원장 · rpa_jobs"],
        ["6", "rpa/erp_typer", "parsed", "ERP 화면 입력 → 결과 확인", "전표번호 · rpa_jobs"],
        ["7", "services/stats", "documents · rpa_jobs", "성공률 · 일별 추이(KST) 집계", "대시보드 · 모니터링"]],
        widths=[7, 16, 16, 35, 26], align=["C", "L", "L", "L", "L"])

    d.h1("3. 프런트엔드 및 백엔드 구조")
    d.h2("3.1 프런트엔드 화면 경로")
    d.table(["경로", "화면", "접근 권한"], [
        ["/", "메인(랜딩) — 최초 접속 화면", "누구나"], ["/login", "로그인 · 회원가입 · 테스트 계정 · OAuth", "누구나"],
        ["/admin/login", "운영 관리자 토큰 로그인", "누구나(토큰 필요)"], ["/oauth/callback", "OAuth 복귀 · 토큰 저장", "누구나"],
        ["/terms · /privacy", "이용약관 · 개인정보처리방침", "누구나"], ["/dashboard", "사용자 KPI · 추이 · 최근 문서", "로그인"],
        ["/documents", "업로드 · 검수 · RPA 실행 · 작업 이력", "로그인"], ["/admin/users", "회원 관리 · 권한 변경", "관리자(테스트 관리자는 조회)"],
        ["/admin/monitoring", "파싱 · RPA 성공률, 분포, 최근 실패", "관리자(테스트 관리자는 조회)"]], widths=[22, 50, 28], label_col=True)
    d.h2("3.2 백엔드 계층")
    d.table(["계층", "모듈", "책임"], [
        ["진입", "main.py", "앱 생성, CORS, 테이블 생성, 테스트 계정 시드 · 권한 복원"],
        ["설정 · DB", "config.py · database.py", "루트 .env 로드, SQLAlchemy 엔진(SQLite / TiDB + TLS)"],
        ["보안", "security.py · deps.py", "PBKDF2 해시 · JWT, 로그인 · 관리자 의존성, 테스트 관리자 쓰기 차단"],
        ["API", "routers/*.py", "auth · documents · admin · erp_demo"],
        ["도메인 로직", "services/*.py", "parser · oauth · stats"],
        ["자동화", "rpa/*.py", "extract · excel_writer · erp_typer"]], widths=[14, 30, 56], label_col=True)

    d.h1("4. 데이터베이스 및 테이블 설계")
    d.p("관계: users 1 : N documents 1 : N rpa_jobs. 모든 시각은 UTC(timezone=True) 로 저장하고, 통계 집계 시 KST 로 변환한다.")
    d.h2("4.1 users")
    d.table(["컬럼", "타입", "제약", "설명"], [
        ["id", "INTEGER", "PK", "회원 번호"], ["email", "VARCHAR(255)", "UNIQUE · INDEX", "로그인 이메일(소문자)"],
        ["name", "VARCHAR(100)", "NOT NULL", "이름"], ["password_hash", "VARCHAR(255)", "NULL 허용", "PBKDF2 해시(OAuth · 토큰 계정은 없음)"],
        ["role", "VARCHAR(20)", "기본 user", "user · test_admin · admin"], ["provider", "VARCHAR(20)", "기본 local", "local · google · naver · kakao · admin_token"],
        ["provider_id", "VARCHAR(255)", "(provider, provider_id) UNIQUE", "OAuth 제공자 식별자"],
        ["created_at · last_login_at", "DATETIME(TZ)", "", "가입 · 최근 로그인 시각"]], widths=[24, 17, 25, 34], align=["L", "C", "L", "L"])
    d.h2("4.2 documents")
    d.table(["컬럼", "타입", "제약", "설명"], [
        ["id", "INTEGER", "PK", "문서 번호"], ["user_id", "INTEGER", "FK users.id · INDEX", "소유자"],
        ["filename · source_type", "VARCHAR(255) · VARCHAR(20)", "", "원본 이름, pdf · image · email · text"],
        ["storage_path", "VARCHAR(500)", "NULL 허용", "업로드 원본 경로"], ["status", "VARCHAR(20)", "기본 uploaded", "uploaded · parsed · failed"],
        ["raw_text", "TEXT", "", "추출 원문"], ["parsed", "JSON", "", "ParsedDocument 결과"],
        ["parser · error", "VARCHAR(30) · TEXT", "", "gemini · rules, 실패 사유"], ["created_at · parsed_at", "DATETIME(TZ)", "", "등록 · 해석 시각"]],
        widths=[24, 24, 20, 32], align=["L", "C", "L", "L"])
    d.h2("4.3 rpa_jobs")
    d.table(["컬럼", "타입", "제약", "설명"], [
        ["id", "INTEGER", "PK", "작업 번호"], ["document_id", "INTEGER", "FK documents.id · INDEX", "대상 문서(문서 삭제 시 함께 삭제)"],
        ["target", "VARCHAR(20)", "", "excel · erp"], ["status", "VARCHAR(20)", "기본 pending", "pending · success · failed"],
        ["message", "TEXT", "", "결과 메시지 · 전표번호 · 실패 사유"], ["created_at · finished_at", "DATETIME(TZ)", "", "시작 · 종료 시각"]],
        widths=[24, 17, 25, 34], align=["L", "C", "L", "L"])

    d.h1("5. API 설계 및 명세")
    d.h2("5.1 엔드포인트")
    d.table(["Method", "Endpoint", "설명", "권한"], [
        ["POST", "/api/auth/register · /login", "이메일 가입 · 로그인(JWT)", "누구나"],
        ["POST", "/api/auth/admin-login", "ADMIN_TOKEN 운영 관리자 로그인", "누구나(토큰)"],
        ["GET", "/api/auth/oauth/{provider}/login · /callback", "OAuth Authorization Code 흐름", "누구나"],
        ["GET", "/api/auth/me · /providers", "내 정보, 활성 OAuth · 관리자 토큰 여부", "로그인 · 누구나"],
        ["GET", "/api/dashboard", "사용자 KPI · 일별 추이", "로그인"],
        ["GET · POST", "/api/documents · /upload · /text", "목록, 업로드, 본문 입력", "로그인"],
        ["GET · PATCH · DELETE", "/api/documents/{id}", "상세, 검수 수정, 삭제", "본인 · 관리자"],
        ["POST", "/api/documents/{id}/reparse · /rpa", "재해석, 엑셀 · ERP 입력", "본인 · 관리자"],
        ["GET", "/api/documents/ledger.xlsx", "엑셀 원장 다운로드", "로그인"],
        ["GET · PATCH", "/api/admin/users · /users/{id}/role · /stats", "회원 관리, 권한 변경, 통계", "관리자"],
        ["GET", "/api/health", "상태, 현재 파서 종류", "누구나"]], widths=[16, 38, 30, 16], align=["C", "L", "L", "C"])
    d.caption("※ 테스트 관리자(test_admin)는 모든 API 에서 GET · HEAD · OPTIONS 만 허용된다(5단계 추가).")
    d.h2("5.2 오류 응답")
    d.table(["코드", "상황"], [
        ["401", "토큰 없음 · 만료, 로그인 실패, 잘못된 관리자 토큰"], ["403", "관리자 권한 없음, 테스트 관리자의 쓰기 요청(읽기 전용)"],
        ["404", "다른 사용자의 문서 접근, 없는 문서"], ["409", "이미 가입된 이메일, 파싱 완료 전 RPA 실행"],
        ["413 · 415", "10MB 초과 업로드 · 지원하지 않는 파일 형식"], ["422", "약한 비밀번호, 스키마에 맞지 않는 검수 값"],
        ["429 · 503", "관리자 토큰 5회 실패 후 10분 차단 · ADMIN_TOKEN 미설정"]], widths=[14, 86], align=["C", "L"])

    d.h1("6. 주요 기능별 처리 흐름")
    d.h2("6.1 문서 처리 파이프라인")
    d.table(["단계", "모듈", "처리", "실패 시"], [
        ["① 추출", "rpa/extract.py", "PDF 텍스트 레이어 → 이미지 Tesseract(kor+eng) → 20자 미만이면 원본을 Gemini 멀티모달로 전달, EML 헤더+본문, HTML 정리", "미지원 형식 415"],
        ["② 정형화", "services/parser.py", "Gemini 구조화 출력(ParsedDocument), 키가 없으면 규칙 파서", "429 · 5xx 재시도, 최종 실패 시 status=failed + 사유"],
        ["③ 검수", "routers/documents.py", "화면 수정값을 같은 스키마로 재검증 후 저장", "형식 오류 422"],
        ["④ 입력", "rpa/excel_writer · erp_typer", "엑셀 원장 upsert / ERP 화면 입력 후 결과 확인", "rpa_jobs 에 실패 사유 기록"]], widths=[11, 22, 45, 22], label_col=True)
    d.h2("6.2 AI 정형화")
    d.bullets(["ParsedDocument(Pydantic) 를 Gemini response_schema 와 API 검증 모델로 함께 사용 — 한쪽만 고치면 됨",
               "프롬프트: 회계 전표 입력 담당자 역할, 금액은 정수, 날짜는 YYYY-MM-DD, '문서에 없는 값은 null, 추측 금지', confidence(0~1)",
               "temperature 0, 문서 텍스트는 최대 30,000자, 이미지 · 스캔 PDF 는 원본 바이트를 함께 전달",
               "재시도: 429 · 500 · 503 · 504 만 2s → 5s → 10s 백오프(최대 4회 시도), 400 등 요청 오류는 즉시 실패",
               "규칙 기반 파서: 날짜 · 사업자번호 · 합계 · 부가세 · 결제수단 · 품목 줄 정규식, confidence = 0.2 + 0.15 × 찾은 핵심 필드 수 + 0.1(품목 있음)"])
    d.h2("6.3 RPA")
    d.table(["항목", "설계"], [
        ["화면 분리", "FIELD_SELECTORS 맵(vendor · business_number · date · total_amount · vat · summary), SUBMIT · RESULT 셀렉터"],
        ["성공 판정", "결과 요소의 data-status=\"ok\" 와 data-voucher(전표번호)를 확인해야 성공"],
        ["대상 주소", "ERP_URL 미설정 시 같은 서버의 데모 ERP(127.0.0.1:$PORT/erp-demo)"],
        ["실행 모드", "RPA_HEADLESS(기본 true), CLI: python -m rpa.erp_typer"],
        ["엑셀 적재", "문서 ID 기준 기존 행 교체 후 정렬, 열 너비 자동 조정, 사용자별 원장 파일"],
        ["오류 처리", "Chromium 미설치 등 환경 오류를 안내 문구로 변환해 작업 이력에 기록"]], widths=[16, 84], label_col=True)
    d.h2("6.4 OAuth 로그인")
    d.table(["순서", "처리"], [
        ["1", "/api/auth/oauth/{provider}/login: 임의 state 생성 → HttpOnly · SameSite=Lax 쿠키 저장 → 제공자 인가 화면으로 이동"],
        ["2", "/callback: 쿠키의 state 와 요청 state 를 compare_digest 로 비교(불일치 시 로그인 화면으로 오류 전달)"],
        ["3", "인가 코드 → 액세스 토큰 교환 → 프로필 조회(Google 은 email_verified, Kakao 는 is_email_verified 확인)"],
        ["4", "(provider, provider_id) 로 회원 식별, 같은 이메일이 다른 방식으로 가입돼 있으면 연결하지 않고 거부"],
        ["5", "JWT 발급 → 프런트 /oauth/callback#token=… (URL 해시로 전달해 서버 로그에 남지 않음)"]], widths=[8, 92], align=["C", "L"])

    d.h1("7. 사용자 인터페이스 및 화면 구성")
    d.table(["화면", "구성 요소"], [
        ["공통 레이아웃", "글로벌 헤더(비로그인: 소개 메뉴 · 로그인 / 로그인: 업무 메뉴 · 역할 배지), 4열 푸터, 원형 To the Top, 토스트"],
        ["메인", "Hero(원문 → AI 추출 → 엑셀/ERP 전표), 지원 형식, 작동 방식 4단계, 주요 기능, 활용 사례, 보안 · 권한, FAQ"],
        ["로그인", "Split 레이아웃(좌측 브랜드 그래픽), 테스트 계정 버튼 2개, OAuth 3사 버튼, 비밀번호 규칙 실시간 체크, 회원가입 전환"],
        ["대시보드", "KPI 카드, 최근 14일 처리 추이, 입력 소스 분포, 최근 문서"],
        ["문서 처리", "드래그&드롭 업로드 / 이메일 본문 탭, 추출 결과 검수 폼, 엑셀 적재 · ERP 입력 버튼, 작업 이력"],
        ["관리자", "회원 관리(검색 · 필터 · 권한 토글), 모니터링(성공률 게이지, 일별 차트, 분포 도넛, 최근 실패)"],
        ["모바일", "햄버거↔X 전환, 우측 드로어(백드롭 · ESC · 스크롤 잠금 · inert)"]], widths=[16, 84], label_col=True)

    d.h1("8. 인증 및 권한 관리 설계")
    d.table(["항목", "설계"], [
        ["인증", "JWT(HS256, 만료 720분), PBKDF2-SHA256 26만 회 반복 해시, hmac.compare_digest 비교"],
        ["비밀번호", "영문 대 · 소문자 + 숫자 + 특수문자 8자 이상, 화면 실시간 체크 + 서버 재검증"],
        ["권한 검사", "deps.get_current_user 단일 진입점: test_admin 의 GET · HEAD · OPTIONS 외 요청 403 / require_admin: admin · test_admin"],
        ["운영 관리자", "/api/auth/admin-login + ADMIN_TOKEN, 같은 IP 5회 실패 시 10분 차단(429), 미설정 시 503"],
        ["공개 테스트 계정", "test_accounts.py 기준 권한을 서버 기동 시 복원, 권한 변경 API 로 변경 불가(400)"],
        ["입력 검증 · 비밀 값", "업로드 확장자 · 10MB 제한, Pydantic 검증 / 루트 .env 하나로 관리(Vite 는 VITE_ 접두사만 노출)"]], widths=[18, 82], label_col=True)
    d.table(["동작", "운영 관리자", "테스트 관리자", "일반 사용자"], [
        ["관리자 화면 조회", "허용", "허용", "차단"], ["문서 업로드 · 검수 · 삭제", "허용", "차단", "본인"],
        ["엑셀 적재 · ERP 타이핑", "허용", "차단", "본인"], ["회원 권한 변경", "허용", "차단", "차단"],
        ["다른 사용자 문서 열람", "허용", "조회만", "차단"]], widths=[34, 22, 22, 22], align=["L", "C", "C", "C"])
    d.caption("※ 권한 매트릭스(5단계 개편 기준). 화면의 버튼 비활성은 편의 기능이며 실제 경계는 서버 검사이다.")

    d.h1("9. 외부 서비스 및 연동 구조")
    d.table(["서비스", "용도", "연동 방식", "설정 키", "실패 대응"], [
        ["Google Gemini", "문서 구조화 추출", "google-genai SDK, response_schema", "GEMINI_API_KEY · GEMINI_MODEL", "일시 오류 재시도, 키 없으면 규칙 파서"],
        ["Google · Naver · Kakao", "소셜 로그인", "Authorization Code + state 쿠키", "*_CLIENT_ID · *_CLIENT_SECRET", "미설정 제공자는 로그인 화면으로 안내"],
        ["TiDB Cloud", "운영 DB", "SQLAlchemy + PyMySQL, TLS", "DATABASE_URL · DB_SSL", "기동 시 연결 실패 → 로그로 원인 확인"],
        ["Render", "백엔드 · 프런트 호스팅", "Git 연동 자동 배포, Build Filter", "대시보드 환경 변수", "헬스 체크 /api/health"],
        ["GitHub Actions", "CI", "paths-filter 로 변경 영역 테스트 · 빌드", "(배포 시크릿은 선택)", "실패 시 배포 중단"]],
        widths=[17, 15, 25, 23, 20])

    d.h1("10. 배포 설계")
    d.bullets(["백엔드: Docker(Tesseract 한국어 + Chromium), Render Web Service, 헬스 체크 /api/health",
               "프런트엔드: Render Static Site(/* → /index.html Rewrite), Netlify 보조",
               "CI/CD: GitHub Actions paths-filter 로 변경 영역만 테스트 · 빌드, Render Build Filter 로 변경 영역만 배포",
               "Mock 모드: VITE_API_URL 미설정 시 localStorage 목업 API → 백엔드 없이 프런트 단독 배포"])
    return d


def output_03() -> Document:
    d = new_doc("03", "구현 산출물", "3단계 구현", "2026년 11월 30일(월) ~ 12월 09일(수)")
    d.h1("1. 개발 환경 및 기술 스택")
    d.table(["구분", "도구 · 버전", "비고"], [
        ["개발 환경", "Windows · Python 3.11.9(.venv) · Node.js 24(로컬) / 22(빌드)", "단일 requirements.txt, 루트 .env 하나로 설정"],
        ["Backend", "FastAPI 0.115.12 · Uvicorn 0.34.2 · SQLAlchemy 2.0.40 · Pydantic 2.11.4 · PyJWT 2.10.1", "python-dotenv · python-multipart"],
        ["DB 드라이버", "PyMySQL 1.1.1 (TiDB) / SQLite (로컬 · 테스트)", "TLS: certifi CA"],
        ["AI", "google-genai 1.14.0 (Gemini)", "구조화 출력 · 멀티모달"],
        ["RPA · 데이터", "Playwright 1.52.0 · pandas 2.2.3 · openpyxl 3.1.5 · pypdf 5.4.0 · pytesseract 0.3.13 · BeautifulSoup4 4.13.4", "Tesseract OCR 은 Docker 이미지에 설치"],
        ["Frontend", "React 19.3 · React Router 7.18 · Vite 8.3 · Tailwind CSS 4.3 · Recharts 3.10 · FontAwesome", "ESLint, 페이지 단위 코드 스플리팅"],
        ["테스트", "pytest 8.3.5 · httpx 0.28.1 (FastAPI TestClient)", "임시 SQLite, 외부 키 격리"]], widths=[14, 56, 30], label_col=True)
    d.caption("※ 버전은 requirements.txt · frontend/package.json 기준이다.")

    d.h1("2. 프로젝트 디렉터리 구조")
    d.table(["경로", "설명"], [
        ["backend/app/main.py", "앱 생성, CORS, 테이블 생성, 테스트 계정 시드 · 권한 복원"],
        ["backend/app/config.py · database.py", "루트 .env 설정, SQLAlchemy 엔진(SQLite / TiDB + TLS)"],
        ["backend/app/deps.py · security.py · test_accounts.py", "인증 · 권한 의존성, PBKDF2 · JWT, 공개 테스트 계정 정의"],
        ["backend/app/routers/", "auth · documents · admin · erp_demo"],
        ["backend/app/services/", "parser(Gemini/규칙) · oauth · stats"],
        ["backend/tests/", "pytest (외부 키를 비워 로컬 설정과 무관하게 실행, 임시 DB)"],
        ["rpa/", "extract.py · excel_writer.py · erp_typer.py"],
        ["frontend/src/", "pages · components/layout · api(client · mock) · context(Auth · Toast) · utils"],
        ["docs/", "md(작업 기록) · 진행일지 · 산출물 · pdf · 발표자료 · video · tools(문서 생성)"],
        ["index.html · .github/workflows/deploy.yml", "GitHub Pages 포트폴리오 · CI"]], widths=[38, 62], label_col=True)

    d.h1("3. 주요 모듈 및 파일별 역할")
    d.table(["모듈", "구현 내용"], [
        ["routers/auth.py", "가입 · 로그인, 운영 관리자 토큰 로그인, OAuth 로그인/콜백(state 쿠키 검증), 내 정보, 활성 제공자 목록"],
        ["routers/documents.py", "업로드(확장자 · 10MB 검사, UUID 파일명), 본문 입력(HTML 정리), 검수 PATCH(스키마 재검증), 재해석, 삭제, RPA 실행, 원장 다운로드"],
        ["routers/admin.py", "회원 목록 · 검색 · 필터, 권한 변경(본인 강등 · 테스트 계정 변경 차단), 통계"],
        ["routers/erp_demo.py", "데모 ERP 전표 입력 화면, 전표번호(JV-YYYYMMDD-NNNN) 발급 API"],
        ["services/parser.py", "Gemini 구조화 출력 · 멀티모달 · 재시도, 규칙 기반 파서, ParseError 로 실패 사유 전달"],
        ["services/stats.py", "파싱 성공률 parsed/(parsed+failed), RPA 성공률 success/(success+failed), 최근 14일 KST 일별 추이, 분포"],
        ["rpa/extract.py", "pypdf, Tesseract(kor+eng), EML(plain/html), HTML(BeautifulSoup), 인코딩 판별(utf-8 · cp949 · euc-kr)"],
        ["rpa/excel_writer.py · erp_typer.py", "문서 ID 기준 upsert · 열 너비 조정 / Playwright 셀렉터 입력 → 저장 → 결과 확인, CLI 실행"]], widths=[28, 72], label_col=True)

    d.h1("4. 기능별 구현 내용")
    d.h2("4.1 프런트엔드")
    d.table(["화면 · 구성 요소", "구현 내용"], [
        ["components/layout", "SiteLayout(헤더 · 푸터 · 원형 Top 버튼 · 읽기 전용 배너), Header(로그인 상태별 메뉴, 모바일 드로어), Footer(4열)"],
        ["pages/Home · Policy", "도메인 맞춤 메인(해시 이동 섹션), 이용약관 · 개인정보처리방침"],
        ["pages/Login · AdminLogin", "Split 로그인, 테스트 계정 원클릭, OAuth 3사, 비밀번호 규칙 칩, 운영 관리자 토큰 로그인"],
        ["pages/Dashboard · Documents", "KPI · 추이 차트, 드래그&드롭 업로드 · 본문 입력, 검수 폼, 엑셀 · ERP 실행, 작업 이력"],
        ["pages/admin", "회원 관리(검색 · 필터 · 권한 토글), 모니터링(게이지 · 일별 막대 · 도넛 · 최근 실패)"],
        ["api/client · mock", "JWT 첨부 · 오류 메시지 변환 / VITE_API_URL 이 비면 localStorage 목업 API(같은 권한 규칙)"],
        ["index.css", "디자인 토큰(text-display ~ caption, container-page, section-y, page-y, eyebrow), @utility 공통 클래스"]], widths=[24, 76], label_col=True)
    d.h2("4.2 백엔드 및 API")
    d.bullets(["FastAPI 라우터 4개(auth · documents · admin · erp_demo), Pydantic 스키마로 요청 검증과 응답 모델 정의, /docs 자동 생성",
               "업로드는 확장자 화이트리스트와 10MB(413) 검사 후 UUID 파일명으로 저장, 원본 이름은 DB 에만 보관",
               "검수 PATCH 는 기존 결과와 수정값을 합쳐 ParsedDocument 로 다시 검증(422), RPA 는 parsed 상태에서만 실행(409)",
               "통계는 DB 에 종속되지 않도록 Python 에서 집계(SQLite · TiDB 동일 동작)"])
    d.h2("4.3 데이터 수집 및 처리 — 단계적 텍스트 추출")
    d.code("""
if suffix in PDF_TYPES:
    text = _pdf_text(data)
    if len(text) >= MIN_TEXT_LENGTH:          # 20자 이상이면 텍스트 레이어 사용
        return Extraction(text, "pdf-text")
    return Extraction(text, "vision", needs_vision=True, mime_type=...)
if suffix in IMAGE_TYPES:
    if tesseract_available():
        text = _ocr_image(data)                # lang="kor+eng"
        if len(text) >= MIN_TEXT_LENGTH:
            return Extraction(text, "tesseract")
    return Extraction("", "vision", needs_vision=True, mime_type=...)""", "코드 1. rpa/extract.py — 가장 싸고 정확한 방법부터 시도")
    d.h2("4.4 AI 정형화 — Gemini 구조화 출력과 재시도")
    d.code("""
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=ParsedDocument,          # API 검증 모델과 같은 클래스
    temperature=0,
)
for attempt, delay in enumerate((*RETRY_DELAYS, None)):   # 2s, 5s, 10s
    try:
        response = client.models.generate_content(model=..., contents=contents, config=config)
        break
    except genai_errors.APIError as exc:
        if exc.code in RETRYABLE_STATUS and delay is not None:   # 429 · 500 · 503 · 504
            time.sleep(delay)
            continue
        raise ParseError(...)
return ParsedDocument.model_validate_json(response.text).model_dump()""", "코드 2. services/parser.py")
    d.h2("4.5 RPA — 결과 확인 후 성공 처리")
    d.code("""
page.goto(url, wait_until="domcontentloaded", timeout=15_000)
for key, selector in FIELD_SELECTORS.items():
    page.fill(selector, "")
    page.type(selector, str(value), delay=delay_ms)
page.click(SUBMIT_SELECTOR)
result = page.wait_for_selector("#result[data-status]", timeout=10_000)
if result.get_attribute("data-status") != "ok":
    raise ErpTypingError(result.inner_text())
return result.get_attribute("data-voucher")       # 전표번호""", "코드 3. rpa/erp_typer.py")
    d.h2("4.6 데이터베이스 연동")
    d.bullets(["DATABASE_URL 하나로 SQLite(로컬 · 테스트) ↔ TiDB(운영) 전환, SQLite 상대 경로는 저장소 기준 절대 경로로 변환",
               "DB_SSL=true 이면 PyMySQL 에 certifi CA 번들을 넘겨 TLS 접속(TiDB Serverless 필수), pool_pre_ping 으로 끊긴 연결 재확인",
               "기동 시 Base.metadata.create_all 로 테이블 생성, SEED_TEST_ACCOUNTS=true 이면 테스트 계정 생성 · 권한 복원"])
    d.h2("4.7 인증 및 보안")
    d.bullets(["PBKDF2-SHA256 26만 회 + 솔트, JWT(HS256) 에 역할 포함, 만료 720분",
               "OAuth state 쿠키(HttpOnly · SameSite=Lax · 운영은 Secure), 이메일 인증 여부 확인, 이메일 중복 계정 자동 연결 차단",
               "CORS 허용 도메인 제한, 관리자 API 는 require_admin, 다른 사용자 문서는 404 로 존재 여부를 숨김"])
    d.h2("4.8 외부 서비스 연동")
    d.bullets(["Gemini: 이미지 · 스캔 PDF 는 원본 바이트를 Part 로 함께 전달, 키가 없으면 규칙 파서로 자동 전환(/api/health 의 parser 로 확인)",
               "OAuth 3사: 제공자별 토큰 · 프로필 엔드포인트와 응답 구조 차이를 services/oauth.py 에서 흡수",
               "데모 ERP: 같은 서버의 /erp-demo 화면을 RPA 대상으로 사용(ERP_URL 로 실제 ERP 주소 교체 가능)"])

    d.h1("5. 배포 및 운영 환경 구성")
    d.p("구현 단계에서는 Docker 이미지(backend · frontend), docker-compose.yml, render.yaml, netlify.toml, deploy.yml 을 작성하고 로컬에서 실행 · 테스트하였다. "
        "운영 배포와 운영 점검 결과는 산출물 04 에 정리하였다.")

    d.h1("6. 구현 단계 테스트")
    d.table(["구분", "대상", "검증 내용"], [
        ["단위", "비밀번호 규칙", "대 · 소문자 · 숫자 · 특수문자 · 길이 조합별 허용 / 거부(6개)"],
        ["통합", "회원", "약한 비밀번호 거부, 가입 · 내 정보, 로그인 실패"],
        ["통합", "OAuth", "미설정 제공자는 로그인 화면으로 이동, 잘못된 state 거부"],
        ["통합", "문서 · RPA", "업로드 → 파싱 → 엑셀 적재, 본문 입력 · 검수 수정, 해석 불가 문서 failed, 미지원 형식 415"],
        ["통합", "대시보드 · 관리자", "사용자별 통계 범위, 관리자 권한 검사, 회원 관리 · 통계"],
        ["통합", "데모 ERP", "전표 입력 시 전표번호 발급"]], widths=[10, 20, 70], align=["C", "L", "L"])
    d.p("결과: pytest 19개 통과, 프런트 lint 오류 0 · build 성공. 실서버 E2E(로그인 → 영수증 업로드 → 규칙 파싱 → Playwright 데모 ERP 입력 · 전표번호 발급 → 엑셀 적재)와 "
        "데스크톱(1440) · 모바일(390) 화면을 Playwright 로 점검하였다. 이후 단계에서 테스트가 22개(4단계) → 30개(5단계)로 늘었다(산출물 04 참조).")

    d.h1("7. 트러블슈팅")
    d.table(["문제", "원인", "해결"], [
        ["키를 넣지 않았는데 Gemini · OAuth 가 '설정됨'", ".env 에서 빈 값 뒤 인라인 주석이 값으로 읽힘", "주석을 별도 줄로 분리, 규칙 문서화, 테스트는 외부 키를 빈 값으로 고정"],
        ["Tailwind 사용자 클래스 @apply 오류", "v4 는 @layer components 클래스에 @apply 불가", "@utility 로 정의"],
        ["모바일 드로어 위치 오류", "헤더 backdrop-filter 가 fixed 요소의 기준 박스가 됨", "드로어를 헤더 밖으로 분리"],
        ["초기 번들 크기", "단일 번들 885KB", "페이지 단위 코드 스플리팅(메인 416KB, 차트는 사용 페이지에서만 로드)"]], widths=[30, 34, 36], label_col=True)
    return d


def output_04() -> Document:
    d = new_doc("04", "배포 산출물", "4단계 배포", "2026년 12월 10일(목) ~ 12월 17일(목)")
    d.h1("1. 배포 구성")
    d.table(["구분", "주소", "플랫폼"], [
        ["프런트엔드", "https://dataquill.onrender.com", "Render Static Site (/* → /index.html Rewrite)"],
        ["백엔드 API", "https://dataquill-api.onrender.com (/docs, /api/health)", "Render Web Service (Docker)"],
        ["프런트엔드(보조)", "https://dataquill.netlify.app", "Netlify"],
        ["데이터베이스", "TiDB Cloud Serverless", "MySQL 호환 · TLS 필수"],
        ["포트폴리오", PORTFOLIO, "GitHub Pages (index.html)"],
        ["저장소", REPO, "GitHub"]], widths=[18, 46, 36], label_col=True)

    d.h1("2. 컨테이너 · 인프라")
    d.bullets(["backend/Dockerfile: python:3.11-slim-bookworm 고정, Tesseract OCR(한국어), playwright install --with-deps chromium, PORT 환경 변수로 uvicorn 실행",
               "frontend/Dockerfile: 빌드 후 nginx 로 정적 파일 제공",
               "docker-compose.yml: backend(8000) · frontend(5173), 업로드 저장소 볼륨",
               "render.yaml: 두 서비스 정의, Build Filter(backend/** · rpa/** · requirements.txt / frontend/**), 헬스 체크 /api/health",
               "netlify.toml: frontend/ 변경 시에만 빌드, SPA 리다이렉트"])

    d.h1("3. CI/CD")
    d.table(["Job", "조건", "내용"], [
        ["changes", "항상", "dorny/paths-filter 로 frontend / backend 변경 판별"],
        ["frontend", "frontend/** 변경", "npm ci · lint · build, Netlify 시크릿이 있으면 배포"],
        ["backend", "backend/** · rpa/** · requirements.txt 변경", "pip install · pytest, Render 배포 훅이 있으면 배포"]], widths=[14, 34, 52], align=["C", "L", "L"])
    d.p("기본 배포는 Render · Netlify 의 Git 연동 자동 배포이며, Actions 는 테스트 · 빌드를 담당한다(시크릿 미등록 시 배포 단계 생략). "
        "문서만 고친 커밋은 어떤 서비스도 다시 빌드하지 않는다.")

    d.h1("4. 환경 변수 명세")
    d.table(["그룹", "키", "설명"], [
        ["앱", "APP_ENV, SECRET_KEY, JWT_EXPIRE_MINUTES", "JWT 서명 키 등"], ["관리자", "ADMIN_TOKEN, ADMIN_EMAIL", "운영 관리자 토큰 로그인"],
        ["DB", "DATABASE_URL, DB_SSL, DB_SSL_CA", "TiDB 는 DB_SSL=true 필수"], ["주소", "FRONTEND_URL, BACKEND_URL, CORS_ORIGINS", "OAuth 복귀 · 콜백, CORS"],
        ["계정", "SEED_TEST_ACCOUNTS", "테스트 계정 자동 생성"], ["AI", "GEMINI_API_KEY, GEMINI_MODEL", "비우면 규칙 기반 파서"],
        ["OAuth", "GOOGLE/NAVER/KAKAO_CLIENT_ID · _CLIENT_SECRET", "Redirect URI: {BACKEND_URL}/api/auth/oauth/{provider}/callback"],
        ["RPA", "ERP_URL, RPA_HEADLESS", "비우면 같은 서버의 데모 ERP"], ["프런트", "VITE_API_URL", "비우면 Mock 모드"]], widths=[12, 42, 46], align=["C", "L", "L"])
    d.caption("※ 값은 저장소에 포함하지 않는다. 로컬은 루트 .env, 운영은 Render 대시보드에 등록한다.")

    d.h1("5. 실행 방법")
    d.h2("5.1 로컬 실행")
    d.code("""
py -3.11 -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m playwright install chromium
.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000   # API  http://localhost:8000/docs
cd frontend && npm install && npm run dev                                       # 화면 http://localhost:5173""")
    d.h2("5.2 Docker 와 검증")
    d.code("""
docker compose up --build                        # backend 8000 · frontend 5173
.venv/Scripts/python -m pytest backend/tests -q  # 백엔드 테스트
cd frontend && npm run lint && npm run build     # 프런트 검증""")
    d.h2("5.3 운영 배포 절차")
    d.bullets(["main 브랜치에 푸시 → GitHub Actions 가 변경 영역 테스트 · 빌드",
               "Render 가 Build Filter 에 해당하는 서비스만 다시 빌드 · 배포, /api/health 로 상태 확인",
               "무료 플랜은 유휴 시 잠들므로 시연 전 /api/health 를 호출해 서버를 깨움"])

    d.h1("6. 테스트")
    d.h2("6.1 테스트 목적 및 범위")
    d.bullets(["목적: 회원 · 권한 · 문서 처리 · RPA · 통계 규칙이 의도대로 동작하고, 운영에서만 발생한 장애가 다시 생기지 않는지 확인",
               "범위: 백엔드 API 통합 테스트(pytest), 프런트 lint · build, 운영 환경 점검, 화면 점검(Playwright)",
               "제외: 파싱 정확도 정량 평가(정답셋 미구축), 부하 테스트"])
    d.h2("6.2 테스트 환경 및 조건")
    d.table(["구분", "환경 · 조건"], [
        ["자동 테스트", "pytest 8.3.5 + FastAPI TestClient, 임시 SQLite, GEMINI_API_KEY · OAuth 키를 비워 로컬 설정과 무관하게 실행"],
        ["관리자 토큰", "테스트 전용 ADMIN_TOKEN 을 환경 변수로 주입"],
        ["외부 API", "Gemini 재시도는 가짜 클라이언트로 429/503/400 응답을 재현"],
        ["운영 점검", "dataquill.onrender.com · dataquill-api.onrender.com, 운영 DB 는 건드리지 않고 임시 DB 로 별도 검증"],
        ["화면 점검", "Playwright(Chromium) 데스크톱 1440px · 모바일 390px"]], widths=[18, 82], label_col=True)
    d.h2("6.3 기능별 테스트 항목 및 결과")
    d.table(["ID", "테스트 항목", "입력값", "예상 결과", "결과"], [
        ["T-01", "비밀번호 규칙", "Abcdef1! / abcdef1! / Ab1! 등 6종", "규칙 충족만 허용", "통과"],
        ["T-02", "약한 비밀번호 가입", "password1", "422", "통과"],
        ["T-03", "가입 · 내 정보 · 중복 가입", "New@Example.com, Strong1!x", "201 · 소문자 저장 · 중복 409", "통과"],
        ["T-04", "로그인 실패", "틀린 비밀번호", "401", "통과"],
        ["T-05", "OAuth 미설정 · 위조 state", "/oauth/google/login, state=forged", "로그인 화면으로 oauth_error", "통과"],
        ["T-06", "업로드 → 파싱 → 엑셀", "영수증 TXT", "parsed · 금액 14,000 · 부가세 1,273 · 원장 xlsx", "통과"],
        ["T-07", "메일 본문 입력 · 검수 수정", "청구 메일 본문, vendor 수정", "email 유형 · 330,000 · 수정 반영", "통과"],
        ["T-08", "해석 불가 문서", "금액 · 날짜 없는 본문", "failed + 사유, RPA 409", "통과"],
        ["T-09", "미지원 형식", "a.exe", "415", "통과"],
        ["T-10", "대시보드 범위", "일반 사용자 토큰", "본인 통계만, 14일 추이", "통과"],
        ["T-11", "관리자 API 권한", "일반 사용자 · 토큰 없음", "403 · 401", "통과"],
        ["T-12", "회원 관리 · 통계", "권한 변경, 본인 강등", "변경 반영 · 본인 강등 400", "통과"],
        ["T-13", "데모 ERP 전표", "거래처 · 일자 · 금액", "JV- 전표번호 발급", "통과"],
        ["T-14", "Gemini 재시도", "503 ×2 / 503 ×9 / 400 ×1", "3회째 성공 / 4회 후 실패 / 즉시 실패", "통과"],
        ["T-15", "운영 관리자 토큰", "올바른 토큰 / 틀린 토큰 5회 / 미설정", "admin 발급 / 429 차단 / 503", "통과"],
        ["T-16", "테스트 관리자 조회", "admin@dataquill.io", "role=test_admin, 관리자 GET 200", "통과"],
        ["T-17", "테스트 관리자 쓰기", "권한 변경 · 문서 생성 · 업로드 · 삭제 · RPA", "모두 403(읽기 전용 안내)", "통과"],
        ["T-18", "공개 계정 권한 고정", "테스트 계정 권한 변경 · 기동 시 복원", "400 · test_admin 복원", "통과"]],
        widths=[7, 20, 28, 34, 11], align=["C", "L", "L", "L", "C"])
    d.caption("※ T-01 ~ T-18 은 backend/tests 의 pytest 30개 케이스를 기능 단위로 묶은 것이다. 최종 결과: 30 passed.")
    d.h2("6.4 운영 환경 점검 결과")
    d.table(["항목", "결과"], [
        ["/api/health", "status ok, env production, parser gemini"],
        ["로그인 · CORS", "프런트 도메인에서 로그인 · API 호출 정상, 허용 도메인 응답 헤더 확인"],
        ["OAuth Redirect", "Google · Naver · Kakao 모두 운영 콜백 주소로 이동"],
        ["Gemini 파싱", "영수증 샘플에서 거래처 · 사업자번호 · 금액 · 부가세 · 품목 정상 추출(신뢰도 0.98)"],
        ["RPA", "엑셀 적재 성공, 발표 영상 녹화 시 운영 서비스에서 ERP 자동 타이핑 · 전표번호 표시 확인"],
        ["권한", "테스트 관리자 role=test_admin, 회원 권한 변경 · 문서 생성 요청 403"],
        ["SPA 라우팅", "Rewrite 적용 후 /login 등 딥링크 새로고침 정상"]], widths=[18, 82], label_col=True)
    d.h2("6.5 예외 상황 및 데이터 검증")
    d.table(["상황", "입력", "처리", "응답"], [
        ["용량 초과", "10MB 를 넘는 파일", "업로드 거부", "413"], ["지원하지 않는 형식", "exe 등", "업로드 거부", "415"],
        ["약한 비밀번호", "규칙 미충족 비밀번호", "가입 거부", "422"], ["형식이 틀린 검수 값", "스키마 불일치 값", "저장 거부", "422"],
        ["해석 불가 문서", "금액 · 날짜 없음", "status=failed + 사유 저장", "201"], ["파싱 전 RPA", "failed 문서", "실행 거부", "409"],
        ["위조된 OAuth state", "쿠키와 다른 state", "로그인 화면으로 오류 전달", "307"], ["LLM 일시 장애", "Gemini 503", "2 · 5 · 10초 재시도", "-"],
        ["관리자 토큰 무차별 대입", "틀린 토큰 5회", "같은 IP 10분 차단", "429"]], widths=[24, 26, 36, 14], align=["L", "L", "L", "C"])
    d.h2("6.6 발견된 오류 및 수정 내용")
    d.table(["이슈", "원인", "조치"], [
        ["코드 변경 없이 Docker 빌드 실패", "slim 태그가 Debian 13 으로 바뀌어 Playwright 1.52 의존성(Debian 11/12 만 지원) 설치 실패", "python:3.11-slim-bookworm 고정"],
        ["TiDB 1105 insecure transport", "TiDB Serverless 는 TLS 필수", "DB_SSL=true + certifi CA, 임시 DB 로 전체 흐름 검증 후 삭제"],
        ["Gemini 503(high demand)", "사용량 폭주 시 일시 오류", "429 · 5xx 만 백오프 재시도, 재시도 테스트 3개 추가(pytest 22개)"],
        ["운영 ERP 타이핑 연결 거부", "Render 컨테이너는 PORT=10000", "기본 대상 127.0.0.1:$PORT"],
        ["/login 새로고침 404", "정적 호스팅 SPA 규칙 없음", "/* → /index.html Rewrite"]], widths=[24, 42, 34], label_col=True)
    d.h2("6.7 테스트 완료 여부 및 개선 사항")
    d.table(["구분", "결과", "개선 사항"], [
        ["자동 테스트", "완료 — 30 passed(5단계 기준)", "프런트 컴포넌트 테스트 추가 검토"],
        ["프런트 검증", "완료 — lint 오류 0, build 성공", "-"],
        ["운영 점검", "완료 — 6.4 항목 정상", "운영 관리자 로그인은 ADMIN_TOKEN 등록 후 재점검 필요"],
        ["정확도 평가", "미실시 — 샘플 단위 검증만 수행", "문서 유형별 정답셋으로 필드 단위 정확도 측정"]], widths=[16, 40, 44], label_col=True)

    d.h1("7. 결과물")
    d.table(["결과물", "위치"], [
        ["소스 코드 · README", REPO], ["운영 서비스", "https://dataquill.onrender.com"],
        ["API 문서", "https://dataquill-api.onrender.com/docs"], ["포트폴리오", PORTFOLIO], ["작업 기록", "docs/md/"]], widths=[22, 78], label_col=True)
    return d


def output_05() -> Document:
    d = new_doc("05", "피드백 산출물", "5단계 피드백", "2026년 12월 18일(금) ~ 12월 21일(월)")
    d.h1("1. 점검 개요")
    d.p("배포 후 플랫폼 표준 가이드(전역 레이아웃 · 도메인 맞춤 UI · 상용 푸터 · 관리자/테스트 관리자 권한) 기준으로 서비스를 점검하고, "
        "발견된 문제를 반영하였다. 이후 발표자료 · 10분 발표 영상 · 포트폴리오 페이지를 제작하고 문서를 최종 정리하였다.")

    d.h1("2. 피드백 내용 및 반영 결과")
    d.table(["No", "피드백 / 발견 사항", "조치", "상태"], [
        ["1", "공개된 테스트 관리자 계정이 실제 관리자 권한을 가져 누구나 회원 권한 변경 가능(보안)", "test_admin 역할 신설, 서버에서 쓰기 요청 403", "반영"],
        ["2", "운영 관리자 진입 경로가 공개 계정과 분리되어 있지 않음", "/admin/login + ADMIN_TOKEN, compare_digest, 5회 실패 시 10분 차단", "반영"],
        ["3", "페이지마다 헤더 · 푸터 구성이 다름", "SiteLayout 으로 전 페이지 공통화, 원형 Top 버튼", "반영"],
        ["4", "첫 화면에서 서비스 성격이 드러나지 않음", "도메인 맞춤 메인(Hero · 지원 형식 · 작동 방식 · 기능 · 활용 사례 · 보안 · FAQ)", "반영"],
        ["5", "상용 서비스 수준의 푸터 · 정책 페이지 부재", "4열 푸터, 이용약관 · 개인정보처리방침 신설(가짜 사업자 정보 미기재)", "반영"],
        ["6", "글자 크기 · 여백이 화면마다 다름", "디자인 토큰(text-display ~ caption, container-page, section-y, page-y)", "반영"],
        ["7", "발표자료 화면 캡처가 개편 전 기준", "운영 서비스에서 재촬영해 발표자료 재생성", "반영"],
        ["8", "발표 · 시연 영상 부재", "10분 발표 · 시연 영상(자막) · 60초 하이라이트 제작", "반영"],
        ["9", "저장소 방문자가 결과물을 한곳에서 보기 어려움", "GitHub Pages 포트폴리오(제자리 영상 재생 · 챕터 이동)", "반영"],
        ["10", "산출물 문서의 글꼴 혼용 · 표와 제목 간격 부족", "표준 디자인(맑은 고딕, 녹색 표 제목 행, 셀 여백, 표-제목 간격)으로 재작성", "반영"]],
        widths=[6, 42, 42, 10], align=["C", "L", "L", "C"])

    d.h1("3. 권한 모델")
    d.table(["역할", "진입", "권한"], [
        ["admin 운영 관리자", "/admin/login 에서 ADMIN_TOKEN 입력", "전체 CRUD, 회원 권한 변경"],
        ["test_admin 테스트 관리자", "로그인 화면 버튼", "관리자 화면 조회만, 쓰기 요청 403"],
        ["user 일반 사용자", "가입 · OAuth · 테스트 버튼", "본인 문서"]], widths=[26, 36, 38], label_col=True)
    d.bullets(["deps.get_current_user 단일 진입점에서 test_admin 의 GET/HEAD/OPTIONS 외 요청 차단 → 새 API 에도 자동 적용",
               "테스트 계정 권한은 test_accounts.py 기준으로 서버 기동 시 복원, 권한 변경 API 로 변경 불가(400)",
               "프런트 Mock 모드도 같은 규칙 적용"])

    d.h1("4. 최종 구현 기능 및 결과")
    d.table(["영역", "구현 결과", "상태"], [
        ["문서 처리", "6종 입력, 단계적 추출(텍스트 → OCR → 멀티모달), Gemini 구조화 출력 · 재시도, 규칙 파서", "완료"],
        ["검수 · RPA", "검수 저장(서버 재검증), 엑셀 원장 upsert · 다운로드, ERP 자동 타이핑(전표번호 확인)", "완료"],
        ["회원 · 권한", "이메일 · OAuth 3사 · 테스트 계정, 운영/테스트 관리자 분리, 서버 권한 강제", "완료"],
        ["화면", "메인 · 로그인 · 대시보드 · 문서 처리 · 관리자 · 정책, 반응형 · 디자인 토큰", "완료"],
        ["운영", "Render 배포, CI/CD, 헬스 체크, 모니터링(파싱 · RPA 성공률)", "완료"],
        ["결과물", "발표자료(16장 + 부록) · 10분 영상 · 60초 하이라이트 · README · 포트폴리오 · 진행일지 · 산출물", "완료"]],
        widths=[14, 74, 12], align=["L", "L", "C"], label_col=True)

    d.h1("5. 요구사항 충족 여부")
    d.table(["ID", "요구사항 요약", "충족", "근거"], [
        ["FR-01", "이메일 가입 · 로그인, 비밀번호 규칙", "충족", "T-01 ~ T-04"], ["FR-02", "OAuth 3사, 이메일 중복 차단", "충족", "T-05, 운영 Redirect 점검"],
        ["FR-03", "테스트 계정 원클릭 로그인", "충족", "화면 점검, T-16"], ["FR-04", "업로드 · 본문 입력 · 형식 거부", "충족", "T-06 · T-07 · T-09"],
        ["FR-05", "Gemini 추출 · 규칙 파서 대체", "충족", "운영 파싱 샘플, T-06 · T-14"], ["FR-06", "검수 수정 · 재해석 · 삭제", "충족", "T-07"],
        ["FR-07", "엑셀 원장 적재 · 다운로드", "충족", "T-06, 운영 점검"], ["FR-08", "ERP 자동 입력 · 전표번호", "충족", "T-13, 시연 영상"],
        ["FR-09", "대시보드", "충족", "T-10"], ["FR-10", "회원 관리 · 모니터링", "충족", "T-12"],
        ["FR-11", "반응형 GNB · Top 버튼 · 토스트", "충족", "Playwright 화면 점검(1440 · 390)"], ["FR-12", "3단계 권한 분리", "충족", "T-15 ~ T-18"],
        ["NFR-02", "외부 장애 시 서비스 지속", "충족", "규칙 파서 · 재시도"], ["NFR-04", "보안", "부분 충족", "JWT 를 localStorage 에 저장(XSS 대비 HttpOnly 쿠키 전환은 과제)"]],
        widths=[10, 36, 14, 40], align=["C", "L", "C", "L"])

    d.h1("6. 최종 검증 결과")
    d.table(["구분", "항목", "결과"], [
        ["자동 테스트", "pytest(권한 테스트 8개 추가)", "30개 통과"],
        ["프런트", "lint · build", "오류 0 · 성공"],
        ["화면 점검", "로컬 데모 인스턴스 Playwright 16항목", "통과(첫 접속 메인, 헤더/푸터, 읽기 전용 배너 · 버튼 비활성, 잘못된 토큰 거부 등)"],
        ["포트폴리오", "GitHub Pages 22항목", "통과(제자리 영상 재생 · 챕터 이동 · 종료 후 다시 재생 · 모바일)"],
        ["반응형", "데스크톱(1440) · 모바일(390)", "정상"]], widths=[16, 34, 50], label_col=True)

    d.h1("7. 시스템 운영 및 관리 방법")
    d.table(["작업", "방법"], [
        ["상태 확인", "https://dataquill-api.onrender.com/api/health (status · env · parser) — 무료 플랜이라 시연 전 호출해 서버를 깨움"],
        ["운영 관리자", "Render 대시보드에 ADMIN_TOKEN 등록 → /admin/login 에서 토큰 입력"],
        ["테스트 계정", "user@dataquill.io / admin@dataquill.io(읽기 전용) — 권한은 서버 기동 시 자동 복원"],
        ["비밀 값 변경", "Render 대시보드 Environment 수정 → 자동 재배포"],
        ["배포", "main 푸시 → Actions 테스트 · 빌드 → Render 가 변경 영역만 배포"],
        ["문서 재생성", "python docs/tools/build_docs.py (HWPX · PDF 동시 생성 및 검수)"]], widths=[16, 84], label_col=True)

    d.h1("8. 배포 환경 및 실행 방법")
    d.table(["대상", "주소", "비고"], [
        ["서비스", "https://dataquill.onrender.com", "Render Static Site"], ["API", "https://dataquill-api.onrender.com/docs", "Render Web Service(Docker)"],
        ["포트폴리오", PORTFOLIO, "GitHub Pages"], ["로컬 실행", "산출물 04 · 5. 실행 방법", "Python 3.11 · Node.js"]], widths=[14, 50, 36], label_col=True)

    d.h1("9. 최종 결과물 목록")
    d.table(["결과물", "위치"], [
        ["발표자료(PPTX · PDF)", "docs/프로젝트_발표자료.pptx · docs/pdf/프로젝트_발표자료.pdf"],
        ["10분 발표 · 시연 영상 · 자막 · 60초 하이라이트", "docs/video/3조_final.mp4 · 3조_final.srt · 3조_highlight.mp4"],
        ["진행일지 · 산출물(HWPX · PDF)", "docs/ · docs/산출물/ · docs/pdf/"],
        ["작업 기록", "docs/md/"], ["포트폴리오 · README", f"{PORTFOLIO} · {REPO}"]], widths=[36, 64], label_col=True)

    d.h1("10. 회고 (KPT)")
    d.table(["구분", "내용"], [
        ["Keep", "대체 경로 설계(텍스트 → OCR → Vision, Gemini → 규칙)로 외부 의존성 장애에도 서비스 유지\n화면과 서버 양쪽 검증, 고친 문제는 테스트로 재발 방지\n작업일마다 결정 · 검증 · 이슈를 docs/md 에 기록"],
        ["Problem", "실패 원인 대부분이 외부 의존성(기본 이미지 태그, LLM 가용성, 플랫폼 포트)이었음\n공개 테스트 계정의 권한 범위를 배포 후에야 점검함\n파싱 품질을 샘플 단위로만 확인함"],
        ["Try", "기본 이미지 · 의존성 버전 고정과 재시도 정책을 초기 설계에 포함\n공개 계정은 처음부터 최소 권한으로 설계\n정답셋 기반 필드 단위 정확도 측정"]], widths=[12, 88], label_col=True, zebra=False)

    d.h1("11. 알려진 제한 사항")
    d.bullets(["RPA 가 API 요청 안에서 동기로 실행 → 오래 걸리는 작업에 취약",
               "업로드 원본이 컨테이너 디스크에 저장 → 재배포 시 원본 유실 가능(메타데이터 · 결과는 TiDB 에 유지)",
               "스키마 변경을 create_all 로 처리(마이그레이션 도구 없음)",
               "데모 ERP 대상 검증(실제 ERP 연동 전), 무료 플랜 유휴 슬립으로 첫 요청 지연",
               "새로고침 후 문서 시각이 9시간 이르게 표시(TiDB 에서 시간대 없는 값으로 읽힘) — 미수정",
               "운영 서버에 ADMIN_TOKEN 미등록 → 운영 관리자 로그인 비활성(테스트 관리자는 읽기 전용으로 정상 동작)"])

    d.h1("12. 향후 개선 및 확장 계획")
    d.table(["우선순위", "과제", "내용"], [
        ["1", "RPA 작업 큐 분리", "워커 프로세스 + 진행 상태 조회 (rpa 패키지가 분리되어 있어 이전 비용 낮음)"],
        ["2", "원본 스토리지 이전", "S3 등 오브젝트 스토리지, 보존 기간 정책"],
        ["3", "시각 표시 · 마이그레이션", "응답 시각에 UTC 시간대 부여, Alembic 도입"],
        ["4", "정확도 평가", "문서 유형별 정답셋, 필드 단위 정확도, 프롬프트 · 모델 비교"],
        ["5", "실제 ERP 연동 · 보안", "ERP 커넥터(API 우선, 없으면 RPA), 조직(테넌트) 단위 권한, HttpOnly 쿠키 인증"]],
        widths=[12, 26, 62], align=["C", "L", "L"])
    return d


OUTPUTS = {"01_기획분석_산출물.hwpx": output_01, "02_설계_산출물.hwpx": output_02, "03_구현_산출물.hwpx": output_03,
           "04_배포_산출물.hwpx": output_04, "05_피드백_산출물.hwpx": output_05}


# ============================================================================ 3. 한글 저장 · PDF · 검수
def hwp_app():
    import win32com.client as win32

    h = win32.Dispatch("HWPFrame.HwpObject")
    h.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    h.XHwpWindows.Item(0).Visible = False
    return h


def hwpx_text(path: Path) -> str:
    xml = zipfile.ZipFile(path).read("Contents/section0.xml").decode("utf-8")
    xml = re.sub(r"<hp:(header|footer)\b.*?</hp:\1>", "", xml, flags=re.S)
    return " ".join(html.unescape(t) for t in re.findall(r"<hp:t>([^<]*)</hp:t>", xml))


def orphan_headings(pdf: Path) -> list[str]:
    """쪽의 마지막 본문 블록이 제목(11pt 이상)이면 = 제목만 쪽 하단에 남은 것"""
    import fitz

    found = []
    doc = fitz.open(pdf)
    for page in list(doc)[:-1]:
        h = page.rect.height
        blocks = [b for b in page.get_text("dict")["blocks"] if b.get("lines") and 60 < b["bbox"][1] < h - 55]
        if not blocks:
            continue
        last = max(blocks, key=lambda b: b["bbox"][3])
        spans = [sp for ln in last["lines"] for sp in ln["spans"] if sp["text"].strip()]
        if spans and max(sp["size"] for sp in spans) >= 10.9:
            found.append(re.sub(r"\s+", " ", "".join(sp["text"] for sp in spans)).strip())
    return found


def verify() -> bool:
    import fitz  # PyMuPDF

    norm = lambda s: re.sub(r"\s+", "", s)
    ok = True
    targets = [DOCS / n for n in JOURNAL] + [OUT_DIR / n for n in OUTPUTS]
    print(f"{'파일':40} {'쪽':>3} {'본문 일치':>9}  글꼴")
    for src in targets:
        pdf = PDF_DIR / (src.stem + ".pdf")
        if not src.exists() or not pdf.exists():
            print("누락:", src.name)
            ok = False
            continue
        doc = fitz.open(pdf)
        pdf_text = norm("".join(p.get_text() for p in doc))
        tokens = [norm(t) for t in re.split(r"\s{2,}| ", hwpx_text(src)) if len(norm(t)) >= 2]
        missing = [t for t in tokens if t not in pdf_text]
        match = 100 * (1 - len(missing) / max(len(tokens), 1))
        fonts = sorted({f[3].split("+")[-1] for p in doc for f in p.get_fonts()})
        bad_fonts = [f for f in fonts if not f.startswith(("MalgunGothic", "Consolas"))]
        blank = [i + 1 for i, p in enumerate(doc) if len(p.get_text().strip()) < 30]
        orphans = orphan_headings(pdf)
        status = "OK" if match >= 99.5 and not bad_fonts and not blank and not orphans else "확인 필요"
        ok &= status == "OK"
        print(f"{src.name:40} {doc.page_count:>3} {match:8.1f}%  {', '.join(fonts)}  {status}"
              + (f" | 빈 쪽 {blank}" if blank else "") + (f" | 하단 제목 {orphans}" if orphans else "")
              + (f" | 누락 예: {missing[:3]}" if missing else ""))
    return ok


def main() -> None:
    if "--verify" not in sys.argv:
        PDF_DIR.mkdir(exist_ok=True)
        for name, rows in JOURNAL.items():
            fill_journal(TEMPLATES / name, DOCS / name, rows)
        tmp = Path(tempfile.mkdtemp())
        h = hwp_app()

        def save(src, dst):
            assert h.Open(str(src), "HWPX", "forceopen:true"), f"열기 실패: {src.name}"
            assert h.SaveAs(str(dst), "HWPX", ""), f"저장 실패: {dst.name}"
            assert h.SaveAs(str(PDF_DIR / (dst.stem + ".pdf")), "PDF", ""), f"PDF 실패: {dst.name}"
            pages = h.PageCount
            h.Clear(1)
            return pages

        try:
            pending = list(OUTPUTS)
            for attempt in range(4):   # 1차 배치 → 하단 제목 검사 → 해당 제목 앞 쪽 나눔 후 재배치
                for name in pending:
                    OUTPUTS[name]().save(TEMPLATES / "산출물_빈양식.hwpx", tmp / name)
                    print("saved", name, "pages", save(tmp / name, OUT_DIR / name), f"(배치 {attempt + 1}차)")
                retry = []
                for name in pending:
                    orphans = orphan_headings(PDF_DIR / (Path(name).stem + ".pdf"))
                    heads = OUTPUTS[name]().headings()
                    new = {hd for hd in heads for o in orphans if re.sub(r"\s+", "", hd) == re.sub(r"\s+", "", o)}
                    if new - BREAKS.setdefault(name[:2], set()):
                        BREAKS[name[:2]] |= new
                        retry.append(name)
                        print("  쪽 나눔 추가:", name, sorted(new))
                pending = retry
                if not pending:
                    break
            for name in JOURNAL:
                print("saved", name, "pages", save(DOCS / name, DOCS / name))
        finally:
            h.Quit()
            shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(0 if verify() else 1)


if __name__ == "__main__":
    main()
