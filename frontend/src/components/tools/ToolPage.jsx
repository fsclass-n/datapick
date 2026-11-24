import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight,
  faBolt,
  faClockRotateLeft,
  faCloudArrowUp,
  faFileLines,
  faPaste,
  faRobot,
  faTrashCan,
  faXmark,
} from '@fortawesome/free-solid-svg-icons'
import { IS_MOCK, api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { READ_ONLY_HINT } from '../../utils/roles'
import { dateTime } from '../../utils/format'
import { LoadingBlock, Spinner } from '../ui'

const ACCEPT = '.pdf,.png,.jpg,.jpeg,.webp,.eml,.html,.htm,.txt'
const EXTENSIONS = ACCEPT.split(',')

export function ToolHero({ tool }) {
  return (
    <section className="relative overflow-hidden rounded-3xl bg-ink text-white">
      <img src={tool.image} alt="" className="absolute inset-0 size-full object-cover opacity-35" />
      <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/90 to-ink/30" />
      <div className="relative grid gap-8 px-6 py-10 sm:px-10 sm:py-12 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold tracking-[0.18em] text-gold-400 uppercase">
            <FontAwesomeIcon icon={tool.icon} /> {tool.eyebrow}
          </p>
          <h1 className="mt-3 text-3xl font-bold text-white sm:text-4xl">{tool.name}</h1>
          <p className="mt-2 font-heading text-lg text-white/90">{tool.headline}</p>
          <p className="mt-4 max-w-xl text-body text-white/70">{tool.tagline}</p>
        </div>
        <ol className="space-y-3 self-end">
          {tool.steps.map((step, i) => (
            <li key={step} className="flex items-center gap-3 rounded-xl bg-white/10 px-4 py-3 text-sm backdrop-blur">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-gold-500 font-heading text-xs font-bold text-ink">{i + 1}</span>
              {step}
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

function Uploader({ tool, onCreated }) {
  const toast = useToast()
  const { readOnly } = useAuth()
  const [files, setFiles] = useState([])
  const [mode, setMode] = useState('file')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)
  const single = tool.max === 1

  function addFiles(list) {
    const valid = list.filter((f) => EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext)))
    if (valid.length < list.length) toast('PDF, 이미지, EML, HTML, TXT 파일만 올릴 수 있습니다.', 'error')
    const merged = single ? valid.slice(0, 1) : [...files, ...valid.filter((f) => !files.some((p) => p.name === f.name))]
    if (merged.length > tool.max) toast(`최대 ${tool.max}개까지 올릴 수 있습니다.`, 'error')
    setFiles(merged.slice(0, tool.max))
  }

  async function submit(chosen, pasted) {
    if (!pasted && chosen.length < tool.min) return toast(`파일을 ${tool.min}개 이상 올려 주세요.`, 'error')
    const form = new FormData()
    if (pasted) form.append('text', pasted)
    else chosen.forEach((f) => form.append(tool.field, f))
    setBusy(true)
    try {
      const analysis = await api(tool.endpoint, { method: 'POST', body: form })
      toast('분석을 완료했습니다.', 'success')
      onCreated(analysis)
      setFiles([])
      setText('')
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function runSample() {
    setBusy(true)
    try {
      const sampleFiles = await Promise.all(
        tool.samples.map(async ([path, name]) => new File([await (await fetch(`/samples/${path}`)).blob()], name, { type: 'text/plain' })),
      )
      setMode('file')
      setFiles(sampleFiles)
      await submit(sampleFiles, '')
    } catch (err) {
      toast(err.message, 'error')
      setBusy(false)
    }
  }

  const disabled = busy || readOnly
  const tabClass = (id) =>
    `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold transition ${mode === id ? 'bg-ink text-white' : 'text-slate-500 hover:bg-white'}`
  const dropClass = readOnly
    ? 'cursor-not-allowed border-slate-200 bg-slate-50 opacity-60'
    : dragging
      ? `cursor-pointer ${tool.accent.border} ${tool.accent.soft}`
      : 'dot-grid cursor-pointer border-slate-200 hover:border-slate-300'

  return (
    <section className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-heading font-semibold">문서 올리기</h2>
          <p className="mt-0.5 text-caption text-slate-500">{tool.input} · 파일당 최대 10MB</p>
        </div>
        <button
          type="button"
          onClick={runSample}
          disabled={disabled}
          title={readOnly ? READ_ONLY_HINT : '가상 샘플 문서로 바로 실행합니다'}
          className="btn border border-gold-200 bg-gold-50 text-gold-700 hover:bg-gold-100"
        >
          <FontAwesomeIcon icon={faBolt} /> 샘플로 바로 체험
        </button>
      </div>

      {tool.allowText && (
        <div className="mt-4 inline-flex gap-1 rounded-xl bg-slate-100 p-1">
          <button type="button" className={tabClass('file')} onClick={() => setMode('file')}>
            <FontAwesomeIcon icon={faCloudArrowUp} /> 파일
          </button>
          <button type="button" className={tabClass('text')} onClick={() => setMode('text')}>
            <FontAwesomeIcon icon={faPaste} /> 본문 붙여넣기
          </button>
        </div>
      )}

      {mode === 'text' ? (
        <textarea
          className="input paper-lines mt-4 min-h-56 font-mono text-[13px] leading-8"
          placeholder="계약서 본문을 붙여 넣으세요. '제1조, 제2조 …' 형태면 조항 단위로 더 정확하게 나눕니다."
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={readOnly}
        />
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            if (!disabled) addFiles([...e.dataTransfer.files])
          }}
          onClick={() => !disabled && inputRef.current.click()}
          aria-disabled={disabled}
          title={readOnly ? READ_ONLY_HINT : undefined}
          className={`mt-4 flex flex-col items-center rounded-2xl border-2 border-dashed px-6 py-9 text-center transition ${dropClass}`}
        >
          <span className={`mb-3 flex size-14 items-center justify-center rounded-2xl text-xl ${tool.accent.soft} ${tool.accent.icon}`}>
            <FontAwesomeIcon icon={tool.icon} />
          </span>
          <p className="font-heading font-semibold text-slate-800">파일을 끌어다 놓거나 클릭해서 선택</p>
          <p className="mt-1 text-sm text-slate-500">{single ? '1개' : `${tool.min}~${tool.max}개`}를 올려 주세요</p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            multiple={!single}
            hidden
            onChange={(e) => {
              addFiles([...e.target.files])
              e.target.value = ''
            }}
          />
        </div>
      )}

      {mode === 'file' && files.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2">
          {files.map((f) => (
            <li key={f.name} className="flex items-center gap-2 rounded-full border border-slate-200 bg-white py-1 pr-1 pl-3 text-sm text-slate-700">
              <FontAwesomeIcon icon={faFileLines} className="text-slate-400" />
              <span className="max-w-52 truncate">{f.name}</span>
              <button
                type="button"
                onClick={() => setFiles((list) => list.filter((x) => x !== f))}
                className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                aria-label={`${f.name} 제거`}
              >
                <FontAwesomeIcon icon={faXmark} className="text-xs" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <p className="text-caption text-slate-400">
          {IS_MOCK ? 'Mock 모드: TXT · EML · HTML 만 규칙 엔진으로 분석합니다.' : '원본 파일은 저장하지 않고 분석 결과만 보관합니다.'}
        </p>
        <button
          type="button"
          onClick={() => submit(files, mode === 'text' ? text.trim() : '')}
          disabled={disabled}
          title={readOnly ? READ_ONLY_HINT : undefined}
          className={`btn px-5 text-white ${tool.accent.solid}`}
        >
          {busy ? <Spinner /> : <FontAwesomeIcon icon={faRobot} />}
          {busy ? 'AI가 읽는 중…' : '분석 실행'}
          {!busy && <FontAwesomeIcon icon={faArrowRight} className="text-xs" />}
        </button>
      </div>
    </section>
  )
}

function History({ items, currentId, onSelect, onDelete }) {
  const { readOnly } = useAuth()
  return (
    <aside className="card overflow-hidden">
      <h2 className="flex items-center gap-2 border-b border-slate-100 px-5 py-4 text-sm font-semibold text-slate-700">
        <FontAwesomeIcon icon={faClockRotateLeft} className="text-slate-400" /> 최근 분석
      </h2>
      {!items ? (
        <LoadingBlock />
      ) : items.length ? (
        <ul className="max-h-[26rem] divide-y divide-slate-100 overflow-y-auto">
          {items.map((a) => (
            <li key={a.id} className={`group flex items-start gap-2 px-4 py-3 ${a.id === currentId ? 'bg-gold-50' : 'hover:bg-slate-50'}`}>
              <button type="button" onClick={() => onSelect(a.id)} className="min-w-0 flex-1 text-left">
                <p className="truncate text-sm font-medium text-slate-800">{a.title}</p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {dateTime(a.created_at)} · {a.engine === 'gemini' ? 'Gemini' : '규칙 엔진'}
                </p>
              </button>
              {!readOnly && (
                <button
                  type="button"
                  onClick={() => onDelete(a.id)}
                  className="rounded-md p-1.5 text-slate-300 opacity-0 transition group-hover:opacity-100 hover:bg-rose-50 hover:text-rose-600 focus:opacity-100"
                  aria-label="분석 기록 삭제"
                >
                  <FontAwesomeIcon icon={faTrashCan} className="text-xs" />
                </button>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="px-5 py-8 text-center text-sm text-slate-400">아직 분석 기록이 없습니다.</p>
      )}
    </aside>
  )
}

const KPI_TONES = {
  slate: 'border-slate-200 bg-white',
  good: 'border-emerald-200 bg-emerald-50/70',
  bad: 'border-rose-200 bg-rose-50/70',
  warn: 'border-amber-200 bg-amber-50/70',
  ink: 'border-ink bg-ink',
}

export function KpiCard({ label, value, sub, tone = 'slate', icon }) {
  const dark = tone === 'ink'
  return (
    <div className={`rounded-2xl border p-4 ${KPI_TONES[tone]}`}>
      <p className={`flex items-center gap-1.5 text-caption ${dark ? 'text-white/70' : 'text-slate-500'}`}>
        {icon && <FontAwesomeIcon icon={icon} className="text-xs" />} {label}
      </p>
      <p className={`mt-1 font-heading text-2xl font-bold ${dark ? 'text-white' : 'text-slate-900'}`}>{value}</p>
      {sub && <p className={`mt-0.5 truncate text-xs ${dark ? 'text-gold-200' : 'text-slate-500'}`}>{sub}</p>}
    </div>
  )
}

export function Insights({ items, icon, title = '핵심 요약' }) {
  if (!items?.length) return null
  return (
    <section className="card p-5">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
        {icon && <FontAwesomeIcon icon={icon} className="text-gold-500" />} {title}
      </h3>
      <ul className="space-y-2">
        {items.map((s, i) => (
          <li key={s} className={`flex gap-3 rounded-xl px-3.5 py-2.5 text-sm ${i === 0 ? 'bg-gold-50 font-medium text-slate-900' : 'bg-slate-50 text-slate-700'}`}>
            <span className="mt-0.5 font-heading text-xs font-bold text-gold-600">{String(i + 1).padStart(2, '0')}</span>
            {s}
          </li>
        ))}
      </ul>
    </section>
  )
}

/** 도구 공통 페이지: 히어로 · 업로드 · 최근 분석 · 결과 */
export default function ToolPage({ tool, Result }) {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const [history, setHistory] = useState(null)
  const [current, setCurrent] = useState(null)
  const resultRef = useRef(null)
  const id = Number(params.get('id')) || null

  const reloadHistory = useCallback(() => {
    api(`/api/tools/analyses?kind=${tool.id}`).then(setHistory).catch((err) => toast(err.message, 'error'))
  }, [tool.id, toast])

  useEffect(reloadHistory, [reloadHistory])

  const loading = Boolean(id) && current?.id !== id

  useEffect(() => {
    if (!id || current?.id === id) return
    api(`/api/tools/analyses/${id}`)
      .then(setCurrent)
      .catch((err) => {
        toast(err.message, 'error')
        setParams({}, { replace: true })
      })
  }, [id, current?.id, toast, setParams])

  useEffect(() => {
    if (current) resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [current])

  function handleCreated(analysis) {
    setCurrent(analysis)
    setParams({ id: String(analysis.id) })
    reloadHistory()
  }

  async function handleDelete(analysisId) {
    try {
      await api(`/api/tools/analyses/${analysisId}`, { method: 'DELETE' })
      setHistory((list) => list.filter((a) => a.id !== analysisId))
      if (current?.id === analysisId) {
        setCurrent(null)
        setParams({})
      }
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <ToolHero tool={tool} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <Uploader tool={tool} onCreated={handleCreated} />
        <History items={history} currentId={current?.id} onSelect={(sel) => setParams({ id: String(sel) })} onDelete={handleDelete} />
      </div>
      <div ref={resultRef} className="scroll-mt-20">
        {loading ? (
          <LoadingBlock />
        ) : (
          current && (
            <div className="animate-fade-in space-y-6">
              <div className="flex flex-wrap items-end justify-between gap-2 border-b border-slate-200 pb-3">
                <div>
                  <p className="eyebrow">분석 결과</p>
                  <h2 className="mt-1 text-2xl font-bold">{current.title}</h2>
                </div>
                <p className="text-caption text-slate-500">
                  {current.filenames.join(' · ')} · {current.engine === 'gemini' ? 'Gemini 추출 + 규칙 판정' : '규칙 엔진'} · {dateTime(current.created_at)}
                </p>
              </div>
              <Result result={current.result} />
            </div>
          )
        )}
      </div>
    </div>
  )
}
