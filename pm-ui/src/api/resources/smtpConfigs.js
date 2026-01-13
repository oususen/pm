export const createSmtpConfigsAPI = (client) => ({
  getSmtpConfigs(params) {
    return client.get('/accounts/smtp-configs/', { params })
  },
  getSmtpConfig(id) {
    return client.get(`/accounts/smtp-configs/${id}/`)
  },
  getCurrentUserConfig() {
    return client.get('/accounts/smtp-configs/current_user/')
  },
  createSmtpConfig(data) {
    return client.post('/accounts/smtp-configs/', data)
  },
  updateSmtpConfig(id, data) {
    return client.put(`/accounts/smtp-configs/${id}/`, data)
  },
  deleteSmtpConfig(id) {
    return client.delete(`/accounts/smtp-configs/${id}/`)
  },
})
