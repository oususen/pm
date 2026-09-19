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
  savePatternManualQuantities(quantities, progressValues) {
    return client.post('/laser-weekly-plans/pattern-manual-quantities/', { quantities, progress_values: progressValues })
  },
  savePatternWeekCarryover(items) {
    return client.post('/laser-weekly-plans/pattern-week-carryover/', { items })
  },
  resetPatternManualQuantities(startDate, endDate) {
    return client.post('/laser-weekly-plans/pattern-manual-reset/', { start_date: startDate, end_date: endDate })
  },
  saveInitialProgress(items) {
    return client.post('/laser-weekly-plans/save-initial-progress/', { items })
  },
  getMaterialOrderProgress(startDate, displayStart = '', displayEnd = '') {
    return client.get('/laser-weekly-plans/material-order-progress/', { params: { start_date: startDate, display_start: displayStart, display_end: displayEnd } })
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
  saveMaterialDailyProgress(items) {
    return client.post('/laser-weekly-plans/material-daily-progress/', { items })
  },
  saveMaterialWeekCarryover(items) {
    return client.post('/laser-weekly-plans/material-week-carryover/', { items })
  },
  getMaterialOrderApproval(startDate, displayStart = '', displayEnd = '') {
    return client.get('/laser-weekly-plans/material-order-approval/', { params: { start_date: startDate, display_start: displayStart, display_end: displayEnd } })
  },
  getMaterialOrderEmailConfigs() {
    return client.get('/laser-material-order-email-configs/')
  },
  updateMaterialOrderEmailConfig(supplier, data) {
    return client.put(`/laser-material-order-email-configs/${supplier}/`, data)
  },
  createMaterialOrderApproval(startDate, lockStartDate, lockEndDate, supplier) {
    return client.post('/laser-weekly-plans/material-order-approval/', {
      start_date: startDate,
      lock_start_date: lockStartDate,
      lock_end_date: lockEndDate,
      supplier,
    })
  },
  reopenMaterialOrderApproval(startDate, lockStartDate, lockEndDate, supplier) {
    return client.post('/laser-weekly-plans/material-order-approval/', {
      start_date: startDate,
      lock_start_date: lockStartDate,
      lock_end_date: lockEndDate,
      supplier,
      action: 'reopen',
    })
  },
  adjustMaterialOrderApproval(startDate, lockStartDate, lockEndDate, supplier) {
    return client.post('/laser-weekly-plans/material-order-approval/', {
      start_date: startDate,
      lock_start_date: lockStartDate,
      lock_end_date: lockEndDate,
      supplier,
      action: 'adjust',
    })
  },
  saveMaterialOrderAdjustment(startDate, lockStartDate, lockEndDate, supplier) {
    return client.post('/laser-weekly-plans/material-order-adjustment-save/', {
      start_date: startDate,
      lock_start_date: lockStartDate,
      lock_end_date: lockEndDate,
      supplier,
    })
  },
  sendMaterialOrder(startDate, supplier, lockStartDate, lockEndDate) {
    return client.post('/laser-weekly-plans/material-order-send/', {
      start_date: startDate,
      supplier,
      lock_start_date: lockStartDate,
      lock_end_date: lockEndDate,
    })
  },
  resetMaterialOrderApproval(startDate, lockStartDate, lockEndDate) {
    return client.post('/laser-weekly-plans/material-order-reset/', {
      start_date: startDate,
      lock_start_date: lockStartDate,
      lock_end_date: lockEndDate,
    })
  },
  exportMaterialOrderExcel(planStartDate, supplier, startDate, endDate) {
    return client.get('/laser-weekly-plans/material-order-excel/', { params: { plan_start_date: planStartDate, start_date: startDate, end_date: endDate, supplier }, responseType: 'blob' })
  },
  exportMaterialOrderPdf(planStartDate, supplier, startDate, endDate) {
    return client.get('/laser-weekly-plans/material-order-pdf/', { params: { plan_start_date: planStartDate, start_date: startDate, end_date: endDate, supplier }, responseType: 'blob' })
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
  getMaterialReceipts(startDate, endDate) {
    return client.get('/laser-weekly-plans/material-receipts/', { params: { start_date: startDate, end_date: endDate } })
  },
  createMaterialReceipt(data) {
    return client.post('/laser-weekly-plans/material-receipts/', data)
  },
  cancelMaterialReceipt(id, cancelReason = '') {
    return client.post(`/laser-weekly-plans/material-receipts/${id}/cancel/`, { cancel_reason: cancelReason })
  },
})
