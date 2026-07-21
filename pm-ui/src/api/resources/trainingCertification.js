export const createTrainingCertificationAPI = (client) => ({
  listBooks(params = {}) {
    return client.get('/training-books/', { params })
  },
  listTracks(params = {}) {
    return client.get('/training-tracks/', { params })
  },
  startSession(payload) {
    return client.post('/training-exam-sessions/start/', payload)
  },
  listAttempts(params = {}) {
    return client.get('/training-attempts/', { params })
  },
  submitAttempt(payload) {
    return client.post('/training-attempts/', payload)
  },
  listStepRecords(params = {}) {
    return client.get('/training-step-records/', { params })
  },
  createStepRecord(payload) {
    return client.post('/training-step-records/', payload)
  },
  getProgressSummary(params = {}) {
    return client.get('/training-progress/summary/', { params })
  },
})
