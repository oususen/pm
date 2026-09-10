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
  createDepartment(data) {
    return client.post('/accounts/departments/', data)
  },
  updateDepartment(id, data) {
    return client.patch(`/accounts/departments/${id}/`, data)
  },
  deleteDepartment(id) {
    return client.delete(`/accounts/departments/${id}/`)
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
  getUnits(params = {}) {
    return client.get('/accounts/units/', { params })
  },
  getUnitLineMappings(params = {}) {
    return client.get('/accounts/unit-line-mappings/', { params })
  },
  setUnitLineMappingsForLine(payload) {
    return client.post('/accounts/unit-line-mappings/set-for-line/', payload)
  },
  getFavorites(params = {}) {
    return client.get('/accounts/favorites/', { params })
  },
  createFavorite(data) {
    return client.post('/accounts/favorites/', data)
  },
  updateFavorite(id, data) {
    return client.patch(`/accounts/favorites/${id}/`, data)
  },
  deleteFavorite(id) {
    return client.delete(`/accounts/favorites/${id}/`)
  },
  getApprovalRoutes(params = {}) {
    return client.get('/accounts/approval-routes/', { params })
  },
  saveApprovalRoutes(routes, deleteIds = []) {
    return client.put('/accounts/approval-routes/bulk-save/', { routes, delete_ids: deleteIds })
  },
  getApprovalRequests(params = {}) {
    return client.get('/accounts/approval-requests/', { params })
  },
  submitApprovalRequest(id) {
    return client.post(`/accounts/approval-requests/${id}/submit/`)
  },
  confirmApprovalRequest(id) {
    return client.post(`/accounts/approval-requests/${id}/confirm/`)
  },
  approveApprovalRequest(id) {
    return client.post(`/accounts/approval-requests/${id}/approve/`)
  },
  rejectApprovalRequest(id, reason = '') {
    return client.post(`/accounts/approval-requests/${id}/reject/`, { reason })
  },
})
