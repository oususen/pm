export const createLineBacklogsAPI = (client) => ({
  expand(payload) {
    return client.post('/line-backlogs/expand/', payload)
  },
  pickup(payload) {
    return client.post('/line-backlogs/pickup/', payload)
  },
  save(payload) {
    return client.post('/line-backlogs/save/', payload)
  },
})
