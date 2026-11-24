// Mock 모드용 AI 도구 규칙 엔진. backend/app/services/analyzers.py 의 규칙 경로를 그대로 옮겼다.

const fail = (status, message) => {
  throw Object.assign(new Error(message), { status })
}
const toInt = (v) => (v ? Number(v.replace(/,/g, '')) : null)
const DATE = /(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})/
const iso = (m) => (m ? `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}` : null)
const round1 = (v) => Math.round(v * 10) / 10

// ── 견적서 ──
const QUOTE_ITEM = /^(.+?)\s+(\d+(?:\.\d+)?)\s*([가-힣a-zA-Z㎡]{0,4})\s+([\d,]+)\s+([\d,]+)\s*원?$/
const QUOTE_SKIP = /^(합\s*계|소\s*계|총\s*액|부가세|공급가액|품목|항목)/
const OUTLIER_PCT = 20

function extractQuote(text) {
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
  const items = lines
    .filter((l) => !QUOTE_SKIP.test(l))
    .map((l) => l.match(QUOTE_ITEM))
    .filter(Boolean)
    .map((m) => ({ name: m[1].trim(), quantity: Number(m[2]), unit: m[3] || null, unit_price: toInt(m[4]), amount: toInt(m[5]) }))
  if (!items.length) fail(422, '견적 품목(품목명 · 수량 · 단가 · 금액)을 찾지 못했습니다.')
  const vendor = text.match(/(?:공급자|업체명|상호|견적처|회사명)\s*[:：]\s*(.+)/)?.[1]
  const total = text.match(/(?:합\s*계|총\s*액|견적\s*금액|총\s*견적)[^\d\n]{0,15}([\d,]{3,})/)?.[1]
  const notes = [...text.matchAll(/(?:유효\s*기간|결제\s*조건|하자\s*보수|비고|특이\s*사항)\s*[:：]\s*(.+)/g)].map((m) => m[0])
  return {
    vendor: (vendor || lines.find((l) => !l.includes('견적')) || lines[0]).trim().slice(0, 100),
    date: iso(text.match(DATE)),
    items,
    total_amount: toInt(total) ?? items.reduce((s, i) => s + (i.amount || 0), 0),
    notes: notes.join(' · ').slice(0, 300) || null,
  }
}

const norm = (s) => s.replace(/[\s()[\]{}·,./\-_~]/g, '').toLowerCase()
// 서버는 문자 순서 유사도와 2글자 조각 겹침 중 큰 값을 쓰고, 목업은 2글자 조각 겹침(dice)만 쓴다
function similar(a, b) {
  if (a === b) return 1
  const grams = (x) => new Set([...Array(Math.max(x.length - 1, 0)).keys()].map((i) => x.slice(i, i + 2)))
  const [ga, gb] = [grams(a), grams(b)]
  return ga.size && gb.size ? (2 * [...ga].filter((g) => gb.has(g)).length) / (ga.size + gb.size) : 0
}

