export const createBomsAPI = (client) => ({
  getBOMs() {
    return client.get('/boms/')
  },
  getBOM(id) {
    return client.get(`/boms/${id}/`)
  },
  getBOMTree(id) {
    return client.get(`/boms/${id}/tree/`)
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

  // BOM Items
  getBOMItems(bomId) {
    return client.get(`/bom-items/?bom=${bomId}`)
  },
  createBOMItem(data) {
    return client.post('/bom-items/', data)
  },
  updateBOMItem(id, data) {
    return client.put(`/bom-items/${id}/`, data)
  },
  deleteBOMItem(id) {
    return client.delete(`/bom-items/${id}/`)
  },
})
