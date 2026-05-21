export function createProductCodeMappingsAPI(client) {
  return {
    list(params = {}) {
      return client.get('/product-code-mappings/', { params })
    },
    create(payload) {
      return client.post('/product-code-mappings/', payload)
    },
    update(id, payload) {
      return client.put(`/product-code-mappings/${id}/`, payload)
    },
    remove(id) {
      return client.delete(`/product-code-mappings/${id}/`)
    },
  }
}

