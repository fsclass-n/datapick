# 2026-11-25 TiDB 데이터베이스명 dataquill → datapick 이관

## 배경

- 프로젝트명 변경에 따라 운영 DB(TiDB Cloud)의 데이터베이스명도 `datapick`으로 맞춤.
- TiDB는 `RENAME DATABASE`를 지원하지 않아 **새 DB 생성 → 테이블 복사** 방식으로 이관.

## 작업

1. `CREATE DATABASE datapick` 후 4개 테이블을 `CREATE TABLE LIKE` + `INSERT SELECT`로 복사:
   - users 6 · documents 20 · rpa_jobs 7 · analyses 10 — 행 수 원본과 일치 확인
2. 로컬 `.env`의 `DATABASE_URL` 끝을 `/dataquill` → `/datapick`으로 변경
3. 새 DB로 백엔드 기동 검증: `/api/health` 정상, `user@datapick.io` 로그인 성공(기동 시 테스트 계정 시드 정상 동작)

## 사용자가 해야 할 것

- **Render 대시보드** → `datapick-api` 서비스 → Environment → `DATABASE_URL` 값 끝의 `/dataquill`을 `/datapick`으로 변경 후 저장(자동 재배포). `render.yaml`에서 `sync: false`라 대시보드 값이 기준.
- 변경 전까지 운영 백엔드는 계속 구 DB(`dataquill`)를 사용하므로 서비스 중단은 없음. 단, 이 기간에 생긴 데이터는 구 DB에만 쌓임 → 전환은 빠를수록 좋음.

## 참고

- 구 DB `dataquill`은 백업 겸용으로 보존 중. 운영 전환 확인 후 삭제하면 됨.
- 새 DB의 users 테이블에는 구 `@dataquill.io` 계정도 복사되어 남아 있음(기능상 문제 없음).
