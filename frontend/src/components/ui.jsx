import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCircleNotch } from '@fortawesome/free-solid-svg-icons'

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <p className="mb-1 text-xs font-semibold tracking-widest text-brand-600 uppercase">{eyebrow}</p>}
        <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

const TONES = {
  brand: 'bg-brand-50 text-brand-600',
  green: 'bg-emerald-50 text-emerald-600',
  amber: 'bg-amber-50 text-amber-600',
  rose: 'bg-rose-50 text-rose-600',
  slate: 'bg-slate-100 text-slate-600',
}

export function StatCard({ icon, label, value, sub, tone = 'brand' }) {
  return (
    <div className="card flex items-start gap-4 p-5">
      <div className={`flex size-11 shrink-0 items-center justify-center rounded-xl ${TONES[tone]}`}>
        <FontAwesomeIcon icon={icon} />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-slate-500">{label}</p>
        <p className="mt-1 font-heading text-2xl font-bold text-slate-900">{value}</p>
        {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
      </div>
    </div>
  )
}

const STATUS = {
  parsed: ['파싱 완료', 'green'],
  failed: ['파싱 실패', 'rose'],
  uploaded: ['대기', 'slate'],
  success: ['성공', 'green'],
  pending: ['대기', 'slate'],
  admin: ['관리자', 'brand'],
  user: ['일반', 'slate'],
}

export function Badge({ status, children, tone }) {
  const [label, defaultTone] = STATUS[status] || [status, 'slate']
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap ${TONES[tone || defaultTone]}`}>
      {children || label}
    </span>
  )
}

export function Spinner({ className = '' }) {
  return <FontAwesomeIcon icon={faCircleNotch} spin className={className} />
}

export function LoadingBlock() {
  return (
    <div className="flex items-center justify-center py-20 text-slate-400">
      <Spinner className="text-2xl" />
    </div>
  )
}

export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-slate-100 text-xl text-slate-400">
        <FontAwesomeIcon icon={icon} />
      </div>
      <p className="font-heading font-semibold text-slate-700">{title}</p>
      {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
