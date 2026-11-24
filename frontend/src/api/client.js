import { mockRequest } from './mock'

export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
export const IS_MOCK = !API_URL
const TOKEN_KEY = 'dq_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

function errorMessage(body, status) {
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ')
  return `요청을 처리하지 못했습니다. (${status})`
}

export async function api(path, { method = 'GET', body, raw = false } = {}) {
  const token = tokenStore.get()
  if (IS_MOCK) {
    try {
      return await mockRequest(path, { method, body, token })
    } catch (err) {
      if (err.status === 401) window.dispatchEvent(new Event('dq:unauthorized'))
      throw new ApiError(err.message, err.status)
    }
  }

  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const isForm = body instanceof FormData
  if (body && !isForm) headers['Content-Type'] = 'application/json'

  let res
  try {
    res = await fetch(`${API_URL}${path}`, { method, headers, body: isForm ? body : body && JSON.stringify(body) })
  } catch {
    throw new ApiError('서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.', 0)
  }
  if (res.status === 401 && token) window.dispatchEvent(new Event('dq:unauthorized'))
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw new ApiError(errorMessage(data, res.status), res.status)
  }
  if (raw) return res.blob()
  return res.status === 204 ? null : res.json()
}

export async function download(path, filename) {
  const blob = await api(path, { raw: true })
  const url = URL.createObjectURL(blob)
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}

export function oauthLoginUrl(provider) {
  return `${API_URL}/api/auth/oauth/${provider}/start`
}
