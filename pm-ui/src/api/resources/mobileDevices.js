export const createMobileDevicesAPI = (client) => ({
  list(params = {}) {
    return client.get('/mobile-devices/', { params })
  },
  get(id) {
    return client.get(`/mobile-devices/${id}/`)
  },
  create(data) {
    return client.post('/mobile-devices/', data)
  },
  update(id, data) {
    return client.put(`/mobile-devices/${id}/`, data)
  },
  delete(id) {
    return client.delete(`/mobile-devices/${id}/`)
  },
  importExcel(formData) {
    return client.post('/mobile-devices/import_excel/', formData)
  },
  getBaseURL() {
    return client.defaults.baseURL || '/api'
  },
  exportExcelUrl() {
    return (client.defaults.baseURL || '/api') + '/mobile-devices/export_excel/'
  },
  inventoryChecklistUrl() {
    return (client.defaults.baseURL || '/api') + '/mobile-devices/inventory_checklist/'
  },
  printLabelsUrl(ids = []) {
    const q = ids.length ? `?ids=${ids.join(',')}` : ''
    return (client.defaults.baseURL || '/api') + `/mobile-devices/print_labels/${q}`
  },
  readManualDoc(path) {
    return client.get('/manual-documents/read/', { params: { path } })
  },
  writeManualDoc(path, content) {
    return client.post('/manual-documents/write/', { path, content })
  },
  listHistory(deviceId) {
    return client.get(`/mobile-devices/${deviceId}/history/`)
  },
  listInventories(params = {}) {
    return client.get('/mobile-device-inventories/', { params })
  },
  createInventory(data) {
    return client.post('/mobile-device-inventories/', data)
  },
  updateInventory(id, data) {
    return client.put(`/mobile-device-inventories/${id}/`, data)
  },
})
