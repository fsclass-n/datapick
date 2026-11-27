import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, tokenStore } from '../api/client'
import { ADMIN_ROLES } from '../utils/roles'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(() => Boolean(tokenStore.get()))

  const logout = useCallback(() => {
    tokenStore.clear()
    setUser(null)
  }, [])

  const loginWithToken = useCallback(async (token) => {
    tokenStore.set(token)
    const me = await api('/api/auth/me')
    setUser(me)
    return me
  }, [])

  const login = useCallback(async (email, password) => {
    const { access_token, user: me } = await api('/api/auth/login', { method: 'POST', body: { email, password } })
    tokenStore.set(access_token)
    setUser(me)
    return me
  }, [])

  const adminLogin = useCallback(async (email, password) => {
    const { access_token, user: me } = await api('/api/auth/admin-login', { method: 'POST', body: { email, password } })
    tokenStore.set(access_token)
    setUser(me)
    return me
  }, [])

  const register = useCallback(async (name, email, password) => {
    const { access_token, user: me } = await api('/api/auth/register', { method: 'POST', body: { name, email, password } })
    tokenStore.set(access_token)
    setUser(me)
    return me
  }, [])

  // 요금제 변경 등으로 서버의 사용자 정보가 바뀐 뒤 다시 읽어온다
  const refreshUser = useCallback(async () => {
    const me = await api('/api/auth/me')
    setUser(me)
    return me
  }, [])

  useEffect(() => {
    if (!tokenStore.get()) return
    api('/api/auth/me')
      .then(setUser)
      .catch(logout)
      .finally(() => setLoading(false))
  }, [logout])

  useEffect(() => {
    window.addEventListener('dq:unauthorized', logout)
    return () => window.removeEventListener('dq:unauthorized', logout)
  }, [logout])

  const value = useMemo(
    () => ({
      user,
      loading,
      // 관리자 화면 접근 (운영 관리자 + 테스트 관리자)
      isAdmin: ADMIN_ROLES.includes(user?.role),
      // 전체 CRUD 권한 (ADMIN_EMAIL · ADMIN_PASSWORD 계정으로 로그인한 운영 관리자)
      isOperator: user?.role === 'admin',
      // 테스트 관리자: 조회만 가능
      readOnly: user?.role === 'test_admin',
      login,
      adminLogin,
      register,
      logout,
      loginWithToken,
      refreshUser,
    }),
    [user, loading, login, adminLogin, register, logout, loginWithToken, refreshUser],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
