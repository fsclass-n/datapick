import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowUp } from '@fortawesome/free-solid-svg-icons'
import { faGithub } from '@fortawesome/free-brands-svg-icons'
import { API_URL, IS_MOCK } from '../../api/client'
import Logo from './Logo'
import { DOCUMENT_TOOL, IMAGE_CREDITS, TOOL_LIST } from '../../utils/tools'

const REPO = 'https://github.com/fsclass-n/dataquill'

const COLUMNS = [
  {
    title: '서비스',
    links: [...TOOL_LIST, DOCUMENT_TOOL].map((tool) => ({ label: tool.name, to: tool.path })),
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
      { label: '작동 방식', to: '/#how' },
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
  const className = `text-sm transition hover:text-gold-400 ${link.strong ? 'font-semibold text-white' : 'text-white/60'}`
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
      className={`fixed right-5 bottom-5 z-20 flex size-12 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-lg shadow-slate-900/10 transition-all duration-300 hover:-translate-y-1 hover:border-gold-400 hover:text-gold-600 sm:right-8 sm:bottom-8 ${
        visible ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'
      }`}
    >
      <FontAwesomeIcon icon={faArrowUp} />
    </button>
  )
}

export default function Footer() {
  return (
    <footer className="bg-ink text-white">
      <div className="container-page grid gap-12 py-14 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <Logo light />
          <p className="mt-4 max-w-xs text-body text-white/60">
            견적서 · 계약서 · 건강검진 결과지 · 영수증을 AI가 읽고, 규칙이 판정하고, 로봇이 입력하는 문서 데이터 플랫폼
          </p>
          <div className="mt-5 flex gap-2">
            <a
              href={REPO}
              target="_blank"
              rel="noreferrer"
              aria-label="GitHub"
              className="flex size-10 items-center justify-center rounded-full border border-white/20 text-white/70 transition hover:border-gold-400 hover:text-gold-400"
            >
              <FontAwesomeIcon icon={faGithub} />
            </a>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4 lg:col-span-8">
          {COLUMNS.map((column) => (
            <div key={column.title}>
              <p className="mb-4 text-sm font-semibold text-gold-400">{column.title}</p>
              <ul className="space-y-3">
                {column.links.map((link) => (
                  <li key={link.label}><FooterLink link={link} /></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="container-page flex flex-col gap-3 py-6 text-caption text-white/45 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <p>
              <span className="font-semibold text-white/70">dataquill</span> · 운영 홍기흥 · 고객센터{' '}
              <a href={`${REPO}/issues`} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">GitHub Issues</a>
            </p>
            <p>개인 포트폴리오 프로젝트로 별도의 사업자 등록 정보가 없습니다. 업로드 문서는 데모 목적 외에 사용하지 않습니다.</p>
            <p>
              사진:{' '}
              {IMAGE_CREDITS.map((c, i) => (
                <span key={c.url}>
                  {i > 0 && ' · '}
                  <a href={c.url} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">{c.name}</a>
                </span>
              ))}{' '}
              on Unsplash (Unsplash License)
            </p>
          </div>
          <p>© {new Date().getFullYear()} dataquill. All rights reserved.</p>
        </div>
      </div>
      <TopButton />
    </footer>
  )
}
