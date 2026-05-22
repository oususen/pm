export const createLineProductDisplayOrdersAPI = (client) => ({
  getOrders(params = {}) {
    return client.get('/line-product-display-orders/', { params })
  },
  bulkSave(payload) {
    return client.post('/line-product-display-orders/bulk-save/', payload)
  },
})
