import * as XLSX from 'xlsx'

const formatDateCompact = (value) => {
  if (!value) return '—'
  // "2026-02-24" → "20260224"
  return String(value).replace(/-/g, '')
}

const formatTimeOnly = (value) => {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const h = d.getHours()
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${h}${mm}`
}

export const buildProductionSummaryRows = (sessions) => {
  const headers = ['生産日', '品番', '工程順', '開始時間', '終了時間', '生産数量']
  const rows = (Array.isArray(sessions) ? sessions : []).map((row) => [
    formatDateCompact(row.plan_date),
    row.product_code || '—',
    row.process_code || '—',
    formatTimeOnly(row.started_at),
    row.ended_at ? formatTimeOnly(row.ended_at) : '—',
    row.production_qty != null ? Math.trunc(Number(row.production_qty)) : '',
  ])
  return { headers, rows }
}

export const exportProductionSummaryExcel = (sessions, startDate, endDate) => {
  const { headers, rows } = buildProductionSummaryRows(sessions)
  if (!rows.length) {
    alert('出力対象のデータがありません。')
    return
  }
  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows])
  XLSX.utils.book_append_sheet(wb, ws, '生産実績2')
  const data = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
  const blob = new Blob([data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `production_record2_${startDate}_${endDate}.xlsx`
  link.click()
  URL.revokeObjectURL(url)
}
