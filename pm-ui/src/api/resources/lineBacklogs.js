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
  save(payload) {
    return client.post('/line-backlogs/save/', payload)
  },
  recalculateInventory(payload) {
    return client.post('/line-backlogs/recalculate_inventory/', payload)
  },
  recalculateScrap(payload) {
    return client.post('/line-backlogs/recalculate_scrap/', payload)
  },
})
