import QRCode from 'qrcode'

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function wrapLabelText(value, maxChars = 15, maxLines = 2) {
  const text = String(value || '').trim()
  if (!text) return ['']

  const lines = []
  for (let i = 0; i < text.length && lines.length < maxLines; i += maxChars) {
    lines.push(text.slice(i, i + maxChars))
  }
  if (text.length > maxChars * maxLines && lines.length) {
    const lastIndex = lines.length - 1
    lines[lastIndex] = `${lines[lastIndex].slice(0, Math.max(0, maxChars - 1))}…`
  }
  return lines
}

function dataUrlToBlob(dataUrl) {
  const [header, base64 = ''] = String(dataUrl || '').split(',')
  const mime = /data:(.*?);base64/.exec(header)?.[1] || 'image/png'
  const binary = window.atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return new Blob([bytes], { type: mime })
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

function buildPdfBytesFromJpeg({ jpegBytes, width, height }) {
  const encoder = new TextEncoder()
  const safeWidth = Math.max(1, Math.round(width || 1))
  const safeHeight = Math.max(1, Math.round(height || 1))
  const contentStream = `q\n${safeWidth} 0 0 ${safeHeight} 0 0 cm\n/Im0 Do\nQ\n`

  const objects = [
    encoder.encode('1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'),
    encoder.encode('2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'),
    encoder.encode(
      `3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${safeWidth} ${safeHeight}] /Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>\nendobj\n`
    ),
    encoder.encode(
      `4 0 obj\n<< /Length ${contentStream.length} >>\nstream\n${contentStream}endstream\nendobj\n`
    ),
    concatUint8Arrays([
      encoder.encode(
        `5 0 obj\n<< /Type /XObject /Subtype /Image /Width ${safeWidth} /Height ${safeHeight} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegBytes.length} >>\nstream\n`
      ),
      jpegBytes,
      encoder.encode('\nendstream\nendobj\n'),
    ]),
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
    `${xrefLines.join('\n')}\ntrailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`
  )

  return concatUint8Arrays([header, ...objects, trailer])
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('image load failed'))
    img.src = src
  })
}

