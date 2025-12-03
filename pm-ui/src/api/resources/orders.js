export const createOrdersAPI = (client) => ({
  getOrders() {
    return client.get('/orders/')
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
