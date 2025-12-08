export const createProductsAPI = (client) => ({
  getProducts(params = {}) {
    return client.get('/products/', { params })
  },
  async getAllProducts(params = {}) {
    // ページネーション対応：全ページをまとめて取得
    const results = []
    let nextUrl = '/products/'
    const query = new URLSearchParams(params).toString()
    if (query) {
      nextUrl += `?${query}`
    }
    while (nextUrl) {
      // eslint-disable-next-line no-await-in-loop
      const res = await client.get(nextUrl)
      const data = res.data
      if (Array.isArray(data)) {
        results.push(...data)
        break
      }
      if (data?.results) {
        results.push(...data.results)
        nextUrl = data.next?.replace(client.defaults.baseURL, '') || null
      } else {
        break
      }
    }
    return results
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
