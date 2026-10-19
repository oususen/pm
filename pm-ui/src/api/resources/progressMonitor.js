export const createProgressMonitorAPI = (client) => ({
  getOptions() {
    return client.get('/progress-monitor-targets/options/')
  },
  getSnapshot({ unit_ids, ...params }) {
    const unitIdParam = Array.isArray(unit_ids) ? unit_ids.join(',') : unit_ids
    return client.get('/progress-monitor-targets/snapshot/', { params: { ...params, unit_id: unitIdParam } })
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
