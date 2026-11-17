import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowsRotate,
  faCloudArrowUp,
  faDownload,
  faEnvelope,
  faFileExcel,
  faFloppyDisk,
  faInbox,
  faKeyboard,
  faTrashCan,
  faWandMagicSparkles,
  faXmark,
} from '@fortawesome/free-solid-svg-icons'
import { IS_MOCK, api, download } from '../api/client'
import { useToast } from '../context/ToastContext'
import { Badge, EmptyState, LoadingBlock, PageHeader, Spinner } from '../components/ui'
import { DOC_TYPE_LABELS, SOURCE_LABELS, dateTime, won } from '../utils/format'
import { sourceIcon } from '../utils/icons'

const ACCEPT = '.pdf,.png,.jpg,.jpeg,.webp,.eml,.html,.htm,.txt'
const SAMPLE_EMAIL = `From: billing@cloudvendor.co.kr
Subject: [청구서] 2026년 11월 클라우드 서비스 이용료

안녕하세요, 클라우드벤더(주)입니다.
11월 서비스 이용료를 아래와 같이 청구드립니다.

거래처: 클라우드벤더(주)
사업자번호: 220-81-12345
청구일: 2026-11-01
공급가액: 300,000원
부가세: 30,000
청구금액: 330,000원
결제수단: 계좌이체`

const FIELDS = [
  { key: 'vendor', label: '거래처' },
  { key: 'business_number', label: '사업자번호' },
  { key: 'date', label: '거래일자', type: 'date' },
  { key: 'total_amount', label: '합계금액', type: 'number' },
  { key: 'vat', label: '부가세', type: 'number' },
  { key: 'payment_method', label: '결제수단' },
  { key: 'summary', label: '적요', wide: true },
]

function Intake({ onCreated }) {
  const toast = useToast()
  const [tab, setTab] = useState('file')
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [email, setEmail] = useState({ title: '', text: '' })
  const inputRef = useRef(null)

  async function run(promise) {
    setBusy(true)
    try {
      const doc = await promise
      toast(doc.status === 'parsed' ? `'${doc.filename}' 해석 완료` : `'${doc.filename}' 해석 실패: ${doc.error}`, doc.status === 'parsed' ? 'success' : 'error')
      onCreated(doc)
      return doc
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function uploadFiles(files) {
    for (const file of files) {
      const form = new FormData()
      form.append('file', file)
      await run(api('/api/documents/upload', { method: 'POST', body: form }))
    }
  }

  async function submitEmail(e) {
    e.preventDefault()
    if (!email.text.trim()) return toast('이메일 본문을 입력해 주세요.', 'error')
    const doc = await run(api('/api/documents/text', { method: 'POST', body: { title: email.title || '이메일 본문', text: email.text } }))
    if (doc) setEmail({ title: '', text: '' })
  }

  const tabClass = (id) =>
    `flex items-center gap-2 border-b-2 px-1 pb-3 text-sm font-semibold transition ${
      tab === id ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-700'
    }`

  return (
    <section className="card p-5">
      <div className="mb-5 flex gap-6 border-b border-slate-100">
        <button className={tabClass('file')} onClick={() => setTab('file')}>
          <FontAwesomeIcon icon={faCloudArrowUp} /> 파일 업로드
        </button>
        <button className={tabClass('email')} onClick={() => setTab('email')}>
          <FontAwesomeIcon icon={faEnvelope} /> 이메일 본문
        </button>
      </div>

      {tab === 'file' ? (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            uploadFiles([...e.dataTransfer.files])
          }}
          onClick={() => !busy && inputRef.current.click()}
          className={`flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging ? 'border-brand-500 bg-brand-50' : 'border-slate-200 hover:border-brand-300 hover:bg-slate-50'
          }`}
        >
          <span className="mb-3 flex size-14 items-center justify-center rounded-2xl bg-brand-50 text-xl text-brand-600">
            {busy ? <Spinner /> : <FontAwesomeIcon icon={faCloudArrowUp} />}
          </span>
          <p className="font-heading font-semibold text-slate-800">{busy ? 'AI가 문서를 해석하고 있습니다…' : '파일을 끌어다 놓거나 클릭해서 선택'}</p>
          <p className="mt-1 text-sm text-slate-500">PDF 영수증 · 이미지(JPG/PNG) · EML/HTML 메일 · TXT, 최대 10MB</p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            multiple
            hidden
            onChange={(e) => {
              uploadFiles([...e.target.files])
              e.target.value = ''
            }}
          />
        </div>
      ) : (
        <form onSubmit={submitEmail} className="space-y-3">
          <input className="input" placeholder="제목 (예: 11월 클라우드 청구 메일)" value={email.title} onChange={(e) => setEmail({ ...email, title: e.target.value })} />
          <textarea
            className="input min-h-44 font-mono text-[13px]"
            placeholder="거래 관련 이메일 본문(텍스트 또는 HTML)을 붙여 넣으세요."
            value={email.text}
            onChange={(e) => setEmail({ ...email, text: e.target.value })}
          />
          <div className="flex flex-wrap justify-between gap-2">
            <button type="button" className="btn-ghost" onClick={() => setEmail({ title: '11월 클라우드 청구 메일', text: SAMPLE_EMAIL })}>
              <FontAwesomeIcon icon={faKeyboard} /> 샘플 채우기
            </button>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? <Spinner /> : <FontAwesomeIcon icon={faWandMagicSparkles} />} AI 해석 실행
            </button>
          </div>
        </form>
      )}
    </section>
  )
}

