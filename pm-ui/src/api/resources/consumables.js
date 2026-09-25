// 消耗品管理API（バックエンド: apps/consumables, /api/consumables/）
export const createConsumablesAPI = (client) => ({
  // 消耗品
  listItems(params = {}) {
    return client.get('/consumables/items/', { params })
  },
  getItem(id) {
    return client.get(`/consumables/items/${id}/`)
  },
  getItemByCode(code) {
    return client.get(`/consumables/items/by-code/${encodeURIComponent(code)}/`)
  },
  createItem(data) {
    return client.post('/consumables/items/', data)
  },
  updateItem(id, data) {
    return client.put(`/consumables/items/${id}/`, data)
  },
  deleteItem(id) {
    return client.delete(`/consumables/items/${id}/`)
  },
  uploadItemImage(id, formData) {
    return client.post(`/consumables/items/${id}/upload-image/`, formData)
  },
  importItemsCsv(formData) {
    return client.post('/consumables/items/import-csv/', formData)
  },
  getFilterOptions() {
    return client.get('/consumables/items/filter-options/')
  },

  // 購入先
  listSuppliers(params = {}) {
    return client.get('/consumables/suppliers/', { params })
  },
  createSupplier(data) {
    return client.post('/consumables/suppliers/', data)
  },
  updateSupplier(id, data) {
    return client.put(`/consumables/suppliers/${id}/`, data)
  },
  deleteSupplier(id) {
    return client.delete(`/consumables/suppliers/${id}/`)
  },
  importSuppliersCsv(formData) {
    return client.post('/consumables/suppliers/import-csv/', formData)
  },
})
