export const createProductionPlanLockSettingAPI = (client) => ({
  getSetting() {
    return client.get('/production-plan-lock-setting/')
  },
  saveSetting(payload) {
    return client.post('/production-plan-lock-setting/', payload)
  },
})
