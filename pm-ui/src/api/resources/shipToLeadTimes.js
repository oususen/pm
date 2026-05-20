export const createShipToLeadTimesAPI = (client) => ({
  getAll(params = {}) {
    return client.get('/ship-to-lead-times/', { params })
  },
  create(data) {
    return client.post('/ship-to-lead-times/', data)
  },
  update(id, data) {
    return client.put(`/ship-to-lead-times/${id}/`, data)
  },
  delete(id) {
    return client.delete(`/ship-to-lead-times/${id}/`)
  },
})
