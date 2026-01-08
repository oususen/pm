export const createProductGroupsAPI = (client) => ({
  getProductGroups(params) {
    return client.get('/product-groups/', { params })
  },
  getProductGroup(id) {
    return client.get(`/product-groups/${id}/`)
  },
  createProductGroup(data) {
    return client.post('/product-groups/', data)
  },
  updateProductGroup(id, data) {
    return client.put(`/product-groups/${id}/`, data)
  },
  deleteProductGroup(id) {
    return client.delete(`/product-groups/${id}/`)
  },
})
