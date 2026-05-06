export const createCameraActualsAPI = (client) => ({
  createEvent(data) {
    return client.post('/camera-events/', data)
  },
  autoDetect(data) {
    return client.post('/camera-auto-detect/', data)
  },
  getDaily(params) {
    return client.get('/camera-results-daily/', { params })
  },
})
