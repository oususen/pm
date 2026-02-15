export const createLineBacklogsAPI = (client) => ({
  getLineBacklogs(params = {}) {
    const queryParams = new URLSearchParams()
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        queryParams.append(key, params[key])
      }
    })
    const query = queryParams.toString()
    return client.get(`/line-backlogs/${query ? '?' + query : ''}`)
  },
  pickup(payload) {
    return client.post('/line-backlogs/pickup/', payload)
  },
  pickupPurchase(payload) {
    return client.post('/line-backlogs/pickup_purchase/', payload)
  },
  expandProcesses(payload) {
    return client.post('/line-backlogs/expand_processes/', payload)
  },
  resolveUpstreamLines(payload) {
    return client.post('/line-backlogs/resolve_upstream_lines/', payload)
  },
  save(payload) {
    return client.post('/line-backlogs/save/', payload)
  },
  recalculateInventory(payload) {
    return client.post('/line-backlogs/recalculate_inventory/', payload)
  },
  importStocktakeExcel(formData) {
    return client.post('/line-backlogs/import_stocktake_excel/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  initializeStocktake(payload) {
    return client.post('/line-backlogs/initialize_stocktake/', payload)
  },
  initializeProgress(payload) {
    return client.post('/line-backlogs/initialize_progress/', payload)
  },
  recalculateScrap(payload) {
    return client.post('/line-backlogs/recalculate_scrap/', payload)
  },
})
