export const createOutsourceAPI = (client) => ({
  // 外作先マスタ
  getSubcontractors(params = {}) {
    return client.get('/outsource/subcontractors/', { params })
  },
  createSubcontractor(data) {
    return client.post('/outsource/subcontractors/', data)
  },
  updateSubcontractor(id, data) {
    return client.put(`/outsource/subcontractors/${id}/`, data)
  },
  deleteSubcontractor(id) {
    return client.delete(`/outsource/subcontractors/${id}/`)
  },

  // 構成品マスタ
  getComponentMaterials(params = {}) {
    return client.get('/outsource/component-materials/', { params })
  },
  createComponentMaterial(data) {
    return client.post('/outsource/component-materials/', data)
  },
  updateComponentMaterial(id, data) {
    return client.put(`/outsource/component-materials/${id}/`, data)
  },
  deleteComponentMaterial(id) {
    return client.delete(`/outsource/component-materials/${id}/`)
  },

  // 外作品目マスタ
  getItems(params = {}) {
    return client.get('/outsource/items/', { params })
  },
  getItem(id) {
    return client.get(`/outsource/items/${id}/`)
  },
  createItem(data) {
    return client.post('/outsource/items/', data)
  },
  updateItem(id, data) {
    return client.put(`/outsource/items/${id}/`, data)
  },
  deleteItem(id) {
    return client.delete(`/outsource/items/${id}/`)
  },

  // 外作BOM
  getBOMLines(params = {}) {
    return client.get('/outsource/bom/', { params })
  },
  createBOMLine(data) {
    return client.post('/outsource/bom/', data)
  },
  updateBOMLine(id, data) {
    return client.put(`/outsource/bom/${id}/`, data)
  },
  deleteBOMLine(id) {
    return client.delete(`/outsource/bom/${id}/`)
  },

  // 受注（案件）
  getOrders(params = {}) {
    return client.get('/outsource/orders/', { params })
  },
  getOrder(id) {
    return client.get(`/outsource/orders/${id}/`)
  },
  importCSV(formData) {
    return client.post('/outsource/orders/import-csv/', formData)
  },
  getFirstArticleContacts(params = {}) {
    return client.get('/outsource/orders/first-article-contacts/', { params })
  },
  sendFirstArticleNotice(data) {
    return client.post('/outsource/orders/send-first-article-notice/', data)
  },
  calculateConstraints(id, data = {}) {
    return client.post(`/outsource/orders/${id}/calculate-constraints/`, data)
  },
  exportExcel(orderIds) {
    return client.post('/outsource/orders/export-excel/', { order_ids: orderIds }, { responseType: 'blob' })
  },
  importSplitExcel(formData) {
    return client.post('/outsource/orders/import-split-excel/', formData)
  },
  explodeMaterials(id) {
    return client.post(`/outsource/orders/${id}/explode-materials/`)
  },

  // 分割計画
  getSplits(params = {}) {
    return client.get('/outsource/splits/', { params })
  },
  createSplit(data) {
    return client.post('/outsource/splits/', data)
  },
  updateSplit(id, data) {
    return client.put(`/outsource/splits/${id}/`, data)
  },
  deleteSplit(id) {
    return client.delete(`/outsource/splits/${id}/`)
  },

  // 材料所要量
  getMaterials(params = {}) {
    return client.get('/outsource/materials/', { params })
  },
  updateMaterial(id, data) {
    return client.put(`/outsource/materials/${id}/`, data)
  },
  patchMaterial(id, data) {
    return client.patch(`/outsource/materials/${id}/`, data)
  },
  supplyMaterial(id, data = {}) {
    return client.post(`/outsource/materials/${id}/supply/`, data)
  },
  receiveMaterial(id, data = {}) {
    return client.post(`/outsource/materials/${id}/receive/`, data)
  },
  generatePurchaseOrder(data = {}) {
    return client.post('/outsource/materials/purchase-order/', data, { responseType: 'blob' })
  },

  // 外作先納入（受入記録）
  getDeliveries(params = {}) {
    return client.get('/outsource/deliveries/', { params })
  },
  createDelivery(data) {
    return client.post('/outsource/deliveries/', data)
  },
  deleteDelivery(id) {
    return client.delete(`/outsource/deliveries/${id}/`)
  },

  // 顧客出荷記録
  getShipments(params = {}) {
    return client.get('/outsource/shipments/', { params })
  },
  createShipment(data) {
    return client.post('/outsource/shipments/', data)
  },
  deleteShipment(id) {
    return client.delete(`/outsource/shipments/${id}/`)
  },

  // 材料在庫
  getMaterialStockTx(params = {}) {
    return client.get('/outsource/material-stock/', { params })
  },
  getMaterialStockSummary(params = {}) {
    return client.get('/outsource/material-stock/summary/', { params })
  },
  createMaterialStockAdjust(data) {
    return client.post('/outsource/material-stock/', data)
  },

  // 完成品在庫
  getProductStockTx(params = {}) {
    return client.get('/outsource/product-stock/', { params })
  },
  getProductStockSummary(params = {}) {
    return client.get('/outsource/product-stock/summary/', { params })
  },
  createProductStockAdjust(data) {
    return client.post('/outsource/product-stock/', data)
  },

  // 分割計画取込履歴
  getSplitImportLogs(params = {}) {
    return client.get('/outsource/split-import-logs/', { params })
  },
})
