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
  getBOMItems(params = {}) {
    const queryParams = new URLSearchParams()
    if (params.bom) queryParams.append('bom', params.bom)
    if (params.sourcing_type) queryParams.append('sourcing_type', params.sourcing_type)
    if (params.supplier) queryParams.append('supplier', params.supplier)
    const query = queryParams.toString()
    return client.get(`/bom-items/${query ? '?' + query : ''}`)
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
