import { runTool } from './mockTools'

// VITE_API_URL 이 비어 있을 때(Netlify 단독 배포 1단계) 사용하는 브라우저 내 목업 API.
// 실제 백엔드(FastAPI)와 동일한 경로·응답 형태를 localStorage 로 흉내 낸다.

const DB_KEY = 'dp_mock_db_v2'
const ADMIN_ROLES = ['admin', 'test_admin']
const TEST_ACCOUNT_EMAILS = ['user@datapick.io', 'admin@datapick.io']
const PASSWORD_RE = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/

const PLANS = {
  free: { label: 'Free', price: 0, docs_per_month: 10, erp_connection: false, features: ['월 문서 10건', 'AI 도구 3종', '엑셀 원장'] },
  pro: { label: 'Pro', price: 29000, docs_per_month: 200, erp_connection: true, features: ['월 문서 200건', '내 ERP 연동', 'AI 도구 3종', '엑셀 원장'] },
  business: { label: 'Business', price: 99000, docs_per_month: 2000, erp_connection: true, features: ['월 문서 2,000건', '내 ERP 연동', '우선 지원'] },
}
const monthStart = () => { const d = new Date(); d.setDate(1); d.setHours(0, 0, 0, 0); return d.toISOString() }
const planOf = (user) => PLANS[user.plan || 'free']
const usageOf = (db, user) => {
  const plan = planOf(user)
  const used = db.documents.filter((d) => d.user_id === user.id && d.created_at >= monthStart()).length
  return { plan: user.plan || 'free', plan_label: plan.label, price: plan.price, docs_used: used, docs_limit: plan.docs_per_month, docs_remaining: Math.max(plan.docs_per_month - used, 0), erp_connection: plan.erp_connection }
}
const checkQuota = (db, user) => {
  const u = usageOf(db, user)
  if (u.docs_used >= u.docs_limit) fail(402, `이번 달 문서 처리 한도(${u.docs_limit}건)를 모두 사용했습니다. 상위 요금제로 업그레이드하세요.`)
}

const fail = (status, message) => {
  throw Object.assign(new Error(message), { status })
}
const now = () => new Date().toISOString()
const daysAgo = (n, hour = 10) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  d.setHours(hour, n * 7 % 60)
  return d.toISOString()
}

const VENDORS = ['스타벅스 강남R점', '쿠팡(주)', '네이버클라우드', 'GS25 역삼점', '대한항공', '오피스디포', 'AWS Korea', '배달의민족']

