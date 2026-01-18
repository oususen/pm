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
  markRead(id) {
    return client.post(`/notifications/${id}/mark_read/`)
  },
  markAllRead(notificationIds = []) {
    return client.post('/notifications/mark_all_read/', { notification_ids: notificationIds })
  },
})
