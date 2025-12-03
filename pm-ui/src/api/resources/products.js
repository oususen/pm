export const createProductsAPI = (client) => ({
  getProducts() {
    return client.get('/products/')
  },
  getProduct(id) {
    return client.get(`/products/${id}/`)
  },
  createProduct(data) {
    return client.post('/products/', data)
  },
  updateProduct(id, data) {
    return client.put(`/products/${id}/`, data)
  },
  deleteProduct(id) {
    return client.delete(`/products/${id}/`)
  },
})
