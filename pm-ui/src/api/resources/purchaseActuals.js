export const createPurchaseActualsAPI = (client) => ({
  getCandidates(productCode) {
    return client.get('/purchase-actual/candidates/', { params: { product_code: productCode } })
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
})
