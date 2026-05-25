export const createAutoPlanAggregateSettingsAPI = (client) => ({
  list(params = {}) {
    return client.get('/auto-plan-aggregate-settings/', { params })
  },
  create(payload) {
    return client.post('/auto-plan-aggregate-settings/', payload)
  },
  update(id, payload) {
    return client.put(`/auto-plan-aggregate-settings/${id}/`, payload)
  },
  patch(id, payload) {
    return client.patch(`/auto-plan-aggregate-settings/${id}/`, payload)
  },
  remove(id) {
    return client.delete(`/auto-plan-aggregate-settings/${id}/`)
  },
})

