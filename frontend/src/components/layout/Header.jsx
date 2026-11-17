import { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRightFromBracket,
  faArrowRightToBracket,
  faChartLine,
  faCircleQuestion,
  faFileImport,
  faGaugeHigh,
  faLayerGroup,
  faRoute,
  faShieldHalved,
  faSitemap,
  faUsersGear,
} from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../../context/AuthContext'
import { IS_MOCK } from '../../api/client'
import { Badge } from '../ui'
import Logo from './Logo'

const MARKETING_NAV = [
  { to: '/#features', label: '주요 기능', icon: faLayerGroup },
  { to: '/#how', label: '작동 방식', icon: faRoute },
  { to: '/#use-cases', label: '활용 사례', icon: faSitemap },
  { to: '/#security', label: '보안 · 권한', icon: faShieldHalved },
  { to: '/#faq', label: 'FAQ', icon: faCircleQuestion },
]

const APP_NAV = [
  { to: '/dashboard', label: '대시보드', icon: faGaugeHigh },
  { to: '/documents', label: '문서 처리', icon: faFileImport },
  { to: '/admin/users', label: '회원 관리', icon: faUsersGear, admin: true },
  { to: '/admin/monitoring', label: '모니터링', icon: faChartLine, admin: true },
]

function HamburgerButton({ open, onClick }) {
  const bar = 'absolute left-0 h-0.5 w-6 rounded-full bg-slate-800 transition-all duration-300 ease-in-out'
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={open ? '메뉴 닫기' : '메뉴 열기'}
      aria-expanded={open}
      aria-controls="mobile-drawer"
      className="relative flex size-10 items-center justify-center rounded-lg hover:bg-slate-100 lg:hidden"
    >
      <span className="relative block h-5 w-6">
        <span className={`${bar} ${open ? 'top-[9px] rotate-45' : 'top-0'}`} />
        <span className={`${bar} top-[9px] ${open ? 'translate-x-3 opacity-0' : 'opacity-100'}`} />
        <span className={`${bar} ${open ? 'top-[9px] -rotate-45' : 'top-[18px]'}`} />
      </span>
    </button>
  )
}

const navClass = ({ isActive }) =>
  `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
    isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`

// 해시 링크(/#features)는 NavLink 의 활성 표시 대상이 아니므로 일반 Link 로 렌더링
function NavItem({ item, className, onClick, iconClass = 'text-xs' }) {
  const content = (
    <>
      <FontAwesomeIcon icon={item.icon} className={iconClass} />
      {item.label}
    </>
  )
  if (item.to.includes('#')) {
    return (
      <Link to={item.to} onClick={onClick} className={className({ isActive: false })}>
        {content}
      </Link>
    )
  }
  return (
    <NavLink to={item.to} onClick={onClick} className={className}>
      {content}
    </NavLink>
  )
}

function UserSummary({ user }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-100 font-heading font-semibold text-brand-700">
        {user.name.slice(0, 1)}
      </span>
      <div className="min-w-0 leading-tight">
        <p className="truncate text-sm font-semibold text-slate-800">{user.name}</p>
        <p className="truncate text-xs text-slate-500">{user.email}</p>
      </div>
    </div>
  )
}

function MobileDrawer({ open, onClose, items }) {
  const { user, logout } = useAuth()
  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-x-0 top-16 bottom-0 z-40 bg-slate-900/40 backdrop-blur-sm transition-opacity duration-300 lg:hidden ${
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        aria-hidden="true"
      />
      <aside
        id="mobile-drawer"
        aria-hidden={!open}
        inert={!open}
        className={`fixed top-16 right-0 bottom-0 z-40 flex w-[84%] max-w-xs flex-col bg-white shadow-2xl transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] lg:hidden ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {user && (
          <div className="space-y-2 border-b border-slate-100 px-5 py-5">
            <UserSummary user={user} />
            <Badge status={user.role} />
          </div>
        )}
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {items.map((item) => (
            <NavItem key={item.to} item={item} onClick={onClose} iconClass="w-5" className={(s) => `${navClass(s)} py-3 text-base`} />
          ))}
          {user && (
            <Link to="/" onClick={onClose} className="mt-2 flex items-center gap-2 rounded-lg px-3 py-3 text-sm text-slate-500 hover:bg-slate-100">
              서비스 소개 보기
            </Link>
          )}
        </nav>
        <div className="space-y-2 border-t border-slate-100 p-4">
          {user ? (
            <button onClick={logout} className="btn-secondary w-full">
              <FontAwesomeIcon icon={faArrowRightFromBracket} /> 로그아웃
            </button>
          ) : (
            <>
              <Link to="/login" onClick={onClose} className="btn-secondary w-full">
                <FontAwesomeIcon icon={faArrowRightToBracket} /> 로그인
              </Link>
              <Link to="/login?mode=signup" onClick={onClose} className="btn-primary w-full">
                무료로 시작하기
              </Link>
            </>
          )}
        </div>
      </aside>
    </>
  )
}

export default function Header() {
  const { user, isAdmin, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const items = user ? APP_NAV.filter((item) => !item.admin || isAdmin) : MARKETING_NAV

  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
        <div className="container-page flex h-16 items-center justify-between gap-6">
          <div className="flex items-center gap-8">
            <Logo />
            <nav className="hidden items-center gap-1 lg:flex" aria-label="주 메뉴">
              {items.map((item) => (
                <NavItem key={item.to} item={item} className={navClass} />
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            {IS_MOCK && <Badge tone="amber">Mock 모드</Badge>}
            {user ? (
              <div className="hidden items-center gap-3 lg:flex">
                <Badge status={user.role} />
                <UserSummary user={user} />
                <button onClick={logout} className="btn-ghost px-2.5" title="로그아웃" aria-label="로그아웃">
                  <FontAwesomeIcon icon={faArrowRightFromBracket} />
                </button>
              </div>
            ) : (
              <div className="hidden items-center gap-2 sm:flex">
                <Link to="/login" className="btn-ghost">로그인</Link>
                <Link to="/login?mode=signup" className="btn-primary">무료로 시작하기</Link>
              </div>
            )}
            <HamburgerButton open={open} onClick={() => setOpen((v) => !v)} />
          </div>
        </div>
      </header>
      <MobileDrawer open={open} onClose={() => setOpen(false)} items={items} />
    </>
  )
}
