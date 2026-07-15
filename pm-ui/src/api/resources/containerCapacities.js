export const createContainerCapacitiesAPI = (client) => ({
  getContainerCapacities(params) {
    return client.get('/container-capacities/', { params })
  },
  getContainerCapacity(id) {
    return client.get(`/container-capacities/${id}/`)
  },
  createContainerCapacity(data) {
    return client.post('/container-capacities/', data)
  },
  updateContainerCapacity(id, data) {
    return client.put(`/container-capacities/${id}/`, data)
  },
  deleteContainerCapacity(id) {
    return client.delete(`/container-capacities/${id}/`)
  },
  importExcelPreview(formData) {
    return client.post('/container-capacities/import_excel_preview/', formData)
  },
  importExcelCommit(payload) {
    return client.post('/container-capacities/import_excel_commit/', payload)
  },
  uploadImages(id, formData) {
    return client.post(`/container-capacities/${id}/upload_images/`, formData)
  },
  deleteImage(id, imageId) {
    return client.delete(`/container-capacities/${id}/images/${imageId}/`)
  },
  addProduct(containerId, data) {
    return client.post(`/container-capacities/${containerId}/products/`, data)
  },
  updateProduct(containerId, pcId, data) {
    return client.patch(`/container-capacities/${containerId}/products/${pcId}/`, data)
  },
  removeProduct(containerId, pcId) {
    return client.delete(`/container-capacities/${containerId}/products/${pcId}/delete/`)
  },
})
