export const createProductionRecordSettingsAPI = (client) => ({
  getSettings() {
    return client.get('/production-record-settings/')
  },
  saveSettings(payload) {
    return client.post('/production-record-settings/', payload)
  },
})
