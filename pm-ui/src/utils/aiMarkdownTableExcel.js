// 社内AIの回答に含まれるMarkdownの表を、Excel(.xlsx)としてダウンロードする。
// 表は回答本文から読み取る。サーバーへは送らず、ブラウザ内でファイルを作る。

const TABLE_LINE = /^\s*\|.*\|\s*$/
const SEPARATOR_LINE = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/
// 先頭が0の数字(000196・05476など)は品番・コードなので、数値にせず文字列のまま保つ
const NUMBER_PATTERN = /^-?(0|[1-9]\d*|[1-9]\d{0,2}(,\d{3})+)(\.\d+)?$/

const splitRow = (line) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim())

const toCellValue = (text) => (NUMBER_PATTERN.test(text) ? Number(text.replace(/,/g, '')) : text)

// 回答本文から、ヘッダー行+区切り行+データ行を持つ表をすべて取り出す
export const parseMarkdownTables = (markdown) => {
  const lines = String(markdown || '').split(/\r?\n/)
  const tables = []
  let index = 0
  while (index < lines.length) {
    if (TABLE_LINE.test(lines[index]) && index + 1 < lines.length && SEPARATOR_LINE.test(lines[index + 1])) {
      const header = splitRow(lines[index])
      const rows = []
      index += 2
      while (index < lines.length && TABLE_LINE.test(lines[index])) {
        rows.push(splitRow(lines[index]))
        index += 1
      }
      tables.push({ header, rows })
    } else {
      index += 1
    }
  }
  return tables
}

export const hasMarkdownTable = (markdown) => parseMarkdownTables(markdown).length > 0

const localDateText = () => {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

export const downloadMarkdownTablesAsExcel = async (markdown) => {
  const tables = parseMarkdownTables(markdown)
  if (!tables.length) return false
  const ExcelJS = (await import('exceljs')).default
  const workbook = new ExcelJS.Workbook()
  tables.forEach((table, tableIndex) => {
    const sheet = workbook.addWorksheet(tables.length === 1 ? '表' : `表${tableIndex + 1}`)
    const headerRow = sheet.addRow(table.header)
    headerRow.font = { bold: true }
    headerRow.eachCell((cell) => {
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDDEBF7' } }
    })
    table.rows.forEach((row) => {
      const values = table.header.map((_, columnIndex) => toCellValue(row[columnIndex] ?? ''))
      const added = sheet.addRow(values)
      added.eachCell((cell) => {
        if (typeof cell.value === 'number') cell.numFmt = Number.isInteger(cell.value) ? '#,##0' : '#,##0.###'
      })
    })
    sheet.columns.forEach((column, columnIndex) => {
      const lengths = [table.header[columnIndex], ...table.rows.map((row) => row[columnIndex])].map((text) => String(text ?? '').length)
      column.width = Math.min(Math.max(10, ...lengths.map((length) => length * 1.6 + 2)), 50)
    })
    sheet.views = [{ state: 'frozen', ySplit: 1 }]
  })
  const buffer = await workbook.xlsx.writeBuffer()
  const url = URL.createObjectURL(new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `社内AI_表_${localDateText()}.xlsx`
  link.click()
  URL.revokeObjectURL(url)
  return true
}