function seed() {
  const users = [
    { id: 1, email: 'user@datapick.io', name: '테스트 사용자', password: 'User1234!', role: 'user', plan: 'free', provider: 'local', created_at: daysAgo(30), last_login_at: null },
    { id: 2, email: 'admin@datapick.io', name: '테스트 관리자', password: 'Admin1234!', role: 'test_admin', provider: 'local', created_at: daysAgo(30), last_login_at: null },
    { id: 3, email: 'kim.hr@acme.co.kr', name: '김인사', password: null, role: 'user', plan: 'pro', provider: 'google', created_at: daysAgo(12), last_login_at: daysAgo(1) },
    { id: 4, email: 'lee.fin@acme.co.kr', name: '이재무', password: null, role: 'user', plan: 'pro', provider: 'naver', created_at: daysAgo(8), last_login_at: daysAgo(2) },
    { id: 5, email: 'park@acme.co.kr', name: '박회계', password: null, role: 'user', plan: 'business', provider: 'kakao', created_at: daysAgo(4), last_login_at: daysAgo(0) },
  ]
  const documents = []
  const jobs = []
  for (let i = 0; i < 26; i++) {
    const day = i % 14
    const failed = i % 6 === 5
    const source = ['pdf', 'image', 'email', 'pdf'][i % 4]
    const amount = 8000 + ((i * 37919) % 420000)
    const doc = {
      id: i + 1,
      user_id: [1, 2, 3, 4, 5][i % 5],
      filename: `${['영수증', '세금계산서', '청구메일', '카드전표'][i % 4]}_${String(i + 1).padStart(3, '0')}.${source === 'image' ? 'jpg' : source === 'email' ? 'eml' : 'pdf'}`,
      source_type: source,
      status: failed ? 'failed' : 'parsed',
      parser: i % 3 ? 'gemini' : 'rules',
      error: failed ? '금액·날짜를 찾지 못했습니다. 문서 형식을 확인하거나 Gemini 파서를 사용하세요.' : null,
      parsed: failed ? null : {
        document_type: source === 'email' ? 'email' : i % 4 === 1 ? 'invoice' : 'receipt',
        vendor: VENDORS[i % VENDORS.length],
        business_number: `${100 + i}-${10 + (i % 80)}-${String(10000 + i * 731).slice(0, 5)}`,
        date: daysAgo(day).slice(0, 10),
        total_amount: amount,
        vat: Math.round(amount / 11),
        currency: 'KRW',
        payment_method: i % 2 ? '신용카드' : '계좌이체',
        items: [{ name: '업무 비용', quantity: 1, unit_price: amount, amount }],
        summary: `${VENDORS[i % VENDORS.length]} 결제`,
        confidence: 0.72 + (i % 5) * 0.06,
      },
      raw_text: '(목업 데이터) 원문 텍스트',
      created_at: daysAgo(day, 9 + (i % 8)),
      parsed_at: daysAgo(day, 9 + (i % 8)),
    }
    documents.push(doc)
    if (!failed && i % 4 !== 3) {
      const ok = i % 9 !== 4
      jobs.push({
        id: jobs.length + 1,
        document_id: doc.id,
        target: i % 2 ? 'erp' : 'excel',
        status: ok ? 'success' : 'failed',
        message: ok ? (i % 2 ? `ERP 전표 입력 완료 (전표번호 JV-${1000 + i})` : '엑셀 원장에 적재했습니다.') : 'ERP 응답 시간 초과',
        created_at: doc.created_at,
        finished_at: doc.created_at,
      })
    }
  }
  return { users, documents, jobs, seq: { user: 6, document: 27, job: jobs.length + 1 } }
}

const load = () => {
  try {
    return JSON.parse(localStorage.getItem(DB_KEY)) || seed()
  } catch {
    return seed()
  }
}
const save = (db) => localStorage.setItem(DB_KEY, JSON.stringify(db))

// eslint-disable-next-line no-unused-vars
const publicUser = ({ password, ...user }) => user
const tokenFor = (user) => `mock.${user.id}.${Date.now()}`
const withJobs = (db, doc) => ({ ...doc, jobs: db.jobs.filter((j) => j.document_id === doc.id) })

function currentUser(db, token) {
  const id = Number(token?.split('.')[1])
  const user = db.users.find((u) => u.id === id)
  if (!user) fail(401, '로그인이 필요합니다.')
  return user
}

function parseText(text) {
  const num = (v) => (v ? Number(v.replace(/,/g, '')) : null)
  const date = text.match(/(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})/)
  const totals = [...text.matchAll(/(?:합\s*계|총\s*액|결제\s*금액|청구\s*금액|total)\s*[:：]?\s*₩?\s*([\d,]+)/gi)].map((m) => num(m[1]))
  const vat = text.match(/(?:부가세|VAT)\s*[:：]?\s*₩?\s*([\d,]+)/i)
  const biz = text.match(/\b(\d{3})-?(\d{2})-?(\d{5})\b/)
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
  if (!totals.length && !date) fail(422, '금액·날짜를 찾지 못했습니다. 문서 형식을 확인하거나 Gemini 파서를 사용하세요.')
  return {
    document_type: /^(From|Subject|제목)\s*:/m.test(text) ? 'email' : 'receipt',
    vendor: (text.match(/(?:상호|가맹점|거래처)\s*[:：]\s*(.+)/)?.[1] || lines[0] || '').slice(0, 100),
    business_number: biz ? biz.slice(1).join('-') : null,
    date: date ? `${date[1]}-${date[2].padStart(2, '0')}-${date[3].padStart(2, '0')}` : null,
    total_amount: totals.length ? Math.max(...totals) : null,
    vat: num(vat?.[1]),
    currency: 'KRW',
    payment_method: text.match(/(신용카드|체크카드|현금|계좌이체)/)?.[1] || null,
    items: [],
    summary: (text.match(/^(?:Subject|제목)\s*:\s*(.+)$/m)?.[1] || lines[0] || '').slice(0, 200),
    confidence: 0.6,
  }
}

