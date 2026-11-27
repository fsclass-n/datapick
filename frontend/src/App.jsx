import { lazy, useEffect, useRef, useState } from 'react'
import { Link, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCompass } from '@fortawesome/free-solid-svg-icons'
import { useAuth } from './context/AuthContext'
import { OAUTH_STATE_KEY, api } from './api/client'
import SiteLayout, { PageContainer } from './components/layout/SiteLayout'
import { EmptyState, LoadingBlock } from './components/ui'
import Home from './pages/Home'
import Login from './pages/Login'

const Billing = lazy(() => import('./pages/Billing'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Documents = lazy(() => import('./pages/Documents'))
const QuoteCompare = lazy(() => import('./pages/tools/QuoteCompare'))
const ContractReview = lazy(() => import('./pages/tools/ContractReview'))
const HealthTrend = lazy(() => import('./pages/tools/HealthTrend'))
const AdminUsers = lazy(() => import('./pages/admin/AdminUsers'))
const AdminMonitoring = lazy(() => import('./pages/admin/AdminMonitoring'))
const AdminLogin = lazy(() => import('./pages/AdminLogin'))
const Terms = lazy(() => import('./pages/Policy').then((m) => ({ default: m.Terms })))
const Privacy = lazy(() => import('./pages/Policy').then((m) => ({ default: m.Privacy })))

function RequireAuth({ admin = false, children = <Outlet /> }) {
  const { user, loading, isAdmin } = useAuth()
  const location = useLocation()
  if (loading) return <LoadingBlock />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  if (admin && !isAdmin) return <Navigate to="/dashboard" replace />
  return children
}

function OAuthCallback() {
  const { loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('token'))
  const [handoff] = useState(() => {
    const p = new URLSearchParams(window.location.search)
    return p.get('provider') && p.get('code') && p.get('state')
      ? { provider: p.get('provider'), code: p.get('code'), state: p.get('state') }
      : null
  })
  const [error, setError] = useState(token || handoff ? '' : '로그인 토큰을 받지 못했습니다.')
  const handled = useRef(false)

  useEffect(() => {
    window.history.replaceState(null, '', window.location.pathname)
    if (handled.current) return
    handled.current = true
    if (handoff) {
      // 쿠키 없이 시작한 흐름: 이 탭의 sessionStorage 에 저장해 둔 state 와 대조한 뒤 서버 교환
      const expected = sessionStorage.getItem(OAUTH_STATE_KEY)
      sessionStorage.removeItem(OAUTH_STATE_KEY)
      if (expected !== handoff.state) {
        const timer = setTimeout(() => setError('로그인 요청이 만료되었거나 올바르지 않습니다. 다시 시도해 주세요.'))
        return () => clearTimeout(timer)
      }
      api(`/api/auth/oauth/${handoff.provider}/exchange`, { method: 'POST', body: { code: handoff.code, state: handoff.state } })
        .then(({ access_token }) => loginWithToken(access_token))
        .then(() => navigate('/dashboard', { replace: true }))
        .catch((err) => setError(err.message))
      return
    }
    if (!token) return
    loginWithToken(token)
      .then(() => navigate('/dashboard', { replace: true }))
      .catch((err) => setError(err.message))
  }, [token, handoff, loginWithToken, navigate])

  if (!error) return <LoadingBlock />
  return (
    <div className="card mx-auto max-w-sm p-6 text-center">
      <p className="text-rose-600">{error}</p>
      <Link to="/login" className="btn-primary mt-4">로그인으로 돌아가기</Link>
    </div>
  )
}

function NotFound() {
  return (
    <div className="card">
      <EmptyState icon={faCompass} title="페이지를 찾을 수 없습니다" action={<Link to="/" className="btn-primary"><FontAwesomeIcon icon={faCompass} /> 메인으로</Link>} />
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      {/* 모든 페이지 공통: 글로벌 헤더 + 푸터 */}
      <Route element={<SiteLayout />}>
        {/* 최초 접속은 항상 메인(랜딩) 페이지 */}
        <Route index element={<Home />} />
        <Route element={<PageContainer />}>
          <Route path="/login" element={<Login />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/oauth/callback" element={<OAuthCallback />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route element={<RequireAuth />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/billing" element={<Billing />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/tools/quotes" element={<QuoteCompare />} />
            <Route path="/tools/contract" element={<ContractReview />} />
            <Route path="/tools/health" element={<HealthTrend />} />
            <Route element={<RequireAuth admin />}>
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/monitoring" element={<AdminMonitoring />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  )
}
