export const createLineCycleTimesAPI = (client) => ({
  list(params = {}) {
    return client.get('/line-cycle-times/', { params: { page_size: 5000, ...params } })
  },
  matrix(lineId) {
    return client.get('/line-cycle-times/matrix/', { params: { line: lineId } })
  },
  bulkUpsert(items) {
    return client.post('/line-cycle-times/bulk_upsert/', { items })
  },
})
