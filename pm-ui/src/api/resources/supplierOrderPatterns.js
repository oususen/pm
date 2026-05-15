export const createSupplierOrderPatternsAPI = (client) => ({
  list(params = {}) {
    return client.get('/supplier-order-patterns/', { params })
  },
  create(data) {
    return client.post('/supplier-order-patterns/', data)
  },
  update(id, data) {
    return client.put(`/supplier-order-patterns/${id}/`, data)
  },
  delete(id) {
    return client.delete(`/supplier-order-patterns/${id}/`)
  },
})