function runParse(doc, text) {
  doc.raw_text = text
  try {
    doc.parsed = parseText(text)
    doc.status = 'parsed'
    doc.error = null
  } catch (err) {
    doc.parsed = null
    doc.status = 'failed'
    doc.error = err.message
  }
  doc.parser = 'rules'
  doc.parsed_at = now()
}

const SAMPLE_BY_TYPE = (name) =>
  `${VENDORS[name.length % VENDORS.length]}\n사업자번호: 214-86-${String(10000 + name.length * 997).slice(0, 5)}\n${new Date().toISOString().slice(0, 10)}\n부가세: 2,000\n합계: 22,000원\n결제수단: 신용카드`

const rate = (ok, total) => (total ? Math.round((ok / total) * 1000) / 10 : 0)
const count = (arr, key) => arr.reduce((acc, x) => ({ ...acc, [x[key]]: (acc[x[key]] || 0) + 1 }), {})
const dayLabel = (iso) => new Date(iso).toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' }).slice(5)

function computeStats(db, userId) {
  const docs = userId ? db.documents.filter((d) => d.user_id === userId) : db.documents
  const ids = new Set(docs.map((d) => d.id))
  const jobs = db.jobs.filter((j) => ids.has(j.document_id))
  const parsed = docs.filter((d) => d.status === 'parsed')
  const failed = docs.filter((d) => d.status === 'failed').length
  const rpaOk = jobs.filter((j) => j.status === 'success').length
  const rpaFail = jobs.filter((j) => j.status === 'failed').length
  const daily = Array.from({ length: 14 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (13 - i))
    return { date: dayLabel(d.toISOString()), parsed: 0, failed: 0, rpa_success: 0, rpa_failed: 0 }
  })
  const byDay = Object.fromEntries(daily.map((d) => [d.date, d]))
  docs.forEach((d) => byDay[dayLabel(d.created_at)] && d.status !== 'uploaded' && byDay[dayLabel(d.created_at)][d.status]++)
  jobs.forEach((j) => byDay[dayLabel(j.created_at)] && byDay[dayLabel(j.created_at)][`rpa_${j.status}`]++)
  const confidences = parsed.map((d) => d.parsed?.confidence).filter((c) => typeof c === 'number')

  const result = {
    documents: {
      total: docs.length,
      parsed: parsed.length,
      failed,
      pending: 0,
      success_rate: rate(parsed.length, parsed.length + failed),
      by_source: count(docs, 'source_type'),
      by_parser: count(docs, 'parser'),
      amount_total: parsed.reduce((sum, d) => sum + (d.parsed?.total_amount || 0), 0),
      avg_confidence: confidences.length ? Math.round((confidences.reduce((a, b) => a + b, 0) / confidences.length) * 100) / 100 : null,
    },
    rpa: { total: jobs.length, success: rpaOk, failed: rpaFail, success_rate: rate(rpaOk, rpaOk + rpaFail), by_target: count(jobs, 'target') },
    daily,
    recent_failures: docs
      .filter((d) => d.status === 'failed')
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .slice(0, 5)
      .map(({ id, filename, error, created_at }) => ({ id, filename, error, created_at })),
  }
  if (!userId) {
    result.users = {
      total: db.users.length,
      admins: db.users.filter((u) => u.role === 'admin').length,
      test_admins: db.users.filter((u) => u.role === 'test_admin').length,
      by_provider: count(db.users, 'provider'),
    }
  }
  return result
}