function DocumentDetail({ docId, onChanged, onDeleted, onClose }) {
  const toast = useToast()
  const [doc, setDoc] = useState(null)
  const [draft, setDraft] = useState({})
  const [busy, setBusy] = useState(null)

  const apply = useCallback(
    (data) => {
      setDoc(data)
      setDraft(data.parsed || {})
      onChanged?.(data)
    },
    [onChanged],
  )

  useEffect(() => {
    api(`/api/documents/${docId}`)
      .then((data) => {
        setDoc(data)
        setDraft(data.parsed || {})
      })
      .catch((err) => toast(err.message, 'error'))
  }, [docId, toast])

  async function action(name, fn) {
    setBusy(name)
    try {
      await fn()
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(null)
    }
  }

  const save = () =>
    action('save', async () => {
      const body = Object.fromEntries(FIELDS.map(({ key, type }) => [key, type === 'number' ? (draft[key] === '' || draft[key] == null ? null : Number(draft[key])) : draft[key] || null]))
      apply(await api(`/api/documents/${docId}`, { method: 'PATCH', body }))
      toast('검수 내용을 저장했습니다.', 'success')
    })

  const reparse = () =>
    action('reparse', async () => {
      const data = await api(`/api/documents/${docId}/reparse`, { method: 'POST' })
      apply(data)
      toast(data.status === 'parsed' ? '재해석을 완료했습니다.' : data.error, data.status === 'parsed' ? 'success' : 'error')
    })

  const runRpa = (target) =>
    action(target, async () => {
      const job = await api(`/api/documents/${docId}/rpa`, { method: 'POST', body: { target } })
      toast(job.message, job.status === 'success' ? 'success' : 'error')
      apply(await api(`/api/documents/${docId}`))
    })

  const remove = () =>
    action('delete', async () => {
      if (!window.confirm('이 문서를 삭제할까요?')) return
      await api(`/api/documents/${docId}`, { method: 'DELETE' })
      toast('문서를 삭제했습니다.', 'success')
      onDeleted(docId)
    })

  if (!doc) return <div className="card"><LoadingBlock /></div>
  const parsed = doc.status === 'parsed'

  return (
    <section className="card animate-fade-in overflow-hidden">
      <div className="flex items-start gap-3 border-b border-slate-100 p-5">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
          <FontAwesomeIcon icon={sourceIcon(doc.source_type)} />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-base font-semibold">{doc.filename}</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {SOURCE_LABELS[doc.source_type]} · {dateTime(doc.created_at)} · 파서 {doc.parser || '-'}
            {doc.parsed?.confidence != null && ` · 신뢰도 ${Math.round(doc.parsed.confidence * 100)}%`}
          </p>
        </div>
        <Badge status={doc.status} />
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600" aria-label="상세 닫기">
          <FontAwesomeIcon icon={faXmark} />
        </button>
      </div>

      <div className="space-y-5 p-5">
        {doc.error && <p className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{doc.error}</p>}

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">추출 결과 검수</h3>
            {doc.parsed?.document_type && <Badge tone="brand">{DOC_TYPE_LABELS[doc.parsed.document_type]}</Badge>}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {FIELDS.map(({ key, label, type, wide }) => (
              <label key={key} className={wide ? 'sm:col-span-2' : ''}>
                <span className="mb-1 block text-xs font-medium text-slate-500">{label}</span>
                <input
                  className="input py-2"
                  type={type || 'text'}
                  value={draft[key] ?? ''}
                  onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
                />
              </label>
            ))}
          </div>
        </div>

        {doc.parsed?.items?.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold">품목</h3>
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs text-slate-500">
                  <tr><th className="px-3 py-2 text-left">품목</th><th className="px-3 py-2 text-right">수량</th><th className="px-3 py-2 text-right">단가</th><th className="px-3 py-2 text-right">금액</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {doc.parsed.items.map((item, i) => (
                    <tr key={i}><td className="px-3 py-2">{item.name}</td><td className="px-3 py-2 text-right">{item.quantity ?? '-'}</td><td className="px-3 py-2 text-right">{won(item.unit_price)}</td><td className="px-3 py-2 text-right">{won(item.amount)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {doc.raw_text && (
          <details className="group rounded-lg border border-slate-200">
            <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-slate-600">원문 텍스트 (OCR/추출 결과)</summary>
            <pre className="max-h-56 overflow-auto border-t border-slate-100 bg-slate-50 p-3 text-xs whitespace-pre-wrap text-slate-600">{doc.raw_text}</pre>
          </details>
        )}

        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" onClick={save} disabled={!!busy}>
            {busy === 'save' ? <Spinner /> : <FontAwesomeIcon icon={faFloppyDisk} />} 검수 저장
          </button>
          <button className="btn-secondary" onClick={reparse} disabled={!!busy}>
            {busy === 'reparse' ? <Spinner /> : <FontAwesomeIcon icon={faArrowsRotate} />} 재해석
          </button>
          <button className="btn-ghost ml-auto text-rose-600 hover:bg-rose-50" onClick={remove} disabled={!!busy}>
            <FontAwesomeIcon icon={faTrashCan} /> 삭제
          </button>
        </div>

        <div className="rounded-xl bg-slate-50 p-4">
          <h3 className="mb-1 text-sm font-semibold">RPA 자동 입력</h3>
          <p className="mb-3 text-xs text-slate-500">검수한 값을 엑셀 원장에 적재하거나, Playwright 로봇이 ERP 전표 화면에 직접 타이핑합니다.</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <button className="btn-primary bg-emerald-600 hover:bg-emerald-700" onClick={() => runRpa('excel')} disabled={!parsed || !!busy}>
              {busy === 'excel' ? <Spinner /> : <FontAwesomeIcon icon={faFileExcel} />} 엑셀 원장 적재
            </button>
            <button className="btn-primary" onClick={() => runRpa('erp')} disabled={!parsed || !!busy}>
              {busy === 'erp' ? <Spinner /> : <FontAwesomeIcon icon={faKeyboard} />} ERP 자동 타이핑
            </button>
          </div>
          {doc.jobs?.length > 0 && (
            <ul className="mt-4 space-y-2">
              {[...doc.jobs].reverse().map((job) => (
                <li key={job.id} className="flex items-start gap-2 text-xs">
                  <Badge status={job.status} />
                  <span className="font-semibold text-slate-600 uppercase">{job.target}</span>
                  <span className="flex-1 text-slate-500">{job.message}</span>
                  <span className="text-slate-400">{dateTime(job.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  )
}

export default function Documents() {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const [docs, setDocs] = useState(null)
  const [filter, setFilter] = useState('')
  const selected = Number(params.get('id')) || null
  const select = (id) => setParams(id ? { id } : {}, { replace: true })

  useEffect(() => {
    api('/api/documents').then(setDocs).catch((err) => toast(err.message, 'error'))
  }, [toast])

  const upsert = useCallback((doc) => setDocs((list) => [doc, ...(list || []).filter((d) => d.id !== doc.id)].sort((a, b) => b.id - a.id)), [])

  const downloadLedger = () =>
    download('/api/documents/ledger.xlsx', IS_MOCK ? 'dataquill_ledger.csv' : 'dataquill_ledger.xlsx').catch((err) => toast(err.message, 'error'))

  const visible = (docs || []).filter((d) => !filter || d.status === filter)

  return (
    <>
      <PageHeader
        eyebrow="Automation"
        title="문서 처리"
        description="비정형 문서를 업로드하면 OCR + Gemini 가 해석하고, 검수 후 RPA 로 ERP·엑셀에 자동 입력합니다."
        actions={
          <button className="btn-secondary" onClick={downloadLedger}>
            <FontAwesomeIcon icon={faDownload} /> 엑셀 원장 다운로드
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-3">
          <Intake
            onCreated={(doc) => {
              upsert(doc)
              select(doc.id)
            }}
          />

          <section className="card overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
              <h2 className="text-base font-semibold">처리 내역 {docs && <span className="text-slate-400">{visible.length}</span>}</h2>
              <div className="flex gap-1 rounded-lg bg-slate-100 p-1 text-xs font-semibold">
                {[['', '전체'], ['parsed', '완료'], ['failed', '실패']].map(([value, label]) => (
                  <button key={value} onClick={() => setFilter(value)} className={`rounded-md px-3 py-1.5 transition ${filter === value ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}>
                    {label}
                  </button>
                ))}
              </div>
            </div>
            {!docs ? (
              <LoadingBlock />
            ) : visible.length ? (
              <ul className="max-h-[560px] divide-y divide-slate-100 overflow-y-auto">
                {visible.map((doc) => (
                  <li key={doc.id}>
                    <button
                      onClick={() => select(doc.id)}
                      className={`flex w-full items-center gap-4 px-5 py-3.5 text-left transition ${selected === doc.id ? 'bg-brand-50/70' : 'hover:bg-slate-50'}`}
                    >
                      <FontAwesomeIcon icon={sourceIcon(doc.source_type)} className="w-4 text-slate-400" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-slate-800">{doc.parsed?.vendor || doc.filename}</p>
                        <p className="truncate text-xs text-slate-500">{doc.filename} · {dateTime(doc.created_at)}</p>
                      </div>
                      <span className="hidden text-sm font-semibold text-slate-800 sm:block">{won(doc.parsed?.total_amount)}</span>
                      {doc.jobs?.some((j) => j.status === 'success') && <Badge tone="brand">RPA</Badge>}
                      <Badge status={doc.status} />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState icon={faInbox} title="표시할 문서가 없습니다" description="위에서 파일을 올리거나 이메일 본문을 붙여 넣어 보세요." />
            )}
          </section>
        </div>

        <div className="lg:col-span-2">
          <div className="lg:sticky lg:top-24">
            {selected ? (
              <DocumentDetail
                key={selected}
                docId={selected}
                onChanged={upsert}
                onClose={() => select(null)}
                onDeleted={(id) => {
                  setDocs((list) => list.filter((d) => d.id !== id))
                  select(null)
                }}
              />
            ) : (
              <div className="card">
                <EmptyState icon={faWandMagicSparkles} title="문서를 선택하세요" description="목록에서 문서를 선택하면 AI 추출 결과를 검수하고 RPA 입력을 실행할 수 있습니다." />
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
