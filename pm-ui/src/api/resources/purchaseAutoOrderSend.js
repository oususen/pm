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
  checkTruckLoad(idOrPayload, payload = null) {
    if (payload === null) {
      return client.post('/purchase-auto-order-send-truck-load-check/', idOrPayload)
    }
    return client.post(`/purchase-auto-order-send-configs/${idOrPayload}/truck-load-check/`, payload)
  },
})
