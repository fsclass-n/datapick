import { createContext, useCallback, useContext, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCircleCheck, faCircleExclamation, faCircleInfo, faXmark } from '@fortawesome/free-solid-svg-icons'

const ToastContext = createContext(() => {})

const STYLES = {
  success: { icon: faCircleCheck, className: 'text-emerald-600' },
  error: { icon: faCircleExclamation, className: 'text-rose-600' },
  info: { icon: faCircleInfo, className: 'text-brand-600' },
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback((id) => setToasts((list) => list.filter((t) => t.id !== id)), [])
  const toast = useCallback(
    (message, type = 'info') => {
      const id = Date.now() + Math.random()
      setToasts((list) => [...list.slice(-3), { id, message, type }])
      setTimeout(() => dismiss(id), 4000)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex flex-col items-center gap-2 px-4" aria-live="polite">
        {toasts.map(({ id, message, type }) => (
          <div key={id} className="card pointer-events-auto flex w-full max-w-sm animate-fade-in items-start gap-3 px-4 py-3 shadow-lg">
            <FontAwesomeIcon icon={STYLES[type].icon} className={`mt-0.5 ${STYLES[type].className}`} />
            <p className="flex-1 text-sm text-slate-700">{message}</p>
            <button onClick={() => dismiss(id)} className="text-slate-400 hover:text-slate-600" aria-label="닫기">
              <FontAwesomeIcon icon={faXmark} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
