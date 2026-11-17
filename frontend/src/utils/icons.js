import { faEnvelopeOpenText, faFileImage, faFileLines, faFilePdf } from '@fortawesome/free-solid-svg-icons'

export const SOURCE_ICONS = { pdf: faFilePdf, image: faFileImage, email: faEnvelopeOpenText, text: faFileLines }
export const sourceIcon = (source) => SOURCE_ICONS[source] || faFileLines
