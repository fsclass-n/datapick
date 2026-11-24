import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowDown,
  faArrowRight,
  faArrowUp,
  faBolt,
  faCircleCheck,
  faCodeBranch,
  faEye,
  faFileExcel,
  faGavel,
  faLock,
  faMagnifyingGlass,
  faPlus,
  faRobot,
  faScaleBalanced,
  faShieldHalved,
  faUserCheck,
  faUserShield,
} from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../context/AuthContext'
import { LogoMark } from '../components/layout/Logo'
import { DOCUMENT_TOOL, TOOL_LIST, TOOLS } from '../utils/tools'

const PIPELINE = [
  {
    icon: faMagnifyingGlass,
    step: '01 · 읽기',
    title: 'AI는 문서를 읽기만 합니다',
    body: 'PDF 텍스트 → OCR → Gemini 멀티모달 순으로 읽고, 정해진 스키마(JSON)로만 답하게 합니다. 문서에 없는 값은 비워 둡니다.',
  },
  {
    icon: faGavel,
    step: '02 · 판정',
    title: '판정은 규칙 코드가 합니다',
    body: '품목 매칭과 최저가 대비 %, 9가지 계약 위험 규칙과 점수, 검진 기준 범위 판정은 코드로 계산합니다. 같은 입력이면 늘 같은 결과입니다.',
  },
  {
    icon: faRobot,
    step: '03 · 결과',
    title: '바로 쓰는 결과로 돌려줍니다',
    body: '비교표 · 빨간펜 · 추이 차트로 보여 주고, 영수증은 사람이 검수한 뒤 엑셀 원장과 ERP 전표에 로봇이 입력합니다.',
  },
]

// 실제 samples/ 문서를 규칙 엔진으로 분석한 결과 (backend/tests/test_tools.py 에서 같은 값을 검증)
const SAMPLE_FACTS = [
  { tool: TOOLS.quote, input: '인테리어 견적서 3장', result: '빠진 품목 1건 · 이상 단가 2건', detail: '총액 최저 견적에 철거 비용이 빠져 있음을 찾아냄' },
  { tool: TOOLS.contract, input: '마케팅 대행 계약서 9개 조항', result: '주의 조항 8곳 표시 · 위험도 높음', detail: '자동 연장 · 잔여 기간 50% 위약금 · 통보 없는 변경' },
  { tool: TOOLS.health, input: '건강검진 2025 · 2026', result: '나빠진 항목 9개 · 좋아진 항목 1개', detail: '공복혈당 98 → 112 mg/dL, 정상 → 주의 범위' },
]

const ROLES = [
  { icon: faUserShield, role: '운영 관리자', how: '환경 변수 ADMIN_EMAIL · ADMIN_PASSWORD 계정', can: '모든 데이터 생성 · 수정 · 삭제, 회원 권한 지정' },
  { icon: faEye, role: '테스트 관리자', how: '로그인 화면의 테스트 관리자 버튼', can: '관리자 화면 조회만, 쓰기 요청은 서버에서 403' },
  { icon: faUserCheck, role: '일반 사용자', how: '이메일 가입 · Google · 네이버 · 카카오', can: '본인 문서 업로드 · 분석 · RPA 실행' },
]

const PRIVACY = [
  'AI 도구(견적 · 계약서 · 검진)는 원본 파일을 저장하지 않고 분석 결과만 본인 계정에 보관합니다.',
  '분석 결과는 본인만 조회할 수 있으며, 관리자 화면에도 노출하지 않습니다.',
  '권한 검사는 모든 API 의 단일 진입점에서 수행합니다. 화면에서 버튼만 숨기지 않습니다.',
  'JWT 인증 · PBKDF2-SHA256 비밀번호 해시 · OAuth state 쿠키 · TiDB TLS 접속.',
]

