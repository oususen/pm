export const createContainerCapacitiesAPI = (client) => ({
  getContainerCapacities(params) {
    return client.get('/container-capacities/', { params })
  },
  getContainerCapacity(id) {
    return client.get(`/container-capacities/${id}/`)
  },
  createContainerCapacity(data) {
    return client.post('/container-capacities/', data)
  },
  updateContainerCapacity(id, data) {
    return client.put(`/container-capacities/${id}/`, data)
  },
  deleteContainerCapacity(id) {
    return client.delete(`/container-capacities/${id}/`)
  },
})
