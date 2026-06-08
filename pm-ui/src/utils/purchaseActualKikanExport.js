import * as XLSX from 'xlsx'

const formatDateCompact = (value) => {
  if (!value) return ''
  return String(value).replace(/-/g, '')
}

const toDateKey = (value) => {
  if (!value) return ''
  const digits = String(value).replace(/[^0-9]/g, '')
  return digits.length >= 8 ? digits.slice(0, 8) : ''
}

/**
 * マッピングを appProductCode で検索して返す
 * 見つからない場合は null
 */
const resolveMapping = (appProductCode, mappings) => {
  const code = String(appProductCode || '').trim().toUpperCase()
  if (!code) return null
  return mappings.find((m) => String(m.appProductCode || '').trim().toUpperCase() === code) || null
}

/**
 * 納入実績行からExcel行データを生成する
 * @param {Array} rows - PurchaseActualInquiry の照会結果
 * @param {Array} mappings - PurchaseActualKikanMapping の mappings
 * @param {string} startDate - 開始日 (YYYY-MM-DD)
 * @param {string} endDate   - 終了日 (YYYY-MM-DD)
 * @returns {{ headers, rows, unmappedCodes }}
 */
export const buildPurchaseKikanRows = (rows, mappings, startDate = '', endDate = '') => {
  const headers = [
    'マッピング状態',
    '品目区分',
    '入荷日',
    'アプリ品番',
    '基幹品番',
    '仕入先コード',
    '品番後Tabキー回数',
    '入荷数後Tabキー回数',
    '入荷数',
  ]

  const startKey = toDateKey(startDate)
  const endKey = toDateKey(endDate)
  const unmappedCodes = new Set()
  const outputRows = []

  for (const row of (Array.isArray(rows) ? rows : [])) {
    const deliveryDateKey = toDateKey(row.delivery_date)
    if (startKey && deliveryDateKey < startKey) continue
    if (endKey && deliveryDateKey > endKey) continue

    const qty = Number(row.qty || 0)
    if (qty <= 0) continue

    const appCode = String(row.product_code || '').trim()
    const mapped = resolveMapping(appCode, mappings)

    if (!mapped) {
      unmappedCodes.add(appCode)
      outputRows.push([
        '未設定',
        '',
        toDateKey(row.delivery_date),
        appCode,
        '',
        '',
        '',
        '',
        qty,
      ])
      continue
    }

    const itemType = mapped.itemType === 'K' ? 'K' : 'G'
    // G: 入荷数後Tab=0、K: 入荷数後Tab=1
    const tabsAfterNyuukosu = itemType === 'K' ? 1 : 0

    outputRows.push([
      '変換済み',
      itemType,
      toDateKey(row.delivery_date),
      appCode,
      mapped.coreProductCode || '',
      mapped.supplierCode || '',
      mapped.tabsAfterHinban ?? 1,
      tabsAfterNyuukosu,
      qty,
    ])
  }

  return { headers, rows: outputRows, unmappedCodes: Array.from(unmappedCodes) }
}

/**
 * Excel ファイルをダウンロードする
 */
export const exportPurchaseKikanExcel = (inquiryRows, mappings, startDate, endDate, supplierCode = '') => {
  const { headers, rows, unmappedCodes } = buildPurchaseKikanRows(inquiryRows, mappings, startDate, endDate)

  if (unmappedCodes.length > 0) {
    const list = unmappedCodes.join('\n  ')
    const proceed = window.confirm(
      `以下の品番はマッピング未設定です。基幹システムへの入力ができません。\n\n  ${list}\n\n未設定品番を含めてExcelを出力しますか？`
    )
    if (!proceed) return
  }

  if (!rows.length) {
    alert('出力対象のデータがありません。')
    return
  }

  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows])
  XLSX.utils.book_append_sheet(wb, ws, '仕入先納入実績')

  const data = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
  const blob = new Blob([data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const label = supplierCode ? `_${supplierCode}` : ''
  link.download = `仕入先納入基幹入力${label}_${formatDateCompact(startDate)}_${formatDateCompact(endDate)}.xlsx`
  link.click()
  URL.revokeObjectURL(url)
}
