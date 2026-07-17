export const createPurchaseAutoDeliveryListAPI = (client) => ({
  getConfigs() {
    return client.get('/purchase-auto-delivery-list-configs/')
  },
  createConfig(payload) {
    return client.post('/purchase-auto-delivery-list-configs/', payload)
  },
  updateConfig(id, payload) {
    return client.put(`/purchase-auto-delivery-list-configs/${id}/`, payload)
  },
  deleteConfig(id) {
    return client.delete(`/purchase-auto-delivery-list-configs/${id}/`)
  },
  runNow(id) {
    return client.post(`/purchase-auto-delivery-list-configs/${id}/run-now/`)
  },
  runHolidayTrial(id) {
    return client.post(`/purchase-auto-delivery-list-configs/${id}/holiday-trial/`)
  },
})