const FAQ = [
  { q: '어떤 문서를 올릴 수 있나요?', a: 'PDF(텍스트 · 스캔), JPG · PNG 등 사진, EML · HTML 메일, TXT 를 지원합니다. 파일당 최대 10MB 이고, 견적 비교와 검진 추이는 한 번에 최대 5개까지 올릴 수 있습니다.' },
  { q: '계약서 빨간펜 결과를 법률 자문으로 봐도 되나요?', a: '아닙니다. 서명 전에 다시 읽어 봐야 할 조항을 표시해 주는 주의 표시입니다. 중요한 계약은 전문가와 상의하세요.' },
  { q: '건강검진 판정은 진단인가요?', a: '아닙니다. 국민건강보험 일반검진 기준을 단순화한 참고용 비교이며 성별 · 나이를 구분하지 않습니다. 이상 소견은 의료진과 상담하세요.' },
  { q: 'AI가 숫자를 잘못 읽으면 어떻게 되나요?', a: 'AI는 값을 추출만 하고 비교 · 판정은 규칙 코드가 하므로, 결과 화면에서 원본 수치를 함께 확인할 수 있습니다. 영수증 자동 입력은 사람이 검수한 뒤에만 엑셀 · ERP 입력을 실행할 수 있습니다.' },
  { q: '업로드한 파일은 어디에 저장되나요?', a: 'AI 도구는 원본을 저장하지 않습니다. 영수증 자동 입력은 재해석을 위해 원본을 서버에 보관합니다. AI 해석이 필요한 경우 내용이 Google Gemini API 로 전송됩니다.' },
]

function SectionHeading({ eyebrow, title, body, center = false, light = false }) {
  return (
    <div className={`max-w-2xl ${center ? 'mx-auto text-center' : ''}`}>
      <p className="eyebrow">{eyebrow}</p>
      <h2 className={`mt-3 text-3xl font-bold sm:text-title ${light ? 'text-white' : ''}`}>{title}</h2>
      {body && <p className={`mt-4 text-body ${light ? 'text-white/70' : 'text-slate-500'}`}>{body}</p>}
    </div>
  )
}

