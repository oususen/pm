export const createProgressMonitorAPI = (client) => ({
  getOptions() {
    return client.get('/progress-monitor-targets/options/')
  },
  getSnapshot(params) {
    return client.get('/progress-monitor-targets/snapshot/', { params })
  },
  getTargets(params = {}) {
    return client.get('/progress-monitor-targets/', { params })
  },
  getProductCandidates(params = {}) {
    return client.get('/progress-monitor-targets/product-candidates/', { params })
  },
  createTarget(data) {
    return client.post('/progress-monitor-targets/', data)
  },
  updateTarget(id, data) {
    return client.patch(`/progress-monitor-targets/${id}/`, data)
  },
})
