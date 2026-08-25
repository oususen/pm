const PAGE_SIZES_MM = {
  A4: { width: 297, height: 210 },
  A3: { width: 420, height: 297 },
}

const MM_TO_PT = 72 / 25.4

const DEFAULT_CELL_STYLE = {
  background: '#e5e7eb',
  border: '#d1d5db',
}

const TYPE_STYLE_MAP = {
  location: {
    background: '#e5e7eb',
    border: '#d1d5db',
    accent: null,
  },
  equipment: {
    background: '#c7d2fe',
    border: '#6366f1',
    accent: '#6366f1',
  },
}

const COLOR_STYLE_MAP = {
  red: { background: '#fecaca', border: '#f87171' },
  orange: { background: '#fed7aa', border: '#fb923c' },
  yellow: { background: '#fef08a', border: '#facc15' },
  green: { background: '#bbf7d0', border: '#4ade80' },
  blue: { background: '#bfdbfe', border: '#60a5fa' },
  purple: { background: '#ddd6fe', border: '#a78bfa' },
  pink: { background: '#fbcfe8', border: '#f472b6' },
  brown: { background: '#d7ccc8', border: '#a1887f' },
}

function dataUrlToBytes(dataUrl) {
  const [, base64 = ''] = String(dataUrl || '').split(',')
  const binary = window.atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

function concatUint8Arrays(chunks) {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const merged = new Uint8Array(total)
  let offset = 0
  for (const chunk of chunks) {
    merged.set(chunk, offset)
    offset += chunk.length
  }
  return merged
}

function escapePdfText(value) {
  return String(value || '')
    .replaceAll('\\', '\\\\')
    .replaceAll('(', '\\(')
    .replaceAll(')', '\\)')
}

function buildPdfBytesFromJpeg({
  jpegBytes,
  imageWidth,
  imageHeight,
  pageWidthPt,
  pageHeightPt,
  marginPt = 18,
  title = '',
}) {
  const encoder = new TextEncoder()
  const safePageWidth = Math.max(1, Math.round(pageWidthPt))
  const safePageHeight = Math.max(1, Math.round(pageHeightPt))
  const safeImageWidth = Math.max(1, Math.round(imageWidth))
  const safeImageHeight = Math.max(1, Math.round(imageHeight))
  const availableWidth = Math.max(1, safePageWidth - marginPt * 2)
  const availableHeight = Math.max(1, safePageHeight - marginPt * 2)
  const scale = Math.min(availableWidth / safeImageWidth, availableHeight / safeImageHeight)
  const drawWidth = safeImageWidth * scale
  const drawHeight = safeImageHeight * scale
  const offsetX = (safePageWidth - drawWidth) / 2
  const offsetY = (safePageHeight - drawHeight) / 2
  const escapedTitle = escapePdfText(title)
  const contentStream = [
    'q',
    `${drawWidth.toFixed(3)} 0 0 ${drawHeight.toFixed(3)} ${offsetX.toFixed(3)} ${offsetY.toFixed(3)} cm`,
    '/Im0 Do',
    'Q',
  ].join('\n') + '\n'

  const objects = [
    encoder.encode('1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'),
    encoder.encode('2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'),
    encoder.encode(
      `3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${safePageWidth} ${safePageHeight}] /Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>\nendobj\n`
    ),
    encoder.encode(
      `4 0 obj\n<< /Length ${contentStream.length} >>\nstream\n${contentStream}endstream\nendobj\n`
    ),
    concatUint8Arrays([
      encoder.encode(
        `5 0 obj\n<< /Type /XObject /Subtype /Image /Width ${safeImageWidth} /Height ${safeImageHeight} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegBytes.length} >>\nstream\n`
      ),
      jpegBytes,
      encoder.encode('\nendstream\nendobj\n'),
    ]),
    encoder.encode(
      `6 0 obj\n<< /Title (${escapedTitle}) /Producer (PM stocktake layout PDF) >>\nendobj\n`
    ),
  ]

  const header = encoder.encode('%PDF-1.4\n')
  const offsets = []
  let currentOffset = header.length
  for (const objectBytes of objects) {
    offsets.push(currentOffset)
    currentOffset += objectBytes.length
  }

  const xrefOffset = currentOffset
  const xrefLines = ['xref', `0 ${objects.length + 1}`, '0000000000 65535 f ']
  for (const offset of offsets) {
    xrefLines.push(`${String(offset).padStart(10, '0')} 00000 n `)
  }

  const trailer = encoder.encode(
    `${xrefLines.join('\n')}\ntrailer\n<< /Size ${objects.length + 1} /Root 1 0 R /Info 6 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`
  )

  return concatUint8Arrays([header, ...objects, trailer])
}

function normalizeCell(cell) {
  if (!cell) return null
  if (typeof cell === 'string') {
    return { location: cell, w: 1, h: 1, type: 'location', color: '', fontSize: '' }
  }
  return {
    location: String(cell.location || ''),
    w: Math.max(1, Number(cell.w || 1)),
    h: Math.max(1, Number(cell.h || 1)),
    type: cell.type === 'equipment' ? 'equipment' : 'location',
    color: String(cell.color || ''),
    fontSize: cell.fontSize ? Number(cell.fontSize) : null,
  }
}

function drawVerticalText(ctx, text, x, y, width, height, fontPx) {
  ctx.save()
  ctx.translate(x + width / 2, y + height / 2)
  ctx.rotate(Math.PI / 2)
  ctx.font = `700 ${fontPx}px "Yu Gothic", "Meiryo", sans-serif`
  ctx.fillStyle = '#1f2937'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, 0, 0, height - 12)
  ctx.restore()
}

