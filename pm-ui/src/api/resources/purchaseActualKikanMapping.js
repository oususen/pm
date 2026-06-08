export const createPurchaseActualKikanMappingAPI = (client) => ({
  getMapping(supplierId) {
    return client.get('/purchase-actual-kikan-mapping/', { params: { supplier_id: supplierId } })
  },
  saveMapping(supplierId, mappings) {
    return client.post('/purchase-actual-kikan-mapping/', { supplier_id: supplierId, mappings })
  },
  getCandidates(supplierId) {
    return client.get('/purchase-actual-kikan-mapping/candidates/', { params: { supplier_id: supplierId } })
  },
})
