export const createRoutingsAPI = (client) => ({
  getRoutings(params = {}) {
    return client.get('/routings/', { params })
  },
  async getAllRoutings(params = {}) {
    const collected = []
    let page = 1
    while (true) {
      const res = await client.get('/routings/', {
        params: { page, page_size: 500, ...params },
      })
      const data = res.data
      if (Array.isArray(data)) return data
      if (data?.results) {
        collected.push(...data.results)
      }
      if (!data?.next) break
      page += 1
    }
    return collected
  },
  getRoutingStepsByLine(lineId) {
    return client.get(`/routing-steps/?line=${lineId}`)
  },
  getRouting(id) {
    return client.get(`/routings/${id}/`)
  },
  createRouting(data) {
    return client.post('/routings/', data)
  },
  updateRouting(id, data) {
    return client.put(`/routings/${id}/`, data)
  },
  patchRouting(id, data) {
    return client.patch(`/routings/${id}/`, data)
  },
  deleteRouting(id) {
    return client.delete(`/routings/${id}/`)
  },

  // Routing Steps
  getRoutingSteps(routingOrParams) {
    if (typeof routingOrParams === 'object' && routingOrParams !== null) {
      return client.get('/routing-steps/', { params: routingOrParams })
    }
    return client.get(`/routing-steps/?routing=${routingOrParams}`)
  },
  createRoutingStep(data) {
    return client.post('/routing-steps/', data)
  },
  updateRoutingStep(id, data) {
    return client.put(`/routing-steps/${id}/`, data)
  },
  patchRoutingStep(id, data) {
    return client.patch(`/routing-steps/${id}/`, data)
  },
  deleteRoutingStep(id) {
    return client.delete(`/routing-steps/${id}/`)
  },
  getRoutingStepMaterials(params = {}) {
    return client.get('/routing-step-materials/', { params })
  },
  getCoproductDriverChildProducts() {
    return client.get('/routing-steps/coproduct-driver-child-products/')
  },
})
