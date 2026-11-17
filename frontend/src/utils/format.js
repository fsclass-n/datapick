export const PASSWORD_RULES = [
  { test: (v) => v.length >= 8, label: '8자 이상' },
  { test: (v) => /[a-z]/.test(v), label: '영문 소문자' },
  { test: (v) => /[A-Z]/.test(v), label: '영문 대문자' },
  { test: (v) => /\d/.test(v), label: '숫자' },
  { test: (v) => /[^A-Za-z0-9]/.test(v), label: '특수문자' },
]
export const isValidPassword = (v) => PASSWORD_RULES.every((rule) => rule.test(v))
export const isValidEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)

export const won = (value) => (value == null ? '-' : `${Number(value).toLocaleString('ko-KR')}원`)
export const compactWon = (value) => {
  if (!value) return '0원'
  if (value >= 1e8) return `${(value / 1e8).toFixed(1)}억원`
  if (value >= 1e4) return `${Math.round(value / 1e4).toLocaleString('ko-KR')}만원`
  return won(value)
}

export const dateTime = (iso) =>
  iso ? new Date(iso).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'
export const dateOnly = (iso) => (iso ? new Date(iso).toLocaleDateString('ko-KR') : '-')

export const SOURCE_LABELS = { pdf: 'PDF', image: '이미지', email: '이메일', text: '텍스트' }
export const PROVIDER_LABELS = { local: '이메일', google: 'Google', naver: '네이버', kakao: '카카오', admin_token: '관리자 토큰' }
export const DOC_TYPE_LABELS = { receipt: '영수증', invoice: '세금계산서', email: '이메일', other: '기타' }
