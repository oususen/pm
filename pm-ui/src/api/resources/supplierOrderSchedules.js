export const createSupplierOrderSchedulesAPI = (client) => ({
  list(params = {}) {
    return client.get('/supplier-order-schedules/', { params })
  },
  create(data) {
    return client.post('/supplier-order-schedules/', data)
  },
  update(id, data) {
    return client.put(`/supplier-order-schedules/${id}/`, data)
  },
  delete(id) {
    return client.delete(`/supplier-order-schedules/${id}/`)
  },
})
