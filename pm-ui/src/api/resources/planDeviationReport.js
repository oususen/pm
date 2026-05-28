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
 * 計画乖離レポート ライン設定API（LineGanttPlan使用ライン）
 */
export function createPlanDeviationLineConfigAPI(client) {
  return {
    get() {
      return client.get('/plan-deviation-line-config/')
    },
    toggle(lineId, enabled) {
      return client.post('/plan-deviation-line-config/', { line_id: lineId, enabled })
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
