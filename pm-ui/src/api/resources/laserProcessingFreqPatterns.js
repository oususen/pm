export const createLaserProcessingFreqPatternsAPI = (client) => ({
  getPatterns(params = {}) {
    return client.get('/laser-processing-freq-patterns/', { params })
  },
  createPattern(data) {
    return client.post('/laser-processing-freq-patterns/', data)
  },
  updatePattern(id, data) {
    return client.put(`/laser-processing-freq-patterns/${id}/`, data)
  },
  deletePattern(id) {
    return client.delete(`/laser-processing-freq-patterns/${id}/`)
  },
})
