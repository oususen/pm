export const createPurchaseAutoOrderSendAPI = (client) => ({
  getConfigs() {
    return client.get('/purchase-auto-order-send-configs/')
  },
  createConfig(payload) {
    return client.post('/purchase-auto-order-send-configs/', payload)
  },
  updateConfig(id, payload) {
    return client.put(`/purchase-auto-order-send-configs/${id}/`, payload)
  },
  deleteConfig(id) {
    return client.delete(`/purchase-auto-order-send-configs/${id}/`)
  },
  runNow(id) {
    return client.post(`/purchase-auto-order-send-configs/${id}/run-now/`)
  },
  runHolidayTrial(id) {
    return client.post(`/purchase-auto-order-send-configs/${id}/holiday-trial/`)
  },
  getHistories(params = {}) {
    return client.get('/purchase-auto-order-send-histories/', { params })
  },
  downloadHistoryOrderExcel(id) {
    return client.get(`/purchase-auto-order-send-histories/${id}/order-excel/`, { responseType: 'blob' })
  },
  getTruckLoadDates(truckId) {
    return client.get('/purchase-auto-order-send-truck-load-check/', { params: { truck_id: truckId } })
  },
  checkTruckLoad(idOrPayload, payload = null, options = {}) {
    if (payload === null) {
      return client.post('/purchase-auto-order-send-truck-load-check/', idOrPayload, options)
    }
    return client.post(`/purchase-auto-order-send-configs/${idOrPayload}/truck-load-check/`, payload, options)
  },
  cancelTruckLoadCheck(requestId) {
    return client.post('/purchase-auto-order-send-truck-load-check/cancel/', { request_id: requestId })
  },
})
