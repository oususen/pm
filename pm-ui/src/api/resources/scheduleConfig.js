export const createScheduleConfigAPI = (client) => ({
  getConfigs() {
    return client.get('/schedule-config/')
  },
  saveConfig(payload) {
    return client.post('/schedule-config/', payload)
  },
  runNow(payload = {}) {
    return client.post('/schedule-config/run-now/', payload)
  },
  getRunLogs(configId) {
    return client.get('/schedule-config/run-logs/', { params: { config_id: configId } })
  },
  getPurchaseActualReconcileReports(params = {}) {
    return client.get('/schedule-config/purchase-actual-reconcile/reports/', { params })
  },
  runPurchaseActualReconcileFix(payload = {}) {
    return client.post('/schedule-config/purchase-actual-reconcile/fix/', payload)
  },
  getProductionActualReconcileReports(params = {}) {
    return client.get('/schedule-config/production-actual-reconcile/reports/', { params })
  },
  runProductionActualReconcileFix(payload = {}) {
    return client.post('/schedule-config/production-actual-reconcile/fix/', payload)
  },
  cancel(payload = {}) {
    return client.post('/schedule-config/cancel/', payload)
  },
})