export async function mockRequest(path, { method, body, token }) {
  await new Promise((r) => setTimeout(r, 250))
  const db = load()
  const [pathname, query = ''] = path.split('?')
  const params = new URLSearchParams(query)
  const route = `${method} ${pathname.replace(/\/\d+/g, '/:id')}`
  const id = Number(pathname.match(/\/(\d+)/)?.[1])
  const done = (value) => (save(db), value)

  if (route === 'GET /api/auth/providers') return { google: false, naver: false, kakao: false, admin_login: false }
  if (route === 'POST /api/auth/admin-login') fail(503, 'Mock 모드에서는 운영 관리자 로그인을 사용할 수 없습니다.')
  if (route === 'POST /api/auth/login') {
    const user = db.users.find((u) => u.email === body.email?.toLowerCase() && u.password && u.password === body.password)
    if (!user) fail(401, '이메일 또는 비밀번호가 올바르지 않습니다.')
    user.last_login_at = now()
    return done({ access_token: tokenFor(user), token_type: 'bearer', user: publicUser(user) })
  }
  if (route === 'POST /api/auth/register') {
    if (!PASSWORD_RE.test(body.password)) fail(422, '비밀번호는 영문 대·소문자, 숫자, 특수문자를 모두 포함해 8자 이상이어야 합니다.')
    if (db.users.some((u) => u.email === body.email.toLowerCase())) fail(409, '이미 가입된 이메일입니다.')
    const user = { id: db.seq.user++, email: body.email.toLowerCase(), name: body.name, password: body.password, role: 'user', plan: 'free', provider: 'local', created_at: now(), last_login_at: now() }
    db.users.push(user)
    return done({ access_token: tokenFor(user), token_type: 'bearer', user: publicUser(user) })
  }

  const user = currentUser(db, token)
  if (user.role === 'test_admin' && method !== 'GET') {
    fail(403, '테스트 관리자 계정은 읽기 전용입니다. 데이터 생성·수정·삭제는 운영 관리자만 할 수 있습니다.')
  }
  const findDoc = () => {
    const doc = db.documents.find((d) => d.id === id && (d.user_id === user.id || ADMIN_ROLES.includes(user.role)))
    if (!doc) fail(404, '문서를 찾을 수 없습니다.')
    return doc
  }

  db.analyses ||= []
  db.seq.analysis ||= 1
  const toolResult = await runTool(route, body)
  if (toolResult) {
    const analysis = { id: db.seq.analysis++, user_id: user.id, engine: 'rules', created_at: now(), ...toolResult }
    db.analyses.push(analysis)
    return done(analysis)
  }
  const findAnalysis = () => {
    const analysis = db.analyses.find((a) => a.id === id && a.user_id === user.id)
    if (!analysis) fail(404, '분석 결과를 찾을 수 없습니다.')
    return analysis
  }

  switch (route) {
    case 'GET /api/tools/analyses': {
      const kind = params.get('kind')
      // eslint-disable-next-line no-unused-vars
      return db.analyses.filter((a) => a.user_id === user.id && (!kind || a.kind === kind)).sort((a, b) => b.id - a.id).slice(0, 50).map(({ result, ...rest }) => rest)
    }
    case 'GET /api/tools/analyses/:id':
      return findAnalysis()
    case 'DELETE /api/tools/analyses/:id': {
      const analysis = findAnalysis()
      db.analyses = db.analyses.filter((a) => a !== analysis)
      return done(null)
    }
    case 'GET /api/auth/me':
      return publicUser(user)
    case 'DELETE /api/auth/me': {
      if (['user@datapick.io', 'admin@datapick.io'].includes(user.email)) fail(403, '공개 체험용 계정은 탈퇴할 수 없습니다.')
      if (user.password && body?.password !== user.password) fail(401, '비밀번호가 일치하지 않습니다.')
      db.users = db.users.filter((u) => u.id !== user.id)
      const docIds = db.documents.filter((d) => d.user_id === user.id).map((d) => d.id)
      db.documents = db.documents.filter((d) => d.user_id !== user.id)
      db.jobs = db.jobs.filter((j) => !docIds.includes(j.document_id))
      db.analyses = (db.analyses || []).filter((a) => a.user_id !== user.id)
      db.erp_connections = (db.erp_connections || []).filter((c) => c.user_id !== user.id)
      return done(null)
    }
    case 'GET /api/billing/plans':
      return { plans: Object.entries(PLANS).map(([id, plan]) => ({ id, ...plan })) }
    case 'GET /api/billing/usage':
      return usageOf(db, user)
    case 'POST /api/billing/subscribe': {
      if (!PLANS[body.plan]) fail(400, '알 수 없는 요금제입니다.')
      user.plan = body.plan
      return done(usageOf(db, user))
    }
    case 'POST /api/billing/cancel': {
      user.plan = 'free'
      return done(usageOf(db, user))
    }
    case 'GET /api/erp/connection': {
      const conn = (db.erp_connections || []).find((c) => c.user_id === user.id)
      // eslint-disable-next-line no-unused-vars
      return conn ? (({ password, ...pub }) => pub)(conn) : null
    }
    case 'PUT /api/erp/connection': {
      if (!planOf(user).erp_connection) fail(403, '고객사 ERP 연동은 Pro 이상 요금제에서 사용할 수 있습니다.')
      db.erp_connections ||= []
      db.seq.erp_connection ||= 1
      const conn = {
        id: db.seq.erp_connection++, user_id: user.id, name: body.name || '우리 회사 ERP',
        erp_url: body.erp_url?.replace(/\/$/, ''), login_url: body.login_url || null,
        username: body.username, password: body.password, has_password: true,
        fields: body.fields || null, updated_at: now(),
      }
      db.erp_connections = db.erp_connections.filter((c) => c.user_id !== user.id).concat(conn)
      // eslint-disable-next-line no-unused-vars
      return done((({ password, ...pub }) => pub)(conn))
    }
    case 'DELETE /api/erp/connection': {
      db.erp_connections = (db.erp_connections || []).filter((c) => c.user_id !== user.id)
      return done(null)
    }
    case 'POST /api/erp/connection/test': {
      const conn = (db.erp_connections || []).find((c) => c.user_id === user.id)
      if (!conn) fail(404, '저장된 ERP 연결 정보가 없습니다.')
      return { ok: true, detail: `로그인 성공 — 세션이 발급되었습니다 (${conn.login_url || conn.erp_url + '/login'})` }
    }
    case 'GET /api/dashboard':
      return computeStats(db, user.id)
    case 'GET /api/documents':
      return db.documents.filter((d) => d.user_id === user.id).sort((a, b) => b.id - a.id).map((d) => withJobs(db, d))
    case 'POST /api/documents/upload': {
      checkQuota(db, user)
      const file = body.get('file')
      const ext = file.name.split('.').pop().toLowerCase()
      const textual = ['txt', 'eml', 'html', 'htm', 'csv', 'md'].includes(ext)
      const doc = { id: db.seq.document++, user_id: user.id, filename: file.name, source_type: ext === 'pdf' ? 'pdf' : textual ? (ext === 'txt' ? 'text' : 'email') : 'image', created_at: now() }
      runParse(doc, textual ? await file.text() : SAMPLE_BY_TYPE(file.name))
      if (!textual && doc.parsed) doc.parser = 'gemini'
      db.documents.push(doc)
      return done(withJobs(db, doc))
    }
    case 'POST /api/documents/text': {
      checkQuota(db, user)
      const doc = { id: db.seq.document++, user_id: user.id, filename: body.title || '이메일 본문', source_type: 'email', created_at: now() }
      runParse(doc, body.text)
      db.documents.push(doc)
      return done(withJobs(db, doc))
    }
    case 'GET /api/documents/ledger.xlsx': {
      const rows = db.jobs.filter((j) => j.target === 'excel' && j.status === 'success').map((j) => db.documents.find((d) => d.id === j.document_id)).filter((d) => d?.user_id === user.id && d.parsed)
      if (!rows.length) fail(404, '아직 엑셀에 적재된 데이터가 없습니다.')
      const csv = ['문서ID,거래처,사업자번호,거래일자,합계금액,부가세', ...rows.map((d) => [d.id, d.parsed.vendor, d.parsed.business_number, d.parsed.date, d.parsed.total_amount, d.parsed.vat].join(','))].join('\n')
      return new Blob(['\ufeff' + csv], { type: 'text/csv' })
    }
    case 'GET /api/documents/:id':
      return withJobs(db, findDoc())
    case 'PATCH /api/documents/:id': {
      const doc = findDoc()
      doc.parsed = { ...doc.parsed, ...body }
      doc.status = 'parsed'
      doc.error = null
      return done(withJobs(db, doc))
    }
    case 'POST /api/documents/:id/reparse': {
      const doc = findDoc()
      runParse(doc, doc.raw_text || '')
      return done(withJobs(db, doc))
    }
    case 'DELETE /api/documents/:id': {
      const doc = findDoc()
      db.documents = db.documents.filter((d) => d !== doc)
      db.jobs = db.jobs.filter((j) => j.document_id !== doc.id)
      return done(null)
    }
    case 'POST /api/documents/:id/rpa': {
      const doc = findDoc()
      if (doc.status !== 'parsed') fail(409, '파싱이 완료된 문서만 RPA 입력을 실행할 수 있습니다.')
      const job = {
        id: db.seq.job++, document_id: doc.id, target: body.target, status: 'success', created_at: now(), finished_at: now(),
        message: body.target === 'excel' ? '엑셀 원장에 적재했습니다. (목업)' : `ERP 입력 완료 (${(db.erp_connections || []).find((c) => c.user_id === user.id) ? 'AC' : 'JV'}-MOCK-${String(db.seq.job).padStart(4, '0')})`,
      }
      db.jobs.push(job)
      return done(job)
    }
  }

  if (!ADMIN_ROLES.includes(user.role)) fail(403, '관리자 권한이 필요합니다.')
  switch (route) {
    case 'GET /api/admin/users': {
      const q = (params.get('q') || '').toLowerCase()
      const role = params.get('role')
      return db.users
        .filter((u) => (!q || u.email.includes(q) || u.name.toLowerCase().includes(q)) && (!role || u.role === role))
        .map((u) => ({ ...publicUser(u), document_count: db.documents.filter((d) => d.user_id === u.id).length }))
    }
    case 'PATCH /api/admin/users/:id/role': {
      const target = db.users.find((u) => u.id === id)
      if (!target) fail(404, '사용자를 찾을 수 없습니다.')
      if (target.id === user.id && body.role !== 'admin') fail(400, '본인의 관리자 권한은 해제할 수 없습니다.')
      if (TEST_ACCOUNT_EMAILS.includes(target.email)) fail(400, '공개된 테스트 계정의 권한은 변경할 수 없습니다.')
      target.role = body.role
      return done(publicUser(target))
    }
    case 'DELETE /api/admin/users/:id': {
      const target = db.users.find((u) => u.id === id)
      if (!target) fail(404, '사용자를 찾을 수 없습니다.')
      if (target.id === user.id) fail(400, '본인 계정은 강퇴할 수 없습니다.')
      if (TEST_ACCOUNT_EMAILS.includes(target.email)) fail(400, '공개된 테스트 계정은 강퇴할 수 없습니다.')
      if (target.role !== 'user') fail(400, '관리자 계정은 권한을 먼저 해제한 뒤 강퇴할 수 있습니다.')
      db.users = db.users.filter((u) => u.id !== target.id)
      const docIds = db.documents.filter((d) => d.user_id === target.id).map((d) => d.id)
      db.documents = db.documents.filter((d) => d.user_id !== target.id)
      db.jobs = db.jobs.filter((j) => !docIds.includes(j.document_id))
      db.analyses = (db.analyses || []).filter((a) => a.user_id !== target.id)
      db.erp_connections = (db.erp_connections || []).filter((c) => c.user_id !== target.id)
      return done(null)
    }
    case 'GET /api/admin/stats':
      return computeStats(db)
  }
  fail(404, `목업 API에 없는 경로입니다: ${route}`)
}

export const resetMockDb = () => localStorage.removeItem(DB_KEY)
