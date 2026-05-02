export const createProductChecksheetsAPI = (client) => ({
  listTemplates(params = {}) {
    return client.get('/product-checksheet-templates/', { params })
  },
  getTemplate(id) {
    return client.get(`/product-checksheet-templates/${id}/`)
  },
  createTemplate(formData) {
    return client.post('/product-checksheet-templates/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  updateTemplate(id, data) {
    const isFormData = data instanceof FormData
    return client.patch(`/product-checksheet-templates/${id}/`, data, isFormData
      ? { headers: { 'Content-Type': 'multipart/form-data' } }
      : undefined)
  },
  saveFields(id, payload) {
    return client.post(`/product-checksheet-templates/${id}/save_fields/`, payload)
  },
  activeForTarget(params = {}) {
    return client.get('/product-checksheet-templates/active_for_target/', { params })
  },
  submitForReview(id, comment = '') {
    return client.post(`/product-checksheet-templates/${id}/submit_for_review/`, { comment })
  },
  review(id) {
    return client.post(`/product-checksheet-templates/${id}/review/`)
  },
  approve(id) {
    return client.post(`/product-checksheet-templates/${id}/approve/`)
  },
  reject(id, comment = '') {
    return client.post(`/product-checksheet-templates/${id}/reject/`, { comment })
  },
  revise(id) {
    return client.post(`/product-checksheet-templates/${id}/revise/`)
  },
  previewPdf(id) {
    return client.get(`/product-checksheet-templates/${id}/preview_pdf/`, { responseType: 'blob' })
  },
  listTasks(params = {}) {
    return client.get('/product-checksheet-tasks/', { params })
  },
  listBatches(params = {}) {
    return client.get('/product-checksheet-batches/', { params })
  },
  getBatch(id) {
    return client.get(`/product-checksheet-batches/${id}/`)
  },
  prepareBatch(data) {
    return client.post('/product-checksheet-batches/prepare/', data)
  },
  listBatchRecords(batchId) {
    return client.get(`/product-checksheet-batches/${batchId}/records/`)
  },
  listRecords(params = {}) {
    return client.get('/product-checksheet-records/', { params })
  },
  getRecord(id) {
    return client.get(`/product-checksheet-records/${id}/`)
  },
  saveRecordInput(id, formData) {
    return client.post(`/product-checksheet-records/${id}/save_input/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  approveRecord(id, data) {
    return client.post(`/product-checksheet-records/${id}/approve/`, data)
  },
})
