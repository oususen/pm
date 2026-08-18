export const createIntegratedChecksheetsAPI = (client) => ({
  listTemplates(params = {}) {
    return client.get('/integrated-checksheet-templates/', { params })
  },
  getTemplate(id) {
    return client.get(`/integrated-checksheet-templates/${id}/`)
  },
  createTemplate(data) {
    return client.post('/integrated-checksheet-templates/', data)
  },
  updateTemplate(id, data) {
    return client.patch(`/integrated-checksheet-templates/${id}/`, data)
  },
  deleteTemplate(id) {
    return client.delete(`/integrated-checksheet-templates/${id}/`)
  },
  approveTemplate(id) {
    return client.post(`/integrated-checksheet-templates/${id}/approve/`)
  },
  submitForReview(id) {
    return client.post(`/integrated-checksheet-templates/${id}/submit_for_review/`)
  },
  reviewTemplate(id) {
    return client.post(`/integrated-checksheet-templates/${id}/review/`)
  },
  rejectTemplate(id, data = {}) {
    return client.post(`/integrated-checksheet-templates/${id}/reject/`, data)
  },
  reviseTemplate(id) {
    return client.post(`/integrated-checksheet-templates/${id}/revise/`)
  },
  saveStructure(id, data) {
    return client.post(`/integrated-checksheet-templates/${id}/save_structure/`, data)
  },
  uploadSketch(templateId, blockId, formData) {
    return client.post(`/integrated-checksheet-templates/${templateId}/upload_sketch/${blockId}/`, formData)
  },
  uploadAttachmentImage(formData) {
    return client.post('/integrated-checksheet-templates/upload-attachment-image/', formData)
  },
  listBatches(params = {}) {
    return client.get('/integrated-checksheet-batches/', { params })
  },
  getAnalyticsRecords(params = {}) {
    return client.get('/integrated-checksheet-batches/analytics_records/', { params })
  },
  getBatch(id) {
    return client.get(`/integrated-checksheet-batches/${id}/`)
  },
  deleteBatch(id) {
    return client.delete(`/integrated-checksheet-batches/${id}/`)
  },
  editBatch(id, data) {
    return client.post(`/integrated-checksheet-batches/${id}/edit_batch/`, data)
  },
  prepareBatch(data) {
    return client.post('/integrated-checksheet-batches/prepare/', data)
  },
  getBatchUnits(batchId) {
    return client.get(`/integrated-checksheet-batches/${batchId}/units/`)
  },
  saveChecks(unitId, data) {
    return client.post(`/integrated-checksheet-units/${unitId}/save_checks/`, data)
  },
  saveSketch(unitId, data) {
    return client.post(`/integrated-checksheet-units/${unitId}/save_sketch/`, data)
  },
  releaseHold(unitId, data) {
    return client.post(`/integrated-checksheet-units/${unitId}/release_hold/`, data)
  },
  searchUnitHistory(params) {
    return client.get('/integrated-checksheet-units/search_history/', { params })
  },
  leaderConfirm(batchId) {
    return client.post(`/integrated-checksheet-batches/${batchId}/leader_confirm/`)
  },
  supervisorConfirm(batchId) {
    return client.post(`/integrated-checksheet-batches/${batchId}/supervisor_confirm/`)
  },
  previewPdf(templateId) {
    return client.get(`/integrated-checksheet-templates/${templateId}/preview_pdf/`, { responseType: 'blob' })
  },
  exportBatchPdf(batchId) {
    return client.get(`/integrated-checksheet-batches/${batchId}/export_pdf/`, { responseType: 'blob' })
  },
  listTasks(params = {}) {
    return client.get('/integrated-checksheet-tasks/', { params })
  },
})
