import { Link } from 'react-router-dom'

export function LogoMark({ className = 'size-9' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <path d="M5.5 26.8h21" stroke="#c7d2fe" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M19.5 26.8v-4M23.75 26.8v-7M28 26.8v-10.5" stroke="#c7d2fe" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M6 24.5C5.5 15.5 12 7.5 23.5 6 24 15.5 15.5 23.5 6 24.5Z" fill="#fff" />
      <path d="M6 24.5C11 19 16.5 12.5 23.5 6" fill="none" stroke="#4f46e5" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

export default function Logo({ light = false, to = '/' }) {
  return (
    <Link to={to} className="flex items-center gap-2.5" aria-label="dataquill 메인으로">
      <span className="flex size-9 items-center justify-center rounded-xl bg-brand-600 shadow-md shadow-brand-600/30">
        <LogoMark className="size-9" />
      </span>
      <span className={`font-heading text-lg font-bold tracking-tight ${light ? 'text-white' : 'text-slate-900'}`}>dataquill</span>
    </Link>
  )
}
