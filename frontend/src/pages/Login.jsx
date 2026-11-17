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
  faFileInvoice,
  faKeyboard,
  faLock,
  faRobot,
  faUser,
  faUserShield,
  faWandMagicSparkles,
} from '@fortawesome/free-solid-svg-icons'
import { faGoogle } from '@fortawesome/free-brands-svg-icons'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { IS_MOCK, api, oauthLoginUrl } from '../api/client'
import Logo from '../components/layout/Logo'
import { Spinner } from '../components/ui'
import { PASSWORD_RULES, isValidEmail, isValidPassword } from '../utils/format'

const TEST_ACCOUNTS = {
  user: { email: 'user@dataquill.io', password: 'User1234!', label: '일반 사용자', desc: '문서 업로드 · RPA 체험', icon: faUser },
  admin: { email: 'admin@dataquill.io', password: 'Admin1234!', label: '테스트 관리자', desc: '관리자 화면 · 읽기 전용', icon: faEyeIcon },
}

const SOCIAL = [
  { id: 'google', label: 'Google', className: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50', icon: <FontAwesomeIcon icon={faGoogle} className="text-[#4285F4]" /> },
  { id: 'naver', label: '네이버', className: 'bg-naver text-white hover:brightness-95', icon: <span className="font-heading text-base leading-none font-black">N</span> },
  { id: 'kakao', label: '카카오', className: 'bg-kakao text-[#191919] hover:brightness-95', icon: <FontAwesomeIcon icon={faComment} /> },
]

const PIPELINE = [
  { icon: faFileInvoice, title: '비정형 문서 수집', desc: 'PDF 영수증 · 이메일 · 스캔 이미지' },
  { icon: faWandMagicSparkles, title: 'OCR + Gemini 해석', desc: '거래처 · 금액 · 날짜 · 품목 자동 정형화' },
  { icon: faRobot, title: 'RPA 자동 타이핑', desc: 'ERP 전표 · 엑셀 원장에 자동 적재' },
]

function BrandPanel() {
  return (
    <div className="relative hidden overflow-hidden bg-brand-900 lg:flex lg:w-[46%] lg:flex-col lg:justify-between lg:gap-10 lg:p-10 xl:p-12">
      <div className="absolute -top-32 -left-32 size-96 rounded-full bg-brand-600/40 blur-3xl" />
      <div className="absolute -right-24 bottom-0 size-96 rounded-full bg-fuchsia-500/20 blur-3xl" />
      <div
        className="absolute inset-0 opacity-[0.07]"
        style={{ backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)', backgroundSize: '40px 40px' }}
      />

      <div className="relative">
        <Logo light />
      </div>

      <div className="relative">
        <h2 className="text-3xl leading-tight font-bold text-white xl:text-4xl">
          서류는 AI가 읽고,
          <br />
          입력은 <span className="bg-gradient-to-r from-brand-200 to-fuchsia-300 bg-clip-text text-transparent">로봇이 합니다.</span>
        </h2>
        <p className="mt-5 max-w-md text-brand-100/80">
          반복되는 데이터 입력 업무를 자동화하세요. 영수증 한 장부터 월말 정산까지, dataquill 이 ERP 와 엑셀에 정확하게 옮겨 드립니다.
        </p>

        <ol className="mt-10 space-y-3">
          {PIPELINE.map((step, i) => (
            <li
              key={step.title}
              className="flex animate-float items-center gap-4 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur"
              style={{ animationDelay: `${i * 0.6}s` }}
            >
              <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-white/10 text-brand-200">
                <FontAwesomeIcon icon={step.icon} />
              </span>
              <div>
                <p className="font-heading font-semibold text-white">
                  <span className="mr-2 text-brand-300">0{i + 1}</span>
                  {step.title}
                </p>
                <p className="text-sm text-brand-100/70">{step.desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="relative grid grid-cols-3 gap-4 border-t border-white/10 pt-8 text-white">
        {[
          ['PDF·IMG·EML', '지원 문서 형식'],
          ['Gemini', 'AI 해석 엔진'],
          ['ERP·Excel', 'RPA 적재 대상'],
        ].map(([value, label]) => (
          <div key={label}>
            <p className="font-heading text-lg font-bold xl:text-xl">{value}</p>
            <p className="text-xs text-brand-100/70">{label}</p>
          </div>
        ))}
      </div>
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

  function socialLogin(provider) {
    if (IS_MOCK) return toast('소셜 로그인은 백엔드(API) 연결 후 사용할 수 있습니다.', 'info')
    if (providers[provider] === false) return setError(`${SOCIAL.find((s) => s.id === provider).label} 로그인이 아직 설정되지 않았습니다.`)
    setBusy(provider)
    window.location.assign(oauthLoginUrl(provider))
  }

  return (
    <div className="mx-auto flex max-w-6xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5">
      <BrandPanel />

      <div className="flex flex-1 flex-col items-center justify-center px-5 py-10 sm:px-10 lg:py-12">
        <div className="w-full max-w-md animate-fade-in">

          <h1 className="text-2xl font-bold sm:text-3xl">{isSignup ? '계정 만들기' : '다시 오신 것을 환영합니다'}</h1>
          <p className="mt-2 text-sm text-slate-500">
            {isSignup ? '업무 자동화를 시작할 계정을 만들어 주세요.' : 'AI 데이터 입력 자동화 워크스페이스에 로그인하세요.'}
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
              <FontAwesomeIcon icon={faUserShield} /> 운영 관리자 로그인 (관리자 토큰)
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
