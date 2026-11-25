import { Link } from 'react-router-dom'

// 깃펜의 한쪽 깃(vane)이 데이터 픽셀로 흩어지는 마크: "문서(깃펜) → 데이터"
const INK = '#14213d'
const GOLD = '#e9a23b'

/** tone: tile(남색 타일) · light(밝은 배경용 남색 깃) · dark(어두운 배경용 흰 깃) */
export function LogoMark({ tone = 'tile', className = 'size-9' }) {
  const quill = tone === 'light' ? INK : '#fff'
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      {tone === 'tile' && <rect width="32" height="32" rx="8" fill={INK} />}
      <g transform="rotate(40 16 16)">
        <path d="M16 2.6C13 4.6 10.3 8 9.7 11.2l2 .5-2.2 1.9c-.3 2.5.3 4 1.1 5.3l1.9-.3-1.1 1.9c1.3 2 2.8 3.2 4.6 3.7z" fill={quill} />
        <g fill={GOLD}>
          <rect x="16.9" y="4.4" width="2" height="2" rx="0.4" />
          <rect x="16.9" y="7" width="2" height="2" rx="0.4" />
          <rect x="19.5" y="7" width="2" height="2" rx="0.4" opacity={0.6} />
          <rect x="16.9" y="9.6" width="2" height="2" rx="0.4" />
          <rect x="19.5" y="9.6" width="2" height="2" rx="0.4" />
          <rect x="22.1" y="9.6" width="2" height="2" rx="0.4" opacity={0.6} />
          <rect x="26.0" y="10.1" width="1.4" height="1.4" rx="0.28" opacity={0.35} />
          <rect x="16.9" y="12.2" width="2" height="2" rx="0.4" />
          <rect x="19.5" y="12.2" width="2" height="2" rx="0.4" />
          <rect x="22.1" y="12.2" width="2" height="2" rx="0.4" opacity={0.6} />
          <rect x="26.0" y="12.7" width="1.4" height="1.4" rx="0.28" opacity={0.35} />
          <rect x="16.9" y="14.8" width="2" height="2" rx="0.4" />
          <rect x="19.5" y="14.8" width="2" height="2" rx="0.4" />
          <rect x="22.1" y="14.8" width="2" height="2" rx="0.4" opacity={0.6} />
          <rect x="26.0" y="15.3" width="1.4" height="1.4" rx="0.28" opacity={0.35} />
          <rect x="16.9" y="17.4" width="2" height="2" rx="0.4" />
          <rect x="19.5" y="17.4" width="2" height="2" rx="0.4" opacity={0.6} />
          <rect x="23.4" y="17.9" width="1.4" height="1.4" rx="0.28" opacity={0.35} />
          <rect x="16.9" y="20" width="2" height="2" rx="0.4" />
          <rect x="19.5" y="20" width="2" height="2" rx="0.4" opacity={0.6} />
          <rect x="16.9" y="22.4" width="2" height="2" rx="0.4" />
        </g>
        <path d="M16 2.8v26.4" stroke={quill} strokeWidth="1.4" strokeLinecap="round" />
        <path d="M16 26.6l-1.05 3.2h2.1z" fill={quill} />
      </g>
    </svg>
  )
}

export function Wordmark({ light = false, className = 'text-lg' }) {
  return (
    <span className={`font-heading font-bold tracking-tight ${className} ${light ? 'text-white' : 'text-ink'}`}>
      data<span className="text-gold-500">pick</span>
    </span>
  )
}

export default function Logo({ light = false, to = '/' }) {
  return (
    <Link to={to} className="flex items-center gap-2.5" aria-label="datapick 메인으로">
      <LogoMark className="size-9 drop-shadow-sm" />
      <Wordmark light={light} />
    </Link>
  )
}
