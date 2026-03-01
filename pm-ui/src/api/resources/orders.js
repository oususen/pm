export const createOrdersAPI = (client) => ({
  getOrders() {
    return client.get('/orders/')
  },
  getProductionOrders(params = {}) {
    return client.get('/production-orders/', { params })
  },
  syncProductionOrdersFromPlan(payload = {}) {
    return client.post('/production-orders/sync-from-plan/', payload)
  },
  getProductionOrder(id) {
    return client.get(`/production-orders/${id}/`)
  },
  transitionProductionOrder(id, action) {
    return client.post(`/production-orders/${id}/${action}/`)
  },
  createProductionOrder(data) {
    return client.post('/production-orders/', data)
  },
  updateProductionOrder(id, data) {
    return client.put(`/production-orders/${id}/`, data)
  },
  getStockAllocations(params = {}) {
    return client.get('/stock-allocations/', { params })
  },
  getStockAllocation(id) {
    return client.get(`/stock-allocations/${id}/`)
  },
  createStockAllocation(data) {
    return client.post('/stock-allocations/', data)
  },
  updateStockAllocation(id, data) {
    return client.put(`/stock-allocations/${id}/`, data)
  },
  deleteStockAllocation(id) {
    return client.delete(`/stock-allocations/${id}/`)
  },
  reserveStockAllocation(id, quantity) {
    return client.post(`/stock-allocations/${id}/reserve/`, { quantity })
  },
  releaseStockAllocation(id, quantity) {
    return client.post(`/stock-allocations/${id}/release/`, { quantity })
  },
  calculateLineLoad(payload) {
    return client.post('/crp/calculate-line-load/', payload)
  },
  // Process actuals
  getProcessActuals(params = {}) {
    return client.get('/process-actuals/', { params })
  },
  createProcessActual(data) {
    return client.post('/process-actuals/', data)
  },
  updateProcessActual(id, data) {
    return client.put(`/process-actuals/${id}/`, data)
  },
  deleteProcessActual(id) {
    return client.delete(`/process-actuals/${id}/`)
  },
  getOrder(id) {
    return client.get(`/orders/${id}/`)
  },
  createOrder(data) {
    return client.post('/orders/', data)
  },
  updateOrder(id, data) {
    return client.put(`/orders/${id}/`, data)
  },
  deleteOrder(id) {
    return client.delete(`/orders/${id}/`)
  },

  // Order Lines
  getOrderLines(orderId) {
    return client.get(`/order-lines/?order=${orderId}`)
  },
  listOrderLines(params = {}) {
    const query = { page_size: 10000, ...params }
    return client.get('/order-lines/', { params: query })
  },
  createOrderLine(data) {
    return client.post('/order-lines/', data)
  },
  updateOrderLine(id, data) {
    return client.put(`/order-lines/${id}/`, data)
  },
  deleteOrderLine(id) {
    return client.delete(`/order-lines/${id}/`)
  },
})
