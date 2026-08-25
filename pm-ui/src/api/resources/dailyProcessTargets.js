export const createDailyProcessTargetsAPI = (client) => ({
  list(params) {
    return client.get('/daily-process-targets/', { params })
  },
  create(payload) {
    return client.post('/daily-process-targets/', payload)
  },
  update(id, payload) {
    return client.put(`/daily-process-targets/${id}/`, payload)
  },
  delete(id) {
    return client.delete(`/daily-process-targets/${id}/`)
  },
})
