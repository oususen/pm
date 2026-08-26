/**
 * BOMサービスAPI
 */
export const createBomServiceAPI = (client) => ({
  getBomTree(productId, referenceDate = null) {
    const params = {}
    if (referenceDate) params.reference_date = referenceDate
    return client.get(`/bom-service/bom-tree/${productId}/`, { params })
  },
})
