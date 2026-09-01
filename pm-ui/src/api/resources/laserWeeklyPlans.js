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
})
