export const createProductsAPI = (client) => ({
  getProducts(params = {}) {
    return client.get('/products/', { params })
  },
  async getAllProducts(params = {}) {
    // ページング有りでも全件取得できるように順次取得
    const collected = []
    let page = 1
    while (true) {
      const res = await client.get('/products/', {
        params: { page, page_size: 5000, ...params },
      })
      const data = res.data
      if (Array.isArray(data)) return data
      if (data?.results) {
        collected.push(...data.results)
      }
      if (!data?.next) break
      page += 1
    }
    return collected
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
  uploadProductImage(id, formData) {
    return client.post(`/products/${id}/upload_image/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteProduct(id) {
    return client.delete(`/products/${id}/`)
  },
  getWhereUsed(id, recursive = false) {
    return client.get(`/products/${id}/where-used/`, {
      params: { recursive: recursive ? 'true' : 'false' },
    })
  },
})
