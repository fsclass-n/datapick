import { useCallback, useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowsRotate, faBrain, faCircleExclamation, faFileExcel, faKeyboard, faRobot, faUsers } from '@fortawesome/free-solid-svg-icons'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../../api/client'
import { useToast } from '../../context/ToastContext'
import { EmptyState, LoadingBlock, PageHeader, Spinner, StatCard } from '../../components/ui'
import { PROVIDER_LABELS, SOURCE_LABELS, dateTime } from '../../utils/format'

const COLORS = ['#284578', '#10b981', '#e9a23b', '#f43f5e', '#0ea5e9']
const tooltipStyle = { borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }

function Gauge({ value, label, color, detail }) {
  return (
    <div className="card flex flex-col items-center p-5">
      <h2 className="self-start text-base font-semibold">{label}</h2>
      <div className="relative h-44 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart innerRadius="72%" outerRadius="100%" data={[{ value }]} startAngle={210} endAngle={-30}>
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar dataKey="value" cornerRadius={12} fill={color} background={{ fill: '#f1f5f9' }} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-heading text-3xl font-bold text-slate-900">{value}%</span>
          <span className="text-xs text-slate-500">성공률</span>
        </div>
      </div>
      <p className="text-sm text-slate-500">{detail}</p>
    </div>
  )
}

function Donut({ title, data, labels }) {
  const rows = Object.entries(data).map(([key, value]) => ({ name: labels?.[key] || key, value }))
  return (
    <section className="card p-5">
      <h2 className="mb-2 text-base font-semibold">{title}</h2>
      {rows.length ? (
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={rows} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="80%" paddingAngle={rows.length > 1 ? 3 : 0}>
                {rows.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="py-10 text-center text-sm text-slate-400">데이터 없음</p>
      )}
    </section>
  )
}

export default function AdminMonitoring() {
  const toast = useToast()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(
    () =>
      api('/api/admin/stats?days=14')
        .then(setStats)
        .catch((err) => toast(err.message, 'error')),
    [toast],
  )

  useEffect(() => {
    load()
  }, [load])

  async function refresh() {
    setLoading(true)
    await load()
    setLoading(false)
  }

  if (!stats) return <LoadingBlock />
  const { documents: d, rpa, users } = stats

  return (
    <>
      <PageHeader
        eyebrow="Admin"
        title="모니터링 대시보드"
        description="전체 사용자 기준 AI 파싱 성공률과 RPA 타이핑 처리 현황입니다. (최근 14일)"
        actions={
          <button className="btn-secondary" onClick={refresh} disabled={loading}>
            {loading ? <Spinner /> : <FontAwesomeIcon icon={faArrowsRotate} />} 새로고침
          </button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={faUsers} label="전체 회원" value={`${users.total}명`} sub={`운영 관리자 ${users.admins}명 · 테스트 관리자 ${users.test_admins ?? 0}명`} />
        <StatCard icon={faBrain} label="AI 파싱" value={`${d.parsed + d.failed}건`} sub={`성공 ${d.parsed} · 실패 ${d.failed}`} tone="green" />
        <StatCard icon={faFileExcel} label="엑셀 적재" value={`${rpa.by_target.excel || 0}건`} tone="amber" />
        <StatCard icon={faKeyboard} label="ERP 타이핑" value={`${rpa.by_target.erp || 0}건`} sub={`RPA 실패 ${rpa.failed}건`} tone="rose" />
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <Gauge value={d.success_rate} label="AI 파싱 성공률" color="#284578" detail={`평균 신뢰도 ${d.avg_confidence != null ? Math.round(d.avg_confidence * 100) + '%' : '-'}`} />
        <Gauge value={rpa.success_rate} label="RPA 타이핑 성공률" color="#10b981" detail={`총 ${rpa.total}건 실행 · 성공 ${rpa.success}건`} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="card p-5">
          <h2 className="mb-4 text-base font-semibold">일별 AI 파싱 결과</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.daily} margin={{ left: -20, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: '#f8fafc' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="parsed" name="성공" stackId="p" fill="#284578" />
                <Bar dataKey="failed" name="실패" stackId="p" fill="#fb7185" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="card p-5">
          <h2 className="mb-4 text-base font-semibold">일별 RPA 타이핑 처리</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.daily} margin={{ left: -20, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: '#f8fafc' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="rpa_success" name="성공" stackId="r" fill="#10b981" />
                <Bar dataKey="rpa_failed" name="실패" stackId="r" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-3">
        <Donut title="문서 소스" data={d.by_source} labels={SOURCE_LABELS} />
        <Donut title="파서 엔진" data={d.by_parser} labels={{ gemini: 'Gemini', rules: '규칙 기반' }} />
        <Donut title="회원 가입 경로" data={users.by_provider} labels={PROVIDER_LABELS} />
      </div>

      <section className="card mt-6 overflow-hidden">
        <h2 className="border-b border-slate-100 px-5 py-4 text-base font-semibold">최근 파싱 실패</h2>
        {stats.recent_failures.length ? (
          <ul className="divide-y divide-slate-100">
            {stats.recent_failures.map((f) => (
              <li key={f.id} className="flex items-start gap-3 px-5 py-3.5">
                <FontAwesomeIcon icon={faCircleExclamation} className="mt-1 text-rose-500" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-800">{f.filename}</p>
                  <p className="text-xs text-slate-500">{f.error}</p>
                </div>
                <span className="text-xs whitespace-nowrap text-slate-400">{dateTime(f.created_at)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState icon={faRobot} title="최근 실패한 문서가 없습니다" />
        )}
      </section>
    </>
  )
}