function QuoteMini() {
  const rows = [
    ['벽지 시공', ['18,000', '17,500', '19,000'], [null, 'low', null]],
    ['바닥 데코타일', ['32,000', '30,000', '41,000'], [null, 'low', 'out']],
    ['LED 조명', ['55,000', '42,000', '46,000'], ['out', 'low', null]],
    ['철거 · 폐기물', ['400,000', null, '350,000'], [null, 'miss', 'low']],
  ]
  const tone = { low: 'bg-emerald-50 text-emerald-700', out: 'bg-rose-50 font-bold text-rose-600', miss: 'text-amber-600' }
  return (
    <table className="w-full text-[12px]">
      <thead className="text-slate-400">
        <tr><th className="pb-2 text-left font-medium">품목 단가</th>{['한빛', '다온', '우리'].map((v) => <th key={v} className="pb-2 text-right font-medium">{v}</th>)}</tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {rows.map(([name, cells, flags]) => (
          <tr key={name}>
            <td className="py-2 text-slate-700">{name}</td>
            {cells.map((c, i) => (
              <td key={i} className="py-1.5 text-right">
                <span className={`rounded px-1.5 py-0.5 tabular-nums ${tone[flags[i]] || 'text-slate-600'}`}>{c ?? '항목 없음'}</span>
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ContractMini() {
  return (
    <div className="paper-lines rounded-lg bg-[#fffdf8] p-3 font-serif text-[13px] leading-8 text-slate-700">
      <b className="font-sans">제2조(계약기간)</b> … 서면 해지 통보가 없으면 <span className="red-pen">동일한 조건으로 1년씩 자동 연장된다.</span>
      <br />
      <b className="font-sans">제4조(중도 해지)</b> … <span className="red-pen">잔여 기간 이용료 총액의 50%를 위약금으로</span> 지급한다.
      <p className="mt-2 flex flex-wrap gap-1.5 font-sans text-[11px]">
        <span className="rounded-full bg-rose-600 px-2 py-0.5 font-bold text-white">위험도 100</span>
        <span className="rounded-full bg-rose-100 px-2 py-0.5 text-rose-700">높음 3</span>
        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700">주의 3</span>
      </p>
    </div>
  )
}

function HealthMini() {
  const rows = [
    ['공복혈당', '98', '112', '주의', true],
    ['LDL 콜레스테롤', '128', '162', '위험', true],
    ['중성지방', '142', '210', '위험', true],
    ['HDL 콜레스테롤', '38', '44', '정상', false],
  ]
  return (
    <ul className="space-y-2 text-[12px]">
      {rows.map(([name, a, b, s, bad]) => (
        <li key={name} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2">
          <span className="flex-1 text-slate-700">{name}</span>
          <span className="text-slate-400 tabular-nums">{a}</span>
          <FontAwesomeIcon icon={bad ? faArrowUp : faArrowDown} className={bad ? 'text-rose-500' : 'text-emerald-500'} />
          <span className="w-8 font-semibold text-slate-900 tabular-nums">{b}</span>
          <span className={`w-10 rounded-full py-0.5 text-center text-[11px] font-bold ${s === '정상' ? 'bg-emerald-100 text-emerald-700' : s === '주의' ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'}`}>{s}</span>
        </li>
      ))}
    </ul>
  )
}

function DocsMini() {
  return (
    <div className="space-y-2 text-[12px]">
      {[['거래처', '브런치카페 퀼 역삼점'], ['사업자번호', '123-45-67890'], ['합계 / 부가세', '21,000원 / 1,909원']].map(([k, v]) => (
        <p key={k} className="flex items-center gap-2 rounded-lg border border-slate-100 px-3 py-2">
          <FontAwesomeIcon icon={faCircleCheck} className="text-emerald-500" />
          <span className="w-20 text-slate-400">{k}</span>
          <span className="font-medium text-slate-800">{v}</span>
        </p>
      ))}
      <p className="flex flex-wrap items-center gap-2 pt-1">
        <span className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-2.5 py-1.5 font-semibold text-white"><FontAwesomeIcon icon={faFileExcel} /> 엑셀 원장</span>
        <span className="flex items-center gap-1.5 rounded-lg bg-ink px-2.5 py-1.5 font-semibold text-white"><FontAwesomeIcon icon={faRobot} /> ERP 전표 JV-0001</span>
      </p>
    </div>
  )
}

const SHOWCASE = [
  { tool: TOOLS.quote, View: QuoteMini },
  { tool: TOOLS.contract, View: ContractMini },
  { tool: TOOLS.health, View: HealthMini },
  { tool: DOCUMENT_TOOL, View: DocsMini },
]

function HeroShowcase() {
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  useEffect(() => {
    if (paused) return
    const timer = setInterval(() => setIndex((i) => (i + 1) % SHOWCASE.length), 4500)
    return () => clearInterval(timer)
  }, [paused])
  const { tool, View } = SHOWCASE[index]

  return (
    <div className="relative" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      <div className="absolute -inset-4 -z-10 rounded-[2rem] bg-gold-500/20 blur-2xl" />
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white shadow-2xl shadow-black/30">
        <div className="flex gap-1 overflow-x-auto border-b border-slate-100 bg-paper p-1.5" role="tablist">
          {SHOWCASE.map(({ tool: t }, i) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={i === index}
              onClick={() => setIndex(i)}
              className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-[12px] font-semibold transition ${i === index ? 'bg-white text-ink shadow-sm' : 'text-slate-500 hover:text-ink'}`}
            >
              <FontAwesomeIcon icon={t.icon} className={i === index ? t.accent.icon : ''} /> {t.short}
            </button>
          ))}
        </div>
        <div key={tool.id} className="animate-fade-in p-5">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[13px] font-semibold text-slate-800">{tool.name}</p>
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${tool.accent.chip}`}>샘플 결과</span>
          </div>
          <View />
        </div>
        <div className="h-1 bg-slate-100">
          <div key={`${index}-${paused}`} className={`h-full bg-gold-500 ${paused ? 'w-full' : 'animate-grow'}`} />
        </div>
      </div>
    </div>
  )
}

function ToolCard({ tool, isNew = false }) {
  return (
    <Link to={tool.path} className="group card flex flex-col overflow-hidden transition hover:-translate-y-1 hover:shadow-xl hover:shadow-ink/10">
      <div className="relative h-44 overflow-hidden">
        <img src={tool.image} alt="" loading="lazy" className="size-full object-cover transition duration-500 group-hover:scale-105" />
        <div className="absolute inset-0 bg-gradient-to-t from-ink/80 via-ink/20 to-transparent" />
        <span className={`absolute bottom-4 left-4 flex size-11 items-center justify-center rounded-xl bg-white text-lg ${tool.accent.icon}`}>
          <FontAwesomeIcon icon={tool.icon} />
        </span>
        {isNew && <span className="absolute top-4 right-4 rounded-full bg-gold-500 px-2.5 py-1 text-[11px] font-bold text-ink">NEW</span>}
      </div>
      <div className="flex flex-1 flex-col p-6">
        <h3 className="text-heading font-semibold">{tool.name}</h3>
        <p className="mt-1 font-heading text-sm font-medium text-slate-700">{tool.headline}</p>
        <p className="mt-3 flex-1 text-body text-slate-500">{tool.tagline}</p>
        <dl className="mt-5 space-y-2 border-t border-slate-100 pt-4 text-sm">
          <div className="flex gap-3"><dt className="w-10 shrink-0 text-slate-400">입력</dt><dd className="text-slate-700">{tool.input}</dd></div>
          <div className="flex gap-3"><dt className="w-10 shrink-0 text-slate-400">결과</dt><dd className="font-medium text-ink">{tool.output}</dd></div>
        </dl>
        <span className={`mt-5 inline-flex items-center gap-2 text-sm font-semibold ${tool.accent.text}`}>
          체험하기 <FontAwesomeIcon icon={faArrowRight} className="text-xs transition group-hover:translate-x-1" />
        </span>
      </div>
    </Link>
  )
}

export default function Home() {
  const { user } = useAuth()
  const primary = user ? { to: TOOLS.quote.path, label: 'AI 도구 바로 쓰기' } : { to: '/login', label: '테스트 계정으로 체험하기' }

  return (
    <>
      <section className="relative overflow-hidden bg-ink text-white">
        <img src="/images/hero-quill.webp" alt="" className="absolute inset-y-0 right-0 h-full w-full object-cover object-[15%_center] opacity-60 lg:w-[62%]" />
        <div className="absolute inset-0 bg-gradient-to-r from-ink from-35% via-ink/80 to-ink/25" />
        <div className="absolute inset-0 opacity-30 [background-image:radial-gradient(rgb(233_162_59/0.35)_1px,transparent_1px)] [background-size:22px_22px]" />
        <div className="container-page relative grid items-center gap-14 py-16 sm:py-20 lg:grid-cols-[1.05fr_1fr] lg:py-24">
          <div className="animate-fade-in">
            <p className="inline-flex items-center gap-2 rounded-full border border-gold-400/40 bg-gold-500/10 px-3 py-1 text-xs font-semibold text-gold-200">
              <LogoMark tone="dark" className="size-4" /> 문서를 데이터로 바꾸는 깃펜
            </p>
            <h1 className="mt-5 text-4xl leading-tight font-bold text-white sm:text-display">
              문서를 올리면,
              <br />
              <span className="text-gold-400">데이터가 답합니다.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-white/75 sm:text-lg">
              견적서는 한 표로 비교하고, 계약서는 위험 조항에 빨간 줄을 긋고, 건강검진은 나빠진 수치만 골라냅니다. 영수증은 로봇이 ERP 에 입력합니다.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={primary.to} className="btn bg-gold-500 px-6 py-3 text-base text-ink hover:bg-gold-400">
                <FontAwesomeIcon icon={faBolt} /> {primary.label}
              </Link>
              <Link to="/#tools" className="btn border border-white/25 px-6 py-3 text-base text-white hover:bg-white/10">
                서비스 둘러보기 <FontAwesomeIcon icon={faArrowRight} />
              </Link>
            </div>
            <p className="mt-6 flex items-center gap-2 text-caption text-white/55">
              <FontAwesomeIcon icon={faLock} />
              가입 없이 테스트 계정으로 바로, 도구마다 &lsquo;샘플로 바로 체험&rsquo; 버튼이 있습니다.
            </p>
          </div>
          <HeroShowcase />
        </div>
      </section>

      <section className="border-b border-ink/10 bg-paper-dark/60">
        <div className="container-page grid gap-4 py-6 sm:grid-cols-3">
          {SAMPLE_FACTS.map((f) => (
            <div key={f.tool.id} className="flex items-start gap-3">
              <span className={`flex size-9 shrink-0 items-center justify-center rounded-lg bg-white ${f.tool.accent.icon}`}>
                <FontAwesomeIcon icon={f.tool.icon} />
              </span>
              <div className="min-w-0">
                <p className="text-xs text-slate-500">{f.input}</p>
                <p className="text-sm font-semibold text-ink">{f.result}</p>
                <p className="truncate text-xs text-slate-400">{f.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section id="tools" className="section-y scroll-mt-16">
        <div className="container-page">
          <SectionHeading eyebrow="Services" title="올리는 문서에 따라, 네 가지 답" body="모두 같은 파이프라인 위에서 동작합니다. 문서를 읽는 방법은 같고, 판정 규칙과 결과 화면만 다릅니다." />
          <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {TOOL_LIST.map((tool) => <ToolCard key={tool.id} tool={tool} isNew />)}
          </div>
          <Link to={DOCUMENT_TOOL.path} className="group card mt-6 grid overflow-hidden transition hover:shadow-xl hover:shadow-ink/10 md:grid-cols-[2fr_3fr]">
            <div className="relative min-h-48 overflow-hidden">
              <img src={DOCUMENT_TOOL.image} alt="" loading="lazy" className="absolute inset-0 size-full object-cover transition duration-500 group-hover:scale-105" />
              <div className="absolute inset-0 bg-gradient-to-r from-transparent to-ink/30" />
            </div>
            <div className="p-6 sm:p-8">
              <p className="eyebrow">{DOCUMENT_TOOL.eyebrow}</p>
              <h3 className="mt-2 text-2xl font-bold">{DOCUMENT_TOOL.name}</h3>
              <p className="mt-1 font-heading text-slate-700">{DOCUMENT_TOOL.headline}</p>
              <p className="mt-3 text-body text-slate-500">{DOCUMENT_TOOL.tagline}</p>
              <div className="mt-5 flex flex-wrap gap-2 text-xs">
                {['단계적 OCR', '사람 검수', '엑셀 중복 방지', 'ERP 전표번호 확인'].map((t) => (
                  <span key={t} className="rounded-full bg-brand-50 px-3 py-1 font-medium text-brand-700">{t}</span>
                ))}
              </div>
              <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-brand-700">
                체험하기 <FontAwesomeIcon icon={faArrowRight} className="text-xs transition group-hover:translate-x-1" />
              </span>
            </div>
          </Link>
        </div>
      </section>

      <section id="how" className="section-y scroll-mt-16 bg-ink">
        <div className="container-page">
          <SectionHeading light eyebrow="How it works" title="AI는 읽고, 규칙이 판정합니다" body="AI의 답을 그대로 믿지 않도록 역할을 나눴습니다. 그래서 결과를 설명할 수 있고, 다시 돌려도 같은 답이 나옵니다." />
          <ol className="relative mt-12 grid gap-6 lg:grid-cols-3">
            <div className="absolute top-8 right-[16%] left-[16%] hidden h-px bg-gradient-to-r from-gold-500/0 via-gold-500/60 to-gold-500/0 lg:block" />
            {PIPELINE.map((p) => (
              <li key={p.step} className="relative rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
                <span className="flex size-14 items-center justify-center rounded-2xl bg-gold-500 text-xl text-ink">
                  <FontAwesomeIcon icon={p.icon} />
                </span>
                <p className="mt-5 text-xs font-semibold tracking-widest text-gold-400">{p.step}</p>
                <h3 className="mt-1 text-heading font-semibold text-white">{p.title}</h3>
                <p className="mt-2 text-body text-white/65">{p.body}</p>
              </li>
            ))}
          </ol>
          <div className="mt-10 flex flex-wrap items-center gap-3 text-xs text-white/60">
            <FontAwesomeIcon icon={faCodeBranch} className="text-gold-400" />
            {['Gemini 구조화 출력', 'Tesseract OCR', 'FastAPI', 'Playwright RPA', 'React 19', 'pytest 50개'].map((t) => (
              <span key={t} className="rounded-full border border-white/15 px-3 py-1">{t}</span>
            ))}
          </div>
        </div>
      </section>

      <section id="security" className="section-y scroll-mt-16">
        <div className="container-page grid gap-12 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <SectionHeading eyebrow="Privacy & roles" title="민감한 문서일수록, 남기지 않습니다" body="계약서와 건강검진 결과는 민감한 정보입니다. 필요한 것만 처리하고, 권한은 서버에서 검사합니다." />
            <ul className="mt-8 space-y-3">
              {PRIVACY.map((item) => (
                <li key={item} className="flex gap-3 text-body text-slate-600">
                  <FontAwesomeIcon icon={faShieldHalved} className="mt-1 text-gold-500" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-4 lg:col-span-7">
            {ROLES.map((r) => (
              <div key={r.role} className="card flex flex-col gap-4 p-6 sm:flex-row sm:items-center">
                <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-ink text-gold-400">
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
            <SectionHeading eyebrow="FAQ" title="자주 묻는 질문" />
          </div>
          <div className="divide-y divide-slate-200 border-y border-slate-200 lg:col-span-8">
            {FAQ.map((item) => (
              <details key={item.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-base font-semibold text-ink">
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
          <div className="relative overflow-hidden rounded-3xl bg-ink px-8 py-14 text-center sm:px-16">
            <img src="/images/hero-quill.webp" alt="" loading="lazy" className="absolute inset-0 size-full object-cover opacity-20" />
            <div className="absolute inset-0 bg-gradient-to-b from-ink/60 to-ink" />
            <LogoMark tone="dark" className="relative mx-auto size-14" />
            <h2 className="relative mt-5 text-3xl font-bold text-white sm:text-title">서류 더미는 깃펜에게 맡기세요</h2>
            <p className="relative mx-auto mt-4 max-w-xl text-body text-white/70">테스트 계정으로 로그인하고 각 도구의 &lsquo;샘플로 바로 체험&rsquo;을 눌러 보세요. 10초면 결과를 볼 수 있습니다.</p>
            <div className="relative mt-8 flex flex-wrap justify-center gap-3">
              <Link to={primary.to} className="btn bg-gold-500 px-6 py-3 text-base text-ink hover:bg-gold-400">
                {primary.label} <FontAwesomeIcon icon={faArrowRight} />
              </Link>
              {!user && <Link to="/login?mode=signup" className="btn border border-white/30 px-6 py-3 text-base text-white hover:bg-white/10">무료로 가입하기</Link>}
              <Link to={TOOLS.quote.path} className="btn border border-white/30 px-6 py-3 text-base text-white hover:bg-white/10">
                <FontAwesomeIcon icon={faScaleBalanced} /> 견적 비교부터
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
