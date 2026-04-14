export const createKubotaSakaiTripAssignmentsAPI = (client) => ({
  list(params = {}) {
    return client.get('/kubota-sakai-trip-assignments/', { params })
  },
  grid(params = {}) {
    return client.get('/kubota-sakai-trip-assignments/grid/', { params })
  },
  bulkSave(targetDate, rows = []) {
    return client.post('/kubota-sakai-trip-assignments/bulk_save/', { target_date: targetDate, rows })
  },
  get(id) {
    return client.get(`/kubota-sakai-trip-assignments/${id}/`)
  },
  create(data) {
    return client.post('/kubota-sakai-trip-assignments/', data)
  },
  update(id, data) {
    return client.put(`/kubota-sakai-trip-assignments/${id}/`, data)
  },
  remove(id) {
    return client.delete(`/kubota-sakai-trip-assignments/${id}/`)
  },
})
