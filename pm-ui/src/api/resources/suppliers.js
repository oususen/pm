export const createSuppliersAPI = (client) => ({
  getSuppliers(params = {}) {
    return client.get('/suppliers/', { params })
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
  patchSupplier(id, data) {
    return client.patch(`/suppliers/${id}/`, data)
  },
  deleteSupplier(id) {
    return client.delete(`/suppliers/${id}/`)
  },
})
