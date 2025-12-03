export const createCustomersAPI = (client) => ({
  getCustomers() {
    return client.get('/customers/')
  },
  getCustomer(id) {
    return client.get(`/customers/${id}/`)
  },
  createCustomer(data) {
    return client.post('/customers/', data)
  },
  updateCustomer(id, data) {
    return client.put(`/customers/${id}/`, data)
  },
  deleteCustomer(id) {
    return client.delete(`/customers/${id}/`)
  },
})
