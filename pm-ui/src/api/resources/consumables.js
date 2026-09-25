// 消耗品管理API（バックエンド: apps/consumables, /api/consumables/）
export const createConsumablesAPI = (client) => ({
  // 消耗品
  listItems(params = {}) {
    return client.get('/consumables/items/', { params })
  },
  getItem(id) {
    return client.get(`/consumables/items/${id}/`)
  },
  // QR文字列から消耗品を特定（正規化・照合はサーバー側）
  lookupByQr(qr) {
    return client.get('/consumables/items/lookup/', { params: { qr } })
  },
  // 在庫一覧カード（未完了の依頼・直近入庫付き）
  listCards(params = {}) {
    return client.get('/consumables/items/cards/', { params })
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

  // 入出庫
  listMovements(params = {}) {
    return client.get('/consumables/movements/', { params })
  },
  summarizeMovements(params = {}) {
    return client.get('/consumables/movements/summary/', { params })
  },
  outbound(data) {
    return client.post('/consumables/movements/outbound/', data)
  },
  inbound(data) {
    return client.post('/consumables/movements/inbound/', data)
  },
  listWorkers() {
    return client.get('/consumables/movements/workers/')
  },

  // 注文依頼
  listRequests(params = {}) {
    return client.get('/consumables/requests/', { params })
  },
  createRequest(data) {
    return client.post('/consumables/requests/', data)
  },
  updateRequest(id, data) {
    return client.patch(`/consumables/requests/${id}/`, data)
  },
  deleteRequest(id) {
    return client.delete(`/consumables/requests/${id}/`)
  },
  setRequestStatus(id, status) {
    return client.post(`/consumables/requests/${id}/set-status/`, { status })
  },

  // 注文書（確認・承認は accounts の承認申請APIを使う）
  listDispatchOrders(params = {}) {
    return client.get('/consumables/dispatch-orders/', { params })
  },
  getDispatchOrder(id) {
    return client.get(`/consumables/dispatch-orders/${id}/`)
  },
  getDispatchRouteStatus() {
    return client.get('/consumables/dispatch-orders/route-status/')
  },
  createDispatchOrder(data) {
    return client.post('/consumables/dispatch-orders/create-order/', data)
  },
  deleteDispatchOrder(id) {
    return client.delete(`/consumables/dispatch-orders/${id}/`)
  },
  sendDispatchOrder(id, email) {
    return client.post(`/consumables/dispatch-orders/${id}/send/`, { email })
  },
  receiveDispatchOrder(id, data = {}) {
    return client.post(`/consumables/dispatch-orders/${id}/receive/`, data)
  },
  // PDFはログインセッション付きで取得する（Blob）
  fetchDispatchOrderPdf(id) {
    return client.get(`/consumables/dispatch-orders/${id}/pdf/`, { responseType: 'blob' })
  },
})
