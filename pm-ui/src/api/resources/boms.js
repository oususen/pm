export const createBomsAPI = (client) => ({
  getBOMs(params = {}) {
    const queryParams = new URLSearchParams()
    if (params.page !== undefined && params.page !== null && params.page !== '') {
      queryParams.append('page', params.page)
    }
    if (params.page_size !== undefined && params.page_size !== null && params.page_size !== '') {
      queryParams.append('page_size', params.page_size)
    }
    if (params.search) queryParams.append('search', params.search)
    if (params.parent_product) queryParams.append('parent_product', params.parent_product)
    if (params.parent_is_final !== undefined && params.parent_is_final !== '') {
      queryParams.append('parent_is_final', params.parent_is_final)
    }
    if (params.parent_is_line_final !== undefined && params.parent_is_line_final !== '') {
      queryParams.append('parent_is_line_final', params.parent_is_line_final)
    }
    if (params.is_coproduct !== undefined && params.is_coproduct !== '') {
      queryParams.append('is_coproduct', params.is_coproduct)
    }
    if (params.version) queryParams.append('version', params.version)
    if (params.created_from) queryParams.append('created_from', params.created_from)
    if (params.created_to) queryParams.append('created_to', params.created_to)
    if (params.is_active !== undefined && params.is_active !== '') {
      queryParams.append('is_active', params.is_active)
    }
    const query = queryParams.toString()
    return client.get(`/boms/${query ? '?' + query : ''}`)
  },
  getBOM(id) {
    return client.get(`/boms/${id}/`)
  },
  getBOMTree(id) {
    return client.get(`/boms/${id}/tree/`)
  },
  getBOMTreeExcelRows(id) {
    return client.get(`/boms/${id}/tree_excel_rows/`)
  },
  createBOM(data) {
    return client.post('/boms/', data)
  },
  updateBOM(id, data) {
    return client.put(`/boms/${id}/`, data)
  },
  deleteBOM(id) {
    return client.delete(`/boms/${id}/`)
  },
  generateRouting(bomId, data) {
    return client.post(`/boms/${bomId}/generate_routing/`, data)
  },
  copyBOM(bomId, newParentProductId) {
    return client.post(`/boms/${bomId}/copy/`, { new_parent_product_id: newParentProductId })
  },
  duplicateBOMVersion(bomId, data) {
    return client.post(`/boms/${bomId}/duplicate_version/`, data)
  },
  exportBOMExcel(bomId) {
    return client.get(`/boms/${bomId}/export_excel/`, { responseType: 'blob' })
  },
  downloadImportTemplateCsv() {
    return client.get('/boms/import_template_csv/', { responseType: 'blob' })
  },
  downloadImportTemplateXlsx() {
    return client.get('/boms/import_template_xlsx/', { responseType: 'blob' })
  },
  importBOMCsv(formData) {
    return client.post('/boms/import_csv/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  importBOMCheck(formData) {
    return client.post('/boms/import_check/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // BOM Items
  getBOMItems(params = {}) {
    const queryParams = new URLSearchParams()
    if (params.bom) queryParams.append('bom', params.bom)
    if (params.child_product) queryParams.append('child_product', params.child_product)
    if (params.sourcing_type) queryParams.append('sourcing_type', params.sourcing_type)
    if (params.process) queryParams.append('process', params.process)
    if (params.line) queryParams.append('line', params.line)
    if (params.supplier) queryParams.append('supplier', params.supplier)
    if (params.page_size) queryParams.append('page_size', params.page_size)
    const query = queryParams.toString()
    return client.get(`/bom-items/${query ? '?' + query : ''}`)
  },
  createBOMItem(data) {
    return client.post('/bom-items/', data)
  },
  updateBOMItem(id, data) {
    return client.put(`/bom-items/${id}/`, data)
  },
  getBOMItemDeletePreview(id) {
    return client.get(`/bom-items/${id}/delete_preview/`)
  },
  deleteBOMItem(id, options = {}) {
    const params = {}
    if (options.deleteRoutingSteps) params.delete_routing_steps = 'true'
    return client.delete(`/bom-items/${id}/`, { params })
  },
})