function drawHorizontalText(ctx, text, x, y, width, height, fontPx) {
  const lines = String(text || '').split('\n')
  const lineHeight = fontPx * 1.18
  const totalHeight = lineHeight * lines.length
  let cursorY = y + (height - totalHeight) / 2 + lineHeight / 2
  ctx.font = `700 ${fontPx}px "Yu Gothic", "Meiryo", sans-serif`
  ctx.fillStyle = '#1f2937'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  for (const line of lines) {
    ctx.fillText(line, x + width / 2, cursorY, width - 8)
    cursorY += lineHeight
  }
}

function wrapTextByCell(text, w, h) {
  const raw = String(text || '').trim()
  if (!raw) return ''
  const capacity = Math.max(3, Math.floor(Math.max(w, h) / 18))
  if (raw.length <= capacity) return raw
  const lines = []
  for (let i = 0; i < raw.length; i += capacity) {
    lines.push(raw.slice(i, i + capacity))
  }
  return lines.slice(0, 3).join('\n')
}

function renderLayoutCanvas({ cols, rows, cells, paperSize }) {
  const page = PAGE_SIZES_MM[paperSize] || PAGE_SIZES_MM.A4
  const baseWidthPx = Math.round(page.width * 14)
  const baseHeightPx = Math.round(page.height * 14)
  const cellSize = Math.max(18, Math.floor(Math.min(baseWidthPx / cols, baseHeightPx / rows)))
  const gridWidth = cellSize * cols
  const gridHeight = cellSize * rows
  const outerMargin = Math.max(12, Math.round(cellSize * 0.35))
  const canvasWidth = gridWidth + outerMargin * 2
  const canvasHeight = gridHeight + outerMargin * 2
  const offsetX = outerMargin
  const offsetY = outerMargin

  const canvas = document.createElement('canvas')
  canvas.width = canvasWidth
  canvas.height = canvasHeight
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('canvas unavailable')
  }

  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)

  ctx.save()
  ctx.strokeStyle = '#93c5fd'
  ctx.lineWidth = Math.max(1, cellSize * 0.025)
  ctx.setLineDash([Math.max(4, cellSize * 0.14), Math.max(2, cellSize * 0.06)])
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      ctx.strokeRect(offsetX + c * cellSize, offsetY + r * cellSize, cellSize, cellSize)
    }
  }
  ctx.restore()

  Object.entries(cells || {}).forEach(([cellKey, rawCell]) => {
    const cell = normalizeCell(rawCell)
    if (!cell || !cell.location) return
    const [r, c] = String(cellKey).split('-').map(Number)
    if (!Number.isFinite(r) || !Number.isFinite(c)) return
    const x = offsetX + c * cellSize
    const y = offsetY + r * cellSize
    const width = cell.w * cellSize
    const height = cell.h * cellSize
    const typeStyle = TYPE_STYLE_MAP[cell.type] || TYPE_STYLE_MAP.location
    const overrideStyle = COLOR_STYLE_MAP[cell.color] || {}
    const background = overrideStyle.background || typeStyle.background || DEFAULT_CELL_STYLE.background
    const border = overrideStyle.border || typeStyle.border || DEFAULT_CELL_STYLE.border

    ctx.fillStyle = background
    ctx.fillRect(x + 1, y + 1, width - 2, height - 2)
    ctx.strokeStyle = border
    ctx.lineWidth = Math.max(1, cellSize * 0.03)
    ctx.setLineDash([])
    ctx.strokeRect(x + 0.5, y + 0.5, width - 1, height - 1)

    const isVertical = cell.h > cell.w
    const fontPx = Math.max(
      10,
      cell.fontSize
        ? Math.round(cell.fontSize * (cellSize / 48))
        : Math.round(Math.min(width, height) * (isVertical ? 0.22 : 0.18))
    )
    const wrappedText = wrapTextByCell(cell.location, width, height)

    if (isVertical) {
      drawVerticalText(ctx, cell.location, x, y, width, height, fontPx)
    } else {
      drawHorizontalText(ctx, wrappedText, x, y, width, height, fontPx)
    }

    if (cell.type === 'equipment') {
      ctx.font = `600 ${Math.max(8, Math.round(fontPx * 0.58))}px "Yu Gothic", "Meiryo", sans-serif`
      ctx.fillStyle = typeStyle.accent || '#6366f1'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'bottom'
      ctx.fillText('設備', x + width / 2, y + height - 4, width - 8)
    }
  })

  return canvas
}

