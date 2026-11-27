# external_erp — datapick RPA 연동 검증용 독립 미니 ERP

같은 서비스 안의 `/erp-demo`와 달리 **별도 프로세스·도메인**으로 실행해
로그인 → 전표 입력 → 전표번호 확인까지 서비스 경계를 넘는 실제 연동을 재현한다.

## 로컬 실행

```bash
.venv/Scripts/python -m uvicorn external_erp.main:app --port 8100
# 로그인 계정: erp / demo1234 (EXT_ERP_ID · EXT_ERP_PW 로 변경 가능)
```

## datapick 에 연결

`.env`에 아래를 설정하고 백엔드를 재시작한다.

```env
ERP_CONFIG=rpa/erp_target.example.json
ERP_URL=http://localhost:8100/
ERP_USERNAME=erp
ERP_PASSWORD=demo1234
```

그 뒤 대시보드에서 'ERP 자동 타이핑'을 실행하면 Playwright 가
`http://localhost:8100`에 로그인해 전표를 등록한다.

## 별도 배포 (Render)

render.yaml 의 주석 블록을 해제하면 `datapick-erp-demo` 서비스가 생성된다.
그 뒤 `datapick-api` 의 Environment 에 아래를 등록한다(JSON 을 통째로 붙일 필요 없음).

```env
ERP_CONFIG=rpa/erp_target.example.json
ERP_URL=https://<외부ERP-서비스주소>/
ERP_USERNAME=erp
ERP_PASSWORD=demo1234
```

`ERP_URL` 이 설정 파일의 url 을 덮어쓰고 로그인 주소({URL}/login)도 자동으로 유도된다.
`ERP_CONFIG` 에는 같은 형식의 완전한 JSON 문자열을 넣어도 된다.
