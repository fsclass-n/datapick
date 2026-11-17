import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, tokenStore } from '../api/client'

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

  const register = useCallback(async (name, email, password) => {
    const { access_token, user: me } = await api('/api/auth/register', { method: 'POST', body: { name, email, password } })
    tokenStore.set(access_token)
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
    () => ({ user, loading, isAdmin: user?.role === 'admin', login, register, logout, loginWithToken }),
    [user, loading, login, register, logout, loginWithToken],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
