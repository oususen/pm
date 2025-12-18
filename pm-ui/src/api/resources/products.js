export const createProductsAPI = (client) => ({
  getProducts(params = {}) {
    return client.get('/products/', { params })
  },
  async getAllProducts(params = {}) {
    // シンプルに1リクエストで全件取得（page_sizeを大きめに指定）
    const res = await client.get('/products/', {
      params: { page_size: 5000, ...params },
    })
    const data = res.data
    if (Array.isArray(data)) return data
    if (data?.results) return data.results
    return []
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
