import { Fragment, useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCircleInfo, faHighlighter, faPenNib, faUserGroup } from '@fortawesome/free-solid-svg-icons'
import ToolPage from '../../components/tools/ToolPage'
import { TOOLS } from '../../utils/tools'

const RISK = {
  high: { label: '높음', mark: 'red-pen', badge: 'bg-rose-600 text-white', card: 'border-l-rose-500', dot: 'bg-rose-500' },
  medium: { label: '주의', mark: 'rounded-sm bg-amber-50 underline decoration-amber-500 decoration-2 underline-offset-4', badge: 'bg-amber-500 text-white', card: 'border-l-amber-400', dot: 'bg-amber-400' },
  low: { label: '참고', mark: 'underline decoration-slate-400 decoration-dotted decoration-2 underline-offset-4', badge: 'bg-slate-200 text-slate-700', card: 'border-l-slate-300', dot: 'bg-slate-400' },
}
const OVERALL = {
  high: ['서명 전 꼭 확인', 'text-rose-600', '#e11d48'],
  medium: ['확인 권장', 'text-amber-600', '#f59e0b'],
  low: ['큰 위험 없음', 'text-emerald-600', '#059669'],
}

/** 원문을 빨간펜 표시 구간과 일반 구간으로 나눈다 (겹치는 구간은 앞선 것만 표시) */
function segments(text, clauses) {
  const marks = clauses
    .map((c, index) => ({ ...c, index }))
    .filter((c) => c.start != null)
    .sort((a, b) => a.start - b.start)
  const parts = []
  let pos = 0
  for (const m of marks) {
    if (m.start < pos) continue
    if (m.start > pos) parts.push({ text: text.slice(pos, m.start) })
    parts.push({ text: text.slice(m.start, m.end), clause: m })
    pos = m.end
  }
  parts.push({ text: text.slice(pos) })
  return parts
}

function ScoreRing({ score, overall }) {
  const [label, tone, color] = OVERALL[overall]
  const r = 34
  const dash = (score / 100) * 2 * Math.PI * r
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 80 80" className="size-24 -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#f1f5f9" strokeWidth="8" />
        <circle cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round" strokeDasharray={`${dash} 999`} />
      </svg>
      <div>
        <p className="text-caption text-slate-500">위험도 점수</p>
        <p className="font-heading text-3xl font-bold text-slate-900">{score}<span className="text-base text-slate-400"> / 100</span></p>
        <p className={`text-sm font-semibold ${tone}`}>{label}</p>
      </div>
    </div>
  )
}

function ContractResult({ result }) {
  const { review, text } = result
  const [active, setActive] = useState(null)
  const parts = useMemo(() => segments(text, review.clauses), [text, review.clauses])

  function focus(index) {
    setActive(index)
    document.getElementById(`mark-${index}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return (
    <>
      <section className="card grid gap-6 p-5 sm:p-6 lg:grid-cols-[auto_1fr_auto] lg:items-center">
        <ScoreRing score={review.score} overall={review.overall} />
        <div className="min-w-0 space-y-2 lg:border-l lg:border-slate-100 lg:pl-6">
          <p className="font-heading text-lg font-semibold text-slate-900">{review.title || '계약서'}</p>
          {review.parties?.length > 0 && (
            <p className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
              <FontAwesomeIcon icon={faUserGroup} className="text-slate-400" />
              {review.parties.map((p) => <span key={p} className="rounded-full bg-slate-100 px-2.5 py-0.5">{p}</span>)}
            </p>
          )}
          {review.summary && <p className="text-body text-slate-600">{review.summary}</p>}
        </div>
        <div className="flex gap-2">
          {['high', 'medium', 'low'].map((level) => (
            <div key={level} className="rounded-xl border border-slate-100 px-4 py-2.5 text-center">
              <p className="font-heading text-2xl font-bold text-slate-900">{review.counts[level]}</p>
              <p className="flex items-center justify-center gap-1.5 text-xs text-slate-500"><i className={`size-2 rounded-full ${RISK[level].dot}`} />{RISK[level].label}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <section className="card overflow-hidden">
          <h3 className="flex items-center gap-2 border-b border-slate-100 px-5 py-4 font-semibold">
            <FontAwesomeIcon icon={faHighlighter} className="text-rose-500" /> 원문 빨간펜
          </h3>
          <div className="paper-lines max-h-[640px] overflow-y-auto bg-[#fffdf8] px-6 py-5 font-serif text-[15px] leading-8 whitespace-pre-wrap text-slate-800">
            {parts.map((part, i) =>
              part.clause ? (
                <mark
                  key={i}
                  id={`mark-${part.clause.index}`}
                  onClick={() => setActive(part.clause.index)}
                  className={`cursor-pointer bg-transparent text-inherit transition ${RISK[part.clause.risk].mark} ${active === part.clause.index ? 'ring-2 ring-gold-400 ring-offset-2' : ''}`}
                >
                  {part.text}
                  <sup className="ml-0.5 font-sans text-[10px] font-bold text-rose-600">{part.clause.index + 1}</sup>
                </mark>
              ) : (
                <Fragment key={i}>{part.text}</Fragment>
              ),
            )}
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="flex items-center gap-2 px-1 font-semibold">
            <FontAwesomeIcon icon={faPenNib} className="text-rose-500" /> 확인할 조항 {review.clauses.length}개
          </h3>
          {review.clauses.length === 0 && <p className="card p-6 text-sm text-slate-500">눈에 띄는 주의 조항을 찾지 못했습니다.</p>}
          <ol className="max-h-[640px] space-y-3 overflow-y-auto pr-1">
            {review.clauses.map((c, i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => focus(i)}
                  className={`card w-full border-l-4 p-4 text-left transition hover:shadow-md ${RISK[c.risk].card} ${active === i ? 'ring-2 ring-gold-400' : ''}`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-heading text-xs font-bold text-rose-600">{i + 1}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${RISK[c.risk].badge}`}>{RISK[c.risk].label}</span>
                    <span className="text-sm font-semibold text-slate-900">{c.label}</span>
                    <span className="ml-auto text-xs text-slate-400">{c.title}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-700">{c.explanation}</p>
                  {c.suggestion && <p className="mt-2 rounded-lg bg-gold-50 px-3 py-2 text-xs leading-relaxed text-gold-700">확인할 점 · {c.suggestion}</p>}
                  {c.start == null && <p className="mt-2 text-xs text-slate-400">원문에서 위치를 찾지 못해 빨간 줄은 표시하지 않았습니다.</p>}
                </button>
              </li>
            ))}
          </ol>
        </section>
      </div>

      <p className="flex items-start gap-2 rounded-xl bg-slate-100 px-4 py-3 text-caption text-slate-600">
        <FontAwesomeIcon icon={faCircleInfo} className="mt-0.5" />
        법률 자문이 아닌 주의 표시입니다. 중요한 계약은 서명 전에 전문가와 상의하세요.
      </p>
    </>
  )
}

export default function ContractReview() {
  return <ToolPage tool={TOOLS.contract} Result={ContractResult} />
}
