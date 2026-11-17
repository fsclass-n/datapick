import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowUp } from '@fortawesome/free-solid-svg-icons'
import { faGithub } from '@fortawesome/free-brands-svg-icons'
import { API_URL, IS_MOCK } from '../../api/client'
import Logo from './Logo'

const REPO = 'https://github.com/fsclass-n/dataquill'

const COLUMNS = [
  {
    title: '제품',
    links: [
      { label: '주요 기능', to: '/#features' },
      { label: '작동 방식', to: '/#how' },
      { label: '활용 사례', to: '/#use-cases' },
      { label: '보안 · 권한', to: '/#security' },
    ],
  },
  {
    title: '리소스',
    links: [
      { label: '이용 가이드', href: `${REPO}#readme` },
      ...(IS_MOCK ? [] : [{ label: 'API 문서', href: `${API_URL}/docs` }, { label: '데모 ERP 화면', href: `${API_URL}/erp-demo` }]),
      { label: '소스 코드', href: REPO },
    ],
  },
  {
    title: '고객지원',
    links: [
      { label: '자주 묻는 질문', to: '/#faq' },
      { label: '문의 · 버그 제보', href: `${REPO}/issues` },
      ...(IS_MOCK ? [] : [{ label: '서비스 상태', href: `${API_URL}/api/health` }]),
    ],
  },
  {
    title: '정책',
    links: [
      { label: '이용약관', to: '/terms' },
      { label: '개인정보처리방침', to: '/privacy', strong: true },
    ],
  },
]

function FooterLink({ link }) {
  const className = `text-sm transition hover:text-slate-900 ${link.strong ? 'font-semibold text-slate-700' : 'text-slate-500'}`
  return link.to ? (
    <Link to={link.to} className={className}>{link.label}</Link>
  ) : (
    <a href={link.href} target="_blank" rel="noreferrer" className={className}>{link.label}</a>
  )
}

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
      type="button"
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      aria-label="맨 위로 이동"
      title="맨 위로"
      className={`fixed right-5 bottom-5 z-20 flex size-12 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-lg shadow-slate-900/10 transition-all duration-300 hover:-translate-y-1 hover:border-brand-200 hover:text-brand-600 sm:right-8 sm:bottom-8 ${
        visible ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'
      }`}
    >
      <FontAwesomeIcon icon={faArrowUp} />
    </button>
  )
}

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="container-page grid gap-12 py-14 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <Logo />
          <p className="mt-4 max-w-xs text-body text-slate-500">
            비정형 문서를 AI가 해석하고, RPA가 ERP와 엑셀에 자동으로 입력하는 데이터 입력 자동화 플랫폼
          </p>
          <div className="mt-5 flex gap-2">
            <a
              href={REPO}
              target="_blank"
              rel="noreferrer"
              aria-label="GitHub"
              className="flex size-10 items-center justify-center rounded-full border border-slate-200 text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
            >
              <FontAwesomeIcon icon={faGithub} />
            </a>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4 lg:col-span-8">
          {COLUMNS.map((column) => (
            <div key={column.title}>
              <p className="mb-4 text-sm font-semibold text-slate-900">{column.title}</p>
              <ul className="space-y-3">
                {column.links.map((link) => (
                  <li key={link.label}><FooterLink link={link} /></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-slate-100">
        <div className="container-page flex flex-col gap-3 py-6 text-caption text-slate-400 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <p>
              <span className="font-semibold text-slate-500">dataquill</span> · 운영 홍기흥 · 고객센터{' '}
              <a href={`${REPO}/issues`} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">GitHub Issues</a>
            </p>
            <p>개인 포트폴리오 프로젝트로 별도의 사업자 등록 정보가 없습니다. 업로드 문서는 데모 목적 외에 사용하지 않습니다.</p>
          </div>
          <p>© {new Date().getFullYear()} dataquill. All rights reserved.</p>
        </div>
      </div>
      <TopButton />
    </footer>
  )
}
