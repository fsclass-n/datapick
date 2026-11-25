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
ERP_USERNAME=erp
ERP_PASSWORD=demo1234
ERP_CONFIG=rpa/erp_target.example.json   # url 을 8100 포트로 설정한 예시
```

그 뒤 대시보드에서 'ERP 자동 타이핑'을 실행하면 Playwright 가
`http://localhost:8100`에 로그인해 전표를 등록한다.

## 별도 배포

Render 에 Web Service 를 새로 만들어 연결할 수 있다(render.yaml 의 주석 예시 참조).
배포 후 `ERP_CONFIG` 의 url 두 곳을 배포 주소로 바꾸면 된다.
