export const createCameraActualsAPI = (client) => ({
  createEvent(data) {
    return client.post('/production/camera-events/', data)
  },
  getDaily(params) {
    return client.get('/production/camera-results-daily/', { params })
  },
})
