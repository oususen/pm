export const createSupplierTrucksAPI = (client) => ({
  getSupplierTrucks(params = {}) {
    return client.get('/supplier-trucks/', { params })
  },
  getSupplierTruck(id) {
    return client.get(`/supplier-trucks/${id}/`)
  },
  createSupplierTruck(data) {
    return client.post('/supplier-trucks/', data)
  },
  updateSupplierTruck(id, data) {
    return client.put(`/supplier-trucks/${id}/`, data)
  },
  deleteSupplierTruck(id) {
    return client.delete(`/supplier-trucks/${id}/`)
  },
})
