import { lazy, useEffect, useRef, useState } from 'react'
import { Link, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCompass } from '@fortawesome/free-solid-svg-icons'
import { useAuth } from './context/AuthContext'
import SiteLayout, { PageContainer } from './components/layout/SiteLayout'
import { EmptyState, LoadingBlock } from './components/ui'
import Home from './pages/Home'
import Login from './pages/Login'

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
  const [error, setError] = useState(token ? '' : '로그인 토큰을 받지 못했습니다.')
  const handled = useRef(false)

  useEffect(() => {
    window.history.replaceState(null, '', window.location.pathname)
    if (handled.current || !token) return
    handled.current = true
    loginWithToken(token)
      .then(() => navigate('/dashboard', { replace: true }))
      .catch((err) => setError(err.message))
  }, [token, loginWithToken, navigate])

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
