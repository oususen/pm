export const createMorningMeetingsAPI = (client) => ({
  list(params = {}) {
    return client.get('/morning-meetings/', { params })
  },
  get(id) {
    return client.get(`/morning-meetings/${id}/`)
  },
  create(data) {
    return client.post('/morning-meetings/', data, data instanceof FormData
      ? { headers: { 'Content-Type': 'multipart/form-data' } }
      : undefined)
  },
  update(id, data) {
    return client.patch(`/morning-meetings/${id}/`, data, data instanceof FormData
      ? { headers: { 'Content-Type': 'multipart/form-data' } }
      : undefined)
  },
  delete(id) {
    return client.delete(`/morning-meetings/${id}/`)
  },
  duplicate(id, data = {}) {
    return client.post(`/morning-meetings/${id}/duplicate/`, data)
  },
  start(id) {
    return client.post(`/morning-meetings/${id}/start/`)
  },
  saveExecution(id, data) {
    return client.post(`/morning-meetings/${id}/save_execution/`, data)
  },
  complete(id, data) {
    return client.post(`/morning-meetings/${id}/complete/`, data)
  },
})
