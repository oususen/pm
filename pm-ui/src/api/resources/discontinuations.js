export const createDiscontinuationsAPI = (client) => ({
  list() {
    return client.get('/discontinuations/')
  },
  create(payload) {
    return client.post('/discontinuations/', payload)
  },
  updateCase(id, payload) {
    return client.put(`/discontinuations/${id}/`, payload)
  },
  deleteCase(id) {
    return client.delete(`/discontinuations/${id}/`)
  },
  addProduct(caseId, payload) {
    return client.post(`/discontinuations/${caseId}/products/`, payload)
  },
  updateProduct(id, payload) {
    return client.put(`/discontinuation-products/${id}/`, payload)
  },
  deleteProduct(id) {
    return client.delete(`/discontinuation-products/${id}/`)
  },
  recalculateProduct(id) {
    return client.post(`/discontinuation-products/${id}/recalculate/`)
  },
  addPart(discProductId, payload) {
    return client.post(`/discontinuation-products/${discProductId}/parts/`, payload)
  },
  deletePart(id) {
    return client.delete(`/discontinuation-parts/${id}/`)
  },
  bomLookup(productId) {
    return client.get(`/discontinuation-bom-lookup/?product_id=${productId}`)
  },
})
