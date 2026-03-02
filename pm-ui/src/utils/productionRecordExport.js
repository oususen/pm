import * as XLSX from 'xlsx'

// エクスポート用日時フォーマット（画面表示とは別の標準形式）
const formatExportDateTime = (value) => {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}/${mm}/${dd} ${hh}:${min}`
}

const formatDuration = (seconds, endedAt) => {
  const isOpen = !endedAt
  const total = isOpen && Number(seconds || 0) <= 0 ? 0 : Number(seconds || 0)
  const hh = Math.floor(total / 3600)
  const mm = Math.floor((total % 3600) / 60)
  const ss = total % 60
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}

const formatNumber = (value) => {
  if (value === null || value === undefined || value === '') return ''
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 3 })
}

const isCountableProductionRow = (row) => {
  if (!row || row.session_type !== 'WORK') return false
  return ['END', 'PAUSE'].includes(String(row.end_action || '').toUpperCase())
}

const isCanceledSession = (row) => {
  if (!row) return false
  return String(row.end_action || '').toUpperCase() === 'CANCEL'
}

const getSessionTypeLabel = (row) => {
  if (isCanceledSession(row)) return '中止'
  return row.session_type === 'PAUSE' ? '中断' : '作業'
}

const formatProductionQty = (row) => {
  if (!isCountableProductionRow(row)) return '—'
  return formatNumber(row.production_qty || 0)
}

const calcWorkSecondsExcludingPause = (row) => {
  if (!row) return 0
  return String(row.session_type || '').toUpperCase() === 'PAUSE'
    ? 0
    : Math.max(Number(row.effective_work_seconds || 0), 0)
}

const calcDurationBasedProductivity = (row) => {
  if (!row || !isCountableProductionRow(row)) return null
  const qty = Number(row.production_qty || 0)
  const dur = Number(row.duration_seconds || 0)
  if (!Number.isFinite(qty) || !Number.isFinite(dur) || qty <= 0 || dur <= 0) return null
  return (qty * 3600) / dur
}

const formatProductivity = (value, row = null) => {
  if (row && !isCountableProductionRow(row)) return '—'
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const escapeHtml = (value) => {
  return `${value ?? ''}`
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export const buildExportRows = (sessions) => {
  const headers = [
    'レコードID', '開始', '終了', '区分', '開始操作', '終了操作',
    '中断理由',
    '工程', '品番', '品名', '作業者', '継続時間', '作業時間(休憩除き)',
    '作業時間(休憩、中断除き)',
    '生産数量', '実績数量', '出来高(台/h)', '出来高', '不整合',
  ]
  const rows = (Array.isArray(sessions) ? sessions : []).map((row) => [
    row.id ?? '—',
    formatExportDateTime(row.started_at),
    row.ended_at ? formatExportDateTime(row.ended_at) : '—',
    getSessionTypeLabel(row),
    row.start_action || '—',
    row.end_action || '—',
    row.pause_reason || '—',
    `${row.process_code || ''} / ${row.process_name || ''}`.trim(),
    row.product_code || '—',
    row.product_name || '',
    row.operator_name || '—',
    formatDuration(row.duration_seconds, row.ended_at),
    formatDuration(row.effective_work_seconds, true),
    formatDuration(calcWorkSecondsExcludingPause(row), true),
    formatNumber(row.production_qty ?? ''),
    formatProductionQty(row),
    formatProductivity(row.productivity_per_hour, row),
    formatProductivity(calcDurationBasedProductivity(row), row),
    (row.issue_flags || []).join(', ') || '—',
  ])
  return { headers, rows }
}

export const exportCsv = (sessions, startDate, endDate) => {
  const { headers, rows } = buildExportRows(sessions)
  if (!rows.length) {
    alert('出力対象のデータがありません。')
    return
  }
  const escapeCsv = (value) => `"${`${value ?? ''}`.replace(/"/g, '""')}"`
  const lines = [headers.map(escapeCsv).join(','), ...rows.map((r) => r.map(escapeCsv).join(','))]
  const blob = new Blob([`\ufeff${lines.join('\r\n')}`], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, `production_record_${startDate}_${endDate}.csv`)
}

