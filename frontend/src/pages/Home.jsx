import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight,
  faBrain,
  faBuildingColumns,
  faChartLine,
  faCheck,
  faCircleCheck,
  faEnvelopeOpenText,
  faEye,
  faFileExcel,
  faFileInvoice,
  faHandshake,
  faKeyboard,
  faLock,
  faMagnifyingGlass,
  faPlus,
  faRobot,
  faShieldHalved,
  faUserCheck,
  faUserShield,
  faWandMagicSparkles,
} from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../context/AuthContext'

const FORMATS_IN = ['PDF 영수증', '스캔 이미지', 'EML 메일', 'HTML 메일', 'TXT', '메일 본문 붙여넣기']
const FORMATS_OUT = ['Excel 원장 (.xlsx)', '웹 ERP 전표 화면']

const STEPS = [
  { icon: faFileInvoice, title: '수집', body: '파일을 끌어다 놓거나 거래 메일 본문을 붙여 넣습니다. 최대 10MB, 형식은 서버에서 검사합니다.' },
  { icon: faWandMagicSparkles, title: '해석', body: '텍스트 레이어 → OCR → Gemini 멀티모달 순으로 읽고, 전표 항목을 스키마에 맞춰 정형화합니다.' },
  { icon: faUserCheck, title: '검수', body: '추출 결과와 신뢰도를 확인하고 필요한 값만 고칩니다. 검수한 문서만 다음 단계로 넘어갑니다.' },
  { icon: faRobot, title: '입력', body: '엑셀 원장에 적재하거나, 로봇이 ERP 전표 화면에 직접 타이핑하고 전표번호까지 확인합니다.' },
]

const FEATURES = [
  { icon: faBrain, title: '구조화 추출', body: '거래처 · 사업자번호 · 거래일자 · 합계 · 부가세 · 품목을 고정된 스키마로 추출하고 신뢰도를 함께 제공합니다.' },
  { icon: faMagnifyingGlass, title: '단계적 OCR', body: 'PDF 텍스트를 먼저 읽고, 스캔본은 Tesseract, 그래도 어려우면 Gemini Vision 으로 해석합니다.' },
  { icon: faUserCheck, title: '사람 검수 단계', body: 'AI 결과를 바로 입력하지 않습니다. 검수 화면에서 값을 확인 · 수정한 문서만 RPA 를 실행할 수 있습니다.' },
  { icon: faFileExcel, title: '엑셀 원장 적재', body: '같은 문서를 다시 적재하면 문서 ID 기준으로 교체해 중복 행이 생기지 않습니다. 원장은 바로 내려받을 수 있습니다.' },
  { icon: faKeyboard, title: 'ERP 자동 타이핑', body: 'Playwright 로봇이 전표 화면에 값을 입력하고, ERP 가 돌려준 전표번호를 확인해야 성공으로 기록합니다.' },
  { icon: faChartLine, title: '운영 모니터링', body: 'AI 파싱 성공률, RPA 성공률, 일별 추이, 최근 실패 원인을 관리자 대시보드에서 추적합니다.' },
]

const USE_CASES = [
  {
    icon: faBuildingColumns,
    team: '재무 · 회계팀',
    title: '법인카드 영수증을 매입 전표로',
    input: 'PDF · 사진 영수증',
    output: 'ERP 매입 전표',
    tone: 'from-brand-600 to-indigo-400',
  },
  {
    icon: faEnvelopeOpenText,
    team: '구매 · 총무팀',
    title: '청구 메일을 엑셀 원장으로',
    input: '청구서 · 이용료 안내 메일',
    output: '월별 Excel 원장',
    tone: 'from-slate-800 to-slate-500',
  },
  {
    icon: faHandshake,
    team: '영업지원팀',
    title: '거래명세서를 주문 데이터로',
    input: '거래명세서 PDF · 주문 확인 메일',
    output: 'ERP 입력 + 원장 이중 기록',
    tone: 'from-fuchsia-700 to-brand-500',
  },
]

const ROLES = [
  { icon: faUserShield, role: '운영 관리자', how: '환경 변수 ADMIN_EMAIL · ADMIN_PASSWORD 계정으로 로그인', can: '모든 데이터 생성 · 수정 · 삭제, 회원 권한 변경', tone: 'border-brand-200 bg-brand-50 text-brand-700' },
  { icon: faEye, role: '테스트 관리자', how: '로그인 화면의 테스트 관리자 버튼', can: '관리자 화면 전체 조회, 쓰기 요청은 서버에서 403 차단', tone: 'border-amber-200 bg-amber-50 text-amber-700' },
  { icon: faUserCheck, role: '일반 사용자', how: '이메일 가입 · Google · 네이버 · 카카오', can: '본인 문서 업로드 · 검수 · RPA 실행', tone: 'border-slate-200 bg-slate-50 text-slate-700' },
]

