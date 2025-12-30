export const createBomsAPI = (client) => ({
  getBOMs(params = {}) {
    const queryParams = new URLSearchParams()
    if (params.search) queryParams.append('search', params.search)
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
