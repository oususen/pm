export const createShippingProgressAPI = (client) => ({
  get(params = {}) {
    return client.get('/shipping-progress/', { params })
  },
  recalculate(payload = {}) {
    return client.post('/shipping-progress/', payload)
  },
  saveAdjust(payload = {}) {
    return client.post('/shipping-progress/adjust/', payload)
  },
  getActuals(params = {}) {
    return client.get('/shipping-actual-edit/', { params })
  },
  saveActuals(payload = {}) {
    return client.post('/shipping-actual-edit/', payload)
  },
})
