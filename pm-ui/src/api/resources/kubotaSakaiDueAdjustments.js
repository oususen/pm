export const createKubotaSakaiDueAdjustmentsAPI = (client) => ({
  list(params = {}) {
    return client.get('/kubota-sakai-due-adjustments/', { params })
  },
  grid(params = {}) {
    return client.get('/kubota-sakai-due-adjustments/grid/', { params })
  },
  importOrders(data = {}) {
    return client.post('/kubota-sakai-due-adjustments/import_orders/', data)
  },
  bulkSave(rows = []) {
    return client.post('/kubota-sakai-due-adjustments/bulk_save/', { rows })
  },
  get(id) {
    return client.get(`/kubota-sakai-due-adjustments/${id}/`)
  },
  create(data) {
    return client.post('/kubota-sakai-due-adjustments/', data)
  },
  update(id, data) {
    return client.put(`/kubota-sakai-due-adjustments/${id}/`, data)
  },
  remove(id) {
    return client.delete(`/kubota-sakai-due-adjustments/${id}/`)
  },
})
