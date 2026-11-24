import { faFileInvoice, faHeartPulse, faPenNib, faScaleBalanced } from '@fortawesome/free-solid-svg-icons'

// Tailwind 는 정적 분석으로 클래스를 만들기 때문에 색상 클래스를 문자열 그대로 둔다
const ACCENTS = {
  sky: { text: 'text-sky-700', icon: 'text-sky-600', solid: 'bg-sky-600 hover:bg-sky-700', soft: 'bg-sky-50', border: 'border-sky-200', chip: 'bg-sky-100 text-sky-800', hex: '#0284c7' },
  rose: { text: 'text-rose-700', icon: 'text-rose-600', solid: 'bg-rose-600 hover:bg-rose-700', soft: 'bg-rose-50', border: 'border-rose-200', chip: 'bg-rose-100 text-rose-800', hex: '#e11d48' },
  emerald: { text: 'text-emerald-700', icon: 'text-emerald-600', solid: 'bg-emerald-600 hover:bg-emerald-700', soft: 'bg-emerald-50', border: 'border-emerald-200', chip: 'bg-emerald-100 text-emerald-800', hex: '#059669' },
  ink: { text: 'text-brand-700', icon: 'text-brand-600', solid: 'bg-brand-600 hover:bg-brand-700', soft: 'bg-brand-50', border: 'border-brand-200', chip: 'bg-brand-100 text-brand-800', hex: '#284578' },
}

export const TOOLS = {
  quote: {
    id: 'quote',
    path: '/tools/quotes',
    name: '견적서 비교기',
    short: '견적 비교',
    eyebrow: 'Quote Compare',
    icon: faScaleBalanced,
    accent: ACCENTS.sky,
    image: '/images/tool-quote.webp',
    headline: '견적서 여러 장, 한 표로 비교',
    tagline: '같은 일의 견적서를 2~5장 올리면 품목을 자동으로 맞춰 단가를 나란히 놓고, 유난히 비싼 항목과 빠진 항목을 찾아냅니다.',
    input: '견적서 2~5장 (PDF · 사진 · TXT)',
    output: '품목별 단가 비교표 · 이상 단가 · 누락 항목 · 절감액',
    steps: ['견적서 2~5장 업로드', 'AI가 품목 · 단가 · 총액 추출', '품목 자동 매칭 후 최저가 대비 비교'],
    endpoint: '/api/tools/quote-compare',
    field: 'files',
    min: 2,
    max: 5,
    samples: [
      ['quote_a.txt', '견적서_A_한빛인테리어.txt'],
      ['quote_b.txt', '견적서_B_다온디자인.txt'],
      ['quote_c.txt', '견적서_C_우리공간.txt'],
    ],
  },
  contract: {
    id: 'contract',
    path: '/tools/contract',
    name: '계약서 빨간펜',
    short: '계약서 빨간펜',
    eyebrow: 'Contract Red Pen',
    icon: faPenNib,
    accent: ACCENTS.rose,
    image: '/images/tool-contract.webp',
    headline: '서명 전에, 위험 조항에 빨간 줄',
    tagline: '계약서를 올리면 자동 연장 · 위약금 · 일방 해지 같은 주의 조항에 원문 그대로 빨간 줄을 긋고, 쉬운 말로 설명합니다.',
    input: '계약서 1부 (PDF · 사진 · TXT) 또는 본문 붙여넣기',
    output: '원문 빨간펜 표시 · 위험도 점수 · 조항별 쉬운 설명 · 확인할 점',
    steps: ['계약서 업로드 또는 붙여넣기', 'AI가 주의 조항을 원문 그대로 발췌', '원문 위치에 빨간 줄 + 쉬운 설명'],
    endpoint: '/api/tools/contract-review',
    field: 'file',
    min: 1,
    max: 1,
    allowText: true,
    samples: [['contract.txt', '마케팅대행_계약서.txt']],
  },
  health: {
    id: 'health',
    path: '/tools/health',
    name: '건강검진 추이 비교기',
    short: '검진 추이',
    eyebrow: 'Health Trend',
    icon: faHeartPulse,
    accent: ACCENTS.emerald,
    image: '/images/tool-health.webp',
    headline: '작년과 올해 검진, 나빠진 수치만 빨갛게',
    tagline: '해마다 받는 건강검진 결과지를 올리면 항목을 맞춰 연도별 추이를 그리고, 범위가 나빠진 수치를 먼저 보여 줍니다.',
    input: '검진 결과지 1~5회분 (PDF · 사진 · TXT)',
    output: '연도별 수치표 · 정상/주의/위험 판정 · 나빠진 항목 · 추이 차트',
    steps: ['연도별 결과지 업로드', 'AI가 검사 항목 · 수치 추출', '기준 범위로 판정하고 변화 비교'],
    endpoint: '/api/tools/health-trend',
    field: 'files',
    min: 1,
    max: 5,
    samples: [
      ['health_2025.txt', '건강검진_2025.txt'],
      ['health_2026.txt', '건강검진_2026.txt'],
    ],
  },
}

export const TOOL_LIST = [TOOLS.quote, TOOLS.contract, TOOLS.health]

export const DOCUMENT_TOOL = {
  id: 'documents',
  path: '/documents',
  name: '영수증 · 청구서 자동 입력',
  short: '문서 자동 입력',
  eyebrow: 'Data Entry RPA',
  icon: faFileInvoice,
  accent: ACCENTS.ink,
  image: '/images/tool-documents.webp',
  headline: '영수증은 AI가 읽고, 입력은 로봇이',
  tagline: '영수증 · 세금계산서 · 거래 메일을 전표 항목으로 정형화하고, 검수한 값을 엑셀 원장과 ERP 화면에 로봇이 입력합니다.',
  input: 'PDF · 사진 · EML · HTML · TXT · 메일 본문',
  output: '엑셀 원장(.xlsx) · ERP 전표(전표번호 확인)',
  steps: ['영수증 · 청구 메일 업로드', 'AI가 전표 항목 추출 → 사람이 검수', '엑셀 원장 적재 · 로봇이 ERP 입력'],
}

export const IMAGE_CREDITS = [
  { name: 'Clark Young', url: 'https://unsplash.com/photos/QdRnZlzYJPA', subject: '깃펜과 잉크병' },
  { name: 'Jakub Żerdzicki', url: 'https://unsplash.com/photos/eGI0aGwuE-A', subject: '견적 비교' },
  { name: 'Owen Michael Grech', url: 'https://unsplash.com/photos/iFLzEx6RNmI', subject: '계약서' },
  { name: 'Derek Finch', url: 'https://unsplash.com/photos/ZeJqVTHlHaY', subject: '건강검진' },
  { name: 'Kelly Sikkema', url: 'https://unsplash.com/photos/wgcUx0kR1ps', subject: '서류 · 영수증' },
]
