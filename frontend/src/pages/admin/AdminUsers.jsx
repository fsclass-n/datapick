import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faMagnifyingGlass, faUserGear, faUserShield, faUsers } from '@fortawesome/free-solid-svg-icons'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { Badge, EmptyState, LoadingBlock, PageHeader, Spinner, StatCard } from '../../components/ui'
import { PROVIDER_LABELS, dateOnly, dateTime } from '../../utils/format'
import { READ_ONLY_HINT, TEST_ACCOUNT_EMAILS } from '../../utils/roles'

function RoleToggle({ user, self, busy, readOnly, onChange }) {
  const isAdmin = user.role === 'admin'
  const fixed = TEST_ACCOUNT_EMAILS.includes(user.email)
  const reason = readOnly ? READ_ONLY_HINT : fixed ? '공개 테스트 계정의 권한은 고정되어 있습니다.' : self ? '본인의 권한은 변경할 수 없습니다.' : null
  return (
    <button
      type="button"
      role="switch"
      aria-checked={isAdmin}
      aria-label={`${user.name} 관리자 권한`}
      disabled={!!reason || busy}
      onClick={() => onChange(user, isAdmin ? 'user' : 'admin')}
      title={reason || (isAdmin ? '일반 사용자로 변경' : '운영 관리자로 변경')}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition disabled:cursor-not-allowed disabled:opacity-40 ${isAdmin ? 'bg-brand-600' : 'bg-slate-300'}`}
    >
      <span className={`inline-flex size-5 items-center justify-center rounded-full bg-white text-[10px] text-brand-600 shadow transition ${isAdmin ? 'translate-x-5.5' : 'translate-x-0.5'}`}>
        {busy && <Spinner />}
      </span>
    </button>
  )
}

export default function AdminUsers() {
  const { user: me, readOnly } = useAuth()
  const toast = useToast()
  const [users, setUsers] = useState(null)
  const [query, setQuery] = useState('')
  const [role, setRole] = useState('')
  const [busyId, setBusyId] = useState(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      const params = new URLSearchParams({ q: query, role })
      api(`/api/admin/users?${params}`).then(setUsers).catch((err) => toast(err.message, 'error'))
    }, 250)
    return () => clearTimeout(timer)
  }, [query, role, toast])

  async function changeRole(user, next) {
    const label = next === 'admin' ? '관리자' : '일반 사용자'
    if (!window.confirm(`${user.name}(${user.email}) 님의 권한을 ${label}(으)로 변경할까요?`)) return
    setBusyId(user.id)
    try {
      const updated = await api(`/api/admin/users/${user.id}/role`, { method: 'PATCH', body: { role: next } })
      setUsers((list) => list.map((u) => (u.id === updated.id ? { ...u, role: updated.role } : u)))
      toast(`${user.name} 님의 권한을 ${label}(으)로 변경했습니다.`, 'success')
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusyId(null)
    }
  }

  const admins = users?.filter((u) => u.role !== 'user').length ?? 0

  return (
    <>
      <PageHeader eyebrow="Admin" title="회원 관리" description="가입한 사용자를 조회하고 일반 사용자 ↔ 관리자 권한을 변경합니다." />

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <StatCard icon={faUsers} label="조회된 회원" value={users ? `${users.length}명` : '-'} />
        <StatCard icon={faUserShield} label="관리자 (운영 + 테스트)" value={users ? `${admins}명` : '-'} tone="amber" />
        <StatCard icon={faUserGear} label="일반 사용자" value={users ? `${users.length - admins}명` : '-'} tone="green" />
      </div>

      <section className="card overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <FontAwesomeIcon icon={faMagnifyingGlass} className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm text-slate-400" />
            <input className="input pl-10" placeholder="이름 또는 이메일 검색" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <select className="input sm:w-40" value={role} onChange={(e) => setRole(e.target.value)} aria-label="권한 필터">
            <option value="">전체 권한</option>
            <option value="admin">운영 관리자</option>
            <option value="test_admin">테스트 관리자</option>
            <option value="user">일반 사용자</option>
          </select>
        </div>

        {!users ? (
          <LoadingBlock />
        ) : !users.length ? (
          <EmptyState icon={faUsers} title="조건에 맞는 회원이 없습니다" />
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs font-semibold text-slate-500">
                  <tr>
                    <th className="px-5 py-3 text-left">회원</th>
                    <th className="px-5 py-3 text-left">가입 방식</th>
                    <th className="px-5 py-3 text-right">처리 문서</th>
                    <th className="px-5 py-3 text-left">가입일</th>
                    <th className="px-5 py-3 text-left">최근 로그인</th>
                    <th className="px-5 py-3 text-left">권한</th>
                    <th className="px-5 py-3 text-center">관리자 지정</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/60">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-3">
                          <span className="flex size-9 items-center justify-center rounded-full bg-brand-50 font-heading font-semibold text-brand-700">{u.name.slice(0, 1)}</span>
                          <div>
                            <p className="font-medium text-slate-800">{u.name} {u.id === me.id && <span className="text-xs text-brand-600">(나)</span>}</p>
                            <p className="text-xs text-slate-500">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-slate-600">{PROVIDER_LABELS[u.provider] || u.provider}</td>
                      <td className="px-5 py-3.5 text-right font-medium">{u.document_count}</td>
                      <td className="px-5 py-3.5 text-slate-600">{dateOnly(u.created_at)}</td>
                      <td className="px-5 py-3.5 text-slate-600">{dateTime(u.last_login_at)}</td>
                      <td className="px-5 py-3.5"><Badge status={u.role} /></td>
                      <td className="px-5 py-3.5 text-center">
                        <RoleToggle user={u} self={u.id === me.id} busy={busyId === u.id} readOnly={readOnly} onChange={changeRole} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <ul className="divide-y divide-slate-100 md:hidden">
              {users.map((u) => (
                <li key={u.id} className="flex items-center gap-3 p-4">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-50 font-heading font-semibold text-brand-700">{u.name.slice(0, 1)}</span>
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-2 font-medium text-slate-800">{u.name} <Badge status={u.role} /></p>
                    <p className="truncate text-xs text-slate-500">{u.email} · {PROVIDER_LABELS[u.provider]} · 문서 {u.document_count}</p>
                  </div>
                  <RoleToggle user={u} self={u.id === me.id} busy={busyId === u.id} readOnly={readOnly} onChange={changeRole} />
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  )
}
