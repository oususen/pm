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
  delete(id) {
    return client.delete(`/purchase-order-proposals/${id}/`)
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
  cancel(id, data = {}) {
    return client.post(`/purchase-order-proposals/${id}/cancel/`, data)
  },
  send(id, data = {}) {
    return client.post(`/purchase-order-proposals/${id}/send/`, data)
  },
  downloadPdf(id) {
    return client.get(`/purchase-order-proposals/${id}/pdf/`, { responseType: 'blob' })
  },
  autoFill(id, data = {}) {
    return client.post(`/purchase-order-proposals/${id}/auto_fill/`, data)
  },
  listTasks(params = {}) {
    return client.get('/purchase-order-tasks/', { params })
  },
  getEmailConfigs() {
    return client.get('/purchase-order-proposal-email-configs/')
  },
  getEmailConfig(supplierId) {
    return client.get(`/purchase-order-proposal-email-configs/${supplierId}/`)
  },
  updateEmailConfig(supplierId, data) {
    return client.put(`/purchase-order-proposal-email-configs/${supplierId}/`, data)
  },
})
