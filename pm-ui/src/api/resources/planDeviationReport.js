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
