export const createSuppliersAPI = (client) => ({
  getSuppliers() {
    return client.get('/suppliers/')
  },
  getSupplier(id) {
    return client.get(`/suppliers/${id}/`)
  },
  createSupplier(data) {
    return client.post('/suppliers/', data)
  },
  updateSupplier(id, data) {
    return client.put(`/suppliers/${id}/`, data)
  },
  deleteSupplier(id) {
    return client.delete(`/suppliers/${id}/`)
  },
})
