export const createOrphanBacklogAPI = (client) => ({
  getReport(params = {}) {
    return client.get('/orphan-backlog/report/', { params })
  },
  runFix(payload = {}) {
    return client.post('/orphan-backlog/fix/', payload)
  },
})