const SECURITY = [
  'JWT 인증 + PBKDF2-SHA256 비밀번호 해시',
  'OAuth state 쿠키로 CSRF 방지, 이메일 중복 계정 자동 연결 차단',
  '역할 검사는 모든 API 의 단일 진입점에서 수행',
  'TiDB Cloud 접속은 TLS 필수',
]

const FAQ = [
  { q: '어떤 문서를 처리할 수 있나요?', a: 'PDF(텍스트 · 스캔), JPG · PNG 등 이미지, EML · HTML 메일, TXT 파일과 메일 본문 붙여넣기를 지원합니다. 파일당 최대 10MB 입니다.' },
  { q: 'AI 가 틀린 값을 추출하면 어떻게 되나요?', a: '추출 결과는 바로 입력되지 않습니다. 신뢰도와 함께 검수 화면에 표시되고, 사용자가 확인 · 수정한 뒤에만 엑셀 적재나 ERP 입력을 실행할 수 있습니다.' },
  { q: '우리 회사 ERP 에도 연결할 수 있나요?', a: 'ERP 화면의 입력 칸 위치(셀렉터)만 바꾸면 같은 로봇으로 입력할 수 있도록 설계했습니다. 현재는 데모 ERP 화면을 기준으로 검증했습니다.' },
  { q: '업로드한 문서는 어디로 전송되나요?', a: '원본은 서비스 서버에 저장되고, AI 해석이 필요한 경우 Google Gemini API 로 내용이 전송됩니다. 자세한 내용은 개인정보처리방침을 확인해 주세요.' },
  { q: '테스트 관리자와 운영 관리자는 무엇이 다른가요?', a: '테스트 관리자는 누구나 관리자 화면을 둘러볼 수 있는 읽기 전용 계정입니다. 데이터 변경은 서버 환경 변수의 관리자 토큰으로 인증한 운영 관리자만 할 수 있습니다.' },
]

function SectionHeading({ overline, title, body, center = false }) {
  return (
    <div className={`max-w-2xl ${center ? 'mx-auto text-center' : ''}`}>
      <p className="eyebrow">{overline}</p>
      <h2 className="mt-3 text-3xl font-bold sm:text-title">{title}</h2>
      {body && <p className="mt-4 text-body text-slate-500">{body}</p>}
    </div>
  )
}

