export const createLaserPatternsAPI = (client) => ({
  getLaserPatterns(params = {}) {
    return client.get('/laser-patterns/', { params })
  },
  getMonthlyMaterialSummary(params = {}) {
    return client.get('/laser-patterns/monthly-material-summary/', { params })
  },
  createLaserPattern(data) {
    return client.post('/laser-patterns/', data)
  },
  updateLaserPattern(id, data) {
    return client.put(`/laser-patterns/${id}/`, data)
  },
  deleteLaserPattern(id) {
    return client.delete(`/laser-patterns/${id}/`)
  },
  copyLaserPattern(id, patternNo) {
    return client.post(`/laser-patterns/${id}/copy/`, { pattern_no: patternNo })
  },
  deactivateLaserPattern(id) {
    return client.post(`/laser-patterns/${id}/deactivate/`)
  },
})
