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
  cancelSupervisorApproval(id, data = {}) {
    return client.post(`/overtime/applications/${id}/cancel_supervisor_approval/`, data)
  },
  rejectApplication(id, data = {}) {
    return client.post(`/overtime/applications/${id}/reject/`, data)
  },

  // 承認待ち一覧
  getPendingApprovals() {
    return client.get('/overtime/applications/pending_approvals/')
  },

  // サイン画像アップロード
  uploadSignature(id, blob) {
    const form = new FormData()
    form.append('signature', blob, 'signature.png')
    return client.post(`/overtime/applications/${id}/upload_signature/`, form)
  },

  // 一括承認（班長→係長へ確認依頼）
  bulkApproveApplications(data) {
    return client.post('/overtime/applications/bulk_approve/', data)
  },

  // PDF出力
  exportPdf(params = {}) {
    return client.get('/overtime/applications/export_pdf/', {
      params,
      responseType: 'blob',
    })
  },
})