function HeroVisual() {
  const fields = [
    ['거래처', '스타벅스 강남R점'],
    ['사업자번호', '123-45-67890'],
    ['거래일자', '2026-11-17'],
    ['합계 / 부가세', '9,000원 / 818원'],
  ]
  return (
    <div className="relative">
      <div className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-br from-brand-100 via-white to-fuchsia-100 blur-2xl" />
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-brand-900/10">
        <div className="flex items-center gap-1.5 border-b border-slate-100 bg-slate-50 px-4 py-3">
          {['bg-rose-300', 'bg-amber-300', 'bg-emerald-300'].map((c) => <span key={c} className={`size-2.5 rounded-full ${c}`} />)}
          <span className="ml-3 text-caption text-slate-400">dataquill · 문서 처리</span>
        </div>
        <div className="grid gap-4 p-5 sm:grid-cols-[1fr_1.15fr]">
          <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 font-mono text-[12px] leading-6 text-slate-500">
            <p className="mb-2 font-sans text-caption font-semibold text-slate-700">receipt_029.pdf</p>
            <p>스타벅스 강남R점</p>
            <p>사업자번호 123-45-67890</p>
            <p>2026.11.17 14:32</p>
            <p>아메리카노 2 4,500 9,000</p>
            <p>부가세 818</p>
            <p className="font-semibold text-slate-700">합계 9,000원</p>
          </div>
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <p className="text-caption font-semibold text-slate-700">AI 추출 결과</p>
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-600">신뢰도 98%</span>
            </div>
            {fields.map(([label, value]) => (
              <div key={label} className="flex items-center gap-2 rounded-lg border border-slate-100 px-3 py-2">
                <FontAwesomeIcon icon={faCheck} className="text-[11px] text-emerald-500" />
                <span className="w-20 shrink-0 text-[11px] text-slate-400">{label}</span>
                <span className="truncate text-[13px] font-medium text-slate-800">{value}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 bg-slate-50/70 px-5 py-4">
          <span className="flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-[12px] font-semibold text-white">
            <FontAwesomeIcon icon={faFileExcel} /> 엑셀 원장 적재
          </span>
          <span className="flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-[12px] font-semibold text-white">
            <FontAwesomeIcon icon={faRobot} /> ERP 자동 타이핑
          </span>
          <span className="ml-auto flex items-center gap-1.5 text-[12px] font-semibold text-emerald-600">
            <FontAwesomeIcon icon={faCircleCheck} /> 전표 JV-20261117-0001
          </span>
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  const { user } = useAuth()
  const primary = user ? { to: '/dashboard', label: '대시보드로 이동' } : { to: '/login', label: '테스트 계정으로 체험하기' }

  return (
    <>
      <section className="relative overflow-hidden bg-white">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,var(--color-brand-50),transparent_55%)]" />
        <div className="container-page relative grid items-center gap-14 py-16 sm:py-20 lg:grid-cols-2 lg:py-28">
          <div className="animate-fade-in">
            <p className="eyebrow">AI · RPA 데이터 입력 자동화</p>
            <h1 className="mt-4 text-4xl leading-tight font-bold sm:text-display">
              서류는 AI가 읽고,
              <br />
              입력은 <span className="bg-gradient-to-r from-brand-600 to-fuchsia-500 bg-clip-text text-transparent">로봇이 합니다.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
              영수증 PDF, 세금계산서, 거래 이메일을 Gemini 가 정형 데이터로 바꾸고, 검수한 값을 RPA 가 ERP 와 엑셀에 자동으로 입력합니다.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={primary.to} className="btn-primary px-6 py-3 text-base">
                {primary.label} <FontAwesomeIcon icon={faArrowRight} />
              </Link>
              <Link to="/#how" className="btn-secondary px-6 py-3 text-base">작동 방식 보기</Link>
            </div>
            <p className="mt-5 flex items-center gap-2 text-caption text-slate-500">
              <FontAwesomeIcon icon={faLock} className="text-slate-400" />
              가입 없이 일반 사용자 또는 테스트 관리자(읽기 전용) 계정으로 바로 둘러볼 수 있습니다.
            </p>
          </div>
          <HeroVisual />
        </div>
      </section>

      <section className="border-y border-slate-200 bg-slate-50">
        <div className="container-page flex flex-col gap-4 py-6 text-sm lg:flex-row lg:items-center lg:gap-8">
          <span className="shrink-0 font-semibold text-slate-700">지원 입력</span>
          <div className="flex flex-wrap gap-2">
            {FORMATS_IN.map((f) => <span key={f} className="rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-600">{f}</span>)}
          </div>
          <span className="shrink-0 font-semibold text-slate-700 lg:ml-auto">출력</span>
          <div className="flex flex-wrap gap-2">
            {FORMATS_OUT.map((f) => <span key={f} className="rounded-full bg-brand-600 px-3 py-1 font-medium text-white">{f}</span>)}
          </div>
        </div>
      </section>

      <section id="how" className="section-y scroll-mt-16 bg-white">
        <div className="container-page">
          <SectionHeading overline="How it works" title="수집부터 입력까지, 네 단계" body="가장 정확하고 비용이 적은 방법부터 시도하고, 실패하면 다음 방법으로 넘어갑니다." />
          <ol className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, i) => (
              <li key={step.title} className="relative rounded-2xl border border-slate-200 p-6">
                <div className="flex items-center justify-between">
                  <span className="flex size-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <FontAwesomeIcon icon={step.icon} />
                  </span>
                  <span className="font-heading text-3xl font-bold text-slate-100">0{i + 1}</span>
                </div>
                <h3 className="mt-5 text-heading font-semibold">{step.title}</h3>
                <p className="mt-2 text-body text-slate-500">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="features" className="section-y scroll-mt-16 bg-slate-50">
        <div className="container-page">
          <SectionHeading overline="Features" title="반복 입력 업무에 필요한 기능만, 정확하게" />
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <article key={f.title} className="card p-7 transition hover:-translate-y-0.5 hover:shadow-md">
                <span className="flex size-11 items-center justify-center rounded-xl bg-slate-900 text-white">
                  <FontAwesomeIcon icon={f.icon} />
                </span>
                <h3 className="mt-5 text-heading font-semibold">{f.title}</h3>
                <p className="mt-2 text-body text-slate-500">{f.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="use-cases" className="section-y scroll-mt-16 bg-white">
        <div className="container-page">
          <SectionHeading overline="Use cases" title="팀별 활용 사례" body="같은 파이프라인을 문서 종류와 입력 대상만 바꿔 여러 부서에 적용할 수 있습니다." />
          <div className="mt-12 grid gap-6 lg:grid-cols-3">
            {USE_CASES.map((c) => (
              <article key={c.team} className="group overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <div className={`relative flex h-44 items-end bg-gradient-to-br p-6 ${c.tone}`}>
                  <FontAwesomeIcon icon={c.icon} className="absolute top-6 right-6 text-5xl text-white/25 transition group-hover:scale-110" />
                  <span className="rounded-full bg-white/15 px-3 py-1 text-caption font-semibold text-white backdrop-blur">{c.team}</span>
                </div>
                <div className="p-6">
                  <h3 className="text-heading font-semibold">{c.title}</h3>
                  <dl className="mt-4 space-y-2 text-sm">
                    <div className="flex gap-3"><dt className="w-10 shrink-0 text-slate-400">입력</dt><dd className="text-slate-700">{c.input}</dd></div>
                    <div className="flex gap-3"><dt className="w-10 shrink-0 text-slate-400">결과</dt><dd className="font-medium text-slate-900">{c.output}</dd></div>
                  </dl>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="security" className="section-y scroll-mt-16 bg-slate-50">
        <div className="container-page grid gap-12 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <SectionHeading overline="Security & roles" title="권한은 세 단계로, 검사는 서버에서" body="화면에서 버튼을 숨기는 것만으로는 막을 수 없기 때문에, 모든 쓰기 요청의 권한을 API 단일 진입점에서 검사합니다." />
            <ul className="mt-8 space-y-3">
              {SECURITY.map((item) => (
                <li key={item} className="flex gap-3 text-body text-slate-600">
                  <FontAwesomeIcon icon={faShieldHalved} className="mt-1 text-brand-500" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-4 lg:col-span-7">
            {ROLES.map((r) => (
              <div key={r.role} className="card flex flex-col gap-4 p-6 sm:flex-row sm:items-center">
                <span className={`flex size-12 shrink-0 items-center justify-center rounded-xl border ${r.tone}`}>
                  <FontAwesomeIcon icon={r.icon} />
                </span>
                <div className="flex-1">
                  <h3 className="text-heading font-semibold">{r.role}</h3>
                  <p className="mt-1 text-caption text-slate-400">{r.how}</p>
                </div>
                <p className="text-body text-slate-600 sm:w-64">{r.can}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="faq" className="section-y scroll-mt-16 bg-white">
        <div className="container-page grid gap-12 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <SectionHeading overline="FAQ" title="자주 묻는 질문" />
          </div>
          <div className="divide-y divide-slate-200 border-y border-slate-200 lg:col-span-8">
            {FAQ.map((item) => (
              <details key={item.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-base font-semibold text-slate-900">
                  {item.q}
                  <FontAwesomeIcon icon={faPlus} className="text-sm text-slate-400 transition group-open:rotate-45" />
                </summary>
                <p className="mt-3 text-body text-slate-600">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white pb-20">
        <div className="container-page">
          <div className="relative overflow-hidden rounded-3xl bg-brand-900 px-8 py-14 text-center sm:px-16">
            <div className="absolute -top-24 -left-24 size-72 rounded-full bg-brand-600/40 blur-3xl" />
            <div className="absolute -right-20 -bottom-24 size-72 rounded-full bg-fuchsia-500/25 blur-3xl" />
            <h2 className="relative text-3xl font-bold text-white sm:text-title">반복 입력은 로봇에게 맡기세요</h2>
            <p className="relative mx-auto mt-4 max-w-xl text-body text-brand-100/80">테스트 계정으로 업로드부터 ERP 입력, 관리자 모니터링까지 바로 확인할 수 있습니다.</p>
            <div className="relative mt-8 flex flex-wrap justify-center gap-3">
              <Link to={primary.to} className="btn bg-white px-6 py-3 text-base text-brand-700 hover:bg-brand-50">
                {primary.label} <FontAwesomeIcon icon={faArrowRight} />
              </Link>
              {!user && <Link to="/login?mode=signup" className="btn border border-white/30 px-6 py-3 text-base text-white hover:bg-white/10">무료로 가입하기</Link>}
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
