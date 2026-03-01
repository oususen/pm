export const createPurchaseOrderProposalsAPI = (client) => ({
  list(params = {}) {
    return client.get('/purchase-order-proposals/', { params })
  },
  create(data) {
    return client.post('/purchase-order-proposals/', data)
  },
  get(id) {
    return client.get(`/purchase-order-proposals/${id}/`)
  },
  update(id, data) {
    return client.put(`/purchase-order-proposals/${id}/`, data)
  },
  submit(id, data = {}) {
    return client.post(`/purchase-order-proposals/${id}/submit/`, data)
  },
  approve(id, data = {}) {
    return client.post(`/purchase-order-proposals/${id}/approve/`, data)
  },
  reject(id, data = {}) {
    return client.post(`/purchase-order-proposals/${id}/reject/`, data)
  },
  send(id, data = {}) {
    return client.post(`/purchase-order-proposals/${id}/send/`, data)
  },
  autoFill(id, data = {}) {
    return client.post(`/purchase-order-proposals/${id}/auto_fill/`, data)
  },
  listTasks(params = {}) {
    return client.get('/purchase-order-tasks/', { params })
  },
})
