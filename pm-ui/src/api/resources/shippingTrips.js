export const createShippingTripsAPI = (client) => ({
  execution(params = {}) {
    return client.get('/shipping-trips/execution/', { params })
  },
  updateExecutionStatus(payload = {}) {
    return client.post('/shipping-trips/execution/', payload)
  },
  progress(params = {}) {
    return client.get('/shipping-trips/progress/', { params })
  },
})
