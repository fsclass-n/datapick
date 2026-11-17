import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faCircleExclamation, faEye, faEyeSlash, faKey, faUserShield } from '@fortawesome/free-solid-svg-icons'
import { IS_MOCK, api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Spinner } from '../components/ui'

export default function AdminLogin() {
  const { user, isOperator, adminLogin } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [token, setToken] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(IS_MOCK ? 'Mock 모드에서는 운영 관리자 로그인을 사용할 수 없습니다. 백엔드(API)를 연결해 주세요.' : '')
  const [enabled, setEnabled] = useState(!IS_MOCK)

  useEffect(() => {
    if (IS_MOCK) return
    api('/api/auth/providers')
      .then((p) => {
        if (p.admin_token === false) {
          setEnabled(false)
          setError('서버에 ADMIN_TOKEN 이 설정되지 않아 운영 관리자 로그인이 비활성화되어 있습니다.')
        }
      })
      .catch(() => {})
  }, [])

  if (isOperator) return <Navigate to="/admin/monitoring" replace />

  async function submit(e) {
    e.preventDefault()
    if (!token.trim()) return setError('관리자 토큰을 입력해 주세요.')
    setBusy(true)
    setError('')
    try {
      await adminLogin(token.trim())
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
          서버 환경 변수 <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[13px] text-brand-700">ADMIN_TOKEN</code> 으로 인증합니다.
          인증되면 모든 데이터의 생성 · 수정 · 삭제와 회원 권한 변경을 할 수 있습니다.
        </p>
        {user && (
          <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2.5 text-caption text-slate-600">
            현재 <strong>{user.name}</strong>({user.email}) 계정으로 로그인되어 있습니다. 인증하면 운영 관리자 계정으로 전환됩니다.
          </p>
        )}

        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          <div>
            <label htmlFor="admin-token" className="label">관리자 토큰</label>
            <div className="relative">
              <FontAwesomeIcon icon={faKey} className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm text-slate-400" />
              <input
                id="admin-token"
                type={show ? 'text' : 'password'}
                className="input px-10 font-mono"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                disabled={!enabled}
                placeholder="••••••••••••••••"
              />
              <button
                type="button"
                onClick={() => setShow((v) => !v)}
                className="absolute top-1/2 right-2 -translate-y-1/2 rounded-md p-1.5 text-slate-400 hover:text-slate-600"
                aria-label={show ? '토큰 숨기기' : '토큰 보기'}
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
            {busy ? <Spinner /> : <FontAwesomeIcon icon={faUserShield} />} 관리자 인증
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