function buildLuckJinglePreviewHtml({ title, description, fileName, imageDataUrl }) {
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escapeHtml(title)}</title>
  <style>
    body { margin: 0; padding: 20px; font-family: "Yu Gothic", "Meiryo", sans-serif; background: #f6f3ea; color: #2f2f2f; }
    .sheet { max-width: 760px; margin: 0 auto; background: #ffffff; border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,.08); padding: 20px; }
    .title { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
    .desc { font-size: 14px; line-height: 1.6; color: #666666; margin-bottom: 16px; }
    .actions { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
    .btn { display: inline-flex; align-items: center; justify-content: center; min-width: 180px; height: 42px; padding: 0 18px; border-radius: 999px; text-decoration: none; font-weight: 700; border: none; cursor: pointer; font-size: 14px; }
    .btn-primary { background: #2f7d61; color: #ffffff; }
    .btn-secondary { background: #edf3ee; color: #2f7d61; }
    .preview { background: #faf7f0; border: 1px solid #eadfca; border-radius: 12px; padding: 18px; display: flex; justify-content: center; }
    .preview img { width: 300px; max-width: 100%; height: auto; border: 1px solid #d7cdb8; background: #ffffff; }
    @media print {
      body { background: none; padding: 0; }
      .sheet { box-shadow: none; border-radius: 0; padding: 0; }
      .title, .desc, .actions { display: none; }
      .preview { border: none; background: none; padding: 0; }
      .preview img { width: 100%; max-width: 600px; border: none; }
    }
  </style>
</head>
<body>
  <div class="sheet">
    <div class="title">${escapeHtml(title)}</div>
    <div class="desc">${escapeHtml(description)}</div>
    <div class="actions">
      <a class="btn btn-primary" href="${imageDataUrl}" download="${escapeHtml(fileName)}">画像を保存</a>
      <button class="btn btn-secondary" onclick="window.print()">印刷</button>
    </div>
    <div class="preview">
      <img src="${imageDataUrl}" alt="${escapeHtml(title)}" />
    </div>
  </div>
</body>
</html>`
}

export function createLuckJingleFileName({ productCode, processDate, qty }) {
  const code = String(productCode || 'label').trim() || 'label'
  const date = String(processDate || '').replaceAll('-', '')
  const count = String(qty || '0').trim() || '0'
  const now = new Date()
  const hh = String(now.getHours()).padStart(2, '0')
  const mm = String(now.getMinutes()).padStart(2, '0')
  const ss = String(now.getSeconds()).padStart(2, '0')
  return `${code}_${date}_${count}_${hh}${mm}${ss}.jpg`
}

export function createLuckJinglePdfFileName(fileName) {
  const baseName = String(fileName || 'luck-jingle-label.jpg')
  return baseName.replace(/\.[^.]+$/, '') + '.pdf'
}

export async function buildLuckJingleLabelDataUrl({
  productCode,
  productName,
  processName,
  nextProcessName = '',
  operatorName,
  processDate,
  qty,
  footerText = '',
}) {
  const nameLines = wrapLabelText(productName, 15, 2)

  let qrImage = null
  try {
    const qrDataUrl = await QRCode.toDataURL(String(productCode || ''), { margin: 1, width: 140 })
    qrImage = await loadImage(qrDataUrl)
  } catch {
    // QR生成失敗時はQRなしで続行
  }

  const rows = [
    { label: '加工工程', value: processName, size: 30, weight: '700' },
    ...(nextProcessName ? [{ label: '後工程', value: nextProcessName, size: 30, weight: '700' }] : []),
    { label: '加工日', value: processDate, size: 38, weight: '900' },
    { label: '加工者', value: operatorName, size: 30, weight: '700' },
  ]

  // 上部テープ止め用余白: 7.5cm (96dpi換算 283px)
  const TOP_MARGIN = 283
  const canvasWidth = 600
  const canvasHeight = 850 + TOP_MARGIN

  const canvas = document.createElement('canvas')
  canvas.width = canvasWidth
  canvas.height = canvasHeight
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('canvas unavailable')

  const fontFamily = "'Noto Sans JP', 'Yu Gothic', 'Meiryo', sans-serif"

  // 背景
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)

  // 外枠
  ctx.strokeStyle = '#111111'
  ctx.lineWidth = 3
  ctx.strokeRect(4, 4, canvasWidth - 8, canvasHeight - 8)

  // コンテンツ領域（TOP_MARGIN分下にずらす）
  ctx.save()
  ctx.translate(0, TOP_MARGIN)

  // タイトル「加工品ラベル」
  ctx.font = `700 32px ${fontFamily}`
  ctx.fillStyle = '#000000'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('加工品ラベル', 300, 76)

  // 区切り線
  ctx.beginPath()
  ctx.moveTo(40, 96)
  ctx.lineTo(560, 96)
  ctx.strokeStyle = '#111111'
  ctx.lineWidth = 1
  ctx.stroke()

  // 品番（大きく太字）
  ctx.textAlign = 'left'
  ctx.font = `900 44px ${fontFamily}`
  ctx.fillStyle = '#000000'
  ctx.fillText(String(productCode || ''), 40, 165)

  // 品名（折り返し）
  ctx.font = `400 28px ${fontFamily}`
  ctx.fillText(nameLines[0] || '', 40, 218)
  if (nameLines[1]) {
    ctx.fillText(nameLines[1], 40, 254)
  }

  // 情報行（工程・後工程・加工日・加工者）
  let rowY = 320
  for (const row of rows) {
    ctx.font = `400 20px ${fontFamily}`
    ctx.fillStyle = '#666666'
    ctx.fillText(row.label, 40, rowY)

    ctx.font = `${row.weight} ${row.size}px ${fontFamily}`
    ctx.fillStyle = '#000000'
    ctx.fillText(String(row.value || ''), 180, rowY)

    rowY += row.label === '加工日' ? 58 : 54
  }

  // 加工数
  const qtyLabelY = Math.max(rowY + 44, 598)
  const qtyValueY = qtyLabelY + 10

  ctx.font = `400 22px ${fontFamily}`
  ctx.fillStyle = '#666666'
  ctx.fillText('加工数', 40, qtyLabelY)

  ctx.font = `900 78px ${fontFamily}`
  ctx.fillStyle = '#000000'
  ctx.fillText(String(qty || ''), 180, qtyValueY)

  // フッター
  ctx.font = `400 16px ${fontFamily}`
  ctx.fillStyle = '#666666'
  ctx.fillText(String(footerText || ''), 40, 760)

  // QRコード
  if (qrImage) {
    ctx.drawImage(qrImage, 390, 560, 150, 150)
  }

  ctx.restore()

  return canvas.toDataURL('image/jpeg', 0.92)
}

export async function shareLuckJingleLabel({ imageDataUrl, fileName, title = 'Luck Jingle用ラベル' }) {
  if (!imageDataUrl || typeof navigator === 'undefined' || typeof navigator.share !== 'function' || typeof File === 'undefined') {
    return false
  }

  const blob = dataUrlToBlob(imageDataUrl)
  const file = new File([blob], fileName, { type: blob.type, lastModified: Date.now() })

  if (typeof navigator.canShare === 'function') {
    try {
      if (!navigator.canShare({ files: [file] })) {
        return false
      }
    } catch {
      return false
    }
  }

  await navigator.share({ files: [file] })
  return true
}

export function downloadLuckJingleLabel({ imageDataUrl, fileName }) {
  if (!imageDataUrl || typeof document === 'undefined') {
    return false
  }

  const link = document.createElement('a')
  link.href = imageDataUrl
  link.download = fileName || 'luck-jingle-label.jpg'
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  return true
}

export async function buildLuckJinglePdfBlob({ imageDataUrl }) {
  if (!imageDataUrl) {
    throw new Error('imageDataUrl is required')
  }

  const image = await loadImage(imageDataUrl)
  const jpegBytes = dataUrlToBytes(imageDataUrl)
  const pdfBytes = buildPdfBytesFromJpeg({
    jpegBytes,
    width: image.naturalWidth || image.width,
    height: image.naturalHeight || image.height,
  })
  return new Blob([pdfBytes], { type: 'application/pdf' })
}

export async function buildLuckJinglePdfBase64({ imageDataUrl }) {
  const pdfBlob = await buildLuckJinglePdfBlob({ imageDataUrl })
  const buffer = await pdfBlob.arrayBuffer()
  let binary = ''
  const bytes = new Uint8Array(buffer)
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i])
  }
  return window.btoa(binary)
}

export async function printLuckJingleLabelToPrinter({
  imageDataUrl,
  pdfFileName,
  printerUrl = 'https://10.0.4.10/home/api/uploadfile-print?methodName=POST',
  context = 'HOME',
}) {
  if (!imageDataUrl || typeof document === 'undefined' || typeof File === 'undefined' || typeof DataTransfer === 'undefined') {
    return false
  }

  const pdfBlob = await buildLuckJinglePdfBlob({ imageDataUrl })
  const pdfFile = new File([pdfBlob], pdfFileName || 'luck-jingle-label.pdf', {
    type: 'application/pdf',
    lastModified: Date.now(),
  })

  const iframeName = `luck-jingle-printer-${Date.now()}`
  const iframe = document.createElement('iframe')
  iframe.name = iframeName
  iframe.style.display = 'none'

  const form = document.createElement('form')
  form.method = 'POST'
  form.action = printerUrl
  form.enctype = 'multipart/form-data'
  form.target = iframeName
  form.style.display = 'none'

  const fileInput = document.createElement('input')
  fileInput.type = 'file'
  fileInput.name = 'File'

  const dataTransfer = new DataTransfer()
  dataTransfer.items.add(pdfFile)
  fileInput.files = dataTransfer.files

  const contextInput = document.createElement('input')
  contextInput.type = 'hidden'
  contextInput.name = 'Context'
  contextInput.value = context

  form.appendChild(fileInput)
  form.appendChild(contextInput)
  document.body.appendChild(iframe)
  document.body.appendChild(form)

  try {
    form.submit()
    return true
  } finally {
    window.setTimeout(() => {
      form.remove()
      iframe.remove()
    }, 10000)
  }
}

export function openLuckJinglePreview({
  imageDataUrl,
  fileName,
  title = 'Luck Jingle用ラベル',
  description = '画像を保存して Luck Jingle へ取り込んでください。',
}) {
  const html = buildLuckJinglePreviewHtml({ title, description, fileName, imageDataUrl })
  try {
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const win = window.open(url, '_blank')
    if (win) {
      setTimeout(() => URL.revokeObjectURL(url), 60000)
      return true
    }
  } catch {
    // Blob URL失敗時はdocument.writeにフォールバック
  }

  const win = window.open('', '_blank')
  if (!win) return false
  win.document.open()
  win.document.write(html)
  win.document.close()
  win.focus()
  return true
}
