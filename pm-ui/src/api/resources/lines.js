export const createLinesAPI = (client) => ({
  getLines(params = {}) {
    return client.get('/lines/', { params })
  },
  getProductionLines(params = {}) {
    return client.get('/production-lines/', { params })
  },
  getLine(id) {
    return client.get(`/lines/${id}/`)
  },
  createLine(data) {
    return client.post('/lines/', data)
  },
  updateLine(id, data) {
    return client.put(`/lines/${id}/`, data)
  },
  patchLine(id, data) {
    return client.patch(`/lines/${id}/`, data)
  },
  deleteLine(id) {
    return client.delete(`/lines/${id}/`)
  },
})
