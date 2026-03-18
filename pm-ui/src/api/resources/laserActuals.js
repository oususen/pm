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
  /** 品番別明細の数量個別更新 PATCH /laser-actual-details/{detail_id}/ */
  patchLaserActualDetail(detailId, data) {
    return client.patch(`/laser-actual-details/${detailId}/`, data)
  },
})
