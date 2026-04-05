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
  pickupForProducts(payload) {
    return client.post('/line-backlogs/pickup_for_products/', payload)
  },
  pickupPurchase(payload) {
    return client.post('/line-backlogs/pickup_purchase/', payload)
  },
  pickupPurchaseForProducts(payload) {
    return client.post('/line-backlogs/pickup_purchase_for_products/', payload)
  },
  seedProgressBacklogsFromDemand(payload) {
    return client.post('/line-backlogs/seed_progress_backlogs_from_demand/', payload)
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
  getCalcStartDate(params) {
    return client.get('/line-backlogs/calc_start_date/', { params })
  },
  getBatchAdjustInfo(params) {
    return client.get('/line-backlogs/batch_adjust_info/', { params })
  },
  recalculateInventory(payload) {
    return client.post('/line-backlogs/recalculate_inventory/', payload)
  },
  recalculateInventoryDeep(payload) {
    return client.post('/line-backlogs/recalculate_inventory_deep/', payload)
  },
  recalculateInventoryForProducts(payload) {
    return client.post('/line-backlogs/recalculate_inventory_for_products/', payload)
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
  recalculateScrapForProducts(payload) {
    return client.post('/line-backlogs/recalculate_scrap_for_products/', payload)
  },
  detectStockMigration(payload) {
    return client.post('/stock-migration/detect/', payload)
  },
  executeStockMigration(payload) {
    return client.post('/stock-migration/execute/', payload)
  },
})
