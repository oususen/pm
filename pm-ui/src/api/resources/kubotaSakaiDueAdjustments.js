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
  bulkSave(rows = [], options = {}) {
    const payload = { rows }
    if (options.change_reason) payload.change_reason = options.change_reason
    return client.post('/kubota-sakai-due-adjustments/bulk_save/', payload)
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
  linkForwardPlans(data) {
    return client.post('/kubota-sakai-due-adjustments/link_forward_plans/', data)
  },
  getContacts() {
    return client.get('/kubota-sakai-due-adjustments/get_contacts/')
  },
  sendEmail(data) {
    return client.post('/kubota-sakai-due-adjustments/send_email/', data)
  },
  saveCoordinationNote(dueAdjustmentId, coordinationNote) {
    return client.post('/kubota-sakai-due-adjustments/save_coordination_note/', {
      due_adjustment_id: dueAdjustmentId,
      coordination_note: coordinationNote,
    })
  },
})
