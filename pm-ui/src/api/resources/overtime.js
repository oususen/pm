export const createOvertimeAPI = (client) => ({
  // 申請一覧・CRUD
  getApplications(params = {}) {
    return client.get('/overtime/applications/', { params })
  },
  getApplication(id) {
    return client.get(`/overtime/applications/${id}/`)
  },
  createApplication(data) {
    return client.post('/overtime/applications/', data)
  },
  updateApplication(id, data) {
    return client.patch(`/overtime/applications/${id}/`, data)
  },
  deleteApplication(id) {
    return client.delete(`/overtime/applications/${id}/`)
  },

  // ワークフローアクション
  submitApplication(id) {
    return client.post(`/overtime/applications/${id}/submit/`)
  },
  approveApplication(id, data = {}) {
    return client.post(`/overtime/applications/${id}/approve/`, data)
  },
  rejectApplication(id, data = {}) {
    return client.post(`/overtime/applications/${id}/reject/`, data)
  },

  // 承認待ち一覧
  getPendingApprovals() {
    return client.get('/overtime/applications/pending_approvals/')
  },
})
