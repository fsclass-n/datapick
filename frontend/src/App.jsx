import { lazy, useEffect, useRef, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCompass } from '@fortawesome/free-solid-svg-icons'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import { EmptyState, LoadingBlock } from './components/ui'
import Login from './pages/Login'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Documents = lazy(() => import('./pages/Documents'))
const AdminUsers = lazy(() => import('./pages/admin/AdminUsers'))
const AdminMonitoring = lazy(() => import('./pages/admin/AdminMonitoring'))

function RequireAuth({ admin = false, children }) {
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
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="card max-w-sm p-6 text-center">
        <p className="text-rose-600">{error}</p>
        <Link to="/login" className="btn-primary mt-4">로그인으로 돌아가기</Link>
      </div>
    </div>
  )
}

function NotFound() {
  return (
    <div className="card">
      <EmptyState icon={faCompass} title="페이지를 찾을 수 없습니다" action={<Link to="/dashboard" className="btn-primary"><FontAwesomeIcon icon={faCompass} /> 대시보드로</Link>} />
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/admin/users" element={<RequireAuth admin><AdminUsers /></RequireAuth>} />
        <Route path="/admin/monitoring" element={<RequireAuth admin><AdminMonitoring /></RequireAuth>} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
