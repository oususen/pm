export const createInterruptionReasonsAPI = (client) => ({
  getInterruptionReasons(params) {
    return client.get('/interruption-reasons/', { params })
  },
  createInterruptionReason(data) {
    return client.post('/interruption-reasons/', data)
  },
  updateInterruptionReason(id, data) {
    return client.patch(`/interruption-reasons/${id}/`, data)
  },
})
