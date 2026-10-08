export const createKubotaSakaiTripAssignmentsAPI = (client) => ({
  list(params = {}) {
    return client.get('/kubota-sakai-trip-assignments/', { params })
  },
  grid(params = {}) {
    return client.get('/kubota-sakai-trip-assignments/grid/', { params })
  },
  importOrders(data = {}) {
    return client.post('/kubota-sakai-trip-assignments/import-orders/', data)
  },
  bulkSave(targetDate, rows = []) {
    return client.post('/kubota-sakai-trip-assignments/bulk_save/', { target_date: targetDate, rows })
  },
  previewLoad(targetDate, rows = [], previewRowsByDate = {}) {
    return client.post('/kubota-sakai-trip-assignments/preview-load/', {
      target_date: targetDate,
      rows,
      preview_rows_by_date: previewRowsByDate,
    })
  },
  autoAssign(startDate, endDate, resetExistingAssignments = false, prioritizeProductDisplayOrder = false) {
    return client.post('/kubota-sakai-trip-assignments/auto-assign/', {
      start_date: startDate,
      end_date: endDate,
      reset_existing_assignments: Boolean(resetExistingAssignments),
      prioritize_product_display_order: Boolean(prioritizeProductDisplayOrder),
    })
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
  getPseudoTruckProducts() {
    return client.get('/kubota-sakai-trip-assignments/pseudo-truck-products/')
  },
  savePseudoTruckProducts(rows) {
    return client.post('/kubota-sakai-trip-assignments/pseudo-truck-products/', { rows })
  },
  getDisplaySettings() {
    return client.get('/kubota-sakai-trip-assignments/display-settings/')
  },
  saveDisplaySettings(rows) {
    return client.post('/kubota-sakai-trip-assignments/display-settings/', { rows })
  },
  saveDeliveryProgressAdjust(rows) {
    return client.post('/kubota-sakai-trip-assignments/delivery-progress-adjust/', { rows })
  },
  getTripNotices(targetDate, truckId = null, tripRef = '') {
    return client.get('/kubota-sakai-trip-assignments/trip-notice/', {
      params: {
        target_date: targetDate,
        ...(truckId ? { truck_id: truckId } : {}),
        ...(tripRef ? { trip_ref: tripRef } : {}),
      },
    })
  },
  saveTripNotice(targetDate, truckId = null, noticeText = '', noticeType = 'NORMAL', tripRef = '') {
    return client.post('/kubota-sakai-trip-assignments/trip-notice/', {
      target_date: targetDate,
      ...(truckId ? { truck_id: truckId } : {}),
      ...(tripRef ? { trip_ref: tripRef } : {}),
      notice_text: noticeText,
      notice_type: noticeType,
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
