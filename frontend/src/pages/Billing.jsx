import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faBuilding,
  faCheck,
  faCircleCheck,
  faCreditCard,
  faLink,
  faPlug,
  faPlugCircleCheck,
  faSpinner,
  faTrashCan,
} from '@fortawesome/free-solid-svg-icons'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { LoadingBlock, PageHeader, Spinner } from '../components/ui'
import { dateTime, won } from '../utils/format'

const PLAN_ORDER = ['free', 'pro', 'business']

export default function Billing() {
  const { refreshUser } = useAuth()
  const toast = useToast()
  const [usage, setUsage] = useState(null)
  const [plans, setPlans] = useState([])
  const [connection, setConnection] = useState(undefined)
  const [error, setError] = useState('')

  const load = () => {
    Promise.all([api('/api/billing/usage'), api('/api/billing/plans'), api('/api/erp/connection')])
      .then(([u, p, c]) => {
        setUsage(u)
        setPlans(p.plans)
        setConnection(c)
      })
      .catch((err) => setError(err.message))
  }
  useEffect(load, [])

  async function subscribe(plan) {
    try {
      const u = await api('/api/billing/subscribe', { method: 'POST', body: { plan } })
      setUsage(u)
      await refreshUser()
      toast(`요금제가 ${u.plan_label}로 변경되었습니다.`, 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  if (error) return <p className="card p-6 text-rose-600">{error}</p>
  if (!usage || connection === undefined) return <LoadingBlock />

  const pct = usage.docs_limit ? Math.min(100, Math.round((usage.docs_used / usage.docs_limit) * 100)) : 0

  return (
    <>
      <PageHeader
        eyebrow="Subscription"
        title="구독 · ERP 연동"
        description="요금제를 관리하고, 우리 회사 ERP 의 접속 정보를 등록해 자동 입력을 연결합니다."
      />

      <section className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <FontAwesomeIcon icon={faCreditCard} />
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-800">
                현재 요금제 <span className="text-brand-700">{usage.plan_label}</span>
                {usage.price > 0 && <span className="text-slate-400"> · 월 {won(usage.price)}</span>}
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                이번 달 문서 처리 {usage.docs_used}건 / {usage.docs_limit}건 (남음 {usage.docs_remaining}건)
              </p>
            </div>
          </div>
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
          <div className={`h-full rounded-full transition-all ${pct >= 90 ? 'bg-rose-500' : 'bg-brand-500'}`} style={{ width: `${pct}%` }} />
        </div>
        {usage.docs_remaining === 0 && (
          <p className="mt-2 text-xs font-medium text-rose-600">이번 달 한도를 모두 사용했습니다. 상위 요금제로 업그레이드하세요.</p>
        )}
      </section>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {PLAN_ORDER.map((id) => {
          const plan = plans.find((p) => p.id === id)
          if (!plan) return null
          const current = usage.plan === id
          return (
            <section key={id} className={`card p-5 ${current ? 'ring-2 ring-brand-500' : ''}`}>
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-900">{plan.label}</h2>
                {current && <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700">사용 중</span>}
              </div>
              <p className="mt-1 text-2xl font-black text-slate-900">
                {plan.price ? won(plan.price) : '무료'}
                {plan.price > 0 && <span className="text-sm font-medium text-slate-400"> /월</span>}
              </p>
              <ul className="mt-4 space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-600">
                    <FontAwesomeIcon icon={faCheck} className="text-xs text-brand-600" /> {f}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                disabled={current}
                onClick={() => subscribe(id)}
                className={`btn mt-5 w-full ${current ? 'btn-secondary opacity-50' : 'btn-primary'}`}
              >
                {current ? '현재 요금제' : plan.price ? `${plan.label}로 변경` : 'Free로 변경'}
              </button>
            </section>
          )
        })}
      </div>

      <section className="card mt-6 p-5">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-gold-100 text-gold-600">
            <FontAwesomeIcon icon={faBuilding} />
          </span>
          <div>
            <h2 className="text-base font-semibold text-slate-900">우리 회사 ERP 연결</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              문서의 'ERP 자동 타이핑'이 이 계정으로 우리 회사 ERP 에 로그인해 전표를 입력합니다. 비밀번호는 암호화해 저장합니다.
            </p>
          </div>
        </div>
        {usage.erp_connection ? (
          <ErpConnectionCard connection={connection} onChange={(c) => setConnection(c)} />
        ) : (
          <p className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
            ERP 연동은 <b>Pro 이상</b> 요금제에서 사용할 수 있습니다. 위에서 Pro 로 변경하면 이 화면에서 접속 정보를 등록할 수 있습니다.
          </p>
        )}
      </section>
    </>
  )
}

function ErpConnectionCard({ connection, onChange }) {
  const toast = useToast()
  const [editing, setEditing] = useState(!connection)
  const [form, setForm] = useState({
    name: connection?.name || '우리 회사 ERP',
    erp_url: connection?.erp_url || '',
    login_url: connection?.login_url || '',
    username: connection?.username || '',
    password: '',
  })
  const [busy, setBusy] = useState('')
  const [testResult, setTestResult] = useState('')

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  async function save(e) {
    e.preventDefault()
    setBusy('save')
    try {
      const saved = await api('/api/erp/connection', {
        method: 'PUT',
        body: { ...form, login_url: form.login_url || null },
      })
      onChange(saved)
      setEditing(false)
      toast('ERP 연결 정보를 저장했습니다.', 'success')
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy('')
    }
  }

  async function test() {
    setBusy('test')
    setTestResult('')
    try {
      const res = await api('/api/erp/connection/test', { method: 'POST' })
      setTestResult(res.detail)
    } catch (err) {
      setTestResult(`실패: ${err.message}`)
    } finally {
      setBusy('')
    }
  }

  async function remove() {
    if (!confirm('저장된 ERP 연결 정보를 삭제할까요?')) return
    await api('/api/erp/connection', { method: 'DELETE' })
    onChange(null)
    setEditing(true)
    toast('ERP 연결을 삭제했습니다.', 'success')
  }

  if (!editing && connection) {
    return (
      <div className="mt-4">
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
          <FontAwesomeIcon icon={faPlugCircleCheck} className="text-emerald-600" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-slate-800">{connection.name}</p>
            <p className="truncate text-xs text-slate-500">
              {connection.erp_url} · 계정 {connection.username} · 최종 수정 {dateTime(connection.updated_at)}
            </p>
          </div>
          <button type="button" className="btn-secondary text-xs" onClick={test} disabled={busy === 'test'}>
            {busy === 'test' ? <FontAwesomeIcon icon={faSpinner} spin /> : <><FontAwesomeIcon icon={faPlug} /> 연결 테스트</>}
          </button>
          <button type="button" className="btn-ghost text-xs" onClick={() => setEditing(true)}>수정</button>
          <button type="button" className="btn-ghost text-xs text-rose-600" onClick={remove}>
            <FontAwesomeIcon icon={faTrashCan} /> 삭제
          </button>
        </div>
        {testResult && (
          <p className={`mt-2 flex items-center gap-2 text-sm ${testResult.startsWith('실패') ? 'text-rose-600' : 'text-emerald-700'}`}>
            <FontAwesomeIcon icon={faCircleCheck} /> {testResult}
          </p>
        )}
      </div>
    )
  }

  return (
    <form onSubmit={save} className="mt-4 grid gap-4 sm:grid-cols-2">
      <div>
        <label className="label" htmlFor="erp-name">연결 이름</label>
        <input id="erp-name" className="input" value={form.name} onChange={set('name')} />
      </div>
      <div>
        <label className="label" htmlFor="erp-user">ERP 아이디</label>
        <input id="erp-user" className="input" value={form.username} onChange={set('username')} required autoComplete="off" />
      </div>
      <div className="sm:col-span-2">
        <label className="label" htmlFor="erp-url">ERP 주소</label>
        <input
          id="erp-url" className="input" value={form.erp_url} onChange={set('erp_url')} required
          placeholder="https://datapick-erp.onrender.com/"
        />
        <p className="mt-1 text-xs text-slate-400">전표 입력 화면 주소. 로그인 주소는 비우면 자동으로 /login 을 사용합니다.</p>
      </div>
      <div>
        <label className="label" htmlFor="erp-login-url">로그인 주소 (선택)</label>
        <input id="erp-login-url" className="input" value={form.login_url} onChange={set('login_url')} placeholder="https://.../login" />
      </div>
      <div>
        <label className="label" htmlFor="erp-pw">ERP 비밀번호</label>
        <input id="erp-pw" type="password" className="input" value={form.password} onChange={set('password')} required autoComplete="new-password" />
      </div>
      <div className="flex items-center gap-2 sm:col-span-2">
        <button type="submit" className="btn-primary" disabled={busy === 'save'}>
          {busy === 'save' ? <Spinner /> : <><FontAwesomeIcon icon={faLink} /> 연결 저장</>}
        </button>
        {connection && <button type="button" className="btn-ghost" onClick={() => setEditing(false)}>취소</button>}
      </div>
    </form>
  )
}
