import QRCode from 'qrcode'

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function escapeXml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')
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

function dataUrlToFile(dataUrl, fileName) {
  const [header, base64 = ''] = String(dataUrl || '').split(',')
  const mime = /data:(.*?);base64/.exec(header)?.[1] || 'image/png'
  const binary = window.atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return new File([bytes], fileName, { type: mime })
}

function buildLuckJinglePreviewHtml({ title, description, fileName, imageDataUrl }) {
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <title>${escapeHtml(title)}</title>
  <style>
    body { margin: 0; padding: 20px; font-family: "Yu Gothic", "Meiryo", sans-serif; background: #f6f3ea; color: #2f2f2f; }
    .sheet { max-width: 760px; margin: 0 auto; background: #ffffff; border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,.08); padding: 20px; }
    .title { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
    .desc { font-size: 14px; line-height: 1.6; color: #666666; margin-bottom: 16px; }
    .actions { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
    .btn { display: inline-flex; align-items: center; justify-content: center; min-width: 180px; height: 42px; padding: 0 18px; border-radius: 999px; text-decoration: none; font-weight: 700; }
    .btn-primary { background: #2f7d61; color: #ffffff; }
    .btn-secondary { background: #edf3ee; color: #2f7d61; }
    .preview { background: #faf7f0; border: 1px solid #eadfca; border-radius: 12px; padding: 18px; display: flex; justify-content: center; }
    .preview img { width: 300px; max-width: 100%; height: auto; border: 1px solid #d7cdb8; background: #ffffff; }
  </style>
</head>
<body>
  <div class="sheet">
    <div class="title">${escapeHtml(title)}</div>
    <div class="desc">${escapeHtml(description)}</div>
    <div class="actions">
      <a class="btn btn-primary" href="${imageDataUrl}" download="${escapeHtml(fileName)}">画像を保存</a>
      <a class="btn btn-secondary" href="${imageDataUrl}" target="_blank" rel="noopener">画像だけ開く</a>
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
  return `${code}_${date}_${count}.png`
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
  let qrDataUrl = ''
  try {
    qrDataUrl = await QRCode.toDataURL(String(productCode || ''), { margin: 1, width: 140 })
  } catch {
    qrDataUrl = ''
  }

  const rows = [
    { label: '加工工程', value: processName, size: 30, weight: '700' },
    ...(nextProcessName ? [{ label: '後工程', value: nextProcessName, size: 30, weight: '700' }] : []),
    { label: '加工日', value: processDate, size: 38, weight: '900' },
    { label: '加工者', value: operatorName, size: 30, weight: '700' },
  ]

  let rowY = 320
  const rowSvg = rows.map((row) => {
    const svg = `
    <text x="40" y="${rowY}" font-size="20" fill="#666666" font-family="Yu Gothic, Meiryo, sans-serif">${escapeXml(row.label)}</text>
    <text x="180" y="${rowY}" font-size="${row.size}" font-family="Yu Gothic, Meiryo, sans-serif" font-weight="${row.weight}">${escapeXml(row.value)}</text>`
    rowY += row.label === '加工日' ? 58 : 54
    return svg
  }).join('')

  const qtyLabelY = Math.max(rowY + 44, 598)
  const qtyValueY = qtyLabelY + 10

  // 上部テープ止め用余白: 7.5cm (96dpi換算 283px)
  const TOP_MARGIN = 283
  const svgHeight = 850 + TOP_MARGIN

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="${svgHeight}" viewBox="0 0 600 ${svgHeight}">
    <rect x="4" y="4" width="592" height="${svgHeight - 8}" fill="#ffffff" stroke="#111111" stroke-width="3"/>
    <g transform="translate(0, ${TOP_MARGIN})">
      <text x="300" y="76" font-size="32" text-anchor="middle" font-family="Yu Gothic, Meiryo, sans-serif" font-weight="700">加工品ラベル</text>
      <line x1="40" y1="96" x2="560" y2="96" stroke="#111111" stroke-width="1"/>
      <text x="40" y="165" font-size="44" font-family="Yu Gothic, Meiryo, sans-serif" font-weight="900">${escapeXml(productCode)}</text>
      <text x="40" y="218" font-size="28" font-family="Yu Gothic, Meiryo, sans-serif">${escapeXml(nameLines[0] || '')}</text>
      <text x="40" y="254" font-size="28" font-family="Yu Gothic, Meiryo, sans-serif">${escapeXml(nameLines[1] || '')}</text>
      ${rowSvg}
      <text x="40" y="${qtyLabelY}" font-size="22" fill="#666666" font-family="Yu Gothic, Meiryo, sans-serif">加工数</text>
      <text x="180" y="${qtyValueY}" font-size="78" font-family="Yu Gothic, Meiryo, sans-serif" font-weight="900">${escapeXml(qty)}</text>
      <text x="40" y="760" font-size="16" fill="#666666" font-family="Yu Gothic, Meiryo, sans-serif">${escapeXml(footerText)}</text>
      ${qrDataUrl ? `<image href="${qrDataUrl}" x="390" y="560" width="150" height="150"/>` : ''}
    </g>
  </svg>`

  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = 600
      canvas.height = svgHeight
      const context = canvas.getContext('2d')
      if (!context) {
        reject(new Error('canvas unavailable'))
        return
      }
      context.fillStyle = '#ffffff'
      context.fillRect(0, 0, canvas.width, canvas.height)
      context.drawImage(image, 0, 0)
      resolve(canvas.toDataURL('image/png'))
    }
    image.onerror = () => reject(new Error('svg render failed'))
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
  })
}

export async function shareLuckJingleLabel({ imageDataUrl, fileName, title = 'Luck Jingle用ラベル' }) {
  if (!imageDataUrl || typeof navigator === 'undefined' || typeof navigator.share !== 'function' || typeof File === 'undefined') {
    return false
  }

  const file = dataUrlToFile(imageDataUrl, fileName)
  const shareData = {
    title,
    text: 'Luck Jingleで開いて印刷してください。',
    files: [file],
  }

  if (typeof navigator.canShare === 'function') {
    try {
      if (!navigator.canShare({ files: [file] })) {
        return false
      }
    } catch {
      return false
    }
  }

  await navigator.share(shareData)
  return true
}

export function openLuckJinglePreview({
  imageDataUrl,
  fileName,
  title = 'Luck Jingle用ラベル',
  description = '共有未対応のため、ラベル画像を開きました。画像を保存して Luck Jingle へ取り込んでください。',
}) {
  const win = window.open('', '_blank')
  if (!win) {
    return false
  }

  win.document.open()
  win.document.write(buildLuckJinglePreviewHtml({ title, description, fileName, imageDataUrl }))
  win.document.close()
  win.focus()
  return true
}