function compareQuotes(quotes) {
  const groups = []
  quotes.forEach((q, qi) => {
    for (const item of q.items) {
      const key = norm(item.name)
      const candidates = groups.filter((g) => !(qi in g.cells))
      let best = candidates.sort((x, y) => similar(key, y.key) - similar(key, x.key))[0]
      if (!best || similar(key, best.key) < 0.6) {
        best = { key, name: item.name, cells: {} }
        groups.push(best)
      }
      const price = item.unit_price ?? (item.amount && item.quantity ? Math.round(item.amount / item.quantity) : null)
      best.cells[qi] = { unit_price: price, quantity: item.quantity, unit: item.unit, amount: item.amount }
    }
  })
  const vendors = quotes.map((q, i) => q.vendor || `견적 ${i + 1}`)
  const insights = []
  let outliers = 0
  const rows = groups.map((g) => {
    const prices = Object.values(g.cells).map((c) => c.unit_price).filter(Boolean)
    const low = prices.length ? Math.min(...prices) : null
    const cells = quotes.map((_, qi) => {
      const cell = g.cells[qi]
      if (!cell) return { flag: 'missing' }
      const pct = low && cell.unit_price ? round1((cell.unit_price / low - 1) * 100) : null
      let flag = null
      if (prices.length >= 2 && cell.unit_price === low) flag = 'lowest'
      else if (pct != null && pct >= OUTLIER_PCT) {
        flag = 'outlier'
        outliers++
        insights.push(`'${g.name}' 단가가 ${vendors[qi]} 견적에서 최저가보다 ${pct}% 높습니다.`)
      }
      return { ...cell, diff_pct: pct, flag }
    })
    return { name: g.name, cells, lowest: low }
  })
  const totals = quotes.map((q) => q.total_amount || q.items.reduce((s, i) => s + (i.amount || 0), 0))
  const common = rows.filter((r) => r.cells.every((c) => c.flag !== 'missing'))
  const commonTotals = quotes.map((_, qi) => common.reduce((s, r) => s + (r.cells[qi].amount || 0), 0))
  const cheapest = totals.indexOf(Math.min(...totals))
  const savings = Math.max(...totals) - Math.min(...totals)
  const missing = quotes.map((_, qi) => rows.filter((r) => r.cells[qi].flag === 'missing').map((r) => r.name))
  if (quotes.length >= 2) {
    insights.unshift(`총액은 ${vendors[cheapest]} 견적이 가장 낮습니다. 가장 비싼 견적보다 ${savings.toLocaleString('ko-KR')}원 적습니다.`)
    if (missing[cheapest].length) insights.splice(1, 0, `단, ${vendors[cheapest]} 견적에는 ${missing[cheapest].join(', ')} 항목이 빠져 있어 실제 비용은 더 들 수 있습니다.`)
  }
  missing.forEach((names, qi) => qi !== cheapest && names.length && insights.push(`${vendors[qi]} 견적에는 ${names.join(', ')} 항목이 없습니다.`))
  return {
    vendors, rows, totals, common_totals: commonTotals, common_items: common.length, cheapest, savings, outliers,
    missing: Object.fromEntries(missing.map((names, qi) => [vendors[qi], names]).filter(([, n]) => n.length)),
    outlier_threshold_pct: OUTLIER_PCT, insights,
  }
}

// ── 계약서 ──
const LABELS = {
  auto_renewal: '자동 연장', penalty: '위약금 · 손해배상', termination: '일방 해지 · 변경', liability: '책임 제한 · 면책',
  payment: '대금 · 지연이자', ip: '권리 귀속', non_compete: '경업 금지', confidentiality: '비밀 유지', jurisdiction: '관할 · 분쟁',
}
const CONTRACT_RULES = [
  ['auto_renewal', 'high', /자동\s*(?:으로\s*)?(?:연장|갱신)|동일한\s*조건으로\s*(?:연장|갱신)/, '만료 전에 해지 의사를 알리지 않으면 같은 조건으로 계약이 자동으로 이어집니다.', "해지 통보 기한을 달력에 적어 두고, '서면 합의 시에만 연장'으로 바꿀 수 있는지 확인하세요."],
  ['penalty', 'high', /위약금|위약벌|손해배상\s*(?:액|의)?\s*예정|배액/, '계약을 중간에 끝내거나 약속을 어기면 정해진 돈을 물어야 합니다.', '위약금 산정 기준(남은 기간 전체인지, 실제 손해인지)과 상한이 합리적인지 확인하세요.'],
  ['termination', 'high', /(?:일방적으로|사전\s*통보\s*없이|통지\s*없이|즉시)[^.]{0,20}(?:해지|해제|중단|변경)/, '상대방이 미리 알리지 않고 계약을 끝내거나 내용을 바꿀 수 있습니다.', '해지 사유를 구체적으로 한정하고, 같은 권리가 양쪽 모두에게 있는지 확인하세요.'],
  ['non_compete', 'high', /경업|동종\s*업종[^.]{0,25}(?:금지|하지\s*않|할\s*수\s*없)/, '계약이 끝난 뒤에도 같은 업종의 일을 하지 못하게 제한합니다.', '제한 기간 · 지역 · 업종 범위가 지나치게 넓지 않은지 확인하세요.'],
  ['liability', 'medium', /책임[을도은]?\s*지지\s*않|면책|책임이\s*없/, '문제가 생겨도 상대방이 책임을 지지 않는다는 조항입니다.', '고의 · 중대한 과실까지 면책되는지, 배상 한도가 너무 낮지 않은지 확인하세요.'],
  ['payment', 'medium', /지연\s*(?:손해금|이자)|연체\s*(?:료|이자)|연\s*\d+(?:\.\d+)?\s*%/, '대금을 늦게 내면 추가 이자나 연체료가 붙습니다.', '지연 이율이 법정 이율(상사 연 6%)보다 과도하지 않은지 확인하세요.'],
  ['ip', 'medium', /(?:지식\s*재산권|저작권|소유권)[^.]{0,25}(?:귀속|양도|이전)/, '결과물에 대한 권리가 누구에게 가는지 정한 조항입니다.', '대금을 다 받기 전에 권리가 넘어가지 않는지, 기존에 가진 기술까지 넘어가지 않는지 확인하세요.'],
  ['confidentiality', 'low', /비밀\s*유지|기밀/, '업무 중 알게 된 정보를 외부에 알리면 안 됩니다.', '비밀 정보의 범위와 유지 기간이 명확한지 확인하세요.'],
  ['jurisdiction', 'low', /관할\s*법원|전속\s*관할|중재/, '분쟁이 생기면 어느 법원에서 다툴지 정한 조항입니다.', '상대방 소재지 법원으로만 정해져 있으면 소송 비용이 커질 수 있습니다.'],
]
const POINTS = { high: 3, medium: 2, low: 1 }

