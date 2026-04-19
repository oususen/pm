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
  previewLoad(targetDate, rows = []) {
    return client.post('/kubota-sakai-trip-assignments/preview-load/', { target_date: targetDate, rows })
  },
  loadDetail(targetDate) {
    return client.get('/kubota-sakai-trip-assignments/load-detail/', { params: { target_date: targetDate } })
  },
  pickupDetailPdf(startDate, endDate) {
    return client.get('/kubota-sakai-trip-assignments/pickup-detail-pdf/', {
      params: { start_date: startDate, end_date: endDate },
      responseType: 'blob',
    })
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
