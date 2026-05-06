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
  uploadShapeDataset(formData) {
    return client.post('/camera-shape-training/upload-dataset/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  uploadShapePhotos(formData) {
    return client.post('/camera-shape-training/upload-photos/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  startShapeTraining(data) {
    return client.post('/camera-shape-training/start/', data)
  },
  getShapeTrainingStatus() {
    return client.get('/camera-shape-training/status/')
  },
})
