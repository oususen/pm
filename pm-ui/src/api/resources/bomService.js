/**
 * BOMサービスAPI
 */
export const createBomServiceAPI = (client) => ({
  getBomTree(productId) {
    return client.get(`/bom-service/bom-tree/${productId}/`)
  },
})

