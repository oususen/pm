import * as XLSX from 'xlsx'
import {
  getProductionRecordMappingsByTab,
  loadProductionRecordMappingsByTab,
  resolveCoreMapping,
} from '@/config/productionRecordSettings'

const formatDateCompact = (value) => {
  if (!value) return '—'
  // "2026-02-24" → "20260224"
  return String(value).replace(/-/g, '')
}

const toDateKey = (value) => {
  if (!value) return ''
  const digits = String(value).replace(/[^0-9]/g, '')
  return digits.length >= 8 ? digits.slice(0, 8) : ''
}

const formatTimeOnly = (value) => {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const h = d.getHours()
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${h}${mm}`
}

export const buildProductionSummaryRows = (
  sessions,
  tabKey = 'tank',
  mappingsByTabInput = null,
  startDate = '',
  endDate = '',
) => {
  const mappingsByTab = mappingsByTabInput || loadProductionRecordMappingsByTab()
  const mappings = getProductionRecordMappingsByTab(mappingsByTab, tabKey)
  const startKey = toDateKey(startDate)
  const endKey = toDateKey(endDate)
  const headers = ['生産日', 'アプリ品番', '基幹品番', '工程コード', '工順', '開始時間', '終了時間', '生産数量', '工程順行きエンター回数', 'マッピング状態']
  const rows = (Array.isArray(sessions) ? sessions : [])
    .map((row) => {
      const appProductCode = row.product_code || ''
      const processCode = row.process_code || ''
      const mapped = resolveCoreMapping(appProductCode, processCode, mappings)
      const qtyRaw = Number(row.production_qty)
      const productionQty = Number.isFinite(qtyRaw) ? Math.trunc(qtyRaw) : null
      const planDateKey = toDateKey(row.plan_date)
      return { row, appProductCode, processCode, mapped, productionQty, planDateKey }
    })
    .filter(({ row, mapped, productionQty, planDateKey }) => {
      const sessionType = String(row?.session_type || '').toUpperCase()
      const endAction = String(row?.end_action || '').toUpperCase()
      const inDateRange = (
        !!planDateKey &&
        (!startKey || planDateKey >= startKey) &&
        (!endKey || planDateKey <= endKey)
      )
      return (
        sessionType === 'WORK' &&
        ['END', 'PAUSE'].includes(endAction) &&
        mapped?.mapped === true &&
        (productionQty || 0) > 0 &&
        inDateRange
      )
    })
    .map(({ row, appProductCode, processCode, mapped, productionQty }) => {
      return [
        formatDateCompact(row.plan_date),
        appProductCode || '—',
        mapped.coreProductCode || '—',
        processCode || '—',
        mapped.coreProcessOrder || '—',
        formatTimeOnly(row.started_at),
        row.ended_at ? formatTimeOnly(row.ended_at) : '—',
        productionQty ?? '',
        mapped.enterCount ?? '',
        mapped.mapped ? '変換済み' : '未設定(アプリ品番)',
      ]
    })
  return { headers, rows }
}

export const exportProductionSummaryExcel = (sessions, startDate, endDate, options = {}) => {
  const tabKey = options?.tabKey || 'tank'
  const { headers, rows } = buildProductionSummaryRows(
    sessions,
    tabKey,
    options?.mappingsByTab || null,
    startDate,
    endDate,
  )
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
  const compactStart = formatDateCompact(startDate)
  const compactEnd   = formatDateCompact(endDate)
  link.download = `${tabKey}_${compactStart}_${compactEnd}.xlsx`
  link.click()
  URL.revokeObjectURL(url)
}
