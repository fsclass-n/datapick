import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight,
  faBrain,
  faCloudArrowUp,
  faCoins,
  faInbox,
  faRobot,
} from '@fortawesome/free-solid-svg-icons'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Badge, EmptyState, LoadingBlock, PageHeader, StatCard } from '../components/ui'
import { SOURCE_LABELS, compactWon, dateTime, won } from '../utils/format'
import { sourceIcon } from '../utils/icons'

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api('/api/dashboard'), api('/api/documents')])
      .then(([s, docs]) => {
        setStats(s)
        setRecent(docs.slice(0, 6))
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
        description="최근 14일간의 문서 해석 및 RPA 자동 입력 현황입니다."
        actions={
          <Link to="/documents" className="btn-primary">
            <FontAwesomeIcon icon={faCloudArrowUp} /> 문서 업로드
          </Link>
        }
      />

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
              <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-full bg-brand-500" />파싱 성공</span>
              <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-full bg-rose-400" />실패</span>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stats.daily} margin={{ left: -20, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="gParsed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }} />
                <Area type="monotone" dataKey="parsed" name="파싱 성공" stroke="#6366f1" strokeWidth={2} fill="url(#gParsed)" />
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
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold">최근 처리 문서</h2>
          <Link to="/documents" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
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
    </>
  )
}
