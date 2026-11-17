import { Suspense, useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRightFromBracket,
  faArrowUp,
  faChartLine,
  faFeatherPointed,
  faFileImport,
  faGaugeHigh,
  faUsersGear,
} from '@fortawesome/free-solid-svg-icons'
import { faGithub } from '@fortawesome/free-brands-svg-icons'
import { useAuth } from '../context/AuthContext'
import { IS_MOCK } from '../api/client'
import { Badge, LoadingBlock } from './ui'

const NAV = [
  { to: '/dashboard', label: '대시보드', icon: faGaugeHigh },
  { to: '/documents', label: '문서 처리', icon: faFileImport },
  { to: '/admin/users', label: '회원 관리', icon: faUsersGear, admin: true },
  { to: '/admin/monitoring', label: '모니터링', icon: faChartLine, admin: true },
]

export function Logo({ light = false }) {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <span className="flex size-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-md shadow-brand-600/30">
        <FontAwesomeIcon icon={faFeatherPointed} />
      </span>
      <span className={`font-heading text-lg font-bold ${light ? 'text-white' : 'text-slate-900'}`}>dataquill</span>
    </Link>
  )
}

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

function navClass({ isActive }) {
  return `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
    isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`
}

function MobileDrawer({ open, onClose, items, user, onLogout }) {
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
        className={`fixed top-16 right-0 bottom-0 z-40 flex w-[82%] max-w-xs flex-col bg-white shadow-2xl transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] lg:hidden ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="border-b border-slate-100 px-5 py-5">
          <p className="font-heading font-semibold text-slate-900">{user.name}</p>
          <p className="mt-0.5 truncate text-sm text-slate-500">{user.email}</p>
          <div className="mt-2">
            <Badge status={user.role} />
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {items.map((item, i) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={(s) => `${navClass(s)} py-3 text-base`}
              style={{ transitionDelay: open ? `${80 + i * 40}ms` : '0ms' }}
            >
              <FontAwesomeIcon icon={item.icon} className="w-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-100 p-4">
          <button onClick={onLogout} className="btn-secondary w-full">
            <FontAwesomeIcon icon={faArrowRightFromBracket} /> 로그아웃
          </button>
        </div>
      </aside>
    </>
  )
}

function Header() {
  const { user, isAdmin, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const items = NAV.filter((item) => !item.admin || isAdmin)

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
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <Logo />
          <nav className="hidden items-center gap-1 lg:flex">
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} className={navClass}>
                <FontAwesomeIcon icon={item.icon} className="text-xs" />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          {IS_MOCK && <Badge tone="amber">Mock 모드</Badge>}
          <div className="hidden items-center gap-3 lg:flex">
            <div className="text-right leading-tight">
              <p className="text-sm font-semibold text-slate-800">{user.name}</p>
              <p className="text-xs text-slate-500">{isAdmin ? '관리자' : '일반 사용자'}</p>
            </div>
            <span className="flex size-9 items-center justify-center rounded-full bg-brand-100 font-heading font-semibold text-brand-700">
              {user.name.slice(0, 1)}
            </span>
            <button onClick={logout} className="btn-ghost px-2.5" title="로그아웃" aria-label="로그아웃">
              <FontAwesomeIcon icon={faArrowRightFromBracket} />
            </button>
          </div>
          <HamburgerButton open={open} onClick={() => setOpen((v) => !v)} />
        </div>
      </div>
    </header>
    <MobileDrawer open={open} onClose={() => setOpen(false)} items={items} user={user} onLogout={logout} />
    </>
  )
}

const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })

function TopButton() {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 320)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return (
    <button
      onClick={scrollToTop}
      aria-label="맨 위로 이동"
      className={`fixed right-5 bottom-5 z-20 flex size-12 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg shadow-brand-600/30 transition-all duration-300 hover:-translate-y-1 hover:bg-brand-700 ${
        visible ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'
      }`}
    >
      <FontAwesomeIcon icon={faArrowUp} />
    </button>
  )
}

function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <div>
          <Logo />
          <p className="mt-2 text-sm text-slate-500">생성형 AI & RPA 기반 데이터 입력 자동화 플랫폼</p>
          <p className="mt-1 text-xs text-slate-400">© {new Date().getFullYear()} dataquill · 홍기흥</p>
        </div>
        <div className="flex items-center gap-3">
          <a href="https://github.com/fsclass-n/dataquill" target="_blank" rel="noreferrer" className="btn-ghost">
            <FontAwesomeIcon icon={faGithub} /> GitHub
          </a>
          <button onClick={scrollToTop} className="btn-secondary">
            <FontAwesomeIcon icon={faArrowUp} /> To the Top
          </button>
        </div>
      </div>
    </footer>
  )
}

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="mx-auto w-full max-w-7xl flex-1 animate-fade-in px-4 py-8 sm:px-6 lg:px-8">
        <Suspense fallback={<LoadingBlock />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
      <TopButton />
    </div>
  )
}
