/**
 * 計画乖離レポートAPI
 */
export function createPlanDeviationReportAPI(client) {
  return {
    get(params = {}) {
      return client.get('/plan-deviation-report/', { params })
    },
  }
}

/**
 * 生産実績確認済みAPI
 */
export function createRecordConfirmationAPI(client) {
  return {
    get(params = {}) {
      return client.get('/record-confirmations/', { params })
    },
    confirm(data) {
      return client.post('/record-confirmations/', data)
    },
  }
}
