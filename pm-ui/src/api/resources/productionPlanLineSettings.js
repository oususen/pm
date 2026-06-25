export const createProductionPlanLineSettingsAPI = (client) => ({
  getSettings() {
    return client.get('/production-plan-line-settings/')
  },
  saveSettings(payload) {
    return client.post('/production-plan-line-settings/', payload)
  },
})
