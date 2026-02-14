export const createProductionPlanChangeLogsAPI = (client) => ({
  getLogs(params = {}) {
    return client.get('/production-plan-change-logs/', { params })
  },
})
