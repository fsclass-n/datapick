"""영상 대본·연출 가이드 생성 → docs/video/영상_대본_및_연출가이드.md

    .venv/Scripts/python docs/video/tools/gen_guide.py
"""

from common import BUILD, VIDEO, load_json, scene_starts
from video_scenes import PITCH, RATE, SCENES, TOTAL, VOICE

ACTIONS = {
    "d00": "메인(비로그인) 히어로 제목 강조 → 제품 화면 목업(원문 → AI 추출 → 엑셀/ERP 전표) 강조",
    "d01": "헤더 `로그인` → 테스트 계정 버튼 2개 강조 → `회원가입` → 비밀번호 `dataPick2026!` 입력(규칙 칩 초록 전환) → `로그인`",
    "d02": "`일반 사용자` 테스트 버튼 → 대시보드, 주 메뉴(대시보드 · 문서 처리) 강조",
    "d03": "`문서 처리` → 업로드 영역 클릭 → 스캔 영수증 PDF 선택 → '해석 완료' 토스트 → 오른쪽 검수 패널 (대기 구간은 편집 제거)",
    "d04": "추출 필드(거래처 · 사업자번호 · 일자 · 합계 · 부가세 · 결제수단 · 적요) → 파서 gemini · 신뢰도 → 품목 표",
    "d05": "`적요` 수정(역삼점 팀 점심 식대) → `검수 저장` → '검수 내용을 저장했습니다' 토스트",
    "d06": "RPA 자동 입력 → `엑셀 원장 적재` → `ERP 자동 타이핑` → 전표번호 토스트 · 작업 이력",
    "d07": "`datapick-api.onrender.com/erp-demo` 에서 rpa/erp_typer.py 와 같은 셀렉터 맵으로 입력 재현 → `전표 저장` → '저장 완료: JV-…'",
    "d08": "`이메일 본문` 탭 → `샘플 채우기` → `AI 해석 실행` → 추출 결과",
    "d09": "`대시보드` → KPI 카드 갱신",
    "d10": "주 메뉴 강조(관리자 없음) → 주소 `/admin/users` 직접 이동 → 대시보드로 되돌아옴 (주소 칩 표시)",
    "d11": "헤더 `로그아웃` → 로그인 화면",
    "a00": "`테스트 관리자` 테스트 버튼 → 주 메뉴(회원 관리 · 모니터링 추가) → 읽기 전용 배너",
    "a01": "`모니터링` → KPI 카드 → 성공률 게이지 2개 → 일별 차트 → 문서 소스 · 파서 엔진 · 가입 경로 분포",
    "a02": "`회원 관리` → 검색 `datapick` → 권한 필터 변경·복귀 → 잠긴 권한 스위치",
    "a03": "`문서 처리` → 비활성 업로드 영역 → `이메일 본문` → 비활성 `AI 해석 실행`",
    "a04": "녹화 시점에 운영 API 를 실제로 호출한 응답: 일반 사용자 `GET /api/admin/users` → 403, 테스트 관리자 `PATCH …/role` → 403",
    "a05": "주소 `/admin/login` → 관리자 토큰 입력 폼 강조 (운영 서버에 ADMIN_TOKEN 미등록 → 비활성 안내, 제출하지 않음)",
    "c00": "계정 비교표(일반 사용자 · 테스트 관리자 · 운영 관리자) 정지 화면",
    "s01": "`datapick-api.onrender.com/docs` Swagger: auth → documents → admin 태그 순서로 이동",
    "s02": "`/api/health` 응답(status · env · parser) — 값은 그대로, 들여쓰기만 적용",
    "s03": "GitHub Actions 최근 실행(CI/CD) 강조",
}


