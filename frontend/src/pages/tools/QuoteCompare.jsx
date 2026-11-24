import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCircleExclamation, faLightbulb, faPiggyBank, faTriangleExclamation, faTrophy } from '@fortawesome/free-solid-svg-icons'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ToolPage, { Insights, KpiCard } from '../../components/tools/ToolPage'
import { TOOLS } from '../../utils/tools'
import { compactWon, won } from '../../utils/format'

function PriceCell({ cell }) {
  if (cell.flag === 'missing') {
    return (
      <td className="px-4 py-3 text-center">
        <span className="inline-flex items-center gap-1 rounded-md border border-dashed border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
          <FontAwesomeIcon icon={faCircleExclamation} /> 항목 없음
        </span>
      </td>
    )
  }
  const tone = cell.flag === 'lowest' ? 'bg-emerald-50' : cell.flag === 'outlier' ? 'bg-rose-50' : ''
  return (
    <td className={`px-4 py-3 text-right ${tone}`}>
      <p className={`font-semibold tabular-nums ${cell.flag === 'outlier' ? 'text-rose-700' : 'text-slate-900'}`}>{won(cell.unit_price)}</p>
      <p className="mt-0.5 flex items-center justify-end gap-1.5 text-xs text-slate-400">
        {cell.quantity != null && <span>× {cell.quantity}{cell.unit || ''}</span>}
        {cell.flag === 'lowest' && <span className="rounded bg-emerald-600 px-1.5 py-px font-semibold text-white">최저</span>}
        {cell.flag !== 'lowest' && cell.diff_pct > 0 && (
          <span className={`rounded px-1.5 py-px font-semibold ${cell.flag === 'outlier' ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-500'}`}>+{cell.diff_pct}%</span>
        )}
      </p>
    </td>
  )
}

function QuoteResult({ result }) {
  const { comparison: c, quotes } = result
  const cheapest = c.cheapest
  const missingCount = Object.values(c.missing).reduce((n, list) => n + list.length, 0)
  const chart = c.vendors.map((v, i) => ({ vendor: v, 총액: c.totals[i], 공통품목: c.common_totals[i] }))

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard tone="ink" icon={faTrophy} label="총액 최저 견적" value={c.vendors[cheapest]} sub={won(c.totals[cheapest])} />
        <KpiCard tone="good" icon={faPiggyBank} label="최고가 대비 차이" value={compactWon(c.savings)} sub={`${c.vendors.length}개 견적 비교`} />
        <KpiCard tone={c.outliers ? 'bad' : 'slate'} icon={faTriangleExclamation} label={`이상 단가 (최저가 +${c.outlier_threshold_pct}% 이상)`} value={`${c.outliers}건`} sub="표에서 빨간색으로 표시" />
        <KpiCard tone={missingCount ? 'warn' : 'slate'} icon={faCircleExclamation} label="빠진 품목" value={`${missingCount}건`} sub={missingCount ? Object.keys(c.missing).join(', ') : '모든 견적에 같은 품목'} />
      </div>

      <Insights items={c.insights} icon={faLightbulb} />

      <section className="card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-5 py-4">
          <h3 className="font-semibold">품목별 단가 비교</h3>
          <div className="flex gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-sm bg-emerald-500" />최저 단가</span>
            <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-sm bg-rose-500" />이상 단가</span>
            <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-sm border border-dashed border-amber-500" />항목 없음</span>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                <th className="px-5 py-3 text-left font-semibold">품목</th>
                {c.vendors.map((v, i) => (
                  <th key={v} className={`px-4 py-3 text-right font-semibold ${i === cheapest ? 'text-ink' : ''}`}>
                    {v} {i === cheapest && <FontAwesomeIcon icon={faTrophy} className="ml-1 text-gold-500" />}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {c.rows.map((row) => (
                <tr key={row.name}>
                  <td className="px-5 py-3 font-medium text-slate-800">{row.name}</td>
                  {row.cells.map((cell, i) => <PriceCell key={i} cell={cell} />)}
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t-2 border-slate-200 bg-paper">
              <tr>
                <td className="px-5 py-3 font-semibold text-slate-900">견적 총액</td>
                {c.totals.map((t, i) => (
                  <td key={i} className={`px-4 py-3 text-right font-heading text-base font-bold tabular-nums ${i === cheapest ? 'text-emerald-700' : 'text-slate-900'}`}>{won(t)}</td>
                ))}
              </tr>
              <tr>
                <td className="px-5 py-3 text-slate-600">
                  공통 품목 기준 합계
                  <span className="ml-1 text-xs text-slate-400">({c.common_items}개 품목)</span>
                </td>
                {c.common_totals.map((t, i) => (
                  <td key={i} className="px-4 py-3 text-right text-slate-600 tabular-nums">{won(t)}</td>
                ))}
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <section className="card p-5">
          <h3 className="mb-1 font-semibold">총액 vs 공통 품목 합계</h3>
          <p className="mb-4 text-caption text-slate-500">빠진 품목이 있는 견적은 총액만 보면 실제보다 싸 보일 수 있습니다.</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart} margin={{ left: 0, right: 8, top: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="vendor" tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <YAxis tickFormatter={(v) => `${Math.round(v / 10000)}만`} tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={false} />
                <Tooltip formatter={(v) => won(v)} contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="총액" fill="#14213d" radius={[6, 6, 0, 0]} />
                <Bar dataKey="공통품목" fill="#e9a23b" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="card p-5">
          <h3 className="mb-3 font-semibold">견적별 조건</h3>
          <ul className="space-y-3">
            {quotes.map((q, i) => (
              <li key={q.filename} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <p className="flex items-center justify-between gap-2 text-sm font-semibold text-slate-800">
                  {c.vendors[i]}
                  <span className="text-xs font-normal text-slate-400">{q.date || '견적일 없음'}</span>
                </p>
                <p className="mt-1 text-xs leading-relaxed text-slate-500">{q.notes || '유효기간 · 결제조건 정보 없음'}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  )
}

export default function QuoteCompare() {
  return <ToolPage tool={TOOLS.quote} Result={QuoteResult} />
}
