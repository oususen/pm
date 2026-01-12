export const createLinePlansAPI = (client) => ({
  getLinePlans(params = {}) {
    const queryParams = new URLSearchParams()
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        queryParams.append(key, params[key])
      }
    })
    const query = queryParams.toString()
    return client.get(`/line-plans/${query ? '?' + query : ''}`)
  },
  save(payload) {
    return client.post('/line-plans/save/', payload)
  },
})
