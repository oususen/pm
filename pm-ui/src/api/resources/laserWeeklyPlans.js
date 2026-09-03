export const createLaserWeeklyPlansAPI = (client) => ({
  getWeeklyPlan(params = {}) {
    return client.get('/laser-weekly-plans/', { params })
  },
  getDownstreamProducts(lineId) {
    return client.get('/laser-weekly-plans/downstream-products/', { params: { line_id: lineId } })
  },
  saveManualQuantities(quantities) {
    return client.post('/laser-weekly-plans/manual-quantities/', { quantities })
  },
  savePatternManualQuantities(quantities) {
    return client.post('/laser-weekly-plans/pattern-manual-quantities/', { quantities })
  },
  saveInitialProgress(items) {
    return client.post('/laser-weekly-plans/save-initial-progress/', { items })
  },
  getMaterialOrderProgress(startDate) {
    return client.get('/laser-weekly-plans/material-order-progress/', { params: { start_date: startDate } })
  },
  saveMaterialOrderProgress(startDate, items) {
    return client.post('/laser-weekly-plans/material-order-progress/', { start_date: startDate, items })
  },
  getMaterialInitialProgress(startDate) {
    return client.get('/laser-weekly-plans/material-initial-progress/', { params: { start_date: startDate } })
  },
  saveMaterialInitialProgress(startDate, items) {
    return client.post('/laser-weekly-plans/material-initial-progress/', { start_date: startDate, items })
  },
  exportMaterialOrderExcel(planStartDate, supplier, startDate, endDate) {
    return client.get('/laser-weekly-plans/material-order-excel/', { params: { plan_start_date: planStartDate, start_date: startDate, end_date: endDate, supplier }, responseType: 'blob' })
  },
  getTargets(params = {}) {
    return client.get('/laser-weekly-plan-targets/', { params })
  },
  createTarget(data) {
    return client.post('/laser-weekly-plan-targets/', data)
  },
  updateTarget(id, data) {
    return client.put(`/laser-weekly-plan-targets/${id}/`, data)
  },
  deleteTarget(id) {
    return client.delete(`/laser-weekly-plan-targets/${id}/`)
  },
  getMaterialGroups(params = {}) {
    return client.get('/laser-weekly-material-groups/', { params })
  },
  createMaterialGroup(data) {
    return client.post('/laser-weekly-material-groups/', data)
  },
  updateMaterialGroup(id, data) {
    return client.put(`/laser-weekly-material-groups/${id}/`, data)
  },
  deleteMaterialGroup(id) {
    return client.delete(`/laser-weekly-material-groups/${id}/`)
  },
  getMaterialOrderSummary(startDate, endDate) {
    return client.get('/laser-weekly-plans/material-order-summary/', { params: { start_date: startDate, end_date: endDate } })
  },
  createMaterialOrderManual(data) {
    return client.post('/laser-weekly-plans/material-order-manual/', data)
  },
  deleteMaterialOrderManual(id) {
    return client.delete(`/laser-weekly-plans/material-order-manual/${id}/`)
  },
})
