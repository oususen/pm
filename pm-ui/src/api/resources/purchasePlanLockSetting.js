export const createPurchasePlanLockSettingAPI = (client) => ({
  getSetting() {
    return client.get('/purchase-plan-lock-setting/')
  },
  saveSetting(payload) {
    return client.post('/purchase-plan-lock-setting/', payload)
  },
})