export const exportExcel = (sessions, startDate, endDate) => {
  const { headers, rows } = buildExportRows(sessions)
  if (!rows.length) {
    alert('出力対象のデータがありません。')
    return
  }
  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows])
  XLSX.utils.book_append_sheet(wb, ws, '生産実績')
  const data = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
  const blob = new Blob([data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  downloadBlob(blob, `production_record_${startDate}_${endDate}.xlsx`)
}

export const buildPrintTableHtml = (sessions, { lineLabel, processLabel, startDate, endDate, summary }) => {
  const { headers, rows } = buildExportRows(sessions)
  const headerInfo = `
    <div class="meta">
      <div><strong>ライン:</strong> ${escapeHtml(lineLabel || 'すべて')}</div>
      <div><strong>工程:</strong> ${escapeHtml(processLabel || 'すべて')}</div>
      <div><strong>期間:</strong> ${escapeHtml(startDate)} ～ ${escapeHtml(endDate)}</div>
    </div>`
  const summaryBlock = `
    <div class="summary">
      <div class="summary-line">
        <div><strong>中断除く加工情報</strong></div>
        <div>期間合計実績: ${escapeHtml(formatNumber(summary.totalProductionQty))}</div>
        <div>期間合計作業時間（休憩除外）: ${escapeHtml(formatDuration(summary.totalEffectiveWorkSeconds, true))}</div>
        <div>期間出来高（台/h）: ${escapeHtml(formatProductivity(summary.totalProductivityPerHour))}</div>
      </div>
      <div class="summary-line">
        <div><strong>中断含む加工情報</strong></div>
        <div>期間合計実績: ${escapeHtml(formatNumber(summary.totalProductionQty))}</div>
        <div>期間合計作業時間（中断含む）: ${escapeHtml(formatDuration(summary.totalDurationIncludingPauseSeconds, true))}</div>
        <div>正味加工時間: ${escapeHtml(formatDuration(summary.totalEffectiveWorkSeconds, true))}</div>
        <div>中断時間: ${escapeHtml(formatDuration(summary.totalPauseSeconds, true))}</div>
        <div>期間出来高（台/h）: ${escapeHtml(formatProductivity(summary.totalProductivityIncludingPausePerHour))}</div>
      </div>
    </div>`
  const thead = `<tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join('')}</tr>`
  const tbody = rows.length
    ? rows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`).join('')
    : `<tr><td colspan="${headers.length}" class="no-data">データがありません</td></tr>`
  return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      @page { size: A4 landscape; margin: 10mm; }
      body { font-family: "Noto Sans JP", "Segoe UI", sans-serif; color: #111; }
      h1 { margin: 0 0 6px; font-size: 16px; }
      .meta { display: flex; gap: 16px; margin-bottom: 6px; font-size: 11px; }
      .summary { border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px; margin-bottom: 8px; }
      .summary-line { display: flex; flex-wrap: wrap; gap: 10px; font-size: 11px; margin-bottom: 4px; }
      table { width: 100%; border-collapse: collapse; font-size: 10px; }
      th, td { border: 1px solid #cbd5e1; padding: 4px 6px; }
      th { background: #f8fafc; }
      td { white-space: nowrap; }
      .no-data { text-align: center; }
    </style>
    <title>生産実績照会</title>
  </head>
  <body>
    <h1>生産実績照会</h1>
    ${headerInfo}
    ${summaryBlock}
    <table>
      <thead>${thead}</thead>
      <tbody>${tbody}</tbody>
    </table>
  </body>
</html>`
}

export const exportPdf = (sessions, opts) => {
  const { rows } = buildExportRows(sessions)
  if (!rows.length) {
    alert('出力対象のデータがありません。')
    return
  }
  const html = buildPrintTableHtml(sessions, opts)
  const win = window.open('', '_blank')
  if (!win) {
    alert('ポップアップがブロックされました。許可して再実行してください。')
    return
  }
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => {
    win.print()
    win.onafterprint = () => win.close()
  }, 150)
}