function reviewContract(text) {
  if (text.trim().length < 30) fail(422, '계약서 본문이 너무 짧습니다.')
  const heads = [...text.matchAll(/^\s*(제\s*\d+\s*조[^\n]*)/gm)]
  const clauses = heads.length
    ? heads.map((m, i) => {
        const body = text.slice(m.index, heads[i + 1]?.index ?? text.length)
        const head = body.match(/^\s*제\s*\d+\s*조\s*(?:\([^)]*\))?/)
        return { title: head[0].trim(), heading: head[0], body: body.slice(head[0].length), offset: m.index + head[0].length }
      })
    : text.split('\n\n').filter((p) => p.trim()).map((p) => ({ title: p.trim().slice(0, 40), heading: '', body: p, offset: text.indexOf(p) }))
  const found = []
  for (const c of clauses) {
    for (const [category, risk, re, explanation, suggestion] of CONTRACT_RULES) {
      const m = c.body.match(re)
      if (!m && !re.test(c.heading)) continue
      const sentences = [...c.body.matchAll(/[^.。]+(?:[.。]|$)/g)]
      const s = sentences.find((x) => m && x.index <= m.index && m.index < x.index + x[0].length) || sentences[0]
      const raw = s ? s[0] : c.body
      const lead = raw.length - raw.trimStart().length
      const start = c.offset + (s ? s.index : 0) + lead
      found.push({ title: c.title, quote: raw.trim().split(/\s+/).join(' '), category, risk, explanation, suggestion, label: LABELS[category], start, end: start + raw.trim().length })
    }
  }
  const order = { high: 0, medium: 1, low: 2 }
  found.sort((a, b) => order[a.risk] - order[b.risk] || a.start - b.start)
  const counts = { high: 0, medium: 0, low: 0 }
  found.forEach((c) => counts[c.risk]++)
  const score = Math.min(100, found.reduce((s, c) => s + POINTS[c.risk], 0) * 8)
  const overall = counts.high >= 2 || score >= 60 ? 'high' : counts.high || score >= 25 ? 'medium' : 'low'
  const parties = [...text.matchAll(/(\S+(?:\s\S+)?)\s*\(이하\s*["“']?(갑|을|병)["”']?\)/g)].map((m) => `${m[2]}: ${m[1]}`)
  const title = text.split('\n').find((l) => l.trim())?.trim().slice(0, 100) || null
  return { review: { title, parties, summary: null, clauses: found, counts, score, overall }, text: text.slice(0, 30000) }
}

// ── 건강검진 ──
const METRICS = [
  ['systolic_bp', '수축기 혈압', 'mmHg', /수축기\s*혈압|최고\s*혈압|수축기/i, 'lower', ['lower', 120, 140]],
  ['diastolic_bp', '이완기 혈압', 'mmHg', /이완기\s*혈압|최저\s*혈압|이완기/i, 'lower', ['lower', 80, 90]],
  ['fasting_glucose', '공복혈당', 'mg/dL', /공복\s*혈당|Glucose/i, 'lower', ['lower', 100, 126]],
  ['total_cholesterol', '총콜레스테롤', 'mg/dL', /총\s*콜레스테롤|Total\s*Cholesterol/i, 'lower', ['lower', 200, 240]],
  ['ldl', 'LDL 콜레스테롤', 'mg/dL', /\bLDL\b|저밀도/i, 'lower', ['lower', 130, 160]],
  ['hdl', 'HDL 콜레스테롤', 'mg/dL', /\bHDL\b|고밀도/i, 'higher', ['higher', 40, 40]],
  ['triglyceride', '중성지방', 'mg/dL', /중성\s*지방|Triglyceride/i, 'lower', ['lower', 150, 200]],
  ['ast', 'AST(SGOT)', 'U/L', /\bAST\b|SGOT/i, 'lower', ['lower', 41, 51]],
  ['alt', 'ALT(SGPT)', 'U/L', /\bALT\b|SGPT/i, 'lower', ['lower', 36, 46]],
  ['ggt', '감마지티피', 'U/L', /감마\s*-?\s*지티피|감마\s*-?\s*GTP|γ\s*-?\s*GTP|\bGGT\b/i, 'lower', ['lower', 64, 78]],
  ['hemoglobin', '혈색소', 'g/dL', /혈색소|헤모글로빈|Hemoglobin/i, null, ['range', 10, 12, 16.6, 18]],
  ['creatinine', '혈청 크레아티닌', 'mg/dL', /크레아티닌|Creatinine/i, 'lower', ['lower', 1.6, 1.6]],
  ['egfr', 'eGFR', 'mL/min/1.73㎡', /e\s*-?\s*GFR|신사구체\s*여과율/i, 'higher', ['higher', 60, 45]],
  ['bmi', '체질량지수', 'kg/㎡', /체질량\s*지수|\bBMI\b/i, null, ['range', 0, 18.5, 23, 25]],
  ['waist', '허리둘레', 'cm', /허리\s*둘레/i, 'lower', null],
  ['weight', '체중', 'kg', /체중|몸무게/i, null, null],
]
const RANK = { normal: 0, caution: 1, risk: 2 }
const SLABEL = { normal: '정상', caution: '주의', risk: '위험' }

function judge(rule, v) {
  if (v == null || !rule) return null
  const [kind, ...t] = rule
  if (kind === 'lower') return v >= t[1] ? 'risk' : v >= t[0] ? 'caution' : 'normal'
  if (kind === 'higher') return v < t[1] ? 'risk' : v < t[0] ? 'caution' : 'normal'
  if (v < t[0] || v >= t[3]) return 'risk'
  return v < t[1] || v >= t[2] ? 'caution' : 'normal'
}

function extractHealth(text) {
  const metrics = {}
  const bp = text.match(/혈압[^\d\n]{0,15}(\d{2,3})\s*\/\s*(\d{2,3})/)
  if (bp) {
    metrics.systolic_bp = Number(bp[1])
    metrics.diastolic_bp = Number(bp[2])
  }
  for (const line of text.split('\n')) {
    const metric = METRICS.find(([code, , , re]) => !(code in metrics) && re.test(line))
    if (!metric) continue
    const tail = line.includes(':') ? line.slice(line.lastIndexOf(':') + 1) : line.split(metric[3]).pop()
    const n = tail.match(/(\d+(?:\.\d+)?)/)
    if (n) metrics[metric[0]] = Number(n[1])
  }
  if (Object.keys(metrics).length < 2) fail(422, '검사 항목 수치를 찾지 못했습니다. 혈압 · 공복혈당 · 콜레스테롤 등 항목명과 수치가 있는 결과지인지 확인하세요.')
  const date = text.match(new RegExp(`(?:검진일|검사일|수검일|검진\\s*일자)[^\\d\\n]{0,10}${DATE.source}`)) || text.match(DATE)
  return {
    exam_date: iso(date),
    institution: text.match(/(?:검진\s*기관|기관명|병원명)\s*[:：]\s*(.+)/)?.[1].trim() || null,
    metrics: Object.entries(metrics).map(([code, value]) => ({ code, value })),
  }
}

const fmt = (v) => String(Math.round(v * 100) / 100)
function compareHealth(input) {
  const exams = [...input].sort((a, b) => (a.exam_date || '9999').localeCompare(b.exam_date || '9999'))
  const rows = []
  const insights = []
  for (const [code, label, unit, , better, rule] of METRICS) {
    const values = exams.map((e) => e.metrics.find((m) => m.code === code)?.value ?? null)
    if (values.every((v) => v == null)) continue
    const statuses = values.map((v) => judge(rule, v))
    const present = values.map((v, i) => (v == null ? -1 : i)).filter((i) => i >= 0)
    const last = present.at(-1)
    const prev = present.length >= 2 ? present.at(-2) : null
    const delta = prev != null ? Math.round((values[last] - values[prev]) * 100) / 100 : null
    let flag = null
    if (prev != null && statuses[last] && statuses[prev]) {
      const worseDir = (better === 'lower' && delta > 0) || (better === 'higher' && delta < 0)
      if (RANK[statuses[last]] > RANK[statuses[prev]]) flag = 'worsened'
      else if (RANK[statuses[last]] < RANK[statuses[prev]]) flag = 'improved'
      else if (worseDir && RANK[statuses[last]] > 0) flag = 'watch'
    }
    if (flag) {
      const change = `${fmt(values[prev])} → ${fmt(values[last])} ${unit}`
      const [now, before] = [SLABEL[statuses[last]], SLABEL[statuses[prev]]]
      const message = {
        worsened: `${label}: ${change}, '${before}'에서 '${now}' 범위로 나빠졌습니다.`,
        watch: `${label}: 이미 '${now}' 범위인데 ${change}로 더 나빠졌습니다.`,
        improved: `${label}: ${change}, '${now}' 범위로 좋아졌습니다.`,
      }[flag]
      insights.push([flag, message])
    }
    const [kind, ...t] = rule || []
    const reference = !rule ? null : kind === 'lower' ? `${t[0]} 미만` : kind === 'higher' ? `${t[0]} 이상` : `${t[1]} ~ ${t[2]} 미만`
    const limits = !rule ? [] : kind === 'range' ? [t[1], t[2]].filter(Boolean) : [t[0]]
    rows.push({ code, label, unit, better, values, statuses, delta, flag, reference, limits })
  }
  const order = { worsened: 0, watch: 1, improved: 2 }
  const latest = rows.map((r) => r.statuses[r.values.map((v, i) => (v == null ? -1 : i)).filter((i) => i >= 0).at(-1)])
  return {
    dates: exams.map((e) => e.exam_date),
    institutions: exams.map((e) => e.institution),
    rows: rows.sort((a, b) => (order[a.flag] ?? 3) - (order[b.flag] ?? 3)),
    counts: { normal: latest.filter((s) => s === 'normal').length, caution: latest.filter((s) => s === 'caution').length, risk: latest.filter((s) => s === 'risk').length },
    worsened: rows.filter((r) => r.flag === 'worsened' || r.flag === 'watch').length,
    improved: rows.filter((r) => r.flag === 'improved').length,
    insights: insights.sort((a, b) => order[a[0]] - order[b[0]]).map(([, message]) => message),
    disclaimer: '참고용 비교 결과이며 의학적 진단이 아닙니다. 판정 기준은 국민건강보험 일반검진 기준을 단순화했고(성별 구분 없음), 이상 소견은 의료진과 상담하세요.',
  }
}

// ── 공통 ──
const TEXT_EXT = ['txt', 'eml', 'html', 'htm', 'md', 'csv']
async function readText(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  if (!TEXT_EXT.includes(ext)) fail(422, `'${file.name}': Mock 모드에서는 TXT · EML · HTML 만 분석할 수 있습니다. 실제 서버에서는 PDF · 사진도 지원합니다.`)
  const text = await file.text()
  return ext.startsWith('htm') ? new DOMParser().parseFromString(text, 'text/html').body.innerText : text
}
const withName = (file, fn, text) => {
  try {
    return fn(text)
  } catch (err) {
    fail(err.status || 422, `'${file.name}': ${err.message}`)
  }
}

export async function runTool(route, body) {
  if (route === 'POST /api/tools/quote-compare') {
    const files = body.getAll('files')
    if (files.length < 2 || files.length > 5) fail(422, '파일은 2~5개를 올려 주세요.')
    const quotes = []
    for (const f of files) quotes.push({ ...withName(f, extractQuote, await readText(f)), filename: f.name })
    const comparison = compareQuotes(quotes)
    return { kind: 'quote', title: `견적 비교 · ${comparison.vendors.join(' vs ')}`, filenames: files.map((f) => f.name), result: { quotes, comparison } }
  }
  if (route === 'POST /api/tools/contract-review') {
    const file = body.get('file')
    const pasted = body.get('text') || ''
    if (!file && !pasted.trim()) fail(422, '계약서 파일을 올리거나 본문을 붙여 넣어 주세요.')
    const name = file ? file.name : '붙여넣은 계약서'
    const result = file ? withName(file, reviewContract, await readText(file)) : reviewContract(pasted)
    return { kind: 'contract', title: `계약서 검토 · ${result.review.title || name}`, filenames: [name], result }
  }
  if (route === 'POST /api/tools/health-trend') {
    const files = body.getAll('files')
    if (files.length < 1 || files.length > 5) fail(422, '파일은 1~5개를 올려 주세요.')
    const exams = []
    for (const f of files) exams.push({ ...withName(f, extractHealth, await readText(f)), filename: f.name })
    const trend = compareHealth(exams)
    const dates = trend.dates.filter(Boolean)
    return { kind: 'health', title: `건강검진 추이 · ${dates.length ? dates.join(' → ') : `${files.length}회`}`, filenames: files.map((f) => f.name), result: { exams, trend } }
  }
  return null
}
