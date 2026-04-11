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
  getPurchaseActualReconcileReports(params = {}) {
    return client.get('/schedule-config/purchase-actual-reconcile/reports/', { params })
  },
  runPurchaseActualReconcileFix(payload = {}) {
    return client.post('/schedule-config/purchase-actual-reconcile/fix/', payload)
  },
  cancel(payload = {}) {
    return client.post('/schedule-config/cancel/', payload)
  },
})
