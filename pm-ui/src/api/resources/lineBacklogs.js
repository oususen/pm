export const createLineBacklogsAPI = (client) => ({
  pickup(payload) {
    return client.post('/line-backlogs/pickup/', payload)
  },
  save(payload) {
    return client.post('/line-backlogs/save/', payload)
  },
})
