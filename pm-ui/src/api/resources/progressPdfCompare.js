export function createProgressPdfCompareAPI(client) {
  return {
    compare(file, lineCode, targetDate) {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('line_code', lineCode)
      formData.append('target_date', targetDate)
      return client.post('/progress-pdf-compare/', formData)
    },
    precheck(lineCode, targetDate, items) {
      return client.put('/progress-pdf-adjust/', {
        line_code: lineCode,
        target_date: targetDate,
        items,
      })
    },
    adjust(lineCode, targetDate, items) {
      return client.post('/progress-pdf-adjust/', {
        line_code: lineCode,
        target_date: targetDate,
        items,
      })
    },
  }
}