def mmss(t: float) -> str:
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def main() -> None:
    starts = scene_starts(SCENES)
    timings = {t["id"]: t for t in (load_json(BUILD / "tts" / "timings.json") or [])}
    rows, detail = [], []
    for s in SCENES:
        a, b = starts[s["id"]], starts[s["id"]] + s["dur"]
        if s["kind"] == "slide":
            screen = f"발표자료 {s['ref']}장"
        elif s["kind"] == "still":
            screen = "계정 비교 카드"
        elif s["id"].startswith("s") or s["id"] in ("d07", "a04"):
            screen = "운영 API · 외부 페이지"
        else:
            screen = "datapick.onrender.com"
        action = ACTIONS.get(s["id"], "슬라이드 표시" + (" · 강조 테두리" if s["hl"] else ""))
        text = " ".join(shown for shown, _ in s["lines"])
        rows.append(f"| {mmss(a)}–{mmss(b)} | {s['label']} | {screen} | {action} | {text} | {s['tag'] or ''} |")
        spoken = [sp for _, sp in s["lines"] if sp]
        detail.append(f"### {mmss(a)} · {s['id']} · {s['label']} ({s['dur']}초)\n\n- 화면: {screen}\n- 동작: {action}\n"
                      + (f"- 안내 태그: `{s['tag']}`\n" if s["tag"] else "")
                      + (f"- 합성 속도: {timings[s['id']]['rate']} · 실제 발화 {timings[s['id']]['speech']}초\n" if s["id"] in timings else "")
                      + "\n" + "\n".join(f"> {shown}" for shown, _ in s["lines"])
                      + ("\n\n발음용 문장: " + " / ".join(spoken) if spoken else "") + "\n")
    speech = sum(t["speech"] for t in timings.values()) if timings else 0
    md = f"""# datapick 10분 발표·시연 영상 — 대본 및 연출 가이드

> 자동 생성 문서 (`docs/video/tools/gen_guide.py`). 대본·시간은 `video_scenes.py` 에서만 수정합니다.

| 항목 | 내용 |
|---|---|
| 파일 | `3조_final.mp4` (1920×1080 · 30fps · H.264 High · AAC 160k 스테레오 · 한국어), 자막 `3조_final.srt`, 하이라이트 `3조_highlight.mp4`, 썸네일 `video-thumbnail.png` |
| 길이 | {mmss(TOTAL)} · 장면 {len(SCENES)}개 · 실제 발화 약 {speech:.0f}초 |
| 구성 | PPT 1~14장 → 일반 사용자 시연 → 테스트 관리자(읽기 전용) 시연 → 계정 비교 → 운영 근거(/docs · /api/health · CI) → 클로징 15·16장 |
| 시연 환경 | 운영 서비스 `https://datapick.onrender.com` (공개 테스트 계정 2개 비교: 일반 사용자 · 테스트 관리자) |
| 내레이션 | 신경망 합성 음성 `{VOICE}` (속도 {RATE}, 톤 {PITCH}), 문장 단위 합성 + 문장 사이 0.35초 쉼, 저역 제거·압축·명료도 보강 후 −16 LUFS |
| 자막 | 화면 자막(한 줄 30자 이내) + `3조_final.srt` |
| 연출 | 노란 원형 커서·클릭 링, 시안 테두리 강조(0.3초 페이드), 주소 칩, 구간 라벨(슬라이드 오른쪽 위 · 시연 왼쪽 아래), 노란 안내 태그 |

## 시연 데이터 원칙

- 녹화를 시작할 때 공개 테스트 일반 사용자의 이전 시연 문서를 지우고, 시연 중 2건(가상 영수증 스캔 PDF · 샘플 청구 메일)을 새로 처리합니다.
  영수증은 시연용으로 만든 가상 문서(`docs/video/assets/sample_receipt_scan.pdf`)입니다.
- AI 해석과 ERP 자동 타이핑은 **운영 서버가 실제로 처리한 결과**입니다. 대기 구간만 편집으로 잘라 냈습니다.
- 서버의 Playwright 로봇은 화면 없이(headless) 동작하므로, 같은 셀렉터 맵(`rpa/erp_typer.py`)과 같은 데모 ERP 화면으로 입력 동작을 재현해 보여 주고 대본·태그로 밝힙니다.
- 테스트 관리자는 읽기 전용이라 데이터가 바뀌지 않습니다. 서버 거부 장면(a04)은 녹화 시점에 운영 API 를 실제로 호출한 응답을 그대로 보여 줍니다.
- 화면에 토큰·비밀번호·환경 변수·개발자 도구는 나오지 않습니다(테스트 계정 비밀번호는 로그인 화면에 공개된 값). 운영 관리자 토큰 입력 화면은 제출하지 않습니다.

## 타임라인

| 시간 | 구간 | 화면 | 동작 | 대본 | 안내 태그 |
|---|---|---|---|---|---|
""" + "\n".join(rows) + "\n\n## 장면별 상세\n\n" + "\n".join(detail) + """
## 다시 만들기

```bash
PYTHONUTF8=1 .venv/Scripts/pip install edge-tts==7.3.1        # 0) 합성 음성 패키지 (requirements.txt 는 건드리지 않음)
.venv/Scripts/python docs/video/tools/tts.py                 # 1) 문장 단위 합성
.venv/Scripts/python docs/video/tools/record_demo.py         # 2) 운영 서비스 시연 녹화 (Edge, CDP 스크린캐스트)
.venv/Scripts/python docs/scripts/capture_screens.py         # 3) 발표자료 화면 캡처 (녹화 후 데이터가 있는 상태)
.venv/Scripts/python docs/scripts/build_presentation.py      # 4) 발표자료 재생성
powershell -File docs/video/tools/export_slides.ps1          # 5) 슬라이드 PNG (읽기 전용으로 열기)
.venv/Scripts/python docs/video/tools/compose.py --rebuild   # 6) 합성 · 자막 · 2-pass 인코딩 · 하이라이트 · 썸네일
.venv/Scripts/python docs/video/tools/check_final.py         # 7) 형식 · 음성 · 깜박임 검사
.venv/Scripts/python docs/video/tools/gen_guide.py           # 8) 이 문서 갱신
```

실제 사람 목소리로 바꾸려면 장면별 녹음을 `docs/video/build/tts/<장면ID>.wav` 로 저장하고(장면 길이보다 0.6초 이상 짧게)
`compose.py --rebuild-audio` 를 실행합니다.
"""
    (VIDEO / "영상_대본_및_연출가이드.md").write_text(md, encoding="utf-8")
    print("saved 영상_대본_및_연출가이드.md")


if __name__ == "__main__":
    main()