export function createStocktakeLayoutPdfFileName({ areaName, paperSize }) {
  const safeArea = String(areaName || 'layout').trim() || 'layout'
  const timestamp = new Date()
  const yyyy = timestamp.getFullYear()
  const mm = String(timestamp.getMonth() + 1).padStart(2, '0')
  const dd = String(timestamp.getDate()).padStart(2, '0')
  const hh = String(timestamp.getHours()).padStart(2, '0')
  const mi = String(timestamp.getMinutes()).padStart(2, '0')
  const ss = String(timestamp.getSeconds()).padStart(2, '0')
  return `棚卸レイアウト_${safeArea}_${paperSize}_${yyyy}${mm}${dd}${hh}${mi}${ss}.pdf`
}

function resolvePageSizeMm(paperSize, orientation) {
  const base = PAGE_SIZES_MM[paperSize] || PAGE_SIZES_MM.A4
  if (orientation === 'portrait') {
    return { width: Math.min(base.width, base.height), height: Math.max(base.width, base.height) }
  }
  return { width: Math.max(base.width, base.height), height: Math.min(base.width, base.height) }
}

export async function buildStocktakeLayoutPdfBlob({
  areaName,
  paperSize = 'A4',
  orientation = 'landscape',
  cols,
  rows,
  cells,
}) {
  const normalizedPaperSize = PAGE_SIZES_MM[paperSize] ? paperSize : 'A4'
  const normalizedOrientation = orientation === 'portrait' ? 'portrait' : 'landscape'
  const canvas = renderLayoutCanvas({
    cols: Math.max(1, Number(cols || 1)),
    rows: Math.max(1, Number(rows || 1)),
    cells: cells || {},
    paperSize: normalizedPaperSize,
  })
  const jpegDataUrl = canvas.toDataURL('image/jpeg', 0.96)
  const jpegBytes = dataUrlToBytes(jpegDataUrl)
  const page = resolvePageSizeMm(normalizedPaperSize, normalizedOrientation)
  const pdfBytes = buildPdfBytesFromJpeg({
    jpegBytes,
    imageWidth: canvas.width,
    imageHeight: canvas.height,
    pageWidthPt: page.width * MM_TO_PT,
    pageHeightPt: page.height * MM_TO_PT,
    marginPt: 12 * MM_TO_PT,
    title: `棚卸レイアウト ${areaName || ''}`.trim(),
  })
  return new Blob([pdfBytes], { type: 'application/pdf' })
}

export function downloadStocktakeLayoutPdf({ blob, fileName }) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName || 'stocktake-layout.pdf'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
