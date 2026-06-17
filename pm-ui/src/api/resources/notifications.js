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
  listCallSessions(params = {}) {
    return client.get('/call-sessions/', { params })
  },
  getCallSession(id) {
    return client.get(`/call-sessions/${id}/`)
  },
  startCall(data) {
    return client.post('/call-sessions/start/', data)
  },
  acceptCall(id) {
    return client.post(`/call-sessions/${id}/accept/`)
  },
  declineCall(id) {
    return client.post(`/call-sessions/${id}/decline/`)
  },
  finishCall(id) {
    return client.post(`/call-sessions/${id}/finish/`)
  },
  getCallSignals(id, params = {}) {
    return client.get(`/call-sessions/${id}/signals/`, { params })
  },
  sendCallSignal(id, data) {
    return client.post(`/call-sessions/${id}/signals/`, data)
  },
  getPushSubscriptionConfig() {
    return client.get('/push-subscriptions/config/')
  },
  listPushSubscriptions() {
    return client.get('/push-subscriptions/')
  },
  subscribePush(data) {
    return client.post('/push-subscriptions/', data)
  },
  unsubscribePush(endpoint) {
    return client.post('/push-subscriptions/unsubscribe/', { endpoint })
  },
})
