export const createLineBacklogAdjustmentsAPI = (client) => ({
  list(params = {}) {
    return client.get('/line-backlog-adjustments/', { params })
  },
  save(payload) {
    return client.post('/line-backlog-adjustments/', payload)
  },
  remove(id) {
    return client.delete('/line-backlog-adjustments/', { params: { id } })
  },
})
