import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight,
  faBrain,
  faCloudArrowUp,
  faCoins,
  faInbox,
  faRobot,
  faTriangleExclamation,
  faUserGear,
  faWandMagicSparkles,
} from '@fortawesome/free-solid-svg-icons'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Badge, EmptyState, LoadingBlock, PageHeader, Spinner, StatCard } from '../components/ui'
import { PROVIDER_LABELS, SOURCE_LABELS, compactWon, dateTime, won } from '../utils/format'
import { sourceIcon } from '../utils/icons'
import { TOOL_LIST, TOOLS } from '../utils/tools'

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [analyses, setAnalyses] = useState([])
  const [error, setError] = useState('')
  const [withdrawOpen, setWithdrawOpen] = useState(false)

  useEffect(() => {
    Promise.all([api('/api/dashboard'), api('/api/documents'), api('/api/tools/analyses')])
      .then(([s, docs, list]) => {
        setStats(s)
        setRecent(docs.slice(0, 6))
        setAnalyses(list.slice(0, 5))
      })
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="card p-6 text-rose-600">{error}</p>
  if (!stats) return <LoadingBlock />

  const { documents: d, rpa } = stats
  const sources = Object.entries(d.by_source).sort((a, b) => b[1] - a[1])

  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title={`안녕하세요, ${user.name}님`}
        description="AI 도구로 문서를 분석하거나, 영수증 · 청구서를 ERP 와 엑셀에 자동으로 입력하세요."
        actions={
          <Link to="/documents" className="btn-primary">
            <FontAwesomeIcon icon={faCloudArrowUp} /> 문서 업로드
          </Link>
        }
      />

      <section className="mb-8">
        <h2 className="mb-3 flex items-center gap-2 text-base font-semibold">
          <FontAwesomeIcon icon={faWandMagicSparkles} className="text-gold-500" /> AI 도구
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          {TOOL_LIST.map((tool) => (
            <Link key={tool.id} to={tool.path} className="group relative overflow-hidden rounded-2xl bg-ink p-5 text-white transition hover:-translate-y-0.5 hover:shadow-lg hover:shadow-ink/20">
              <img src={tool.image.replace('.webp', '-sm.webp')} alt="" className="absolute inset-0 size-full object-cover opacity-25 transition duration-500 group-hover:scale-105 group-hover:opacity-35" />
              <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/85 to-ink/40" />
              <div className="relative flex items-start gap-4">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-white text-lg">
                  <FontAwesomeIcon icon={tool.icon} className={tool.accent.icon} />
                </span>
                <div className="min-w-0">
                  <p className="font-heading font-semibold">{tool.name}</p>
                  <p className="mt-1 text-sm text-white/65">{tool.headline}</p>
                  <p className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-gold-400">
                    샘플로 바로 체험 <FontAwesomeIcon icon={faArrowRight} className="transition group-hover:translate-x-1" />
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <h2 className="mb-3 text-base font-semibold">영수증 · 청구서 자동 입력 (최근 14일)</h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={faInbox} label="처리 문서" value={`${d.total}건`} sub={`완료 ${d.parsed} · 실패 ${d.failed}`} />
        <StatCard icon={faBrain} label="AI 파싱 성공률" value={`${d.success_rate}%`} sub={d.avg_confidence ? `평균 신뢰도 ${Math.round(d.avg_confidence * 100)}%` : '데이터 없음'} tone="green" />
        <StatCard icon={faRobot} label="RPA 자동 입력" value={`${rpa.success}건`} sub={`성공률 ${rpa.success_rate}% · 실패 ${rpa.failed}`} tone="amber" />
        <StatCard icon={faCoins} label="정형화된 거래 금액" value={compactWon(d.amount_total)} sub="파싱 완료 문서 합계" tone="slate" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <section className="card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold">일별 처리 추이</h2>
            <div className="flex gap-3 text-xs text-slate-500">
              <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-full bg-brand-600" />파싱 성공</span>
              <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-full bg-rose-400" />실패</span>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stats.daily} margin={{ left: -20, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="gParsed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#284578" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#284578" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }} />
                <Area type="monotone" dataKey="parsed" name="파싱 성공" stroke="#284578" strokeWidth={2} fill="url(#gParsed)" />
                <Area type="monotone" dataKey="failed" name="실패" stroke="#fb7185" strokeWidth={2} fill="transparent" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="card p-5">
          <h2 className="mb-4 text-base font-semibold">문서 소스 분포</h2>
          {sources.length ? (
            <ul className="space-y-4">
              {sources.map(([source, n]) => (
                <li key={source}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 text-slate-700">
                      <FontAwesomeIcon icon={sourceIcon(source)} className="w-4 text-slate-400" />
                      {SOURCE_LABELS[source] || source}
                    </span>
                    <span className="font-semibold text-slate-900">{n}건</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${(n / d.total) * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">아직 처리한 문서가 없습니다.</p>
          )}
        </section>
      </div>

      <section className="card mt-6 overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold">최근 AI 분석</h2>
        </div>
        {analyses.length ? (
          <ul className="divide-y divide-slate-100">
            {analyses.map((a) => {
              const tool = TOOLS[a.kind]
              return (
                <li key={a.id}>
                  <Link to={`${tool.path}?id=${a.id}`} className="flex items-center gap-4 px-5 py-3.5 transition hover:bg-slate-50">
                    <span className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${tool.accent.soft} ${tool.accent.icon}`}>
                      <FontAwesomeIcon icon={tool.icon} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-800">{a.title}</p>
                      <p className="truncate text-xs text-slate-500">{tool.name} · {dateTime(a.created_at)}</p>
                    </div>
                    <FontAwesomeIcon icon={faArrowRight} className="text-xs text-slate-300" />
                  </Link>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="px-5 py-8 text-center text-sm text-slate-500">아직 AI 분석 기록이 없습니다. 위의 도구에서 샘플로 바로 체험해 보세요.</p>
        )}
      </section>

      <section className="card mt-6 overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold">최근 처리 문서</h2>
          <Link to="/documents" className="text-sm font-semibold text-brand-700 hover:text-ink">
            전체 보기 <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
          </Link>
        </div>
        {recent.length ? (
          <ul className="divide-y divide-slate-100">
            {recent.map((doc) => (
              <li key={doc.id}>
                <Link to={`/documents?id=${doc.id}`} className="flex items-center gap-4 px-5 py-3.5 transition hover:bg-slate-50">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
                    <FontAwesomeIcon icon={sourceIcon(doc.source_type)} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">{doc.parsed?.vendor || doc.filename}</p>
                    <p className="truncate text-xs text-slate-500">{doc.filename} · {dateTime(doc.created_at)}</p>
                  </div>
                  <span className="hidden text-sm font-semibold text-slate-800 sm:block">{won(doc.parsed?.total_amount)}</span>
                  <Badge status={doc.status} />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={faInbox}
            title="처리한 문서가 없습니다"
            description="영수증 PDF나 이메일 본문을 업로드해 자동화를 시작하세요."
            action={<Link to="/documents" className="btn-primary">첫 문서 업로드</Link>}
          />
        )}
      </section>

      <section className="card mt-6">
        <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
              <FontAwesomeIcon icon={faUserGear} />
            </span>
            <div>
              <p className="text-sm font-medium text-slate-800">
                {user.email}
                <span className="text-slate-400"> · {PROVIDER_LABELS[user.provider] || user.provider}</span>
              </p>
              <p className="mt-0.5 text-xs text-slate-500">가입일 {dateTime(user.created_at)}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/billing" className="text-sm font-semibold text-brand-700 transition hover:text-ink">
              구독 · ERP 연동
            </Link>
            <button type="button" onClick={() => setWithdrawOpen(true)} className="text-sm font-semibold text-rose-600 transition hover:text-rose-700">
              회원 탈퇴
            </button>
          </div>
        </div>
      </section>

      {withdrawOpen && <WithdrawModal user={user} onClose={() => setWithdrawOpen(false)} />}
    </>
  )
}

function WithdrawModal({ user, onClose }) {
  const { logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const needsPassword = ['local', 'admin'].includes(user.provider)

  async function submit(e) {
    e.preventDefault()
    if (needsPassword && !password) return setError('비밀번호를 입력해 주세요.')
    setBusy(true)
    setError('')
    try {
      await api('/api/auth/me', { method: 'DELETE', body: { password: password || null } })
      logout()
      toast('탈퇴가 완료되었습니다. 이용해 주셔서 감사합니다.', 'success')
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="withdraw-title">
      <form onSubmit={submit} className="card w-full max-w-md p-6">
        <h3 id="withdraw-title" className="flex items-center gap-2 text-lg font-bold text-rose-600">
          <FontAwesomeIcon icon={faTriangleExclamation} /> 회원 탈퇴
        </h3>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          계정과 함께 <b>업로드한 문서, AI 분석 기록, RPA 작업 이력, 엑셀 원장</b>이 모두 삭제되며 되돌릴 수 없습니다.
        </p>
        {needsPassword && (
          <div className="mt-4">
            <label htmlFor="withdraw-pw" className="label">비밀번호 확인</label>
            <input
              id="withdraw-pw"
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="현재 비밀번호를 입력하세요"
              autoComplete="current-password"
            />
          </div>
        )}
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>취소</button>
          <button type="submit" className="btn bg-rose-600 text-white hover:bg-rose-700" disabled={busy}>
            {busy ? <Spinner /> : '탈퇴하기'}
          </button>
        </div>
      </form>
    </div>
  )
}
