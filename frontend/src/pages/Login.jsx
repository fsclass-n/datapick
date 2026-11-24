import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight,
  faCheck,
  faCircleExclamation,
  faComment,
  faEnvelope,
  faEye as faEyeIcon,
  faEye,
  faEyeSlash,
  faKeyboard,
  faLock,
  faUser,
  faUserShield,
} from '@fortawesome/free-solid-svg-icons'
import { faGoogle } from '@fortawesome/free-brands-svg-icons'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { IS_MOCK, OAUTH_STATE_KEY, api, oauthLoginUrl } from '../api/client'
import Logo from '../components/layout/Logo'
import { DOCUMENT_TOOL, TOOL_LIST } from '../utils/tools'
import { Spinner } from '../components/ui'
import { PASSWORD_RULES, isValidEmail, isValidPassword } from '../utils/format'

const TEST_ACCOUNTS = {
  user: { email: 'user@dataquill.io', password: 'User1234!', label: '일반 사용자', desc: 'AI 도구 · 문서 자동 입력', icon: faUser },
  admin: { email: 'admin@dataquill.io', password: 'Admin1234!', label: '테스트 관리자', desc: '관리자 화면 · 읽기 전용', icon: faEyeIcon },
}

const SOCIAL = [
  { id: 'google', label: 'Google', className: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50', icon: <FontAwesomeIcon icon={faGoogle} className="text-[#4285F4]" /> },
  { id: 'naver', label: '네이버', className: 'bg-naver text-white hover:brightness-95', icon: <span className="font-heading text-base leading-none font-black">N</span> },
  { id: 'kakao', label: '카카오', className: 'bg-kakao text-[#191919] hover:brightness-95', icon: <FontAwesomeIcon icon={faComment} /> },
]

const SERVICES = [...TOOL_LIST, DOCUMENT_TOOL]

function BrandPanel() {
  return (
    <div className="relative hidden overflow-hidden bg-ink lg:flex lg:w-[46%] lg:flex-col lg:justify-between lg:gap-10 lg:p-10 xl:p-12">
      <img src="/images/hero-quill.webp" alt="" className="absolute inset-0 size-full object-cover opacity-25" />
      <div className="absolute inset-0 bg-gradient-to-b from-ink/70 via-ink/90 to-ink" />
      <div className="absolute inset-0 opacity-25 [background-image:radial-gradient(rgb(233_162_59/0.4)_1px,transparent_1px)] [background-size:22px_22px]" />

      <div className="relative">
        <Logo light />
      </div>

      <div className="relative">
        <h2 className="text-3xl leading-tight font-bold text-white xl:text-4xl">
          문서를 올리면,
          <br />
          <span className="text-gold-400">데이터가 답합니다.</span>
        </h2>
        <p className="mt-5 max-w-md text-white/70">
          견적서 비교, 계약서 위험 조항, 건강검진 추이, 영수증 자동 입력까지. 로그인하면 도구마다 샘플 문서로 바로 체험할 수 있습니다.
        </p>

        <ul className="mt-10 grid grid-cols-2 gap-3">
          {SERVICES.map((tool, i) => (
            <li
              key={tool.id}
              className="flex animate-float items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-3.5 backdrop-blur"
              style={{ animationDelay: `${i * 0.5}s` }}
            >
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gold-500 text-ink">
                <FontAwesomeIcon icon={tool.icon} />
              </span>
              <span className="min-w-0">
                <span className="block truncate font-heading text-sm font-semibold text-white">{tool.short}</span>
                <span className="block truncate text-xs text-white/55">{tool.output.split(' · ')[0]}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="relative border-t border-white/10 pt-6 text-xs text-white/45">
        AI는 문서를 읽기만 하고, 비교 · 판정은 규칙 코드가 계산합니다. 공개 테스트 계정에는 실제 문서를 올리지 마세요.
      </p>
    </div>
  )
}

export default function Login() {
  const { user, login, register } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [params, setParams] = useSearchParams()
  const [mode, setMode] = useState(() => (params.get('mode') === 'signup' ? 'signup' : 'login'))
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [touched, setTouched] = useState(false)
  const [error, setError] = useState(() => params.get('oauth_error') || '')
  const [busy, setBusy] = useState(null)
  const [providers, setProviders] = useState({})

  const isSignup = mode === 'signup'
  const passwordOk = isValidPassword(form.password)
  const emailOk = isValidEmail(form.email)

  useEffect(() => {
    api('/api/auth/providers').then(setProviders).catch(() => {})
  }, [])

  // 소셜 로그인 중 뒤로가기·탭 복귀 시 로딩 상태가 남지 않도록 해제 (bfcache 복원 포함)
  useEffect(() => {
    const onPageShow = (e) => { if (e.persisted) setBusy(null) }
    const onVisible = () => { if (!document.hidden) setBusy(null) }
    window.addEventListener('pageshow', onPageShow)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.removeEventListener('pageshow', onPageShow)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [])

  useEffect(() => {
    if (params.has('oauth_error') || params.has('mode')) setParams({}, { replace: true })
  }, [params, setParams])

  if (user) return <Navigate to={location.state?.from || '/dashboard'} replace />

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  async function submit(values = form, source = 'form') {
    setTouched(true)
    setError('')
    if (!isValidEmail(values.email)) return setError('올바른 이메일 주소를 입력해 주세요.')
    if (!isValidPassword(values.password)) return setError('비밀번호는 영문 대·소문자, 숫자, 특수문자를 조합해 8자 이상이어야 합니다.')
    if (isSignup && source === 'form' && !values.name.trim()) return setError('이름을 입력해 주세요.')

    setBusy(source)
    try {
      const me = isSignup && source === 'form' ? await register(values.name, values.email, values.password) : await login(values.email, values.password)
      toast(`${me.name}님, 환영합니다.`, 'success')
      navigate(location.state?.from || '/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  function quickLogin(kind) {
    const account = TEST_ACCOUNTS[kind]
    setMode('login')
    setForm({ name: '', email: account.email, password: account.password })
    submit({ name: '', ...account }, kind)
  }

  async function socialLogin(provider) {
    if (IS_MOCK) return toast('소셜 로그인은 백엔드(API) 연결 후 사용할 수 있습니다.', 'info')
    if (providers[provider] === false) return setError(`${SOCIAL.find((s) => s.id === provider).label} 로그인이 아직 설정되지 않았습니다.`)
    setBusy(provider)
    try {
      // API 주소를 주소창에 거치지 않고 서비스 로그인 페이지로 바로 이동 (경고 페이지 우회)
      const res = await fetch(`${oauthLoginUrl(provider)}?format=json`, { credentials: 'include' })
      const type = res.headers.get('content-type') || ''
      if (res.ok && type.includes('json')) {
        const { url, state } = await res.json()
        if (state) sessionStorage.setItem(OAUTH_STATE_KEY, state)
        window.location.assign(url)
        return
      }
      if (res.redirected) { window.location.assign(res.url); return }
    } catch { /* 네트워크 오류 시 아래 기본 경로로 */ }
    window.location.assign(oauthLoginUrl(provider))
  }

  return (
    <div className="mx-auto flex max-w-6xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5">
      <BrandPanel />

      <div className="flex flex-1 flex-col items-center justify-center px-5 py-10 sm:px-10 lg:py-12">
        <div className="w-full max-w-md animate-fade-in">

          <h1 className="text-2xl font-bold sm:text-3xl">{isSignup ? '계정 만들기' : '다시 오신 것을 환영합니다'}</h1>
          <p className="mt-2 text-sm text-slate-500">
            {isSignup ? '문서를 데이터로 바꿀 계정을 만들어 주세요.' : 'dataquill 문서 데이터 워크스페이스에 로그인하세요.'}
          </p>

          {!isSignup && (
            <div className="mt-7 grid grid-cols-2 gap-3">
              {Object.entries(TEST_ACCOUNTS).map(([kind, account]) => (
                <button
                  key={kind}
                  type="button"
                  onClick={() => quickLogin(kind)}
                  disabled={!!busy}
                  className="group flex items-center gap-3 rounded-xl border border-dashed border-brand-200 bg-brand-50/50 p-3 text-left transition hover:border-brand-400 hover:bg-brand-50 disabled:opacity-60"
                >
                  <span className="flex size-9 items-center justify-center rounded-lg bg-white text-brand-600 shadow-sm">
                    {busy === kind ? <Spinner /> : <FontAwesomeIcon icon={account.icon} />}
                  </span>
                  <span className="min-w-0 leading-tight">
                    <span className="block text-sm font-semibold text-slate-800">{account.label}</span>
                    <span className="block text-xs text-slate-500">{account.desc}</span>
                  </span>
                </button>
              ))}
            </div>
          )}

          <form
            className="mt-7 space-y-4"
            noValidate
            onSubmit={(e) => {
              e.preventDefault()
              submit()
            }}
          >
            {isSignup && (
              <div>
                <label htmlFor="name" className="label">이름</label>
                <div className="relative">
                  <FontAwesomeIcon icon={faUser} className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm text-slate-400" />
                  <input id="name" className="input pl-10" value={form.name} onChange={update('name')} placeholder="홍길동" autoComplete="name" />
                </div>
              </div>
            )}
            <div>
              <label htmlFor="email" className="label">이메일</label>
              <div className="relative">
                <FontAwesomeIcon icon={faEnvelope} className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm text-slate-400" />
                <input
                  id="email"
                  type="email"
                  className={`input pl-10 ${touched && !emailOk ? 'border-rose-400 focus:border-rose-500 focus:ring-rose-100' : ''}`}
                  value={form.email}
                  onChange={update('email')}
                  placeholder="name@company.com"
                  autoComplete="email"
                />
              </div>
            </div>
            <div>
              <label htmlFor="password" className="label">비밀번호</label>
              <div className="relative">
                <FontAwesomeIcon icon={faLock} className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm text-slate-400" />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className={`input px-10 ${touched && !passwordOk ? 'border-rose-400 focus:border-rose-500 focus:ring-rose-100' : ''}`}
                  value={form.password}
                  onChange={update('password')}
                  placeholder="영문 대·소문자, 숫자, 특수문자 8자 이상"
                  autoComplete={isSignup ? 'new-password' : 'current-password'}
                  aria-describedby="password-rules"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute top-1/2 right-2 -translate-y-1/2 rounded-md p-1.5 text-slate-400 hover:text-slate-600"
                  aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 보기'}
                >
                  <FontAwesomeIcon icon={showPassword ? faEyeSlash : faEye} />
                </button>
              </div>
              {(isSignup || form.password) && (
                <ul id="password-rules" className="mt-2.5 flex flex-wrap gap-1.5">
                  {PASSWORD_RULES.map((rule) => {
                    const ok = rule.test(form.password)
                    return (
                      <li
                        key={rule.label}
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs transition ${ok ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}
                      >
                        <FontAwesomeIcon icon={faCheck} className={ok ? '' : 'opacity-30'} />
                        {rule.label}
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>

            {error && (
              <p role="alert" className="flex items-start gap-2 rounded-lg bg-rose-50 px-3 py-2.5 text-sm text-rose-700">
                <FontAwesomeIcon icon={faCircleExclamation} className="mt-0.5" />
                {error}
              </p>
            )}

            <button type="submit" className="btn-primary w-full py-3" disabled={!!busy}>
              {busy === 'form' ? <Spinner /> : <FontAwesomeIcon icon={faArrowRight} />}
              {isSignup ? '회원가입' : '로그인'}
            </button>
          </form>

          <div className="my-7 flex items-center gap-3 text-xs text-slate-400">
            <span className="h-px flex-1 bg-slate-200" />
            또는 소셜 계정으로 계속하기
            <span className="h-px flex-1 bg-slate-200" />
          </div>

          <div className="grid grid-cols-3 gap-3">
            {SOCIAL.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => socialLogin(s.id)}
                disabled={!!busy}
                className={`btn ${s.className}`}
                aria-label={`${s.label}로 로그인`}
              >
                {busy === s.id ? <Spinner /> : s.icon}
                <span className="hidden sm:inline">{s.label}</span>
              </button>
            ))}
          </div>

          <p className="mt-8 text-center text-sm text-slate-500">
            {isSignup ? '이미 계정이 있으신가요?' : '아직 계정이 없으신가요?'}{' '}
            <button
              type="button"
              className="font-semibold text-brand-600 hover:text-brand-700"
              onClick={() => {
                setMode(isSignup ? 'login' : 'signup')
                setError('')
                setTouched(false)
              }}
            >
              {isSignup ? '로그인' : '회원가입'}
            </button>
          </p>

          <div className="mt-8 flex flex-col items-center gap-2 border-t border-slate-100 pt-6 text-xs text-slate-400">
            <p className="flex items-center gap-1.5">
              <FontAwesomeIcon icon={faKeyboard} /> 테스트 계정은 클릭 한 번으로 자동 입력 후 로그인됩니다.
            </p>
            <Link to="/admin/login" className="flex items-center gap-1.5 font-semibold text-slate-500 hover:text-brand-600">
              <FontAwesomeIcon icon={faUserShield} /> 운영 관리자 로그인
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
