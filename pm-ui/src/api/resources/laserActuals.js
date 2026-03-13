export const createLaserActualsAPI = (client) => ({
  getLaserActuals(params = {}) {
    return client.get('/laser-actuals/', { params })
  },
  getLaserActual(id) {
    return client.get(`/laser-actuals/${id}/`)
  },
  createLaserActual(data) {
    return client.post('/laser-actuals/', data)
  },
  updateLaserActual(id, data) {
    return client.put(`/laser-actuals/${id}/`, data)
  },
  patchLaserActual(id, data) {
    return client.patch(`/laser-actuals/${id}/`, data)
  },
  deleteLaserActual(id) {
    return client.delete(`/laser-actuals/${id}/`)
  },
})
