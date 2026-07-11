export const createShippingProgressHorizonSettingAPI = (client) => ({
  getSetting() {
    return client.get('/shipping-progress-horizon-setting/')
  },
  saveSetting(payload) {
    return client.post('/shipping-progress-horizon-setting/', payload)
  },
})
