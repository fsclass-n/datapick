"""로그인 화면에 공개되는 테스트 계정. 비밀번호가 공개되어 있으므로 권한은 항상 아래 값으로 고정한다."""

TEST_ACCOUNTS = [
    {"email": "user@dataquill.io", "name": "테스트 사용자", "password": "User1234!", "role": "user"},
    # 테스트 관리자: 관리자 화면은 보이지만 모든 쓰기 요청이 차단되는 읽기 전용 계정
    {"email": "admin@dataquill.io", "name": "테스트 관리자", "password": "Admin1234!", "role": "test_admin"},
]
TEST_ACCOUNT_EMAILS = {account["email"] for account in TEST_ACCOUNTS}
