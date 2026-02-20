export const createAccountsAPI = (client) => ({
  getDepartments(params = {}) {
    return client.get('/accounts/departments/', { params })
  },
  getDepartmentPermissions(params = {}) {
    return client.get('/accounts/department-permissions/', { params })
  },
  setDepartmentPermissions(payload) {
    return client.post('/accounts/department-permissions/set/', payload)
  },
  getDepartmentPositionPermissions(params = {}) {
    return client.get('/accounts/department-position-permissions/', { params })
  },
  setDepartmentPositionPermissions(payload) {
    return client.post('/accounts/department-position-permissions/set/', payload)
  },
  getDepartmentPositions(params = {}) {
    return client.get('/accounts/department-positions/', { params })
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
  updateUserPartial(id, data) {
    return client.patch(`/accounts/users/${id}/`, data)
  },
  deleteUser(id) {
    return client.delete(`/accounts/users/${id}/`)
  },
  getPositions() {
    return client.get('/accounts/positions/')
  },
  getPositionPermissions(params = {}) {
    return client.get('/accounts/position-permissions/', { params })
  },
  setPositionPermissions(payload) {
    return client.post('/accounts/position-permissions/set/', payload)
  },
  getDivisions() {
    return client.get('/accounts/divisions/')
  },
  getGroups(params = {}) {
    return client.get('/accounts/groups/', { params })
  },
  getTeams(params = {}) {
    return client.get('/accounts/teams/', { params })
  },
})
