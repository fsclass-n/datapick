import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faFeatherPointed } from '@fortawesome/free-solid-svg-icons'

export default function Logo({ light = false, to = '/' }) {
  return (
    <Link to={to} className="flex items-center gap-2.5" aria-label="dataquill 메인으로">
      <span className="flex size-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-md shadow-brand-600/30">
        <FontAwesomeIcon icon={faFeatherPointed} />
      </span>
      <span className={`font-heading text-lg font-bold tracking-tight ${light ? 'text-white' : 'text-slate-900'}`}>dataquill</span>
    </Link>
  )
}
