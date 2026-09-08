export const createPurchaseActualsAPI = (client) => ({
  getCandidates(productCode, arrivalDate) {
    return client.get('/purchase-actual/candidates/', {
      params: { product_code: productCode, arrival_date: arrivalDate || undefined },
    })
  },
  getProgress(params) {
    return client.get('/purchase-actual/progress/', { params })
  },
  getInquiry(params) {
    return client.get('/purchase-actual/inquiry/', { params })
  },
  register(payload) {
    return client.post('/purchase-actual/register/', payload)
  },
  bulkRegister(payload) {
    return client.post('/purchase-actual/bulk-register/', payload)
  },
  update(id, payload) {
    return client.put(`/purchase-actual/${id}/`, payload)
  },
  remove(id) {
    return client.delete(`/purchase-actual/${id}/`)
  },
  getBulkItems(params) {
    return client.get('/purchase-actual/bulk-items/', { params })
  },
  resolveCsvItems(payload) {
    return client.post('/purchase-actual/csv-resolve/', payload)
  },
})
