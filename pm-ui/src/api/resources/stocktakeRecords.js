export const createStocktakeRecordsAPI = (client) => ({
  list(params = {}) {
    return client.get('/stocktake-records/', { params })
  },
  save(payload) {
    return client.post('/stocktake-records/', payload)
  },
  history(productId, params = {}) {
    return client.get(`/stocktake-records/${productId}/history/`, { params })
  },
  deleteRecord(productId, recordId) {
    return client.delete(`/stocktake-records/${productId}/history/`, { params: { record_id: recordId } })
  },
  listRecorders(params = {}) {
    return client.get('/stocktake-recorders/', { params })
  },
  addRecorder(payload) {
    return client.post('/stocktake-recorders/', payload)
  },
  removeRecorder(payload) {
    return client.delete('/stocktake-recorders/', { data: payload })
  },
  getLayoutConfig() {
    return client.get('/stocktake-layout-config/')
  },
  saveLayoutConfig(payload) {
    return client.post('/stocktake-layout-config/', payload)
  },
})
