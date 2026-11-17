import { Suspense, useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faEye } from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../../context/AuthContext'
import { LoadingBlock } from '../ui'
import Header from './Header'
import Footer from './Footer'

function ReadOnlyBanner() {
  return (
    <div className="border-b border-amber-200 bg-amber-50">
      <p className="container-page flex items-center gap-2 py-2.5 text-caption text-amber-800">
        <FontAwesomeIcon icon={faEye} />
        <span>
          <strong className="font-semibold">테스트 관리자 모드 · 읽기 전용</strong> — 관리자 화면을 모두 볼 수 있지만, 데이터 생성 · 수정 · 삭제 요청은 서버에서 차단됩니다.
        </span>
      </p>
    </div>
  )
}

// 해시(/#features) 이동과 페이지 전환 시 스크롤 위치를 맞춘다
function ScrollManager() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (hash) {
      const timer = setTimeout(() => document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: 'smooth' }), 50)
      return () => clearTimeout(timer)
    }
    window.scrollTo({ top: 0 })
  }, [pathname, hash])
  return null
}

/** 모든 페이지 공통 레이아웃: 글로벌 헤더 + 본문 + 푸터 */
export default function SiteLayout() {
  const { readOnly } = useAuth()
  return (
    <div className="flex min-h-screen flex-col">
      <ScrollManager />
      <Header />
      {readOnly && <ReadOnlyBanner />}
      <main className="flex-1">
        <Suspense fallback={<LoadingBlock />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
    </div>
  )
}

/** 앱 · 정책 페이지 공통 본문 폭과 여백 */
export function PageContainer() {
  return (
    <div className="container-page page-y animate-fade-in">
      <Outlet />
    </div>
  )
}
