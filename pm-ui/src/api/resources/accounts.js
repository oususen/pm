export const createAccountsAPI = (client) => ({
  getDepartments(params = {}) {
    return client.get('/accounts/departments/', { params })
  },
  getUsers(params = {}) {
    return client.get('/accounts/users/', { params })
  },
  getUser(id) {
    return client.get(`/accounts/users/${id}/`)
  },
  createUser(data) {
    return client.post('/accounts/users/', data)
  },
  updateUser(id, data) {
    return client.put(`/accounts/users/${id}/`, data)
  },
})
