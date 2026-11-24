import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowDown,
  faArrowUp,
  faCalendarCheck,
  faCircleInfo,
  faHeartPulse,
  faMinus,
  faStethoscope,
  faThumbsUp,
  faTriangleExclamation,
} from '@fortawesome/free-solid-svg-icons'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ToolPage, { Insights, KpiCard } from '../../components/tools/ToolPage'
import { TOOLS } from '../../utils/tools'

const STATUS = {
  normal: ['정상', 'bg-emerald-50 text-emerald-700', '#059669'],
  caution: ['주의', 'bg-amber-50 text-amber-700', '#d97706'],
  risk: ['위험', 'bg-rose-50 text-rose-700', '#e11d48'],
}
const FLAG = {
  worsened: ['범위 악화', 'bg-rose-600 text-white'],
  watch: ['계속 악화', 'bg-amber-500 text-white'],
  improved: ['개선', 'bg-emerald-600 text-white'],
}
const fmt = (v) => (v == null ? '-' : Number(v).toLocaleString('ko-KR', { maximumFractionDigits: 2 }))

function Delta({ row }) {
  if (row.delta == null || row.delta === 0) return <FontAwesomeIcon icon={faMinus} className="text-slate-300" />
  const up = row.delta > 0
  const bad = (row.better === 'lower' && up) || (row.better === 'higher' && !up)
  const tone = row.better ? (bad ? 'text-rose-600' : 'text-emerald-600') : 'text-slate-500'
  return (
    <span className={`inline-flex items-center gap-1 font-semibold tabular-nums ${tone}`}>
      <FontAwesomeIcon icon={up ? faArrowUp : faArrowDown} className="text-xs" />
      {fmt(Math.abs(row.delta))}
    </span>
  )
}

function TrendChart({ row, dates }) {
  const data = dates.map((d, i) => ({ date: d?.slice(0, 7) || `${i + 1}회`, value: row.values[i] }))
  const color = STATUS[row.statuses.at(-1)]?.[2] || '#14213d'
  return (
    <div className="card p-4">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-800">{row.label}</p>
        {row.flag && <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${FLAG[row.flag][1]}`}>{FLAG[row.flag][0]}</span>}
      </div>
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ left: -24, right: 12, top: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
            <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
            <Tooltip formatter={(v) => `${fmt(v)} ${row.unit}`} contentStyle={{ borderRadius: 10, fontSize: 12 }} />
            {row.limits.map((l) => <ReferenceLine key={l} y={l} stroke="#f59e0b" strokeDasharray="4 3" />)}
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} dot={{ r: 4, fill: color }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-[11px] text-slate-400">점선: 정상 범위 경계 ({row.reference})</p>
    </div>
  )
}

function HealthResult({ result }) {
  const { trend: t, exams } = result
  const multi = t.dates.length >= 2
  const charted = t.rows.filter((r) => r.flag && r.values.filter((v) => v != null).length >= 2)

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard tone="ink" icon={faCalendarCheck} label="비교한 검진" value={`${t.dates.length}회`} sub={t.dates.filter(Boolean).join(' → ') || exams.map((e) => e.filename).join(', ')} />
        <KpiCard tone={t.worsened ? 'bad' : 'slate'} icon={faTriangleExclamation} label="나빠진 항목" value={`${t.worsened}개`} sub={multi ? '범위 악화 + 계속 악화' : '비교하려면 2회분 이상 필요'} />
        <KpiCard tone={t.improved ? 'good' : 'slate'} icon={faThumbsUp} label="좋아진 항목" value={`${t.improved}개`} sub="더 나은 범위로 이동" />
        <KpiCard tone={t.counts.risk ? 'warn' : 'good'} icon={faStethoscope} label="최근 판정" value={`위험 ${t.counts.risk} · 주의 ${t.counts.caution}`} sub={`정상 ${t.counts.normal}개 항목`} />
      </div>

      <Insights items={t.insights} icon={faHeartPulse} title="눈여겨볼 변화" />

      {charted.length > 0 && (
        <section>
          <h3 className="mb-3 px-1 font-semibold">변화가 있는 항목 추이</h3>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {charted.map((row) => <TrendChart key={row.code} row={row} dates={t.dates} />)}
          </div>
        </section>
      )}

      <section className="card overflow-hidden">
        <h3 className="border-b border-slate-100 px-5 py-4 font-semibold">항목별 수치표</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                <th className="px-5 py-3 text-left font-semibold">검사 항목</th>
                {t.dates.map((d, i) => (
                  <th key={i} className="px-4 py-3 text-right font-semibold">{d || `${i + 1}회차`}</th>
                ))}
                {multi && <th className="px-4 py-3 text-right font-semibold">변화</th>}
                <th className="px-4 py-3 text-center font-semibold">변화 판정</th>
                <th className="px-5 py-3 text-left font-semibold">정상 기준</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {t.rows.map((row) => (
                <tr key={row.code}>
                  <td className="px-5 py-3">
                    <p className="font-medium text-slate-800">{row.label}</p>
                    <p className="text-xs text-slate-400">{row.unit}</p>
                  </td>
                  {row.values.map((v, i) => {
                    const s = STATUS[row.statuses[i]]
                    return (
                      <td key={i} className="px-4 py-3 text-right">
                        <span className={`inline-block rounded-lg px-2.5 py-1 font-semibold tabular-nums ${s ? s[1] : 'text-slate-700'}`}>{fmt(v)}</span>
                        {s && <p className="mt-0.5 text-[11px] text-slate-400">{s[0]}</p>}
                      </td>
                    )
                  })}
                  {multi && <td className="px-4 py-3 text-right"><Delta row={row} /></td>}
                  <td className="px-4 py-3 text-center">
                    {row.flag ? <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${FLAG[row.flag][1]}`}>{FLAG[row.flag][0]}</span> : <span className="text-xs text-slate-300">-</span>}
                  </td>
                  <td className="px-5 py-3 text-xs text-slate-500">{row.reference || '추이만 표시'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <p className="flex items-start gap-2 rounded-xl bg-slate-100 px-4 py-3 text-caption text-slate-600">
        <FontAwesomeIcon icon={faCircleInfo} className="mt-0.5" />
        {t.disclaimer}
      </p>
    </>
  )
}

export default function HealthTrend() {
  return <ToolPage tool={TOOLS.health} Result={HealthResult} />
}
