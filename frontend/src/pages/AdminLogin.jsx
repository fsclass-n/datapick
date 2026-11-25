import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faCircleExclamation, faEnvelope, faEye, faEyeSlash, faKey, faUserShield } from '@fortawesome/free-solid-svg-icons'
import { IS_MOCK, api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Spinner } from '../components/ui'

export default function AdminLogin() {
  const { user, isOperator, adminLogin } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(IS_MOCK ? 'Mock 모드에서는 운영 관리자 로그인을 사용할 수 없습니다. 백엔드(API)를 연결해 주세요.' : '')
  const [enabled, setEnabled] = useState(!IS_MOCK)

  useEffect(() => {
    if (IS_MOCK) return
    api('/api/auth/providers')
      .then((p) => {
        if (p.admin_login === false) {
          setEnabled(false)
          setError('서버에 ADMIN_EMAIL · ADMIN_PASSWORD 가 설정되지 않아 운영 관리자 로그인이 비활성화되어 있습니다.')
        }
      })
      .catch(() => {})
  }, [])

  if (isOperator) return <Navigate to="/admin/monitoring" replace />

  async function submit(e) {
    e.preventDefault()
    if (!email.trim() || !password) return setError('이메일과 비밀번호를 입력해 주세요.')
    setBusy(true)
    setError('')
    try {
      await adminLogin(email.trim(), password)
      toast('운영 관리자로 로그인했습니다.', 'success')
      navigate('/admin/monitoring', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="card p-8">
        <span className="flex size-12 items-center justify-center rounded-xl bg-brand-900 text-white">
          <FontAwesomeIcon icon={faUserShield} />
        </span>
        <h1 className="mt-5 text-2xl font-bold">운영 관리자 로그인</h1>
        <p className="mt-2 text-body text-slate-500">
          서버 환경 변수 <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[13px] text-brand-700">ADMIN_EMAIL</code> ·{' '}
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[13px] text-brand-700">ADMIN_PASSWORD</code> 에 등록된 계정으로 로그인합니다.
          인증되면 모든 데이터의 생성 · 수정 · 삭제와 회원 권한 변경을 할 수 있습니다.
        </p>
        {user && (
          <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2.5 text-caption text-slate-600">
            현재 <strong>{user.name}</strong>({user.email}) 계정으로 로그인되어 있습니다. 인증하면 운영 관리자 계정으로 전환됩니다.
          </p>
        )}

        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          <div>
            <label htmlFor="admin-email" className="label">관리자 이메일</label>
            <div className="relative">
              <FontAwesomeIcon icon={faEnvelope} className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm text-slate-400" />
              <input
                id="admin-email"
                type="email"
                className="input px-10"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                spellCheck={false}
                disabled={!enabled}
                placeholder="operator@datapick.io"
              />
            </div>
          </div>
          <div>
            <label htmlFor="admin-password" className="label">관리자 비밀번호</label>
            <div className="relative">
              <FontAwesomeIcon icon={faKey} className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm text-slate-400" />
              <input
                id="admin-password"
                type={show ? 'text' : 'password'}
                className="input px-10"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                disabled={!enabled}
                placeholder="••••••••••••••••"
              />
              <button
                type="button"
                onClick={() => setShow((v) => !v)}
                className="absolute top-1/2 right-2 -translate-y-1/2 rounded-md p-1.5 text-slate-400 hover:text-slate-600"
                aria-label={show ? '비밀번호 숨기기' : '비밀번호 보기'}
              >
                <FontAwesomeIcon icon={show ? faEyeSlash : faEye} />
              </button>
            </div>
          </div>
          {error && (
            <p role="alert" className="flex items-start gap-2 rounded-lg bg-rose-50 px-3 py-2.5 text-sm text-rose-700">
              <FontAwesomeIcon icon={faCircleExclamation} className="mt-0.5" />
              {error}
            </p>
          )}
          <button type="submit" className="btn-primary w-full py-3" disabled={busy || !enabled}>
            {busy ? <Spinner /> : <FontAwesomeIcon icon={faUserShield} />} 관리자 로그인
          </button>
        </form>
        <p className="mt-4 text-caption text-slate-400">5회 연속 실패하면 10분 동안 인증이 차단됩니다.</p>
      </div>
      <Link to="/login" className="mt-6 flex items-center justify-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-800">
        <FontAwesomeIcon icon={faArrowLeft} /> 일반 로그인으로 돌아가기
      </Link>
    </div>
  )
}
