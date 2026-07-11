export const createShippingTraceAPI = (client) => ({
  getShippingTrace(params = {}) {
    const queryParams = new URLSearchParams()
    Object.keys(params).forEach((key) => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        queryParams.append(key, params[key])
      }
    })
    const query = queryParams.toString()
    return client.get(`/shipping-trace/${query ? '?' + query : ''}`)
  },
})
