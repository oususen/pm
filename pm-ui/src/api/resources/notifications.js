export const createNotificationsAPI = (client) => ({
  list(params = {}) {
    return client.get('/notifications/', { params })
  },
  get(id) {
    return client.get(`/notifications/${id}/`)
  },
  create(data) {
    return client.post('/notifications/', data)
  },
  update(id, data) {
    return client.put(`/notifications/${id}/`, data)
  },
  delete(id) {
    return client.delete(`/notifications/${id}/`)
  },
})
