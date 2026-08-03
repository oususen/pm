export const createProductsAPI = (client) => ({
  getProducts(params = {}) {
    return client.get('/products/', { params })
  },
  async getAllProducts(params = {}) {
    // ページング有りでも全件取得できるように順次取得
    const collected = []
    let page = 1
    while (true) {
      const res = await client.get('/products/', {
        params: { page, page_size: 5000, ...params },
      })
      const data = res.data
      if (Array.isArray(data)) return data
      if (data?.results) {
        collected.push(...data.results)
      }
      if (!data?.next) break
      page += 1
    }
    return collected
  },
  getProductsByCodesIn(codes) {
    if (!codes.length) return Promise.resolve({ data: [] })
    return client.get('/products/', {
      params: { product_codes_in: codes.join(','), page_size: codes.length + 10 },
    })
  },
  getProduct(id) {
    return client.get(`/products/${id}/`)
  },
  createProduct(data) {
    return client.post('/products/', data)
  },
  updateProduct(id, data) {
    return client.put(`/products/${id}/`, data)
  },
  uploadProductImage(id, formData) {
    return client.post(`/products/${id}/upload_image/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteProduct(id) {
    return client.delete(`/products/${id}/`)
  },
  setStockLocations(id, locations) {
    return client.post(`/products/${id}/stock-locations/`, { locations })
  },
  getWhereUsed(id, recursive = false, referenceDate = null) {
    const params = { recursive: recursive ? 'true' : 'false' }
    if (referenceDate) params.reference_date = referenceDate
    return client.get(`/products/${id}/where-used/`, {
      params,
    })
  },
  getLineFinalCandidates(lineId = null, processId = null) {
    const params = {}
    if (lineId) params.line_id = lineId
    if (processId) params.process_id = processId
    return client.get('/products/line-final-candidates/', { params })
  },
  getDisplayProductCandidates(lineId, processId) {
    return client.get('/products/display-product-candidates/', {
      params: { line_id: lineId, process_id: processId },
    })
  },
  bulkUpdateLineFinal(updates) {
    return client.post('/products/bulk-update-line-final/', { updates })
  },
  bulkImport(items) {
    return client.post('/products/bulk-import/', { items })
  },
  downloadImportTemplateXlsx() {
    return client.get('/products/import_template_xlsx/', { responseType: 'blob' })
  },
  importFile(formData) {
    return client.post('/products/import_file/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  downloadUpdateImportTemplateXlsx() {
    return client.get('/products/update_import_template_xlsx/', { responseType: 'blob' })
  },
  bulkUpdateImport(formData, { dryRun = false, appendG = false } = {}) {
    const qp = new URLSearchParams()
    if (dryRun) qp.set('dry_run', 'true')
    if (appendG) qp.set('append_g', 'true')
    const params = qp.toString() ? `?${qp}` : ''
    return client.post(`/products/bulk_update_import/${params}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listContainers(productId) {
    return client.get(`/products/${productId}/containers/`)
  },
  addContainer(productId, data) {
    return client.post(`/products/${productId}/containers/add/`, data)
  },
  updateContainer(productId, pcId, data) {
    return client.patch(`/products/${productId}/containers/${pcId}/`, data)
  },
  removeContainer(productId, pcId) {
    return client.delete(`/products/${productId}/containers/${pcId}/delete/`)
  },
})
