export const createKubotaSakaiTripAssignmentsAPI_new = (client) => ({
  list(params = {}) {
    return client.get('/kubota-sakai-trip-assignments-new/', { params })
  },
  grid(params = {}) {
    return client.get('/kubota-sakai-trip-assignments-new/grid/', { params })
  },
  bulkSave(targetDate, rows = []) {
    return client.post('/kubota-sakai-trip-assignments-new/bulk_save/', { target_date: targetDate, rows })
  },
  previewLoad(targetDate, rows = [], previewRowsByDate = {}) {
    return client.post('/kubota-sakai-trip-assignments-new/preview-load/', {
      target_date: targetDate,
      rows,
      preview_rows_by_date: previewRowsByDate,
    })
  },
  loadDetail(targetDate) {
    return client.get('/kubota-sakai-trip-assignments-new/load-detail/', { params: { target_date: targetDate } })
  },
  pickupDetailPdf(startDate, endDate) {
    return client.get('/kubota-sakai-trip-assignments-new/pickup-detail-pdf/', {
      params: { start_date: startDate, end_date: endDate },
      responseType: 'blob',
    })
  },
  getPseudoTruckProducts() {
    return client.get('/kubota-sakai-trip-assignments-new/pseudo-truck-products/')
  },
  savePseudoTruckProducts(rows) {
    return client.post('/kubota-sakai-trip-assignments-new/pseudo-truck-products/', { rows })
  },
  getDisplaySettings() {
    return client.get('/kubota-sakai-trip-assignments-new/display-settings/')
  },
  saveDisplaySettings(rows) {
    return client.post('/kubota-sakai-trip-assignments-new/display-settings/', { rows })
  },
  saveDeliveryProgressAdjust(rows) {
    return client.post('/kubota-sakai-trip-assignments-new/delivery-progress-adjust/', { rows })
  },
  getTripNotices(targetDate, truckId) {
    return client.get('/kubota-sakai-trip-assignments-new/trip-notice/', {
      params: { target_date: targetDate, truck_id: truckId },
    })
  },
  saveTripNotice(targetDate, truckId, noticeText, noticeType = 'NORMAL') {
    return client.post('/kubota-sakai-trip-assignments-new/trip-notice/', {
      target_date: targetDate,
      truck_id: truckId,
      notice_text: noticeText,
      notice_type: noticeType,
    })
  },
  get(id) {
    return client.get(`/kubota-sakai-trip-assignments-new/${id}/`)
  },
  create(data) {
    return client.post('/kubota-sakai-trip-assignments-new/', data)
  },
  update(id, data) {
    return client.put(`/kubota-sakai-trip-assignments-new/${id}/`, data)
  },
  remove(id) {
    return client.delete(`/kubota-sakai-trip-assignments-new/${id}/`)
  },
})
