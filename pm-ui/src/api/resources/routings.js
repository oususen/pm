export const createRoutingsAPI = (client) => ({
  getRoutings() {
    return client.get('/routings/')
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
  deleteRouting(id) {
    return client.delete(`/routings/${id}/`)
  },

  // Routing Steps
  getRoutingSteps(routingId) {
    return client.get(`/routing-steps/?routing=${routingId}`)
  },
  createRoutingStep(data) {
    return client.post('/routing-steps/', data)
  },
  updateRoutingStep(id, data) {
    return client.put(`/routing-steps/${id}/`, data)
  },
  deleteRoutingStep(id) {
    return client.delete(`/routing-steps/${id}/`)
  },
})
